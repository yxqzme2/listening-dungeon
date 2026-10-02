# -----------------------------------------
# Section 1
# -----------------------------------------
import re
import time
import threading
import os
from contextlib import asynccontextmanager
from typing import List, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# Your existing logic imports
from .config import load_settings
from .absstats_client import ABSStatsClient
from .state_sqlite import StateStore
from .release_radar import (
    search_series_candidates, check_all_series as radar_check_all,
    _product_to_release, search_audible, find_newest_in_series,
    generate_ics, radar_worker, seed_from_abs, check_library_status,
)

# -----------------------------------------
# Section 2: Global Configuration & Initialization
# -----------------------------------------

cfg = load_settings()
store = StateStore(cfg.state_db_path)
client = ABSStatsClient(cfg.absstats_base_url)

def _parse_allowed_users(raw: str) -> set:
    return {
        p.strip().lower()
        for p in str(raw or '').split(',')
        if p and p.strip()
    }

_ALLOWED_USERS = _parse_allowed_users(getattr(cfg, 'allowed_users', ''))

def _user_is_allowed(username: str) -> bool:
    # Empty allow-list means "no filter" (show all users).
    if not _ALLOWED_USERS:
        return True
    return str(username or '').strip().lower() in _ALLOWED_USERS


# -----------------------------------------
# Section 3: Background Worker (The Engine)
# -----------------------------------------


