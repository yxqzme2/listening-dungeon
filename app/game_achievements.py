# -----------------------------------------
# game_achievements.py — light game badges for The Listening Dungeon
# -----------------------------------------
# Badges pay nothing (no XP, no bookmarks), so the few that depend on what the
# phone reports about a fight ("beat a boss without a potion") can safely
# trust it. Each badge is checked against a player's lifetime counters
# (game_players.stats_json) plus their dungeon shelf.
#
# December boss badges: land a hit, top damage in a week, part of the kill,
# and the scar everyone who fought gets if the Null Regent escapes.
# -----------------------------------------

from typing import Callable, Dict, List

from . import game_rules as R

# Lifetime counters kept in stats_json. Lists are stored as sorted lists.
COUNTERS = ("kills", "elites", "bosses", "stairs", "deaths", "loot_boxes", "spent", "smoke_escapes", "revive_clears", "boss_damage", "duel_wins")
SETS = ("classes_cleared", "beasts", "minions", "flags", "scars")  # scars: "YEAR:PCT" (the Regent escaped at PCT%)


def _stat(key: str, n: int) -> Callable[[Dict], bool]:
    return lambda ctx: ctx["stats"].get(key, 0) >= n


def _flag(name: str) -> Callable[[Dict], bool]:
    return lambda ctx: name in ctx["stats"].get("flags", [])


