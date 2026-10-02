# -----------------------------------------
# game_rules.py — The Listening Dungeon: every tunable number, in one place
# -----------------------------------------
# Economy, class stats, enemy scaling, XP, and loot. Pure functions only (no
# database), so tests can check the math directly. Change numbers here to
# balance the game; the design reference is docs/BOOK_DUNGEON_DESIGN.md §6a.
# -----------------------------------------

import math
import random
import re
from typing import Dict, List, Optional

# ── bookmarks ─────────────────────────────────────────────────────────────
WELCOME_CHEST = 50
BOOK_FINISHED_BONUS = 25          # books finished after launch only
BM_PER_FLOOR = 2                  # each floor reached (max 3)
BM_CLEAR = 2
BM_BOSS = 3
SCRAP_VALUE = {"Common": 0, "Uncommon": 1, "Rare": 2, "Epic": 5, "Legendary": 10}
BADGE_BOOKMARKS = 10              # every badge (game_achievements.py) pays this once
LOOK_CHANGE_COST = 10             # first build free
CLASS_CHANGE_COST = 25            # first pick free


def revive_cost(hours: float) -> int:
    return 5 + int(max(0.0, hours) // 5)


# ── the Bindery: permanent upgrades. Most have 10 ranks where rank r costs
# 5·r; an entry can set its own "max" and "costs". ──────────────────────────
BINDERY = {
    "thick_skin": {"name": "Thick Skin", "text": "+5 max health per rank"},
    "whetstone": {"name": "Whetstone", "text": "+1 attack per rank"},
    "iron_hide": {"name": "Iron Hide", "text": "+1 defense per rank"},
    "scholar": {"name": "Scholar", "text": "+3% XP from dungeons per rank"},
    "lucky_find": {"name": "Lucky Find", "text": "Better loot rarity odds"},
    "field_medic": {"name": "Field Medic", "text": "+4% potion healing per rank; +1 starting potion at ranks 5 and 10"},
    # Never a full bar (2026-09-30): a full bar meant a special on turn one, every fight.
    # Level gates and real prices (owner, 2026-09-30: "too powerful to get that easy").
    "battle_ready": {"name": "Battle Ready", "text": "Start every fight with +1 energy per rank, up to one short of your class's full bar",
                     "max": 4, "costs": [100, 250, 500, 800], "levels": [5, 15, 30, 45]},
}
BINDERY_MAX_RANK = 10


def bindery_max(key: str) -> int:
    return BINDERY[key].get("max", BINDERY_MAX_RANK)


def bindery_level(next_rank: int, key: str = "") -> int:
    """The player level a rank needs (1 = none)."""
    levels = BINDERY.get(key, {}).get("levels")
    return levels[next_rank - 1] if levels else 1


FORGE_RANK_PRICE = 12   # rank r costs 12·r (was 5·r): the Forge should take a long time to finish (owner, 2026-10-01)


def bindery_cost(next_rank: int, key: str = "") -> int:
    costs = BINDERY.get(key, {}).get("costs")
    return costs[next_rank - 1] if costs else FORGE_RANK_PRICE * next_rank


BAG_BASE = 12
BAG_UPGRADE_COSTS = [40, 80, 120]  # each adds 4 slots
BAG_PER_UPGRADE = 4


def bag_capacity(bag_rank: int) -> int:
    return BAG_BASE + BAG_PER_UPGRADE * max(0, min(bag_rank, len(BAG_UPGRADE_COSTS)))


# ── classes ───────────────────────────────────────────────────────────────
CLASS_STATS = {
    "brawler":     {"hp": 72, "atk": 10, "def": 4, "grow": (13, 3.0, 1.0), "energy": 3, "crit": 0.12},
    "runeblade":   {"hp": 62, "atk": 10, "def": 3, "grow": (11, 3.0, 1.0), "energy": 5, "crit": 0.10},
    "hexcaster":   {"hp": 52, "atk": 12, "def": 2, "grow": (9, 3.5, 1.0), "energy": 3, "crit": 0.10},
    "ranger":      {"hp": 56, "atk": 11, "def": 3, "grow": (10, 3.0, 1.0), "energy": 4, "crit": 0.25},  # Volley: an arrow per energy
    "paladin":     {"hp": 66, "atk": 9, "def": 5, "grow": (12, 2.5, 1.5), "energy": 3, "crit": 0.10},
    "beastmaster": {"hp": 60, "atk": 9, "def": 3, "grow": (11, 2.5, 1.0), "energy": 3, "crit": 0.10},
    "necromancer": {"hp": 54, "atk": 7, "def": 3, "grow": (10, 2.0, 1.0), "energy": 4, "crit": 0.08},
}
# Necromancer minions cost different amounts of energy (Raise Dead menu).
RAISE_COSTS = {"skeleton": 2, "ghoul": 3, "wraith": 4}
SLOTS = ["Weapon", "Head", "Chest", "Neck", "Ring", "Trinket"]


def xp_to_next(level: int) -> int:
    return 40 * level + 10 * level * level


def gear_bonus(items: List[Dict]) -> Dict[str, int]:
    b = {"hp": 0, "atk": 0, "def": 0}
    for it in items:
        b["atk"] += round((it.get("str", 0) + it.get("mag", 0)) / 8)
        b["def"] += round(it.get("def", 0) / 6)
        b["hp"] += round(it.get("hp", 0) / 2)
    return b


def player_stats(cls: str, level: int, equipped: List[Dict], upgrades: Dict[str, int]) -> Dict:
    """`equipped` holds item_view() dicts, which already carry game stats."""
    c = CLASS_STATS.get(cls) or CLASS_STATS["brawler"]
    g = {k: sum(int(it.get(k, 0)) for it in equipped) for k in ("hp", "atk", "def")}
    L = max(1, level) - 1
    medic = upgrades.get("field_medic", 0)
    return {
        "hp": round(c["hp"] + c["grow"][0] * L + g["hp"] + 5 * upgrades.get("thick_skin", 0)),
        "atk": round(c["atk"] + c["grow"][1] * L + g["atk"] + upgrades.get("whetstone", 0)),
        "def": round(c["def"] + c["grow"][2] * L + g["def"] + upgrades.get("iron_hide", 0)),
        "energy": c["energy"],
        "crit": c["crit"],
        # never a full bar (specials need a strike first), and only the ranks your level has unlocked
        "start_energy": min(c["energy"] - 1, upgrades.get("battle_ready", 0), sum(1 for lv in BINDERY["battle_ready"]["levels"] if level >= lv)),
        "potions": 2 + (1 if medic >= 5 else 0) + (1 if medic >= 10 else 0),
        "potion_heal": round(0.45 * (1 + 0.04 * medic), 3),
    }


# ── dungeons and enemies ──────────────────────────────────────────────────
# Practice mode: a random dungeon with no rewards. Enemies scale as if the
# player were this many levels higher (or lower).
PRACTICE_DIFFICULTY = {
    "easy": {"name": "Easy", "levels": -3, "mult": 0.8},
    "normal": {"name": "Normal", "levels": 0},
    "hard": {"name": "Hard", "levels": 5},
    "brutal": {"name": "Brutal", "levels": 12},
}


def practice_scale(level: int, difficulty: str) -> Dict[str, float]:
    d = PRACTICE_DIFFICULTY[difficulty]
    s = enemy_scale(level + d["levels"])
    m = d.get("mult", 1.0)
    return {**s, "hp": round(s["hp"] * m, 3), "atk": round(s["atk"] * m, 3)}

FLOORS = [3, 3, 2]          # rooms per floor; then boss-or-stairs
MAX_KILLS = sum(FLOORS)     # at most one fight per room
MIN_RUN_SECONDS = 8         # a finish sooner than this is rejected (no human clears 9 rooms this fast)


def enemy_scale(level: int) -> Dict[str, float]:
    """Enemies grow with the player so a fight stays ~4–6 turns at any level."""
    L = max(1, level) - 1
    return {"hp": round(1 + 0.13 * L, 3), "atk": round(1 + 0.11 * L, 3), "xp": round(1 + 0.08 * L, 3)}


# Monsters also grow with your POWER, not just your level (2026-09-30: gear
# and the Forge made early fights trivial). Power = your real Attack compared
# with a bare crawler of your class and level; monsters make up POWER_SCALE of
# that gap in health, and POWER_SCALE_ATK of it in attack.
# Only your attack counts (owner, 2026-10-01). It used to be that their attack
# followed your health, which made health gear backfire: each point raised
# their hits more than it helped. Now health and defense make you tankier and
# attack makes fights faster but hit back harder, which is a real choice.
POWER_SCALE = 0.75   # raised from 0.6 (owner, 2026-10-01): a careful player still beat 99% of floor bosses
POWER_SCALE_ATK = 0.75


def power_factors(cls: str, level: int, stats: Dict) -> Dict[str, float]:
    """Extra enemy multipliers for a player's gear and upgrades. Both follow
    your attack: their health so fights keep a few turns, their attack so a
    glass cannon still gets hit hard. Your health and defense don't scale them."""
    bare = player_stats(cls, level, [], {})
    off = stats["atk"] / max(1, bare["atk"])
    return {"hp": round(max(1.0, 1 + POWER_SCALE * (off - 1)), 3), "atk": round(max(1.0, 1 + POWER_SCALE_ATK * (off - 1)), 3)}


def with_power(scale: Dict[str, float], factors: Dict[str, float]) -> Dict[str, float]:
    return {**scale, "hp": round(scale["hp"] * factors["hp"], 3), "atk": round(scale["atk"] * factors["atk"], 3)}


# ── Best gear (the bag's Best button) ─────────────────────────────────────
# A loadout is scored by how a fight would go: how hard you hit, times how
# many hits you can take (defense knocks half its value off every hit).
# Same stats, different classes, different answers: a frail Hexcaster gets
# more from health, a sturdy Paladin more from defense. Pet classes lean
# further toward health because their pets' health is a share of yours.
# The monster's hit is the one you face now (it grows with your current
# attack) and is held there while loadouts are compared. Defense can block at
# most 80% of a hit, so it can't look priceless just because one ordinary
# monster barely scratches you.
BEST_FOE_ATK = 7 * 1.2 * 1.1          # a regular monster's hit on the middle floor
BEST_PET_HP_WEIGHT = {"beastmaster": 1.25, "necromancer": 1.25}


def best_foe_hit(cls: str, level: int, upgrades: Dict[str, int], worn: List[Dict]) -> float:
    pf = power_factors(cls, level, player_stats(cls, level, worn, upgrades))
    return BEST_FOE_ATK * enemy_scale(level)["atk"] * pf["atk"]


def loadout_score(cls: str, level: int, upgrades: Dict[str, int], gear: List[Dict], foe_hit: Optional[float] = None) -> float:
    c = CLASS_STATS.get(cls) or CLASS_STATS["brawler"]
    L = max(1, level) - 1
    g = {k: sum(float(it.get(k, 0) or 0) for it in gear) for k in ("hp", "atk", "def")}
    hp = c["hp"] + c["grow"][0] * L + g["hp"] + 5 * upgrades.get("thick_skin", 0)
    atk = c["atk"] + c["grow"][1] * L + g["atk"] + upgrades.get("whetstone", 0)
    dfn = c["def"] + c["grow"][2] * L + g["def"] + upgrades.get("iron_hide", 0)
    foe = foe_hit if foe_hit is not None else BEST_FOE_ATK * enemy_scale(level)["atk"]
    hit = max(0.2 * foe, foe - 0.5 * dfn)
    return atk * (hp / hit) ** BEST_PET_HP_WEIGHT.get(cls, 1.0)


def better_than_worn(cls: str, level: int, upgrades: Dict[str, int], worn: Dict[str, Dict], bag: List[Dict]) -> List[int]:
    """Ids of bag items that would improve your loadout if swapped in alone
    (the bag's ▲ marker; same judgement as the Best button)."""
    gear = list(worn.values())
    foe = best_foe_hit(cls, level, upgrades, gear)
    now = loadout_score(cls, level, upgrades, gear, foe)
    return [it["id"] for it in bag
            if loadout_score(cls, level, upgrades, [w for s, w in worn.items() if s != it["slot"]] + [it], foe) > now + 1e-9]


def best_loadout(cls: str, level: int, upgrades: Dict[str, int], items: List[Dict]) -> Dict[str, Optional[Dict]]:
    """The best item per slot from `items` (worn and bag together). Slots
    affect each other through the score, so pick slot by slot and repeat
    until nothing improves. Starts from what's worn, so ties keep it."""
    by_slot: Dict[str, List[Dict]] = {s: [] for s in SLOTS}
    for it in items:
        by_slot.setdefault(it["slot"], []).append(it)
    pick = {s: next((it for it in by_slot[s] if it.get("equipped_slot")), None) for s in by_slot}
    foe = best_foe_hit(cls, level, upgrades, [it for it in pick.values() if it])
    score = lambda p: loadout_score(cls, level, upgrades, [it for it in p.values() if it], foe)
    best = score(pick)
    for _ in range(6):
        changed = False
        for s, options in by_slot.items():
            for it in options:
                if it is pick[s]:
                    continue
                trial = score({**pick, s: it})
                if trial > best + 1e-9:
                    pick, best, changed = {**pick, s: it}, trial, True
        if not changed:
            break
    return pick


def enemy_tier(level: int) -> int:
    """Levels 1–9 → tier 1, 10–19 → tier 2, … up to tier 5 (40+)."""
    return min(5, 1 + max(1, level) // 10)


BASE_XP = {"regular": 22, "elite": 50, "boss": 140}


def run_xp(level: int, kills: int, elites: int, boss: bool, floors: int, cleared: bool, hours: float,
           scholar_rank: int, died: bool) -> int:
    """Server-side XP for a finished run, from what the player reports.
    Floor multiplier matches the client (deeper floors pay more)."""
    s = enemy_scale(level)["xp"]
    regular = max(0, kills - elites)
    avg_floor_mult = 1 + 0.5 * max(0, min(floors, 3) - 1) / 2
    xp = (regular * BASE_XP["regular"] + elites * BASE_XP["elite"]) * avg_floor_mult * s
    if boss:
        xp += BASE_XP["boss"] * s
    if cleared:
        xp += hours * 10
    xp *= 1 + 0.03 * scholar_rank
    if died:
        xp /= 2
    return int(round(xp))


def run_bookmarks(floors: int, cleared: bool, boss: bool) -> int:
    return BM_PER_FLOOR * max(0, min(floors, 3)) + (BM_CLEAR if cleared else 0) + (BM_BOSS if boss else 0)


# ── series finales ────────────────────────────────────────────────────────
# Catching up on a series pays once: the first time a player has cleared every
# numbered book (1..N) that the library has, the chest is at least Epic. If
# new books arrive later and they catch up again, the chest is at least Rare
# ("Caught Up"). Only series of SERIES_FINALE_MIN_BOOKS+ whole-numbered books
# with no gaps in the library get the chest; novellas (#1.5) don't count or block.
# Every finished series of SERIES_COMPLETE_MIN_BOOKS+ books also pays bookmarks
# per book and gets a popup (owner, 2026-10-01); catching up again pays for
# the new books only.
SERIES_FINALE_MIN_BOOKS = 5
SERIES_COMPLETE_MIN_BOOKS = 2
SERIES_BOOKMARKS_PER_BOOK = 5
SERIES_REWARD_FLOOR = {"finale": "Epic", "caught_up": "Rare"}
_SERIES_RE = re.compile(r"(.+?) #(\d+(?:\.\d+)?)(?:, |$)")


def series_key(name: str) -> str:
    return " ".join((name or "").lower().split())


def parse_series(series_name: str) -> List[tuple]:
    """"Ark Royal #4, Warspite #1" -> [("ark royal", "Ark Royal", 4.0), ("warspite", "Warspite", 1.0)]."""
    return [(series_key(n), n.strip(), float(q)) for n, q in _SERIES_RE.findall(series_name or "") if n.strip()]


def build_series_index(items) -> tuple:
    """From library items ({libraryItemId, seriesName}): (index, item_series).
    index[key] = {name, books: {n: [item_ids]}, count: N, complete_ok, qualifies}
    (complete_ok: books 1..N with no gaps, at least 2; qualifies: and 5+, for the chest)
    item_series[item_id] = [(key, n)] for whole-numbered memberships."""
    index: Dict[str, Dict] = {}
    item_series: Dict[str, List[tuple]] = {}
    for it in items:
        iid = str(it.get("libraryItemId") or "")
        for key, name, seq in parse_series(it.get("seriesName") or ""):
            if seq < 1 or seq != int(seq):
                continue  # novellas and prequels (#0.5, #1.5) are optional
            entry = index.setdefault(key, {"name": name, "books": {}})
            entry["books"].setdefault(int(seq), []).append(iid)
            item_series.setdefault(iid, []).append((key, int(seq)))
    for entry in index.values():
        nums = sorted(entry["books"])
        entry["count"] = nums[-1] if nums else 0
        whole = bool(nums) and nums == list(range(1, nums[-1] + 1))
        entry["complete_ok"] = whole and len(nums) >= SERIES_COMPLETE_MIN_BOOKS
        entry["qualifies"] = whole and len(nums) >= SERIES_FINALE_MIN_BOOKS
    return index, item_series


def series_bookmarks(entry: Dict, rewarded_books: Optional[int]) -> int:
    """Bookmarks for finishing a series: per book, or per new book when catching up."""
    return SERIES_BOOKMARKS_PER_BOOK * max(0, entry["count"] - (rewarded_books or 0))


def series_outcome(entry: Dict, cleared_ids: set, rewarded_books: Optional[int]) -> Optional[str]:
    """"finale", "caught_up" or None for a player whose cleared dungeons are
    `cleared_ids`; `rewarded_books` is the book count at their last reward."""
    if not entry or not entry["complete_ok"]:
        return None
    if not all(any(i in cleared_ids for i in entry["books"][n]) for n in range(1, entry["count"] + 1)):
        return None
    if rewarded_books is None:
        return "finale"
    return "caught_up" if entry["count"] > rewarded_books else None


# ── dungeon looks from the book's genre (look only, never difficulty) ─────
# Tags come from the series tags used by Recommendations (Audible categories,
# description keywords, Royal Road) plus the book's Audiobookshelf genres.
# Audible categories are noisy (plain fantasy gets "Paranormal & Urban" or
# "Science Fiction"), so a theme needs at least one STRONG keyword; weak
# keywords only add to the score. No strong match: the classic stone dungeon.
THEMES = {
    "dungeon": {"name": "Stone Halls", "strong": [], "weak": []},
    "digital": {"name": "Glitched Server", "strong": ["vrmmo", "virtual reality", "gamelit", "mmorpg", "full dive"], "weak": ["video game", "game world"]},
    "sect": {"name": "Mountain Sect", "strong": ["cultivat", "xianxia", "wuxia", "martial arts"], "weak": ["eastern", "sect"]},
    "ruins": {"name": "Ruined City", "strong": ["apocalyp", "zombie", "dystopia", "wasteland"], "weak": ["survival"]},
    "crypt": {"name": "Haunted Crypt", "strong": ["horror", "undead", "necromanc", "vampire", "gothic"], "weak": ["dark fantasy", "ghost"]},
    "station": {"name": "Derelict Station", "strong": ["space opera", "space exploration", "starship", "alien", "first contact", "galactic", "mech"],
                "weak": ["science fiction", "sci-fi", "scifi", "military"]},
    "city": {"name": "Night City", "strong": ["urban fantasy", "private investigator", "cyberpunk", "contemporary fantasy"],
             "weak": ["urban", "paranormal", "contemporary", "supernatural"]},
    "academy": {"name": "Arcane Academy", "strong": ["magic academy", "magic school", "academy", "school", "university"], "weak": ["wizard", "mage"]},
    "wilds": {"name": "Wild Frontier", "strong": ["wilderness", "monster tamer", "tamer", "beast taming"], "weak": ["dragon", "mythical creature", "beast", "survival"]},
}
THEME_ORDER = ["digital", "sect", "ruins", "crypt", "station", "city", "academy", "wilds"]  # ties: most specific first
# Shelf-wide categories that say nothing about the setting.
GENERIC_GENRES = {"science fiction & fantasy", "literature & fiction", "audiobook", "fantasy", "action & adventure", "epic",
                  "genre fiction", "teen & young adult", "adventure", "litrpg", "fiction", "themes & styles"}


# Series with their own look (static/game/dungeon-themes.js SERIES): the
# series the family has finished. They override the genre look.
SERIES_LOOKS = {
    "he who fights with monsters": "hwfwm",
    "dungeon crawler carl": "dcc",
    "the primal hunter": "primal",
    "system universe series": "sysuni",
    "system universe": "sysuni",
    "the infinite world": "infinite",
    "the perfect run": "perfectrun",
    "the ripple system": "ripple",
    "tower of jack": "towerjack",
    "art of the adept": "adept",
    "azarinth healer": "azarinth",
    # Round 2: series one reader has finished (no boss nicknames)
    "a soldier's life": "soldier",
    "ajax's ascension": "ajax",
    "battleforged": "battleforged",
    "benjamin ashwood series": "ashwood",
    "beware of chicken": "chicken",
    "book of the dead": "bookdead",
    "chaos seeds": "chaos",
    "cradle": "cradle",
    "descend": "descend",
    "discount dan's backroom bargains": "discountdan",
    "dragonlance chronicles": "dlchronicles",
    "legends": "dllegends",
    "war of souls": "dlwar",
    "dual class": "dualclass",
    "endless online series": "endless",
    "full murderhobo": "murderhobo",
    "healer's way": "healersway",
    "how i built a magic empire": "magicempire",
    "i'm not the hero": "nothero",
    "instrument of omens": "omens",
    "lost fleet": "lostfleet",
    "mark of the fool": "fool",
    "mimic & me": "mimic",
    "noobtown": "noobtown",
    "path of the berserker": "berserker",
    "savage awakening": "savage",
    "the dark healer": "darkhealer",
    "the hedge wizard": "hedgewizard",
    "the lord of the rings": "lotr",
    "the path of ascension": "ascension",
    "welcome to the multiverse": "multiverse",
    # S-tier favorites from the family's tier lists (2026-09-29)
    "mana runners": "manarunners",
    "kingkiller chronicle": "kingkiller",
    "ready player one": "rpo",
}


def series_look(series_name: str) -> Optional[str]:
    for key, _name, _seq in parse_series(series_name):
        if key in SERIES_LOOKS:
            return SERIES_LOOKS[key]
    key = series_key(series_name)
    return SERIES_LOOKS.get(key)


def pick_theme(tags) -> str:
    """The dungeon look for a book from its genre tags."""
    parts = set()
    for t in tags or []:
        for piece in re.split(r"[:,>/]", str(t).lower()):
            piece = " ".join(piece.split())
            if piece and piece not in GENERIC_GENRES:
                parts.add(piece)
    best, best_score = "dungeon", 0.0
    for key in THEME_ORDER:
        th = THEMES[key]
        strong = sum(1 for p in parts if any(w in p for w in th["strong"]))
        if not strong:
            continue
        score = strong + 0.5 * sum(1 for p in parts if any(w in p for w in th["weak"]))
        if score > best_score:
            best, best_score = key, score
    return best


# ── loot ──────────────────────────────────────────────────────────────────
RARITIES = ["Common", "Uncommon", "Rare", "Epic", "Legendary"]


def chest_count(hours: float) -> int:
    return 2 if hours >= 20 else 1


def rarity_table(boss: bool, hours: float, lucky_rank: int) -> Dict[str, float]:
    # Legendary is never rolled directly (owner, 2026-09-30): an Epic may
    # upgrade to one (upgrade_rarity). Longer books push odds toward Epic.
    if boss:
        t = {"Uncommon": 20, "Rare": 50, "Epic": 30}
    else:
        t = {"Common": 35, "Uncommon": 55, "Rare": 10}
    # Longer books shift weight toward better rarities.
    shift = (6 if hours >= 6 else 0) + (6 if hours >= 12 else 0) + 2 * lucky_rank
    if shift:
        order = [r for r in RARITIES if r in t]
        low, high = order[0], order[-1]
        moved = min(shift, t[low] - 1)
        t[low] -= moved
        t[high] += moved
    if hours >= 20:  # long books guarantee Rare or better
        t = {k: v for k, v in t.items() if RARITIES.index(k) >= 2} or {"Rare": 1}
    return t


LEGENDARY_CHANCE = 0.10          # an Epic drop becomes Legendary this often...
LEGENDARY_PER_LUCKY = 0.0        # Lucky Find no longer helps here (owner, 2026-10-01: ~15 Legendaries per 350 drops)


def upgrade_rarity(rarity: str, rng: random.Random, lucky_rank: int = 0) -> str:
    """Every Epic about to drop rolls for an upgrade to Legendary."""
    if rarity == "Epic" and rng.random() < LEGENDARY_CHANCE + LEGENDARY_PER_LUCKY * lucky_rank:
        return "Legendary"
    return rarity


def roll_rarity(table: Dict[str, float], rng: random.Random) -> str:
    r = rng.random() * sum(table.values())
    for k, v in table.items():
        r -= v
        if r < 0:
            return k
    return next(iter(table))


def roll_item(catalog: List[Dict], rarity: str, series: str, rng: random.Random) -> Optional[Dict]:
    """Pick a catalog item of `rarity`, preferring gear tagged with the book's series."""
    pool = [i for i in catalog if i["rarity"] == rarity]
    if not pool:
        return None
    key = (series or "").split("#")[0].strip().lower()
    themed = [i for i in pool if key and i.get("series_tag", "").strip().lower() and i["series_tag"].strip().lower() in key]
    return rng.choice(themed if themed and rng.random() < 0.6 else pool)


# Item level (2026-09-30): gear is stamped with the player's level when they
# get it, and its stats scale with that level. An early Legendary is exciting
# but won't carry you at 50; a level-50 Common roughly matches a level-7
# Legendary. The catalog's numbers are the base; ITEM_LEVEL_* sets the curve.
ITEM_LEVEL_BASE = 0.4
ITEM_LEVEL_STEP = 0.12


def item_level_mult(ilvl: int) -> float:
    return ITEM_LEVEL_BASE + ITEM_LEVEL_STEP * max(1, ilvl)


def stamp_item(item: Dict, level: int) -> Dict:
    """Give an item its level (in place) and scale its stats. Already-stamped items are left alone."""
    if item.get("ilvl"):
        return item
    m = item_level_mult(level)
    base = {k: item.get(k, 0) for k in ("atk", "def", "hp")}
    item.update({"ilvl": max(1, level), "base_atk": base["atk"], "base_def": base["def"], "base_hp": base["hp"],
                 **{k: int(round(v * m)) for k, v in base.items()}})
    return item


def item_view(raw: Dict) -> Dict:
    """The shape stored in the bag: catalog fields plus game stats."""
    g = gear_bonus([raw])
    return {
        "catalog_id": raw["item_id"], "name": raw["item_name"], "slot": raw["slot"], "rarity": raw["rarity"],
        "str": raw.get("str", 0), "mag": raw.get("mag", 0), "def_raw": raw.get("def", 0), "hp_raw": raw.get("hp", 0),
        "atk": g["atk"], "def": g["def"], "hp": g["hp"],
        "flavor": raw.get("flavor_text", ""), "series": raw.get("series_tag", ""), "icon": raw.get("icon", ""),
    }


# ── cosmetics (the Wardrobe): looks only, no stats ────────────────────────
# Drawing details live in the front end (crawler-art.js capes, dungeon.js
# pet skins, hub.js nameplate colors); the server only knows names and prices.
COSMETICS = {
    "title": {
        "bookworm": {"name": "the Bookworm", "cost": 8},
        "page_turner": {"name": "the Page-Turner", "cost": 8},
        "night_listener": {"name": "the Night Listener", "cost": 10},
        "speed_reader": {"name": "the Speed Reader", "cost": 10},
        "unspoiled": {"name": "the Unspoiled", "cost": 12},
        "narrators_favorite": {"name": "Narrator's Favorite", "cost": 12},
        "dungeon_critic": {"name": "the Dungeon Critic", "cost": 15},
        "legend": {"name": "Legend of the Stacks", "cost": 20},
    },
    "plate": {
        "red": {"name": "Stamp Red", "cost": 8}, "mustard": {"name": "Mustard", "cost": 8},
        "navy": {"name": "Midnight Navy", "cost": 8}, "forest": {"name": "Forest", "cost": 8},
        "royal": {"name": "Royal Purple", "cost": 8}, "ink": {"name": "Ink Black", "cost": 8},
    },
    "cape": {
        "plain": {"name": "Plain Cape", "cost": 10}, "stripes": {"name": "Striped Cape", "cost": 10},
        "stars": {"name": "Starry Cape", "cost": 10}, "checks": {"name": "Checkered Cape", "cost": 10},
        "flames": {"name": "Flame Cape", "cost": 10},
    },
    "pet": {
        "frost": {"name": "Frost Pack", "cost": 15, "cls": "beastmaster"},
        "shadow": {"name": "Shadow Pack", "cost": 15, "cls": "beastmaster"},
        "golden": {"name": "Golden Pack", "cost": 15, "cls": "beastmaster"},
        "spectral": {"name": "Spectral Legion", "cost": 15, "cls": "necromancer"},
        "crimson": {"name": "Crimson Legion", "cost": 15, "cls": "necromancer"},
    },
}
COSMETIC_KINDS = {"title": "Titles", "plate": "Nameplate colors", "cape": "Capes", "pet": "Pet skins"}


# ── the System Store (unlocks after STORE_UNLOCK_CLEARS cleared dungeons) ──
STORE_UNLOCK_CLEARS = 10
# Daily and shared (owner, 2026-10-01): restocks at midnight (server time, the
# container's TZ); each piece can be bought once, by anyone, first come first
# served. The last slot is an Epic, or on a rare day a Legendary priced so high
# that buying one is a real decision.
STORE_STOCK = ["Rare", "Rare", "Epic", "Epic", "Epic"]   # one of each slot below, daily
STORE_LEGENDARY_CHANCE = 1 / 365   # the last Epic becomes a Legendary: about once a year
STORE_PRICES = {"Rare": 30, "Epic": 60, "Legendary": 250}
STORE_BOOST = 1.15   # store gear is a sponsored, slightly stronger version of catalog gear
STORE_PREFIXES = ["Sponsored", "Limited-Edition", "System-Certified", "Collector's", "Premium", "Crowd-Favorite"]
CRATE_COST = 15
CRATE_TABLE = {"Common": 30, "Uncommon": 35, "Rare": 22, "Epic": 13}   # Epics may still upgrade to Legendary

# Supplies: packed automatically when entering a dungeon; unused ones come back.
SUPPLIES = {
    "potion": {"name": "Extra Potion", "cost": 3, "text": "+1 potion in your next dungeon"},
    "lantern": {"name": "Lantern", "cost": 4, "text": "On one floor, see exactly what's behind both doors"},
    "smoke": {"name": "Smoke Bomb", "cost": 5, "text": "Escape one fight (not the boss). No kill, no XP, but you live"},
    "coin": {"name": "Lucky Coin", "cost": 6, "text": "Your next chest rolls twice and you keep the better one"},
}
SUPPLY_CARRY = 3


def week_start(now: float) -> int:
    """Midnight (server local time) of the Monday that starts `now`'s week."""
    import time as _t
    lt = _t.localtime(now)
    midnight = _t.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))
    return int(midnight - lt.tm_wday * 86400) if lt.tm_wday else int(midnight)