def _fetch_abs_series_index(fallback: Optional[List[Dict]] = None, timeout: int = 30) -> List[Dict]:
    """Fetch fresh series index from ABS Stats; fallback when unavailable."""
    import urllib.request
    import json as _json

    base = cfg.absstats_base_url.rstrip("/")
    req = urllib.request.Request(base + "/api/series", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            payload = _json.loads(r.read())
        series = payload.get("series") or []
        return series if isinstance(series, list) else (fallback or [])
    except Exception:
        return fallback or []

def series_refresh_worker():
    """Keeps the library's series list fresh (Recommendations and the dungeon
    looks use it). The old achievement engine that also ran here is retired."""
    while True:
        try:
            _SERIES_INDEX_CACHE["data"] = client.get_series_index()
            _SERIES_INDEX_CACHE["updated_at"] = int(time.time())
        except Exception as e:
            print(f"Series refresh failed: {e}")
        time.sleep(max(60, cfg.series_refresh_seconds))


# -----------------------------------------
# Section 4: FastAPI App + Lifespan
# -----------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    from . import admin_auth
    admin_auth.startup_notice()

    # Backfill tier-lists.json from DB on every startup
    try:
        _sync_tier_lists_json()
    except Exception as e:
        print(f"[tier-lists] startup JSON sync failed: {e}")

    # Start the background thread on startup
    t = threading.Thread(target=series_refresh_worker, daemon=True)
    t.start()

    # Start the Release Radar background thread
    radar_t = threading.Thread(
        target=radar_worker,
        kwargs={
            "state": store,
            "absstats_base_url": cfg.absstats_base_url,
            "check_interval_hours": cfg.radar_check_interval_hours,
        },
        daemon=True,
    )
    radar_t.start()

    yield
    # nothing on shutdown


app = FastAPI(lifespan=lifespan)

# -----------------------------------------
# The Listening Dungeon (game): player login, characters, dungeon queue
# -----------------------------------------
from . import game_auth as _game_auth
from .game_store import GameStore
from .game_api import build_router as _build_game_router

_game_auth.init(os.path.dirname(os.path.abspath(cfg.state_db_path)))
game_store = GameStore(cfg.state_db_path)
app.include_router(_build_game_router(game_store, store, client, cfg.completed_endpoint, _user_is_allowed,
                                     achievement_defs=lambda: _load_defs_cached()["by_id"]))


def _game_page_path() -> str:
    """The game's front page. Served from the image's static folder so the
    page always matches the running code."""
    baked = os.path.join(_STATIC_DIR, "game", "index.html")
    return baked if os.path.exists(baked) else _get_static_path("game/index.html")

# -----------------------------------------
# Admin session gate
# -----------------------------------------
# Every route with "admin" in its path — pages and APIs alike — requires a
# valid signed session cookie. This is a structural, path-pattern gate
# rather than a per-route Depends() so a future route can't accidentally
# ship unauthenticated just because someone forgot to add the dependency.
from . import admin_auth as _admin_auth

_ADMIN_GATE_EXEMPT = {"/admin/login", "/admin/logout"}

# Write routes without "admin" in the path that still need the admin login.
_ADMIN_ONLY_WRITES = ("/radar/api/", "/awards/api/tier-lists/import-json")


def _is_admin(request: Request) -> bool:
    return _admin_auth.is_valid_session_token(request.cookies.get(_admin_auth.COOKIE_NAME, ""))


def _require_reader(request: Request, user_id: str = "") -> None:
    """Admin, or logged into the game (as user_id, when one is given)."""
    if _is_admin(request):
        return
    session_user = _game_auth.user_from_token(request.cookies.get(_game_auth.COOKIE_NAME, ""))
    if not session_user or (user_id and session_user != user_id):
        raise HTTPException(status_code=401, detail="Log into the game as this reader first.")


@app.middleware("http")
async def _admin_session_gate(request: Request, call_next):
    path = request.url.path
    admin_write = request.method != "GET" and path.startswith(_ADMIN_ONLY_WRITES)
    if (admin_write or "admin" in path.lower()) and path not in _ADMIN_GATE_EXEMPT:
        token = request.cookies.get(_admin_auth.COOKIE_NAME, "")
        if not _admin_auth.is_valid_session_token(token):
            is_api = "/api/" in path
            if request.method == "GET" and not is_api:
                from urllib.parse import quote
                return RedirectResponse(url=f"/admin/login?next={quote(path)}", status_code=302)
            return JSONResponse({"detail": "Admin authentication required."}, status_code=401)
    return await call_next(request)


_LOGIN_PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Admin Login · The Listening Dungeon</title>
<link rel="stylesheet" href="/static/game/paper.css?v=2">
<style>
body{{display:flex;min-height:100vh;align-items:center;justify-content:center;padding:16px}}
form{{background:var(--card);padding:28px;box-shadow:4px 8px 0 rgba(0,0,0,.2);display:flex;flex-direction:column;gap:12px;width:min(340px,100%);transform:rotate(-.6deg)}}
h1{{font-size:28px;margin:0}}
p{{margin:0;color:var(--muted);font-size:16px}}
input{{background:var(--paper);border:2px solid var(--ink);padding:8px 10px;font-size:18px}}
body.paper button{{background:var(--red);color:var(--card);border:0;padding:10px;font-family:var(--marker);font-size:19px;cursor:pointer;clip-path:var(--tilt);box-shadow:2px 3px 0 rgba(0,0,0,.25)}}
.err{{color:var(--red);font-size:16px}}
a{{color:var(--muted);font-size:15px;text-align:center}}
</style></head><body class="paper">
<form method="post" action="/admin/login?next={next_q}">
<h1>Dungeon Admin</h1>
<p>Behind the curtain. Password, please.</p>
{error_html}
<input type="password" name="password" placeholder="Admin password" autofocus>
<button type="submit">Enter</button>
<a href="/">Back to the game</a>
</form></body></html>"""


@app.get("/admin/login")
def admin_login_page(next: str = "/admin"):
    from urllib.parse import quote
    return HTMLResponse(_LOGIN_PAGE.format(next_q=quote(next), error_html=""))


@app.post("/admin/login")
async def admin_login_submit(request: Request, next: str = "/admin"):
    from urllib.parse import quote

    remaining = _admin_auth.login_lockout_remaining(request)
    if remaining > 0:
        mins = max(1, remaining // 60)
        body = _LOGIN_PAGE.format(
            next_q=quote(next),
            error_html=f'<div class="err">Too many failed attempts. Try again in ~{mins} min.</div>',
        )
        return HTMLResponse(body, status_code=429)

    form = await request.form()
    password = str(form.get("password", ""))
    if not _admin_auth.check_password(password):
        _admin_auth.record_login_failure(request)
        body = _LOGIN_PAGE.format(
            next_q=quote(next),
            error_html='<div class="err">Incorrect password.</div>',
        )
        return HTMLResponse(body, status_code=401)

    _admin_auth.record_login_success(request)
    resp = RedirectResponse(url=next or "/admin", status_code=302)
    resp.set_cookie(
        _admin_auth.COOKIE_NAME,
        _admin_auth.make_session_token(),
        max_age=_admin_auth.SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        # HTTPS-only when reached over HTTPS (SWAG); plain http at home would
        # otherwise drop the cookie and bounce back to the login page.
        secure=request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").lower() == "https",
    )
    return resp


@app.get("/admin/logout")
def admin_logout():
    resp = RedirectResponse(url="/admin/login", status_code=302)
    resp.delete_cookie(_admin_auth.COOKIE_NAME)
    return resp


# Serve CSS, JS, and shared assets from /static/
# Use the volume-mounted /static only if it actually has files; otherwise use the
# baked-in /app/static. Docker creates the bind-mount dir as an empty directory
# BEFORE setup.sh runs, so os.path.isdir() alone would always pick the empty dir.
def _static_dir_has_content(path: str) -> bool:
    try:
        return bool(os.listdir(path))
    except Exception:
        return False

# The image's own copy wins so page updates ship with the code; the old
# mount locations are only a fallback.
_STATIC_DIR = "/app/static" if _static_dir_has_content("/app/static") else "/static"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static_assets")

# -----------------------------------------
# Section 5: Web Routes + API (Dashboard data)
# -----------------------------------------

import json
from fastapi import HTTPException

ARCHIVES_PATH = "/app/static/stats.html"
TIER_PATH = "/app/static/tier.html"

# Helper to find data files in either the volume root or a 'data' subfolder
def _get_data_path(filename):
    # PREFERRED: Look in /data subfolders first (The Master Mount model)
    ext = os.path.splitext(filename)[1].lower()
    subfolder = "json" if ext == ".json" else "csv" if ext == ".csv" else ""

    paths = [
        os.path.join("/data", subfolder, filename),
        os.path.join("/data", filename),
        os.path.join("/app", subfolder, filename),  # baked-in fallback
        os.path.join("/app/data", filename),
        filename
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return os.path.join("/data", subfolder, filename) # Default to structured /data

def _find_dir(dirname, default_container_path):
    """Helper to find a directory in common volume locations or workspace."""
    candidates = [
        os.path.join("/data", dirname),       # Master Mount: /data/icons, /data/covers
        default_container_path,              # e.g. /data/covers
        os.path.join("/app", dirname),        # baked-in fallback: /app/icons
        os.path.join("./data", dirname),      # ./data/covers
        os.path.join(".", dirname),           # ./covers
    ]
    for p in candidates:
        if os.path.isdir(p):
            return p
    return os.path.join("/data", dirname)

ACHIEVEMENTS_JSON_PATH = _get_data_path("achievements.points.json")
ICONS_DIR = _find_dir("icons", "/data/icons")
COVERS_DIR = _find_dir("covers", "/data/covers")

# Helper: find a page, preferring the image copy (see below)
def _get_static_path(filename):
    # Search paths in priority order
    # The image's copy comes first: /data/static is seeded once on first
    # install and never updated, so preferring it would hide page updates.
    paths = [
        os.path.join("/app/static", filename),   # Internal build (ships with the code)
        os.path.join("/data/static", filename), # Old master mount: fallback only
        os.path.join("/static", filename),       # Legacy mount
        os.path.join("data/static", filename),  # Local dev (data folder)
        os.path.join("pages", filename),         # Local dev (pages folder)
        os.path.join("static", filename),        # Local dev (static folder)
        filename
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return os.path.join("/app/static", filename) # Default

ARCHIVES_PATH = _get_static_path("stats.html")
TIER_PATH = _get_static_path("tier.html")
RADAR_PATH = _get_static_path("radar.html")
REQUEST_PATH = _get_static_path("request.html")

# Integration Launch Date (January 01, 2026 00:00 AM UTC)


# Gear system CSV paths (Checking /data volume first, then internal /app/csv)
def _get_csv_path(filename):
    data_path = os.path.join("/data/csv", filename)
    if os.path.exists(data_path):
        return data_path
    return os.path.join("/app/csv", filename)

# Gear catalog loaded once at module level (reload on mtime change)
_GEAR_CACHE: Dict = {
    "gear":           {},   # item_id -> item dict
    "quests_by_id":   {},
    "quests_by_series": {},
    "quests_by_book": {},
    "xp_per_level":   [],
    "loot_mtime":     0,
    "quest_mtime":    0,
    "loot_path":      "",
}

# Global series index for API enrichment
_SERIES_INDEX_CACHE = {"data": [], "updated_at": 0}


# Cache definitions so we don't re-read JSON on every request
_DEFS_CACHE = {"mtime": 0, "items": [], "by_id": {}}


def _load_defs_cached():
    try:
        st = os.stat(ACHIEVEMENTS_JSON_PATH)
        mtime = int(st.st_mtime)
    except FileNotFoundError:
        _DEFS_CACHE["mtime"] = 0
        _DEFS_CACHE["items"] = []
        _DEFS_CACHE["by_id"] = {}
        return _DEFS_CACHE

    if _DEFS_CACHE["items"] and _DEFS_CACHE["mtime"] == mtime:
        return _DEFS_CACHE

    with open(ACHIEVEMENTS_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Your file is typically {"achievements":[...]}
    items = data["achievements"] if isinstance(data, dict) and "achievements" in data else data
    if not isinstance(items, list):
        items = []

    by_id = {}
    for a in items:
        ach_id = a.get("id") or a.get("achievement_id") or a.get("key")
        if ach_id:
            by_id[str(ach_id)] = a

    _DEFS_CACHE["mtime"] = mtime
    _DEFS_CACHE["items"] = items
    _DEFS_CACHE["by_id"] = by_id
    return _DEFS_CACHE


def _get_user_map_best_effort() -> Dict[str, str]:
    """
    Pull uuid -> username map from ABSStats /api/usernames.
    Do it via direct HTTP so we don't depend on ABSStatsClient implementing get_usernames().
    """
    user_map: Dict[str, str] = {}
    try:
        import urllib.request
        import json as _json

        url = cfg.absstats_base_url.rstrip("/") + "/api/usernames"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            u = _json.loads(raw)

        if isinstance(u, dict):
            if isinstance(u.get("map"), dict):
                user_map = {str(k): str(v) for k, v in u["map"].items()}
            elif isinstance(u.get("users"), list):
                for row in u["users"]:
                    uid = row.get("id")
                    un = row.get("username")
                    if uid and un:
                        user_map[str(uid)] = str(un)

        if not user_map:
            print(f"[api] /api/usernames returned empty map from {url}")

    except Exception as e:
        print(f"[api] /api/usernames fetch failed (continuing without usernames): {e}")

    return user_map


_USER_XP_START_CACHE: Dict = {
    "path": "",
    "mtime": 0,
    "map": {},
}


# -----------------------------------------
# Cover Sync State (shared across threads)
# -----------------------------------------

_SYNC_STATE: Dict = {
    "running": False,
    "done": False,
    "total": 0,
    "synced": 0,
    "skipped": 0,
    "errors": 0,
    "message": "Idle",
}


def _sanitize_cover_filename(title: str) -> str:
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", title)
    safe = re.sub(r"\s+", "_", safe.strip())
    return safe[:200] or "unknown"


def _download_cover(absstats_base_url: str, item_id: str, dest: str) -> bool:
    """Download a single cover by libraryItemId. Returns True on success."""
    import urllib.request
    cover_url = absstats_base_url.rstrip("/") + f"/api/cover/{item_id}"
    try:
        with urllib.request.urlopen(urllib.request.Request(cover_url), timeout=15) as resp:
            if resp.status != 200:
                return False
            cover_data = resp.read()
        if len(cover_data) > 100:
            with open(dest, "wb") as f:
                f.write(cover_data)
            return True
        return False
    except Exception:
        return False


def _run_cover_sync(absstats_base_url: str, covers_dir: str, force: bool = False):
    import urllib.request, json as _json

    _SYNC_STATE.update({"running": True, "done": False, "total": 0,
                        "synced": 0, "skipped": 0, "errors": 0,
                        "message": "Fetching series list from ABS…"})
    try:
        base = absstats_base_url.rstrip("/")
        os.makedirs(covers_dir, exist_ok=True)

        # Step 1: Fetch series index — one cover per series (first book only)
        try:
            with urllib.request.urlopen(urllib.request.Request(base + "/api/series"), timeout=30) as resp:
                series_data = _json.loads(resp.read())
            series_list = series_data.get("series") or []
        except Exception:
            series_list = []

        # Build set of all book IDs that belong to a series (to exclude from standalone sync)
        series_book_ids: set = set()
        # List of (series_name, first_book_item_id) to download
        series_covers: list = []

        for s in series_list:
            series_name = (s.get("seriesName") or "").strip()
            books = s.get("books") or []
            if not series_name or not books:
                continue

            # Track all book IDs in this series
            for b in books:
                bid = b.get("libraryItemId")
                if bid:
                    series_book_ids.add(bid)

            # Find first book by seriesSequence (numeric sort), fallback to list order
            def _seq(b):
                try:
                    return float(b.get("seriesSequence") or 9999)
                except Exception:
                    return 9999.0

            first_book = min(books, key=_seq)
            first_id = first_book.get("libraryItemId")
            if first_id:
                series_covers.append((series_name, first_id))

        # Step 2: Fetch all items — find standalones (not in any series)
        _SYNC_STATE["message"] = "Fetching full item list for standalone books…"
        try:
            with urllib.request.urlopen(urllib.request.Request(base + "/api/all-items"), timeout=30) as resp:
                items_data = _json.loads(resp.read())
            all_items = items_data.get("items") or []
        except Exception:
            all_items = []

        standalone_covers: list = []  # (title, item_id)
        for item in all_items:
            item_id = item.get("libraryItemId") or ""
            if not item_id or item_id in series_book_ids:
                continue
            title = (item.get("title") or "").strip() or item_id
            standalone_covers.append((title, item_id))

        total = len(series_covers) + len(standalone_covers)
        _SYNC_STATE["total"] = total
        _SYNC_STATE["message"] = (
            f"Downloading {len(series_covers)} series covers "
            f"and {len(standalone_covers)} standalone covers…"
        )

        # Build covers-meta: filename -> {series, books}
        covers_meta: dict = {}

        # Step 3: Download series covers — saved as {series_name}.jpg
        for s in series_list:
            series_name = (s.get("seriesName") or "").strip()
            books = s.get("books") or []
            if not series_name or not books:
                continue
            filename = _sanitize_cover_filename(series_name) + ".jpg"
            book_titles = [b.get("title", "").strip() for b in books if b.get("title")]
            covers_meta[filename] = {"series": series_name, "books": book_titles}

        for series_name, item_id in series_covers:
            filename = _sanitize_cover_filename(series_name) + ".jpg"
            dest = os.path.join(covers_dir, filename)
            if not force and os.path.exists(dest):
                _SYNC_STATE["skipped"] += 1
                continue
            if _download_cover(base, item_id, dest):
                _SYNC_STATE["synced"] += 1
            else:
                _SYNC_STATE["errors"] += 1

        # Step 4: Download standalone covers — saved as {book_title}.jpg
        for title, item_id in standalone_covers:
            filename = _sanitize_cover_filename(title) + ".jpg"
            dest = os.path.join(covers_dir, filename)
            covers_meta[filename] = {"series": None, "books": [title]}
            if not force and os.path.exists(dest):
                _SYNC_STATE["skipped"] += 1
                continue
            if _download_cover(base, item_id, dest):
                _SYNC_STATE["synced"] += 1
            else:
                _SYNC_STATE["errors"] += 1

        # Write covers-meta.json sidecar for tier page book-title search
        try:
            meta_path = os.path.join(covers_dir, "covers-meta.json")
            with open(meta_path, "w", encoding="utf-8") as mf:
                _json.dump(covers_meta, mf, ensure_ascii=False)
        except Exception:
            pass

        skipped_part = f", {_SYNC_STATE['skipped']} already existed" if _SYNC_STATE["skipped"] else ""
        errors_part  = f", {_SYNC_STATE['errors']} errors" if _SYNC_STATE["errors"] else ""
        _SYNC_STATE["message"] = f"Done: {_SYNC_STATE['synced']} new{skipped_part}{errors_part}."
    except Exception as e:
        _SYNC_STATE["message"] = f"Sync failed: {e}"
    finally:
        _SYNC_STATE["running"] = False
        _SYNC_STATE["done"] = True


@app.post("/awards/api/sync-covers")
def start_cover_sync(request: Request, force: bool = False):
    _require_reader(request)
    if _SYNC_STATE["running"]:
        return JSONResponse({"started": False, "message": "Sync already in progress."}, status_code=409)
    t = threading.Thread(target=_run_cover_sync, args=(cfg.absstats_base_url, COVERS_DIR, force), daemon=True)
    t.start()
    return JSONResponse({"started": True, "message": "Cover sync started."})


@app.get("/awards/api/sync-covers/status")
def cover_sync_status():
    return JSONResponse(dict(_SYNC_STATE))


@app.get("/awards/api/covers-meta")
def covers_meta_endpoint():
    """Return covers-meta.json — maps cover filename to series name + book titles."""
    import json as _json
    meta_path = os.path.join(COVERS_DIR, "covers-meta.json")
    if not os.path.exists(meta_path):
        return JSONResponse({})
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return JSONResponse(_json.load(f))
    except Exception:
        return JSONResponse({})


@app.get("/")
def game_front_page():
    return FileResponse(_game_page_path())

# Pages retired by The Listening Dungeon (docs/BOOK_DUNGEON_DESIGN.md §8).
# Old bookmarks land on the hub; the files stay in static/ for reference.
_RETIRED_PAGES = ["/landing", "/awards/", "/awards/landing", "/quests", "/journal", "/champions", "/timeline",
                  "/playlist", "/review", "/forge", "/character", "/roster", "/loot",
                  "/awards/journal", "/awards/champions", "/awards/timeline", "/awards/playlist", "/awards/forge",
                  "/awards/quests", "/awards/character", "/awards/roster",
                  # the old Wrapped slides, dashboards and achievement poller (removed with the old engine)
                  "/wrapped", "/awards/wrapped", "/system-alert", "/system/poll", "/dashboard", "/leaderboard"]


def _retired_page():
    return RedirectResponse(url="/", status_code=302)


for _path in _RETIRED_PAGES:
    app.add_api_route(_path, _retired_page, methods=["GET"], include_in_schema=False)

# Admin pages retired with the old achievement system and the installer
# builders (Forge, Bounty Board, Template Manager, Docker Script).
_RETIRED_ADMIN_PAGES = ["/admin/forge", "/admin/template", "/admin/template-builder", "/admin/quest", "/admin/bounties",
                        "/admin/setup", "/awards/admin/quest", "/awards/admin/bounties", "/awards/admin/setup",
                        "/template", "/awards/template"]


def _retired_admin_page():
    return RedirectResponse(url="/admin", status_code=302)


for _path in _RETIRED_ADMIN_PAGES:
    app.add_api_route(_path, _retired_admin_page, methods=["GET"], include_in_schema=False)


@app.get("/chronicle")
@app.get("/awards/chronicle")
def read_chronicle_root():
    return FileResponse(_get_static_path("chronicle.html"))

@app.get("/archives")
def read_archives_root():
    return FileResponse(_get_static_path("stats.html"))

@app.get("/tier")
def read_tier_root():
    return FileResponse(_get_static_path("tier.html"))

@app.get("/admin/requests")
def read_requests_admin():
    return FileResponse(_get_static_path("admin/requests.html"))

@app.get("/admin/monsters")
def read_monster_workshop():
    return FileResponse(_get_static_path("admin/monsters.html"))

@app.get("/admin/radar")
def read_radar_admin():
    return FileResponse(_get_static_path("admin/radar.html"))


# ── Wrapped slide pages ────────────────────────────────────────────────────────
_WRAPPED_SLIDES = ['intro','hours','books','author','months','personality','execute','gear','outro']


@app.get("/recommendations")
def read_recommendations_root():
    return FileResponse(_get_static_path("recommendations.html"))

@app.get("/awards/archives")
def read_archives():
    return FileResponse(_get_static_path("stats.html"))

@app.get("/awards/tier")
def read_tier():
    return FileResponse(_get_static_path("tier.html"))


@app.get("/admin")
@app.get("/awards/admin")
def read_admin_hub():
    return FileResponse(_get_static_path("admin/index.html"))

@app.get("/admin/ops")
@app.get("/awards/admin/ops")
def read_admin_ops():
    return FileResponse(_get_static_path("admin/ops.html"))

@app.get("/admin/loot")
@app.get("/admin/armory")
@app.get("/awards/admin/loot")
@app.get("/awards/admin/armory")
def read_admin_armory():
    return FileResponse(_get_static_path("admin/loot.html"))

# --- Admin API: Script Execution ---
import subprocess

@app.post("/awards/api/admin/run-script/{script_id}")
async def api_admin_run_script(script_id: str):
    script_map = {
        "fix_icons": "reassign_broken_icons.py",
        "generate_10": "generate_10.py",
    }
    
    script_file = script_map.get(script_id)
    if not script_file:
        raise HTTPException(status_code=404, detail="Script definition not found.")
    
    # The image's copy first (/data/scripts is seeded once and goes stale).
    candidates = [os.path.join(d, script_file) for d in ("/defaults/scripts", "/app/scripts", "/data/scripts", "scripts")]
    script_path = next((c for c in candidates if os.path.exists(c)), None)
    if not script_path:
        raise HTTPException(status_code=404, detail=f"Script file {script_file} not found on disk.")

    try:
        # Run the script and capture output
        result = subprocess.run(
            ["python", script_path],
            capture_output=True,
            text=True,
            timeout=120 # 2 minute timeout
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Script timed out after 120 seconds."}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# --- Admin API: Manual Loot/Quest Add ---
import csv

@app.post("/awards/api/admin/loot/add")
async def api_admin_loot_add(request: Request):
    data = await request.json()
    loot_path = _get_csv_path("loot.csv")
    
    # 1. Generate new ID
    new_id = "loot_001"
    try:
        with open(loot_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            last_id_num = 0
            for row in reader:
                try:
                    num = int(row['item_id'].split('_')[1])
                    if num > last_id_num: last_id_num = num
                except: pass
            new_id = f"loot_{last_id_num + 1:03}"
    except: pass

    # 2. Append row
    new_row = {
        "item_id": new_id,
        "item_name": data.get("item_name"),
        "slot": data.get("slot"),
        "str": data.get("str", 0),
        "mag": data.get("mag", 0),
        "def": data.get("def", 0),
        "hp": data.get("hp", 0),
        "special_ability": data.get("special_ability", "None"),
        "rarity": data.get("rarity", "Common"),
        "flavor_text": data.get("flavor_text", ""),
        "series_tag": data.get("series_tag", ""),
        "icon": data.get("icon", "")
    }
    
    try:
        with open(loot_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=new_row.keys(), quoting=csv.QUOTE_ALL)
            writer.writerow(new_row)
        # Clear gear cache
        _GEAR_CACHE["loot_mtime"] = 0
        return {"ok": True, "id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Test/Development Routes (For working on "good" pages while event is live) ---


@app.get("/awards/api/tier-users")
def api_tier_users():
    user_map = _get_user_map_best_effort()
    users = []
    for uid, uname in (user_map or {}).items():
        username = str(uname or "").strip()
        if not username:
            continue
        if not _user_is_allowed(username):
            continue
        users.append({"user_id": str(uid), "username": username})
    users.sort(key=lambda x: str(x.get("username") or "").lower())
    return JSONResponse({"users": users})


@app.get("/api/tier-users")
def api_tier_users_root():
    return api_tier_users()


TIER_LISTS_JSON = "/data/tier-lists.json"

def _sync_tier_lists_json():
    """Write all saved tier lists to /data/tier-lists.json as a human-readable mirror."""
    import json as _json
    try:
        rows = store.get_tier_lists()
        out = []
        for r in rows:
            out.append({
                "user_id":    str(r.get("user_id") or ""),
                "username":   str(r.get("username") or ""),
                "list_name":  str(r.get("list_name") or "Tier List"),
                "query":      str(r.get("query") or ""),
                "updated_at": int(r.get("updated_at") or 0),
            })
        os.makedirs(os.path.dirname(TIER_LISTS_JSON), exist_ok=True)
        with open(TIER_LISTS_JSON, "w", encoding="utf-8") as f:
            _json.dump(out, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[tier-lists] failed to write JSON mirror: {e}")


@app.get("/awards/api/tier-lists")
def api_tier_lists():
    user_map = _get_user_map_best_effort()
    rows = store.get_tier_lists()
    out = []
    for r in rows:
        uid = str(r.get("user_id") or "").strip()
        uname = str(r.get("username") or user_map.get(uid) or uid).strip()
        if not _user_is_allowed(uname):
            continue
        out.append({
            "user_id": uid,
            "username": uname,
            "name": str(r.get("list_name") or "Tier List"),
            "query": str(r.get("query") or ""),
            "updated_at": int(r.get("updated_at") or 0),
        })
    return JSONResponse({"lists": out})


@app.get("/api/tier-lists")
def api_tier_lists_root():
    return api_tier_lists()


@app.post("/awards/api/tier-lists")
async def api_tier_lists_save(request: Request):
    body = await request.json()
    raw_user = str((body or {}).get("user_id") or "").strip()
    raw_name = str((body or {}).get("name") or "").strip()
    raw_query = str((body or {}).get("query") or "").strip()
    raw_pin = str((body or {}).get("pin") or "").strip()

    if not raw_user:
        raise HTTPException(status_code=400, detail="user_id is required")
    if not raw_query:
        raise HTTPException(status_code=400, detail="query is required")
    user_map = _get_user_map_best_effort()
    user_id = raw_user
    username = user_map.get(user_id, "")
    if not username:
        lower = raw_user.lower()
        rev = {str(v).lower(): str(k) for k, v in user_map.items()}
        if lower in rev:
            user_id = rev[lower]
            username = raw_user
        else:
            username = raw_user

    if not _user_is_allowed(username):
        raise HTTPException(status_code=403, detail="user not allowed")

    # Logged into the game as this reader? Then no PIN needed.
    session_user = _game_auth.user_from_token(request.cookies.get(_game_auth.COOKIE_NAME, ""))
    if session_user != user_id:
        if not raw_pin:
            raise HTTPException(status_code=400, detail="pin is required")
        if store.get_pin(user_id) is None:
            raise HTTPException(status_code=403, detail="PIN not set for this user.")
        if not store.verify_pin(user_id, raw_pin):
            raise HTTPException(status_code=401, detail="Invalid PIN.")

    list_name = raw_name or f"{username}'s Tier List"
    ts = int(time.time())
    store.upsert_tier_list(user_id=user_id, username=username, list_name=list_name, query=raw_query, updated_at=ts)
    _sync_tier_lists_json()
    return JSONResponse({
        "ok": True,
        "list": {
            "user_id": user_id,
            "username": username,
            "name": list_name,
            "query": raw_query,
            "updated_at": ts,
        }
    })


@app.post("/api/tier-lists")
async def api_tier_lists_save_root(request: Request):
    return await api_tier_lists_save(request)


@app.post("/awards/api/tier-lists/{user_id}/delete")
async def api_tier_lists_delete(user_id: str, request: Request):
    body = await request.json()
    raw_pin = str((body or {}).get("pin") or "").strip()
    if not raw_pin:
        raise HTTPException(status_code=400, detail="pin is required")

    target_uid = str(user_id).strip()
    if store.get_pin(target_uid) is None:
        raise HTTPException(status_code=403, detail="PIN not set for this user.")
    if not store.verify_pin(target_uid, raw_pin):
        raise HTTPException(status_code=401, detail="Invalid PIN.")

    store.delete_tier_list(target_uid)
    _sync_tier_lists_json()
    return JSONResponse({"ok": True})


@app.post("/api/tier-lists/{user_id}/delete")
async def api_tier_lists_delete_root(user_id: str, request: Request):
    return await api_tier_lists_delete(user_id=user_id, request=request)


# -----------------------------------------
# Recommendations engine (series_recs.py)
# -----------------------------------------

def _get_finished_ids_for_user(user_id: str) -> set:
    """Same /api/completed fetch-and-match pattern used throughout main.py
    for other per-user routes."""
    import urllib.request, json as _json
    base = cfg.absstats_base_url.rstrip("/")
    try:
        req = urllib.request.Request(base + cfg.completed_endpoint, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = _json.loads(r.read())
        for u in (data.get("users") or []):
            uid = str(u.get("userId") or u.get("id") or "")
            if uid == user_id:
                return set(str(k) for k, v in (u.get("finishedDates") or {}).items() if v)
    except Exception as e:
        print(f"[recs] finished_ids fetch failed for {user_id}: {e}")
    return set()


def _first_book_id_in_series(series_key: str, series_index: List[Dict]) -> Optional[str]:
    """Lowest seriesSequence book's libraryItemId, for the tag-submission gate."""
    from .series_recs import series_library_item_ids
    item_ids = series_library_item_ids(series_key, series_index)
    return item_ids[0] if item_ids else None


@app.get("/awards/api/series-names")
def api_series_names():
    """Plain list of known series names, for the tag-submission autocomplete."""
    series_index = _fetch_abs_series_index()
    names = sorted({(s.get("seriesName") or "").strip() for s in series_index if s.get("seriesName")})
    return JSONResponse({"series": names})


@app.get("/awards/api/recommendations/{user_id}")
def api_recommendations(user_id: str, boost: str = "", fresh: bool = False):
    from .series_recs import score_recommendations
    tl = store.get_tier_list(user_id)
    boost_tags = [t.strip() for t in boost.split(",") if t.strip()] if boost else None

    # "Start from scratch" mode doesn't need tier-list history at all — it
    # ranks purely by checked tags. Only the normal personalized mode
    # requires a saved tier list to build an affinity profile from.
    if not fresh and (not tl or not tl.get("query")):
        return JSONResponse({"user_id": user_id, "recommendations": [], "reason": "no_tier_list"})

    series_index = _fetch_abs_series_index()
    tier_query = (tl or {}).get("query", "")
    results = score_recommendations(store, tier_query, series_index, boost_tags=boost_tags, fresh=fresh)
    return JSONResponse({"user_id": user_id, "recommendations": results, "fresh": fresh})


@app.post("/awards/api/auth/verify-pin")
async def api_verify_user_pin(request: Request):
    """Small internal-safe PIN check used before an Audiobookshelf write."""
    data = await request.json()
    user_id = str(data.get("user_id") or "").strip()
    pin = str(data.get("pin") or "").strip()
    if not user_id or not pin:
        raise HTTPException(status_code=400, detail="user_id and pin are required")
    if store.get_pin(user_id) is None:
        raise HTTPException(status_code=403, detail="PIN not set for this user.")
    if not store.verify_pin(user_id, pin):
        raise HTTPException(status_code=401, detail="Invalid PIN.")
    return JSONResponse({"ok": True})


@app.get("/awards/api/taste-profile/{user_id}")
def api_taste_profile(user_id: str):
    """Return an explainable visual summary of this user's liked tiers."""
    from .series_recs import build_taste_profile

    tl = store.get_tier_list(user_id)
    if not tl or not tl.get("query"):
        return JSONResponse({
            "user_id": user_id,
            "liked_series_count": 0,
            "tagged_series_count": 0,
            "tier_counts": {"S": 0, "A": 0, "B": 0},
            "traits": [],
            "reason": "no_tier_list",
        })

    series_index = _fetch_abs_series_index()
    profile = build_taste_profile(store, tl["query"], series_index)
    return JSONResponse({"user_id": user_id, **profile})


@app.get("/awards/api/tags/all")
def api_all_tags():
    from .series_recs import all_distinct_tags
    return JSONResponse({"tags": all_distinct_tags(store)})


@app.get("/awards/api/series-tags/{series_key}")
def api_get_series_tags(series_key: str):
    return JSONResponse({"series_key": series_key, "tags": store.get_series_tags(series_key)})


@app.post("/awards/api/series-tags")
async def api_add_series_tag(request: Request):
    from .series_recs import normalize_series_key, normalize_tag
    data = await request.json()
    user_id = str(data.get("user_id") or "").strip()
    series_name = str(data.get("series_name") or "").strip()
    tag = normalize_tag(str(data.get("tag") or ""))
    if not user_id or not series_name or not tag:
        raise HTTPException(status_code=400, detail="user_id, series_name, and tag are required")
    _require_reader(request, user_id)

    series_key = normalize_series_key(series_name)
    series_index = _fetch_abs_series_index()
    first_book_id = _first_book_id_in_series(series_key, series_index)
    if not first_book_id:
        raise HTTPException(status_code=404, detail="Series not found in library.")

    finished_ids = _get_finished_ids_for_user(user_id)
    if first_book_id not in finished_ids:
        raise HTTPException(
            status_code=403,
            detail="Finish at least the first book in this series before tagging it.",
        )

    added = store.add_series_tag(series_key, tag, source="user", user_id=user_id)
    return JSONResponse({"ok": True, "already_existed": not added})


@app.delete("/awards/api/series-tags")
async def api_delete_series_tag(request: Request):
    from .series_recs import normalize_series_key, normalize_tag
    data = await request.json()
    user_id = str(data.get("user_id") or "").strip()
    series_name = str(data.get("series_name") or "").strip()
    tag = normalize_tag(str(data.get("tag") or ""))
    if not user_id or not series_name or not tag:
        raise HTTPException(status_code=400, detail="user_id, series_name, and tag are required")
    _require_reader(request, user_id)
    series_key = normalize_series_key(series_name)
    removed = store.delete_user_series_tag(series_key, tag, user_id)
    return JSONResponse({"ok": True, "removed": removed})


@app.post("/awards/api/admin/tags/backfill")
def api_admin_tags_backfill(royalroad: bool = False):
    """Runs the combined Audible category+keyword backfill against every
    series Release Radar has already matched an ASIN for. Synchronous —
    one request per tracked series with a small delay between, so this can
    take a while for a large tracked-series list; that's expected.

    royalroad=true additionally attempts a strict, owner-triggered Royal
    Road enrichment pass (see series_recs.py) — off by default, only runs
    when explicitly requested, never automatically."""
    from .series_recs import backfill_tags_from_audible
    rows = store.get_tracked_series()
    result = backfill_tags_from_audible(store, rows, include_royalroad=royalroad)
    result["source_counts"] = store.series_tag_source_counts()
    return JSONResponse(result)


@app.post("/awards/api/tier-lists/import-json")
def api_tier_lists_import_json():
    """
    Re-import tier-lists.json from /data/ into the database.
    Overwrites any existing row for each user_id found in the file.
    Useful after manually editing the JSON file.
    """
    import json as _json
    if not os.path.exists(TIER_LISTS_JSON):
        raise HTTPException(status_code=404, detail="tier-lists.json not found in /data/")
    try:
        with open(TIER_LISTS_JSON, "r", encoding="utf-8") as f:
            rows = _json.load(f)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse tier-lists.json: {e}")

    if not isinstance(rows, list):
        raise HTTPException(status_code=400, detail="tier-lists.json must be a JSON array")

    imported = 0
    for row in rows:
        uid  = str(row.get("user_id") or "").strip()
        uname = str(row.get("username") or uid).strip()
        lname = str(row.get("list_name") or "Tier List").strip()
        query = str(row.get("query") or "").strip()
        ts    = int(row.get("updated_at") or int(time.time()))
        if not uid or not query:
            continue
        store.upsert_tier_list(user_id=uid, username=uname, list_name=lname, query=query, updated_at=ts)
        imported += 1

    return JSONResponse({"ok": True, "imported": imported})


@app.post("/awards/api/gear/set-pin")
async def api_set_pin(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    pin = str(data.get("pin", "")).strip()
    
    if not user_id or not pin:
        raise HTTPException(status_code=400, detail="user_id and pin required")
    
    if store.get_pin(user_id) is not None:
        raise HTTPException(status_code=403, detail="PIN already set. System reset required for changes.")
    
    store.set_pin(user_id, pin)
    return JSONResponse({"ok": True})


@app.get("/awards/api/usernames")
def awards_proxy_usernames():
    import urllib.request, json as _json
    url = cfg.absstats_base_url.rstrip("/") + "/api/usernames"
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=10) as r:
            body = r.read()
        data = _json.loads(body)
        # Apply achievement-engine ALLOWED_USERS filter on top of abs-stats ALLOWED_USERNAMES
        if _ALLOWED_USERS:
            if "users" in data:
                data["users"] = [u for u in data["users"] if _user_is_allowed(u.get("username", ""))]
            if "map" in data:
                data["map"] = {k: v for k, v in data["map"].items() if _user_is_allowed(v)}
        return JSONResponse(data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/awards/api/users")
def awards_proxy_users():
    import urllib.request
    import json
    url = cfg.absstats_base_url.rstrip("/") + "/api/users"
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=60) as r:
            body = r.read()

        # Filter the users list when ALLOWED_USERS is configured
        data = json.loads(body)
        if "users" in data and _ALLOWED_USERS:
            data["users"] = [u for u in data["users"] if _user_is_allowed(u.get("username"))]
            body = json.dumps(data).encode('utf-8')

        return Response(content=body, media_type="application/json")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/awards/api/playlists")
def awards_proxy_playlists():
    import urllib.request
    url = cfg.absstats_base_url.rstrip("/") + "/api/playlists"
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=10) as r:
            body = r.read()
            ct = r.headers.get("Content-Type", "application/json")
        return Response(content=body, media_type=ct)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/awards/api/playlists/{user_id}")
