# -----------------------------------------
# game_monsters.py — who you fight, by level tier
# -----------------------------------------
# Monsters never carry raw numbers: health, attack and XP come from their
# ROLE (regular / elite / boss) times a STYLE preset, and the run's level
# scaling (game_rules.enemy_scale) grows them with the player. This keeps
# every monster — including future Monster Workshop ones — balanced.
#
# Art is either a built-in tier-1 drawing ("svg": key in dungeon.js) or a
# set of parts drawn by static/js/monster-art.js.
# -----------------------------------------

import random
import re
from typing import Dict, List, Optional

ROLE_BASE = {
    "regular": {"hp": 26, "atk": 7, "xp": 22},
    "elite": {"hp": 52, "atk": 9, "xp": 50},
    "boss": {"hp": 145, "atk": 11, "xp": 140},
}
STYLES = {
    "balanced": {"hp": 1.0, "atk": 1.0, "label": "Balanced"},
    "brute": {"hp": 1.3, "atk": 0.9, "label": "Brute (tough, slower hits)"},
    "glass": {"hp": 0.75, "atk": 1.25, "label": "Glass cannon (fragile, hits hard)"},
    "tank": {"hp": 1.6, "atk": 0.75, "label": "Tank (very tough, weak hits)"},
}
MOVES = {
    "attack": "Attack",
    "heavy": "Heavy hit (telegraphed; guard!)",
    "frenzy": "Double hit",
    "spit": "Poison spit (ignores armor)",
    "rage": "Get angry (+attack)",
    "windup": "Wind-up slam (next turn, huge; guard!)",
    "gorge": "Heal itself",
    "drain": "Life drain (hits and heals itself)",
    "poison": "Poison (a light hit, then you take damage for 3 turns)",
    "weaken": "Weaken (a light hit that lowers your attack for the fight)",
    "shield": "Shield up (takes half damage until its next turn)",
}
MODIFIERS = {
    "armored": {"name": "Armored", "text": "takes 30% less damage"},
    "frenzied": {"name": "Frenzied", "text": "every attack hits twice"},
    "vampiric": {"name": "Vampiric", "text": "heals from the damage it deals"},
    "explosive": {"name": "Explosive", "text": "bursts when it dies. Guard or take the blast"},
}
# Chance a regular monster rolls a modifier, by tier. From tier 2 on, elites
# and bosses always carry one.
MODIFIER_CHANCE = {1: 0.08, 2: 0.25, 3: 0.35, 4: 0.45, 5: 0.5}

# Art parts. Must match static/js/monster-art.js.
PARTS = {
    "body": {"humanoid", "beast", "blob", "bug", "ghost", "construct", "bigboss", "serpent", "plant"},
    "head": {"round", "skull", "horned", "hood", "bug", "beak", "none"},
    "eyes": {"two", "one", "glowing", "many", "slits"},
    "horns": {"none", "curved", "spikes", "antlers", "crown"},
    "teeth": {"none", "fangs", "grin", "tusks"},
    "item": {"none", "club", "dagger", "staff", "shield", "scythe", "bow", "sword", "axe", "trident", "orb"},
    "extra": {"none", "wings", "tail", "tentacles", "aura"},
}

TIERS = {
    1: "Goblin warrens",
    2: "Crypts and undead",
    3: "The Fungal Deep",
    4: "The Clockwork Vaults",
    5: "The Infernal Stacks",
}