def week_key(now: float) -> str:
    import time as _t
    return _t.strftime("%Y-%m-%d", _t.localtime(week_start(now) + 3600))


def day_start(now: float) -> int:
    """Midnight (server local time) that starts `now`'s day."""
    import time as _t
    lt = _t.localtime(now)
    return int(_t.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1)))


def day_key(now: float) -> str:
    import time as _t
    return _t.strftime("%Y-%m-%d", _t.localtime(day_start(now) + 3600))


def next_day_start(now: float) -> int:
    return day_start(day_start(now) + 36 * 3600)   # safe across daylight-saving changes


def store_stock(key: str, catalog: List[Dict]) -> List[Dict]:
    """The day's store gear: the same for everyone, different every day."""
    rng = random.Random(f"store:{key}")
    slots = rng.sample(SLOTS, len(STORE_STOCK))
    rarities = list(STORE_STOCK)
    if rng.random() < STORE_LEGENDARY_CHANCE:
        rarities[-1] = "Legendary"
    out = []
    for i, (rarity, slot) in enumerate(zip(rarities, slots)):
        pool = [c for c in catalog if c["rarity"] == rarity and c["slot"] == slot] or [c for c in catalog if c["rarity"] == rarity]
        if not pool:
            continue
        base = rng.choice(pool)
        boosted = {**base, **{k: int(round(base.get(k, 0) * STORE_BOOST)) for k in ("str", "mag", "def", "hp")}}
        item = item_view(boosted)
        item.update({"name": f"{rng.choice(STORE_PREFIXES)} {base['item_name']}", "store_only": True,
                     "flavor": "Sold exclusively by the System. No refunds.", "catalog_id": f"store:{key}:{i}"})
        out.append({"idx": i, "price": STORE_PRICES[rarity], "item": item})
    return out