# (key, group, name, text, test)
BADGES = [
    # progress
    ("first_blood", "Progress", "First Blood", "Win your first fight.", _stat("kills", 1)),
    ("first_clear", "Progress", "Spoiler Alert", "Clear your first dungeon.", lambda c: c["clears"] >= 1),
    ("clears_10", "Progress", "Regular", "Clear 10 dungeons.", lambda c: c["clears"] >= 10),
    ("clears_25", "Progress", "Bookworm", "Clear 25 dungeons.", lambda c: c["clears"] >= 25),
    ("clears_50", "Progress", "Shelf Clearer", "Clear 50 dungeons.", lambda c: c["clears"] >= 50),
    ("clears_100", "Progress", "Centurion", "Clear 100 dungeons.", lambda c: c["clears"] >= 100),
    ("level_5", "Progress", "Getting Somewhere", "Reach level 5.", lambda c: c["level"] >= 5),
    ("level_10", "Progress", "Double Digits", "Reach level 10.", lambda c: c["level"] >= 10),
    ("level_25", "Progress", "Veteran", "Reach level 25.", lambda c: c["level"] >= 25),
    ("level_50", "Progress", "Legend of the Stacks", "Reach level 50.", lambda c: c["level"] >= 50),
    ("first_boss", "Progress", "Boss Fight", "Beat a floor boss.", _stat("bosses", 1)),
    ("bosses_25", "Progress", "Boss Collector", "Beat 25 floor bosses.", _stat("bosses", 25)),
    # skill
    ("no_potion_boss", "Skill", "Teetotaler", "Beat a floor boss without drinking a potion that run.", _flag("no_potion_boss")),
    ("clutch", "Skill", "Clutch", "Win a fight with 5% health or less left.", _flag("clutch")),
    ("flawless", "Skill", "Untouchable", "Clear a dungeon without dropping below half health.", _flag("flawless")),
    ("overcharge_boss", "Skill", "Overcharged", "Finish a floor boss with an Overcharge.", _flag("overcharge_boss")),
    ("elites_25", "Skill", "Elite Hunter", "Defeat 25 elites.", _stat("elites", 25)),
    # reading-linked
    ("long_haul", "Reading", "The Long Haul", "Clear a dungeon from a 20+ hour book.", _flag("long_haul")),
    ("series_done", "Reading", "Series Finale", "Catch up on a series of 5+ books (and find its guaranteed Epic).", _flag("series_finale")),
    ("comeback", "Reading", "Comeback Story", "Revive a fallen book and clear it.", _stat("revive_clears", 1)),
    ("tier_25", "Reading", "Critic", "Rank 25 series you've finished in your Tier List.", lambda c: c.get("tier_ranked", 0) >= 25),
    ("tier_50", "Reading", "Curator", "Rank 50 series you've finished in your Tier List.", lambda c: c.get("tier_ranked", 0) >= 50),
    ("tier_current", "Reading", "Up to Date", "Every series you've finished is ranked in your Tier List.", _flag("tier_current")),
    # class
    ("all_classes", "Class", "Jack of All Trades", "Clear a dungeon with each of the 7 classes.",
     lambda c: len(set(c["stats"].get("classes_cleared", [])) & set(R.CLASS_STATS)) >= len(R.CLASS_STATS)),
    ("full_menagerie", "Class", "Full Menagerie", "Summon a wolf, a hawk and a bear as a Beastmaster.",
     lambda c: {"wolf", "hawk", "bear"} <= set(c["stats"].get("beasts", []))),
    ("full_crypt", "Class", "Full Crypt", "Raise a skeleton, a ghoul and a wraith as a Necromancer.",
     lambda c: {"skeleton", "ghoul", "wraith"} <= set(c["stats"].get("minions", []))),
    # economy
    ("store_open", "Economy", "Valued Customer", f"Unlock the System Store ({R.STORE_UNLOCK_CLEARS} clears).",
     lambda c: c["clears"] >= R.STORE_UNLOCK_CLEARS),
    ("legendary", "Economy", "It's Orange!", "Own a Legendary item.", _flag("legendary")),
    ("big_spender", "Economy", "Big Spender", "Spend 500 bookmarks.", _stat("spent", 500)),
    # the Bestiary and the Monster Workshop
    ("bestiary_25", "Reading", "Field Notes", "Discover 25 monsters in your Bestiary.", lambda c: c.get("bestiary", 0) >= 25),
    ("bestiary_100", "Reading", "Walking Bestiary", "Discover 100 monsters in your Bestiary.", lambda c: c.get("bestiary", 0) >= 100),
    ("monster_live", "Silly", "It's Alive!", "A monster you suggested comes to life in the dungeons.", _flag("monster_live")),
    # the December boss
    ("boss_hit", "Boss", "Null Pointer", "Land a hit on the Null Regent.", _flag("boss_hit")),
    ("boss_top_week", "Boss", "Top of the Charts", "Deal the most damage to the Null Regent in a week.", _flag("boss_top_week")),
    ("boss_kill", "Boss", "Regent Slayer", "Be part of the party that brings down the Null Regent.", _flag("boss_kill")),
    ("boss_scar", "Boss", "Scarred by the Regent", "Fight the Null Regent in a December he escapes. The scar remembers how close you got.", _flag("boss_scar")),
    # the Arena (ghost duels)
    ("duel_win", "Arena", "Duelist", "Beat another crawler's ghost in the Arena.", _stat("duel_wins", 1)),
    ("duel_wins_25", "Arena", "Gladiator", "Win 25 duels.", _stat("duel_wins", 25)),
    ("giant_slayer", "Arena", "Giant Slayer", f"Beat the ghost of a crawler {R.GIANT_SLAYER_LEVELS}+ levels above you.", _flag("giant_slayer")),
    ("arena_top", "Arena", "King of the Hill", "Reach #1 on the Arena ladder.", _flag("arena_top")),
    ("arena_champion", "Arena", "Arena Champion", "Be #1 on the Arena ladder when a month ends.", _flag("arena_champion")),
    # silly (the System AI approves)
    ("floor_one", "Silly", "Tutorial Casualty", "Fall on floor 1. The System took notes.", _flag("floor_one")),
    ("loot_boxes_10", "Silly", "Gambling Problem", "Open 10 loot boxes.", _stat("loot_boxes", 10)),
    ("stairs_5", "Silly", "Fire Exit Enthusiast", "Take the stairs instead of the boss 5 times.", _stat("stairs", 5)),
    ("smoke", "Silly", "Tactical Retreat", "Escape a fight with a Smoke Bomb.", _stat("smoke_escapes", 1)),
]
BY_KEY = {b[0]: b for b in BADGES}


def earned(ctx: Dict) -> List[str]:
    """Keys of every badge `ctx` qualifies for. ctx: stats, level, clears, dungeons."""
    return [key for key, _g, _n, _t, test in BADGES if test(ctx)]


def view(key: str) -> Dict:
    _k, group, name, text, _t = BY_KEY[key]
    return {"key": key, "group": group, "name": name, "text": text}
