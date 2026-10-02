/* The Listening Dungeon — one dungeon run, played on the phone.
 *
 *   Dungeon.start(run, { onFinish(report) -> Promise<result>, onDone(result, pending),
 *                        onSave(progress), onLeave() })
 *
 * Progress is checkpointed after every room (onSave) so a run can be left and
 * resumed; `run.progress` restores it. Leaving mid-fight restarts that fight.
 *
 * `run` comes from POST /api/game/runs: the player's real stats, class, look,
 * level-based enemy scaling and the book. The phone plays the fights; when the
 * run ends it reports {outcome, floors, kills, elites} and the SERVER decides
 * XP, bookmarks and loot. Monster art and System AI lines started in the
 * prototype (achievement-engine-clean/prototypes/book-dungeon).
 *
 *   Dungeon.duel(duel, hooks)   the Arena: one fight against another crawler's ghost
 *   Dungeon.raid(attack, hooks)  the December boss: one long fight against the
 * Null Regent's shared health bar, for `attack.turns` turns or until you fall.
 * It reports {outcome: fell | time | kill, damage}; the server caps the damage.
 */
(function () {
  const EDGE = 'stroke="rgba(40,25,15,.28)" stroke-width="2" stroke-linejoin="round"';
  const FOES = {
    goblin: { h: 150, svg: `<svg viewBox="0 0 220 240"><path d="M60 120 L20 80 L66 104 Z M160 120 L200 80 L154 104 Z" fill="#7FA650" ${EDGE}/>
     <rect x="78" y="180" width="22" height="48" rx="8" fill="#5A6E3A" ${EDGE}/><rect x="120" y="180" width="22" height="48" rx="8" fill="#5A6E3A" ${EDGE}/>
     <path d="M66 140 Q110 126 154 140 L160 200 Q110 212 60 200 Z" fill="#8C6A3E" ${EDGE}/><rect x="60" y="176" width="100" height="10" fill="#5B3A22"/>
     <circle cx="110" cy="110" r="46" fill="#8DB85A" ${EDGE}/><ellipse cx="94" cy="104" rx="10" ry="8" fill="#F2D14A"/><ellipse cx="126" cy="104" rx="10" ry="8" fill="#F2D14A"/>
     <circle cx="96" cy="105" r="4" fill="#2B2621"/><circle cx="124" cy="105" r="4" fill="#2B2621"/><path d="M92 130 Q110 140 128 130" stroke="#2B2621" stroke-width="4" fill="none"/>
     <path d="M100 131 l4 7 l4 -6 M114 131 l4 6 l4 -7" fill="#FBF8F0"/><ellipse cx="170" cy="170" rx="24" ry="28" fill="#C9A36B" ${EDGE}/><path d="M160 146 q10 -8 20 0" stroke="#5B3A22" stroke-width="4" fill="none"/></svg>` },
    rat: { h: 160, svg: `<svg viewBox="0 0 220 250"><path d="M150 210 C200 220, 210 170, 190 150" stroke="#D9A0A0" stroke-width="8" fill="none" stroke-linecap="round"/>
     <rect x="76" y="190" width="24" height="44" rx="8" fill="#6E6A66" ${EDGE}/><rect x="118" y="190" width="24" height="44" rx="8" fill="#6E6A66" ${EDGE}/>
     <ellipse cx="110" cy="164" rx="52" ry="50" fill="#8A8580" ${EDGE}/><ellipse cx="110" cy="176" rx="30" ry="30" fill="#B8B1A8"/>
     <circle cx="70" cy="62" r="24" fill="#8A8580" ${EDGE}/><circle cx="70" cy="62" r="13" fill="#E8A0A8"/><circle cx="150" cy="62" r="24" fill="#8A8580" ${EDGE}/><circle cx="150" cy="62" r="13" fill="#E8A0A8"/>
     <path d="M70 90 C70 60, 150 60, 150 90 L126 130 Q110 140 94 130 Z" fill="#8A8580" ${EDGE}/><circle cx="110" cy="134" r="7" fill="#E8A0A8"/>
     <circle cx="94" cy="96" r="6" fill="#D6503E"/><circle cx="126" cy="96" r="6" fill="#D6503E"/><path d="M60 78 L160 78 L154 92 L66 92 Z" fill="#D6503E" ${EDGE}/>
     <path d="M92 132 l-26 -4 M92 138 l-24 4 M128 132 l26 -4 M128 138 l24 4" stroke="#2B2621" stroke-width="2"/></svg>` },
    crawler: { h: 110, svg: `<svg viewBox="0 0 260 170"><g stroke="#2B2621" stroke-width="5" stroke-linecap="round">
     <path d="M70 120 l-20 36 M100 124 l-10 40 M150 124 l10 40 M180 120 l20 36"/></g>
     <ellipse cx="170" cy="100" rx="70" ry="48" fill="#7A5A9C" ${EDGE}/><ellipse cx="120" cy="104" rx="56" ry="44" fill="#8C6AB0" ${EDGE}/>
     <path d="M150 62 q20 20 0 80 M190 62 q20 20 0 76" stroke="#5E4480" stroke-width="4" fill="none"/>
     <circle cx="72" cy="104" r="40" fill="#9C7AC0" ${EDGE}/><circle cx="58" cy="94" r="8" fill="#F2D14A"/><circle cx="80" cy="90" r="8" fill="#F2D14A"/>
     <circle cx="58" cy="94" r="3.5" fill="#2B2621"/><circle cx="80" cy="90" r="3.5" fill="#2B2621"/><path d="M40 118 l-12 12 M56 124 l-6 16" stroke="#E3E0D5" stroke-width="6" stroke-linecap="round"/></svg>` },
    bruiser: { h: 185, svg: `<svg viewBox="0 0 240 280"><path d="M60 110 L14 70 L66 96 Z M180 110 L226 70 L174 96 Z" fill="#5E8A3A" ${EDGE}/>
     <rect x="80" y="214" width="30" height="54" rx="10" fill="#4E5E30" ${EDGE}/><rect x="132" y="214" width="30" height="54" rx="10" fill="#4E5E30" ${EDGE}/>
     <path d="M48 140 Q120 118 192 140 L200 226 Q120 244 40 226 Z" fill="#6E7A8C" ${EDGE}/><path d="M70 150 L170 150 L162 200 L78 200 Z" fill="#8C95A6"/>
     <circle cx="120" cy="100" r="52" fill="#6FA046" ${EDGE}/><path d="M86 86 L108 94 M154 86 L132 94" stroke="#2B2621" stroke-width="6" stroke-linecap="round"/>
     <circle cx="100" cy="100" r="6" fill="#D6503E"/><circle cx="140" cy="100" r="6" fill="#D6503E"/><path d="M96 130 L144 130" stroke="#2B2621" stroke-width="5"/>
     <path d="M100 130 l5 -10 l5 10 M130 130 l5 -10 l5 10" fill="#FBF8F0"/>
     <g transform="rotate(25 40 180)"><rect x="32" y="110" width="16" height="120" rx="6" fill="#6B4A2E" ${EDGE}/><ellipse cx="40" cy="104" rx="26" ry="34" fill="#8A6A48" ${EDGE}/></g></svg>` },
    boss: { h: 230, svg: `<svg viewBox="0 0 280 320"><path d="M60 120 L8 72 L66 100 Z M220 120 L272 72 L214 100 Z" fill="#5E8A3A" ${EDGE}/>
     <rect x="90" y="250" width="36" height="58" rx="12" fill="#4E5E30" ${EDGE}/><rect x="154" y="250" width="36" height="58" rx="12" fill="#4E5E30" ${EDGE}/>
     <ellipse cx="140" cy="200" rx="104" ry="80" fill="#6FA046" ${EDGE}/><ellipse cx="140" cy="214" rx="66" ry="54" fill="#9CC46E"/>
     <path d="M40 180 Q140 150 240 180 L236 206 Q140 180 44 206 Z" fill="#8C6A3E" ${EDGE}/><circle cx="140" cy="192" r="14" fill="#D4A93A" ${EDGE}/>
     <circle cx="140" cy="104" r="60" fill="#76A84A" ${EDGE}/><path d="M92 58 L104 20 L122 48 L140 14 L158 48 L176 20 L188 58 Z" fill="#E3A93B" ${EDGE}/>
     <circle cx="122" cy="44" r="5" fill="#D6503E"/><circle cx="158" cy="44" r="5" fill="#3F74B5"/>
     <path d="M104 90 L128 100 M176 90 L152 100" stroke="#2B2621" stroke-width="7" stroke-linecap="round"/><circle cx="118" cy="108" r="8" fill="#F2D14A"/><circle cx="162" cy="108" r="8" fill="#F2D14A"/>
     <circle cx="118" cy="108" r="3.5" fill="#2B2621"/><circle cx="162" cy="108" r="3.5" fill="#2B2621"/><path d="M110 140 Q140 128 170 140 Q140 156 110 140 Z" fill="#3A2A20"/>
     <path d="M118 138 l6 -12 l6 12 M150 138 l6 -12 l6 12" fill="#FBF8F0"/>
     <g transform="rotate(30 36 200)"><rect x="28" y="110" width="18" height="140" rx="7" fill="#6B4A2E" ${EDGE}/><ellipse cx="37" cy="104" rx="30" ry="40" fill="#7A6A5A" ${EDGE}/>
     <path d="M10 90 l-12 -4 M12 116 l-12 4 M64 90 l12 -4 M62 116 l12 4 M37 62 l0 -12" stroke="#C9C3B6" stroke-width="7" stroke-linecap="round"/></g></svg>` },
  };

  const DOOR_ART = {
    monster: `<svg viewBox="0 0 80 80"><path d="M16 64 L64 16 M24 16 L64 56" stroke="#EDE6D6" stroke-width="8" stroke-linecap="round"/><path d="M14 52 l14 14 M52 14 l14 14" stroke="#E3A93B" stroke-width="8" stroke-linecap="round"/></svg>`,
    elite: `<svg viewBox="0 0 80 80"><path d="M40 10 C18 10 12 30 16 44 L22 52 L22 64 L58 64 L58 52 L64 44 C68 30 62 10 40 10 Z" fill="#EDE6D6"/><circle cx="30" cy="38" r="7" fill="#353B4D"/><circle cx="50" cy="38" r="7" fill="#353B4D"/><path d="M32 64 v-8 M40 64 v-8 M48 64 v-8" stroke="#353B4D" stroke-width="4"/></svg>`,
    treasure: `<svg viewBox="0 0 80 80"><rect x="10" y="34" width="60" height="34" rx="4" fill="#C9A36B"/><path d="M10 34 C10 14 70 14 70 34 Z" fill="#A87E4A"/><rect x="10" y="34" width="60" height="6" fill="#6B4A2E"/><rect x="34" y="30" width="12" height="16" rx="2" fill="#E3A93B"/></svg>`,
    shrine: `<svg viewBox="0 0 80 80"><path d="M40 12 C24 30 22 44 40 60 C58 44 56 30 40 12 Z" fill="#9BE07A"/><path d="M40 28 v24 M28 40 h24" stroke="#2F5A36" stroke-width="6" stroke-linecap="round"/><rect x="22" y="62" width="36" height="8" rx="3" fill="#EDE6D6"/></svg>`,
    trap: `<svg viewBox="0 0 80 80"><path d="M8 66 L18 30 L28 66 M28 66 L40 22 L52 66 M52 66 L62 30 L72 66" fill="#EDE6D6"/><rect x="6" y="64" width="68" height="8" fill="#C9C3B6"/></svg>`,
    mystery: `<svg viewBox="0 0 80 80"><text x="40" y="62" text-anchor="middle" font-family="Permanent Marker, sans-serif" font-size="60" fill="#EDE6D6">?</text></svg>`,
    boss: `<svg viewBox="0 0 80 80"><path d="M12 58 L18 22 L30 40 L40 16 L50 40 L62 22 L68 58 Z" fill="#E3A93B"/><rect x="12" y="58" width="56" height="10" fill="#C98A1E"/></svg>`,
    exit: `<svg viewBox="0 0 80 80"><path d="M14 68 h14 v-14 h14 v-14 h14 v-14 h14" fill="none" stroke="#EDE6D6" stroke-width="8" stroke-linejoin="round"/><path d="M50 12 l14 0 l0 14" stroke="#9BE07A" stroke-width="6" fill="none" stroke-linecap="round"/></svg>`,
  };
  const ENEMIES = {
    goblin: { name: "Goblin Scavenger", hp: 26, atk: 7, xp: 22, moves: ["attack", "attack", "heavy"] },
    rat: { name: "Rat-Kin Brawler", hp: 32, atk: 6, xp: 24, moves: ["attack", "frenzy", "attack"] },
    crawler: { name: "Tunnel Crawler", hp: 22, atk: 8, xp: 20, moves: ["attack", "spit", "attack"] },
    bruiser: { name: "Goblin Bruiser", hp: 52, atk: 9, xp: 50, moves: ["attack", "heavy", "rage", "attack"] },
    boss: { name: "The Stairwell Warden", hp: 145, atk: 11, xp: 140, moves: ["attack", "windup", "attack", "gorge", "windup", "attack"] },
  };



  const SAY = {
    door: ["Pick a door. The System does not offer refunds.", "Two doors. One of them is probably fine.", "Choose wisely. Or quickly. The audience prefers quickly.", "Left or right? Statistically, both have monsters."],
    kill: ["Kill confirmed. Your viewers mildly approve.", "That goblin had a family. Kidding. It had fleas.", "Efficient. Violent. Adequate.", "XP awarded. Try to look less surprised.", "The corpse will be cleaned up by nobody."],
    start: ["A wild %s appears. It looks hungry.", "%s blocks the way. Talking is not an option.", "%s is here. It has read none of the books you have."],
    treasure: { potion: "Loot box opened: one healing potion. Don't drink it all at once. Actually, you can't.", buff: "Sponsor gift: a sharpening stone. +2 attack for this dungeon.", xp: "Loot box opened: a crumpled note. It says 'good job'. +30 XP." },
    shrine: "The shrine hums. You feel better, and slightly judged.",
    trapHit: "Spike trap. The System finds this hilarious.",
    trapDodge: "You spotted the pressure plate. The System is disappointed.",
    bossDoor: "The Stairwell Warden is awake. Beat it for better loot. Or take the stairs and leave. Nobody will judge you. Out loud.",
    boon: "The System offers you a gift. Pick one. It lasts until you leave or die.",
    winBoss: "Floor boss defeated. The crowd goes mild.",
    exit: "You took the stairs. Sensible. Boring, but sensible.",
    dead: "You have died. The System has confiscated half your XP and all of your loot. It left your bookmarks. It's not a monster. Well. It is, but not that kind.",
  };

  const BOONS = {
    vamp: { name: "Vampire Fangs", text: "Heal 15% of the damage you deal." },
    thorns: { name: "Spiked Coat", text: "Enemies take 30% of the damage they deal you." },
    quick: { name: "Gas Station Coffee", text: "Start every fight with +2 energy." },
    iron: { name: "Iron Skin", text: "+3 defense for this run." },
    keen: { name: "Keen Eye", text: "+15% critical hit chance." },
    brew: { name: "Spare Flask", text: "+1 potion right now.", repeat: true },
    vigor: { name: "Second Breakfast", text: "+20% max health, healed right now." },
    fury: { name: "Last Stand", text: "+40% damage while below half health." },
  };

  // ── pets (Beastmaster: live, Necromancer: undead) ────────────────────
  const PET_POOL = { beastmaster: ["wolf", "hawk", "bear"], necromancer: ["skeleton", "ghoul", "wraith"] };
  const RAISE_COST = { skeleton: 2, ghoul: 3, wraith: 4 };  // matches game_rules.RAISE_COSTS
  // Every class picks from a small menu of powers (the Necromancer's is the
  // Raise Dead menu). [id, name, energy, what it does]
  const POWERS = {
    brawler: [["haymaker", "Haymaker", 3, "2.8× hit"], ["body", "Body Blow", 2, "1.6× hit · its next attack is halved"],
      ["wind", "Second Wind", 2, "heal 20% · shake off poison and weakness"]],
    paladin: [["smite", "Smite", 3, "2.2× hit · heal 15%"], ["holy", "Holy Strike", 2, "1.5× hit · double vs undead"], ["lay", "Lay on Hands", 3, "heal 35%"]],
    runeblade: [["rune2", "Rune Burst", 2, "1.6× hit"], ["rune3", "Greater Burst", 3, "2.2× hit"], ["over", "OVERCHARGE", 5, "4× hit"]],
    hexcaster: [["drain", "Soul Drain", 3, "2.2× hit · heal half of it"], ["detonate", "Detonate", 2, "burst every curse stack at once"], ["wither", "Wither", 1, "+2 curse stacks"]],
  };
  // What each class calls its menu (owner, 2026-09-30).
  const MENU_NAME = { brawler: "Rage", paladin: "Judgements", hexcaster: "Hexes", runeblade: "Runes" };
  // Beastmaster: one button. No beast yet: call one. Then it becomes that beast's move.
  const BEAST_MOVE = {
    wolf: ["Pack Attack", "you and your wolf strike together"],
    bear: ["Hibernate", "you and your bear rest, heal and brace"],
    hawk: ["Murder of Crows", "your hawk calls the flock: 5 quick hits"],
  };
  const powerCost = (id) => { for (const list of Object.values(POWERS)) for (const p of list) if (p[0] === id) return p[2]; return 3; };
  const MAX_MINIONS = 2;
  const PETS = {
    wolf: { name: "Wolf", hp: 0.35, mult: 0.6, taunt: 0.25, color: "#8C8F99", text: "bites" },
    hawk: { name: "Hawk", hp: 0.25, mult: 0.35, hits: 2, crit: 0.3, taunt: 0.15, color: "#A87E4A", text: "pecks" },
    bear: { name: "Bear", hp: 0.6, mult: 0.5, taunt: 0.6, color: "#6B4A2E", text: "swipes" },
    skeleton: { name: "Skeleton", hp: 0.55, mult: 0.4, taunt: 0.6, color: "#E3DCC8", text: "slashes", blurb: "tough, takes hits for you" },
    ghoul: { name: "Ghoul", hp: 0.35, mult: 0.55, lifesteal: 0.5, taunt: 0.25, color: "#8FA870", text: "bites", blurb: "its bites heal you" },
    wraith: { name: "Wraith", hp: 0.3, mult: 0.45, drain: true, taunt: 0.15, color: "#6FE0FF", text: "drains", blurb: "hits hard and drains every turn" },
  };
  const PET_ART = {
    wolf: `<svg viewBox="0 0 120 90"><path d="M20 60 Q30 30 70 34 L92 20 L96 36 L110 44 L98 52 Q96 70 80 72 L78 86 L70 86 L68 72 L40 72 L38 86 L30 86 L30 70 Q18 66 20 60 Z" fill="#8C8F99" ${EDGE}/><circle cx="96" cy="40" r="3" fill="#2B2621"/><path d="M20 60 Q6 50 8 40" stroke="#8C8F99" stroke-width="7" fill="none" stroke-linecap="round"/></svg>`,
    hawk: `<svg viewBox="0 0 120 90"><path d="M60 50 Q30 20 6 30 Q30 40 44 56 Z M60 50 Q90 20 114 30 Q90 40 76 56 Z" fill="#A87E4A" ${EDGE}/><ellipse cx="60" cy="56" rx="16" ry="20" fill="#C9A36B" ${EDGE}/><circle cx="60" cy="40" r="10" fill="#C9A36B" ${EDGE}/><path d="M60 42 l8 4 l-8 3 Z" fill="#E3A93B"/><circle cx="56" cy="38" r="2" fill="#2B2621"/></svg>`,
    bear: `<svg viewBox="0 0 120 100"><ellipse cx="60" cy="64" rx="44" ry="30" fill="#6B4A2E" ${EDGE}/><circle cx="92" cy="42" r="20" fill="#6B4A2E" ${EDGE}/><circle cx="84" cy="24" r="7" fill="#6B4A2E" ${EDGE}/><circle cx="102" cy="26" r="7" fill="#6B4A2E" ${EDGE}/><ellipse cx="104" cy="48" rx="8" ry="6" fill="#C9A36B"/><circle cx="96" cy="38" r="3" fill="#2B2621"/><rect x="26" y="84" width="14" height="14" fill="#5A3E26"/><rect x="74" y="84" width="14" height="14" fill="#5A3E26"/></svg>`,
    skeleton: `<svg viewBox="0 0 90 120"><circle cx="45" cy="22" r="16" fill="#E3DCC8" ${EDGE}/><circle cx="39" cy="22" r="4" fill="#2B2621"/><circle cx="51" cy="22" r="4" fill="#2B2621"/><path d="M45 38 V80 M28 48 H62 M30 58 H60 M32 68 H58 M45 80 L32 112 M45 80 L58 112 M28 48 L16 78 M62 48 L74 78" stroke="#E3DCC8" stroke-width="7" stroke-linecap="round"/></svg>`,
    ghoul: `<svg viewBox="0 0 90 120"><path d="M22 110 L28 60 Q45 40 62 60 L68 110 Z" fill="#6E7F58" ${EDGE}/><circle cx="45" cy="38" r="20" fill="#8FA870" ${EDGE}/><circle cx="38" cy="36" r="4" fill="#D6503E"/><circle cx="52" cy="36" r="4" fill="#D6503E"/><path d="M36 48 l3 5 l3 -5 l3 5 l3 -5 l3 5" stroke="#F3EBDA" stroke-width="2" fill="none"/><path d="M28 64 L10 86 M62 64 L80 86" stroke="#8FA870" stroke-width="8" stroke-linecap="round"/></svg>`,
    wraith: `<svg viewBox="0 0 90 120"><path d="M45 10 C20 10 16 40 18 70 L10 112 L26 100 L36 114 L45 100 L54 114 L64 100 L80 112 L72 70 C74 40 70 10 45 10 Z" fill="#2B3350" stroke="#6FE0FF" stroke-width="3" opacity=".92"/><rect x="32" y="40" width="9" height="5" fill="#6FE0FF"/><rect x="50" y="40" width="9" height="5" fill="#6FE0FF"/></svg>`,
  };

  // ── class actions ────────────────────────────────────────────────────
  const CLASS_UI = {
    brawler: { strike: "Hammer Swing", special: "Haymaker", specialText: "3 energy · 2.8× hit", mult: 2.8 },
    runeblade: { strike: "Rune Strike", strikeText: "+2 energy", special: "Rune Burst", specialText: "3 energy · 2.2×, or 5 for 4×", mult: 2.2, strikeEnergy: 2 },
    hexcaster: { strike: "Hex Bolt", strikeText: "+1 energy · adds a curse", special: "Soul Drain", specialText: "3 energy · 2.2×, heals you", mult: 2.2, strikeMult: 0.9 },
    ranger: { strike: "Arrow", special: "Volley", specialText: "2–4 energy · an arrow per energy", mult: 0.65 },
    paladin: { strike: "Mace", special: "Smite", specialText: "3 energy · 2.2×, heals 15%", mult: 2.2, guardText: "block and heal 10%" },
    beastmaster: { strike: "Spear Jab", special: "Call Beast", specialText: "3 energy · random wolf, hawk or bear", mult: 1.5, strikeMult: 0.9 },
    necromancer: { strike: "Bone Dart", special: "Raise Dead", specialText: "2–4 energy · pick a minion", mult: 1, strikeMult: 0.7, guard: "Bone Shield", guardText: "you and your minions block" },
  };

  const $ = (id) => document.getElementById(id);
  const rnd = (a, b) => a + Math.random() * (b - a);
  const pick = (xs) => xs[Math.floor(Math.random() * xs.length)];
  // Auto battle plays the animations faster.
  const wait = (ms) => new Promise((r) => setTimeout(r, matchMedia("(prefers-reduced-motion: reduce)").matches ? Math.min(ms, 120) : run && run.auto ? ms * 0.4 : ms));
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  let cfg, hooks, run, foe, root;

  const MARKUP = `
    <div class="dg-top"><div><div class="dg-book" id="dg-book"></div><h2 id="dg-floor">Floor 1</h2></div><div class="dg-track" id="dg-track"></div></div>
    <div class="dg-hud" id="dg-hud"></div>
    <div class="dg-xp" id="dg-xp"></div>
    <div class="dg-boons" id="dg-boons"></div>
    <section id="dg-map">
      <div class="dg-system"><b>SYSTEM AI</b><span id="dg-msg"></span></div>
      <button class="dg-leave" id="dg-leave">Back to hub · your place is saved</button>
      <div class="dg-doors" id="dg-doors"></div>
      <button class="btn alt dg-supply-btn" id="dg-lantern" hidden>Light the Lantern<small>see exactly what's behind both doors</small></button>
      <div class="dg-boonpick" id="dg-boonpick" hidden></div>
      <button class="btn alt" id="dg-continue" hidden>Continue</button>
    </section>
    <section id="dg-battle" hidden>
      <div class="dg-stage" id="dg-stage">
        <div class="dg-actor sticker" id="dg-hero"></div>
        <div class="dg-pets" id="dg-pets"></div>
        <div class="dg-actor dg-idle" id="dg-foe"></div>
      </div>
      <div class="dg-bars">
        <div class="dg-bar me"><div class="nm" id="dg-me-name"></div><div class="hp"><i id="dg-php"></i><span id="dg-phptext"></span></div><div class="dg-energy" id="dg-energy"></div></div>
        <div class="dg-bar"><div class="nm" id="dg-fname"></div><div class="hp"><i id="dg-fhp"></i><span id="dg-fhptext"></span></div><div class="dg-intent" id="dg-intent"></div></div>
      </div>
      <div class="dg-system" aria-live="polite"><b>SYSTEM AI</b><span id="dg-log"></span></div>
      <div class="dg-actions">
        <button class="btn act-strike" id="dg-a-strike"></button>
        <button class="btn act-power" id="dg-a-power"></button>
        <button class="btn act-guard" id="dg-a-guard"></button>
        <button class="btn act-potion" id="dg-a-potion"></button>
      </div>
      <div class="dg-actions" id="dg-raise" hidden></div>
      <button class="btn ghost dg-supply-btn" id="dg-smoke" hidden>Throw a Smoke Bomb<small>escape this fight · no kill, no XP</small></button>
      <button class="btn alt dg-auto" id="dg-auto" aria-pressed="false" hidden>Auto battle <i class="light" aria-hidden="true"></i></button>
    </section>
    <section id="dg-end" hidden></section>`;

  // ── start / screens ──────────────────────────────────────────────────
  function start(runCfg, h) {
    cfg = runCfg; hooks = h;
    root = $("dungeon");
    root.innerHTML = MARKUP;
    const s = cfg.stats;
    const packed = cfg.supplies || {};
    run = { floor: 0, step: 0, hp: s.hp, energy: 0, potions: s.potions + (packed.potion || 0), buffAtk: 0, xpEst: 0, kills: 0, elites: 0,
      busy: false, boons: {}, pets: [], over: false, used: {}, drunk: 0, doors: [],
      feats: { low: 1, clutch: false, overcharge_boss: false, loot_boxes: 0, pets: [], seen: {} } };  // badges + Bestiary
    root.classList.toggle("dg-practice", !!cfg.practice);
    root.classList.remove("dg-raid");
    root.classList.toggle("dg-null", !!cfg.null);  // January after the Regent escaped
    $("dg-pets").dataset.skin = cfg.pet_skin || "";  // Wardrobe pet skin (dungeon.css)
    const look = window.DungeonThemes && DungeonThemes.THEMES[cfg.theme] ? cfg.theme : "dungeon";
    $("dg-book").textContent = (window.DungeonThemes ? `${cfg.title} · ${DungeonThemes.THEMES[look].name}` : cfg.title) + (cfg.null ? " · the Null spreads" : "");
    if (window.DungeonThemes) $("dg-stage").insertAdjacentHTML("afterbegin", DungeonThemes.stage(look));  // backdrop from the book's genre
    if (cfg.practice) $("dg-leave").textContent = "Quit practice · nothing is saved";
    $("dg-me-name").textContent = cfg.username || "You";
    for (const a of ["strike", "power", "guard", "potion"]) $("dg-a-" + a).onclick = () => playerAct(a);
    $("dg-auto").onclick = () => setAuto(!run.auto);
    $("dg-leave").onclick = () => { run.over = true; hooks.onLeave && hooks.onLeave(); };
    $("dg-lantern").onclick = useLantern;
    $("dg-smoke").onclick = useSmoke;
    const p = cfg.progress;
    if (cfg.null && !p) toast("The Null spreads", "#22305A");
    exploreMusic();
    if (!p) { toast(`Floor 1`, "var(--navy)"); return renderMap(window.DungeonThemes ? DungeonThemes.THEMES[look].intro : pick(SAY.door)); }
    // Resume where the player left off.
    for (const k of ["floor", "step", "hp", "potions", "buffAtk", "xpEst", "kills", "elites", "drunk", "lastGift"]) if (typeof p[k] === "number") run[k] = p[k];
    run.boons = p.boons || {};
    run.used = p.used || {};
    if (p.feats) run.feats = { ...run.feats, ...p.feats };
    toast("Welcome back", "var(--navy)");
    if (p.next === "fight" && findMonster(p.fight)) return startBattle(p.fight, "You're back. The fight starts over.", p.mods);
    if (p.next === "advance") return advance();
    if (p.next === "boon_advance") return offerBoon("Welcome back. " + SAY.boon, advance);
    if (p.next === "boon_map") return offerBoon("Welcome back. " + SAY.boon, () => renderMap("The monsters get meaner from here."));
    renderMap("Welcome back, crawler. The dungeon waited. It had no choice.", p.doors, p.revealed);
  }
  // Checkpoint: where to pick up if the player leaves now.
  function save(next, extra = {}) {
    if (!hooks.onSave || run.over) return;
    const { floor, step, hp, potions, buffAtk, xpEst, kills, elites, boons, used, drunk, feats, lastGift } = run;
    hooks.onSave({ next, floor, step, hp, potions, buffAtk, xpEst, kills, elites, boons, used, drunk, feats, lastGift, supplies_used: suppliesUsed(), ...extra });
  }
  // ── the December boss: one long fight against the shared health bar ──
  function raid(attackCfg, h) {
    cfg = attackCfg; hooks = h;
    root = $("dungeon");
    root.innerHTML = MARKUP;
    root.classList.remove("dg-practice", "dg-null"); root.classList.add("dg-raid");
    const s = cfg.stats;
    run = { raid: true, turn: 0, floor: 0, step: 0, hp: s.hp, energy: 0, potions: s.potions, buffAtk: 0, xpEst: 0, kills: 0, elites: 0,
      busy: false, boons: {}, pets: [], over: false, used: {}, drunk: 0, doors: [],
      feats: { low: 1, clutch: false, overcharge_boss: false, loot_boxes: 0, pets: [], seen: {} } };
    $("dg-pets").dataset.skin = cfg.pet_skin || "";
    $("dg-book").textContent = `${cfg.title} · ${cfg.slot_name}`;
    if (window.DungeonThemes) $("dg-stage").insertAdjacentHTML("afterbegin", DungeonThemes.stage("regent"));
    $("dg-me-name").textContent = cfg.username || "You";
    for (const a of ["strike", "power", "guard", "potion"]) $("dg-a-" + a).onclick = () => playerAct(a);
    $("dg-auto").onclick = () => setAuto(!run.auto);
    const b = cfg.boss;
    foe = { id: b.id, role: "boss", kind: "boss", name: b.name, base: b.name, mods: new Set(), maxHp: b.max_hp, hp: b.hp,
      atk: b.atk, xp: b.xp, moves: b.moves, turn: 0, enraged: b.hp < b.max_hp / 2, charged: false, hex: 0,
      art: window.Regent ? Regent.art({ height: 240 }) : "", h: null, moveNames: {}, barks: [], shielded: false };
    run.poison = 0; run.weak = 0;
    run.energy = Math.min(s.energy, s.start_energy || 0);
    planIntent();
    $("dg-hero").innerHTML = CrawlerArt.render(cfg.look, cfg.cls, { height: 190 });
    $("dg-foe").innerHTML = foe.art; $("dg-foe").className = "dg-actor dg-idle";
    $("dg-fname").textContent = foe.name;
    const c = cls();
    $("dg-a-strike").innerHTML = `${c.strike}<small>${c.strikeText || "+1 energy"}</small>`;
    $("dg-a-guard").innerHTML = `${c.guard || "Guard"}<small>${c.guardText || "block most damage"}</small>`;
    const flying = (cfg.banners || []).map((k) => BANNER_NAMES[k]).filter(Boolean);
    log(`The Null Regent looks up from his terminal. "${pick(regentLines())}"${cfg.momentum ? ` Momentum: +${cfg.momentum}% damage.` : ""}${flying.length ? ` Flying: ${flying.join(", ")}.` : ""}`);
    raidHeader(); renderPets(); renderBattle(); showPart("dg-battle");
    $("dg-auto").hidden = true;  // the Null Regent is always fought by hand
    toast(cfg.slot_name === "Christmas" ? "Christmas attack!" : "Attack!", "#22305A");
    window.Music && Music.play("regent");
    if (cfg.cls === "ranger") openingShot();
  }
  // ── the Arena: one fight against another crawler's ghost ──────────────
  // The ghost has its owner's real stats (health, attack, defense, crit,
  // potions), their look, and a move script for their class (GHOST_MOVES on
  // the server). Your hits lose half its defense, like its hits on you.
  function duel(duelCfg, h) {
    cfg = duelCfg; hooks = h;
    root = $("dungeon");
    root.innerHTML = MARKUP;
    root.classList.remove("dg-practice", "dg-null", "dg-raid"); root.classList.add("dg-duel");
    const s = cfg.stats, g = cfg.ghost;
    run = { duel: true, turn: 0, floor: 0, step: 0, hp: s.hp, energy: 0, potions: s.potions, buffAtk: 0, xpEst: 0, kills: 0, elites: 0,
      busy: false, boons: {}, pets: [], over: false, used: {}, drunk: 0, doors: [],
      feats: { low: 1, clutch: false, overcharge_boss: false, loot_boxes: 0, pets: [], seen: {} } };
    $("dg-pets").dataset.skin = cfg.pet_skin || "";
    $("dg-book").textContent = `The Arena · #${g.your_rank} vs #${g.rank}`;
    if (window.DungeonThemes) $("dg-stage").insertAdjacentHTML("afterbegin", DungeonThemes.stage("dungeon"));
    $("dg-me-name").textContent = cfg.username || "You";
    for (const a of ["strike", "power", "guard", "potion"]) $("dg-a-" + a).onclick = () => playerAct(a);
    $("dg-auto").onclick = () => setAuto(!run.auto);
    const gs = g.stats, gname = `${g.username.toUpperCase()}'s ghost`;
    foe = { id: "ghost", role: "duel", kind: "duel", name: gname, base: gname, mods: new Set(), maxHp: gs.hp, hp: gs.hp,
      atk: gs.atk, def: gs.def, crit: gs.crit, potions: gs.potions, potionHeal: gs.potion_heal, xp: 0, moves: g.moves, turn: 0,
      enraged: false, charged: false, hex: 0, h: null, moveNames: g.move_names || {}, shielded: false,
      barks: ["You read that slowly. I can tell.", "My owner finished that series. Have you?", "Bookmarks won't save you.", "I've seen your Tier List."],
      art: `<div class="ghost-art">${CrawlerArt.render(g.look, g.cls, { height: 190 })}</div>` };
    run.poison = 0; run.weak = 0;
    run.energy = Math.min(s.energy, s.start_energy || 0);
    planIntent();
    $("dg-hero").innerHTML = CrawlerArt.render(cfg.look, cfg.cls, { height: 190 });
    $("dg-foe").innerHTML = foe.art; $("dg-foe").className = "dg-actor dg-idle dg-ghost";
    $("dg-fname").textContent = foe.name;
    const c = cls();
    $("dg-a-strike").innerHTML = `${c.strike}<small>${c.strikeText || "+1 energy"}</small>`;
    $("dg-a-guard").innerHTML = `${c.guard || "Guard"}<small>${c.guardText || "block most damage"}</small>`;
    log(`${gname} steps out of the mist: a Level ${g.level} ${g.cls.charAt(0).toUpperCase() + g.cls.slice(1)} with every piece of their gear. Their stats are real.`);
    duelHeader(); renderPets(); renderBattle(); showPart("dg-battle");
    $("dg-auto").hidden = false; setAuto(false);
    toast("Duel!", "#22305A");
    window.Music && Music.play("boss", cfg.title, "dungeon");
    if (cfg.cls === "ranger") openingShot(); else autoSoon();
  }
  function duelHeader() {
    $("dg-floor").textContent = `Turn ${run.turn + 1} of ${cfg.turns}`;
    $("dg-track").innerHTML = `<span class="raid-dmg">vs <b>${esc(cfg.ghost.username.toUpperCase())}</b></span>`;
  }
  const pct = (hp, max) => Math.round((1000 * Math.max(0, hp)) / Math.max(1, max)) / 10;
  const BANNER_NAMES = { war: "War Banner", mending: "Banner of Mending", resolve: "Banner of Resolve", defiance: "Banner of Defiance", pack: "Banner of the Pack", bulwark: "Banner of the Bulwark" };
  // What the Regent says, built from the player's real year of listening.
  function regentLines() {
    const t = cfg.taunts || {};
    const lines = ["I am the System Administrator. Your subscription has expired.", "Every book you finished, I archived. Every one you didn't, I deleted."];
    if (t.books) lines.push(`${t.books} book${t.books === 1 ? "" : "s"} this year. I've sat through longer loading screens.`);
    else lines.push("Not one book finished this year, and you still showed up? Bold.");
    if (t.hours) lines.push(`${t.hours} hours of listening this year. I'll make the next ten minutes feel longer.`);
    if (t.longest) lines.push(`You made it through all of ${t.longest}. You can make it through me. Probably not.`);
    return lines;
  }
  function raidDealt() { return Math.max(0, cfg.boss.hp - foe.hp); }
  function raidHeader() {
    $("dg-floor").textContent = `Turn ${run.turn + 1}`;
    const rage = Math.round(100 * (cfg.escalate || 0) * run.turn);
    $("dg-track").innerHTML = `<span class="raid-dmg">Damage dealt <b>${raidDealt().toLocaleString()}</b></span>${rage ? `<span class="raid-rage">Regent +${rage}%</span>` : ""}`;
  }
  const cls = () => CLASS_UI[cfg.cls] || CLASS_UI.brawler;
  function stats() {
    const s = cfg.stats;
    const atk = s.atk + run.buffAtk;
    return { ...s, hp: Math.round(s.hp * (run.boons.vigor ? 1.2 : 1)), atk: Math.max(1, atk - Math.min(run.weak || 0, Math.floor(atk * 0.4))), def: s.def + (run.boons.iron ? 3 : 0) };
  }
  function showPart(id) {
    for (const k of ["dg-map", "dg-battle", "dg-end"]) $(k).hidden = k !== id;
    root.classList.toggle("dg-ending", id === "dg-end");  // results screen hides the in-run header
    window.scrollTo(0, 0);
  }
  function toast(text, bg = "var(--red)") {
    const t = document.createElement("div");
    t.className = "stamp dg-toast"; t.style.background = bg; t.textContent = text;
    document.body.appendChild(t); setTimeout(() => t.remove(), 1700);
  }
  function hud() {
    const s = stats();
    run.feats.low = Math.min(run.feats.low, run.hp / s.hp);
    $("dg-hud").innerHTML = `<span class="hud-hp" role="img" aria-label="Health ${run.hp} of ${s.hp}"><i style="width:${Math.max(0, Math.min(100, (100 * run.hp) / s.hp))}%"></i><b>${run.hp} / ${s.hp} HP</b></span><span>Potions <b>${run.potions}</b></span><span>ATK <b>${s.atk}</b></span><span>DEF <b>${s.def}</b></span>`;
    const need = cfg.xp_next || 50;
    const pct = Math.min(100, (100 * ((cfg.xp || 0) + run.xpEst)) / need);
    $("dg-xp").innerHTML = `<b>Lv ${cfg.level}</b><div class="xpbar"><i style="width:${pct}%"></i></div><span>+${Math.round(run.xpEst)} XP so far</span>`;
    const left = supplyLeft();
    $("dg-boons").innerHTML = Object.keys(run.boons).map((k) => `<span class="boon-chip">${BOONS[k].name}${run.boons[k] > 1 ? " ×" + run.boons[k] : ""}</span>`).join("")
      + Object.entries(left).filter(([, n]) => n).map(([k, n]) => `<span class="boon-chip supply">${SUPPLY_NAMES[k]}${n > 1 ? " ×" + n : ""}</span>`).join("");
  }
  // ── supplies (packed from the System Store) ──────────────────────────
  const SUPPLY_NAMES = { potion: "Extra Potion", lantern: "Lantern", smoke: "Smoke Bomb", coin: "Lucky Coin" };
  function supplyLeft() {
    const packed = cfg.supplies || {}, out = {};
    for (const k of Object.keys(packed)) out[k] = Math.max(0, packed[k] - (suppliesUsed()[k] || 0));
    return out;
  }
  // Extra potions count as used only once you drink past your normal ones.
  function suppliesUsed() {
    const packed = cfg.supplies || {};
    return { ...run.used, potion: Math.max(0, Math.min(packed.potion || 0, run.drunk - cfg.stats.potions)) };
  }
  function useLantern() {
    if (!supplyLeft().lantern || !run.doors.length) return;
    run.used.lantern = (run.used.lantern || 0) + 1;
    showReveal();
    $("dg-msg").textContent = "The Lantern flares. Now you know. The System hates when you know.";
    hud(); save("map", { doors: run.doors, revealed: true });
  }
  function showReveal() {
    $("dg-lantern").hidden = true;
    document.querySelectorAll(".dg-door").forEach((el, i) => { el.querySelector(".ddesc").textContent = reveal(run.doors[i]); el.classList.add("revealed"); });
  }
  function reveal(d) {
    const M = cfg.monsters, mods = (d.mods || []).map((m) => M.modifiers[m].name + " ").join("");
    const name = (id) => { const m = findMonster(id); return m ? mods + m.name : "something"; };
    switch (d.real) {
      case "monster": return `Fight: ${name(d.monster)}`;
      case "elite": return `Elite: ${name(d.monster)}`;
      case "treasure": return d.loot === "potion" ? "Loot: a healing potion" : "Loot: +2 attack for this dungeon";
      case "shrine": return "Heal half your health";
      case "trap": return d.trapHit ? "Trap! It will hurt." : "Empty. The trap is broken.";
      default: return "";
    }
  }
  function useSmoke() {
    if (run.busy || run.over || !supplyLeft().smoke || foe.role === "boss") return;
    run.used.smoke = (run.used.smoke || 0) + 1;
    $("dg-smoke").hidden = true; run.pets = [];
    afterEvent(`You vanish in a cloud of smoke. ${foe.base} is very confused.`);
  }

  // ── map / doors ──────────────────────────────────────────────────────
  const DOORS = {
    monster: { name: "Monster", desc: "A normal fight. Safe XP." },
    elite: { name: "Elite", desc: "Tough fight. Double XP and a gift." },
    treasure: { name: "Loot Box", desc: "Something useful. Probably." },
    shrine: { name: "Shrine", desc: "Heal half your health." },
    trap: { name: "Hallway", desc: "Quiet. Too quiet." },
    mystery: { name: "???", desc: "Could be anything." },
  };
  function rollDoorType() {
    const w = [["monster", 42], ["elite", run.floor === 0 && run.step === 0 ? 0 : 14], ["treasure", 16], ["shrine", 12], ["trap", 10], ["mystery", 6]];
    let r = Math.random() * w.reduce((t, [, n]) => t + n, 0);
    for (const [k, n] of w) { if ((r -= n) < 0) return k; }
    return "monster";
  }
  const doorHtml = (type, name, desc, i) => `<button class="dg-door" data-i="${i}">${DOOR_ART[type]}<span class="dname">${name}</span><span class="ddesc">${desc}</span></button>`;
  // Decide what's behind a door when it appears (so the Lantern can show it).
  function makeDoor(type) {
    const M = cfg.monsters;
    const real = type === "mystery" ? (Math.random() < 0.5 ? "treasure" : "elite") : type;
    const d = { type, real };
    if (real === "monster" || real === "elite") {
      const def = real === "elite" ? pick(M.elite.length ? M.elite : M.regular) : pick(M.regular);
      d.monster = def.id; d.mods = rollMods(def);
    }
    if (real === "treasure") d.loot = Math.random() < 0.45 ? "potion" : "buff";
    if (real === "trap") d.trapHit = Math.random() >= 0.35;
    return d;
  }
  function header() {
    const F = cfg.floors;
    $("dg-floor").textContent = `Floor ${Math.min(run.floor + 1, F.length)} of ${F.length}`;
    const total = F.reduce((a, b) => a + b, 0);
    const done = F.slice(0, run.floor).reduce((a, b) => a + b, 0) + run.step;
    $("dg-track").innerHTML = Array.from({ length: total }, (_, i) => `<i class="${i < done ? "done" : i === done ? "now" : ""}"></i>`).join("") + `<i class="boss ${done >= total ? "now" : ""}"></i>`;
    hud();
  }
  function renderMap(message, savedDoors, revealed) {
    const F = cfg.floors;
    header();
    $("dg-msg").textContent = message;
    $("dg-continue").hidden = true; $("dg-boonpick").hidden = true;
    const doors = $("dg-doors"); doors.hidden = false;
    if (run.floor >= F.length) {
      run.doors = [{ type: "boss", real: "boss" }, { type: "exit", real: "exit" }];
      doors.innerHTML = doorHtml("boss", "Floor Boss", "Better loot if you win.", 0) + doorHtml("exit", "Take the Stairs", "Leave now with normal loot.", 1);
    } else {
      if (savedDoors && savedDoors.length === 2) run.doors = savedDoors;
      else {
        let a = rollDoorType(), b = rollDoorType();
        while (b === a) b = rollDoorType();
        run.doors = [makeDoor(a), makeDoor(b)];
      }
      doors.innerHTML = run.doors.map((d, i) => doorHtml(d.type, DOORS[d.type].name, DOORS[d.type].desc, i)).join("");
    }
    doors.querySelectorAll(".dg-door").forEach((d) => d.addEventListener("click", () => chooseDoor(Number(d.dataset.i))));
    $("dg-lantern").hidden = !(supplyLeft().lantern && run.floor < F.length);
    $("dg-leave").hidden = false;
    showPart("dg-map"); exploreMusic();
    if (revealed) showReveal();
    save("map", { doors: run.doors, revealed: !!revealed });
  }
  function afterEvent(message, then = advance) {
    showPart("dg-map"); header(); exploreMusic();
    $("dg-msg").textContent = message;
    $("dg-doors").hidden = true; $("dg-boonpick").hidden = true; $("dg-lantern").hidden = true;
    const c = $("dg-continue"); c.hidden = false; c.onclick = then;
    $("dg-leave").hidden = false;
    save(then === advance ? "advance" : "boon_advance");
  }
  const roomIndex = () => cfg.floors.slice(0, run.floor).reduce((a, b) => a + b, 0) + run.step;
  function offerBoon(message, then) {
    // Never two gifts in a row (an elite's gift right before the stairs' gift): skip the second.
    if (run.lastGift !== undefined && run.lastGift !== null && roomIndex() - run.lastGift <= 1) { run.lastGift = null; return then(); }
    run.lastGift = roomIndex();
    showPart("dg-map"); header();
    $("dg-leave").hidden = false;
    save(then === advance ? "boon_advance" : "boon_map");
    $("dg-msg").textContent = message;
    $("dg-doors").hidden = true; $("dg-continue").hidden = true; $("dg-lantern").hidden = true;
    const pool = Object.keys(BOONS).filter((k) => BOONS[k].repeat || !run.boons[k]);
    const opts = [];
    while (opts.length < 3 && pool.length) opts.push(pool.splice(Math.floor(Math.random() * pool.length), 1)[0]);
    const el = $("dg-boonpick"); el.hidden = false;
    el.innerHTML = opts.map((k) => `<button class="dg-boon" data-b="${k}"><strong>${BOONS[k].name}</strong><span>${BOONS[k].text}</span></button>`).join("");
    el.querySelectorAll(".dg-boon").forEach((b) => b.addEventListener("click", () => {
      const k = b.dataset.b; run.boons[k] = (run.boons[k] || 0) + 1;
      if (k === "brew") run.potions++;
      if (k === "vigor") run.hp += Math.round(cfg.stats.hp * 0.2);
      toast(BOONS[k].name, "var(--mustard)"); then();
    }));
  }
  function advance() {
    run.step++;
    if (run.step >= cfg.floors[run.floor]) {
      run.floor++; run.step = 0;
      if (run.floor < cfg.floors.length) {
        toast(`Floor ${run.floor + 1}`, "var(--navy)");
        return offerBoon("Stairs down. " + SAY.boon, () => renderMap("The monsters get meaner from here."));
      }
      return renderMap(`${bossName()} is awake. Beat it for better loot. Or take the stairs and leave. Nobody will judge you. Out loud.`);
    }
    renderMap(doorLine());
  }
  // Music (music.js): each book composes its own theme; the look sets the mood.
  function exploreMusic() { window.Music && Music.play("explore", cfg.title, cfg.theme); }
  // Series looks mix their own System AI quips in with the usual ones.
  function seriesLook() { return window.DungeonThemes && DungeonThemes.THEMES[cfg.theme] && DungeonThemes.THEMES[cfg.theme].series ? DungeonThemes.THEMES[cfg.theme] : null; }
  function doorLine() { const sl = seriesLook(); return sl && Math.random() < 0.5 ? pick(sl.quips) : pick(SAY.door); }
  function bossName() { const sl = seriesLook(), b = cfg.monsters.boss; return sl && sl.boss && !b.series ? sl.boss.name : b.name; }
  function chooseDoor(i) {
    const s = stats(), d = run.doors[i], M = cfg.monsters;
    window.Music && Music.sfx("door");
    if (d.real === "monster" || d.real === "elite") return startBattle(d.monster, null, d.mods);
    if (d.real === "boss") return startBattle(M.boss.id);
    if (d.real === "exit") return finish("exit");
    if (d.real === "shrine") { run.hp = Math.min(s.hp, run.hp + Math.round(s.hp * 0.5)); return afterEvent(SAY.shrine); }
    if (d.real === "trap") {
      if (!d.trapHit) return afterEvent(SAY.trapDodge);
      run.hp = Math.max(1, run.hp - Math.round(s.hp * (0.12 + 0.04 * run.floor)));
      return afterEvent(SAY.trapHit);
    }
    if (d.real === "treasure") {
      run.feats.loot_boxes++; window.Music && Music.sfx("coin");
      if (d.loot === "potion") { run.potions++; return afterEvent(SAY.treasure.potion); }
      run.buffAtk += 2; return afterEvent(SAY.treasure.buff);
    }
  }

  // ── battle ───────────────────────────────────────────────────────────
  function findMonster(id) {
    const M = cfg.monsters;
    return [...M.regular, ...M.elite, M.boss].find((m) => m.id === id);
  }
  function rollMods(def) {
    const M = cfg.monsters, keys = Object.keys(M.modifiers || {});
    if (!keys.length) return [];
    const always = M.always_modded && def.role !== "regular";
    return always || Math.random() < M.modifier_chance ? [pick(keys)] : [];
  }
  function startBattle(id, openingLine, savedMods) {
    const def = findMonster(id), sc = cfg.enemy_scale;
    const mods = savedMods || rollMods(def);
    if (!(id in run.feats.seen)) run.feats.seen[id] = 0;  // Bestiary: met it
    window.Music && Music.play(def.role === "boss" ? "boss" : "battle", cfg.title, cfg.theme);
    save("fight", { fight: id, mods });
    const f = Math.min(run.floor, cfg.floors.length - 1);
    const floorScale = def.role === "boss" ? 1 : 1 + 0.3 * f;
    const modNames = mods.map((m) => cfg.monsters.modifiers[m].name);
    const sl = def.role === "boss" && !def.series ? seriesLook() : null;  // a villain from the books (name only), unless it's a monster made for this series
    const baseName = sl && sl.boss ? sl.boss.name : def.name;
    foe = { id, role: def.role, kind: def.role === "boss" ? "boss" : def.role === "elite" ? "bruiser" : "regular",
      name: baseName.startsWith("The ") ? ["The", ...modNames, baseName.slice(4)].join(" ") : [...modNames, baseName].join(" "), base: baseName, mods: new Set(mods), death: def.death,
      maxHp: Math.round(def.hp * floorScale * sc.hp * (mods.includes("armored") ? 1.1 : 1)), atk: Math.round(def.atk * (1 + 0.2 * f) * sc.atk),
      xp: def.xp * (1 + 0.25 * f) * sc.xp, moves: def.moves, turn: 0, enraged: false, charged: false, hex: 0,
      moveNames: def.move_names || {}, barks: def.barks || [], shielded: false, undead: !!def.undead };
    run.poison = 0; run.weak = 0;
    if (def.role === "elite") foe.maxHp = Math.max(foe.maxHp, Math.round(stats().hp * rnd(1.5, 2.0)));  // elites outlast you: 1.5–2× your health
    // Below level 25 a regular monster survives your first hit (crits included);
    // the guard in dealDamage catches the rare big special.
    if (def.role === "regular" && (cfg.level || 1) < ONE_SHOT_LEVEL) foe.maxHp = Math.max(foe.maxHp, Math.round(stats().atk * rnd(2.2, 2.8)));
    foe.hp = foe.maxHp;
    foe.art = def.art ? MonsterArt.render(def.art, { height: def.role === "boss" ? 230 : def.role === "elite" ? 190 : 165 }) : FOES[def.svg].svg;
    foe.h = def.art ? null : FOES[def.svg].h;
    foe.appear = sl && sl.boss ? sl.boss.appear : def.appear;
    run.energy = Math.min(stats().energy, (stats().start_energy || 0) + (run.boons.quick ? 2 : 0));
    run.pets = [];
    planIntent();
    $("dg-hero").innerHTML = CrawlerArt.render(cfg.look, cfg.cls, { height: 190 });
    $("dg-foe").innerHTML = foe.art; $("dg-foe").className = "dg-actor dg-idle";
    if (foe.h) $("dg-foe").style.setProperty("--foe-h", foe.h + "px"); else $("dg-foe").style.removeProperty("--foe-h");
    $("dg-fname").textContent = foe.name;
    const c = cls();
    $("dg-a-strike").innerHTML = `${c.strike}<small>${c.strikeText || "+1 energy"}</small>`;
    $("dg-a-guard").innerHTML = `${c.guard || "Guard"}<small>${c.guardText || "block most damage"}</small>`;
    const modText = [...foe.mods].map((m) => `${cfg.monsters.modifiers[m].name}: ${cfg.monsters.modifiers[m].text}.`).join(" ");
    log(openingLine || [foe.appear || pick(SAY.start).replace("%s", foe.name), modText].filter(Boolean).join(" "));
    $("dg-smoke").hidden = !(supplyLeft().smoke && def.role !== "boss");
    $("dg-auto").hidden = def.role === "boss";
    const locked = (cfg.level || 1) < AUTO_LEVEL;  // learn to fight first
    $("dg-auto").disabled = locked;
    $("dg-auto").innerHTML = locked ? `Auto battle <small>unlocks at level ${AUTO_LEVEL}</small><i class="light off" aria-hidden="true"></i>` : `Auto battle <i class="light" aria-hidden="true"></i>`;
    setAuto(false);  // switched on per fight
    renderPets(); renderBattle(); showPart("dg-battle");
    if (cfg.cls === "ranger") openingShot(); else autoSoon();
  }
  async function openingShot() {
    run.busy = true; renderBattle(); await wait(500);
    const { dmg, crit } = rollHit(stats().atk, 1);
    await dealDamage(dmg, crit, "Opening shot");
    run.busy = false; renderBattle();
    if (foe.hp <= 0) return winBattle();
    autoSoon();
  }
  function planIntent() {
    if (foe.charged) { foe.intent = "slam"; return; }
    if (run.duel && foe.potions > 0 && foe.hp < foe.maxHp * 0.35) { foe.intent = "quaff"; return; }
    foe.intent = foe.moves[foe.turn % foe.moves.length]; foe.turn++;
  }
  // The Regent hits harder every turn (cfg.escalate); everyone else doesn't.
  function foeAtk() {
    const base = foe.atk + (foe.enraged ? 4 : 0);
    return run.raid ? Math.round(base * (1 + (cfg.escalate || 0) * run.turn)) : base;
  }
  function intentText() {
    const [txt, danger] = baseIntent();
    const nm = foe.moveNames && foe.moveNames[foe.intent];
    if (!nm) return [txt, danger];
    const cut = txt.indexOf(": ");  // "Poison: about 2 now…" -> "Dust of Rot: about 2 now…"
    const rest = cut > 0 && cut < 24 ? txt.slice(cut + 2) : txt.charAt(0).toLowerCase() + txt.slice(1);
    return [`${nm}: ${rest}`, danger];
  }
  function baseIntent() {
    const a = foeAtk();
    switch (foe.intent) {
      case "attack": return [`Attacking for about ${a}`, false];
      case "heavy": return [`Heavy hit for about ${Math.round(a * 2)}. Guard!`, true];
      case "frenzy": return [`Frenzy: 2 hits of about ${Math.round(a * 0.7)}`, false];
      case "spit": return [`Acid spit for ${Math.round(a * 1.2)}, ignores armor`, false];
      case "rage": return ["Getting angry (+3 attack)", false];
      case "windup": return ["Winding up something huge…", true];
      case "slam": return [`GROUND SLAM for about ${Math.round(a * 2.8)}. Guard!`, true];
      case "gorge": return ["Eating a snack (heals)", false];
      case "drain": return [`Life drain for about ${a}, heals itself`, false];
      case "purge": return [`Null Purge for about ${a}, wipes your energy`, false];
      case "cascade": return [`Cascade Failure: about ${Math.round(a * 1.1)} to you AND every pet`, true];
      case "poison": return [`Poison: about ${Math.round(a * 0.6)} now, then ${Math.max(1, Math.round(a * 0.35))} a turn for 3 turns`, false];
      case "weaken": return [`Weakening hit for about ${Math.round(a * 0.7)}. Lowers your attack`, false];
      case "shield": return ["Raising its guard: half damage until its next turn", false];
      case "wipe": return [`SYSTEM WIPE for about ${Math.round(a * 1.6)}. Can't be guarded!`, true];
      case "quaff": return [`Drinking a potion (${foe.potions} left)`, false];
    }
  }
  const minPower = () => (cfg.cls === "necromancer" || cfg.cls === "ranger" ? 2 : cfg.cls === "beastmaster" ? 3
    : Math.min(...(POWERS[cfg.cls] || [[0, 0, 3]]).map((p) => p[2])));
  function specialLabel() {
    if (cfg.cls === "necromancer") return `Raise Dead<small>2–4 energy · pick a minion</small>`;
    if (cfg.cls === "ranger") return `Volley<small>${run.energy >= 2 ? `${run.energy} arrows` : "needs 2 energy"} · 65% each</small>`;
    if (cfg.cls === "beastmaster") {
      const beast = run.pets[0];
      return beast && BEAST_MOVE[beast.kind] ? `${BEAST_MOVE[beast.kind][0]}<small>3 energy · ${BEAST_MOVE[beast.kind][1]}</small>` : `Call Beast<small>3 energy · a random wolf, hawk or bear</small>`;
    }
    return `${MENU_NAME[cfg.cls] || "Powers"}<small>tap to choose · from ${minPower()} energy</small>`;
  }
  function renderBattle() {
    const s = stats();
    run.feats.low = Math.min(run.feats.low, run.hp / s.hp);
    $("dg-php").style.width = `${Math.max(0, (100 * run.hp) / s.hp)}%`;
    $("dg-phptext").textContent = `${run.hp} / ${s.hp} HP`;
    $("dg-energy").innerHTML = Array.from({ length: s.energy }, (_, i) => `<i class="${i < run.energy ? "on" : ""}"></i>`).join("");
    $("dg-fhp").style.width = `${(100 * foe.hp) / foe.maxHp}%`;
    $("dg-fhptext").textContent = run.raid ? `${foe.hp.toLocaleString()} / ${foe.maxHp.toLocaleString()} · ${(100 * foe.hp / foe.maxHp).toFixed(1)}%${foe.hex ? ` · cursed ×${foe.hex}` : ""}`
      : `${foe.hp} / ${foe.maxHp} HP${foe.hex ? ` · cursed ×${foe.hex}` : ""}${foe.shielded ? " · guarded" : ""}`;
    if (run.raid) raidHeader();
    if (run.duel) duelHeader();
    const [txt, danger] = intentText();
    $("dg-intent").textContent = "Next: " + txt;
    $("dg-intent").className = "dg-intent" + (danger ? " danger" : "");
    $("dg-a-power").innerHTML = specialLabel();
    $("dg-a-power").disabled = run.energy < minPower() || run.busy;
    $("dg-a-potion").innerHTML = `Potion<small>${run.potions} left · heal ${Math.round(s.potion_heal * 100)}%</small>`;
    $("dg-a-potion").disabled = run.potions < 1 || run.busy || run.hp >= s.hp;
    $("dg-a-strike").disabled = $("dg-a-guard").disabled = run.busy;
    $("dg-smoke").disabled = run.busy;
    hud();
  }
  function renderPets() {
    $("dg-pets").innerHTML = run.pets.map((p, i) => `<div class="dg-pet sticker" data-i="${i}">${PET_ART[p.kind]}<div class="pet-hp"><i style="width:${(100 * p.hp) / p.maxHp}%"></i></div></div>`).join("");
  }
  function log(t) { $("dg-log").textContent = t; }
  function floatNum(el, text, c = "") {
    const stage = $("dg-stage").getBoundingClientRect(), r = el.getBoundingClientRect();
    const f = document.createElement("div");
    f.className = "dg-float " + c; f.textContent = text;
    f.style.left = `${r.left - stage.left + r.width / 2 - 20 + rnd(-14, 14)}px`; f.style.top = `${r.top - stage.top + 10}px`;
    $("dg-stage").appendChild(f); setTimeout(() => f.remove(), 950);
  }
  function jolt(el, c) { el.classList.remove(c); void el.offsetWidth; el.classList.add(c); }
  function rollHit(atk, mult, forceCrit = false) {
    const s = stats();
    const crit = forceCrit || Math.random() < s.crit + (run.boons.keen ? 0.15 : 0);
    const fury = run.boons.fury && run.hp < s.hp / 2 ? 1.4 : 1;
    return { dmg: Math.max(1, Math.round(atk * rnd(0.85, 1.15) * mult * fury * (crit ? (cfg.cls === "ranger" ? 1.9 : 1.75) : 1))), crit };
  }
  async function dealDamage(dmg, crit, label, from = $("dg-hero")) {
    if (run.duel && foe.def) dmg = Math.max(1, dmg - Math.round(foe.def * 0.5));   // a ghost blocks like you do
    if (foe.mods && foe.mods.has("armored")) dmg = Math.max(1, Math.round(dmg * 0.7));
    if (foe.shielded) dmg = Math.max(1, Math.round(dmg * 0.5));
    from.classList.add("lunge-r"); await wait(170); from.classList.remove("lunge-r");
    // No one-hit kills from full health (owner, 2026-10-01): never on elites or
    // bosses, and not on regular monsters until level 25 (then it feels earned).
    const guarded = foe.role !== "regular" || (cfg.level || 1) < ONE_SHOT_LEVEL;
    let staggered = false;
    if (guarded && foe.hp === foe.maxHp && dmg >= foe.hp) { dmg = foe.hp - Math.max(1, Math.round(foe.maxHp * 0.08)); staggered = true; }
    foe.hp = Math.max(0, foe.hp - dmg);
    window.Music && Music.sfx(crit ? "crit" : "hit");
    jolt($("dg-foe"), "hit"); if (dmg > stats().atk * 2) jolt($("dg-stage"), "shake");
    floatNum($("dg-foe"), dmg, crit ? "crit" : "");
    if (run.boons.vamp && from.id === "dg-hero") run.hp = Math.min(stats().hp, run.hp + Math.max(1, Math.round(dmg * 0.15)));
    log(`${label}${crit ? " (critical!)" : ""}: ${dmg} damage.${staggered ? ` ${foe.base} staggers, but it's still standing!` : ""}`);
    renderBattle(); await wait(380);
  }
  async function summon(kind = pick(PET_POOL[cfg.cls])) {
    const def = PETS[kind], maxHp = Math.round(stats().hp * def.hp * (run.raid ? cfg.pet_hp || 1 : 1));
    run.pets.push({ kind, hp: maxHp, maxHp, shield: 0 });
    if (!run.feats.pets.includes(kind)) run.feats.pets.push(kind);
    renderPets(); toast(`${def.name}!`, "var(--mustard)");
    log(cfg.cls === "necromancer" ? `The ground cracks. A ${def.name.toLowerCase()} claws its way out.` : `A ${def.name.toLowerCase()} answers your call.`);
    await wait(450);  // the new minion arrives swinging: it acts with the others this turn
  }
  // Necromancer: pick which minion to raise (or mend the ones you have).
  function openRaiseMenu() {
    if (run.busy) return;
    const full = run.pets.length >= MAX_MINIONS;
    const opt = (id, label, sub, cost, off) => `<button class="btn act-power" data-raise="${id}" ${off || run.energy < cost ? "disabled" : ""}>${label}<small>${sub}</small></button>`;
    $("dg-raise").innerHTML = Object.keys(RAISE_COST).map((k) => opt(k, PETS[k].name, `${RAISE_COST[k]} energy · ${PETS[k].blurb}`, RAISE_COST[k], full)).join("")
      + (run.pets.length ? opt("mend", "Mend Flesh", "3 energy · heal your minions", 3, false) : "")
      + `<button class="btn alt" data-raise="back">Back<small>${full ? "you have 2 minions (max)" : "keep your energy"}</small></button>`;
    $("dg-raise").querySelectorAll("[data-raise]").forEach((b) => b.addEventListener("click", () => {
      closeRaiseMenu();
      if (b.dataset.raise !== "back") playerAct("power", b.dataset.raise);
    }));
    $("dg-raise").hidden = false; document.querySelector("#dg-battle .dg-actions:not(#dg-raise)").hidden = true;
  }
  // Everyone else: pick a power.
  function openPowerMenu() {
    if (run.busy) return;
    const off = (id) => id === "detonate" && !foe.hex;
    $("dg-raise").innerHTML = (POWERS[cfg.cls] || []).map(([id, name, cost, text]) =>
      `<button class="btn act-power" data-raise="${id}" ${run.energy < cost || off(id) ? "disabled" : ""}>${name}<small>${cost} energy · ${text}</small></button>`).join("")
      + `<button class="btn alt" data-raise="back">Back<small>keep your energy</small></button>`;
    $("dg-raise").querySelectorAll("[data-raise]").forEach((b) => b.addEventListener("click", () => {
      closeRaiseMenu();
      if (b.dataset.raise !== "back") playerAct("power", b.dataset.raise);
    }));
    $("dg-raise").hidden = false; document.querySelector("#dg-battle .dg-actions:not(#dg-raise)").hidden = true;
  }
  function closeRaiseMenu() { $("dg-raise").hidden = true; document.querySelector("#dg-battle .dg-actions:not(#dg-raise)").hidden = false; }
  async function playerAct(action, choice) {
    if (run.busy || run.over) return;
    if (action === "power" && !choice) {
      if (cfg.cls === "necromancer") return openRaiseMenu();
      if (cfg.cls === "ranger") choice = "volley";
      else if (cfg.cls === "beastmaster") choice = "beast";
      else return openPowerMenu();
    }
    run.busy = true; renderBattle();
    const s = stats(), c = cls(), hero = $("dg-hero");
    let guarding = false, petsDone = false;
    const gain = (n) => { run.energy = Math.min(s.energy, run.energy + n); };
    const heal = (n) => { run.hp = Math.min(s.hp, run.hp + n); floatNum(hero, "+" + n, "heal"); window.Music && Music.sfx("heal"); };
    if (action === "strike") {
      const h = rollHit(s.atk, c.strikeMult || 1);
      gain(c.strikeEnergy || 1);
      await dealDamage(h.dmg, h.crit, c.strike);
      if (cfg.cls === "hexcaster") foe.hex = Math.min(5, foe.hex + 1);
    } else if (action === "power") {
      if (cfg.cls === "necromancer") {
        if (choice === "mend") {
          run.energy -= 3;
          for (const p of run.pets) p.hp = Math.min(p.maxHp, p.hp + Math.round(p.maxHp * 0.5));
          heal(Math.round(s.hp * 0.1)); renderPets(); log("Mend Flesh: your minions knit back together.");
        } else {
          run.energy -= RAISE_COST[choice];
          await summon(choice);
        }
      } else if (choice === "volley") {
        // Ranger: every point of energy is an arrow (2–4), each at 65% of a normal shot.
        const n = run.energy; run.energy = 0;
        for (let i = 0; i < n && foe.hp > 0; i++) { const h = rollHit(s.atk, 0.65); await dealDamage(h.dmg, h.crit, `Volley arrow ${i + 1} of ${n}`); }
      } else if (choice === "beast") {
        run.energy -= 3;
        const beast = run.pets[0];
        if (!beast) await summon();
        else if (beast.kind === "wolf") { const h = rollHit(s.atk, 1.5); await dealDamage(h.dmg, h.crit, "Pack Attack"); if (foe.hp > 0) await petsAct(1.5); petsDone = true; }
        else if (beast.kind === "bear") {
          heal(Math.round(s.hp * 0.25)); beast.hp = Math.min(beast.maxHp, beast.hp + Math.round(beast.maxHp * 0.5)); renderPets();
          guarding = true; petsDone = true;
          log("Hibernate: you and your bear curl up, heal, and brace for the next hit.");
        } else {
          const el = $("dg-pets").children[0];
          for (let i = 0; i < 5 && foe.hp > 0; i++) {
            const crit = Math.random() < 0.15;
            await dealDamage(Math.max(1, Math.round(s.atk * 0.35 * rnd(0.85, 1.15) * (crit ? 1.75 : 1))), crit, `Murder of Crows ${i + 1}/5`, el);
          }
          petsDone = true;
        }
      } else {
        run.energy -= powerCost(choice);
        const hitWith = async (mult, label, forceCrit = false) => { const h = rollHit(s.atk, mult, forceCrit); await dealDamage(h.dmg, h.crit, label); return h; };
        switch (choice) {
          case "haymaker": await hitWith(2.8, "Haymaker"); break;
          case "body": await hitWith(1.6, "Body Blow"); foe.dazed = true; if (foe.hp > 0) log(`Body Blow! ${foe.base} is winded: its next attack is halved.`); break;
          case "wind": heal(Math.round(s.hp * 0.2)); run.poison = 0; run.weak = 0; log("Second Wind: you shake it off and get back up."); break;
          case "smite": { await hitWith(2.2, "Smite"); heal(Math.round(s.hp * 0.15)); break; }
          case "holy": { const holy = foe.undead ? 3 : 1.5; await hitWith(holy, foe.undead ? "Holy Strike (undead: double!)" : "Holy Strike"); break; }
          case "lay": heal(Math.round(s.hp * 0.35)); log("Lay on Hands: warm light closes your wounds."); break;
          case "rune2": await hitWith(1.6, "Rune Burst"); break;
          case "rune3": await hitWith(2.2, "Greater Burst"); break;
          case "over": await hitWith(4, "OVERCHARGE"); if (foe.kind === "boss" && foe.hp <= 0) run.feats.overcharge_boss = true; break;
          case "drain": { const h = await hitWith(2.2, "Soul Drain"); heal(Math.round(h.dmg * 0.5)); break; }
          case "detonate": {
            const dmg = Math.max(1, Math.round(foe.hex * s.atk * 0.7)); const stacks = foe.hex; foe.hex = 0;
            await dealDamage(dmg, false, `Detonate (${stacks} curse${stacks === 1 ? "" : "s"})`); break;
          }
          case "wither": foe.hex = Math.min(5, foe.hex + 2); log(`Wither: the curse deepens (×${foe.hex}).`); break;
        }
      }
    } else if (action === "guard") {
      guarding = true; gain(1); window.Music && Music.sfx("guard");
      if (cfg.cls === "paladin") { const n = Math.round(s.hp * 0.1); heal(n); log(`You raise your shield and pray. +${n} HP.`); }
      else if (cfg.cls === "necromancer") { for (const p of run.pets) p.shield = 1; log(run.pets.length ? "Bone Shield: you and your minions brace." : "You raise a wall of bone."); }
      else log("You raise your guard and catch your breath.");
    } else if (action === "potion") {
      const n = Math.round(s.hp * s.potion_heal); run.potions--; run.drunk++; heal(n); log(`Potion down. +${n} HP.`);
    }
    renderBattle(); await wait(400);
    if (foe.hp > 0 && !petsDone) await petsAct(1);
    if (foe.hp > 0 && foe.hex) {
      const burn = foe.hex * (2 + Math.floor(cfg.level / 2));
      foe.hp = Math.max(0, foe.hp - burn); floatNum($("dg-foe"), burn, ""); log(`The curse burns for ${burn}.`); renderBattle(); await wait(420);
    }
    if (foe.hp <= 0) return winBattle();
    await foeAct(guarding);
    for (const p of run.pets) p.shield = 0;
    if (run.hp <= 0) return finish("dead");
    if (foe.hp <= 0) return winBattle();
    if (run.raid && ++run.turn >= cfg.turns) { log("The System force-closes the fight. Nobody lasts this long. Nobody."); await wait(900); return finish("time"); }
    if (run.duel && ++run.turn >= cfg.turns) { log("Time! The System calls it on health left."); await wait(900); return finish("time"); }
    planIntent();
    run.busy = false; renderBattle();
    autoSoon();
  }

  // ── Auto battle: plays regular and elite fights sensibly (never floor
  // bosses or the Null Regent). Switched on per fight; tap again to take
  // over. Stops itself when things look grim.
  const AUTO_LEVEL = 5;   // auto battle unlocks at this level
  const ONE_SHOT_LEVEL = 25;   // regular monsters can die to one hit from here on
  function setAuto(on) {
    if (on && (cfg.level || 1) < AUTO_LEVEL) return;
    run.auto = !!on;
    $("dg-auto").setAttribute("aria-pressed", String(run.auto));
    $("dg-battle").classList.toggle("auto-on", run.auto);
    if (run.auto) autoSoon();
  }
  function autoSoon() { if (run.auto) setTimeout(autoTick, 250); }
  function autoTick() {
    if (!run.auto || run.busy || run.over || $("dg-battle").hidden || !foe || foe.hp <= 0) return;
    const s = stats(), hpFrac = run.hp / s.hp, [, danger] = intentText();
    if (hpFrac < 0.35 && run.potions > 0 && run.hp < s.hp) return playerAct("potion");
    if (hpFrac < 0.25 && run.potions === 0) { setAuto(false); toast("Auto stopped: low health, your call"); return; }
    if (danger && foe.intent !== "wipe") return playerAct("guard");
    const e = run.energy;
    if (cfg.cls === "necromancer") {
      const hurt = run.pets.some((p) => p.hp < p.maxHp * 0.5);
      if (run.pets.length && hurt && e >= 3) return playerAct("power", "mend");
      if (run.pets.length < MAX_MINIONS) {
        const has = new Set(run.pets.map((p) => p.kind));
        const want = !has.has("skeleton") ? "skeleton" : e >= RAISE_COST.wraith ? "wraith" : "ghoul";
        if (e >= RAISE_COST[want]) return playerAct("power", want);
      }
      return playerAct("strike");
    }
    const act = (id) => playerAct("power", id);
    switch (cfg.cls) {
      case "runeblade": return e >= 5 ? act("over") : playerAct("strike");  // save up for Overcharge
      case "brawler":
        if (hpFrac < 0.4 && e >= 2) return act("wind");
        return e >= 3 ? act("haymaker") : playerAct("strike");
      case "paladin":
        if (hpFrac < 0.4 && e >= 3) return act("lay");
        if (foe.undead && e >= 2) return act("holy");
        return e >= 3 ? act("smite") : playerAct("strike");
      case "ranger":
        return e >= 4 || (e >= 2 && foe.hp < s.atk * 0.65 * e) ? act("volley") : playerAct("strike");
      case "hexcaster":
        if (foe.hex >= 4 && e >= 2) return act("detonate");
        return e >= 3 ? act("drain") : playerAct("strike");
      case "beastmaster": {
        if (e < 3) return playerAct("strike");
        const beast = run.pets[0];
        if (beast && beast.kind === "bear" && hpFrac > 0.6) return playerAct("strike");  // save Hibernate for when it's needed
        return act("beast");
      }
    }
    return playerAct("strike");
  }
  async function petsAct(mult) {
    const s = stats();
    for (let i = 0; i < run.pets.length && foe.hp > 0; i++) {
      const p = run.pets[i], def = PETS[p.kind], el = $("dg-pets").children[i];
      for (let n = 0; n < (def.hits || 1) && foe.hp > 0; n++) {
        const crit = Math.random() < (def.crit || 0.05);
        const dmg = Math.max(1, Math.round(s.atk * def.mult * mult * rnd(0.85, 1.15) * (crit ? 1.75 : 1)));
        await dealDamage(dmg, crit, `Your ${def.name.toLowerCase()} ${def.text}`, el);
        if (def.lifesteal) { const n2 = Math.round(dmg * def.lifesteal); run.hp = Math.min(s.hp, run.hp + n2); floatNum($("dg-hero"), "+" + n2, "heal"); }
        if (def.drain && foe.hp > 0) { const d = 2 + Math.floor(cfg.level / 2); foe.hp = Math.max(0, foe.hp - d); floatNum($("dg-foe"), d); }
      }
    }
    renderBattle();
  }
  function pickTarget() {
    for (let i = 0; i < run.pets.length; i++) if (Math.random() < PETS[run.pets[i].kind].taunt) return i;
    return -1;
  }
  async function foeAct(guarding) {
    const hero = $("dg-hero"), foeEl = $("dg-foe"), s = stats();
    const weak = foe.dazed;  // Body Blow
    const a = Math.round(foeAtk() * (weak ? 0.5 : 1));
    const guardMult = run.raid ? 1 - (cfg.guard_block ?? 0.5) : 0.3;  // the Regent's hits get through a guard
    const L = (fallback) => (foe.moveNames && foe.moveNames[foe.intent]) || fallback;  // the monster's own name for this move
    foe.shielded = false;
    foe.dazed = false;
    if (run.poison > 0) {
      const pd = Math.max(1, Math.round(run.poisonDmg || 1));
      run.poison--; run.hp = Math.max(0, run.hp - pd); jolt(hero, "hit"); floatNum(hero, pd, "poison"); window.Music && Music.sfx("poison");
      log(`Poison burns for ${pd}.${run.poison ? "" : " It wears off."}`); renderBattle(); await wait(500);
      if (run.hp <= 0) return;
    }
    const hit = async (raw, ignoreDef = false, label = "", selfHeal = 0, unguardable = false) => {
      if (foe.mods.has("frenzied") && !label.startsWith("Frenzied")) {
        await hit(raw * 0.6, ignoreDef, `Frenzied ${label || "strike"}`, selfHeal);
        if (run.hp > 0) await hit(raw * 0.6, ignoreDef, "Frenzied follow-up", selfHeal);
        return;
      }
      const healFoe = (dmg) => {
        const h = Math.round(dmg * (selfHeal + (foe.mods.has("vampiric") ? 0.3 : 0)));
        if (h > 0 && foe.hp > 0) { foe.hp = Math.min(foe.maxHp, foe.hp + h); floatNum(foeEl, "+" + h, "heal"); }
      };
      const target = pickTarget();
      foeEl.classList.add("lunge-l"); await wait(170); foeEl.classList.remove("lunge-l");
      if (target >= 0) {
        const p = run.pets[target], def = PETS[p.kind];
        let dmg = Math.max(1, Math.round(raw * rnd(0.9, 1.1)));
        if (p.shield) dmg = Math.max(1, Math.round(dmg * 0.4));
        p.hp -= dmg; floatNum($("dg-pets").children[target], dmg); healFoe(dmg);
        log(`${label || foe.name} hits your ${def.name.toLowerCase()} for ${dmg}.`);
        if (p.hp <= 0) { run.pets.splice(target, 1); log(`Your ${def.name.toLowerCase()} is gone.`); }
        renderPets(); renderBattle(); await wait(480); return;
      }
      const ghostCrit = run.duel && Math.random() < (foe.crit || 0);
      if (ghostCrit) { raw *= 1.75; label = `${label || foe.name + " hits you"} (critical!)`; }
      let dmg = Math.max(1, Math.round(raw * rnd(0.9, 1.1) - (ignoreDef ? 0 : s.def * 0.5)));
      const guarded = guarding && !unguardable;
      if (guarded) dmg = Math.max(1, Math.round(dmg * guardMult));
      run.hp = Math.max(0, run.hp - dmg); jolt(hero, "hit"); floatNum(hero, dmg); healFoe(dmg); window.Music && Music.sfx("hurt");
      if (raw > a * 1.8) jolt($("dg-stage"), "shake");
      let extra = "";
      if (run.boons.thorns) { const t = Math.max(1, Math.round(dmg * 0.3)); foe.hp = Math.max(0, foe.hp - t); floatNum(foeEl, t); extra = ` Spikes hit back for ${t}.`; }
      log(`${label || foe.name + " hits you"} for ${dmg}${guarded ? " (guarded)" : guarding ? " (it went right through your guard)" : ""}.${extra}`);
      renderBattle(); await wait(480);
    };
    switch (foe.intent) {
      case "attack": await hit(a, false, L("")); break;
      case "heavy": await hit(a * 2, false, L("Heavy hit")); break;
      case "frenzy": await hit(a * 0.7, false, L("Frenzy")); if (run.hp > 0) await hit(a * 0.7, false, L("Frenzy") + " again"); break;
      case "spit": await hit(a * 1.2, true, L("Acid spit")); break;
      case "poison": await hit(a * 0.6, false, L("Poison")); if (run.hp > 0) { run.poison = 3; run.poisonDmg = a * 0.35; log(`${$("dg-log").textContent} You're poisoned for 3 turns.`); } break;
      case "weaken": await hit(a * 0.7, false, L("Weakening hit")); if (run.hp > 0) { run.weak = (run.weak || 0) + Math.max(1, Math.round(cfg.stats.atk * 0.12)); log(`${$("dg-log").textContent} Your attack drops.`); renderBattle(); } break;
      case "shield": foe.shielded = true; log(`${L(foe.name + " raises its guard")}. Your hits do half damage until its next turn.`); renderBattle(); await wait(650); break;
      case "rage": foe.atk += 3; log(`${foe.name} is furious. Attack up.`); await wait(550); break;
      case "windup": foe.charged = true; log(`${foe.name} winds up. Something big is coming next turn.`); await wait(650); break;
      case "slam": foe.charged = false; await hit(a * 2.8, false, (foe.moveNames && foe.moveNames.windup) ? foe.moveNames.windup.toUpperCase() : "GROUND SLAM"); break;
      case "drain": await hit(a, false, L("Life drain"), 0.5); break;
      case "wipe": await hit(a * 1.6, true, "SYSTEM WIPE", 0, true); break;
      case "cascade": {
        // Hits you and every pet at once: pets can't take it for you.
        foeEl.classList.add("lunge-l"); await wait(170); foeEl.classList.remove("lunge-l");
        jolt($("dg-stage"), "shake"); window.Music && Music.sfx("cascade");
        let dmg = Math.max(1, Math.round(a * 1.1 * rnd(0.9, 1.1) - s.def * 0.5));
        if (guarding) dmg = Math.max(1, Math.round(dmg * guardMult));
        run.hp = Math.max(0, run.hp - dmg); jolt(hero, "hit"); floatNum(hero, dmg);
        let lost = 0;
        for (let i = run.pets.length - 1; i >= 0; i--) {
          const p = run.pets[i], pd = Math.max(1, Math.round(a * 1.1 * rnd(0.9, 1.1) * (p.shield ? 0.4 : 1)));
          p.hp -= pd; floatNum($("dg-pets").children[i], pd);
          if (p.hp <= 0) { run.pets.splice(i, 1); lost++; }
        }
        log(`Cascade Failure hits everything: ${dmg} to you${guarding ? " (guarded)" : ""}${run.pets.length || lost ? ", and your pets too" : ""}.${lost ? ` ${lost} of them ${lost === 1 ? "is" : "are"} gone.` : ""}`);
        renderPets(); renderBattle(); await wait(600); break;
      }
      case "purge": await hit(a, false, "Null Purge"); run.energy = 0; window.Music && Music.sfx("purge"); if (run.hp > 0) { log(`Null Purge: your energy is wiped. "${pick(regentLines())}"`); renderBattle(); await wait(900); } break;
      case "quaff": { const h = Math.round(foe.maxHp * (foe.potionHeal || 0.45)); foe.potions--; foe.hp = Math.min(foe.maxHp, foe.hp + h); floatNum(foeEl, "+" + h, "heal"); log(`${foe.name} drinks a potion. +${h} HP.`); renderBattle(); await wait(600); break; }
      case "gorge": { const h = Math.round(foe.maxHp * 0.1); foe.hp = Math.min(foe.maxHp, foe.hp + h); floatNum(foeEl, "+" + h, "heal"); log(`${foe.name} eats something unspeakable. +${h} HP.`); renderBattle(); await wait(600); break; }
    }
    if (foe.barks && foe.barks.length && run.hp > 0 && Math.random() < 0.3) log(`${$("dg-log").textContent} "${pick(foe.barks)}"`);
    if (foe.kind === "boss" && !foe.enraged && foe.hp > 0 && foe.hp < foe.maxHp / 2) {
      foe.enraged = true; toast("Boss enraged!"); log(`${foe.base} is enraged. Every hit now lands harder.`); await wait(650);
    }
  }
  async function winBattle() {
    $("dg-foe").classList.add("dead");
    if (run.duel) {
      log(`${foe.name} fades back into the mist.`); await wait(1100); run.busy = false;
      return finish("win");
    }
    if (run.raid) {
      log("The Null Regent's windows go dark, one by one. The last one says: Shutting down.");
      jolt($("dg-stage"), "shake"); await wait(1400); run.busy = false;
      return finish("kill");
    }
    run.kills++; if (foe.role === "elite") run.elites++;
    run.feats.seen[foe.id] = (run.feats.seen[foe.id] || 0) + 1;  // Bestiary: beat it
    if (run.hp > 0 && run.hp / stats().hp <= 0.05) run.feats.clutch = true;
    run.xpEst += foe.xp;
    log(foe.death || pick(SAY.kill));
    if (foe.mods.has("explosive")) {
      await wait(500);
      const blast = Math.round(stats().hp * 0.15);
      run.hp = Math.max(1, run.hp - blast);  // the blast hurts, but never kills
      jolt($("dg-stage"), "shake"); floatNum($("dg-hero"), blast);
      log(`It explodes! ${blast} damage.`); renderBattle();
    }
    await wait(900);
    run.busy = false;
    if (foe.kind === "boss") return finish("boss");
    if (foe.kind === "bruiser") return afterEvent(`${foe.name} defeated.`, () => offerBoon("Elite down. " + SAY.boon, advance));
    afterEvent(`${foe.name} defeated.`);
  }

  // ── end of run: the server decides the rewards ───────────────────────
  async function finish(outcome) {
    if (run.over) return;
    run.over = true; run.busy = true;
    if (window.Music) { Music.sting(outcome === "dead" ? "fall" : "win"); setTimeout(() => Music.play("hub"), 1200); }
    const f = run.feats;
    const report = run.duel ? { outcome: outcome === "dead" ? "lose" : outcome, my_pct: pct(run.hp, stats().hp), ghost_pct: pct(foe.hp, foe.maxHp) }
      : run.raid ? { outcome: outcome === "dead" ? "fell" : outcome, damage: raidDealt() } : { outcome, floors: Math.min(run.floor + 1, cfg.floors.length), kills: run.kills, elites: run.elites, supplies_used: suppliesUsed(),
      feats: { no_potion: run.drunk === 0, clutch: f.clutch, flawless: f.low >= 0.5, overcharge_boss: f.overcharge_boss, loot_boxes: f.loot_boxes, pets: f.pets, seen: f.seen } };
    showPart("dg-end");
    $("dg-end").innerHTML = `<div class="dg-result"><p class="empty">The System is tallying your run…</p></div>`;
    let result;
    try {
      result = await hooks.onFinish(report);
    } catch (e) {
      $("dg-end").innerHTML = `<div class="dg-result"><p>${esc(e.message)}</p><button class="btn" id="dg-retry">Try again</button></div>`;
      run.over = false; $("dg-retry").onclick = () => { run.over = false; finish(outcome); };
      return;
    }
    renderResult(outcome, result);
  }
  const RC = { Common: "var(--r-common)", Uncommon: "var(--r-uncommon)", Rare: "var(--r-rare)", Epic: "var(--r-epic)", Legendary: "var(--r-legendary)" };
  const PLACED = { equipped: "Equipped! It went straight into an empty slot.", bag: "Added to your bag.", pending: "Your bag is full. Decide what to keep in your bag." };
  function lootCard(it) {
    const st = [["ATK", it.atk], ["DEF", it.def], ["HP", it.hp]].filter(([, v]) => v).map(([k, v]) => `<span>${k} +${v}</span>`).join("");
    return `<div class="dg-loot" style="--rc:${RC[it.rarity]}"><div class="icon">${it.icon ? `<img src="${esc(it.icon)}" alt="">` : ""}</div>
      <div style="min-width:0"><div class="rar">${it.ilvl ? `Lv ${it.ilvl} ` : ""}${it.rarity} ${it.slot}</div><div class="iname">${esc(it.name)}</div>
      <div class="istats">${st}</div>${it.flavor ? `<div class="flav">“${esc(it.flavor)}”</div>` : ""}<div class="placed">${PLACED[it.placed] || ""}</div></div></div>`;
  }
  function renderResult(outcome, r) {
    const dead = outcome === "dead";
    if (cfg.practice) return renderPractice(outcome);
    if (cfg.raid) return renderRaid(outcome, r);
    if (cfg.duel) return renderDuel(outcome, r);
    const stamp = dead ? ["You fell", "var(--ink)"] : outcome === "boss" ? ["Boss defeated", "var(--mustard)"] : ["Dungeon cleared", "var(--red)"];
    const msg = dead ? SAY.dead : outcome === "boss" ? SAY.winBoss : SAY.exit;
    const rows = [["Monsters defeated", run.kills], ["XP earned", `+${r.xp}`], ["Bookmarks", `+${r.bookmarks}`],
      ["Level", r.levels_gained ? `${r.level} (+${r.levels_gained}!)` : r.level]];
    const pending = r.loot.some((i) => i.placed === "pending");
    $("dg-end").innerHTML = `<div class="dg-result">
      <span class="stamp" style="background:${stamp[1]};font-size:30px">${stamp[0]}</span>
      <div class="dg-system" style="width:100%;text-align:left"><b>SYSTEM AI</b><span>${esc(msg)}</span></div>
      <div class="tape dg-tally">${rows.map(([a, b]) => `<span>${a}</span><span>${b}</span>`).join("")}</div>
      ${dead ? `<div class="dg-lost">This book went to your Fallen shelf. Revive it any time for ${r.revive_cost} bookmarks and try again.</div>` : ""}
      ${r.loot.length ? `<p style="font-size:18px;margin:0">${outcome === "boss" ? "Boss chest" : "Exit chest"}${r.loot.length > 1 ? "s (long book bonus)" : ""}</p>` + r.loot.map(lootCard).join("") : ""}
      ${r.series_reward ? `<p class="note" style="color:var(--r-epic)">${r.series_reward.kind === "finale"
        ? `Series complete! You've cleared all ${r.series_reward.books} books of ${esc(r.series_reward.series)}: +${r.series_bookmarks} bookmarks.${r.series_reward.chest ? " Your chest was guaranteed Epic or better." : ""}`
        : `Caught up on ${esc(r.series_reward.series)} again: +${r.series_bookmarks} bookmarks.${r.series_reward.chest ? " Your chest was guaranteed Rare or better." : ""}`}</p>` : ""}
      ${r.coin_used ? `<p class="note">Your Lucky Coin rolled the first chest twice and kept the better one.</p>` : ""}
      ${Object.keys(r.supplies_returned || {}).length ? `<p class="note">Unused supplies went back in your pack: ${Object.entries(r.supplies_returned).map(([k, n]) => `${SUPPLY_NAMES[k]}${n > 1 ? " ×" + n : ""}`).join(", ")}.</p>` : ""}
      ${outcome === "exit" ? `<p class="note">Beat the floor boss next time for Rare, Epic or Legendary odds.</p>` : ""}
      <button class="btn" id="dg-done" style="width:100%">${pending ? "Sort your bag" : "Back to the hub"}</button></div>`;
    if (r.levels_gained) toast(`Level up! Lv ${r.level}`, "var(--mustard)");
    if (r.levels_gained && r.level >= AUTO_LEVEL && r.level - r.levels_gained < AUTO_LEVEL) setTimeout(() => toast("Auto battle unlocked!", "#2E9E3A"), 1900);
    if (window.Music) setTimeout(() => Music.sting(r.levels_gained ? "level" : r.loot.length ? "chest" : ""), 900);
    $("dg-done").onclick = () => hooks.onDone(r, pending);
  }

  // December boss results: the damage and what's left of the shared bar.
  function renderRaid(outcome, r) {
    const stamp = r.late ? ["Too late", "var(--ink)"] : r.killed ? ["Regent defeated!", "var(--mustard)"]
      : outcome === "dead" ? ["You fell", "var(--ink)"] : ["Force-closed", "#22305A"];
    const line = r.late ? `Someone else finished him while you were fighting. ${r.status === "defeated" ? "The party won!" : ""}`
      : r.killed ? "You landed the killing blow. The System is… rebooting. Everyone who fought gets a chest."
      : r.damage ? `${r.pct}% of his health left. He noticed. He'll remember.` : "Not a scratch. He didn't even look up.";
    const rows = [["Damage dealt", (r.damage || 0).toLocaleString()], ["Regent's health", `${(r.hp || 0).toLocaleString()} (${r.pct ?? 0}%)`],
      ["XP earned", `+${r.xp}`], ["Bookmarks", `+${r.bookmarks}`], ["Level", r.levels_gained ? `${r.level} (+${r.levels_gained}!)` : r.level]];
    const pending = (r.loot || []).some((i) => i.placed === "pending");
    $("dg-end").innerHTML = `<div class="dg-result">
      <span class="stamp" style="background:${stamp[1]};font-size:30px">${stamp[0]}</span>
      <div class="dg-system" style="width:100%;text-align:left"><b>SYSTEM AI</b><span>${esc(line)}</span></div>
      <div class="tape dg-tally">${rows.map(([a, b]) => `<span>${a}</span><span>${b}</span>`).join("")}</div>
      ${(r.loot || []).length ? `<p style="font-size:18px;margin:0">The Regent's hoard</p>` + r.loot.map(lootCard).join("") : ""}
      <button class="btn" id="dg-done" style="width:100%">${pending ? "Sort your bag" : "Back to the hub"}</button></div>`;
    if (r.levels_gained) toast(`Level up! Lv ${r.level}`, "var(--mustard)");
    if (window.Music) setTimeout(() => Music.sting(r.levels_gained ? "level" : (r.loot || []).length ? "chest" : ""), 900);
    $("dg-done").onclick = () => hooks.onDone(r, pending);
  }

  function renderDuel(outcome, r) {
    const g = cfg.ghost.username.toUpperCase();
    const stamp = r.won ? ["Victory!", "var(--mustard)"] : ["Defeated", "var(--ink)"];
    const line = r.won ? (r.moved ? `You beat ${g}'s ghost and took #${r.rank_after} on the ladder.` : `You beat ${g}'s ghost. Your rank holds at #${r.rank_after}.`)
      : outcome === "time" ? `Time ran out and ${g}'s ghost had more health left. They'll hear about it.` : `${g}'s ghost wins this one. They'll hear about it.`;
    const rows = [["Your health left", `${pct(run.hp, stats().hp)}%`], ["Ghost's health left", `${pct(foe.hp, foe.maxHp)}%`],
      ["Bookmarks", `+${r.bookmarks}`], ["Ladder", r.moved ? `#${r.rank_before} → #${r.rank_after}` : `#${r.rank_after}`]];
    $("dg-end").innerHTML = `<div class="dg-result">
      <span class="stamp" style="background:${stamp[1]};font-size:30px">${stamp[0]}</span>
      <div class="dg-system" style="width:100%;text-align:left"><b>SYSTEM AI</b><span>${esc(line)}</span></div>
      <div class="tape dg-tally">${rows.map(([a, b]) => `<span>${a}</span><span>${b}</span>`).join("")}</div>
      <button class="btn" id="dg-done" style="width:100%">Back to the Arena</button></div>`;
    if (window.Music) setTimeout(() => Music.sting(r.won ? "level" : ""), 900);
    $("dg-done").onclick = () => hooks.onDone(r);
  }

  // Practice pays nothing and saves nothing: just how it went.
  function renderPractice(outcome) {
    const dead = outcome === "dead";
    const stamp = dead ? ["You fell", "var(--ink)"] : outcome === "boss" ? ["Boss defeated", "var(--mustard)"] : ["Dungeon cleared", "var(--red)"];
    const line = dead ? "Practice death. It doesn't count. The System counted anyway." : "Nicely done. It counts for nothing. That's what practice is.";
    $("dg-end").innerHTML = `<div class="dg-result">
      <span class="stamp" style="background:${stamp[1]};font-size:30px">${stamp[0]}</span>
      <div class="dg-system" style="width:100%;text-align:left"><b>SYSTEM AI</b><span>${esc(line)}</span></div>
      <div class="tape dg-tally"><span>Mode</span><span>Practice</span><span>Monsters defeated</span><span>${run.kills}</span>
        <span>Floors reached</span><span>${Math.min(run.floor + 1, cfg.floors.length)}</span><span>Potions drunk</span><span>${run.drunk}</span></div>
      <p class="note">Practice gives no XP, loot, bookmarks or badges.</p>
      <div class="split-actions" style="width:100%"><button class="btn alt" id="dg-again">Again</button><button class="btn" id="dg-done">Back to the hub</button></div></div>`;
    $("dg-done").onclick = () => hooks.onDone(null, false);
    $("dg-again").onclick = () => hooks.onAgain && hooks.onAgain();
  }

  window.Dungeon = { start, raid, duel, legacyArt: (key) => (FOES[key] ? FOES[key].svg : "") };
})();
