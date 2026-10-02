# -----------------------------------------
# game_store.py — The Listening Dungeon: persistent game state
# -----------------------------------------
# One character per player (keyed by ABS user id), their items, one dungeon
# per finished book, dungeon runs, notices, and a party feed. Lives in the
# same SQLite file as the rest of the app; every table is prefixed game_ and
# created or migrated on demand.
#
# Numbers (costs, rewards, stats) come from game_rules.py.
# Design reference: docs/BOOK_DUNGEON_DESIGN.md
# -----------------------------------------

import json
import random
import re
from contextlib import contextmanager
import secrets
import sqlite3
import time
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from . import game_achievements as ACH
from . import game_monsters
from . import game_rules as R

GAME_SCHEMA = """
CREATE TABLE IF NOT EXISTS game_meta (
  key   TEXT NOT NULL PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS game_players (
  user_id       TEXT NOT NULL PRIMARY KEY,
  username      TEXT NOT NULL,
  look_json     TEXT,
  cls           TEXT,
  level         INTEGER NOT NULL DEFAULT 1,
  xp            INTEGER NOT NULL DEFAULT 0,
  bookmarks     INTEGER NOT NULL DEFAULT 0,
  upgrades_json TEXT NOT NULL DEFAULT '{}',
  created_at    INTEGER NOT NULL,
  updated_at    INTEGER NOT NULL
);

-- One row per (player, finished book). status: waiting | fallen | cleared
CREATE TABLE IF NOT EXISTS game_dungeons (
  user_id     TEXT NOT NULL,
  item_id     TEXT NOT NULL,
  title       TEXT NOT NULL,
  series      TEXT NOT NULL DEFAULT '',
  hours       REAL NOT NULL DEFAULT 0,
  finished_at INTEGER NOT NULL DEFAULT 0,
  status      TEXT NOT NULL DEFAULT 'waiting',
  attempts    INTEGER NOT NULL DEFAULT 0,
  cleared_at  INTEGER,
  PRIMARY KEY (user_id, item_id)
);
CREATE INDEX IF NOT EXISTS idx_game_dungeons_status ON game_dungeons(user_id, status);

-- Every owned item. equipped_slot is NULL while it sits in the bag.
CREATE TABLE IF NOT EXISTS game_items (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id       TEXT NOT NULL,
  item_json     TEXT NOT NULL,
  locked        INTEGER NOT NULL DEFAULT 0,
  equipped_slot TEXT,
  acquired_at   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_game_items_user ON game_items(user_id);

-- Loot that didn't fit in a full bag, waiting for the player to decide.
CREATE TABLE IF NOT EXISTS game_pending_loot (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    TEXT NOT NULL,
  item_json  TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS game_runs (
  id            TEXT NOT NULL PRIMARY KEY,
  user_id       TEXT NOT NULL,
  item_id       TEXT NOT NULL,
  started_at    INTEGER NOT NULL,
  finished_at   INTEGER,
  outcome       TEXT,
  snapshot_json TEXT NOT NULL,
  result_json   TEXT
);
CREATE INDEX IF NOT EXISTS idx_game_runs_user ON game_runs(user_id, finished_at);

-- Retired 2026-10-01 (the store went daily and shared: game_store_sold). Kept for history.
-- The Arena: ghost duels, the ladder (rank 1 = top) and each month's champion.
CREATE TABLE IF NOT EXISTS game_duels (
  id          TEXT PRIMARY KEY,
  challenger  TEXT NOT NULL,
  defender    TEXT NOT NULL,
  day         TEXT NOT NULL,
  started_at  INTEGER NOT NULL,
  finished_at INTEGER,
  won         INTEGER,              -- 1: the challenger won, 0: the ghost held
  snapshot_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS game_duels_challenger_day ON game_duels(challenger, day);
CREATE TABLE IF NOT EXISTS game_ladder (
  user_id TEXT PRIMARY KEY,
  rank    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS game_arena_weeks (
  week     TEXT PRIMARY KEY,         -- the Monday it started (week_key)
  champion TEXT,                     -- user_id who got the Epic, if anyone
  climber  TEXT,                     -- user_id who got the Rare, if anyone
  settled_at INTEGER
);
CREATE TABLE IF NOT EXISTS game_arena_months (
  month    TEXT PRIMARY KEY,         -- YYYY-MM
  champion TEXT,                     -- user_id, set once the month is over
  settled_at INTEGER
);
-- The day's store gear sold so far: each piece once, to whoever buys it first.
CREATE TABLE IF NOT EXISTS game_store_sold (
  day     TEXT NOT NULL,
  idx     INTEGER NOT NULL,
  user_id TEXT NOT NULL,
  bought_at INTEGER NOT NULL,
  PRIMARY KEY (day, idx)
);
CREATE TABLE IF NOT EXISTS game_store_purchases (
  user_id TEXT NOT NULL,
  week    TEXT NOT NULL,
  idx     INTEGER NOT NULL,
  bought_at INTEGER NOT NULL,
  PRIMARY KEY (user_id, week, idx)
);

-- Messages shown once at next login (welcome chest, book finished, ...).
CREATE TABLE IF NOT EXISTS game_notices (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id      TEXT NOT NULL,
  kind         TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at   INTEGER NOT NULL,
  seen         INTEGER NOT NULL DEFAULT 0
);

-- Game badges (app/game_achievements.py), earned once each.
CREATE TABLE IF NOT EXISTS game_achievements (
  user_id   TEXT NOT NULL,
  key       TEXT NOT NULL,
  earned_at INTEGER NOT NULL,
  PRIMARY KEY (user_id, key)
);

-- Monster Workshop: admin-made monsters, and players' monster ideas.
CREATE TABLE IF NOT EXISTS game_custom_monsters (
  id            TEXT NOT NULL PRIMARY KEY,
  data_json     TEXT NOT NULL,
  enabled       INTEGER NOT NULL DEFAULT 0,
  suggestion_id INTEGER,
  created_at    INTEGER NOT NULL,
  updated_at    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS game_monster_suggestions (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id    TEXT NOT NULL,
  username   TEXT NOT NULL,
  name       TEXT NOT NULL,
  idea       TEXT NOT NULL,
  tier       INTEGER NOT NULL DEFAULT 0,
  status     TEXT NOT NULL DEFAULT 'new',
  monster_id TEXT,
  created_at INTEGER NOT NULL
);

-- Series catch-up rewards: one row per (player, series). `books` is the
-- series length when they were last rewarded (finale Epic once, then Rare
-- "Caught Up" chests only when new books have arrived since).
CREATE TABLE IF NOT EXISTS game_series_rewards (
  user_id    TEXT NOT NULL,
  series_key TEXT NOT NULL,
  books      INTEGER NOT NULL,
  finale_at  INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  PRIMARY KEY (user_id, series_key)
);

-- The Bestiary: monsters each player has fought in real dungeons.
CREATE TABLE IF NOT EXISTS game_bestiary (
  user_id    TEXT NOT NULL,
  monster_id TEXT NOT NULL,
  first_seen INTEGER NOT NULL,
  defeated   INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (user_id, monster_id)
);

-- The December boss: one row per year (docs/BOOK_DUNGEON_DESIGN.md §7).
-- status: active | defeated | escaped. settled_json: weeks whose top damage
-- badge was given, and when January's Null was cleansed.
CREATE TABLE IF NOT EXISTS game_boss (
  year          INTEGER NOT NULL PRIMARY KEY,
  max_hp        INTEGER NOT NULL,
  hp            INTEGER NOT NULL,
  status        TEXT NOT NULL DEFAULT 'active',
  returning_pct INTEGER,
  killer        TEXT,
  ended_at      INTEGER,
  settled_json  TEXT NOT NULL DEFAULT '{}',
  created_at    INTEGER NOT NULL
);
-- Tier List rewards: one row per (player, series) they've been paid for
-- ranking. tier/book_at are as of the last payment (for re-rank rewards).
CREATE TABLE IF NOT EXISTS game_tier_rewards (
  user_id     TEXT NOT NULL,
  series_norm TEXT NOT NULL,
  series_name TEXT NOT NULL,
  tier        TEXT NOT NULL,
  kind        TEXT NOT NULL,
  book_at     INTEGER NOT NULL,
  rewarded_at INTEGER NOT NULL,
  PRIMARY KEY (user_id, series_norm)
);

-- One row per boss attack. slot: the week's Monday, or "YYYY-xmas".
CREATE TABLE IF NOT EXISTS game_boss_attacks (
  id            TEXT NOT NULL PRIMARY KEY,
  year          INTEGER NOT NULL,
  user_id       TEXT NOT NULL,
  username      TEXT NOT NULL,
  slot          TEXT NOT NULL,
  week          TEXT NOT NULL,
  started_at    INTEGER NOT NULL,
  finished_at   INTEGER,
  damage        INTEGER NOT NULL DEFAULT 0,
  outcome       TEXT,
  snapshot_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_game_boss_attacks ON game_boss_attacks(year, user_id);
-- Boss banners raised for a week (party-wide; game_rules.BANNERS).
CREATE TABLE IF NOT EXISTS game_boss_banners (
  year      INTEGER NOT NULL,
  week      TEXT NOT NULL,
  kind      TEXT NOT NULL,
  user_id   TEXT NOT NULL,
  username  TEXT NOT NULL,
  raised_at INTEGER NOT NULL,
  PRIMARY KEY (year, week, kind)
);

CREATE TABLE IF NOT EXISTS game_feed (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at   INTEGER NOT NULL,
  user_id      TEXT NOT NULL,
  username     TEXT NOT NULL,
  kind         TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}'
);
"""

# Columns added after the first version of a table: (table, column, definition)
MIGRATIONS = [
    ("game_players", "look_changes", "INTEGER NOT NULL DEFAULT 0"),
    ("game_players", "class_changes", "INTEGER NOT NULL DEFAULT 0"),
    ("game_players", "bag_rank", "INTEGER NOT NULL DEFAULT 0"),
    ("game_dungeons", "bonus_paid", "INTEGER NOT NULL DEFAULT 0"),
    ("game_runs", "progress_json", "TEXT"),
    ("game_players", "supplies_json", "TEXT NOT NULL DEFAULT '{}'"),
    ("game_players", "stats_json", "TEXT NOT NULL DEFAULT '{}'"),
    ("game_players", "cosmetics_json", "TEXT NOT NULL DEFAULT '{}'"),
    ("game_monster_suggestions", "monster_json", "TEXT"),   # a player-built monster (Monster Maker)
]
PETS_BY_CLASS = {"beastmaster": ("beasts", {"wolf", "hawk", "bear"}), "necromancer": ("minions", {"skeleton", "ghoul", "wraith"})}
MAX_PROGRESS_BYTES = 8000

# ── Character options. Must match static/js/crawler-art.js ─────────────────
ANCESTRIES = {"human": 5, "dwarf": 4, "elf": 4, "darkelf": 4, "orc": 4}  # value = skin swatch count
NO_BEARD = {"elf", "darkelf"}
HAIR_STYLES = {"bald", "short", "long", "mohawk", "bun", "braid"}
HAIR_COLOR_COUNT = 8
BEARDS = {"none", "stubble", "full", "braided"}
FACES = {"determined", "cheerful", "grumpy", "glowing"}
ACCENT_COUNT = 8
CLASSES = set(R.CLASS_STATS)
DUNGEON_STATUSES = ("waiting", "fallen", "cleared")
OUTCOMES = {"exit", "boss", "dead"}
BOSS_OUTCOMES = {"fell", "time", "kill"}

xp_to_next = R.xp_to_next


class GameError(Exception):
    """A request the rules don't allow (not enough bookmarks, bag full, ...).
    The message is shown to the player."""


def clean_look(raw) -> Dict:
    """Validate a look from the character builder. Raises ValueError on
    anything outside the known options, so only drawable looks are stored."""
    if not isinstance(raw, dict):
        raise ValueError("look must be an object")

    def choice(key, allowed):
        v = raw.get(key)
        if v not in allowed:
            raise ValueError(f"invalid {key}")
        return v

    def index(key, count):
        v = raw.get(key)
        if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v < count:
            raise ValueError(f"invalid {key}")
        return v

    ancestry = choice("ancestry", ANCESTRIES)
    look = {
        "ancestry": ancestry,
        "skin": index("skin", ANCESTRIES[ancestry]),
        "hair": choice("hair", HAIR_STYLES),
        "hairColor": index("hairColor", HAIR_COLOR_COUNT),
        "beard": choice("beard", BEARDS),
        "face": choice("face", FACES),
        "accent": index("accent", ACCENT_COUNT),
    }
    if ancestry in NO_BEARD:
        look["beard"] = "none"  # elves can't grow beards
    return look