MONSTERS: List[Dict] = [
    # ── tier 1: goblin warrens (built-in drawings) ──────────────────────
    {"id": "goblin", "name": "Goblin Scavenger", "tier": 1, "role": "regular", "style": "balanced", "svg": "goblin",
     "moves": ["attack", "attack", "heavy"]},
    {"id": "rat", "name": "Rat-Kin Brawler", "tier": 1, "role": "regular", "style": "brute", "svg": "rat",
     "moves": ["attack", "frenzy", "attack"]},
    {"id": "crawler", "name": "Tunnel Crawler", "tier": 1, "role": "regular", "style": "glass", "svg": "crawler",
     "moves": ["attack", "spit", "attack"]},
    {"id": "bruiser", "name": "Goblin Bruiser", "tier": 1, "role": "elite", "style": "balanced", "svg": "bruiser",
     "moves": ["attack", "heavy", "rage", "attack"]},
    {"id": "warden", "name": "The Stairwell Warden", "tier": 1, "role": "boss", "style": "balanced", "svg": "boss",
     "moves": ["attack", "windup", "attack", "gorge", "windup", "attack"]},

    # ── tier 2: crypts and undead (parts) ───────────────────────────────
    {"id": "shambler", "name": "Grave Shambler", "tier": 2, "role": "regular", "style": "brute",
     "art": {"body": "humanoid", "color": "#8C9A7E", "accent": "#5A4E44", "head": "round", "eyes": "glowing", "teeth": "grin", "item": "club"},
     "moves": ["attack", "attack", "heavy"],
     "appear": "A Grave Shambler lurches up. It is not in a hurry. Neither is death.", "death": "It lies back down. Politely, this time."},
    {"id": "bone_archer", "name": "Bone Archer", "tier": 2, "role": "regular", "style": "glass",
     "art": {"body": "humanoid", "color": "#E3DCC8", "accent": "#4A3A30", "head": "skull", "eyes": "glowing", "item": "bow"},
     "moves": ["attack", "frenzy", "attack"],
     "appear": "A Bone Archer nocks an arrow made from someone's shin.", "death": "The archer comes apart like a dropped wind chime."},
    {"id": "crypt_crawler", "name": "Crypt Crawler", "tier": 2, "role": "regular", "style": "balanced",
     "art": {"body": "bug", "color": "#4E3F66", "accent": "#8A6FB0", "head": "bug", "eyes": "many", "teeth": "fangs"},
     "moves": ["spit", "attack", "attack"],
     "appear": "Something with too many eyes skitters out of a coffin.", "death": "The crawler curls up. The coffin is available again."},
    {"id": "wailing_shade", "name": "Wailing Shade", "tier": 2, "role": "regular", "style": "glass",
     "art": {"body": "ghost", "color": "#9FB8C9", "accent": "#6FE0FF", "head": "round", "eyes": "glowing"},
     "moves": ["drain", "attack", "drain"],
     "appear": "A Wailing Shade drifts through the wall, complaining about the draft.", "death": "The shade fades out mid-wail."},
    {"id": "ghoul_hound", "name": "Ghoul Hound", "tier": 2, "role": "regular", "style": "balanced",
     "art": {"body": "beast", "color": "#7E8A6A", "accent": "#4A5238", "head": "round", "eyes": "slits", "teeth": "fangs"},
     "moves": ["frenzy", "attack", "attack"],
     "appear": "A Ghoul Hound sniffs you. You smell like leftovers.", "death": "Bad dog. Very dead dog."},
    {"id": "tomb_knight", "name": "Tomb Knight", "tier": 2, "role": "elite", "style": "tank",
     "art": {"body": "humanoid", "color": "#5A6072", "accent": "#353B4D", "head": "horned", "horns": "spikes", "eyes": "glowing", "item": "shield"},
     "moves": ["attack", "heavy", "rage", "attack"],
     "appear": "A Tomb Knight stands. Its oath outlived its kingdom.", "death": "The knight kneels one last time."},
    {"id": "bone_colossus", "name": "Bone Colossus", "tier": 2, "role": "elite", "style": "brute",
     "art": {"body": "construct", "color": "#D8CFB8", "accent": "#8C7458", "head": "skull", "eyes": "one", "horns": "spikes"},
     "moves": ["windup", "attack", "attack"],
     "appear": "The ossuary rearranges itself into something large and angry.", "death": "The Colossus collapses into a very tidy pile."},
    {"id": "ossuary_king", "name": "The Ossuary King", "tier": 2, "role": "boss", "style": "balanced",
     "art": {"body": "bigboss", "color": "#6E6A7E", "accent": "#3E2F4A", "head": "skull", "horns": "crown", "eyes": "glowing", "teeth": "grin", "item": "staff"},
     "moves": ["attack", "drain", "windup", "attack", "gorge", "drain"],
     "appear": "The Ossuary King rises from a throne of femurs. He has been expecting a reader.", "death": "The crown rolls away. Nobody picks it up."},

    # ── tier 3: the Fungal Deep (levels 20–29) ──────────────────────────
    {"id": "spore_puff", "name": "Spore Puff", "tier": 3, "role": "regular", "style": "glass",
     "art": {"body": "blob", "color": "#B7A36B", "accent": "#D6503E", "head": "round", "eyes": "many", "size": 0.85},
     "moves": ["spit", "attack", "spit"],
     "appear": "A Spore Puff wobbles toward you, wheezing something yellow.", "death": "It pops. You try not to breathe for a while."},
    {"id": "fungal_shambler", "name": "Fungal Shambler", "tier": 3, "role": "regular", "style": "brute",
     "art": {"body": "humanoid", "color": "#9C8B6A", "accent": "#6E7F58", "head": "round", "horns": "antlers", "eyes": "glowing", "item": "club"},
     "moves": ["attack", "heavy", "gorge"],
     "appear": "A Fungal Shambler lurches out. Something is growing on its something.", "death": "It crumbles into very good compost."},
    {"id": "cave_stalker", "name": "Cave Stalker", "tier": 3, "role": "regular", "style": "balanced",
     "art": {"body": "beast", "color": "#4F5A66", "accent": "#8FA870", "head": "round", "eyes": "slits", "teeth": "fangs"},
     "moves": ["frenzy", "attack", "attack"],
     "appear": "Two eyes open in the dark. Then the rest of the Cave Stalker.", "death": "The Stalker slinks off to die somewhere dramatic."},
    {"id": "glow_beetle", "name": "Glow Beetle", "tier": 3, "role": "regular", "style": "tank",
     "art": {"body": "bug", "color": "#3A5A4E", "accent": "#8CFF5A", "head": "bug", "eyes": "glowing"},
     "moves": ["attack", "attack", "spit"],
     "appear": "A Glow Beetle lights up the tunnel. Rude, but useful.", "death": "The light goes out. So does the beetle."},
    {"id": "tunnel_cultist", "name": "Tunnel Cultist", "tier": 3, "role": "regular", "style": "glass",
     "art": {"body": "humanoid", "color": "#B98A6A", "accent": "#5A4E6E", "head": "hood", "eyes": "glowing", "item": "dagger"},
     "moves": ["drain", "attack", "frenzy"],
     "appear": "A Tunnel Cultist whispers your name. It pronounces it wrong.", "death": "The cultist's prayers go unanswered. Typical."},
    {"id": "rot_hulk", "name": "Rot Hulk", "tier": 3, "role": "elite", "style": "tank",
     "art": {"body": "blob", "color": "#6E7F58", "accent": "#B7A36B", "head": "round", "eyes": "one", "teeth": "grin", "size": 1.25},
     "moves": ["attack", "gorge", "heavy", "attack"],
     "appear": "The Rot Hulk heaves itself up. The smell arrives first.", "death": "It deflates with a sound you'll remember."},
    {"id": "sporefather_guard", "name": "Mycelid Warden", "tier": 3, "role": "elite", "style": "brute",
     "art": {"body": "humanoid", "color": "#8C7A5A", "accent": "#4E6B3A", "head": "horned", "horns": "antlers", "eyes": "glowing", "teeth": "tusks", "item": "shield", "size": 1.15},
     "moves": ["attack", "rage", "heavy", "attack"],
     "appear": "A Mycelid Warden blocks the tunnel. It has roots here. Literally.", "death": "The Warden topples like a tree. A soft, spongy tree."},
    {"id": "sporefather", "name": "The Sporefather", "tier": 3, "role": "boss", "style": "balanced",
     "art": {"body": "bigboss", "color": "#8C7A5A", "accent": "#6E7F58", "head": "round", "horns": "antlers", "eyes": "many", "teeth": "grin", "item": "staff"},
     "moves": ["attack", "spit", "windup", "attack", "gorge", "drain"],
     "appear": "The Sporefather unfolds from the cavern wall. Every mushroom in the room turns to look at you.",
     "death": "The Sporefather sighs out one last cloud of spores. The cave goes quiet."},

    # ── tier 4: the Clockwork Vaults (levels 30–39) ─────────────────────
    {"id": "cog_sentry", "name": "Cog Sentry", "tier": 4, "role": "regular", "style": "tank",
     "art": {"body": "construct", "color": "#B08A4A", "accent": "#5A6072", "head": "round", "eyes": "one", "size": 0.9},
     "moves": ["attack", "heavy", "attack"],
     "appear": "A Cog Sentry ticks to life. Its warranty expired centuries ago.", "death": "The sentry winds down. Tick. Tick. Tock."},
    {"id": "brass_hound", "name": "Brass Hound", "tier": 4, "role": "regular", "style": "balanced",
     "art": {"body": "beast", "color": "#B08A4A", "accent": "#5A6072", "head": "round", "eyes": "glowing", "teeth": "fangs"},
     "moves": ["frenzy", "attack", "frenzy"],
     "appear": "A Brass Hound bounds in, clanking like a drawer of spoons.", "death": "The hound's spring snaps. It lies down, finally."},
    {"id": "spark_wisp", "name": "Spark Wisp", "tier": 4, "role": "regular", "style": "glass",
     "art": {"body": "ghost", "color": "#E3A93B", "accent": "#FFF2A0", "head": "round", "eyes": "glowing", "size": 0.85},
     "moves": ["spit", "attack", "spit"],
     "appear": "A Spark Wisp crackles in the air. Your hair stands up.", "death": "The wisp fizzles out with a tiny, sad zap."},
    {"id": "clockwork_spider", "name": "Clockwork Spider", "tier": 4, "role": "regular", "style": "balanced",
     "art": {"body": "bug", "color": "#8C857A", "accent": "#E3A93B", "head": "bug", "eyes": "many", "teeth": "fangs"},
     "moves": ["attack", "spit", "frenzy"],
     "appear": "A Clockwork Spider skitters down on a copper thread.", "death": "Gears everywhere. You'll be finding them for weeks."},
    {"id": "vault_automaton", "name": "Vault Automaton", "tier": 4, "role": "regular", "style": "brute",
     "art": {"body": "humanoid", "color": "#8C8F99", "accent": "#B08A4A", "head": "skull", "eyes": "glowing", "item": "shield"},
     "moves": ["attack", "attack", "heavy"],
     "appear": "A Vault Automaton asks for your library card. You don't have it.", "death": "ACCESS GRANTED, it croaks, and collapses."},
    {"id": "siege_golem", "name": "Siege Golem", "tier": 4, "role": "elite", "style": "tank",
     "art": {"body": "construct", "color": "#6E7A8C", "accent": "#D6503E", "head": "round", "eyes": "one", "horns": "spikes", "size": 1.3},
     "moves": ["windup", "attack", "attack", "rage"],
     "appear": "The floor shakes. The Siege Golem has noticed you.", "death": "The golem grinds to a halt. It had a good run."},
    {"id": "arc_warden", "name": "Arc Warden", "tier": 4, "role": "elite", "style": "glass",
     "art": {"body": "humanoid", "color": "#5A6072", "accent": "#3F74B5", "head": "hood", "eyes": "glowing", "item": "staff"},
     "moves": ["spit", "drain", "heavy", "attack"],
     "appear": "An Arc Warden hums with stored lightning. It hasn't been grounded in years.", "death": "The Warden discharges into the floor. Harmlessly, for once."},
    {"id": "archivist_engine", "name": "The Archivist Engine", "tier": 4, "role": "boss", "style": "balanced",
     "art": {"body": "bigboss", "color": "#9C8C6A", "accent": "#3F74B5", "head": "round", "horns": "spikes", "eyes": "one", "teeth": "grin", "item": "scythe"},
     "moves": ["attack", "windup", "attack", "rage", "spit", "windup"],
     "appear": "The Archivist Engine powers up. It has catalogued every reader who failed here.",
     "death": "The Engine files itself under DEFEATED. Alphabetically."},

    # ── tier 5: the Infernal Stacks (levels 40+) ────────────────────────
    {"id": "imp_scribe", "name": "Imp Scribe", "tier": 5, "role": "regular", "style": "glass",
     "art": {"body": "humanoid", "color": "#D6503E", "accent": "#2B2621", "head": "horned", "horns": "curved", "eyes": "slits", "teeth": "fangs", "item": "dagger", "size": 0.85},
     "moves": ["frenzy", "attack", "spit"],
     "appear": "An Imp Scribe is writing your obituary. It's saving the ending.", "death": "The imp's quill snaps. So does the imp."},
    {"id": "hellhound", "name": "Hellhound", "tier": 5, "role": "regular", "style": "balanced",
     "art": {"body": "beast", "color": "#6E2E2A", "accent": "#E3A93B", "head": "horned", "horns": "curved", "eyes": "glowing", "teeth": "fangs"},
     "moves": ["frenzy", "attack", "drain"],
     "appear": "A Hellhound pads out of the flames. It's a good boy. From hell.", "death": "The Hellhound whimpers into embers."},
    {"id": "ink_demon", "name": "Ink Demon", "tier": 5, "role": "regular", "style": "tank",
     "art": {"body": "blob", "color": "#22222E", "accent": "#8A4FB8", "head": "round", "eyes": "many", "teeth": "grin"},
     "moves": ["drain", "attack", "gorge"],
     "appear": "An Ink Demon pools out of a spilled bottle. Mind the carpet.", "death": "It dries into a very ugly stain."},
    {"id": "ember_wraith", "name": "Ember Wraith", "tier": 5, "role": "regular", "style": "glass",
     "art": {"body": "ghost", "color": "#E37B3B", "accent": "#F2D14A", "head": "round", "eyes": "glowing"},
     "moves": ["spit", "drain", "attack"],
     "appear": "An Ember Wraith flickers in, smelling of burnt pages.", "death": "The wraith gutters out like a candle."},
    {"id": "brimstone_beetle", "name": "Brimstone Beetle", "tier": 5, "role": "regular", "style": "brute",
     "art": {"body": "bug", "color": "#5A2A22", "accent": "#E3A93B", "head": "bug", "eyes": "glowing", "horns": "spikes"},
     "moves": ["attack", "heavy", "attack"],
     "appear": "A Brimstone Beetle trundles over, glowing like a coal.", "death": "It cracks open. It was hot inside. Very hot."},
    {"id": "pit_fiend", "name": "Pit Fiend", "tier": 5, "role": "elite", "style": "brute",
     "art": {"body": "humanoid", "color": "#8C2E2A", "accent": "#2B2621", "head": "horned", "horns": "curved", "eyes": "glowing", "teeth": "tusks", "item": "scythe", "size": 1.2},
     "moves": ["attack", "heavy", "rage", "windup"],
     "appear": "A Pit Fiend ducks through the doorway. It has to duck a lot.", "death": "The Pit Fiend falls back into its pit. Good riddance."},
    {"id": "doom_librarian", "name": "Doom Librarian", "tier": 5, "role": "elite", "style": "glass",
     "art": {"body": "humanoid", "color": "#3E2F4A", "accent": "#D6503E", "head": "hood", "eyes": "glowing", "item": "staff"},
     "moves": ["drain", "spit", "heavy", "drain"],
     "appear": "The Doom Librarian says SHHH. The walls bleed a little.", "death": "The Librarian is overdue. Permanently."},
    {"id": "unwritten_king", "name": "The Unwritten King", "tier": 5, "role": "boss", "style": "balanced",
     "art": {"body": "bigboss", "color": "#3E2F4A", "accent": "#D6503E", "head": "horned", "horns": "crown", "eyes": "glowing", "teeth": "grin", "item": "staff"},
     "moves": ["attack", "drain", "windup", "attack", "rage", "windup", "drain"],
     "appear": "The Unwritten King rises from a throne of burning manuscripts. Every story ends here, he says. Yours first.",
     "death": "The King's crown falls and his story ends mid-sentence."},
]
_BY_ID = {m["id"]: m for m in MONSTERS}


