# -----------------------------------------
# game_api.py — HTTP API for The Listening Dungeon
# -----------------------------------------
# Routes (all JSON, under /api/game):
#   GET  /players            title screen: who can log in, dungeons waiting
#   POST /login              {username, pin}; first login sets the PIN
#   POST /logout
#   GET  /me                 the logged-in player's character and counts
#   PUT  /me/look            character builder result
#   PUT  /me/class           chosen class
#   GET  /me/dungeons        the player's shelf (?status=waiting|fallen|cleared)
#   POST /me/dungeons/{id}/revive   bring a Fallen book back (costs bookmarks)
#   POST /runs               start a dungeon run {item_id}
#   POST /runs/{id}/finish   report the result; the server decides rewards
#   GET  /me/bag             equipped items, bag, loot waiting for a decision
#   POST /me/items/{id}/equip | unequip | lock | scrap
#   POST /me/equip-best      wear the best gear for your class
#   POST /me/pending/{id}/take | scrap
#   GET  /bindery            permanent upgrades; POST /bindery/{key}, /bindery/bag
#   GET  /wardrobe           cosmetics; POST /wardrobe/{kind}/{key}/buy|wear|off
#   GET  /arena              the Arena ladder; POST /arena/duel/{username} starts a ghost duel
#   GET  /store              today's System Store, shared by everyone (unlocks after 10 clears)
#   POST /store/stock/{idx} | /store/crate | /store/supply/{key}
#   GET  /feed               party feed
#   GET  /bestiary           monsters this player has met (others stay hidden)
#   GET  /party              everyone's crawler; /party/{username} adds badges + Hall of Fame
#   GET  /practice           practice options; POST /practice {difficulty, tier} (no rewards)
#   POST /suggestions        a player's monster idea; GET /suggestions/mine
#   GET  /boss               the December boss panel; POST /boss/attack starts an attack,
#   POST /boss/attack/{id}/finish reports its damage; POST /boss/banners/{kind} raises a party-wide banner
#   /admin/...               Monster Workshop (behind the admin login, see main.py)
#
# Dungeons come from Audiobookshelf: every book a reader has finished becomes
# a waiting dungeon (game_store.sync_dungeons), refreshed at most every
# READERS_TTL seconds.
# -----------------------------------------

import os
import threading
import time
from typing import Callable, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from . import game_auth
from . import game_rules as R
from .gear_engine import load_loot_csv
from .game_store import CLASSES, GameError, GameStore

READERS_TTL = 120
CATALOG_TTL = 600


def boss_preview_offset(value: str, now: Optional[float] = None) -> int:
    """GAME_BOSS_PREVIEW_DATE=YYYY-MM-DD shifts the December boss's clock to
    that day (same time of day), so the event can be tried in Docker before
    December. Unset or bad: no shift. Never set it on the live server."""
    if not value:
        return 0
    try:
        day = time.mktime(time.strptime(value.strip()[:10], "%Y-%m-%d"))
    except ValueError:
        return 0
    now = now or time.time()
    lt = time.localtime(now)
    today = time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))
    return int(day - today)