# ── the Arena: ghost duels and the ladder (owner, 2026-10-02) ─────────────
# Challenge any crawler and fight their ghost: their real stats, gear and
# look, played by the System with a move script for their class. Real stats
# on purpose (a friendly league, but bragging rights matter). Beat someone
# ranked above you on the ladder and you swap places. Whoever is #1 when a
# month ends is that month's Arena Champion.
DUEL_DAILY_LIMIT = 3          # challenges a crawler can start per day (midnight server time)
DUEL_WIN_BOOKMARKS = 5        # the challenger, for winning
DUEL_DEFEND_BOOKMARKS = 2     # the defender, when their ghost wins
DUEL_TURNS = 30               # then it's decided on health left (as a % of full)
DUEL_MIN_SECONDS = 6          # a finish sooner than this is rejected
GIANT_SLAYER_LEVELS = 10      # beat a crawler this many levels above you
# Weekly prizes (owner, 2026-10-02), settled after Sunday midnight:
# - #1 on the ladder gets an Epic at their level (10% Legendary, like any Epic),
#   but only if they started at least one duel that week;
# - whoever won the most duels that week (if not that #1) gets a Rare.
ARENA_WEEK_CHAMPION_RARITY = "Epic"
ARENA_WEEK_CLIMBER_RARITY = "Rare"
# The ghost's moves, in order, using the monster moves the fight already knows,
# renamed for each class. "quaff" (drink a potion) is added by the fight when
# the ghost is low and still has potions.
GHOST_MOVES = {
    "brawler": (["attack", "heavy", "attack", "windup", "slam"], {"heavy": "Body Blow", "windup": "Haymaker"}),
    "paladin": (["attack", "shield", "drain", "attack", "heavy"], {"shield": "Raises a holy shield", "drain": "Smite", "heavy": "Holy Strike"}),
    "runeblade": (["attack", "attack", "windup", "slam"], {"windup": "Overcharge"}),
    "hexcaster": (["poison", "attack", "weaken", "drain"], {"poison": "Hex", "weaken": "Wither", "drain": "Soul Drain"}),
    "ranger": (["attack", "frenzy", "attack", "heavy"], {"frenzy": "Volley", "heavy": "Aimed Shot"}),
    "beastmaster": (["attack", "frenzy", "heavy", "attack"], {"frenzy": "Pack Attack", "heavy": "Bear Maul"}),
    "necromancer": (["drain", "poison", "attack", "frenzy"], {"drain": "Soul Siphon", "poison": "Grave Rot", "frenzy": "Skeleton Swarm"}),
}