def stats_for(m: Dict) -> Dict:
    base, style = ROLE_BASE[m["role"]], STYLES[m.get("style", "balanced")]
    return {"hp": round(base["hp"] * style["hp"]), "atk": round(base["atk"] * style["atk"]), "xp": base["xp"]}


def export(m: Dict) -> Dict:
    """What the phone needs for one monster."""
    out = {k: m[k] for k in ("id", "name", "role", "moves") if k in m}
    out.update(stats_for(m))
    for k in ("svg", "art", "appear", "death", "custom", "series", "move_names", "barks"):
        if m.get(k):
            out[k] = m[k]
    if is_undead(m):
        out["undead"] = True   # the Paladin's Holy Strike does double damage
    return out


def is_undead(m: Dict) -> bool:
    """Undead: drawn as a ghost or with a skull, or a general crypt-tier monster."""
    art = m.get("art") or {}
    return bool(m.get("undead") or art.get("body") == "ghost" or art.get("head") == "skull"
                or (m.get("tier") == 2 and not m.get("series") and m.get("role") != "boss" and not m.get("custom")))


def series_keys(series_name: str) -> set:
    """Series keys a book belongs to ("Ark Royal #4, Warspite #1" -> both)."""
    from .game_rules import parse_series, series_key
    keys = {k for k, _n, _q in parse_series(series_name)}
    return keys or ({series_key(series_name)} if series_name else set())


