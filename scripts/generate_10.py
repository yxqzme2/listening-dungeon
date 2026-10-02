import csv
import os
import random
import re
import sys
import glob

# --- CONFIGURATION ---
BATCH_SIZE = 10
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Find the loot folder (the admin button runs this from /data/scripts, but the
# word lists and loot.csv live in the csv folder).
def _find_dir(candidates, marker):
    for d in candidates:
        if d and os.path.exists(os.path.join(d, marker)):
            return d
    return candidates[-1]

CSV_DIR = _find_dir([os.environ.get("CSV_DIR"), "/data/csv", "/app/csv", os.path.join(SCRIPT_DIR, "..", "csv"), SCRIPT_DIR], "loot_prefixes.csv")
# New gear goes straight into loot.csv, the file the game drops loot from.
NEW_LOOT_FILE = os.path.join(CSV_DIR, "loot.csv")
OLD_LOOT_FILE = NEW_LOOT_FILE

PREFIX_FILE = os.path.join(CSV_DIR, "loot_prefixes.csv")
BASE_FILE = os.path.join(CSV_DIR, "loot_bases.csv")
SUFFIX_FILE = os.path.join(CSV_DIR, "loot_suffixes.csv")
FLAVOR_FILE = os.path.join(CSV_DIR, "loot_flavor.csv")

ICON_DIR = next((d for d in ["/data/icons", "/app/icons", os.path.join(SCRIPT_DIR, "..", "icons"), os.path.join(CSV_DIR, "..", "icons")] if os.path.isdir(d)), "icons")

RARITY_BUDGETS = {
    "Common": 20, "Uncommon": 40, "Rare": 60, "Epic": 80, "Legendary": 100
}
RARITY_ORDER = ["Common", "Uncommon", "Rare", "Epic", "Legendary"]

# Mapping Base Type to Icon Prefix
ICON_PREFIX_MAP = {
    "Sword": "weapon_sword_",
    "Staff": "weapon_mace_",
    "Bow": "weapon_bow_",
    "Dagger": "weapon_shortblade_",
    "Mace": "weapon_mace_",
    "Axe": "weapon_axe_",
    "Plate": "plate_",
    "Cloth": "cloth_", 
    "Mail": "mail_",
    "Jewelry": "acc_",
    "Relic": "icons_quest_misc_"
}

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '_', (text or "item").lower()).strip('_')

def pick_random_icon(slot, item_type):
    """Searches /icons/ for a matching slot/type pattern."""
    slot_low = slot.lower()
    prefix = ICON_PREFIX_MAP.get(item_type, "icons_quest_misc_")
    
    pattern = ""
    if slot_low == "weapon":
        pattern = f"{prefix}*.png"
    elif slot_low in ["chest", "head"]:
        pattern = f"{slot_low}_{prefix}*.png"
    elif slot_low in ["ring", "neck", "trinket"]:
        if slot_low == "ring": pattern = "acc_ring*.png"
        elif slot_low == "neck": pattern = "acc_neck*.png"
        else: pattern = "acc_trinket*.png"
    else:
        pattern = "icons_quest_misc_*.png"

    matches = glob.glob(os.path.join(ICON_DIR, pattern))
    if not matches:
        matches = glob.glob(os.path.join(ICON_DIR, "icons_quest_misc_*.png"))
        if not matches: return "/icons/unknown.png"

    return f"/icons/{os.path.basename(random.choice(matches))}"