def duel_winner(outcome: str, my_pct: float, ghost_pct: float) -> bool:
    """Did the challenger win? A fight that hits the turn limit goes to whoever has more health left."""
    if outcome == "win":
        return True
    if outcome == "time":
        return my_pct > ghost_pct
    return False


# ── the December boss: the Null Regent (docs/BOOK_DUNGEON_DESIGN.md §7) ────
# One shared health bar for the whole party, all December. Each player gets
# one attack per week (Monday to Sunday; week 1 starts Dec 1) plus one on
# Christmas Day, which never shares a day with the weekly attack. An attack is
# one long fight: deal as much damage as you can before you fall or the turn
# limit ends it. The phone plays it; the server caps what it will believe.
BOSS_NAME = "The Null Regent"
# Retuned 2026-09-30 (owner: "he's supposed to be hard"): every attack is a
# fight to the death. He hits harder every turn, his Cascade Failure hits you
# and every pet at once, System Wipe can't be guarded, and guarding only
# halves his hits. BOSS_TURNS is only a safety stop.
BOSS_TURNS = 50                  # safety stop; fights end when you fall
BOSS_ATK = 1.2                   # his opening hits vs. a floor boss at your level
BOSS_ESCALATE = 0.10             # +10% to his hits every turn (sim: ~6–12 turns to fall without gear)
BOSS_GUARD = 0.5                 # guarding blocks half (a normal guard blocks 70%)
BOSS_MOVES = ["attack", "cascade", "heavy", "purge", "attack", "wipe", "windup", "cascade", "frenzy", "attack"]
BOSS_SLOTS = 6                   # weekly attacks in a December (5 windows) + Christmas
BOSS_HP_SHARE = 0.8              # full health = 80% of every possible attack at today's strength
BOSS_MIN_PARTY = 4               # size him for at least this many crawlers (readers still building count at the party average)
BOSS_MIN_HP = 2000
BOSS_REGEN = 0.25                # he escaped: next December he's back with what he had left + 25%
BOSS_MOMENTUM = 0.05             # +5% damage per dungeon cleared since your last attack...
BOSS_MOMENTUM_MAX = 6            # ...counting up to 6 dungeons (+30%)
BOSS_ATTACK_BOOKMARKS = 5
BOSS_WIN_BOOKMARKS = 50          # everyone who landed a hit, when he falls
BOSS_WIN_RARITY = "Epic"         # ...plus a chest at least this good
BOSS_MIN_SECONDS = 8               # like MIN_RUN_SECONDS: a hard boss can end a fight quickly
# Boss banners: December only, never in the Store. One player raises a banner
# and it helps the WHOLE party's attacks for the rest of that week (the
# Christmas attack counts in its week). Each banner once per week; each player
# raises at most one banner per week, so the cost gets shared around.
BANNERS = {
    # Pricey on purpose (owner, 2026-09-30): raising one is a sacrifice for the team.
    "war": {"name": "War Banner", "cost": 50, "text": "+15% damage"},
    "mending": {"name": "Banner of Mending", "cost": 40, "text": "2 extra potions"},
    "resolve": {"name": "Banner of Resolve", "cost": 40, "text": "Start with full energy"},
    "defiance": {"name": "Banner of Defiance", "cost": 50, "text": "His hits grow half as fast"},
    "pack": {"name": "Banner of the Pack", "cost": 30, "text": "Double health for pets and minions"},
    "bulwark": {"name": "Banner of the Bulwark", "cost": 40, "text": "+25% defense"},
}
# The Null spreads (January after he escapes): monsters are a little
# stronger until the party cleanses it by finishing books.
NULL_BUFF = 1.10
NULL_CLEANSE_PER_PLAYER = 2      # books finished in January, per player who fought him (min 2 players)