def roster(tier: int, custom: Optional[List[Dict]] = None, rng: Optional[random.Random] = None, series: str = "") -> Dict:
    """Monsters for a dungeon at `tier`: the built-in ones plus any enabled
    Monster Workshop monsters (`custom`). Monsters made for a book series
    only appear in that series' dungeons, whatever the tier, and show up
    twice as often there; a series boss always takes the boss room. When a
    tier has several bosses, one is picked per dungeon."""
    custom = list(custom or [])
    general = MONSTERS + [m for m in custom if not m.get("series")]
    keys = series_keys(series)
    own = [m for m in custom if m.get("series") and series_keys(m["series"]) & keys] if keys else []
    built = sorted({m["tier"] for m in MONSTERS})
    use = max([t for t in built if t <= tier] or [built[0]])
    pick = lambda role: [export(m) for m in general if m["tier"] == use and m["role"] == role] + [export(m) for m in own if m["role"] == role] * 2
    own_bosses = [export(m) for m in own if m["role"] == "boss"]
    bosses = own_bosses or pick("boss")
    return {
        "tier": use,
        "theme": TIERS.get(use, ""),
        "regular": pick("regular"),
        "elite": pick("elite"),
        "boss": (rng or random).choice(bosses) if bosses else export(_BY_ID["warden"]),
        "modifier_chance": MODIFIER_CHANCE.get(tier, 0.5),
        "always_modded": tier >= 2,
        "modifiers": MODIFIERS,
    }