class GameStore:
    def __init__(self, db_path: str, now: Optional[int] = None):
        self.db_path = db_path
        # The library's series (R.build_series_index), refreshed by game_api.
        self.series_index: Dict[str, Dict] = {}
        self.library_series: List[str] = []   # every series name in the library (incl. #0 / novella-only)
        self.item_series: Dict[str, List[tuple]] = {}
        # (item_id, series) -> (genre tags, series description) for the
        # dungeon look; set by game_api.
        self.genre_tags: Optional[Callable[[str, str], Tuple[List[str], str]]] = None
        # Seconds added to the clock for the December boss only, so the event
        # can be previewed in Docker (GAME_BOSS_PREVIEW_DATE, see game_api).
        self.boss_offset = 0
        with self._conn() as c:
            c.executescript(GAME_SCHEMA)
            for table, col, definition in MIGRATIONS:
                cols = {r[1] for r in c.execute(f"PRAGMA table_info({table})")}
                if col not in cols:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
            c.execute("UPDATE game_dungeons SET status='fallen' WHERE status='attempted'")  # old name
            # Item levels (2026-09-30): stamp gear owned before them at the owner's
            # current level, keeping its stats exactly (nobody's gear gets weaker).
            levels = {r[0]: r[1] for r in c.execute("SELECT user_id, level FROM game_players")}
            for table in ("game_items", "game_pending_loot"):
                for r in c.execute(f"SELECT id, user_id, item_json FROM {table}").fetchall():
                    it = json.loads(r[2])
                    if it.get("ilvl"):
                        continue
                    lv = levels.get(r[1], 1)
                    m = R.item_level_mult(lv)
                    it.update({"ilvl": lv, **{f"base_{k}": round(it.get(k, 0) / m, 2) for k in ("atk", "def", "hp")}})
                    c.execute(f"UPDATE {table} SET item_json=? WHERE id=?", (json.dumps(it), r[0]))
            # Battle Ready lost its 5th rank (2026-09-30): refund it.
            for r in c.execute("SELECT user_id, upgrades_json FROM game_players").fetchall():
                ups = json.loads(r[1] or "{}")
                if ups.get("battle_ready", 0) > R.bindery_max("battle_ready"):
                    refund = sum(R.bindery_cost(n, "battle_ready") if n <= R.bindery_max("battle_ready") else 75
                                 for n in range(R.bindery_max("battle_ready") + 1, ups["battle_ready"] + 1))
                    ups["battle_ready"] = R.bindery_max("battle_ready")
                    c.execute("UPDATE game_players SET upgrades_json=?, bookmarks=bookmarks+? WHERE user_id=?", (json.dumps(ups), refund, r[0]))
                    self._notice(c, r[0], "forge_refund", {"bookmarks": refund, "name": "Battle Ready"})
            # The moment the game first ran on this database. Only books
            # finished after it pay the book-finished bonus.
            c.execute("INSERT OR IGNORE INTO game_meta(key, value) VALUES('launched_at', ?)", (str(int(now or time.time())),))

    @contextmanager
    def _conn(self):
        """A connection that commits on success, rolls back on error, and always closes."""
        c = sqlite3.connect(self.db_path, timeout=10)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    @property
    def launched_at(self) -> int:
        with self._conn() as c:
            return int(c.execute("SELECT value FROM game_meta WHERE key='launched_at'").fetchone()[0])

    # ── notices + feed ───────────────────────────────────────────────────
    @staticmethod
    def _notice(c, user_id: str, kind: str, payload: Dict) -> None:
        c.execute("INSERT INTO game_notices(user_id, kind, payload_json, created_at) VALUES(?,?,?,?)",
                  (user_id, kind, json.dumps(payload), int(time.time())))

    def take_notices(self, user_id: str) -> List[Dict]:
        """Unseen notices, oldest first; marks them seen."""
        with self._conn() as c:
            rows = c.execute("SELECT * FROM game_notices WHERE user_id=? AND seen=0 ORDER BY id", (user_id,)).fetchall()
            c.execute("UPDATE game_notices SET seen=1 WHERE user_id=? AND seen=0", (user_id,))
        return [{"kind": r["kind"], **json.loads(r["payload_json"])} for r in rows]

    @staticmethod
    def _feed(c, user_id: str, username: str, kind: str, payload: Dict) -> None:
        c.execute("INSERT INTO game_feed(created_at, user_id, username, kind, payload_json) VALUES(?,?,?,?,?)",
                  (int(time.time()), user_id, username, kind, json.dumps(payload)))

    def add_feed(self, user_id: str, username: str, kind: str, payload: Optional[Dict] = None) -> None:
        with self._conn() as c:
            self._feed(c, user_id, username, kind, payload or {})

    def list_feed(self, limit: int = 20) -> List[Dict]:
        with self._conn() as c:
            rows = c.execute("SELECT f.*, p.look_json, p.cls, p.cosmetics_json FROM game_feed f LEFT JOIN game_players p ON p.user_id=f.user_id "
                             "ORDER BY f.id DESC LIMIT ?", (max(1, min(int(limit), 100)),)).fetchall()
        return [{"id": r["id"], "created_at": r["created_at"], "username": r["username"], "kind": r["kind"],
                 "payload": json.loads(r["payload_json"] or "{}"), "cls": r["cls"],
                 "look": self._dressed(r["look_json"], self._worn(r["cosmetics_json"]))} for r in rows]

    # ── lifetime counters + badges ───────────────────────────────────────
    @staticmethod
    def _bump(c, user_id: str, add: Optional[Dict[str, int]] = None, sets: Optional[Dict[str, Iterable[str]]] = None) -> None:
        """Add to a player's lifetime counters (stats_json) and sets."""
        row = c.execute("SELECT stats_json FROM game_players WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return
        st = json.loads(row[0] or "{}")
        for k, n in (add or {}).items():
            if n:
                st[k] = st.get(k, 0) + int(n)
        for k, vals in (sets or {}).items():
            vals = set(vals or ())
            if vals - set(st.get(k, [])):
                st[k] = sorted(set(st.get(k, [])) | vals)
        c.execute("UPDATE game_players SET stats_json=? WHERE user_id=?", (json.dumps(st), user_id))

    def _check_badges(self, c, user_id: str) -> List[Dict]:
        """Award any newly earned badges (notice + feed). Returns them."""
        p = c.execute("SELECT username, level, stats_json FROM game_players WHERE user_id=?", (user_id,)).fetchone()
        if not p:
            return []
        dungeons = [dict(r) for r in c.execute("SELECT series, status FROM game_dungeons WHERE user_id=?", (user_id,))]
        ctx = {"stats": json.loads(p["stats_json"] or "{}"), "level": p["level"], "dungeons": dungeons,
               "clears": sum(1 for d in dungeons if d["status"] == "cleared"),
               "bestiary": c.execute("SELECT COUNT(*) FROM game_bestiary WHERE user_id=?", (user_id,)).fetchone()[0],
               "tier_ranked": c.execute("SELECT COUNT(*) FROM game_tier_rewards WHERE user_id=?", (user_id,)).fetchone()[0]}
        have = {r[0] for r in c.execute("SELECT key FROM game_achievements WHERE user_id=?", (user_id,))}
        new = [k for k in ACH.earned(ctx) if k not in have]
        now = int(time.time())
        for k in new:
            b = ACH.view(k)
            if c.execute("INSERT OR IGNORE INTO game_achievements(user_id, key, earned_at) VALUES(?,?,?)", (user_id, k, now)).rowcount:
                c.execute("UPDATE game_players SET bookmarks=bookmarks+? WHERE user_id=?", (R.BADGE_BOOKMARKS, user_id))
            self._notice(c, user_id, "achievement", {"key": k, "name": b["name"], "text": b["text"], "bookmarks": R.BADGE_BOOKMARKS})
        if new:  # one feed line per batch, so a big run doesn't flood the feed
            names = [ACH.view(k)["name"] for k in new]
            text = f"earned the badge {names[0]}." if len(names) == 1 else f"earned {len(names)} badges: {', '.join(names)}."
            self._feed(c, user_id, p["username"], "achievement", {"text": text, "keys": new})
        return [{**ACH.view(k), "bookmarks": R.BADGE_BOOKMARKS} for k in new]

    def achievements(self, user_id: str) -> List[Dict]:
        """Every badge, with when this player earned it (or None). The scar
        badge names each December the Regent escaped and how close it got."""
        with self._conn() as c:
            got = {r["key"]: r["earned_at"] for r in c.execute("SELECT key, earned_at FROM game_achievements WHERE user_id=?", (user_id,))}
            row = c.execute("SELECT stats_json FROM game_players WHERE user_id=?", (user_id,)).fetchone()
        out = [{**ACH.view(k), "earned_at": got.get(k)} for k, *_ in ACH.BADGES]
        scars = sorted(json.loads(row[0] or "{}").get("scars", []) if row else [])
        if scars:
            marks = "; ".join(f"{y} (Regent at {pct}%)" for y, pct in (s.split(":") for s in scars))
            for b in out:
                if b["key"] == "boss_scar":
                    b["text"] = f"The Null Regent escaped: {marks}."
        return out

    # ── cosmetics ────────────────────────────────────────────────────────
    @staticmethod
    def _worn(cosmetics_json: Optional[str]) -> Dict[str, str]:
        """What a player is wearing, dropping anything no longer sold."""
        worn = (json.loads(cosmetics_json or "{}").get("worn") or {})
        return {k: v for k, v in worn.items() if k in R.COSMETICS and v in R.COSMETICS[k]}

    @staticmethod
    def _dressed(look_json: Optional[str], worn: Dict[str, str]) -> Optional[Dict]:
        """The builder look plus a worn cape, which crawler-art.js draws."""
        if not look_json:
            return None
        look = json.loads(look_json)
        return {**look, "cape": worn["cape"]} if worn.get("cape") else look

    def wardrobe(self, user_id: str) -> Dict:
        with self._conn() as c:
            row = c.execute("SELECT cosmetics_json, bookmarks, cls FROM game_players WHERE user_id=?", (user_id,)).fetchone()
        cos = json.loads(row["cosmetics_json"] or "{}")
        owned = set(cos.get("owned") or [])
        worn = self._worn(row["cosmetics_json"])
        return {"bookmarks": row["bookmarks"], "cls": row["cls"], "kinds": R.COSMETIC_KINDS, "worn": worn,
                "items": {kind: [{"key": k, **v, "owned": f"{kind}:{k}" in owned, "worn": worn.get(kind) == k} for k, v in items.items()]
                          for kind, items in R.COSMETICS.items()}}

    def buy_cosmetic(self, user_id: str, kind: str, key: str) -> None:
        """Buy a cosmetic and put it on."""
        item = R.COSMETICS.get(kind, {}).get(key)
        if not item:
            raise ValueError("unknown cosmetic")
        with self._conn() as c:
            cos = json.loads(c.execute("SELECT cosmetics_json FROM game_players WHERE user_id=?", (user_id,)).fetchone()[0] or "{}")
            owned = set(cos.get("owned") or [])
            if f"{kind}:{key}" in owned:
                raise GameError("You already own that.")
            self._spend(c, user_id, item["cost"])
            owned.add(f"{kind}:{key}")
            cos["owned"] = sorted(owned)
            cos.setdefault("worn", {})[kind] = key
            c.execute("UPDATE game_players SET cosmetics_json=? WHERE user_id=?", (json.dumps(cos), user_id))

    def wear_cosmetic(self, user_id: str, kind: str, key: Optional[str]) -> None:
        """Put on an owned cosmetic, or take that kind off (key=None)."""
        if kind not in R.COSMETICS:
            raise ValueError("unknown cosmetic")
        with self._conn() as c:
            cos = json.loads(c.execute("SELECT cosmetics_json FROM game_players WHERE user_id=?", (user_id,)).fetchone()[0] or "{}")
            worn = cos.setdefault("worn", {})
            if key is None:
                worn.pop(kind, None)
            elif f"{kind}:{key}" not in (cos.get("owned") or []):
                raise GameError("Buy it first.")
            else:
                worn[kind] = key
            c.execute("UPDATE game_players SET cosmetics_json=? WHERE user_id=?", (json.dumps(cos), user_id))

    @staticmethod
    def _title(worn: Dict[str, str]) -> Optional[str]:
        return R.COSMETICS["title"][worn["title"]]["name"] if worn.get("title") else None

    @staticmethod
    def _pet_skin(p: Dict) -> Optional[str]:
        """The worn pet skin, if it fits the current class."""
        skin = p["worn"].get("pet")
        return skin if skin and R.COSMETICS["pet"][skin]["cls"] == p["cls"] else None

    # ── players ──────────────────────────────────────────────────────────
    def get_player(self, user_id: str) -> Optional[Dict]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM game_players WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return None
        upgrades = json.loads(row["upgrades_json"] or "{}")
        worn = self._worn(row["cosmetics_json"])
        return {
            "user_id": row["user_id"],
            "username": row["username"],
            "look": self._dressed(row["look_json"], worn),
            "worn": worn,
            "title": self._title(worn),
            "cls": row["cls"],
            "level": row["level"],
            "xp": row["xp"],
            "xp_next": R.xp_to_next(row["level"]),
            "bookmarks": row["bookmarks"],
            "upgrades": upgrades,
            "bag_rank": row["bag_rank"],
            "bag_capacity": R.bag_capacity(row["bag_rank"]),
            "supplies": json.loads(row["supplies_json"] or "{}"),
            "look_change_cost": R.LOOK_CHANGE_COST if row["look_json"] else 0,
            "class_change_cost": R.CLASS_CHANGE_COST if row["cls"] else 0,
            "guide_seen": "guide" in json.loads(row["stats_json"] or "{}").get("flags", []),
        }

    def mark_guide_seen(self, user_id: str) -> None:
        """The first-time guide was closed; don't show it again (any device)."""
        with self._conn() as c:
            self._bump(c, user_id, sets={"flags": ["guide"]})

    def ensure_player(self, user_id: str, username: str) -> Dict:
        """Create the character on first login (with the Welcome Chest)."""
        now = int(time.time())
        with self._conn() as c:
            cur = c.execute("INSERT OR IGNORE INTO game_players(user_id, username, bookmarks, created_at, updated_at) "
                            "VALUES(?,?,?,?,?)", (user_id, username, R.WELCOME_CHEST, now, now))
            if cur.rowcount:
                self._notice(c, user_id, "welcome", {"bookmarks": R.WELCOME_CHEST})
            else:
                c.execute("UPDATE game_players SET username=? WHERE user_id=?", (username, user_id))
        self.pay_book_bonuses(user_id)
        return self.get_player(user_id)

    def _spend(self, c, user_id: str, amount: int) -> None:
        if amount <= 0:
            return
        cur = c.execute("UPDATE game_players SET bookmarks = bookmarks - ? WHERE user_id=? AND bookmarks >= ?",
                        (amount, user_id, amount))
        if not cur.rowcount:
            raise GameError(f"You need {amount} bookmarks for that.")
        self._bump(c, user_id, {"spent": amount})
        self._check_badges(c, user_id)

    def set_look(self, user_id: str, look: Dict) -> Dict:
        look = clean_look(look)
        with self._conn() as c:
            row = c.execute("SELECT look_json FROM game_players WHERE user_id=?", (user_id,)).fetchone()
            if row["look_json"] and json.loads(row["look_json"]) == look:
                return look  # nothing changed, nothing charged
            if row["look_json"]:
                self._spend(c, user_id, R.LOOK_CHANGE_COST)
            c.execute("UPDATE game_players SET look_json=?, look_changes=look_changes+?, updated_at=? WHERE user_id=?",
                      (json.dumps(look), 1 if row["look_json"] else 0, int(time.time()), user_id))
        return look

    def set_class(self, user_id: str, cls: str, restart_run: bool = False) -> None:
        """Pick or change class. A dungeon in progress was started with the old
        class, so changing needs restart_run=True: that run is dropped with no
        penalty (the book stays waiting, packed supplies come back)."""
        if cls not in CLASSES:
            raise ValueError("invalid class")
        with self._conn() as c:
            row = c.execute("SELECT cls FROM game_players WHERE user_id=?", (user_id,)).fetchone()
            if row["cls"] == cls:
                return
            run = c.execute("SELECT * FROM game_runs WHERE user_id=? AND finished_at IS NULL ORDER BY started_at DESC LIMIT 1", (user_id,)).fetchone()
            if run and not restart_run:
                raise GameError(f"You're in the middle of {json.loads(run['snapshot_json']).get('title', 'a dungeon')}. Changing class restarts it from floor 1.")
            if row["cls"]:
                self._spend(c, user_id, R.CLASS_CHANGE_COST)
            if run:
                snap = json.loads(run["snapshot_json"])
                self._return_supplies(c, user_id, snap.get("supplies") or {}, {})
                c.execute("UPDATE game_runs SET finished_at=?, outcome='restarted' WHERE id=?", (int(time.time()), run["id"]))
                c.execute("UPDATE game_dungeons SET attempts=MAX(0, attempts-1) WHERE user_id=? AND item_id=?", (user_id, run["item_id"]))
            c.execute("UPDATE game_players SET cls=?, class_changes=class_changes+?, updated_at=? WHERE user_id=?",
                      (cls, 1 if row["cls"] else 0, int(time.time()), user_id))

    def buy_upgrade(self, user_id: str, key: str) -> Dict:
        if key not in R.BINDERY:
            raise ValueError("unknown upgrade")
        with self._conn() as c:
            ups = json.loads(c.execute("SELECT upgrades_json FROM game_players WHERE user_id=?", (user_id,)).fetchone()[0] or "{}")
            rank = ups.get(key, 0)
            if rank >= R.bindery_max(key):
                raise GameError("That upgrade is already maxed.")
            need = R.bindery_level(rank + 1, key)
            lvl = c.execute("SELECT level FROM game_players WHERE user_id=?", (user_id,)).fetchone()[0]
            if lvl < need:
                raise GameError(f"The next rank unlocks at level {need}.")
            if key == "battle_ready":
                cls = c.execute("SELECT cls FROM game_players WHERE user_id=?", (user_id,)).fetchone()[0]
                if rank >= R.CLASS_STATS.get(cls or "brawler")["energy"] - 1:
                    raise GameError("Battle Ready is maxed for your class (it stops one short of a full bar).")
            self._spend(c, user_id, R.bindery_cost(rank + 1, key))
            ups[key] = rank + 1
            c.execute("UPDATE game_players SET upgrades_json=? WHERE user_id=?", (json.dumps(ups), user_id))
        return ups

    def buy_bag_upgrade(self, user_id: str) -> int:
        with self._conn() as c:
            rank = c.execute("SELECT bag_rank FROM game_players WHERE user_id=?", (user_id,)).fetchone()[0]
            if rank >= len(R.BAG_UPGRADE_COSTS):
                raise GameError("Your bag is already as big as it gets.")
            self._spend(c, user_id, R.BAG_UPGRADE_COSTS[rank])
            c.execute("UPDATE game_players SET bag_rank=? WHERE user_id=?", (rank + 1, user_id))
        return R.bag_capacity(rank + 1)

    # ── items ────────────────────────────────────────────────────────────
    @staticmethod
    def _item_row(r) -> Dict:
        return {**json.loads(r["item_json"]), "id": r["id"], "locked": bool(r["locked"]), "equipped_slot": r["equipped_slot"]}

    def equipped(self, user_id: str) -> Dict[str, Dict]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM game_items WHERE user_id=? AND equipped_slot IS NOT NULL", (user_id,)).fetchall()
        return {r["equipped_slot"]: self._item_row(r) for r in rows}

    def bag(self, user_id: str) -> List[Dict]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM game_items WHERE user_id=? AND equipped_slot IS NULL ORDER BY id DESC", (user_id,)).fetchall()
        return [self._item_row(r) for r in rows]

    def pending_loot(self, user_id: str) -> List[Dict]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM game_pending_loot WHERE user_id=? ORDER BY id", (user_id,)).fetchall()
        return [{**json.loads(r["item_json"]), "pending_id": r["id"]} for r in rows]

    @staticmethod
    def _bag_count(c, user_id: str) -> int:
        return c.execute("SELECT COUNT(*) FROM game_items WHERE user_id=? AND equipped_slot IS NULL", (user_id,)).fetchone()[0]

    @staticmethod
    def _capacity(c, user_id: str) -> int:
        return R.bag_capacity(c.execute("SELECT bag_rank FROM game_players WHERE user_id=?", (user_id,)).fetchone()[0])

    def _give_item(self, c, user_id: str, item: Dict) -> str:
        """Equip into an empty slot, else bag, else pending. Returns where it went.
        The item is stamped with the player's level first (in place)."""
        now = int(time.time())
        lvl = c.execute("SELECT level FROM game_players WHERE user_id=?", (user_id,)).fetchone()
        R.stamp_item(item, lvl[0] if lvl else 1)
        if item.get("rarity") == "Legendary":
            self._bump(c, user_id, sets={"flags": ["legendary"]})
            self._check_badges(c, user_id)
        slot_taken = c.execute("SELECT 1 FROM game_items WHERE user_id=? AND equipped_slot=?", (user_id, item["slot"])).fetchone()
        if not slot_taken:
            c.execute("INSERT INTO game_items(user_id, item_json, equipped_slot, acquired_at) VALUES(?,?,?,?)",
                      (user_id, json.dumps(item), item["slot"], now))
            return "equipped"
        if self._bag_count(c, user_id) < self._capacity(c, user_id):
            c.execute("INSERT INTO game_items(user_id, item_json, acquired_at) VALUES(?,?,?)", (user_id, json.dumps(item), now))
            return "bag"
        c.execute("INSERT INTO game_pending_loot(user_id, item_json, created_at) VALUES(?,?,?)", (user_id, json.dumps(item), now))
        return "pending"

    def _owned(self, c, user_id: str, item_id: int):
        row = c.execute("SELECT * FROM game_items WHERE id=? AND user_id=?", (item_id, user_id)).fetchone()
        if not row:
            raise GameError("That item isn't yours.")
        return row

    def equip(self, user_id: str, item_id: int) -> None:
        """Wear a bag item; whatever was in that slot moves into its bag spot."""
        with self._conn() as c:
            row = self._owned(c, user_id, item_id)
            slot = json.loads(row["item_json"])["slot"]
            c.execute("UPDATE game_items SET equipped_slot=NULL WHERE user_id=? AND equipped_slot=?", (user_id, slot))
            c.execute("UPDATE game_items SET equipped_slot=? WHERE id=?", (slot, item_id))

    def equip_best(self, user_id: str) -> List[Dict]:
        """Wear the best gear for the crawler's class. Returns the items put on."""
        player = self.get_player(user_id)
        if not player or not player["cls"]:
            raise GameError("Pick a class first.")
        items = list(self.equipped(user_id).values()) + self.bag(user_id)
        pick = R.best_loadout(player["cls"], player["level"], player["upgrades"], items)
        put_on = [it for it in pick.values() if it and not it.get("equipped_slot")]
        with self._conn() as c:
            for it in put_on:  # a swap: the old piece goes to the bag, so the bag never overfills
                c.execute("UPDATE game_items SET equipped_slot=NULL WHERE user_id=? AND equipped_slot=?", (user_id, it["slot"]))
                c.execute("UPDATE game_items SET equipped_slot=? WHERE id=?", (it["slot"], it["id"]))
        return put_on

    def unequip(self, user_id: str, item_id: int) -> None:
        with self._conn() as c:
            self._owned(c, user_id, item_id)
            if self._bag_count(c, user_id) >= self._capacity(c, user_id):
                raise GameError("Your bag is full.")
            c.execute("UPDATE game_items SET equipped_slot=NULL WHERE id=?", (item_id,))

    def set_locked(self, user_id: str, item_id: int, locked: bool) -> None:
        with self._conn() as c:
            self._owned(c, user_id, item_id)
            c.execute("UPDATE game_items SET locked=? WHERE id=?", (1 if locked else 0, item_id))

    def scrap(self, user_id: str, item_id: int) -> int:
        with self._conn() as c:
            row = self._owned(c, user_id, item_id)
            if row["locked"]:
                raise GameError("That item is locked. Unlock it first.")
            if row["equipped_slot"]:
                raise GameError("Take it off before scrapping it.")
            value = R.SCRAP_VALUE.get(json.loads(row["item_json"])["rarity"], 0)
            c.execute("DELETE FROM game_items WHERE id=?", (item_id,))
            c.execute("UPDATE game_players SET bookmarks=bookmarks+? WHERE user_id=?", (value, user_id))
        return value

    def take_pending(self, user_id: str, pending_id: int) -> str:
        with self._conn() as c:
            row = c.execute("SELECT * FROM game_pending_loot WHERE id=? AND user_id=?", (pending_id, user_id)).fetchone()
            if not row:
                raise GameError("That loot is gone.")
            if self._bag_count(c, user_id) >= self._capacity(c, user_id):
                raise GameError("Your bag is still full. Scrap something first.")
            c.execute("INSERT INTO game_items(user_id, item_json, acquired_at) VALUES(?,?,?)", (user_id, row["item_json"], int(time.time())))
            c.execute("DELETE FROM game_pending_loot WHERE id=?", (pending_id,))
        return "bag"

    def scrap_pending(self, user_id: str, pending_id: int) -> int:
        with self._conn() as c:
            row = c.execute("SELECT * FROM game_pending_loot WHERE id=? AND user_id=?", (pending_id, user_id)).fetchone()
            if not row:
                raise GameError("That loot is gone.")
            value = R.SCRAP_VALUE.get(json.loads(row["item_json"])["rarity"], 0)
            c.execute("DELETE FROM game_pending_loot WHERE id=?", (pending_id,))
            c.execute("UPDATE game_players SET bookmarks=bookmarks+? WHERE user_id=?", (value, user_id))
        return value

    # ── the Arena: ghost duels and the ladder ───────────────────────────
    def _ladder(self, c) -> List[str]:
        """Everyone with a finished crawler, rank 1 first. Newcomers join at
        the bottom (highest level first); gaps close up."""
        crawlers = [r[0] for r in c.execute("SELECT user_id FROM game_players WHERE look_json IS NOT NULL AND cls IS NOT NULL "
                                             "ORDER BY level DESC, xp DESC, username")]
        ranked = [r[0] for r in c.execute("SELECT user_id FROM game_ladder ORDER BY rank")]
        order = [u for u in ranked if u in set(crawlers)] + [u for u in crawlers if u not in set(ranked)]
        if order != ranked:
            c.execute("DELETE FROM game_ladder")
            c.executemany("INSERT INTO game_ladder(user_id, rank) VALUES(?,?)", [(u, i + 1) for i, u in enumerate(order)])
        return order

    def _settle_arena_month(self, c, now: float) -> None:
        """The first Arena visit in a new month crowns last month's #1."""
        import time as _t
        month = _t.strftime("%Y-%m", _t.localtime(now))
        if c.execute("SELECT 1 FROM game_arena_months WHERE month=?", (month,)).fetchone():
            return
        prev = c.execute("SELECT month FROM game_arena_months WHERE champion IS NULL AND month < ? ORDER BY month DESC LIMIT 1", (month,)).fetchone()
        c.execute("INSERT INTO game_arena_months(month) VALUES(?)", (month,))
        ladder = self._ladder(c)
        if not prev or not ladder:
            return
        champ = ladder[0]
        c.execute("UPDATE game_arena_months SET champion=?, settled_at=? WHERE month=?", (champ, int(now), prev[0]))
        name = c.execute("SELECT username FROM game_players WHERE user_id=?", (champ,)).fetchone()[0]
        self._bump(c, champ, sets={"flags": ["arena_champion"]})
        self._feed(c, champ, name, "arena", {"text": f"finished {_t.strftime('%B', _t.strptime(prev[0], '%Y-%m'))} at #1 in the Arena. Arena Champion!"})
        self._check_badges(c, champ)

    def settle_arena_week(self, catalog: List[Dict], now: Optional[float] = None, rng: Optional[random.Random] = None) -> None:
        """After Sunday midnight, pay last week's Arena prizes (once). Called
        before any duel starts and whenever someone opens the game, so the
        ladder it reads is the one the week ended with."""
        now = now or time.time()
        week = R.week_key(now)
        with self._conn() as c:
            if c.execute("SELECT 1 FROM game_arena_weeks WHERE week=?", (week,)).fetchone():
                return
            prev = c.execute("SELECT week FROM game_arena_weeks WHERE settled_at IS NULL AND week < ? ORDER BY week DESC LIMIT 1", (week,)).fetchone()
            c.execute("INSERT INTO game_arena_weeks(week) VALUES(?)", (week,))
            if not prev:
                return
            start = R.week_start(R.week_start(now) - 3 * 86400)   # last Monday
            wins: Dict[str, int] = {}
            started = set()
            for ch, won in c.execute("SELECT challenger, won FROM game_duels WHERE finished_at IS NOT NULL AND started_at >= ? AND started_at < ?",
                                     (start, R.week_start(now))):   # an abandoned duel doesn't count as fighting
                started.add(ch)
                if won:
                    wins[ch] = wins.get(ch, 0) + 1
            ladder = self._ladder(c)
            champ = ladder[0] if ladder and ladder[0] in started else None
            rest = sorted(((n, u) for u, n in wins.items() if u != champ), reverse=True)
            climber = rest[0][1] if rest and (len(rest) == 1 or rest[0][0] > rest[1][0]) else None   # a tie: nobody
            rng = rng or random.Random()
            for uid, rarity, kind in ((champ, R.ARENA_WEEK_CHAMPION_RARITY, "champion"), (climber, R.ARENA_WEEK_CLIMBER_RARITY, "climber")):
                if not uid:
                    continue
                raw = R.roll_item(catalog, R.upgrade_rarity(rarity, rng), "", rng) if catalog else None
                item = R.item_view(raw) if raw else None
                if item:
                    self._give_item(c, uid, item)   # stamped with their level
                name = c.execute("SELECT username FROM game_players WHERE user_id=?", (uid,)).fetchone()[0]
                self._notice(c, uid, "arena_week", {"prize": kind, "wins": wins.get(uid, 0),
                                                    "item": {"name": item["name"], "rarity": item["rarity"]} if item else None})
                got = f" and won {'an' if item and item['rarity'][0] in 'AEIOU' else 'a'} {item['rarity']} {item['name']}" if item else ""
                self._feed(c, uid, name, "arena", {"text": (f"held #1 in the Arena this week{got}." if kind == "champion"
                                                            else f"won the most duels this week ({wins[uid]}){got}.")})
            c.execute("UPDATE game_arena_weeks SET champion=?, climber=?, settled_at=? WHERE week=?", (champ, climber, int(now), prev[0]))

    def _duel_record(self, c) -> Dict[str, Dict[str, int]]:
        rec: Dict[str, Dict[str, int]] = {}
        for ch, de, won in c.execute("SELECT challenger, defender, won FROM game_duels WHERE finished_at IS NOT NULL"):
            for uid, w in ((ch, won), (de, 1 - won)):
                r = rec.setdefault(uid, {"wins": 0, "losses": 0})
                r["wins" if w else "losses"] += 1
        return rec

    def arena_view(self, user_id: str, now: Optional[float] = None) -> Dict:
        now = now or time.time()
        with self._conn() as c:
            self._settle_arena_month(c, now)
            ladder = self._ladder(c)
            rec = self._duel_record(c)
            used = c.execute("SELECT COUNT(*) FROM game_duels WHERE challenger=? AND day=?", (user_id, R.day_key(now))).fetchone()[0]
            names = {r[0]: r[1] for r in c.execute("SELECT user_id, username FROM game_players")}
            recent = [{"challenger": names.get(r["challenger"], "?"), "defender": names.get(r["defender"], "?"), "won": bool(r["won"]),
                       "at": r["finished_at"]} for r in c.execute(
                "SELECT * FROM game_duels WHERE finished_at IS NOT NULL ORDER BY finished_at DESC LIMIT 10")]
            champs = [{"month": r[0], "username": names.get(r[1], "?")} for r in c.execute(
                "SELECT month, champion FROM game_arena_months WHERE champion IS NOT NULL ORDER BY month DESC LIMIT 6")]
            last = c.execute("SELECT champion, climber FROM game_arena_weeks WHERE settled_at IS NOT NULL ORDER BY week DESC LIMIT 1").fetchone()
            last_week = {"champion": names.get(last[0]) if last and last[0] else None, "climber": names.get(last[1]) if last and last[1] else None}
            week_wins = {r[0]: r[1] for r in c.execute("SELECT challenger, COUNT(*) FROM game_duels WHERE won=1 AND started_at >= ? GROUP BY challenger",
                                                       (R.week_start(now),))}
            fought = c.execute("SELECT 1 FROM game_duels WHERE challenger=? AND finished_at IS NOT NULL AND started_at >= ?",
                               (user_id, R.week_start(now))).fetchone() is not None
        party = {m["user_id"]: m for m in self.party()}
        rows = []
        for i, uid in enumerate(ladder):
            m = party.get(uid)
            if not m:
                continue
            rows.append({"rank": i + 1, "username": m["username"], "cls": m["cls"], "level": m["level"], "look": m["look"], "worn": m["worn"],
                         "title": m["title"], "stats": m["stats"], **rec.get(uid, {"wins": 0, "losses": 0}), "you": uid == user_id,
                         "week_wins": week_wins.get(uid, 0)})
        return {"ladder": rows, "challenges_left": max(0, R.DUEL_DAILY_LIMIT - used), "daily_limit": R.DUEL_DAILY_LIMIT,
                "win_bookmarks": R.DUEL_WIN_BOOKMARKS, "recent": recent, "champions": champs, "last_week": last_week,
                "you_fought_this_week": fought, "week_ends_at": R.week_start(now) + 7 * 86400,
                "resets_at": R.next_day_start(now)}

    def start_duel(self, user_id: str, opponent: str, now: Optional[float] = None) -> Dict:
        now = int(now or time.time())
        p = self.get_player(user_id)
        if not p or not p["look"] or not p["cls"]:
            raise GameError("Finish building your character first.")
        foe = next((m for m in self.party() if m["username"].lower() == (opponent or "").lower()), None)
        if not foe:
            raise GameError("No crawler by that name.")
        if foe["user_id"] == user_id:
            raise GameError("You can't duel your own ghost. It knows all your moves.")
        day = R.day_key(now)
        with self._conn() as c:
            if c.execute("SELECT COUNT(*) FROM game_duels WHERE challenger=? AND day=?", (user_id, day)).fetchone()[0] >= R.DUEL_DAILY_LIMIT:
                raise GameError(f"You've used all {R.DUEL_DAILY_LIMIT} challenges today. More at midnight.")
            ladder = self._ladder(c)
            fp = c.execute("SELECT upgrades_json FROM game_players WHERE user_id=?", (foe["user_id"],)).fetchone()
            ups = json.loads(fp[0] or "{}")
            moves, names = R.GHOST_MOVES.get(foe["cls"], R.GHOST_MOVES["brawler"])
            duel_id = secrets.token_hex(12)
            cfg = self.run_config(user_id)
            snap = {**cfg, "monsters": None, "duel": True, "title": "The Arena", "theme": "dungeon", "turns": R.DUEL_TURNS,
                    "ghost": {"username": foe["username"], "cls": foe["cls"], "level": foe["level"], "look": foe["look"],
                              "rank": ladder.index(foe["user_id"]) + 1, "your_rank": ladder.index(user_id) + 1,
                              "stats": R.player_stats(foe["cls"], foe["level"], list(foe["gear"].values()), ups),
                              "moves": moves, "move_names": names}}
            c.execute("INSERT INTO game_duels(id, challenger, defender, day, started_at, snapshot_json) VALUES(?,?,?,?,?,?)",
                      (duel_id, user_id, foe["user_id"], day, now, json.dumps(snap)))
        return {"duel_id": duel_id, **snap}

    def finish_duel(self, user_id: str, duel_id: str, report: Dict, now: Optional[float] = None) -> Dict:
        now = int(now or time.time())
        outcome = report.get("outcome")
        if outcome not in ("win", "lose", "time"):
            raise ValueError("invalid outcome")
        with self._conn() as c:
            d = c.execute("SELECT * FROM game_duels WHERE id=? AND challenger=?", (duel_id, user_id)).fetchone()
            if not d:
                raise GameError("That duel doesn't exist.")
            if d["finished_at"]:
                raise GameError("That duel is already over.")
            if now - d["started_at"] < R.DUEL_MIN_SECONDS:
                raise GameError("That was suspiciously fast.")
            won = R.duel_winner(outcome, float(report.get("my_pct") or 0), float(report.get("ghost_pct") or 0))
            c.execute("UPDATE game_duels SET finished_at=?, won=? WHERE id=?", (now, 1 if won else 0, duel_id))
            ladder = self._ladder(c)
            me_rank, foe_rank = ladder.index(user_id) + 1, ladder.index(d["defender"]) + 1 if d["defender"] in ladder else None
            moved = bool(won and foe_rank and me_rank > foe_rank)
            if moved:   # swap places
                c.execute("UPDATE game_ladder SET rank=? WHERE user_id=?", (foe_rank, user_id))
                c.execute("UPDATE game_ladder SET rank=? WHERE user_id=?", (me_rank, d["defender"]))
            names = {r[0]: (r[1], r[2]) for r in c.execute("SELECT user_id, username, level FROM game_players WHERE user_id IN (?,?)",
                                                           (user_id, d["defender"]))}
            me_name, me_lvl = names[user_id]
            foe_name, foe_lvl = names.get(d["defender"], ("someone", 0))
            new_rank = foe_rank if moved else me_rank
            if won:
                c.execute("UPDATE game_players SET bookmarks=bookmarks+? WHERE user_id=?", (R.DUEL_WIN_BOOKMARKS, user_id))
                flags = (["giant_slayer"] if foe_lvl >= me_lvl + R.GIANT_SLAYER_LEVELS else []) + (["arena_top"] if new_rank == 1 else [])
                self._bump(c, user_id, {"duel_wins": 1}, sets={"flags": flags})
            else:
                c.execute("UPDATE game_players SET bookmarks=bookmarks+? WHERE user_id=?", (R.DUEL_DEFEND_BOOKMARKS, d["defender"]))
            self._notice(c, d["defender"], "duel", {"challenger": me_name, "ghost_won": not won,
                                                     "bookmarks": 0 if won else R.DUEL_DEFEND_BOOKMARKS,
                                                     "rank": (me_rank if moved else foe_rank), "moved": moved})
            text = (f"beat {foe_name.upper()}'s ghost in the Arena" + (f" and took #{new_rank} on the ladder." if moved else ".")) if won \
                else f"challenged {foe_name.upper()}'s ghost in the Arena and lost."
            self._feed(c, user_id, me_name, "arena", {"text": text})
            badges = self._check_badges(c, user_id)
            self._check_badges(c, d["defender"])
        return {"won": won, "opponent": foe_name, "bookmarks": R.DUEL_WIN_BOOKMARKS if won else 0, "rank_before": me_rank,
                "rank_after": new_rank, "moved": moved, "badges": badges}

    # ── the System Store ─────────────────────────────────────────────────
    def clears(self, user_id: str) -> int:
        with self._conn() as c:
            return c.execute("SELECT COUNT(*) FROM game_dungeons WHERE user_id=? AND status='cleared'", (user_id,)).fetchone()[0]

    def _require_store(self, user_id: str) -> None:
        if self.clears(user_id) < R.STORE_UNLOCK_CLEARS:
            raise GameError(f"The System Store opens after {R.STORE_UNLOCK_CLEARS} cleared dungeons.")

    def store_view(self, user_id: str, catalog: List[Dict], now: Optional[float] = None) -> Dict:
        now = now or time.time()
        key = R.day_key(now)
        with self._conn() as c:
            sold = {r["idx"]: {"by": r["username"] or "someone", "you": r["user_id"] == user_id} for r in c.execute(
                "SELECT s.idx, s.user_id, p.username FROM game_store_sold s LEFT JOIN game_players p ON p.user_id = s.user_id WHERE s.day=?", (key,))}
        p = self.get_player(user_id)
        clears = self.clears(user_id)
        stock = [{**s, "item": R.stamp_item(dict(s["item"]), p["level"]), "sold": sold.get(s["idx"])} for s in R.store_stock(key, catalog)]
        if p["cls"]:   # ▲ on pieces that beat what you wear, judged like the bag's Best gear
            better = set(R.better_than_worn(p["cls"], p["level"], p["upgrades"], self.equipped(user_id),
                                            [{**o["item"], "id": o["idx"]} for o in stock]))
            for o in stock:
                o["upgrade"] = o["idx"] in better
        return {
            "unlocked": clears >= R.STORE_UNLOCK_CLEARS, "clears": clears, "unlock_at": R.STORE_UNLOCK_CLEARS,
            "bookmarks": p["bookmarks"], "restocks_at": R.next_day_start(now),
            "stock": stock,
            "crate_cost": R.CRATE_COST,
            "supplies": [{"key": k, **v, "owned": p["supplies"].get(k, 0)} for k, v in R.SUPPLIES.items()],
            "carry": sum(p["supplies"].values()), "carry_max": R.SUPPLY_CARRY,
        }

    def buy_stock(self, user_id: str, idx: int, catalog: List[Dict], now: Optional[float] = None) -> Dict:
        self._require_store(user_id)
        now = now or time.time()
        key = R.day_key(now)
        offer = next((s for s in R.store_stock(key, catalog) if s["idx"] == idx), None)
        if not offer:
            raise GameError("That item isn't in the store today.")
        with self._conn() as c:
            # The primary key (day, idx) makes this first come, first served even if two people tap at once.
            cur = c.execute("INSERT OR IGNORE INTO game_store_sold(day, idx, user_id, bought_at) VALUES(?,?,?,?)", (key, idx, user_id, int(now)))
            if not cur.rowcount:
                raise GameError("Someone already bought that one today.")
            self._spend(c, user_id, offer["price"])
            item = dict(offer["item"])
            placed = self._give_item(c, user_id, item)
            if item["rarity"] == "Legendary":
                name = c.execute("SELECT username FROM game_players WHERE user_id=?", (user_id,)).fetchone()[0]
                self._feed(c, user_id, name, "store", {"text": f"bought the Legendary {item['name']} from the System Store for {offer['price']} bookmarks."})
        return {**item, "placed": placed}

    def buy_crate(self, user_id: str, catalog: List[Dict], rng: Optional[random.Random] = None) -> Dict:
        self._require_store(user_id)
        rng = rng or random.Random()
        raw = R.roll_item(catalog, R.upgrade_rarity(R.roll_rarity(R.CRATE_TABLE, rng), rng), "", rng)
        if not raw:
            raise GameError("The crate is empty. The System apologizes. Not really.")
        item = R.item_view(raw)
        with self._conn() as c:
            self._spend(c, user_id, R.CRATE_COST)
            placed = self._give_item(c, user_id, item)
        return {**item, "placed": placed}

    def buy_supply(self, user_id: str, key: str) -> Dict:
        if key not in R.SUPPLIES:
            raise ValueError("unknown supply")
        self._require_store(user_id)
        with self._conn() as c:
            sup = json.loads(c.execute("SELECT supplies_json FROM game_players WHERE user_id=?", (user_id,)).fetchone()[0] or "{}")
            if sum(sup.values()) >= R.SUPPLY_CARRY:
                raise GameError(f"You can only carry {R.SUPPLY_CARRY} supplies.")
            self._spend(c, user_id, R.SUPPLIES[key]["cost"])
            sup[key] = sup.get(key, 0) + 1
            c.execute("UPDATE game_players SET supplies_json=? WHERE user_id=?", (json.dumps(sup), user_id))
        return sup

    @staticmethod
    def _return_supplies(c, user_id: str, packed: Dict, used: Dict) -> Dict:
        """Put back whatever was packed but not used. Returns what came back."""
        back = {k: max(0, int(n) - max(0, int(used.get(k, 0) or 0))) for k, n in (packed or {}).items()}
        back = {k: n for k, n in back.items() if n}
        if back:
            sup = json.loads(c.execute("SELECT supplies_json FROM game_players WHERE user_id=?", (user_id,)).fetchone()[0] or "{}")
            for k, n in back.items():
                sup[k] = sup.get(k, 0) + n
            c.execute("UPDATE game_players SET supplies_json=? WHERE user_id=?", (json.dumps(sup), user_id))
        return back

    # ── dungeons ─────────────────────────────────────────────────────────
    def sync_dungeons(self, user_id: str, books: Iterable[Tuple[str, str, str, float, int]]) -> int:
        """Add a waiting dungeon for every finished book not seen before.
        `books` yields (item_id, title, series, hours, finished_at). Existing
        rows keep their status; only their descriptive fields refresh.
        Returns the number of new dungeons."""
        with self._conn() as c:
            known = {r[0] for r in c.execute("SELECT item_id FROM game_dungeons WHERE user_id=?", (user_id,))}
            rows = list({i: (user_id, i, t, s or "", float(h or 0), int(f or 0)) for i, t, s, h, f in books}.values())
            c.executemany(
                "INSERT INTO game_dungeons(user_id, item_id, title, series, hours, finished_at) VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(user_id, item_id) DO UPDATE SET title=excluded.title, series=excluded.series, "
                "hours=excluded.hours, finished_at=excluded.finished_at",
                rows,
            )
        self.pay_book_bonuses(user_id)
        return sum(1 for r in rows if r[1] not in known)

    def pay_book_bonuses(self, user_id: str) -> int:
        """+25 bookmarks per book finished after launch, once each. Only for
        players who have a character; others are paid when they first log in."""
        with self._conn() as c:
            if not c.execute("SELECT 1 FROM game_players WHERE user_id=?", (user_id,)).fetchone():
                return 0
            rows = c.execute("SELECT item_id, title, series FROM game_dungeons WHERE user_id=? AND bonus_paid=0 AND finished_at >= ?",
                             (user_id, self.launched_at)).fetchall()
            for r in rows:
                c.execute("UPDATE game_dungeons SET bonus_paid=1 WHERE user_id=? AND item_id=?", (user_id, r["item_id"]))
                c.execute("UPDATE game_players SET bookmarks=bookmarks+? WHERE user_id=?", (R.BOOK_FINISHED_BONUS, user_id))
                self._notice(c, user_id, "book_finished", {"title": r["title"], "item_id": r["item_id"], "bookmarks": R.BOOK_FINISHED_BONUS,
                                                           "series": [n for _k, n, _q in R.parse_series(r["series"])]})
        return len(rows)

    def dungeon_counts(self, user_id: str) -> Dict[str, int]:
        counts = {s: 0 for s in DUNGEON_STATUSES}
        with self._conn() as c:
            for row in c.execute("SELECT status, COUNT(*) n FROM game_dungeons WHERE user_id=? GROUP BY status", (user_id,)):
                counts[row["status"]] = row["n"]
        counts["open"] = counts["waiting"]
        return counts

    def list_dungeons(self, user_id: str, status: str = "waiting", sort: str = "new",
                      limit: int = 60, offset: int = 0) -> List[Dict]:
        order = {"long": "hours DESC, finished_at DESC", "random": "RANDOM()"}.get(sort, "finished_at DESC, hours DESC")
        with self._conn() as c:
            rows = c.execute(
                f"SELECT item_id, title, series, hours, finished_at, status, attempts, cleared_at FROM game_dungeons "
                f"WHERE user_id=? AND status=? ORDER BY {order} LIMIT ? OFFSET ?",
                (user_id, status if status in DUNGEON_STATUSES else "waiting", max(1, min(int(limit), 500)), max(0, int(offset))),
            ).fetchall()
        out = [{**dict(r), "revive_cost": R.revive_cost(r["hours"]), "theme": self.theme_for(r["item_id"], r["series"])} for r in rows]
        if status == "waiting" and out:
            with self._conn() as c:
                cleared = self._cleared_ids(c, user_id)
                rewarded = self._series_rewarded(c, user_id)
            for d in out:
                d["series_reward"] = self._series_reward_for(d["item_id"], cleared | {d["item_id"]}, rewarded)
        return out

    def theme_for(self, item_id: str, series: str) -> str:
        """The dungeon's look from its book's genre (never its difficulty)."""
        look = R.series_look(series or "")
        if look:
            return look  # a series the family knows gets its own look
        if not self.genre_tags:
            return "dungeon"
        try:
            tags, text = self.genre_tags(item_id, series)
            theme = R.pick_theme(tags)
            # Tags decide; the blurb only helps when the tags say nothing.
            return R.pick_theme([text]) if theme == "dungeon" and text else theme
        except Exception:
            return "dungeon"  # a missing tag source never blocks a run

    # ── series catch-up rewards ──────────────────────────────────────────
    @staticmethod
    def _cleared_ids(c, user_id: str) -> set:
        return {r[0] for r in c.execute("SELECT item_id FROM game_dungeons WHERE user_id=? AND status='cleared'", (user_id,))}

    @staticmethod
    def _series_rewarded(c, user_id: str) -> Dict[str, int]:
        return {r[0]: r[1] for r in c.execute("SELECT series_key, books FROM game_series_rewards WHERE user_id=?", (user_id,))}

    def _series_reward_for(self, item_id: str, cleared: set, rewarded: Dict[str, int]) -> Optional[Dict]:
        """The best series reward clearing `item_id` would pay (finale beats
        caught_up), or None. `cleared` already includes item_id."""
        best = None
        for key, _n in self.item_series.get(item_id, []):
            entry = self.series_index.get(key)
            kind = R.series_outcome(entry, cleared, rewarded.get(key))
            if kind and (not best or (entry["qualifies"] and not best["chest"]) or kind == "finale"):
                best = {"kind": kind, "key": key, "series": entry["name"], "books": entry["count"], "chest": entry["qualifies"],
                        "bookmarks": R.series_bookmarks(entry, rewarded.get(key))}
        return best

    def _claim_series_rewards(self, c, user_id: str, item_id: str, now: int) -> List[Dict]:
        """Record every series this clear finishes (or catches the player up on)
        and pay its bookmarks. Returns them, the chest-worthy ones first."""
        cleared = self._cleared_ids(c, user_id) | {item_id}
        rewarded = self._series_rewarded(c, user_id)
        done = []
        for key, _n in self.item_series.get(item_id, []):
            entry = self.series_index.get(key)
            kind = R.series_outcome(entry, cleared, rewarded.get(key))
            if not kind:
                continue
            c.execute("INSERT INTO game_series_rewards(user_id, series_key, books, finale_at, updated_at) VALUES(?,?,?,?,?) "
                      "ON CONFLICT(user_id, series_key) DO UPDATE SET books=excluded.books, updated_at=excluded.updated_at",
                      (user_id, key, entry["count"], now, now))
            done.append({"kind": kind, "key": key, "series": entry["name"], "books": entry["count"], "chest": entry["qualifies"],
                         "bookmarks": R.series_bookmarks(entry, rewarded.get(key))})
        done.sort(key=lambda d: (not d["chest"], d["kind"] != "finale"))
        if done:
            c.execute("UPDATE game_players SET bookmarks = bookmarks + ? WHERE user_id=?", (sum(d["bookmarks"] for d in done), user_id))
        return done

    def get_dungeon(self, user_id: str, item_id: str) -> Optional[Dict]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM game_dungeons WHERE user_id=? AND item_id=?", (user_id, item_id)).fetchone()
        return dict(row) if row else None

    def revive(self, user_id: str, item_id: str) -> int:
        with self._conn() as c:
            row = c.execute("SELECT status, hours FROM game_dungeons WHERE user_id=? AND item_id=?", (user_id, item_id)).fetchone()
            if not row or row["status"] != "fallen":
                raise GameError("That book isn't on your Fallen shelf.")
            cost = R.revive_cost(row["hours"])
            self._spend(c, user_id, cost)
            c.execute("UPDATE game_dungeons SET status='waiting' WHERE user_id=? AND item_id=?", (user_id, item_id))
        return cost

    # ── Monster Workshop ─────────────────────────────────────────────────
    def custom_monsters(self, enabled_only: bool = False) -> List[Dict]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM game_custom_monsters" + (" WHERE enabled=1" if enabled_only else "") +
                             " ORDER BY updated_at DESC").fetchall()
        return [{**json.loads(r["data_json"]), "enabled": bool(r["enabled"]), "suggestion_id": r["suggestion_id"],
                 "updated_at": r["updated_at"]} for r in rows]

    def save_custom_monster(self, raw: Dict, suggestion_id: Optional[int] = None) -> Dict:
        """Create or update a Workshop monster (new ones start disabled)."""
        if isinstance(raw, dict) and raw.get("series"):
            full, note = self.resolve_series(str(raw["series"]))
            if full is None:
                raise GameError(note[:1].upper() + note[1:] + ". Use the exact name from docs/MONSTER_SERIES.md.")
            raw = {**raw, "series": full}
        m = game_monsters.clean_monster(raw)
        now = int(time.time())
        with self._conn() as c:
            old = c.execute("SELECT suggestion_id FROM game_custom_monsters WHERE id=?", (m["id"],)).fetchone()
            if old and not raw.get("id"):
                raise GameError("A Workshop monster already has that name. Edit that one instead.")
            if old:
                c.execute("UPDATE game_custom_monsters SET data_json=?, updated_at=? WHERE id=?", (json.dumps(m), now, m["id"]))
            else:
                if suggestion_id and not c.execute("SELECT 1 FROM game_monster_suggestions WHERE id=?", (suggestion_id,)).fetchone():
                    suggestion_id = None
                c.execute("INSERT INTO game_custom_monsters(id, data_json, enabled, suggestion_id, created_at, updated_at) VALUES(?,?,0,?,?,?)",
                          (m["id"], json.dumps(m), suggestion_id, now, now))
                if suggestion_id:
                    c.execute("UPDATE game_monster_suggestions SET status='building', monster_id=? WHERE id=?", (m["id"], suggestion_id))
        return m

    def set_monster_enabled(self, monster_id: str, enabled: bool) -> None:
        """Turn a Workshop monster on or off. The first time a monster built
        from a player's idea goes live, that player hears about it."""
        with self._conn() as c:
            row = c.execute("SELECT * FROM game_custom_monsters WHERE id=?", (monster_id,)).fetchone()
            if not row:
                raise GameError("No such monster.")
            c.execute("UPDATE game_custom_monsters SET enabled=?, updated_at=? WHERE id=?", (int(enabled), int(time.time()), monster_id))
            if enabled and row["suggestion_id"]:
                sug = c.execute("SELECT * FROM game_monster_suggestions WHERE id=?", (row["suggestion_id"],)).fetchone()
                if sug and sug["status"] != "live":
                    m = json.loads(row["data_json"])
                    c.execute("UPDATE game_monster_suggestions SET status='live' WHERE id=?", (sug["id"],))
                    theme = f"{m['series']} dungeons" if m.get("series") else game_monsters.TIERS.get(m["tier"], "")
                    self._notice(c, sug["user_id"], "monster_live", {"name": m["name"], "theme": theme})
                    self._feed(c, sug["user_id"], sug["username"], "monster",
                               {"text": f"had a monster idea come to life: {m['name']} now lurks in {theme}."})
                    self._bump(c, sug["user_id"], sets={"flags": ["monster_live"]})
                    self._check_badges(c, sug["user_id"])

    def resolve_series(self, name: str) -> Tuple[Optional[str], str]:
        """A monster's series name -> (the library's exact series name, note).
        Accepts a cut-off name ("Last Save Da") when one library series starts
        with it (or one candidate is the start of all the others: "Ascend
        Onli" -> "Ascend Online"). "&" and "and" count as the same. Returns
        (None, reason) when nothing matches. Needs self.library_series (every
        series name in the library, set by game_api)."""
        names = self.library_series or [e["name"] for e in self.series_index.values()]
        if not name or not names:
            return name, ""
        norm = lambda n: R.tier_norm(re.sub(r"\s*&\s*", " and ", n or ""))
        lib: Dict[str, str] = {}
        for full in names:
            lib.setdefault(norm(full), full)
        wanted = [norm(n) for _k, n, _q in R.parse_series(name)] or [norm(name)]
        for w in wanted:
            if w in lib:
                return lib[w], ""
            starts = sorted((k for k in lib if k.startswith(w)), key=len) if len(w) >= 6 else []
            if starts and all(k.startswith(starts[0]) for k in starts):
                full = lib[starts[0]]
                return full, f"series completed to '{full}'"
            if starts:
                return None, f"'{name}' could be several series: {', '.join(sorted(lib[k] for k in starts)[:4])}"
        return None, f"no series called '{name}' in the library"

    def repair_monster_series(self) -> Dict:
        """Fix imported monsters whose series name doesn't match the library
        (e.g. cut off while copying). Keeps their ids; returns what changed."""
        fixed, unmatched = [], []
        with self._conn() as c:
            for r in c.execute("SELECT id, data_json FROM game_custom_monsters").fetchall():
                m = json.loads(r["data_json"])
                if not m.get("series"):
                    continue
                full, note = self.resolve_series(m["series"])
                if full is None:
                    unmatched.append({"id": r["id"], "name": m["name"], "series": m["series"], "why": note})
                elif full != m["series"]:
                    fixed.append({"name": m["name"], "from": m["series"], "to": full})
                    m["series"] = full
                    c.execute("UPDATE game_custom_monsters SET data_json=?, updated_at=? WHERE id=?", (json.dumps(m), int(time.time()), r["id"]))
        return {"fixed": fixed, "unmatched": unmatched}

    def import_monsters(self, items: List[Dict], enable: bool = True) -> List[Dict]:
        """Bulk-add monsters (e.g. from docs/MONSTER_PROMPT.md). Each is checked
        like a Workshop monster; one with the same name and series replaces the
        old one, and the same name in a different series gets its own id.
        Returns {name, ok, id | error} per monster."""
        if not isinstance(items, list) or not items:
            raise ValueError("Paste a JSON list of monsters.")
        if len(items) > 300:
            raise ValueError("At most 300 monsters per import.")
        out = []
        for raw in items:
            name = str((raw or {}).get("name") or "?") if isinstance(raw, dict) else "?"
            try:
                note = ""
                if isinstance(raw, dict) and raw.get("series"):
                    full, note = self.resolve_series(str(raw["series"]))
                    if full is None:
                        raise ValueError(note[:1].upper() + note[1:] + ". Use the exact name from docs/MONSTER_SERIES.md.")
                    raw = {**raw, "series": full}
                m = game_monsters.clean_monster(raw)
                with self._conn() as c:
                    old = c.execute("SELECT data_json FROM game_custom_monsters WHERE id=?", (m["id"],)).fetchone()
                if old and json.loads(old[0]).get("series", "") != m.get("series", ""):
                    m = game_monsters.clean_monster({**raw, "id": f"{m.get('series', 'general')} {m['name']}"})
                self.save_custom_monster({**raw, "id": m["id"]})
                if enable:
                    self.set_monster_enabled(m["id"], True)
                out.append({"name": m["name"], "ok": True, "id": m["id"], "series": m.get("series", ""), "note": note})
            except (ValueError, GameError) as e:
                out.append({"name": name, "ok": False, "error": str(e)})
        return out

    def delete_custom_monster(self, monster_id: str) -> None:
        with self._conn() as c:
            row = c.execute("SELECT suggestion_id FROM game_custom_monsters WHERE id=?", (monster_id,)).fetchone()
            if not row:
                raise GameError("No such monster.")
            c.execute("DELETE FROM game_custom_monsters WHERE id=?", (monster_id,))
            if row["suggestion_id"]:
                c.execute("UPDATE game_monster_suggestions SET status='new', monster_id=NULL WHERE id=? AND status='building'",
                          (row["suggestion_id"],))

    SUGGESTION_OPEN_LIMIT = 3

    def suggest_monster(self, user_id: str, name: str, idea: str, tier: int = 0) -> Dict:
        name = " ".join(str(name or "").split())[:40]
        idea = " ".join(str(idea or "").split())[:400]
        if len(name) < 3 or len(idea) < 10:
            raise GameError("Give it a name and a sentence or two about it.")
        if tier and tier not in game_monsters.TIERS:
            raise ValueError("unknown theme")
        with self._conn() as c:
            p = c.execute("SELECT username FROM game_players WHERE user_id=?", (user_id,)).fetchone()
            open_n = c.execute("SELECT COUNT(*) FROM game_monster_suggestions WHERE user_id=? AND status IN ('new','building')",
                               (user_id,)).fetchone()[0]
            if open_n >= self.SUGGESTION_OPEN_LIMIT:
                raise GameError(f"You already have {open_n} ideas waiting. Give the Workshop a moment.")
            cur = c.execute("INSERT INTO game_monster_suggestions(user_id, username, name, idea, tier, created_at) VALUES(?,?,?,?,?,?)",
                            (user_id, p["username"], name, idea, int(tier or 0), int(time.time())))
        return {"id": cur.lastrowid, "name": name, "idea": idea, "tier": tier, "status": "new"}

    def suggestions(self, user_id: Optional[str] = None) -> List[Dict]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM game_monster_suggestions" + (" WHERE user_id=?" if user_id else "") +
                             " ORDER BY id DESC", (user_id,) if user_id else ()).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["monster"] = json.loads(d.pop("monster_json")) if d.get("monster_json") else None
            out.append(d)
        return out

    def submit_monster(self, user_id: str, raw: Dict) -> Dict:
        """Monster Maker: a player builds a whole monster; it waits for the
        admin to approve it (same checks as the Workshop)."""
        if not isinstance(raw, dict):
            raise ValueError("Monster must be an object.")
        raw = {k: v for k, v in raw.items() if k != "id"}
        if raw.get("series"):
            full, note = self.resolve_series(str(raw["series"]))
            if full is None:
                raise GameError(note[:1].upper() + note[1:] + ". Pick a series from your library.")
            raw["series"] = full
        m = game_monsters.clean_monster(raw)
        with self._conn() as c:
            if c.execute("SELECT 1 FROM game_custom_monsters WHERE id=?", (m["id"],)).fetchone():
                raise GameError("A monster with that name already exists. Try another name.")
            p = c.execute("SELECT username FROM game_players WHERE user_id=?", (user_id,)).fetchone()
            open_n = c.execute("SELECT COUNT(*) FROM game_monster_suggestions WHERE user_id=? AND status IN ('new','building')",
                               (user_id,)).fetchone()[0]
            if open_n >= self.SUGGESTION_OPEN_LIMIT:
                raise GameError(f"You already have {open_n} monsters waiting for approval.")
            idea = m.get("appear") or f"A {m['role']} for {m.get('series') or game_monsters.TIERS.get(m['tier'], '')}."
            cur = c.execute("INSERT INTO game_monster_suggestions(user_id, username, name, idea, tier, created_at, monster_json) VALUES(?,?,?,?,?,?,?)",
                            (user_id, p["username"], m["name"], idea[:400], m["tier"], int(time.time()), json.dumps(m)))
        return {"id": cur.lastrowid, "name": m["name"], "status": "new"}

    def approve_submission(self, suggestion_id: int) -> Dict:
        """Admin approves a Monster Maker build: it joins the dungeons, and the
        player gets the "your monster is alive" popup and badge."""
        with self._conn() as c:
            row = c.execute("SELECT * FROM game_monster_suggestions WHERE id=?", (suggestion_id,)).fetchone()
        if not row or not row["monster_json"]:
            raise GameError("No player-built monster there.")
        raw = json.loads(row["monster_json"])
        m = self.save_custom_monster({k: v for k, v in raw.items() if k != "id"}, suggestion_id=suggestion_id)
        self.set_monster_enabled(m["id"], True)
        return m

    def set_suggestion_status(self, suggestion_id: int, status: str) -> None:
        if status not in ("new", "dismissed"):
            raise ValueError("unknown status")
        with self._conn() as c:
            if not c.execute("UPDATE game_monster_suggestions SET status=? WHERE id=?", (status, suggestion_id)).rowcount:
                raise GameError("No such idea.")

    # ── the party ────────────────────────────────────────────────────────
    def party(self) -> List[Dict]:
        """Everyone with a finished character, highest level first."""
        with self._conn() as c:
            players = c.execute("SELECT * FROM game_players WHERE look_json IS NOT NULL AND cls IS NOT NULL "
                                "ORDER BY level DESC, xp DESC, username").fetchall()
            clears = {r[0]: r[1] for r in c.execute("SELECT user_id, COUNT(*) FROM game_dungeons WHERE status='cleared' GROUP BY user_id")}
            badges = {r[0]: r[1] for r in c.execute("SELECT user_id, COUNT(*) FROM game_achievements GROUP BY user_id")}
            gear: Dict[str, Dict] = {}
            for r in c.execute("SELECT * FROM game_items WHERE equipped_slot IS NOT NULL"):
                gear.setdefault(r["user_id"], {})[r["equipped_slot"]] = self._item_row(r)
        return [{"user_id": p["user_id"], "username": p["username"], "look": self._dressed(p["look_json"], self._worn(p["cosmetics_json"])),
                 "worn": self._worn(p["cosmetics_json"]), "title": self._title(self._worn(p["cosmetics_json"])), "cls": p["cls"],
                 "level": p["level"], "xp": p["xp"], "xp_next": R.xp_to_next(p["level"]), "clears": clears.get(p["user_id"], 0),
                 "badges": badges.get(p["user_id"], 0), "gear": gear.get(p["user_id"], {}), "joined_at": p["created_at"],
                 "stats": R.player_stats(p["cls"], p["level"], list(gear.get(p["user_id"], {}).values()), json.loads(p["upgrades_json"] or "{}"))}
                for p in players]

    # ── practice (no rewards, nothing saved) ─────────────────────────────
    def practice_config(self, user_id: str, difficulty: str, tier: int) -> Dict:
        p = self.get_player(user_id)
        if not p["look"] or not p["cls"]:
            raise GameError("Finish building your character first.")
        if difficulty not in R.PRACTICE_DIFFICULTY:
            raise ValueError("unknown difficulty")
        if tier not in game_monsters.TIERS:
            raise ValueError("unknown theme")
        cfg = self.run_config(user_id)
        diff = R.PRACTICE_DIFFICULTY[difficulty]
        cfg.update({"practice": True, "difficulty": difficulty, "enemy_scale": R.with_power(R.practice_scale(p["level"], difficulty), cfg["power"]),
                    "monsters": game_monsters.roster(tier, self.custom_monsters(enabled_only=True)), "title": f"Practice: {game_monsters.TIERS[tier]} ({diff['name']})",
                    "hours": 0, "series": "", "supplies": {}, "theme": random.choice(list(R.THEMES))})
        return cfg

    # ── runs ─────────────────────────────────────────────────────────────
    def run_config(self, user_id: str) -> Dict:
        """Everything the phone needs to play: stats come from the server."""
        p = self.get_player(user_id)
        stats = R.player_stats(p["cls"], p["level"], list(self.equipped(user_id).values()), p["upgrades"])
        tier = R.enemy_tier(p["level"])
        power = R.power_factors(p["cls"], p["level"], stats)
        return {"stats": stats, "level": p["level"], "cls": p["cls"], "look": p["look"], "pet_skin": self._pet_skin(p),
                "enemy_scale": R.with_power(R.enemy_scale(p["level"]), power), "power": power, "enemy_tier": tier, "floors": R.FLOORS,
                "monsters": game_monsters.roster(tier, self.custom_monsters(enabled_only=True))}

    def start_run(self, user_id: str, item_id: str, now: Optional[int] = None) -> Dict:
        now = int(now or time.time())
        p = self.get_player(user_id)
        if not p["look"] or not p["cls"]:
            raise GameError("Finish building your character first.")
        with self._conn() as c:
            if c.execute("SELECT 1 FROM game_pending_loot WHERE user_id=?", (user_id,)).fetchone():
                raise GameError("You have loot waiting. Sort your bag first.")
        active = self.active_run(user_id)
        if active:
            raise GameError(f"You're still in {active['title']}. Resume it or give up first.")
        dungeon = self.get_dungeon(user_id, item_id)
        if not dungeon:
            raise GameError("That book hasn't unlocked a dungeon for you.")
        if dungeon["status"] == "cleared":
            raise GameError("You've already cleared that dungeon.")
        if dungeon["status"] == "fallen":
            raise GameError("That book is on your Fallen shelf. Revive it first.")
        with self._conn() as c:
            run_id = secrets.token_hex(12)
            cfg = self.run_config(user_id)
            packed = {k: n for k, n in json.loads(c.execute("SELECT supplies_json FROM game_players WHERE user_id=?",
                                                             (user_id,)).fetchone()[0] or "{}").items() if n}
            c.execute("UPDATE game_players SET supplies_json='{}' WHERE user_id=?", (user_id,))
            snapshot = {**cfg, "hours": dungeon["hours"], "title": dungeon["title"], "series": dungeon["series"], "supplies": packed,
                        "theme": self.theme_for(item_id, dungeon["series"]),
                        "monsters": game_monsters.roster(cfg["enemy_tier"], self.custom_monsters(enabled_only=True), series=dungeon["series"])}
            null = self._null_state(c, now + self.boss_offset)
            if null and null["active"]:  # the Null spreads: monsters a little stronger until cleansed
                sc = snapshot["enemy_scale"]
                snapshot.update(null=True, enemy_scale={**sc, "hp": round(sc["hp"] * R.NULL_BUFF, 3), "atk": round(sc["atk"] * R.NULL_BUFF, 3)})
            c.execute("INSERT INTO game_runs(id, user_id, item_id, started_at, snapshot_json) VALUES(?,?,?,?,?)",
                      (run_id, user_id, item_id, now, json.dumps(snapshot)))
            c.execute("UPDATE game_dungeons SET attempts=attempts+1 WHERE user_id=? AND item_id=?", (user_id, item_id))
        return {"run_id": run_id, **snapshot, "item_id": item_id}

    def active_run(self, user_id: str) -> Optional[Dict]:
        """The player's open dungeon run (at most one), with its saved progress."""
        with self._conn() as c:
            r = c.execute("SELECT * FROM game_runs WHERE user_id=? AND finished_at IS NULL ORDER BY started_at DESC LIMIT 1",
                          (user_id,)).fetchone()
        if not r:
            return None
        snap = json.loads(r["snapshot_json"])
        cls = self.get_player(user_id)["cls"]
        if snap.get("cls") and cls and snap["cls"] != cls:
            # Class changed since this run began (before the restart prompt existed):
            # drop it with no penalty so the book restarts as the right class.
            with self._conn() as c:
                self._return_supplies(c, user_id, snap.get("supplies") or {}, {})
                c.execute("UPDATE game_runs SET finished_at=?, outcome='restarted' WHERE id=?", (int(time.time()), r["id"]))
                c.execute("UPDATE game_dungeons SET attempts=MAX(0, attempts-1) WHERE user_id=? AND item_id=?", (user_id, r["item_id"]))
            return None
        if self._upgrade_snapshot(snap, r["item_id"]):
            with self._conn() as c:
                c.execute("UPDATE game_runs SET snapshot_json=? WHERE id=?", (json.dumps(snap), r["id"]))
        return {"run_id": r["id"], "item_id": r["item_id"], **snap,
                "progress": json.loads(r["progress_json"]) if r["progress_json"] else None}

    def _upgrade_snapshot(self, snap: Dict, item_id: str) -> bool:
        """Fill in what runs started by older builds didn't save (the monster
        roster, supplies, the dungeon look), so they can still be resumed.
        Returns True if anything was added."""
        changed = False
        if not snap.get("monsters"):
            tier = snap.get("enemy_tier") or R.enemy_tier(snap.get("level", 1))
            snap["monsters"] = game_monsters.roster(tier, self.custom_monsters(enabled_only=True))
            changed = True
        if "supplies" not in snap:
            snap["supplies"] = {}
            changed = True
        if "theme" not in snap:
            snap["theme"] = self.theme_for(item_id, snap.get("series", ""))
            changed = True
        return changed

    def save_progress(self, user_id: str, run_id: str, progress: Dict) -> None:
        """Checkpoint between rooms so a run can be resumed later."""
        data = json.dumps(progress)
        if len(data) > MAX_PROGRESS_BYTES:
            raise ValueError("progress too large")
        with self._conn() as c:
            cur = c.execute("UPDATE game_runs SET progress_json=? WHERE id=? AND user_id=? AND finished_at IS NULL",
                            (data, run_id, user_id))
            if not cur.rowcount:
                raise GameError("That run is already over.")

    def abandon_run(self, user_id: str, run_id: str, now: Optional[int] = None) -> Dict:
        """Give up: counts exactly like falling at the last saved checkpoint
        (half XP for what you'd beaten, floor bookmarks, book to Fallen)."""
        with self._conn() as c:
            row = c.execute("SELECT progress_json FROM game_runs WHERE id=? AND user_id=?", (run_id, user_id)).fetchone()
            prog = json.loads(row["progress_json"]) if row and row["progress_json"] else {}
            report = {"outcome": "dead", "floors": int(prog.get("floor", 0)) + 1 if prog else 0,
                      "kills": int(prog.get("kills", 0)), "elites": int(prog.get("elites", 0)),
                      "supplies_used": prog.get("supplies_used") or {},
                      "feats": {"seen": (prog.get("feats") or {}).get("seen") or {}}}
            return self._settle(c, user_id, run_id, report, int(now or time.time()), abandoned=True)

    def finish_run(self, user_id: str, run_id: str, report: Dict, catalog: List[Dict],
                   now: Optional[int] = None, rng: Optional[random.Random] = None) -> Dict:
        now = int(now or time.time())
        with self._conn() as c:
            return self._settle(c, user_id, run_id, report, now, catalog=catalog, rng=rng)

    def _settle(self, c, user_id: str, run_id: str, report: Dict, now: int, catalog: Optional[List[Dict]] = None,
                rng: Optional[random.Random] = None, abandoned: bool = False) -> Dict:
        run = c.execute("SELECT * FROM game_runs WHERE id=? AND user_id=?", (run_id, user_id)).fetchone()
        if not run:
            raise GameError("That run doesn't exist.")
        if run["finished_at"]:
            raise GameError("That run is already over.")
        outcome = report.get("outcome")
        if outcome not in OUTCOMES:
            raise ValueError("invalid outcome")
        if not abandoned and now - run["started_at"] < R.MIN_RUN_SECONDS:
            raise GameError("That was suspiciously fast.")
        snap = json.loads(run["snapshot_json"])

        # Trust the phone's report only within what a real run can produce.
        died = outcome == "dead"
        cleared = not died
        boss = outcome == "boss"
        floors = 3 if cleared else max(0, min(int(report.get("floors", 0)), 3))
        kills = max(0, min(int(report.get("kills", 0)), R.MAX_KILLS))
        elites = max(0, min(int(report.get("elites", 0)), kills))

        p = c.execute("SELECT * FROM game_players WHERE user_id=?", (user_id,)).fetchone()
        ups = json.loads(p["upgrades_json"] or "{}")
        xp = R.run_xp(snap["level"], kills, elites, boss, floors, cleared, snap["hours"], ups.get("scholar", 0), died)
        bookmarks = R.run_bookmarks(floors, cleared, boss)

        level, levels_gained = self._add_xp(c, user_id, xp, bookmarks, now)

        packed = dict(snap.get("supplies") or {})
        used = {k: v for k, v in (report.get("supplies_used") or {}).items() if k in packed}
        series_done = self._claim_series_rewards(c, user_id, run["item_id"], now) if cleared else []
        series_reward = series_done[0] if series_done else None
        chest_reward = series_reward if series_reward and series_reward["chest"] else None
        loot = []
        if cleared and catalog:
            rng = rng or random.Random()
            table = R.rarity_table(boss, snap["hours"], ups.get("lucky_find", 0))
            for n in range(R.chest_count(snap["hours"])):
                rarity = R.roll_rarity(table, rng)
                if n == 0 and packed.get("coin") and not used.get("coin"):
                    second = R.roll_rarity(table, rng)  # Lucky Coin: roll twice, keep the better
                    rarity = max(rarity, second, key=RARITY_RANK.get)
                    used["coin"] = 1
                if n == 0 and chest_reward:  # series finale / caught up (5+ books): first chest at least Epic / Rare
                    rarity = max(rarity, R.SERIES_REWARD_FLOOR[chest_reward["kind"]], key=RARITY_RANK.get)
                rarity = R.upgrade_rarity(rarity, rng, ups.get("lucky_find", 0))
                raw = R.roll_item(catalog, rarity, snap.get("series", ""), rng)
                if raw:
                    item = R.item_view(raw)
                    placed = self._give_item(c, user_id, item)  # stamps its level
                    loot.append({**item, "placed": placed})

        c.execute("UPDATE game_dungeons SET status=?, cleared_at=? WHERE user_id=? AND item_id=?",
                  ("fallen" if died else "cleared", None if died else now, user_id, run["item_id"]))
        self._count_run(c, user_id, snap, report, used, died, boss, floors, kills, elites, abandoned, run["item_id"])
        returned = self._return_supplies(c, user_id, packed, used)
        result = {"outcome": outcome, "xp": xp, "bookmarks": bookmarks, "level": level, "levels_gained": levels_gained,
                  "supplies_returned": returned, "coin_used": bool(used.get("coin")) and cleared,
                  "loot": loot, "abandoned": abandoned, "revive_cost": R.revive_cost(snap["hours"]) if died else 0,
                  "series_reward": series_reward, "series_bookmarks": sum(d["bookmarks"] for d in series_done)}
        c.execute("UPDATE game_runs SET finished_at=?, outcome=?, result_json=? WHERE id=?",
                  (now, "abandoned" if abandoned else outcome, json.dumps(result), run_id))

        title = snap.get("title", "a book")
        if levels_gained:
            self._feed(c, user_id, p["username"], "level", {"text": f"reached level {level}."})
        if boss:
            best = max((RARITY_RANK[i["rarity"]] for i in loot), default=-1)
            self._feed(c, user_id, p["username"], "boss", {"text": f"beat the floor boss in {title}" + (
                f" and found {'an' if R.RARITIES[best][0] in 'AEIOU' else 'a'} {R.RARITIES[best]} chest." if best >= 2 else ".")})
        elif died and not abandoned:
            self._feed(c, user_id, p["username"], "death", {"text": f"fell in {title}. The System was delighted."})
        for sr in series_done:
            chest = ""
            if sr is chest_reward:
                got = loot[0]["rarity"] if loot else R.SERIES_REWARD_FLOOR[sr["kind"]]
                chest = f" and found {'an' if got[0] in 'AEIOU' else 'a'} {got} chest"
                sr["chest_rarity"] = got
            text = (f"finished all {sr['books']} books of {sr['series']}{chest}!" if sr["kind"] == "finale"
                    else f"caught up on {sr['series']} again{chest}.")
            self._feed(c, user_id, p["username"], "series", {"text": text})
            self._notice(c, user_id, "series_complete", {"outcome": sr["kind"], "series": sr["series"], "books": sr["books"],
                                                         "new_books": sr["bookmarks"] // R.SERIES_BOOKMARKS_PER_BOOK,
                                                         "bookmarks": sr["bookmarks"], "chest_rarity": sr.get("chest_rarity")})
            if sr["kind"] == "finale" and sr["chest"]:
                self._bump(c, user_id, sets={"flags": ["series_finale"]})
        result["badges"] = self._check_badges(c, user_id)
        return result

    def _count_run(self, c, user_id: str, snap: Dict, report: Dict, used: Dict, died: bool, boss: bool,
                   floors: int, kills: int, elites: int, abandoned: bool, item_id: str) -> None:
        """Lifetime counters from one finished run. `feats` come from the phone
        and only unlock badges (which pay nothing)."""
        feats = report.get("feats") or {}
        cleared = not died
        add = {"kills": kills, "elites": elites, "bosses": int(boss), "stairs": int(cleared and not boss),
               "deaths": int(died and not abandoned), "loot_boxes": max(0, min(int(feats.get("loot_boxes") or 0), R.MAX_KILLS)),
               "smoke_escapes": min(int(used.get("smoke") or 0), 3)}
        flags = []
        if died and not abandoned and floors <= 1:
            flags.append("floor_one")
        if feats.get("clutch"):
            flags.append("clutch")
        if cleared:
            if snap.get("hours", 0) >= 20:
                flags.append("long_haul")
            if feats.get("flawless"):
                flags.append("flawless")
            if boss and feats.get("no_potion"):
                flags.append("no_potion_boss")
            if boss and snap.get("cls") == "runeblade" and feats.get("overcharge_boss"):
                flags.append("overcharge_boss")
            attempts = c.execute("SELECT attempts FROM game_dungeons WHERE user_id=? AND item_id=?", (user_id, item_id)).fetchone()
            add["revive_clears"] = int(bool(attempts and attempts[0] > 1))
        sets = {"flags": flags, "classes_cleared": [snap["cls"]] if cleared and snap.get("cls") else []}
        if snap.get("cls") in PETS_BY_CLASS:
            key, allowed = PETS_BY_CLASS[snap["cls"]]
            sets[key] = [k for k in (feats.get("pets") or []) if k in allowed]
        self._bump(c, user_id, add, sets)
        self._record_bestiary(c, user_id, feats.get("seen") or {}, snap)

    @staticmethod
    def _record_bestiary(c, user_id: str, seen: Dict, snap: Dict) -> None:
        """Add the monsters met this run to the player's Bestiary. Only ids
        from the run's own roster count (so nothing can be invented)."""
        roster = snap.get("monsters") or {}
        known = {m["id"] for m in (roster.get("regular") or []) + (roster.get("elite") or [])}
        if roster.get("boss"):
            known.add(roster["boss"]["id"])
        now = int(time.time())
        for mid, n in list(seen.items())[:40]:
            if mid not in known:
                continue
            n = max(0, min(int(n or 0), R.MAX_KILLS + 1))
            c.execute("INSERT INTO game_bestiary(user_id, monster_id, first_seen, defeated) VALUES(?,?,?,?) "
                      "ON CONFLICT(user_id, monster_id) DO UPDATE SET defeated = defeated + excluded.defeated",
                      (user_id, mid, now, n))

    def bestiary(self, user_id: str) -> Dict:
        """Every live monster; the ones this player hasn't met stay hidden."""
        with self._conn() as c:
            seen = {r["monster_id"]: dict(r) for r in c.execute("SELECT * FROM game_bestiary WHERE user_id=?", (user_id,))}
        pool = game_monsters.MONSTERS + self.custom_monsters(enabled_only=True)
        entries = []
        for m in pool:
            s = seen.get(m["id"])
            if not s:
                e = {"id": m["id"], "tier": m["tier"], "role": m["role"], "seen": False, "series": m.get("series", "")}
                if m.get("art"):
                    e["art"] = m["art"]   # drawn as a silhouette
                else:
                    e["svg"] = m.get("svg")
                entries.append(e)
                continue
            e = {**game_monsters.export(m), "tier": m["tier"], "series": m.get("series", ""), "style": game_monsters.STYLES[m.get("style", "balanced")]["label"],
                 "seen": True, "first_seen": s["first_seen"], "defeated": s["defeated"]}
            if not s["defeated"]:  # lore unlocks after the first win
                e.pop("death", None)
            entries.append(e)
        return {"tiers": game_monsters.TIERS, "entries": entries,
                "found": sum(1 for e in entries if e["seen"]), "total": len(entries)}

    # ── Tier List rewards ────────────────────────────────────────────────
    @staticmethod
    def _finished_series(c, user_id: str, launched: int) -> Dict[str, Dict]:
        """Series this player has finished a book in: {norm: {name, last, fresh}}.
        fresh = a book in it was finished after launch."""
        out: Dict[str, Dict] = {}
        for r in c.execute("SELECT series, finished_at FROM game_dungeons WHERE user_id=? AND series != ''", (user_id,)):
            for _k, name, _q in R.parse_series(r["series"]):
                e = out.setdefault(R.tier_norm(name), {"name": name, "last": 0, "fresh": False})
                e["last"] = max(e["last"], r["finished_at"] or 0)
                e["fresh"] = e["fresh"] or (r["finished_at"] or 0) >= launched
        return out

    def settle_tier_rewards(self, user_id: str, query: str, now: Optional[int] = None) -> Dict:
        """Pay for what the player's saved Tier List ranks (see game_rules
        TIER_*), then report what's left to rank. Called whenever they open
        the game, so a save made on the Tier List page pays on their next visit."""
        now = int(now or time.time())
        ranked = R.tier_entries(query)
        launched = self.launched_at
        with self._conn() as c:
            if not c.execute("SELECT 1 FROM game_players WHERE user_id=?", (user_id,)).fetchone():
                return {"to_rank": [], "fresh": 0}
            finished = self._finished_series(c, user_id, launched)
            rows = {r["series_norm"]: dict(r) for r in c.execute("SELECT * FROM game_tier_rewards WHERE user_id=?", (user_id,))}
            st = json.loads(c.execute("SELECT stats_json FROM game_players WHERE user_id=?", (user_id,)).fetchone()[0] or "{}")
            backlog_paid = st.get("tier_backlog", 0)
            paid, names, backlog_new = 0, [], 0
            for norm, info in finished.items():
                tier = R.tier_rank_of(ranked, norm)
                if not tier:
                    continue
                row = rows.get(norm)
                if not row:
                    if info["fresh"]:
                        pay, kind = R.TIER_FRESH_BOOKMARKS, "fresh"
                    else:
                        pay = R.TIER_BACKLOG_BOOKMARKS if backlog_paid + backlog_new < R.TIER_BACKLOG_CAP else 0
                        kind, backlog_new = "backlog", backlog_new + pay
                    c.execute("INSERT INTO game_tier_rewards VALUES(?,?,?,?,?,?,?)", (user_id, norm, info["name"], tier, kind, info["last"], now))
                elif tier != row["tier"] and info["last"] > row["book_at"]:
                    pay = R.TIER_RERANK_BOOKMARKS
                    c.execute("UPDATE game_tier_rewards SET tier=?, book_at=?, rewarded_at=? WHERE user_id=? AND series_norm=?",
                              (tier, info["last"], now, user_id, norm))
                else:
                    if tier != row["tier"]:  # moved without a new book: remember it, no pay
                        c.execute("UPDATE game_tier_rewards SET tier=? WHERE user_id=? AND series_norm=?", (tier, user_id, norm))
                    continue
                if pay:
                    paid += pay
                    names.append(info["name"])
            to_rank = sorted((info for norm, info in finished.items() if not R.tier_rank_of(ranked, norm)), key=lambda i: -i["last"])
            # Finishing another book in a ranked series is not a to-do (keeping
            # its rank is fine; moving it still pays TIER_RERANK_BOOKMARKS).
            rerank: List[Dict] = []
            if paid:
                p = c.execute("SELECT username FROM game_players WHERE user_id=?", (user_id,)).fetchone()
                c.execute("UPDATE game_players SET bookmarks=bookmarks+? WHERE user_id=?", (paid, user_id))
                self._bump(c, user_id, {"tier_backlog": backlog_new})
                self._notice(c, user_id, "tier_reward", {"bookmarks": paid, "count": len(names), "names": names[:4]})
                self._feed(c, user_id, p["username"], "tier", {"text": f"updated their Tier List and earned {paid} bookmark{'s' if paid != 1 else ''}."})
            if ranked and not to_rank:
                self._bump(c, user_id, sets={"flags": ["tier_current"]})
            self._check_badges(c, user_id)
        return {"to_rank": [i["name"] for i in to_rank], "fresh": sum(1 for i in to_rank if i["fresh"]),
                "rerank": [i["name"] for i in rerank], "paid": paid}

    # ── the December boss: the Null Regent ───────────────────────────────
    def _boss_now(self, now: Optional[float] = None) -> int:
        return int((now or time.time()) + self.boss_offset)

    @staticmethod
    def _boss_row(c, year: int) -> Optional[Dict]:
        r = c.execute("SELECT * FROM game_boss WHERE year=?", (year,)).fetchone()
        if not r:
            return None
        d = dict(r)
        d["settled"] = json.loads(d.pop("settled_json") or "{}")
        return d

    def _ensure_boss(self, c, year: int, now: int) -> Dict:
        """This December's Regent, created on first visit. Full health is
        sized from everyone's strength today (game_rules.boss_max_hp). If he
        escaped last year, he comes back with what he had left + BOSS_REGEN."""
        row = self._boss_row(c, year)
        if row:
            return row
        expected = []
        for p in c.execute("SELECT * FROM game_players WHERE look_json IS NOT NULL AND cls IS NOT NULL"):
            gear = [self._item_row(r) for r in c.execute("SELECT * FROM game_items WHERE user_id=? AND equipped_slot IS NOT NULL", (p["user_id"],))]
            st = R.player_stats(p["cls"], p["level"], gear, json.loads(p["upgrades_json"] or "{}"))
            expected.append(R.expected_attack(st, p["cls"], p["level"]))
        readers = c.execute("SELECT COUNT(*) FROM game_players").fetchone()[0]  # includes readers still building a character
        max_hp = R.boss_max_hp(expected, readers)
        hp, back = max_hp, None
        last = self._boss_row(c, year - 1)
        if last and last["status"] == "escaped":
            back = max(1, round(100 * last["hp"] / last["max_hp"]))
            hp = max(1, round(max_hp * min(1.0, last["hp"] / last["max_hp"] + R.BOSS_REGEN)))
        c.execute("INSERT OR IGNORE INTO game_boss(year, max_hp, hp, returning_pct, created_at) VALUES(?,?,?,?,?)",
                  (year, max_hp, hp, back, now))
        return self._boss_row(c, year)

    @staticmethod
    def _boss_participants(c, year: int) -> List[Tuple[str, str]]:
        return [(r[0], r[1]) for r in c.execute("SELECT user_id, MAX(username) FROM game_boss_attacks "
                                                "WHERE year=? AND finished_at IS NOT NULL AND damage > 0 GROUP BY user_id", (year,))]

    def _settle_boss(self, c, now: int) -> None:
        """Catch up on anything whose time has passed: each finished week's
        top damage badge, and the Regent escaping when December ends."""
        cal = R.boss_calendar(now)
        row = self._boss_row(c, cal["year"])
        if not row:
            return
        over = row["status"] != "active" or now >= cal["ends_at"]
        weeks = set(row["settled"].get("weeks", []))
        changed = False
        for (week,) in c.execute("SELECT DISTINCT week FROM game_boss_attacks WHERE year=? AND finished_at IS NOT NULL", (row["year"],)).fetchall():
            if week in weeks:
                continue
            start = int(time.mktime(time.strptime(week, "%Y-%m-%d")))
            if not over and now < start + 7 * 86400:
                continue
            top = c.execute("SELECT user_id, SUM(damage) d FROM game_boss_attacks WHERE year=? AND week=? AND finished_at IS NOT NULL "
                            "GROUP BY user_id ORDER BY d DESC LIMIT 1", (row["year"], week)).fetchone()
            if top and top["d"] > 0:
                self._bump(c, top["user_id"], sets={"flags": ["boss_top_week"]})
                self._check_badges(c, top["user_id"])
            weeks.add(week)
            changed = True
        if changed:
            row["settled"]["weeks"] = sorted(weeks)
            c.execute("UPDATE game_boss SET settled_json=? WHERE year=?", (json.dumps(row["settled"]), row["year"]))
        if row["status"] == "active" and now >= cal["ends_at"]:
            self._boss_escapes(c, row, now)

    def _boss_escapes(self, c, row: Dict, now: int) -> None:
        """December is over and he's still standing: he escapes, wounded.
        Everyone who fought gets a scar (badge) marked with the year and how
        close the party got; January brings the Null."""
        pct = max(1, round(100 * row["hp"] / row["max_hp"]))
        c.execute("UPDATE game_boss SET status='escaped', ended_at=? WHERE year=? AND status='active'", (now, row["year"]))
        for uid, _name in self._boss_participants(c, row["year"]):
            self._bump(c, uid, sets={"flags": ["boss_scar"], "scars": [f"{row['year']}:{pct}"]})
            self._notice(c, uid, "boss_escaped", {"year": row["year"], "pct": pct})
            self._check_badges(c, uid)
        self._feed(c, "system", R.BOSS_NAME, "boss_escaped",
                   {"text": f"escaped with {pct}% of his health. He'll be back next December, still wounded. Until then, the Null spreads."})

    def _null_state(self, c, now: int) -> Optional[Dict]:
        """January after an escape: the Null spreads (monsters stronger)
        until the party finishes enough books to cleanse it."""
        cal = R.boss_calendar(now)
        if cal["phase"] != "january":
            return None
        self._settle_boss(c, now)
        row = self._boss_row(c, cal["year"])
        if not row or row["status"] != "escaped":
            return None
        jan = cal["ends_at"]
        feb = int(time.mktime((cal["year"] + 1, 2, 1, 0, 0, 0, 0, 0, -1)))
        done = c.execute("SELECT COUNT(*) FROM game_dungeons WHERE finished_at >= ? AND finished_at < ?", (jan, feb)).fetchone()[0]
        target = R.NULL_CLEANSE_PER_PLAYER * max(2, len(self._boss_participants(c, row["year"])))
        cleansed = row["settled"].get("cleansed_at")
        if not cleansed and done >= target:
            cleansed = now
            row["settled"]["cleansed_at"] = now
            c.execute("UPDATE game_boss SET settled_json=? WHERE year=?", (json.dumps(row["settled"]), row["year"]))
            self._feed(c, "system", "The party", "null_cleansed",
                       {"text": f"finished {done} books this January and cleansed the Null. The dungeons are back to normal."})
        return {"active": not cleansed, "books": min(done, target), "target": target, "cleansed_at": cleansed, "ends_at": feb}

    def _momentum_clears(self, c, user_id: str, year: int, since: int) -> int:
        last = c.execute("SELECT MAX(finished_at) FROM game_boss_attacks WHERE year=? AND user_id=? AND finished_at IS NOT NULL",
                         (year, user_id)).fetchone()[0]
        return c.execute("SELECT COUNT(*) FROM game_dungeons WHERE user_id=? AND status='cleared' AND cleared_at > ?",
                         (user_id, max(since, last or 0))).fetchone()[0]

    def _slot_free(self, c, user_id: str, cal: Dict) -> bool:
        return not c.execute("SELECT 1 FROM game_boss_attacks WHERE user_id=? AND slot=? AND finished_at IS NOT NULL",
                             (user_id, cal["slot"])).fetchone()

    def _next_attack_at(self, c, user_id: str, cal: Dict, now: int) -> Optional[int]:
        """When this player's next attack opens (None: no more this year)."""
        year = cal["year"]
        xmas = int(time.mktime((year, 12, 25, 0, 0, 0, 0, 0, -1)))
        options = []
        if cal["slot_ends"] < cal["ends_at"]:
            options.append(cal["slot_ends"])
        if now < xmas and not c.execute("SELECT 1 FROM game_boss_attacks WHERE user_id=? AND slot=? AND finished_at IS NOT NULL",
                                        (user_id, f"{year}-xmas")).fetchone():
            options.append(xmas)
        return min(options) if options else None

    def settle_boss(self, now: Optional[float] = None) -> None:
        """Hand out anything the boss clock owes (weekly badges, the escape)
        so its notices are ready before the hub reads them."""
        with self._conn() as c:
            self._settle_boss(c, self._boss_now(now))

    def boss_state(self, user_id: str, now: Optional[float] = None) -> Dict:
        """Everything the hub's boss panel shows."""
        now = self._boss_now(now)
        cal = R.boss_calendar(now)
        with self._conn() as c:
            self._settle_boss(c, now)
            null = self._null_state(c, now)
            out = {"phase": cal["phase"], "year": cal["year"], "starts_at": cal["starts_at"], "ends_at": cal["ends_at"],
                   "now": now, "name": R.BOSS_NAME, "null": null, "turns": R.BOSS_TURNS}
            if cal["phase"] == "before":
                last = self._boss_row(c, cal["year"] - 1)
                out["last"] = {"year": last["year"], "status": last["status"], "pct": round(100 * last["hp"] / last["max_hp"])} if last else None
                return out
            row = self._ensure_boss(c, cal["year"], now) if cal["phase"] == "event" else self._boss_row(c, cal["year"])
            if not row:
                return {**out, "boss": None}
            week = R.week_key(now)
            raised = {r["kind"]: dict(r) for r in c.execute("SELECT kind, username, user_id FROM game_boss_banners WHERE year=? AND week=?",
                                                          (row["year"], week))}
            attacks = [dict(r) for r in c.execute("SELECT username, user_id, slot, damage, outcome, finished_at FROM game_boss_attacks "
                                                  "WHERE year=? AND finished_at IS NOT NULL ORDER BY finished_at DESC", (row["year"],))]
            totals: Dict[str, Dict] = {}
            for a in attacks:
                t = totals.setdefault(a["user_id"], {"username": a["username"], "damage": 0, "attacks": 0})
                t["damage"] += a["damage"]
                t["attacks"] += 1
            this_week = R.week_key(now)
            week_top = c.execute("SELECT MAX(username) u, SUM(damage) d FROM game_boss_attacks WHERE year=? AND week=? AND finished_at IS NOT NULL "
                                 "GROUP BY user_id ORDER BY d DESC LIMIT 1", (row["year"], this_week)).fetchone()
            boss = {"max_hp": row["max_hp"], "hp": row["hp"], "status": row["status"], "returning_pct": row["returning_pct"],
                    "pct": round(100 * row["hp"] / row["max_hp"], 1), "killer": row["killer"], "ended_at": row["ended_at"]}
            banners = [{"key": k, **v, "raised_by": raised[k]["username"] if k in raised else None} for k, v in R.BANNERS.items()]
            out.update(boss=boss, banners=banners, raised_one=any(r["user_id"] == user_id for r in raised.values()),
                       log=[{k: a[k] for k in ("username", "damage", "outcome", "finished_at")} | {"christmas": a["slot"].endswith("xmas")} for a in attacks[:12]],
                       board=sorted(totals.values(), key=lambda t: -t["damage"]),
                       mine=totals.get(user_id, {"damage": 0, "attacks": 0}),
                       week_top={"username": week_top["u"], "damage": week_top["d"]} if week_top else None)
            if cal["phase"] == "event" and row["status"] == "active":
                clears = self._momentum_clears(c, user_id, row["year"], cal["starts_at"])
                ready = self._slot_free(c, user_id, cal)
                out.update(slot=cal["slot"], slot_name=cal["slot_name"], ready=ready,
                           next_at=None if ready else self._next_attack_at(c, user_id, cal, now),
                           momentum={"clears": min(clears, R.BOSS_MOMENTUM_MAX), "max": R.BOSS_MOMENTUM_MAX,
                                     "bonus": round(100 * (R.momentum(clears) - 1))})
        return out

    def raise_banner(self, user_id: str, kind: str, now: Optional[float] = None) -> None:
        """Raise a boss banner: it helps everyone's attacks for the rest of
        this week. Once per banner per week; one banner per player per week."""
        if kind not in R.BANNERS:
            raise ValueError("unknown banner")
        now = self._boss_now(now)
        cal = R.boss_calendar(now)
        if cal["phase"] != "event":
            raise GameError("Banners can only be raised in December.")
        week = R.week_key(now)
        with self._conn() as c:
            row = self._ensure_boss(c, cal["year"], now)
            if row["status"] != "active":
                raise GameError("The fight is over.")
            if c.execute("SELECT 1 FROM game_boss_banners WHERE year=? AND week=? AND kind=?", (row["year"], week, kind)).fetchone():
                raise GameError("Someone already raised that banner this week.")
            if c.execute("SELECT 1 FROM game_boss_banners WHERE year=? AND week=? AND user_id=?", (row["year"], week, user_id)).fetchone():
                raise GameError("You've already raised a banner this week. Let someone else carry one.")
            p = c.execute("SELECT username FROM game_players WHERE user_id=?", (user_id,)).fetchone()
            self._spend(c, user_id, R.BANNERS[kind]["cost"])
            c.execute("INSERT INTO game_boss_banners(year, week, kind, user_id, username, raised_at) VALUES(?,?,?,?,?,?)",
                      (row["year"], week, kind, user_id, p["username"], now))
            b = R.BANNERS[kind]
            self._feed(c, user_id, p["username"], "banner", {"text": f"raised the {b['name']} for the whole party this week ({b['text'][0].lower() + b['text'][1:]} in every Regent fight)."})

    def _taunts(self, c, user_id: str, year: int) -> Dict:
        """The Regent's lines come from the player's real year of listening."""
        start = int(time.mktime((year, 1, 1, 0, 0, 0, 0, 0, -1)))
        rows = c.execute("SELECT title, hours FROM game_dungeons WHERE user_id=? AND finished_at >= ? ORDER BY hours DESC",
                         (user_id, start)).fetchall()
        return {"books": len(rows), "hours": round(sum(r["hours"] for r in rows)), "longest": rows[0]["title"] if rows else None}

    def start_boss_attack(self, user_id: str, now: Optional[float] = None) -> Dict:
        now = self._boss_now(now)
        cal = R.boss_calendar(now)
        if cal["phase"] != "event":
            raise GameError("The Null Regent wakes on December 1.")
        p = self.get_player(user_id)
        if not p["look"] or not p["cls"]:
            raise GameError("Finish building your character first.")
        with self._conn() as c:
            self._settle_boss(c, now)
            row = self._ensure_boss(c, cal["year"], now)
            if row["status"] != "active":
                raise GameError("The Null Regent has already fallen." if row["status"] == "defeated" else "He's gone. Until next December.")
            if not self._slot_free(c, user_id, cal):
                raise GameError("You've already attacked in this window.")
            c.execute("DELETE FROM game_boss_attacks WHERE user_id=? AND slot=? AND finished_at IS NULL", (user_id, cal["slot"]))
            cfg = self.run_config(user_id)
            clears = self._momentum_clears(c, user_id, row["year"], cal["starts_at"])
            raised = [r[0] for r in c.execute("SELECT kind FROM game_boss_banners WHERE year=? AND week=?", (row["year"], R.week_key(now)))]
            fx = R.banner_effects(raised)
            mult = R.momentum(clears) * fx["damage"]
            st = cfg["stats"]
            stats = {**st, "atk": round(st["atk"] * mult), "def": round(st["def"] * fx["defense"]), "potions": st["potions"] + fx["potions"],
                     "start_energy": st["energy"] if fx["full_energy"] else st.get("start_energy", 0)}
            bs = R.boss_stats(p["level"], cfg["power"]["atk"])
            attack_id = secrets.token_hex(12)
            snap = {**cfg, "stats": stats, "raid": True, "title": R.BOSS_NAME, "theme": "regent", "slot_name": cal["slot_name"],
                    "turns": R.BOSS_TURNS, "damage_mult": round(mult, 3), "banners": raised,
                    "escalate": fx["escalate"], "guard_block": R.BOSS_GUARD, "pet_hp": fx["pet_hp"],
                    "momentum": round(100 * (R.momentum(clears) - 1)), "taunts": self._taunts(c, user_id, row["year"]),
                    "boss": {"id": "null_regent", "name": R.BOSS_NAME, "role": "boss", "hp": row["hp"], "max_hp": row["max_hp"],
                             "atk": bs["atk"], "xp": bs["xp"], "moves": R.BOSS_MOVES}}
            c.execute("INSERT INTO game_boss_attacks(id, year, user_id, username, slot, week, started_at, snapshot_json) VALUES(?,?,?,?,?,?,?,?)",
                      (attack_id, row["year"], user_id, p["username"], cal["slot"], R.week_key(now), now, json.dumps(snap)))
        return {"attack_id": attack_id, **snap}

    def finish_boss_attack(self, user_id: str, attack_id: str, report: Dict, catalog: List[Dict],
                           now: Optional[float] = None, rng: Optional[random.Random] = None) -> Dict:
        now = self._boss_now(now)
        outcome = report.get("outcome")
        if outcome not in BOSS_OUTCOMES:
            raise ValueError("invalid outcome")
        with self._conn() as c:
            a = c.execute("SELECT * FROM game_boss_attacks WHERE id=? AND user_id=?", (attack_id, user_id)).fetchone()
            if not a:
                raise GameError("That attack doesn't exist.")
            if a["finished_at"]:
                raise GameError("That attack is already over.")
            if now - a["started_at"] < R.BOSS_MIN_SECONDS:
                raise GameError("That was suspiciously fast.")
            snap = json.loads(a["snapshot_json"])
            row = self._boss_row(c, a["year"])
            if row["status"] != "active":  # someone else finished him mid-fight
                c.execute("UPDATE game_boss_attacks SET finished_at=?, outcome='late', damage=0 WHERE id=?", (now, attack_id))
                return {"damage": 0, "late": True, "status": row["status"], "killer": row["killer"], "xp": 0, "bookmarks": 0,
                        "level": self.get_player(user_id)["level"], "levels_gained": 0, "badges": [], "loot": [], "hp": row["hp"], "max_hp": row["max_hp"]}
            damage = max(0, min(int(report.get("damage") or 0), R.boss_damage_cap(snap["stats"]["atk"]), row["hp"]))
            hp = row["hp"] - damage
            killed = hp <= 0
            c.execute("UPDATE game_boss SET hp=? WHERE year=?", (hp, a["year"]))
            c.execute("UPDATE game_boss_attacks SET finished_at=?, damage=?, outcome=? WHERE id=?",
                      (now, damage, "kill" if killed else outcome, attack_id))
            p = c.execute("SELECT * FROM game_players WHERE user_id=?", (user_id,)).fetchone()
            xp = int(round(snap["boss"]["xp"] * (1 + 0.03 * json.loads(p["upgrades_json"] or "{}").get("scholar", 0)))) if damage else 0
            bookmarks = R.BOSS_ATTACK_BOOKMARKS if damage else 0
            level, levels_gained = self._add_xp(c, user_id, xp, bookmarks, now)
            if damage:
                self._bump(c, user_id, {"boss_damage": damage}, sets={"flags": ["boss_hit"]})
            pct = round(100 * max(hp, 0) / row["max_hp"])
            days = max(0, (R.boss_calendar(now)["ends_at"] - now) // 86400)
            self._feed(c, user_id, p["username"], "boss_hit", {"text": (
                f"landed the killing blow on the Null Regent for {damage:,}!" if killed else
                f"hit the Null Regent for {damage:,}. {pct}% left, {days} day{'s' if days != 1 else ''} to go." if damage else
                "went after the Null Regent and didn't leave a mark.")})
            loot: List[Dict] = []
            if killed:
                c.execute("UPDATE game_boss SET status='defeated', killer=?, ended_at=? WHERE year=?", (p["username"], now, a["year"]))
                loot = self._boss_victory(c, a["year"], user_id, p["username"], catalog, rng or random.Random())
                self._settle_boss(c, now)
            if levels_gained:
                self._feed(c, user_id, p["username"], "level", {"text": f"reached level {level}."})
            badges = self._check_badges(c, user_id)
        return {"damage": damage, "killed": killed, "hp": max(hp, 0), "max_hp": row["max_hp"], "pct": pct, "xp": xp,
                "bookmarks": bookmarks + (R.BOSS_WIN_BOOKMARKS if killed else 0), "level": level, "levels_gained": levels_gained,
                "loot": loot, "badges": badges}

    def _boss_victory(self, c, year: int, killer_id: str, killer: str, catalog: List[Dict], rng: random.Random) -> List[Dict]:
        """He fell. Everyone who landed a hit gets bookmarks and a chest of at
        least BOSS_WIN_RARITY. Returns the killer's loot."""
        mine: List[Dict] = []
        for uid, _name in self._boss_participants(c, year):
            p = c.execute("SELECT upgrades_json FROM game_players WHERE user_id=?", (uid,)).fetchone()
            ups = json.loads(p["upgrades_json"] or "{}") if p else {}
            c.execute("UPDATE game_players SET bookmarks=bookmarks+? WHERE user_id=?", (R.BOSS_WIN_BOOKMARKS, uid))
            item = None
            if catalog:
                rarity = max(R.roll_rarity(R.rarity_table(True, 20, ups.get("lucky_find", 0)), rng), R.BOSS_WIN_RARITY, key=RARITY_RANK.get)
                rarity = R.upgrade_rarity(rarity, rng, ups.get("lucky_find", 0))
                raw = R.roll_item(catalog, rarity, "", rng)
                if raw:
                    item = R.item_view(raw)
                    placed = self._give_item(c, uid, item)  # stamps its level
                    item = {**item, "placed": placed}
            if uid == killer_id and item:
                mine.append(item)
            self._bump(c, uid, sets={"flags": ["boss_kill"]})
            if uid != killer_id:
                self._notice(c, uid, "boss_won", {"killer": killer, "bookmarks": R.BOSS_WIN_BOOKMARKS,
                                                   "item": {k: item[k] for k in ("name", "rarity", "slot")} if item else None})
                self._check_badges(c, uid)
        self._feed(c, "system", "The party", "boss_won",
                   {"text": f"brought down the Null Regent! {killer} landed the final blow. Everyone who fought gets a chest of {R.BOSS_WIN_RARITY} or better."})
        return mine

    def _add_xp(self, c, user_id: str, xp: int, bookmarks: int, now: int) -> Tuple[int, int]:
        """Add XP (levelling up as needed) and bookmarks. Returns (level, levels gained)."""
        p = c.execute("SELECT level, xp FROM game_players WHERE user_id=?", (user_id,)).fetchone()
        level, cur_xp, gained = p["level"], p["xp"] + xp, 0
        while cur_xp >= R.xp_to_next(level):
            cur_xp -= R.xp_to_next(level)
            level += 1
            gained += 1
        c.execute("UPDATE game_players SET level=?, xp=?, bookmarks=bookmarks+?, updated_at=? WHERE user_id=?",
                  (level, cur_xp, bookmarks, now, user_id))
        return level, gained


RARITY_RANK = {r: i for i, r in enumerate(R.RARITIES)}