def build_router(game: GameStore, state_store, abs_client, completed_endpoint: str,
                 user_allowed: Callable[[str], bool], achievement_defs: Optional[Callable[[], Dict]] = None) -> APIRouter:
    router = APIRouter(prefix="/api/game")
    cache_lock = threading.Lock()
    cache: Dict = {"readers": None, "readers_at": 0.0, "catalog": None, "catalog_at": 0.0, "loot": None,
                   "tags": None, "tags_at": 0.0}

    def loot_catalog() -> List[Dict]:
        """Droppable gear from loot.csv (system-only items excluded). Reloads
        when the file changes, so admin-generated gear drops right away."""
        path = next((p for p in ("/data/csv/loot.csv", "/app/csv/loot.csv", "csv/loot.csv") if os.path.exists(p)), None)
        mtime = os.path.getmtime(path) if path else 0
        if cache["loot"] is None or cache.get("loot_mtime") != mtime:
            items = load_loot_csv(path) if path else {}
            cache["loot"] = [i for i in items.values() if not i["item_id"].startswith("loot_000") and i["slot"] in R.SLOTS]
            cache["loot_mtime"] = mtime
        return cache["loot"]

    def guard(fn, *args):
        try:
            return fn(*args)
        except GameError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # ── Audiobookshelf data, cached ──────────────────────────────────────
    def catalog() -> Dict[str, Dict]:
        if cache["catalog"] is None or time.time() - cache["catalog_at"] > CATALOG_TTL:
            items = abs_client._get("/api/all-items").get("items") or []
            cache["catalog"] = {str(i.get("libraryItemId")): i for i in items if i.get("libraryItemId")}
            cache["catalog_at"] = time.time()
        return cache["catalog"]

    def genre_tags(item_id: str, series: str):
        """(series tags from the Recommendations data plus the book's own
        genres, the series description) for the dungeon look."""
        from .series_recs import normalize_series_key
        if cache["tags"] is None or time.time() - cache["tags_at"] > CATALOG_TTL:
            cache["tags"] = state_store.get_all_series_tags()
            cache["descs"] = state_store.get_all_series_descriptions()
            cache["tags_at"] = time.time()
        keys = [normalize_series_key(n) for n in ([name for _k, name, _q in R.parse_series(series)] or ([series] if series else []))]
        tags = [row["tag"] for k in keys for row in cache["tags"].get(k, [])]
        item = (cache["catalog"] or {}).get(item_id) or {}
        return tags + list(item.get("genres") or []), " ".join(cache["descs"].get(k, "") for k in keys)

    game.genre_tags = genre_tags
    game.boss_offset = boss_preview_offset(os.environ.get("GAME_BOSS_PREVIEW_DATE", ""))

    def readers(force: bool = False) -> List[Dict]:
        """Readers who can play: allowed ABS users with at least one finished
        book. Refreshing also adds new dungeons for newly finished books."""
        with cache_lock:
            fresh = cache["readers"] is not None and time.time() - cache["readers_at"] < READERS_TTL
            if fresh and not force:
                return cache["readers"]
            snaps = abs_client.get_completed(completed_endpoint)
            books_by_id = catalog()
            game.series_index, game.item_series = R.build_series_index(books_by_id.values())
            game.library_series = sorted({n for it in books_by_id.values() for _k, n, _q in R.parse_series(it.get("seriesName") or "")})
            out = []
            for snap in snaps:
                if not user_allowed(snap.username):
                    continue
                books = []
                for item_id in snap.finished_ids:
                    item = books_by_id.get(item_id)
                    if not item:
                        continue  # no longer in the library
                    books.append((item_id, item.get("title") or "Untitled", item.get("seriesName") or "",
                                  float(item.get("durationHours") or 0), int(snap.finished_dates.get(item_id, 0))))
                if not books:
                    continue
                game.sync_dungeons(snap.user_id, books)
                out.append({"user_id": snap.user_id, "username": snap.username})
            out.sort(key=lambda r: r["username"].lower())
            cache["readers"], cache["readers_at"] = out, time.time()
            return out

    def reader_by_name(username: str) -> Optional[Dict]:
        name = (username or "").strip().lower()
        return next((r for r in readers() if r["username"].lower() == name), None)

    def current_user_id(request: Request) -> str:
        user_id = game_auth.user_from_token(request.cookies.get(game_auth.COOKIE_NAME, ""))
        if not user_id or not game.get_player(user_id):
            raise HTTPException(status_code=401, detail="Log in to play.")
        return user_id

    def me_payload(user_id: str, with_notices: bool = False) -> Dict:
        tier = None
        if with_notices:
            game.settle_boss()  # the December boss's weekly badges and escape notices
            game.settle_arena_week(loot_catalog())  # last week's Arena prizes
            try:  # Tier List rewards: pays for series ranked since the last visit
                saved = state_store.get_tier_list(user_id) or {}
                tier = game.settle_tier_rewards(user_id, saved.get("query") or "")
            except Exception as e:
                print(f"[tier-rewards] {e}")
        player = game.get_player(user_id)
        equipped = game.equipped(user_id)
        return {
            **player,
            "gear": equipped,
            "stats": R.player_stats(player["cls"], player["level"], list(equipped.values()), player["upgrades"]) if player["cls"] else None,
            "bag_count": len(game.bag(user_id)),
            "pending_loot": len(game.pending_loot(user_id)),
            "dungeons": game.dungeon_counts(user_id),
            "store_unlock_at": R.STORE_UNLOCK_CLEARS,
            "needs_look": player["look"] is None,
            "needs_class": player["cls"] is None,
            "notices": game.take_notices(user_id) if with_notices else [],
            "active_run": _run_summary(game.active_run(user_id)),
            **({"tier": tier} if tier is not None else {}),  # only on full loads, so partial updates keep it
        }

    def _run_summary(run: Optional[Dict]) -> Optional[Dict]:
        if not run:
            return None
        prog = run.get("progress") or {}
        return {"run_id": run["run_id"], "item_id": run["item_id"], "title": run["title"], "floor": int(prog.get("floor", 0)) + 1}

    def is_https(request: Request) -> bool:
        return request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").lower() == "https"

    # ── routes ───────────────────────────────────────────────────────────
    @router.get("/players")
    def list_players():
        try:
            rs = readers()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Couldn't reach Audiobookshelf: {e}")
        crew = {m["user_id"]: m for m in game.party()}  # finished crawlers show on their button
        return {"players": [{
            "username": r["username"],
            "has_pin": state_store.get_pin(r["user_id"]) is not None,
            "dungeons_open": game.dungeon_counts(r["user_id"])["open"],
            "look": crew[r["user_id"]]["look"] if r["user_id"] in crew else None,
            "cls": crew[r["user_id"]]["cls"] if r["user_id"] in crew else None,
            "level": crew[r["user_id"]]["level"] if r["user_id"] in crew else None,
        } for r in rs]}

    @router.post("/login")
    async def login(request: Request):
        body = await request.json()
        reader = reader_by_name(str(body.get("username", "")))
        if not reader:
            raise HTTPException(status_code=404, detail="That reader isn't in the dungeon yet.")
        user_id, pin = reader["user_id"], str(body.get("pin", ""))
        if not game_auth.valid_pin(pin):
            raise HTTPException(status_code=400, detail="A PIN is exactly 4 digits.")
        wait = game_auth.lockout_remaining(user_id)
        if wait:
            raise HTTPException(status_code=429, detail=f"Too many wrong PINs. Try again in {(wait + 59) // 60} min.")

        first_time = state_store.get_pin(user_id) is None
        if first_time:
            state_store.set_pin(user_id, pin)
        elif not state_store.verify_pin(user_id, pin):
            game_auth.record_failure(user_id)
            raise HTTPException(status_code=401, detail="Wrong PIN.")
        game_auth.record_success(user_id)

        game.ensure_player(user_id, reader["username"])
        resp = JSONResponse({"first_time": first_time, "me": me_payload(user_id, with_notices=True)})
        resp.set_cookie(game_auth.COOKIE_NAME, game_auth.make_token(user_id), max_age=game_auth.SESSION_TTL_SECONDS,
                        httponly=True, samesite="lax", secure=is_https(request), path="/")
        return resp

    @router.post("/logout")
    def logout():
        resp = JSONResponse({"ok": True})
        resp.delete_cookie(game_auth.COOKIE_NAME, path="/")
        return resp

    @router.get("/me")
    def me(request: Request):
        return me_payload(current_user_id(request), with_notices=True)

    @router.get("/me/tier-status")
    def tier_status(request: Request):
        """For the Tier List page: who's logged in, and which finished series
        they still need to rank (paying for anything newly ranked)."""
        user_id = current_user_id(request)
        saved = state_store.get_tier_list(user_id) or {}
        status = guard(game.settle_tier_rewards, user_id, saved.get("query") or "")
        return {"user_id": user_id, "username": game.get_player(user_id)["username"], "has_list": bool(saved), **status}

    @router.post("/me/guide")
    def guide_seen(request: Request):
        game.mark_guide_seen(current_user_id(request))
        return {"ok": True}

    @router.put("/me/look")
    async def save_look(request: Request):
        user_id = current_user_id(request)
        body = await request.json()
        look = guard(game.set_look, user_id, body.get("look"))
        return {"look": look, "me": me_payload(user_id)}

    @router.put("/me/class")
    async def save_class(request: Request):
        user_id = current_user_id(request)
        body = await request.json()
        cls = body.get("cls")
        if cls not in CLASSES:
            raise HTTPException(status_code=400, detail="Unknown class.")
        guard(game.set_class, user_id, cls, bool(body.get("restart_run")))
        return {"cls": cls, "me": me_payload(user_id)}

    @router.get("/me/dungeons")
    def my_dungeons(request: Request, status: str = "waiting", sort: str = "new", limit: int = 60, offset: int = 0):
        user_id = current_user_id(request)
        try:
            readers()  # picks up newly finished books
        except Exception:
            pass  # show what we already have if ABS is briefly unreachable
        return {
            "counts": game.dungeon_counts(user_id),
            "dungeons": game.list_dungeons(user_id, status=status, sort=sort if sort in ("long", "random") else "new", limit=limit, offset=offset),
        }

    @router.post("/me/dungeons/{item_id}/revive")
    def revive(item_id: str, request: Request):
        user_id = current_user_id(request)
        cost = guard(game.revive, user_id, item_id)
        return {"spent": cost, "me": me_payload(user_id)}

    # ── dungeon runs ─────────────────────────────────────────────────────
    @router.post("/runs")
    async def start_run(request: Request):
        user_id = current_user_id(request)
        body = await request.json()
        return guard(game.start_run, user_id, str(body.get("item_id", "")))

    @router.get("/runs/active")
    def active_run(request: Request):
        run = game.active_run(current_user_id(request))
        if not run:
            raise HTTPException(status_code=404, detail="No dungeon in progress.")
        return run

    @router.put("/runs/{run_id}/progress")
    async def save_progress(run_id: str, request: Request):
        user_id = current_user_id(request)
        body = await request.json()
        guard(game.save_progress, user_id, run_id, body.get("progress") or {})
        return {"ok": True}

    @router.post("/runs/{run_id}/abandon")
    def abandon(run_id: str, request: Request):
        user_id = current_user_id(request)
        result = guard(game.abandon_run, user_id, run_id)
        return {"result": result, "me": me_payload(user_id)}

    @router.post("/runs/{run_id}/finish")
    async def finish_run(run_id: str, request: Request):
        user_id = current_user_id(request)
        body = await request.json()
        report = {k: body.get(k) for k in ("outcome", "floors", "kills", "elites")}
        try:
            report = {**report, **{k: int(report.get(k) or 0) for k in ("floors", "kills", "elites")}}
            used = body.get("supplies_used") or {}
            report["supplies_used"] = {k: min(9, int(v)) for k, v in used.items() if k in R.SUPPLIES} if isinstance(used, dict) else {}
            feats = body.get("feats") if isinstance(body.get("feats"), dict) else {}
            report["feats"] = {**{k: bool(feats.get(k)) for k in ("no_potion", "clutch", "flawless", "overcharge_boss")},
                               "loot_boxes": min(20, int(feats.get("loot_boxes") or 0)),
                               "pets": [str(b) for b in feats.get("pets")][:6] if isinstance(feats.get("pets"), list) else [],
                               "seen": {str(k)[:40]: int(v or 0) for k, v in list(feats.get("seen").items())[:40]} if isinstance(feats.get("seen"), dict) else {}}
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Bad run report.")
        result = guard(game.finish_run, user_id, run_id, report, loot_catalog())
        return {"result": result, "me": me_payload(user_id)}

    # ── inventory ────────────────────────────────────────────────────────
    @router.get("/me/bag")
    def my_bag(request: Request):
        user_id = current_user_id(request)
        p = game.get_player(user_id)
        equipped, bag = game.equipped(user_id), game.bag(user_id)
        better = R.better_than_worn(p["cls"], p["level"], p["upgrades"], equipped, bag) if p["cls"] else []
        return {"equipped": equipped, "bag": bag, "pending": game.pending_loot(user_id),
                "capacity": p["bag_capacity"], "scrap_value": R.SCRAP_VALUE, "better": better}

    @router.post("/me/equip-best")
    def equip_best(request: Request):
        user_id = current_user_id(request)
        before = me_payload(user_id)["stats"]
        put_on = guard(game.equip_best, user_id)
        return my_bag(request) | {"me": me_payload(user_id), "put_on": [it["name"] for it in put_on], "before": before}

    @router.post("/me/items/{item_id}/{action}")
    async def item_action(item_id: int, action: str, request: Request):
        user_id = current_user_id(request)
        if action == "equip":
            guard(game.equip, user_id, item_id)
        elif action == "unequip":
            guard(game.unequip, user_id, item_id)
        elif action == "lock":
            body = await request.json()
            guard(game.set_locked, user_id, item_id, bool(body.get("locked")))
        elif action == "scrap":
            guard(game.scrap, user_id, item_id)
        else:
            raise HTTPException(status_code=404, detail="Unknown action.")
        return my_bag(request) | {"me": me_payload(user_id)}

    @router.post("/me/pending/{pending_id}/{action}")
    def pending_action(pending_id: int, action: str, request: Request):
        user_id = current_user_id(request)
        if action == "take":
            guard(game.take_pending, user_id, pending_id)
        elif action == "scrap":
            guard(game.scrap_pending, user_id, pending_id)
        else:
            raise HTTPException(status_code=404, detail="Unknown action.")
        return my_bag(request) | {"me": me_payload(user_id)}

    # ── the System Store ─────────────────────────────────────────────────
    @router.get("/store")
    def store(request: Request):
        return game.store_view(current_user_id(request), loot_catalog())

    @router.post("/store/{kind}")
    @router.post("/store/{kind}/{key}")
    def store_buy(kind: str, request: Request, key: str = ""):
        user_id = current_user_id(request)
        if kind == "stock":
            try:
                idx = int(key)
            except ValueError:
                raise HTTPException(status_code=400, detail="Bad item.")
            got = guard(game.buy_stock, user_id, idx, loot_catalog())
        elif kind == "crate":
            got = guard(game.buy_crate, user_id, loot_catalog())
        elif kind == "supply":
            guard(game.buy_supply, user_id, key)
            got = None
        else:
            raise HTTPException(status_code=404, detail="Unknown purchase.")
        return {"got": got, "store": game.store_view(user_id, loot_catalog()), "me": me_payload(user_id)}

    # ── the Wardrobe (cosmetics) ─────────────────────────────────────────
    @router.get("/wardrobe")
    def wardrobe(request: Request):
        return game.wardrobe(current_user_id(request))

    @router.post("/wardrobe/{kind}/{key}/{action}")
    def wardrobe_action(kind: str, key: str, action: str, request: Request):
        user_id = current_user_id(request)
        if action == "buy":
            guard(game.buy_cosmetic, user_id, kind, key)
        elif action == "wear":
            guard(game.wear_cosmetic, user_id, kind, key)
        elif action == "off":
            guard(game.wear_cosmetic, user_id, kind, None)
        else:
            raise HTTPException(status_code=404, detail="Unknown action.")
        return {"wardrobe": game.wardrobe(user_id), "me": me_payload(user_id)}

    # ── the Bindery ──────────────────────────────────────────────────────
    @router.get("/bindery")
    def bindery(request: Request):
        user_id = current_user_id(request)
        p = game.get_player(user_id)
        ups = []
        for k, v in R.BINDERY.items():
            rank, top = p["upgrades"].get(k, 0), R.bindery_max(k)
            row = {"key": k, "name": v["name"], "text": v["text"], "rank": rank, "max": top,
                   "cost": R.bindery_cost(rank + 1, k) if rank < top else None}
            if rank < top and p["level"] < R.bindery_level(rank + 1, k):
                row["needs_level"] = R.bindery_level(rank + 1, k)
            if k == "battle_ready" and rank < top and rank >= R.CLASS_STATS.get(p["cls"] or "brawler")["energy"] - 1:
                row["full_for_class"] = True
            ups.append(row)
        bag_rank = p["bag_rank"]
        return {"bookmarks": p["bookmarks"], "upgrades": ups,
                "bag": {"rank": bag_rank, "max": len(R.BAG_UPGRADE_COSTS), "capacity": p["bag_capacity"],
                        "cost": R.BAG_UPGRADE_COSTS[bag_rank] if bag_rank < len(R.BAG_UPGRADE_COSTS) else None,
                        "next_capacity": R.bag_capacity(bag_rank + 1)}}

    @router.post("/bindery/{key}")
    def buy(key: str, request: Request):
        user_id = current_user_id(request)
        if key == "bag":
            guard(game.buy_bag_upgrade, user_id)
        else:
            guard(game.buy_upgrade, user_id, key)
        return bindery(request) | {"me": me_payload(user_id)}

    @router.get("/bestiary")
    def bestiary(request: Request):
        """The monsters this player has met (the rest stay silhouettes)."""
        return game.bestiary(current_user_id(request))

    @router.get("/admin/gallery")
    def monsters():
        """Every live monster with its stats (admin only: spoilers)."""
        from . import game_monsters as M
        pool = M.MONSTERS + game.custom_monsters(enabled_only=True)
        return {"tiers": M.TIERS, "modifiers": M.MODIFIERS,
                "monsters": [{**M.export(m), "tier": m["tier"], "style": m.get("style", "balanced")} for m in pool]}

    # ── monster ideas from players ───────────────────────────────────────
    @router.post("/suggestions")
    async def suggest(request: Request):
        user_id = current_user_id(request)
        body = await request.json()
        try:
            tier = int(body.get("tier") or 0)
        except (TypeError, ValueError):
            tier = 0
        got = guard(game.suggest_monster, user_id, body.get("name"), body.get("idea"), tier)
        return {"suggestion": got}

    # ── Monster Maker: players build monsters; the admin approves them ──
    @router.get("/maker")
    def maker_options(request: Request):
        current_user_id(request)
        try:
            readers()  # the library's series list, for the series picker
        except Exception:
            pass
        from . import game_monsters as M
        return {"tiers": M.TIERS, "roles": M.ROLE_BASE, "styles": M.STYLES, "moves": M.MOVES,
                "parts": {k: sorted(v) for k, v in M.PARTS.items()}, "enemy_scale": {L: R.enemy_scale(L) for L in (1, 10, 20, 30, 40, 50)},
                "library_series": game.library_series}

    @router.post("/maker/submit")
    async def maker_submit(request: Request):
        user_id = current_user_id(request)
        body = await request.json()
        return {"submitted": guard(game.submit_monster, user_id, body.get("monster") or {})}

    @router.get("/suggestions/mine")
    def my_suggestions(request: Request):
        return {"suggestions": [{**{k: s[k] for k in ("id", "name", "idea", "tier", "status", "created_at")}, "built": bool(s.get("monster"))}
                                for s in game.suggestions(current_user_id(request))]}

    # ── Monster Workshop (admin; the "admin" path is gated in main.py) ───
    @router.get("/admin/monsters")
    def workshop():
        from . import game_monsters as M
        return {"tiers": M.TIERS, "roles": M.ROLE_BASE, "styles": M.STYLES, "moves": M.MOVES, "modifiers": M.MODIFIERS,
                "parts": {k: sorted(v) for k, v in M.PARTS.items()}, "enemy_scale": {L: R.enemy_scale(L) for L in (1, 10, 20, 30, 40, 50)},
                "built_in": [{**M.export(m), "tier": m["tier"], "style": m.get("style", "balanced")} for m in M.MONSTERS],
                "custom": [{**m, **M.stats_for(m)} for m in game.custom_monsters()],
                "suggestions": game.suggestions()}

    @router.post("/admin/monsters")
    async def workshop_save(request: Request):
        body = await request.json()
        sug = body.get("suggestion_id")
        m = guard(game.save_custom_monster, body.get("monster") or {}, int(sug) if sug else None)
        return {"monster": m}

    @router.post("/admin/monsters/import")
    async def workshop_import(request: Request):
        """A JSON list of monsters (docs/MONSTER_PROMPT.md), or {monsters: [...]}."""
        body = await request.json()
        items = body.get("monsters") if isinstance(body, dict) else body
        enable = bool(body.get("enable", True)) if isinstance(body, dict) else True
        try:
            readers()  # the library's series list, to check each monster's series
        except Exception:
            pass
        results = guard(game.import_monsters, items, enable)
        return {"results": results, "added": sum(1 for r in results if r["ok"])}

    @router.post("/admin/monsters/repair-series")
    def workshop_repair_series():
        """Fix monsters whose series name doesn't match the library."""
        readers(force=True)  # refresh the library's series list first
        return game.repair_monster_series()

    @router.post("/admin/monsters/{monster_id}/enabled")
    async def workshop_enable(monster_id: str, request: Request):
        body = await request.json()
        guard(game.set_monster_enabled, monster_id, bool(body.get("enabled")))
        return {"ok": True}

    @router.delete("/admin/monsters/{monster_id}")
    def workshop_delete(monster_id: str):
        guard(game.delete_custom_monster, monster_id)
        return {"ok": True}

    @router.post("/admin/suggestions/{suggestion_id}/approve")
    def workshop_approve(suggestion_id: int):
        return {"monster": guard(game.approve_submission, suggestion_id)}

    @router.post("/admin/suggestions/{suggestion_id}")
    async def workshop_suggestion(suggestion_id: int, request: Request):
        body = await request.json()
        guard(game.set_suggestion_status, suggestion_id, str(body.get("status") or ""))
        return {"ok": True}

    @router.get("/feed")
    def feed(request: Request, limit: int = 20):
        current_user_id(request)
        return {"feed": game.list_feed(limit)}

    # ── the party ────────────────────────────────────────────────────────
    def public(member: Dict) -> Dict:
        return {k: v for k, v in member.items() if k != "user_id"}

    @router.get("/party")
    def party(request: Request):
        me_id = current_user_id(request)
        return {"members": [{**public(m), "you": m["user_id"] == me_id} for m in game.party()]}

    def hall_of_fame(user_id: str) -> List[Dict]:
        """The old journal achievements, frozen at the moment the game launched."""
        defs = achievement_defs() if achievement_defs else {}
        cutoff = game.launched_at
        out = []
        for a in state_store.get_all_awards():
            if a["user_id"] != user_id or a["awarded_at"] > cutoff:
                continue
            d = defs.get(a["achievement_id"]) or {}
            out.append({"id": a["achievement_id"], "name": d.get("achievement") or d.get("title") or a["achievement_id"],
                        "text": d.get("flavorText") or d.get("trigger") or "", "rarity": d.get("rarity") or "Common",
                        "icon": d.get("iconPath") or "", "points": d.get("points") or 0, "awarded_at": a["awarded_at"]})
        out.sort(key=lambda x: (-R.RARITIES.index(x["rarity"]) if x["rarity"] in R.RARITIES else 0, -x["awarded_at"]))
        return out

    @router.get("/party/{username}")
    def party_member(username: str, request: Request):
        me_id = current_user_id(request)
        member = next((m for m in game.party() if m["username"].lower() == username.lower()), None)
        if not member:
            raise HTTPException(status_code=404, detail="No crawler by that name.")
        return {**public(member), "you": member["user_id"] == me_id,
                "achievements": game.achievements(member["user_id"]), "hall_of_fame": hall_of_fame(member["user_id"])}

    # ── the December boss ────────────────────────────────────────────────
    @router.get("/boss")
    def boss(request: Request):
        return game.boss_state(current_user_id(request))

    @router.post("/boss/banners/{kind}")
    def boss_banner(kind: str, request: Request):
        user_id = current_user_id(request)
        guard(game.raise_banner, user_id, kind)
        return {"boss": game.boss_state(user_id), "me": me_payload(user_id)}

    @router.post("/boss/attack")
    def boss_attack(request: Request):
        return guard(game.start_boss_attack, current_user_id(request))

    @router.post("/boss/attack/{attack_id}/finish")
    async def boss_finish(attack_id: str, request: Request):
        user_id = current_user_id(request)
        body = await request.json()
        try:
            report = {"outcome": str(body.get("outcome") or ""), "damage": int(body.get("damage") or 0)}
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Bad attack report.")
        result = guard(game.finish_boss_attack, user_id, attack_id, report, loot_catalog())
        return {"result": result, "me": me_payload(user_id)}

    # ── the Arena: ghost duels and the ladder ────────────────────────────
    @router.get("/arena")
    def arena(request: Request):
        game.settle_arena_week(loot_catalog())
        return game.arena_view(current_user_id(request))

    @router.post("/arena/duel/{username}")
    def arena_duel(username: str, request: Request):
        game.settle_arena_week(loot_catalog())   # last week's ladder is paid before anyone moves it
        return guard(game.start_duel, current_user_id(request), username)

    @router.post("/arena/duel/{duel_id}/finish")
    async def arena_finish(duel_id: str, request: Request):
        user_id = current_user_id(request)
        body = await request.json()
        try:
            report = {"outcome": str(body.get("outcome") or ""), "my_pct": float(body.get("my_pct") or 0), "ghost_pct": float(body.get("ghost_pct") or 0)}
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Bad duel report.")
        result = guard(game.finish_duel, user_id, duel_id, report)
        return {"result": result, "me": me_payload(user_id)}

    # ── practice: a random dungeon that pays nothing ─────────────────────
    @router.get("/practice")
    def practice_options(request: Request):
        from . import game_monsters as M
        p = game.get_player(current_user_id(request))
        return {"difficulties": [{"key": k, "name": v["name"]} for k, v in R.PRACTICE_DIFFICULTY.items()],
                "themes": [{"tier": t, "name": n} for t, n in M.TIERS.items()],
                "your_tier": min(R.enemy_tier(p["level"]), max(M.TIERS))}

    @router.post("/practice")
    async def practice(request: Request):
        user_id = current_user_id(request)
        body = await request.json()
        try:
            tier = int(body.get("tier") or 1)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Bad theme.")
        return guard(game.practice_config, user_id, str(body.get("difficulty") or "normal"), tier)

    return router