def banner_effects(banners) -> Dict:
    """What the week's raised banners do to one attack."""
    b = set(banners or ())
    return {"damage": 1.15 if "war" in b else 1.0, "potions": 2 if "mending" in b else 0, "full_energy": "resolve" in b,
            "escalate": BOSS_ESCALATE * (0.5 if "defiance" in b else 1.0), "pet_hp": 2.0 if "pack" in b else 1.0,
            "defense": 1.25 if "bulwark" in b else 1.0}


def boss_calendar(now: float) -> Dict:
    """Where `now` falls in the boss year (server local time).
    phase: "before" (Feb–Nov), "event" (December), "january" (the Null can spread).
    During the event, `slot` is this attack window: "YYYY-xmas" on Dec 25,
    otherwise the week's Monday ("YYYY-MM-DD", week 1 starts Dec 1)."""
    import time as _t
    lt = _t.localtime(now)
    if lt.tm_mon == 12:
        year, phase = lt.tm_year, "event"
    elif lt.tm_mon == 1:
        year, phase = lt.tm_year - 1, "january"
    else:
        year, phase = lt.tm_year, "before"
    start = int(_t.mktime((year, 12, 1, 0, 0, 0, 0, 0, -1)))
    end = int(_t.mktime((year + 1, 1, 1, 0, 0, 0, 0, 0, -1)))
    out = {"phase": phase, "year": year, "starts_at": start, "ends_at": end, "slot": None}
    if phase == "event":
        week1 = week_start(start)
        if lt.tm_mday == 25:
            out.update(slot=f"{year}-xmas", slot_name="Christmas", slot_ends=int(_t.mktime((year, 12, 26, 0, 0, 0, 0, 0, -1))))
        else:
            ws = week_start(now)
            n = 1 + round((ws - week1) / (7 * 86400))
            out.update(slot=week_key(now), slot_name=f"Week {n}", week=n, slot_ends=min(end, ws + 7 * 86400))
    return out