# ── Monster Workshop: validating admin-made monsters ────────────────────
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
NAME_OK = re.compile(r"^[A-Za-z0-9 '\-,.!?]+$")
TEXT_LIMIT = 160


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:40]


def clean_monster(raw: Dict) -> Dict:
    """A Workshop monster, checked against the same parts, roles, styles and
    moves as the built-in ones. Raises ValueError with a readable message."""
    if not isinstance(raw, dict):
        raise ValueError("Monster must be an object.")
    name = " ".join(str(raw.get("name") or "").split())[:40]
    if len(name) < 3:
        raise ValueError("Give the monster a name (3–40 characters).")
    if not NAME_OK.match(name):
        raise ValueError("Names can use letters, numbers, spaces and ' - , . ! ?")
    mid = slug(str(raw.get("id") or "")) or slug(name)
    if not mid:
        raise ValueError("That name has no letters or numbers.")
    if mid in _BY_ID:
        raise ValueError("A built-in monster already uses that name.")
    try:
        tier = int(raw.get("tier"))
    except (TypeError, ValueError):
        raise ValueError("Pick a tier.")
    if tier not in TIERS:
        raise ValueError("Pick a tier.")
    role, style = raw.get("role"), raw.get("style") or "balanced"
    if role not in ROLE_BASE:
        raise ValueError("Pick a role.")
    if style not in STYLES:
        raise ValueError("Pick a style.")
    moves = raw.get("moves")
    if not isinstance(moves, list) or not 2 <= len(moves) <= 8 or any(m not in MOVES for m in moves):
        raise ValueError("Give it 2 to 8 moves from: " + ", ".join(MOVES) + ".")
    art_in = raw.get("art") or {}
    art = {}
    for part, allowed in PARTS.items():
        v = art_in.get(part, "none" if "none" in allowed else sorted(allowed)[0])
        if v not in allowed:
            raise ValueError(f"Unknown {part}.")
        art[part] = v
    for key in ("color", "accent"):
        v = art_in.get(key) or ""
        if not HEX.match(v):
            raise ValueError(f"Pick a {key} color.")
        art[key] = v.upper()
    try:
        art["size"] = round(min(1.4, max(0.7, float(art_in.get("size", 1)))), 2)
    except (TypeError, ValueError):
        raise ValueError("Bad size.")
    out = {"id": mid, "name": name, "tier": tier, "role": role, "style": style, "moves": moves, "art": art, "custom": True}
    for key in ("appear", "death"):
        text = " ".join(str(raw.get(key) or "").split())[:TEXT_LIMIT]
        if text:
            out[key] = text
    series = " ".join(str(raw.get("series") or "").split())[:80]
    if series:
        out["series"] = series
    names = raw.get("move_names") or {}
    if not isinstance(names, dict):
        raise ValueError("move_names must map a move to its name.")
    clean_names = {}
    for mv, label in names.items():
        label = " ".join(str(label or "").split())[:28]
        if mv not in moves or not label:
            continue  # names for moves it doesn't use are ignored
        if not NAME_OK.match(label):
            raise ValueError(f"Move name '{label}' can use letters, numbers, spaces and ' - , . ! ?")
        clean_names[mv] = label
    if clean_names:
        out["move_names"] = clean_names
    barks = raw.get("barks") or []
    if not isinstance(barks, list):
        raise ValueError("barks must be a list of short lines.")
    barks = [" ".join(str(b).split())[:TEXT_LIMIT] for b in barks if str(b).strip()][:4]
    if barks:
        out["barks"] = barks
    return out
