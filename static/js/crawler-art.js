/* Crawler art: draws a player's paper-cutout character as an SVG string.
 *
 *   CrawlerArt.render(look, cls) -> "<svg ...>"
 *
 * `look` comes from the character builder (ancestry, skin, hair, hairColor,
 * beard, face, accent). `cls` picks the outfit and weapon. Everything is drawn
 * in layers inside a 240×330 box with the feet at y≈318, so one look works
 * with every class.
 */
(function () {
  const EDGE = 'stroke="rgba(40,25,15,.28)" stroke-width="2" stroke-linejoin="round"';

  const ANCESTRIES = {
    human: { name: "Human", body: [1, 1], head: 40, ears: "round", skins: ["#F2CDA8", "#E0B089", "#C68E62", "#9A6A45", "#6E4A32"] },
    dwarf: { name: "Dwarf", body: [1.14, 0.84], head: 42, ears: "round", skins: ["#F0C4A0", "#E8B48A", "#C68E62", "#9A6A45"] },
    elf: { name: "Elf", body: [0.93, 1.02], head: 38, ears: "elf", noBeard: true, skins: ["#F6DCC2", "#EACAA6", "#D3A984", "#B98D6A"] },
    darkelf: { name: "Dark Elf", body: [0.93, 1.02], head: 38, ears: "longelf", noBeard: true, skins: ["#7B5FA8", "#5E4A86", "#6B6A8C", "#4A3E5E"] },
    orc: { name: "Orc", body: [1.12, 1], head: 44, ears: "orc", skins: ["#7FA650", "#6A8F45", "#8C9A5A", "#5C7A48"] },
  };
  const HAIR_STYLES = { bald: "Bald", short: "Short", long: "Long", mohawk: "Mohawk", bun: "Top knot", braid: "Braid" };
  const HAIR_COLORS = ["#2B2621", "#5B3A22", "#8A4E24", "#C0602E", "#D9B25B", "#ECEAF2", "#8C8F99", "#3F74B5"];
  const BEARDS = { none: "None", stubble: "Stubble", full: "Full", braided: "Braided" };
  const FACES = { determined: "Determined", cheerful: "Cheerful", grumpy: "Grumpy", glowing: "Glowing eyes" };
  const ACCENTS = ["#D6503E", "#E3A93B", "#3F74B5", "#4E9A55", "#8A4FB8", "#22305A", "#2B2621", "#E8E1D2"];

  const CLASSES = {
    brawler: { name: "Brawler", role: "Tough melee" },
    runeblade: { name: "Runeblade", role: "Energy fighter" },
    hexcaster: { name: "Hexcaster", role: "Dark magic" },
    ranger: { name: "Ranger", role: "Ranged crits" },
    paladin: { name: "Paladin", role: "Holy tank" },
    beastmaster: { name: "Beastmaster", role: "Live pets" },
    necromancer: { name: "Necromancer", role: "Undead pets" },
  };

  const DEFAULT_LOOK = { ancestry: "human", skin: 1, hair: "short", hairColor: 1, beard: "none", face: "determined", accent: 0 };

  // ── outfits: colors, torso details, back pieces, and a weapon held in the front hand ──
  function outfit(cls, a) {
    const rune = "#4FD6FF";
    switch (cls) {
      case "runeblade": return {
        shirt: "#343B4A", sleeve: "#343B4A", pants: "#2B303C", boots: "#1E222B", cuff: "#4A5568",
        back: `<path d="M80 150 L160 150 L182 304 Q120 316 58 304 Z" fill="${a}" ${EDGE}/>`,
        torso: `<path d="M94 162 Q120 152 146 162 L140 210 Q120 220 100 210 Z" fill="#4A5568"/><path d="M110 176 l10 16 l10 -16 M120 198 v-16" stroke="${rune}" stroke-width="3.5" fill="none" stroke-linecap="round"/><rect x="76" y="232" width="88" height="12" fill="#1E222B"/>`,
        pad: `<circle r="24" fill="#4A5568" ${EDGE}/><path d="M-6 -6 l6 10 l6 -10" stroke="${rune}" stroke-width="3" fill="none"/>`,
        weapon: `<g transform="translate(14 0)"><rect x="-6" y="-150" width="12" height="176" rx="5" fill="#262B36" ${EDGE}/><rect x="-42" y="-186" width="84" height="50" rx="6" fill="#343B4A" ${EDGE}/><path d="M-8 -170 l8 12 l8 -12 M0 -150 v-10" stroke="${rune}" stroke-width="3.5" fill="none"/><circle cy="-161" r="22" fill="${rune}" opacity=".18"/></g>`,
      };
      case "hexcaster": return {
        shirt: "#2B2530", sleeve: "#2B2530", pants: "#231F28", boots: "#1E1A22", cuff: a, robe: true,
        back: `<path d="M78 152 L162 152 L182 306 Q120 318 58 306 Z" fill="#231F28" ${EDGE}/>`,
        torso: `<path d="M86 300 L96 150 M154 300 L144 150" stroke="${a}" stroke-width="5"/><path d="M84 236 H156" stroke="${a}" stroke-width="9"/><circle cx="120" cy="236" r="11" fill="#E3DCC8" ${EDGE}/>`,
        pad: `<path d="M-22 6 L-28 -22 L-10 -6 L0 -30 L10 -6 L28 -22 L22 6 Z" fill="#2B2530" ${EDGE}/>`,
        weapon: `<g transform="translate(-40 -26)"><path d="M-8 -12 C 2 -54, 42 -30, 30 -74" stroke="#8CFF5A" stroke-width="4" fill="none" opacity=".65" stroke-linecap="round"/><circle cx="36" cy="-60" r="6" fill="#8CFF5A" opacity=".5"/><path d="M-22 -8 L10 -2 L10 44 L-22 38 Z" fill="#3E2F1E" ${EDGE}/><path d="M42 -8 L10 -2 L10 44 L42 38 Z" fill="#3E2F1E" ${EDGE}/><path d="M-17 -4 L8 0 L8 38 L-17 33 Z M37 -4 L12 0 L12 38 L37 33 Z" fill="#DCE8C4"/><ellipse cx="10" cy="16" rx="26" ry="18" fill="#8CFF5A" opacity=".28"/></g>`,
      };
      case "ranger": return {
        shirt: "#8A6440", sleeve: "#4B5E3A", pants: "#4B4034", boots: "#3A2A1E", cuff: "#8A6440",
        back: `<path d="M76 136 L164 136 L188 304 Q120 318 52 304 Z" fill="${a}" ${EDGE}/><g transform="rotate(18 160 160)"><rect x="150" y="104" width="24" height="96" rx="6" fill="#6E4A2E" ${EDGE}/><path d="M154 104v-24 M162 104v-24 M170 104v-24" stroke="#6E5A3A" stroke-width="3"/><path d="M149 82l5-10 5 10z M157 82l5-10 5 10z M165 82l5-10 5 10z" fill="#E3DCC8"/></g>`,
        torso: `<path d="M96 146 L144 240" stroke="#5B3A22" stroke-width="8"/><rect x="78" y="226" width="84" height="12" fill="#4A3222"/><rect x="112" y="223" width="16" height="18" rx="3" fill="#C9A04A" ${EDGE}/>`,
        weapon: `<g transform="translate(18 -20)"><path d="M0 -120 C 44 -70, 44 30, 0 80" fill="none" stroke="#7A5230" stroke-width="10" stroke-linecap="round"/><path d="M0 -120 L0 80" stroke="#EDE6D6" stroke-width="2"/><rect x="-6" y="-26" width="12" height="32" rx="4" fill="#8A6440"/></g>`,
      };
      case "paladin": return {
        shirt: "#B9BCC6", sleeve: "#B9BCC6", pants: "#9EA1AB", boots: "#8A8D97", cuff: "#D4A93A",
        back: "",
        torso: `<path d="M92 156 Q120 146 148 156 L144 206 Q120 216 96 206 Z" fill="#CFD2DA"/><path d="M92 156 Q120 146 148 156" stroke="#D4A93A" stroke-width="5" fill="none"/><rect x="76" y="228" width="88" height="14" fill="#D4A93A" ${EDGE}/><path d="M98 240 H142 L138 300 L120 290 L102 300 Z" fill="${a}" ${EDGE}/><path d="M120 256 L104 250 L110 262 L130 262 L136 250 Z" fill="#D4A93A"/>`,
        pad: `<ellipse rx="28" ry="22" fill="#B9BCC6" ${EDGE}/><ellipse rx="28" ry="22" fill="none" stroke="#D4A93A" stroke-width="5"/>`,
        weapon: `<g transform="translate(16 0)"><rect x="-6" y="-150" width="12" height="180" rx="5" fill="#4A3A2E" ${EDGE}/><rect x="-46" y="-190" width="92" height="54" rx="8" fill="#B9BCC6" ${EDGE}/><rect x="-46" y="-170" width="92" height="14" fill="#9EA1AB"/><circle cy="-163" r="12" fill="#D4A93A" ${EDGE}/></g>`,
      };
      case "beastmaster": return {
        shirt: a, sleeve: "#7A5A3A", pants: "#5B4A3A", boots: "#3E2F22", cuff: "#C9B48A",
        back: "",
        torso: `<path d="M78 146 Q120 134 162 146 L152 200 Q120 212 88 200 Z" fill="#7A5A3A" ${EDGE}/><path d="M80 150 l8 12 l8 -10 l8 12 l8 -10 l8 12 l8 -10 l8 12 l8 -10 l8 12 l8 -10" stroke="#C9B48A" stroke-width="4" fill="none"/><path d="M100 176 Q120 190 140 176" stroke="#E3DCC8" stroke-width="3" fill="none"/><path d="M112 184 l-3 9 M120 188 l0 10 M128 184 l3 9" stroke="#E3DCC8" stroke-width="4" stroke-linecap="round"/><rect x="78" y="228" width="84" height="12" fill="#4A3222"/>`,
        weapon: `<g transform="translate(12 0)"><rect x="-5" y="-170" width="10" height="200" rx="4" fill="#7A5230" ${EDGE}/><path d="M0 -200 L12 -170 L-12 -170 Z" fill="#C9C3B6" ${EDGE}/><path d="M-5 -160 l-16 22 M-5 -150 l-12 24" stroke="${a}" stroke-width="5" stroke-linecap="round"/></g>`,
      };
      case "necromancer": return {
        shirt: "#1E1A22", sleeve: "#1E1A22", pants: "#16131A", boots: "#100E12", cuff: "#E3DCC8", robe: true,
        back: `<path d="M76 150 L164 150 L186 308 Q120 320 54 308 Z" fill="#16131A" ${EDGE}/>`,
        torso: `<path d="M100 150 L110 300 M140 150 L130 300" stroke="${a}" stroke-width="5"/><path d="M92 176 h56 M94 190 h52 M96 204 h48" stroke="#E3DCC8" stroke-width="4" stroke-linecap="round" opacity=".85"/>`,
        pad: `<circle r="16" fill="#E3DCC8" ${EDGE}/><circle cx="-5" cy="-2" r="3.5" fill="#1E1A22"/><circle cx="5" cy="-2" r="3.5" fill="#1E1A22"/><path d="M-5 8 h10" stroke="#1E1A22" stroke-width="2"/>`,
        weapon: `<g transform="translate(14 0)"><rect x="-5" y="-160" width="10" height="190" rx="4" fill="#3A2E28" ${EDGE}/><circle cy="-176" r="20" fill="#E3DCC8" ${EDGE}/><circle cx="-7" cy="-178" r="5" fill="#6FE0FF"/><circle cx="7" cy="-178" r="5" fill="#6FE0FF"/><path d="M-8 -164 h16" stroke="#1E1A22" stroke-width="3"/><circle cy="-176" r="32" fill="#6FE0FF" opacity=".14"/></g>`,
      };
      default: return { // brawler
        shirt: "#8B5A2B", sleeve: "#8B5A2B", pants: "#5B4A3A", boots: "#4A3222", cuff: "#EFE3C8",
        back: "",
        torso: `<path d="M120 150 L120 256" stroke="#6E4420" stroke-width="4"/><path d="M68 248 Q120 262 172 248 L174 262 Q120 278 66 262 Z" fill="#EFE3C8" ${EDGE}/><rect x="74" y="208" width="92" height="14" fill="#3E2A1C"/><rect x="110" y="205" width="22" height="20" rx="3" fill="#D4A93A" ${EDGE}/><path d="M84 150 Q120 170 156 150 L152 164 Q120 184 88 164 Z" fill="${a}" ${EDGE}/>`,
        weapon: `<g transform="translate(14 0)"><rect x="-6" y="-110" width="12" height="130" rx="5" fill="#5B3A22" ${EDGE}/><rect x="-26" y="-136" width="52" height="34" rx="5" fill="#8C8F99" ${EDGE}/></g>`,
      };
    }
  }

  function ears(kind, skin, r) {
    const x = r - 2;
    if (kind === "elf") return `<path d="M${120 - x} 100 L${120 - x - 34} 78 L${120 - x + 2} 116 Z M${120 + x} 100 L${120 + x + 34} 78 L${120 + x - 2} 116 Z" fill="${skin}" ${EDGE}/>`;
    if (kind === "longelf") return `<path d="M${120 - x} 100 L${120 - x - 50} 72 L${120 - x + 2} 118 Z M${120 + x} 100 L${120 + x + 50} 72 L${120 + x - 2} 118 Z" fill="${skin}" ${EDGE}/>`;
    if (kind === "orc") return `<path d="M${120 - x} 96 L${120 - x - 18} 84 L${120 - x + 2} 118 Z M${120 + x} 96 L${120 + x + 18} 84 L${120 + x - 2} 118 Z" fill="${skin}" ${EDGE}/>`;
    return `<circle cx="${120 - x}" cy="106" r="9" fill="${skin}" ${EDGE}/><circle cx="${120 + x}" cy="106" r="9" fill="${skin}" ${EDGE}/>`;
  }

  function hairBack(style, color, r) {
    if (style === "long") return `<path d="M${120 - r - 4} 96 Q${120 - r - 10} 180 ${120 - r + 10} 204 L${120 + r - 10} 204 Q${120 + r + 10} 180 ${120 + r + 4} 96 Z" fill="${color}" ${EDGE}/>`;
    if (style === "braid") return `<g fill="${color}" ${EDGE}>${[0, 1, 2, 3].map((i) => `<ellipse cx="${120 + r - 6}" cy="${136 + i * 20}" rx="9" ry="12"/>`).join("")}</g><circle cx="${120 + r - 6}" cy="${218}" r="5" fill="#D4A93A"/>`;
    return "";
  }
  function hairFront(style, color, r) {
    const top = 102 - r;
    switch (style) {
      case "short": return `<path d="M${120 - r + 2} 100 C${120 - r} ${top - 8}, ${120 + r} ${top - 8}, ${120 + r - 2} 100 C${120 + r - 14} 82, ${120 - r + 14} 82, ${120 - r + 2} 100 Z" fill="${color}" ${EDGE}/>`;
      case "long": return `<path d="M${120 - r} 104 C${120 - r - 4} ${top - 10}, ${120 + r + 4} ${top - 10}, ${120 + r} 104 C${120 + r - 10} 80, 126 76, 120 90 C114 76, ${120 - r + 10} 80, ${120 - r} 104 Z" fill="${color}" ${EDGE}/>`;
      case "mohawk": return `<path d="M104 ${top + 10} Q120 ${top - 34} 136 ${top + 10} L130 ${top + 20} Q120 ${top + 8} 110 ${top + 20} Z" fill="${color}" ${EDGE}/>`;
      case "bun": return `<circle cx="120" cy="${top - 6}" r="16" fill="${color}" ${EDGE}/><path d="M${120 - r + 2} 100 C${120 - r} ${top - 4}, ${120 + r} ${top - 4}, ${120 + r - 2} 100 C${120 + r - 12} 84, ${120 - r + 12} 84, ${120 - r + 2} 100 Z" fill="${color}" ${EDGE}/>`;
      case "braid": return `<path d="M${120 - r + 2} 102 C${120 - r} ${top - 8}, ${120 + r} ${top - 8}, ${120 + r - 2} 102 C${120 + r - 16} 84, ${120 - r + 10} 80, ${120 - r + 2} 102 Z" fill="${color}" ${EDGE}/>`;
      default: return `<ellipse cx="108" cy="${top + 16}" rx="13" ry="5" fill="#fff" opacity=".25"/>`; // bald shine
    }
  }
  function beard(kind, color, r) {
    if (kind === "stubble") return `<path d="M${120 - r + 8} 112 Q120 ${150} ${120 + r - 8} 112 Q${120 + r - 12} 138 120 142 Q${120 - r + 12} 138 ${120 - r + 8} 112 Z" fill="${color}" opacity=".35"/>`;
    if (kind === "full") return `<path d="M${120 - r + 2} 108 C${120 - r + 2} 160, 100 176, 120 178 C140 176, ${120 + r - 2} 160, ${120 + r - 2} 108 C${120 + r - 12} 124, 136 128, 120 128 C104 128, ${120 - r + 12} 124, ${120 - r + 2} 108 Z" fill="${color}" ${EDGE}/>`;
    if (kind === "braided") return `<path d="M${120 - r + 2} 108 C${120 - r + 2} 156, 98 188, 120 192 C142 188, ${120 + r - 2} 156, ${120 + r - 2} 108 C${120 + r - 12} 124, 136 128, 120 128 C104 128, ${120 - r + 12} 124, ${120 - r + 2} 108 Z" fill="${color}" ${EDGE}/><ellipse cx="106" cy="196" rx="7" ry="10" fill="${color}" ${EDGE}/><ellipse cx="134" cy="196" rx="7" ry="10" fill="${color}" ${EDGE}/><rect x="100" y="203" width="12" height="5" fill="#D4A93A"/><rect x="128" y="203" width="12" height="5" fill="#D4A93A"/>`;
    return "";
  }
  function face(kind, hasBeard, orc) {
    const eye = (x) => kind === "glowing"
      ? `<ellipse cx="${x}" cy="106" rx="9" ry="6" fill="#8CFF5A" opacity=".45"/><ellipse cx="${x}" cy="106" rx="5.5" ry="3.5" fill="#D8FF9E"/>`
      : kind === "cheerful" ? `<path d="M${x - 6} 108 Q${x} 99 ${x + 6} 108" stroke="#2B2621" stroke-width="3.5" fill="none" stroke-linecap="round"/>`
      : `<ellipse cx="${x}" cy="106" rx="4.5" ry="5" fill="#2B2621"/><circle cx="${x + 1.5}" cy="104" r="1.4" fill="#fff"/>`;
    const brows = kind === "determined" || kind === "glowing" ? `<path d="M97 95 L113 99 M143 95 L127 99" stroke="#2B2621" stroke-width="4" stroke-linecap="round"/>`
      : kind === "grumpy" ? `<path d="M97 97 L113 97 M127 97 L143 97" stroke="#2B2621" stroke-width="5" stroke-linecap="round"/>` : "";
    const mouth = hasBeard ? "" : kind === "cheerful" ? `<path d="M110 124 Q120 134 130 124" stroke="#6B3A2A" stroke-width="3" fill="none" stroke-linecap="round"/>`
      : kind === "grumpy" ? `<path d="M110 130 Q120 122 130 130" stroke="#6B3A2A" stroke-width="3" fill="none" stroke-linecap="round"/>`
      : `<path d="M111 127 H129" stroke="#6B3A2A" stroke-width="3" stroke-linecap="round"/>`;
    const tusks = orc ? `<path d="M108 128 l-3 -10 l6 2 Z M132 128 l3 -10 l-6 2 Z" fill="#F3EBDA" ${EDGE}/>` : "";
    return eye(106) + eye(134) + brows + mouth + tusks + `<circle cx="96" cy="118" r="6" fill="#E88A7A" opacity=".3"/><circle cx="144" cy="118" r="6" fill="#E88A7A" opacity=".3"/>`;
  }

  // ── Wardrobe capes (look.cape): drawn behind the body in the accent color ──
  const CAPE_PATH = "M76 146 L164 146 L206 316 Q120 332 34 316 Z";  // flares out past the body so it shows
  const CAPES = ["plain", "stripes", "stars", "checks", "flames"];
  let capeId = 0;
  function cape(kind, color) {
    if (!CAPES.includes(kind)) return "";
    const id = `cape${++capeId}`, light = "rgba(251,248,240,.45)";
    const star = (x, y, r) => `<path d="M${x} ${y - r} L${x + r * 0.3} ${y - r * 0.3} L${x + r} ${y} L${x + r * 0.3} ${y + r * 0.3} L${x} ${y + r} L${x - r * 0.3} ${y + r * 0.3} L${x - r} ${y} L${x - r * 0.3} ${y - r * 0.3} Z" fill="#FBF8F0"/>`;
    const art = {
      plain: "",
      stripes: [34, 56, 78, 150, 172, 194].map((x) => `<rect x="${x}" y="140" width="11" height="200" fill="${light}"/>`).join(""),
      stars: [[54, 286, 9], [186, 286, 9], [66, 244, 7], [174, 244, 7], [76, 206, 5], [164, 206, 5], [44, 314, 5], [196, 314, 5]].map(([x, y, r]) => star(x, y, r)).join(""),
      checks: Array.from({ length: 9 }, (_, row) => Array.from({ length: 9 }, (_, col) => (row + col) % 2 ? "" :
        `<rect x="${34 + col * 20}" y="${146 + row * 21}" width="20" height="21" fill="${light}"/>`).join("")).join(""),
      flames: `<path d="M30 330 Q40 270 52 296 Q60 230 76 284 Q92 250 120 290 Q148 250 164 284 Q180 230 188 296 Q200 270 210 330 Z" fill="#E3A93B"/>
        <path d="M34 332 Q44 294 54 310 Q64 272 80 306 Q100 286 120 310 Q140 286 160 306 Q176 272 186 310 Q196 294 206 332 Z" fill="#D6503E"/>`,
    }[kind];
    return `<defs><clipPath id="${id}"><path d="${CAPE_PATH}"/></clipPath></defs>
      <path d="${CAPE_PATH}" fill="${color}" ${EDGE}/><g clip-path="url(#${id})">${art}</g>`;
  }

  function render(lookIn, cls = "brawler", opts = {}) {
    const look = { ...DEFAULT_LOOK, ...(lookIn || {}) };
    const anc = ANCESTRIES[look.ancestry] || ANCESTRIES.human;
    if (anc.noBeard) look.beard = "none"; // elves can't grow beards
    const skin = anc.skins[Math.min(look.skin, anc.skins.length - 1)];
    const hair = HAIR_COLORS[look.hairColor] || HAIR_COLORS[0];
    const accent = ACCENTS[look.accent] || ACCENTS[0];
    const o = outfit(cls, accent);
    const r = anc.head;
    const [sx, sy] = anc.body;
    // Shorter bodies drop the head so it still sits on the shoulders.
    const headDrop = (1 - sy) * (318 - 148);
    const bodyT = `translate(120 318) scale(${sx} ${sy}) translate(-120 -318)`;
    const legs = o.robe
      ? `<path d="M78 246 L162 246 L170 312 L70 312 Z" fill="${o.shirt}" ${EDGE}/><path d="M84 312 h26 v6 h-30 z M130 312 h26 v6 h-30 z" fill="${o.boots}"/>`
      : `<rect x="96" y="238" width="26" height="72" rx="10" fill="${o.pants}" ${EDGE}/><rect x="120" y="238" width="26" height="72" rx="10" fill="${o.pants}" ${EDGE}/>
         <path d="M92 300 h30 q12 0 14 12 v6 h-44 z" fill="${o.boots}" ${EDGE}/><path d="M120 300 h30 q12 0 14 12 v6 h-44 z" fill="${o.boots}" ${EDGE}/>`;
    const arm = (x, ang, front) => `<g transform="rotate(${ang} ${x} 152)">
        <rect x="${x - 13}" y="144" width="26" height="66" rx="12" fill="${o.sleeve}" ${EDGE}/>
        <rect x="${x - 15}" y="196" width="30" height="12" rx="5" fill="${o.cuff}" ${EDGE}/>
        ${front ? `<g transform="translate(${x} 214) rotate(${-ang})">${o.weapon}</g>` : ""}
        <circle cx="${x}" cy="216" r="12" fill="${skin}" ${EDGE}/>
        ${o.pad ? `<g transform="translate(${x} 152)">${o.pad}</g>` : ""}</g>`;
    const h = opts.height || 330;
    return `<svg viewBox="-30 -40 300 370" height="${h}" width="${Math.round((h * 300) / 370)}" style="overflow:visible" role="img" aria-label="${anc.name} ${CLASSES[cls]?.name || ""}">
      <g transform="${bodyT}">
        ${o.back}
        ${look.cape ? cape(look.cape, accent) : ""}
        ${arm(84, 10, false)}
        ${legs}
        <path d="M80 146 Q120 132 160 146 L166 254 Q120 266 74 254 Z" fill="${o.shirt}" ${EDGE}/>
        ${o.torso}
      </g>
      <g transform="translate(0 ${headDrop})">
        ${hairBack(look.hair, hair, r)}
        ${ears(anc.ears, skin, r)}
        <circle cx="120" cy="104" r="${r}" fill="${skin}" ${EDGE}/>
        ${face(look.face, look.beard === "full" || look.beard === "braided", look.ancestry === "orc")}
        ${beard(look.beard, hair, r)}
        ${hairFront(look.hair, hair, r)}
      </g>
      <g transform="${bodyT}">${arm(156, -14, true)}</g>
    </svg>`;
  }

  function randomLook() {
    const keys = Object.keys(ANCESTRIES), ancestry = keys[Math.floor(Math.random() * keys.length)];
    const pick = (o) => { const k = Object.keys(o); return k[Math.floor(Math.random() * k.length)]; };
    return {
      ancestry, skin: Math.floor(Math.random() * ANCESTRIES[ancestry].skins.length),
      hair: pick(HAIR_STYLES), hairColor: Math.floor(Math.random() * HAIR_COLORS.length),
      beard: ANCESTRIES[ancestry].noBeard || Math.random() < 0.5 ? "none" : pick(BEARDS), face: pick(FACES), accent: Math.floor(Math.random() * ACCENTS.length),
    };
  }

  window.CrawlerArt = { render, randomLook, CAPES, ANCESTRIES, HAIR_STYLES, HAIR_COLORS, BEARDS, FACES, ACCENTS, CLASSES, DEFAULT_LOOK };
})();