def boss_stats(level: int, atk_factor: float = 1.0) -> Dict:
    """The Regent's opening attack at a player's level (his health is
    shared; his hits grow every turn, BOSS_ESCALATE). atk_factor: the
    player's power factor (power_factors), like any monster."""
    s = enemy_scale(level)
    return {"atk": round(11 * BOSS_ATK * s["atk"] * atk_factor), "xp": round(140 * s["xp"])}


def momentum(clears_since: int) -> float:
    return 1 + BOSS_MOMENTUM * max(0, min(clears_since, BOSS_MOMENTUM_MAX))


def boss_damage_cap(atk: int) -> int:
    """The most one attack can believably deal (a long fight, every turn a
    critical special)."""
    return int(atk * 40 * 5.5) + 50


# Specials, roughly as dungeon.js plays them: (energy, damage multiplier).
# Pet classes' multipliers include their pets' share.
_SIM_SPECIAL = {"brawler": (3, 2.8), "runeblade": (5, 4.0), "hexcaster": (3, 2.4), "ranger": (4, 2.6),
                "paladin": (3, 2.2), "beastmaster": (3, 2.6), "necromancer": (3, 2.5)}


def simulate_attack(stats: Dict, cls: str, level: int, rng: Optional[random.Random] = None,
                    banners=(), detail: bool = False):
    """Balance simulation of one fight to the death: strikes build energy,
    the special fires when ready, potions below 35%, guard on telegraphed
    hits. Returns the damage dealt (or (damage, turns survived) with detail)."""
    rng = rng or random.Random()
    fx = banner_effects(banners)
    boss = boss_stats(level)
    hp, potions = stats["hp"], stats["potions"] + fx["potions"]
    energy = stats["energy"] if fx["full_energy"] else min(stats["energy"], stats.get("start_energy", 0))
    need, mult = _SIM_SPECIAL.get(cls, (3, 2.2))
    strike_energy = 2 if cls == "runeblade" else 1
    atk = stats["atk"] * fx["damage"]
    dealt, charged, turn = 0, False, 0
    while turn < BOSS_TURNS:
        intent = "slam" if charged else BOSS_MOVES[turn % len(BOSS_MOVES)]
        guard = intent in ("heavy", "slam")
        if hp < stats["hp"] * 0.35 and potions:
            potions -= 1
            hp = min(stats["hp"], hp + round(stats["hp"] * stats["potion_heal"]))
        elif guard:
            energy = min(stats["energy"], energy + 1)
        else:
            m = 1.0
            if energy >= need:
                energy -= need
                m = mult
            else:
                energy = min(stats["energy"], energy + strike_energy)
            crit = rng.random() < stats["crit"]
            dealt += round(atk * m * rng.uniform(0.85, 1.15) * (1.75 if crit else 1))
        a = boss["atk"] * (1 + fx["escalate"] * turn)
        raw = {"attack": a, "heavy": a * 2, "purge": a, "frenzy": a * 1.4, "slam": a * 2.8, "windup": 0,
               "cascade": a * 1.1, "wipe": a * 1.6}[intent]
        charged = intent == "windup"
        if intent == "purge":
            energy = 0
        if raw:
            dmg = max(1, round(raw - (0 if intent == "wipe" else stats["def"] * 0.5)))
            hp -= max(1, round(dmg * (1 - BOSS_GUARD))) if guard else dmg
        turn += 1
        if hp <= 0:
            break
    return (dealt, turn) if detail else dealt