def awards_user_playlists(user_id: str):
    """Return only the existing playlists owned by the selected listener."""
    import urllib.request

    target = str(user_id or "").strip()
    if not target:
        raise HTTPException(status_code=400, detail="user_id is required")
    url = cfg.absstats_base_url.rstrip("/") + "/api/playlists"
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=15) as response:
            data = json.loads(response.read())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    user = next(
        (
            row for row in (data.get("users") or [])
            if target.casefold() in {
                str(row.get("userId") or row.get("id") or "").casefold(),
                str(row.get("username") or "").casefold(),
            }
        ),
        None,
    )
    if not user:
        return JSONResponse({"user_id": target, "playlists": []})
    if not _user_is_allowed(user.get("username")):
        raise HTTPException(status_code=403, detail="user not allowed")

    playlists = [
        {
            "id": str(playlist.get("id") or ""),
            "name": str(playlist.get("name") or "Untitled playlist"),
            "item_count": int(playlist.get("itemCount") or 0),
        }
        for playlist in (user.get("playlists") or [])
        if playlist.get("id")
    ]
    return JSONResponse({
        "user_id": str(user.get("userId") or target),
        "username": str(user.get("username") or ""),
        "playlists": playlists,
    })


@app.post("/awards/api/playlists/{user_id}/add-series")
async def awards_add_series_to_playlist(user_id: str, request: Request):
    """PIN-gated proxy that adds every live library item in a series."""
    import asyncio
    import urllib.error
    import urllib.parse
    import urllib.request
    from .series_recs import normalize_series_key, series_library_item_ids

    data = await request.json()
    target = str(user_id or "").strip()
    pin = str(data.get("pin") or "").strip()
    playlist_id = str(data.get("playlist_id") or "").strip()
    series_key = normalize_series_key(str(data.get("series_key") or ""))
    if not target or not pin or not playlist_id or not series_key:
        raise HTTPException(
            status_code=400,
            detail="user_id, pin, playlist_id, and series_key are required",
        )
    if store.get_pin(target) is None:
        raise HTTPException(status_code=403, detail="PIN not set for this user.")
    if not store.verify_pin(target, pin):
        raise HTTPException(status_code=401, detail="Invalid PIN.")

    series_index = _fetch_abs_series_index(timeout=30)
    item_ids = series_library_item_ids(series_key, series_index)
    if not item_ids:
        raise HTTPException(status_code=404, detail="Series not found in the live library.")

    url = (
        cfg.absstats_base_url.rstrip("/")
        + f"/api/users/{urllib.parse.quote(target, safe='')}/playlists/"
        + f"{urllib.parse.quote(playlist_id, safe='')}/items"
    )
    body = json.dumps({
        "libraryItemIds": item_ids,
        "pin": pin,
    }).encode("utf-8")

    def forward_request():
        upstream = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(upstream, timeout=90) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {"message": raw.decode("utf-8", errors="replace")}
            return exc.code, payload

    try:
        status, result = await asyncio.to_thread(forward_request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    if status >= 400:
        detail = result.get("message") or result.get("detail") or result.get("error") or "Audiobookshelf rejected the update."
        raise HTTPException(status_code=status, detail=detail)
    return JSONResponse(result)


@app.get("/awards/api/cover/{item_id}")
def awards_proxy_cover(item_id: str):
    import urllib.request
    url = cfg.absstats_base_url.rstrip("/") + f"/api/cover/{item_id}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=10) as r:
            body = r.read()
            ct = r.headers.get("Content-Type", "image/jpeg")
        return Response(content=body, media_type=ct)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/awards/api/avatar/{uid}")
def awards_proxy_avatar(uid: str):
    import urllib.request
    url = cfg.absstats_base_url.rstrip("/") + f"/api/avatar/{uid}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=3) as r:
            body = r.read()
            ct = r.headers.get("Content-Type", "image/jpeg")
        return Response(content=body, media_type=ct)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/awards/covers/")
def awards_covers_list():
    """Return a JSON listing of cover image files for the tier list page."""
    if not os.path.isdir(COVERS_DIR):
        return JSONResponse([])
    files = [
        {"name": f}
        for f in sorted(os.listdir(COVERS_DIR))
        if f.lower().endswith((".webp", ".png", ".jpg", ".jpeg"))
    ]
    return JSONResponse(files)

@app.get("/awards/covers/{cover_path:path}")
def awards_covers(cover_path: str):
    safe = cover_path.replace("\\", "/").lstrip("/")
    full_path = os.path.join(COVERS_DIR, safe)
    norm_covers = os.path.abspath(COVERS_DIR)
    norm_full = os.path.abspath(full_path)
    if not norm_full.startswith(norm_covers + os.sep) and norm_full != norm_covers:
        raise HTTPException(status_code=400, detail="Invalid cover path")
    if not os.path.exists(norm_full):
        raise HTTPException(status_code=404, detail=f"Cover not found: {safe}")
    return FileResponse(norm_full)


@app.get("/awards/api/icons")
@app.get("/api/icons")
def api_icons_list():
    """Return available icon file paths from ICONS_DIR for admin pickers."""
    exts = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
    icons = []

    if os.path.isdir(ICONS_DIR):
        for root, _dirs, files in os.walk(ICONS_DIR):
            for name in files:
                ext = os.path.splitext(name)[1].lower()
                if ext not in exts:
                    continue
                full = os.path.join(root, name)
                rel = os.path.relpath(full, ICONS_DIR).replace("\\", "/")
                icons.append(f"/icons/{rel}")

    icons.sort(key=lambda s: s.lower())
    return JSONResponse({"icons": icons, "total": len(icons)})
@app.get("/icons/{icon_path:path}")
def get_icon(icon_path: str):
    safe = icon_path.replace("\\", "/").lstrip("/")
    # Check if the path includes /icons/ prefix from the CSV and strip it for local lookup
    if safe.startswith("icons/"):
        safe = safe[6:]
        
    full_path = os.path.join(ICONS_DIR, safe)

    # prevent path traversal
    norm_icons = os.path.abspath(ICONS_DIR)
    norm_full = os.path.abspath(full_path)
    if not norm_full.startswith(norm_icons + os.sep) and norm_full != norm_icons:
        raise HTTPException(status_code=400, detail="Invalid icon path")

    if not os.path.exists(norm_full):
        raise HTTPException(status_code=404, detail=f"Icon not found: {safe}")

    return FileResponse(norm_full)


@app.get("/api/ui-config")
def api_ui_config_root():
    return api_ui_config()

@app.get("/api/users")
def api_users_root():
    return awards_proxy_users()

@app.get("/api/usernames")
def api_usernames_root():
    return awards_proxy_usernames()


@app.get("/awards/api/reading-history")
@app.get("/api/reading-history")
def api_reading_history():
    """
    Per-user book/series completion history, enriched with series membership,
    duration, rarity tier, and series-completion markers.
    Respects ALLOWED_USERS and progression scope filters.
    """
    import urllib.request as _req, json as _json

    base = cfg.absstats_base_url.rstrip("/")

    # client.get_completed() returns List[UserSnapshot] — iterate directly
    try:
        snapshots = client.get_completed(cfg.completed_endpoint)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Completions unavailable: {e}")

    # User map (uuid -> username)
    try:
        user_map = _json.loads(
            _req.urlopen(_req.Request(base + "/api/usernames"), timeout=10).read()
        ).get("map") or {}
    except Exception:
        user_map = {}

    # Sessions
    try:
        s_data = client.get_listening_sessions()
        all_sessions_map = {str(u.get("userId")): u.get("sessions") for u in s_data.get("users", [])}
    except Exception:
        all_sessions_map = {}

    # Series index — use cache, fall back to fresh fetch
    series_index = _SERIES_INDEX_CACHE["data"] or _fetch_abs_series_index()

    # Book metadata lookup: libraryItemId -> {duration, title}
    # Duration = actual book length from ABS, not listening time
    book_metadata: Dict[str, dict] = {}  # {libraryItemId: {duration: float(seconds), title: str}}

    # Fetch from all-items for accurate book duration and titles
    try:
        with _req.urlopen(_req.Request(base + "/api/all-items"), timeout=15) as _r:
            _items_data = _json.loads(_r.read())
        for _item in (_items_data.get("items") or []):
            _iid = _item.get("libraryItemId") or ""
            if _iid:
                # Try multiple possible duration field names (duration, durationMs, durationHours)
                _dur = _item.get("duration") or _item.get("durationMs") or 0
                _dur_sec = float(_dur) / 1000.0 if isinstance(_dur, (int, float)) else 0.0
                book_metadata[_iid] = {
                    "duration": _dur_sec,  # convert to seconds
                    "title": (_item.get("title") or "").strip(),
                }
    except Exception as e:
        print(f"[reading-history] all-items fetch failed: {e}")
        pass  # will fall back to series index data

    # Build book lookup: libraryItemId -> metadata
    book_lookup: Dict[str, dict] = {}
    series_book_sets: Dict[str, set] = {}  # series_name -> all libraryItemIds in series

    for s in series_index:
        sname = (s.get("seriesName") or "").strip()
        books = s.get("books") or []
        if not sname:
            continue
        bids: set = set()
        for b in books:
            bid = b.get("libraryItemId")
            if not bid:
                continue
            bids.add(bid)
            try:
                seq_f = float(b.get("seriesSequence") or 0)
            except Exception:
                seq_f = 0.0
            seq_str = (str(int(seq_f)) if seq_f > 0 and seq_f == int(seq_f) else str(seq_f)) if seq_f > 0 else ""
            # Use book_metadata for accurate duration; fall back to series index
            # Try multiple duration field names (duration, durationMs, durationHours)
            _dur_fallback = float(b.get("duration") or b.get("durationMs") or 0)
            if b.get("durationHours"):
                _dur_fallback = float(b.get("durationHours")) * 3600.0  # convert hours to seconds
            book_dur = book_metadata.get(bid, {}).get("duration", _dur_fallback)
            book_title = book_metadata.get(bid, {}).get("title") or (b.get("title") or "").strip()

            book_lookup[bid] = {
                "title":        book_title,
                "series_name":  sname,
                "sequence":     seq_f,
                "sequence_str": seq_str,
                "duration":     book_dur,
                "series_total": len(books),
                "cover":        _sanitize_cover_filename(sname) + ".jpg",
            }
        series_book_sets[sname] = bids

    result_users = []

    # Iterate over UserSnapshot objects returned by client.get_completed()
    for snap in snapshots:
        uid   = str(snap.user_id or "")
        uname = str(snap.username or user_map.get(uid, uid))
        if not uid or not _user_is_allowed(uname):
            continue

        # snap.finished_dates is already in seconds (client converts ms → s)
        # Chronicle shows ALL-TIME reading history, not filtered by XP scope
        finished_dates = {str(bid): int(ts) for bid, ts in (snap.finished_dates or {}).items()}
        finished_ids = set(finished_dates.keys())

        # Calculate total listening hours from user's sessions (all-time)
        # This matches the stats page calculation
        user_sessions = all_sessions_map.get(uid) or []
        user_listening_seconds = sum(int(s.get("timeListening") or 0) for s in user_sessions)
        user_listening_hours = user_listening_seconds / 3600.0

        # Build per-book entries
        books_out = []
        for bid, ts in finished_dates.items():
            info  = book_lookup.get(bid, {})
            title = info.get("title") or book_metadata.get(bid, {}).get("title") or bid
            sname = info.get("series_name") or ""
            dur   = info.get("duration") or book_metadata.get(bid, {}).get("duration", 0.0)
            books_out.append({
                "book_id":          bid,
                "title":            title,
                "series_name":      sname,
                "sequence":         info.get("sequence") or 0,
                "sequence_str":     info.get("sequence_str") or "",
                "duration_seconds": dur,
                "duration_hours":   round(dur / 3600, 1),
                "series_total":     info.get("series_total") or 0,
                "finished_at":      ts,
                "cover":            info.get("cover") or (_sanitize_cover_filename(sname or title) + ".jpg"),
            })

        books_out.sort(key=lambda x: x["finished_at"], reverse=True)

        # Determine completed series + their completion timestamp/metadata
        completed_series = []
        for sname, bids in series_book_sets.items():
            if not bids or not bids.issubset(finished_ids):
                continue
            # Completion timestamp = when the LAST book in the series was finished
            completed_ts = max((finished_dates.get(bid, 0) for bid in bids), default=0)
            # Sum actual book durations (not listening time) for series total
            total_dur = sum(book_lookup.get(bid, {}).get("duration") or book_metadata.get(bid, {}).get("duration", 0.0) for bid in bids)
            # Books sorted by sequence for display
            s_books = sorted(
                [book_lookup[bid] for bid in bids if bid in book_lookup],
                key=lambda b: float(b.get("sequence") or 9999),
            )
            completed_series.append({
                "series_name":  sname,
                "completed_at": completed_ts,
                "book_count":   len(bids),
                "total_hours":  round(total_dur / 3600, 1),
                "cover":        _sanitize_cover_filename(sname) + ".jpg",
                "books":        [b.get("title") for b in s_books],
            })

        completed_series.sort(key=lambda s: s["completed_at"], reverse=True)

        result_users.append({
            "user_id":         uid,
            "username":        uname,
            "books":           books_out,
            "completed_series": completed_series,
            "stats": {
                "total_books":      len(books_out),
                "total_hours":      round(user_listening_hours, 1),
                "series_completed": len(completed_series),
            },
        })

    return JSONResponse({"users": result_users, "user_map": user_map})


@app.get("/health")
def health():
    return JSONResponse({
        "status": "ok",
        "state_db_path": cfg.state_db_path,
    })


@app.get("/awards/api/ui-config")
def api_ui_config():
    """User display names (USER_ALIASES) for the frontend."""
    aliases = {}
    for pair in (os.getenv("USER_ALIASES", "") or "").split(","):
        pair = pair.strip()
        if ":" in pair:
            key, val = pair.split(":", 1)
            aliases[key.strip()] = val.strip()

    return JSONResponse({"aliases": aliases, "icons": {}})


# -----------------------------------------
# Section 5b: Release Radar Routes
# -----------------------------------------

@app.get("/radar")
def read_radar():
    return FileResponse(RADAR_PATH)


@app.get("/radar/api/series")
def radar_get_series():
    """Return all tracked series."""
    return JSONResponse({"series": store.get_tracked_series()})


@app.post("/radar/api/series")
async def radar_add_series(request: Request):
    """
    Add a series to track.
    Body: { series_asin, series_name, author, cover_url }
    """
    body = await request.json()
    series_asin = (body.get("series_asin") or "").strip()
    series_name = (body.get("series_name") or "").strip()
    author      = (body.get("author") or "").strip()
    cover_url   = (body.get("cover_url") or "").strip()

    if not series_asin or not series_name:
        raise HTTPException(status_code=400, detail="series_asin and series_name are required")

    row_id = store.add_tracked_series(series_name, series_asin, author, cover_url)
    return JSONResponse({"ok": True, "id": row_id})


@app.delete("/radar/api/series/{series_id}")
def radar_delete_series(series_id: int):
    # Look up the ASIN before deleting so we can ignore it
    series = store.get_tracked_series_by_id(series_id)
    if series:
        store.ignore_series(series["series_asin"])
    store.delete_tracked_series(series_id)
    return JSONResponse({"ok": True})


@app.get("/radar/api/releases")
def radar_get_releases(days_back: int = 90):
    """Return upcoming + recent releases."""
    releases = store.get_releases(days_back=days_back)
    return JSONResponse({"releases": releases})


@app.get("/radar/releases.ics")
def radar_ics():
    """Downloadable/subscribable ICS calendar feed."""
    releases = store.get_releases(days_back=30)
    ics_content = generate_ics(releases)
    return Response(
        content=ics_content,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": "inline; filename=audiobook-releases.ics"},
    )


@app.get("/radar/api/search")
def radar_search(q: str = ""):
    """Search Audible for series candidates to add."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="q parameter required")
    candidates = search_series_candidates(q.strip())
    return JSONResponse({"candidates": candidates})


@app.post("/radar/api/check")
def radar_manual_check():
    """Manually trigger a full series poll (runs synchronously, may be slow)."""
    found = radar_check_all(store)
    return JSONResponse({"ok": True, "new_releases": found})


@app.post("/radar/api/check/{series_asin}")
def radar_check_single_series(series_asin: str):
    """Check a single series for updates. Returns {status, next_book, last_checked, debug}."""
    import time

    series = None
    for s in store.get_tracked_series():
        if s["series_asin"] == series_asin:
            series = s
            break

    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    try:
        # Debug: capture what the API returns
        products = search_audible(series["series_name"])
        debug_info = {
            "query": series["series_name"],
            "api_returned": len(products),
            "candidates": [],
            "chosen": None,
        }

        # Find matching products
        for p in products:
            from .release_radar import _extract_series_info
            series_info = _extract_series_info(p)
            is_match = series_info and series_info.get("asin") == series_asin
            debug_info["candidates"].append({
                "title": p.get("title", "?"),
                "asin": p.get("asin", "?"),
                "series_asin": series_info.get("asin", "?") if series_info else "?",
                "sequence": series_info.get("sequence", "?") if series_info else "?",
                "release_date": p.get("release_date", "?"),
                "matches": is_match,
            })

        newest = find_newest_in_series(products, series_asin)
        store.touch_series_checked(series_asin)

        if newest is None:
            debug_info["reason"] = "No products matched series_asin"
            return JSONResponse({
                "status": "no_new_releases",
                "next_book": None,
                "last_checked": int(time.time()),
                "debug": debug_info,
            })

        release = _product_to_release(newest, series_asin, series["series_name"])
        is_new = store.upsert_release(**release)
        debug_info["chosen"] = {
            "title": release["title"],
            "sequence": release["sequence"],
            "release_date": release["release_date"],
            "is_new": is_new,
        }

        if is_new:
            store.update_series_last_seen(
                series_asin, release["asin"], release["title"],
                release["sequence"], release["release_date"]
            )

        return JSONResponse({
            "status": "found",
            "next_book": {
                "title": release["title"],
                "sequence": release["sequence"],
                "release_date": release["release_date"],
                "is_preorder": release["is_preorder"],
            },
            "last_checked": int(time.time()),
            "is_new": is_new,
            "debug": debug_info,
        })
    except Exception as e:
        import traceback
        return JSONResponse({
            "status": "error",
            "error": str(e),
            "last_checked": int(time.time()),
            "debug": {"traceback": traceback.format_exc()},
        })


@app.post("/radar/api/seed-from-abs")
def radar_seed_from_abs():
    """Pull all series from ABS and auto-add any not already tracked."""
    added, unmatched = seed_from_abs(store, cfg.absstats_base_url)
    return JSONResponse({"ok": True, "added": added, "unmatched": unmatched})


@app.get("/request")
def read_request():
    return FileResponse(REQUEST_PATH)


@app.get("/request/api/library-check")
def request_library_check(series_name: str = ""):
    """
    Check if a series already exists in the ABS library.
    Uses the cached series index (populated by background worker).
    Returns {"exists": bool, "matched_name": str|null}
    """
    import re as _re2

    q = series_name.strip()
    if not q:
        return JSONResponse({"exists": False, "matched_name": None})

    def _norm(s: str) -> str:
        s = s.lower()
        s = _re2.sub(r"[^a-z0-9 ]", " ", s)
        return _re2.sub(r"\s+", " ", s).strip()

    abs_series = _SERIES_INDEX_CACHE["data"] or _fetch_abs_series_index()
    qn = _norm(q)

    for s in abs_series:
        raw = (s.get("seriesName") or "").strip()
        if not raw:
            continue
        sn = _norm(raw)
        if qn == sn or qn in sn or sn in qn:
            return JSONResponse({"exists": True, "matched_name": raw})
        wq, ws = set(qn.split()), set(sn.split())
        shorter = min(len(wq), len(ws))
        if shorter > 0 and len(wq & ws) / shorter >= 0.8:
            return JSONResponse({"exists": True, "matched_name": raw})

    return JSONResponse({"exists": False, "matched_name": None})


@app.get("/api/request-config")
def api_request_config():
    return JSONResponse({"admin_email": "", "smtp_enabled": False})  # requests go to the admin Requests page


@app.post("/request/submit")
async def request_submit(request: Request):
    body = await request.json()
    series_name = (body.get("series_name") or "").strip()
    series_asin = (body.get("series_asin") or "").strip()
    author      = (body.get("author") or "").strip()
    cover_url   = (body.get("cover_url") or "").strip()
    book_title  = (body.get("book_title") or "").strip()
    note        = (body.get("note") or "").strip()

    if not series_name:
        return JSONResponse({"ok": False, "error": "Series name is required."}, status_code=400)

    req_id = store.add_request(
        series_name=series_name, series_asin=series_asin, author=author,
        cover_url=cover_url, book_title=book_title, note=note,
    )

    return JSONResponse({"ok": True, "id": req_id})


@app.get("/admin/api/requests")
def admin_get_requests():
    store.purge_old_fulfilled_requests()
    items = store.get_active_requests()
    return JSONResponse({"requests": items})


@app.post("/admin/api/requests/{request_id}/check")
def admin_check_request(request_id: int):
    ok = store.set_request_status(request_id, "fulfilled")
    if not ok:
        return JSONResponse({"ok": False, "error": "Not found"}, status_code=404)
    return JSONResponse({"ok": True})


@app.post("/admin/api/requests/{request_id}/uncheck")
def admin_uncheck_request(request_id: int):
    ok = store.set_request_status(request_id, "pending")
    if not ok:
        return JSONResponse({"ok": False, "error": "Not found"}, status_code=404)
    return JSONResponse({"ok": True})


@app.delete("/admin/api/requests/{request_id}")
def admin_delete_request(request_id: int):
    ok = store.delete_request(request_id)
    if not ok:
        return JSONResponse({"ok": False, "error": "Not found"}, status_code=404)
    return JSONResponse({"ok": True})


@app.post("/admin/api/requests/verify")
def admin_verify_requests():
    import re as _re3
    items = store.get_active_requests()
    pending = [r for r in items if r["status"] == "pending"]
    if not pending:
        return JSONResponse({"ok": True, "checked": 0, "fulfilled": 0})

    abs_series = _SERIES_INDEX_CACHE["data"] or _fetch_abs_series_index()

    all_items_cache = []
    try:
        base = cfg.absstats_base_url.rstrip("/")
        import urllib.request, json as _json2
        req = urllib.request.Request(base + "/api/all-items", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = _json2.loads(r.read())
        all_items_cache = payload.get("items") or payload if isinstance(payload, list) else []
    except Exception:
        pass

    def _norm(s: str) -> str:
        s = s.lower()
        s = _re3.sub(r"[^a-z0-9 ]", " ", s)
        return _re3.sub(r"\s+", " ", s).strip()

    def series_exists(name: str) -> bool:
        qn = _norm(name)
        for s in abs_series:
            raw = (s.get("seriesName") or "").strip()
            if not raw: continue
            sn = _norm(raw)
            if qn == sn or qn in sn or sn in qn:
                return True
            wq, ws = set(qn.split()), set(sn.split())
            shorter = min(len(wq), len(ws))
            if shorter > 0 and len(wq & ws) / shorter >= 0.8:
                return True
        return False

    def book_exists(title: str) -> bool:
        qn = _norm(title)
        for item in all_items_cache:
            t = _norm(item.get("title") or "")
            if qn == t or qn in t or t in qn:
                return True
        return False

    fulfilled_count = 0
    for r in pending:
        found = False
        if r.get("book_title"):
            found = book_exists(r["book_title"])
        else:
            found = series_exists(r["series_name"])
        if found:
            store.set_request_status(r["id"], "fulfilled")
            fulfilled_count += 1

    return JSONResponse({"ok": True, "checked": len(pending), "fulfilled": fulfilled_count})


@app.get("/radar/api/library-check")
def radar_library_check():
    """
    Cross-check released books against the ABS library.
    Returns {asin: bool|null} — true=in library, false=missing, null=unknown.
    """
    releases = store.get_releases(days_back=365)
    status = check_library_status(releases, cfg.absstats_base_url)
    return JSONResponse({"status": status})


# -----------------------------------------
# Section 6: Core Engine Logic (run_once)
# -----------------------------------------


