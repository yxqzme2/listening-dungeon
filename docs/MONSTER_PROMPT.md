# Making monsters with another AI

How to fill the dungeons with series monsters:

1. Open `docs/MONSTER_SERIES.md` and pick about 10 series. Starred (★) series are the party favorites, so start with those.
2. Copy **the prompt below** into another AI (ChatGPT, Gemini, Claude…). Replace the `SERIES LIST` line with your 10 series names, copied exactly.
3. It answers with a JSON list. Copy all of it.
4. Go to **Dungeon Admin → Monster Workshop → Import monsters**, paste it in and click **Import**.
   - Every monster is checked. Anything wrong is listed with the reason and skipped, so you can ask the AI to fix just those.
   - Importing the same name for the same series again replaces the old version.
5. Repeat until you have the count you want. 2–3 monsters × 60 series ≈ 150 monsters.

What the game does with them:
- A series monster **only appears in that series' dungeons**, twice as often as the regular monsters there.
- It fights at the right strength for **any** player level. Its health and damage come from its role and style, scaled to the player.
- New monsters appear in everyone's Bestiary as silhouettes, in a section named after their series.

---

## Which prompt?

- **Series monsters:** the first prompt below. They only appear in that series' dungeons.
- **General monsters:** the second prompt, further down. These have no series and appear in **every** dungeon at the matching level. This is the pool that keeps fights varied. As of 2026-09-30 it's thin: tier 1 has only 3 regulars, 1 elite and 1 boss, and each tier has a single floor boss. Run the general prompt once, or twice for even more variety.

## The prompt (copy everything below this line)

You are designing monsters for **The Listening Dungeon**, a small, friendly roguelite for a group of audiobook listeners. Every audiobook they finish becomes a short dungeon, and monsters inspired by that book's series appear in its dungeon. The tone is light, funny and affectionate: a snarky "System AI" narrates fights, like a LitRPG.

Design **2 or 3 monsters for each series** in this list:

SERIES LIST: <paste series names here, one per line, exactly as written>

For each series, make:
- **1 or 2 regular monsters**: common enemies of that world, like creatures, minions, soldiers or pests.
- **1 elite**: a tougher, memorable foe or rival from that world.
- **No bosses.** The game already has bosses and villains.

Base them on the world, its creatures, factions and running jokes. Write **original** names and lines "in the spirit of" the books:
- Never quote the books.
- Never use a main character as a monster.
- Keep spoilers vague: nothing past book 1's setup.

### Output format