def expected_attack(stats: Dict, cls: str, level: int, runs: int = 200) -> int:
    rng = random.Random(f"{cls}:{level}:{stats['atk']}")
    return round(sum(simulate_attack(stats, cls, level, rng) for _ in range(runs)) / runs)


def boss_max_hp(expected_per_player: List[int], party_size: int = 0) -> int:
    """Full health: BOSS_HP_SHARE of every attack the party could make, at
    their current strength. The party counts at least BOSS_MIN_PARTY (or
    `party_size`, every reader) crawlers; missing ones count at the average.
    Everyone growing through December (levels, gear, momentum, banners) is
    what makes it winnable."""
    if not expected_per_player:
        return BOSS_MIN_HP
    avg = sum(expected_per_player) / len(expected_per_player)
    n = max(len(expected_per_player), party_size, BOSS_MIN_PARTY)
    return max(BOSS_MIN_HP, int(avg * n * BOSS_SLOTS * BOSS_HP_SHARE))


# ── Tier List rewards (owner, 2026-09-30: get everyone ranking again) ─────
# Paid when a player's saved Tier List ranks series they've finished a book
# in. Each series pays once; moving it after finishing another book in it
# pays a little more. Backlog (series finished before launch) pays 1 each up
# to a cap, so hundreds of old books can't flood the economy.
TIER_FRESH_BOOKMARKS = 5       # a series finished after launch
TIER_RERANK_BOOKMARKS = 2      # moved to another tier after a newly finished book in it
TIER_BACKLOG_BOOKMARKS = 1     # a series finished before launch...
TIER_BACKLOG_CAP = 50          # ...up to this many bookmarks in total