def load_csv(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            reader.fieldnames = [fn.strip().strip(',') for fn in reader.fieldnames]
            return list(reader)
    except Exception:
        return []

def get_used_names():
    names = set()
    for row in load_csv(OLD_LOOT_FILE):
        val = row.get('item_name')
        if val: names.add(val.lower().strip())
    for row in load_csv(NEW_LOOT_FILE):
        val = row.get('item_name')
        if val: names.add(val.lower().strip())
    return names

def allocate_stats(rarity):
    budget = RARITY_BUDGETS[rarity]
    max_cap = int(budget * 0.6)
    stats = {"str": 0, "mag": 0, "def": 0, "hp": 0}
    
    # 1. Choose primary stat and assign 40-60% of budget
    primary = random.choice(["str", "mag", "def"])
    stats[primary] = random.randint(int(budget * 0.4), max_cap)
    
    # 2. Distribute remaining budget among others
    remaining_points = budget - stats[primary]
    
    secondary = random.choice([s for s in ["str", "mag", "def"] if s != primary])
    stats[secondary] = random.randint(0, remaining_points)
    remaining_points -= stats[secondary]
    
    tertiary = [s for s in ["str", "mag", "def"] if s not in [primary, secondary]][0]
    stats[tertiary] = random.randint(0, remaining_points)
    remaining_points -= stats[tertiary]
    
    # 3. Everything left over MUST go to HP (1 pt = 5 HP)
    stats["hp"] = remaining_points * 5
    
    return stats, primary.upper()

def run_gen():
    print(f"--- SYSTEM: Generating {BATCH_SIZE} PBS items with Icon Mapping ---")
    prefixes, bases, suffixes, flavors = load_csv(PREFIX_FILE), load_csv(BASE_FILE), load_csv(SUFFIX_FILE), load_csv(FLAVOR_FILE)
    if not prefixes or not bases:
        print(f"ERROR: loot word lists not found in {CSV_DIR}.")
        sys.exit(1)
    used_names = get_used_names()
    new_items = []
    
    for _ in range(BATCH_SIZE):
        r_roll = random.random()
        rarity = "Legendary" if r_roll > 0.98 else "Epic" if r_roll > 0.90 else "Rare" if r_roll > 0.75 else "Uncommon" if r_roll > 0.50 else "Common"
        ridx = RARITY_ORDER.index(rarity)
        stats, pkey = allocate_stats(rarity)

        while True:
            pre_row = random.choice([p for p in prefixes if RARITY_ORDER.index(p.get('Min_Rarity', 'Common')) <= ridx])
            base_row = random.choice(bases)
            valid_s = [s for s in suffixes if s.get('Primary_Stat') == pkey]
            suf_row = random.choice(valid_s if valid_s else suffixes)
            name = f"{pre_row.get('Prefix', 'Generic')} {base_row.get('Base_Item', 'Item')} {suf_row.get('Suffix', '')}".strip()
            if name.lower() not in used_names:
                used_names.add(name.lower()); break
        
        f_pool = [f for f in flavors if f.get('Category') == pre_row.get('Theme') or f.get('Category') in ['General', 'System']]
        f_pool = [f for f in f_pool if RARITY_ORDER.index(f.get('Min_Rarity', 'Common')) <= ridx]
        flavor = random.choice(f_pool if f_pool else (flavors if flavors else [{'Flavor_Text': 'Mysterious.'}]))['Flavor_Text']

        new_items.append({
            "item_id": f"new_{random.randint(100000, 999999)}",
            "item_name": name,
            "slot": base_row.get('Slot', 'Trinket'),
            "str": stats['str'], "mag": stats['mag'], "def": stats['def'], "hp": stats['hp'],
            "special_ability": "None", "rarity": rarity, "flavor_text": flavor,
            "series_tag": pre_row.get('Theme', 'System'),
            "icon": pick_random_icon(base_row.get('Slot', 'Trinket'), base_row.get('Type', 'Misc'))
        })

    # Make sure the file ends with a newline before appending rows.
    if os.path.exists(NEW_LOOT_FILE) and os.path.getsize(NEW_LOOT_FILE):
        with open(NEW_LOOT_FILE, 'rb') as f:
            f.seek(-1, os.SEEK_END)
            needs_nl = f.read(1) not in (b"\n", b"\r")
    else:
        needs_nl = False
    with open(NEW_LOOT_FILE, 'a', newline='', encoding='utf-8') as f:
        if needs_nl: f.write("\n")
        writer = csv.DictWriter(f, fieldnames=new_items[0].keys())
        if f.tell() == 0: writer.writeheader()
        writer.writerows(new_items)
    print(f"SUCCESS: {BATCH_SIZE} new items added to {NEW_LOOT_FILE}. They can drop in dungeons right away.")
    for it in new_items:
        print(f"  {it['rarity']:<9} {it['slot']:<8} {it['item_name']}")

if __name__ == "__main__":
    run_gen()