Reply with **only** a JSON array (in one ```json code block), one object per monster, following these rules exactly. Anything outside these rules is rejected.

```json
{
  "name": "Glitter Mimic",
  "series": "Dungeon Crawler Carl",
  "tier": 2,
  "role": "regular",
  "style": "glass",
  "moves": ["attack", "shield", "poison", "attack"],
  "move_names": {"attack": "Lid Chomp", "shield": "Play Dead", "poison": "Sparkle Spores"},
  "barks": ["The viewers LOVE a surprise!", "Loot? No. Teeth."],
  "appear": "A treasure chest with suspiciously good lighting opens its lid. The lid has teeth.",
  "death": "It snaps shut one last time and drops a single copper coin.",
  "art": {"body": "blob", "head": "none", "eyes": "many", "horns": "none", "teeth": "grin", "item": "none", "extra": "aura",
          "color": "#C9A04A", "accent": "#8C3A2E", "size": 1.0}
}
```

**Fields**
- `name`: 3–40 characters. Only letters, numbers, spaces and `' - , . ! ?`. Don't use colons, ampersands, accented letters or emoji. Make it unique; add a series flavor word if it's generic (e.g. "Ashwood Slime", not "Slime").
- `series`: the series name **exactly** as given in the list.
- `tier`: 1–5, how dangerous it feels in that world (1 = pest, 5 = nightmare). This only sorts it in the Bestiary; fight strength scales automatically.
- `role`: `"regular"` or `"elite"`.
- `style`: one of:
  - `"balanced"`
  - `"brute"`: tough, hits a bit softer
  - `"glass"`: fragile, hits hard
  - `"tank"`: very tough, weak hits
- `moves`: 2–8 moves. It uses them in this order, then repeats. Only these keys:
  - `attack`: a normal hit
  - `heavy`: a big telegraphed hit (the player is warned to guard)
  - `frenzy`: two quick hits
  - `spit`: a ranged hit that ignores armor
  - `rage`: gets angry; its attack goes up for the rest of the fight
  - `windup`: charges up; the next turn it slams for huge damage
  - `gorge`: heals itself
  - `drain`: hits and heals itself for half
  - `poison`: a light hit, then 3 turns of poison damage
  - `weaken`: a light hit that lowers the player's attack for the fight
  - `shield`: raises its guard; takes half damage until its next turn

  Make each monster's rhythm feel different. A brute might go `["attack", "rage", "heavy", "attack"]`; a trickster might go `["shield", "poison", "attack", "weaken"]`. Elites should have 4–6 moves including at least one `heavy` or `windup`.
- `move_names` (optional but wanted): gives moves their own names, e.g. `{"heavy": "Tail Slam"}`. Each name is 1–28 characters, same character rules as `name`. Only name moves the monster actually uses. For `windup`, the name is what it shouts when the slam lands.
- `barks`: 1–4 short lines (under 100 characters) it may say during the fight. Funny, in character.
- `appear`: one sentence (under 160 characters) when it shows up.
- `death`: one sentence (under 160 characters) when it's beaten.
- `art`: the monster is drawn from paper-cutout parts. Pick the combination that best suggests the creature:
  - `body`:
    - `humanoid`: two legs, arms, holds an item
    - `beast`: four legs, tail
    - `blob`: slime or mound
    - `bug`: insect or spider
    - `ghost`: floating spirit, holds an item
    - `construct`: golem, robot, machine; holds an item
    - `serpent`: snake, worm, eel
    - `plant`: flower or vine creature
    - Don't use `bigboss`; it's for bosses.
  - `head`: `round`, `skull`, `horned`, `hood` (dark hood with a face in shadow), `bug`, `beak`, `none`
  - `eyes`: `two`, `one`, `glowing`, `many`, `slits`
  - `horns`: `none`, `curved`, `spikes`, `antlers`, `crown`
  - `teeth`: `none`, `fangs`, `grin`, `tusks`
  - `item`: `none`, `club`, `dagger`, `staff`, `shield`, `scythe`, `bow`, `sword`, `axe`, `trident`, `orb`. Only `humanoid`, `ghost` and `construct` bodies show it.
  - `extra`: `none`, `wings`, `tail`, `tentacles`, `aura` (a glowing halo, good for magic creatures)
  - `color`: main color as `#RRGGBB`. `accent`: clothing, stripes, wings or horns, as `#RRGGBB`. Pick colors that fit the world and differ between monsters.
  - `size`: 0.7–1.4. Elites usually 1.1–1.3.

Vary bodies, colors and move patterns across the whole list so no two monsters look or fight alike:
- At most a third of the monsters may use the `humanoid` body.
- Use `shield` in at most one monster out of three.
- Avoid goblins unless the books really have them.
- Names must clearly belong to that world (good: "Sponsor Bait Chest", "Syndic Boarding Trooper"; bad: "Dungeon Shield Breaker", "Field Goblin").

Output the JSON array only.


---

## General monsters: the prompt (copy everything below this line)

You are designing monsters for **The Listening Dungeon**, a small, friendly roguelite for a group of audiobook listeners. Every audiobook they finish becomes a short dungeon. A snarky "System AI" narrates the fights, LitRPG style. The tone is light and funny, with a little menace.

Design **general dungeon monsters**, not tied to any book, for these five level tiers. Each tier has a theme:

| tier | theme | feel |
|---|---|---|
| 1 | Goblin warrens | scrappy tunnels, junk, vermin, goblin tricks (levels 1–9: every new player lives here, so make it varied) |
| 2 | Crypts and undead | bones, ghosts, curses, grave-robbers |
| 3 | The Fungal Deep | spores, slimes, bugs, rot, glowing caves |
| 4 | The Clockwork Vaults | constructs, traps, gears, mad inventions |
| 5 | The Infernal Stacks | demons, burning libraries, forbidden books |

For **each tier** make:
- **8 regular** monsters
- **3 elites**
- **2 bosses**: the floor boss at the bottom of a dungeon

That's 65 monsters in total. Book jokes are welcome in the Infernal Stacks and elsewhere (overdue fines, cursed bookmarks, a library that shushes), but don't copy real books or their characters.

### Output format

Reply with **only** a JSON array (in one ```json code block), one object per monster. The format is the same as the series prompt, with these differences:
- **Leave out `series`** entirely.
- `tier`: 1–5, from the table above.
- `role`: `"regular"`, `"elite"` or `"boss"`.
- **Bosses:**
  - `moves`: 5–8, including at least one `windup` and one of `rage` / `drain` / `gorge`.
  - `art.body`: `"bigboss"` or another big body, with `size` 1.2–1.4.
  - `appear`: a dramatic entrance line.
- **Elites:** 4–6 moves, including at least one `heavy` or `windup`.

```json
{
  "name": "Overdue Fines Collector",
  "tier": 5,
  "role": "elite",
  "style": "brute",
  "moves": ["attack", "weaken", "heavy", "rage", "attack"],
  "move_names": {"attack": "Stamp of Lateness", "weaken": "Compound Interest", "heavy": "Final Notice", "rage": "Second Final Notice"},
  "barks": ["That book was due in 1847.", "Cash, card, or soul?"],
  "appear": "A clerk made of red ink and paperwork drifts out of the stacks, already tallying what you owe.",
  "death": "It stamps itself PAID IN FULL and flutters apart.",
  "art": {"body": "ghost", "head": "hood", "eyes": "glowing", "horns": "none", "teeth": "grin", "item": "staff", "extra": "aura",
          "color": "#8C2E2A", "accent": "#E3A93B", "size": 1.2}
}
```

**Field rules** (anything else is rejected):
- `name`: 3–40 characters. Only letters, numbers, spaces and `' - , . ! ?`. Must be unique across all 65.
- `style`: `balanced`, `brute`, `glass` or `tank`.
- `moves`: only `attack`, `heavy`, `frenzy`, `spit`, `rage`, `windup`, `gorge`, `drain`, `poison`, `weaken`, `shield`.
- `move_names`: names for the moves it uses, 1–28 characters, same character rules as `name`.
- `barks`: 1–4 short lines. `appear` and `death`: one sentence each, under 160 characters.
- `art`:
  - `body`: `humanoid`, `beast`, `blob`, `bug`, `ghost`, `construct`, `serpent`, `plant`, `bigboss` (bosses only)
  - `head`: `round`, `skull`, `horned`, `hood`, `bug`, `beak`, `none`
  - `eyes`: `two`, `one`, `glowing`, `many`, `slits`
  - `horns`: `none`, `curved`, `spikes`, `antlers`, `crown`
  - `teeth`: `none`, `fangs`, `grin`, `tusks`
  - `item` (only `humanoid`, `ghost` and `construct` show it): `none`, `club`, `dagger`, `staff`, `shield`, `scythe`, `bow`, `sword`, `axe`, `trident`, `orb`
  - `extra`: `none`, `wings`, `tail`, `tentacles`, `aura`
  - `color` and `accent`: `#RRGGBB`
  - `size`: 0.7–1.4

**Variety rules:**
- In each tier, use at least 5 different bodies.
- At most 2 humanoids per tier.
- `shield` in at most a third of the monsters.
- Every monster needs a different move rhythm.
- Colors should fit the tier's theme and differ from each other.

Output the JSON array only.