def tier_norm(name: str) -> str:
    """Series names and tier-list cover names, compared loosely."""
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def tier_entries(query: str) -> Dict[str, str]:
    """A saved tier list ("S=<b64>,<b64>&A=...") -> {normalized series: tier}.
    Each entry is a base64 cover filename like "Dungeon_Crawler_Carl.jpg"."""
    import base64
    from urllib.parse import parse_qs
    out: Dict[str, str] = {}
    for tier, vals in parse_qs(query or "").items():
        for token in ",".join(vals).split(","):
            token = token.strip()
            if not token:
                continue
            try:
                raw = base64.b64decode(token.replace("-", "+").replace("_", "/") + "=" * (-len(token) % 4)).decode("utf-8", "ignore")
            except Exception:
                continue
            name = re.sub(r"\.(jpe?g|png|webp)$", "", raw, flags=re.I).replace("_", " ")
            if tier_norm(name):
                out[tier_norm(name)] = tier
            # A book cover stands in for its series too: "The Legend of William
            # Oh (Unabridged)" and "Monster Merchant Class: A LitRPG Adventure"
            # rank those series (book 1 sometimes lacks its series in ABS).
            base = re.sub(r"\s*\((un)?abridged\)\s*$", "", name, flags=re.I).split(":")[0].strip()
            if tier_norm(base):
                out.setdefault(tier_norm(base), tier)
    return out


def tier_rank_of(ranked: Dict[str, str], series_norm: str) -> Optional[str]:
    """The tier a series has in `ranked`, allowing for covers named after a
    book of the series ("Shadowcroft Academy for Dungeons Year One")."""
    if series_norm in ranked:
        return ranked[series_norm]
    if len(series_norm) >= 8:
        for k, t in ranked.items():
            if k.startswith(series_norm):
                return t
    return None
