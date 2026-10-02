/* Monster art: draws a paper-cutout monster from parts.
 *
 *   MonsterArt.render(art, { height }) -> "<svg ...>"
 *
 * `art` = { body, color, accent, eyes, head, horns, teeth, item, extra, size }.
 * Built-in monsters and Monster Workshop monsters both use these parts, so
 * every monster matches the game's paper style.
 */
(function () {
  const EDGE = 'stroke="rgba(40,25,15,.28)" stroke-width="2" stroke-linejoin="round"';

  const BODIES = ["humanoid", "beast", "blob", "bug", "ghost", "construct", "bigboss", "serpent", "plant"];
  const HEADS = ["round", "skull", "horned", "hood", "bug", "beak", "none"];
  const EYES = ["two", "one", "glowing", "many", "slits"];
  const HORNS = ["none", "curved", "spikes", "antlers", "crown"];
  const TEETH = ["none", "fangs", "grin", "tusks"];
  const ITEMS = ["none", "club", "dagger", "staff", "shield", "scythe", "bow", "sword", "axe", "trident", "orb"];
  const EXTRAS = ["none", "wings", "tail", "tentacles", "aura"];

  const shade = (hex, amt) => {
    const n = parseInt(hex.slice(1), 16);
    const f = (c) => Math.max(0, Math.min(255, Math.round(c + amt * 255)));
    return "#" + [n >> 16, (n >> 8) & 255, n & 255].map((c) => f(c).toString(16).padStart(2, "0")).join("");
  };

  // Head centered at (hx, hy), radius r.
  function head(kind, hx, hy, r, a) {
    const skin = a.color, dark = shade(a.color, -0.12);
    switch (kind) {
      case "skull": return `<path d="M${hx - r} ${hy} C${hx - r} ${hy - r * 1.3}, ${hx + r} ${hy - r * 1.3}, ${hx + r} ${hy} Q${hx + r * 0.8} ${hy + r * 0.7} ${hx + r * 0.45} ${hy + r * 0.8} L${hx - r * 0.45} ${hy + r * 0.8} Q${hx - r * 0.8} ${hy + r * 0.7} ${hx - r} ${hy} Z" fill="#E3DCC8" ${EDGE}/>`;
      case "horned": return `<circle cx="${hx}" cy="${hy}" r="${r}" fill="${skin}" ${EDGE}/><path d="M${hx - r * 0.6} ${hy - r * 0.2} Q${hx} ${hy - r * 0.55} ${hx + r * 0.6} ${hy - r * 0.2}" stroke="${dark}" stroke-width="4" fill="none"/>`;
      case "hood": return `<path d="M${hx - r * 1.15} ${hy + r} C${hx - r * 1.2} ${hy - r * 1.4}, ${hx + r * 1.2} ${hy - r * 1.4}, ${hx + r * 1.15} ${hy + r} Z" fill="${a.accent}" ${EDGE}/><ellipse cx="${hx}" cy="${hy + r * 0.1}" rx="${r * 0.72}" ry="${r * 0.8}" fill="#15121C"/>`;
      case "beak": return `<circle cx="${hx}" cy="${hy}" r="${r}" fill="${skin}" ${EDGE}/><path d="M${hx - r * 0.3} ${hy + r * 0.2} L${hx} ${hy + r * 0.95} L${hx + r * 0.3} ${hy + r * 0.2} Z" fill="#E3A93B" ${EDGE}/>`;
      case "bug": return `<ellipse cx="${hx}" cy="${hy}" rx="${r * 1.1}" ry="${r * 0.85}" fill="${skin}" ${EDGE}/><path d="M${hx - r * 0.4} ${hy - r * 0.8} q-${r * 0.4} -${r * 0.8} -${r} -${r * 0.9} M${hx + r * 0.4} ${hy - r * 0.8} q${r * 0.4} -${r * 0.8} ${r} -${r * 0.9}" stroke="${dark}" stroke-width="4" fill="none" stroke-linecap="round"/>`;
      case "none": return "";
      default: return `<circle cx="${hx}" cy="${hy}" r="${r}" fill="${skin}" ${EDGE}/>`;
    }
  }
  function eyes(kind, hx, hy, r, hooded) {
    const y = hy - r * 0.05, dx = r * 0.38;
    const glow = hooded ? "#6FE0FF" : "#F2D14A";
    switch (kind) {
      case "one": return `<circle cx="${hx}" cy="${y}" r="${r * 0.3}" fill="#F3EBDA" ${EDGE}/><circle cx="${hx}" cy="${y}" r="${r * 0.13}" fill="#2B2621"/>`;
      case "glowing": return [-1, 1].map((s) => `<ellipse cx="${hx + s * dx}" cy="${y}" rx="${r * 0.22}" ry="${r * 0.12}" fill="${glow}" opacity=".5"/><ellipse cx="${hx + s * dx}" cy="${y}" rx="${r * 0.13}" ry="${r * 0.08}" fill="#F7F3C8"/>`).join("");
      case "many": return [[-0.45, 0], [0, -0.15], [0.45, 0], [-0.22, 0.25], [0.22, 0.25]].map(([ox, oy]) => `<circle cx="${hx + ox * r}" cy="${y + oy * r}" r="${r * 0.1}" fill="#D6503E"/>`).join("");
      case "slits": return [-1, 1].map((s) => `<ellipse cx="${hx + s * dx}" cy="${y}" rx="${r * 0.15}" ry="${r * 0.13}" fill="#F2D14A"/><rect x="${hx + s * dx - 1.5}" y="${y - r * 0.12}" width="3" height="${r * 0.24}" fill="#2B2621"/>`).join("");
      default: return [-1, 1].map((s) => `<circle cx="${hx + s * dx}" cy="${y}" r="${r * 0.14}" fill="#F2D14A"/><circle cx="${hx + s * dx}" cy="${y}" r="${r * 0.07}" fill="#2B2621"/>`).join("");
    }
  }
  function horns(kind, hx, hy, r, a) {
    const c = shade(a.color === "#E3DCC8" ? "#8C857A" : a.accent, -0.05);
    switch (kind) {
      case "curved": return `<path d="M${hx - r * 0.6} ${hy - r * 0.6} C${hx - r * 1.4} ${hy - r * 0.9}, ${hx - r * 1.3} ${hy - r * 1.7}, ${hx - r * 0.9} ${hy - r * 1.8} C${hx - r * 1.0} ${hy - r * 1.3}, ${hx - r * 0.6} ${hy - r * 1.0}, ${hx - r * 0.3} ${hy - r * 0.8} Z M${hx + r * 0.6} ${hy - r * 0.6} C${hx + r * 1.4} ${hy - r * 0.9}, ${hx + r * 1.3} ${hy - r * 1.7}, ${hx + r * 0.9} ${hy - r * 1.8} C${hx + r * 1.0} ${hy - r * 1.3}, ${hx + r * 0.6} ${hy - r * 1.0}, ${hx + r * 0.3} ${hy - r * 0.8} Z" fill="${c}" ${EDGE}/>`;
      case "spikes": return [-0.6, -0.2, 0.2, 0.6].map((o) => `<path d="M${hx + o * r - r * 0.16} ${hy - r * 0.85} L${hx + o * r} ${hy - r * 1.45} L${hx + o * r + r * 0.16} ${hy - r * 0.85} Z" fill="${c}" ${EDGE}/>`).join("");
      case "antlers": return [-1, 1].map((s) => `<path d="M${hx + s * r * 0.4} ${hy - r * 0.8} L${hx + s * r * 0.8} ${hy - r * 1.7} M${hx + s * r * 0.6} ${hy - r * 1.25} L${hx + s * r * 1.15} ${hy - r * 1.45} M${hx + s * r * 0.72} ${hy - r * 1.5} L${hx + s * r * 0.55} ${hy - r * 1.9}" stroke="#C9A36B" stroke-width="6" stroke-linecap="round"/>`).join("");
      case "crown": return `<path d="M${hx - r * 0.8} ${hy - r * 0.75} L${hx - r * 0.7} ${hy - r * 1.5} L${hx - r * 0.3} ${hy - r * 1.05} L${hx} ${hy - r * 1.65} L${hx + r * 0.3} ${hy - r * 1.05} L${hx + r * 0.7} ${hy - r * 1.5} L${hx + r * 0.8} ${hy - r * 0.75} Z" fill="#E3A93B" ${EDGE}/><circle cx="${hx}" cy="${hy - r * 1.15}" r="${r * 0.1}" fill="#D6503E"/>`;
      default: return "";
    }
  }
  function teeth(kind, hx, hy, r) {
    const y = hy + r * 0.45;
    switch (kind) {
      case "fangs": return `<path d="M${hx - r * 0.35} ${y} Q${hx} ${y + r * 0.12} ${hx + r * 0.35} ${y}" stroke="#2B2621" stroke-width="3" fill="none"/><path d="M${hx - r * 0.22} ${y + 1} l${r * 0.07} ${r * 0.22} l${r * 0.07} -${r * 0.2} Z M${hx + r * 0.08} ${y + 1} l${r * 0.07} ${r * 0.22} l${r * 0.07} -${r * 0.2} Z" fill="#FBF8F0"/>`;
      case "grin": return `<path d="M${hx - r * 0.45} ${y - r * 0.05} Q${hx} ${y + r * 0.35} ${hx + r * 0.45} ${y - r * 0.05} Z" fill="#2B2621"/><path d="M${hx - r * 0.35} ${y} h${r * 0.7}" stroke="#FBF8F0" stroke-width="3" stroke-dasharray="4 3"/>`;
      case "tusks": return `<path d="M${hx - r * 0.3} ${y} l-${r * 0.08} -${r * 0.35} l${r * 0.17} ${r * 0.1} Z M${hx + r * 0.3} ${y} l${r * 0.08} -${r * 0.35} l-${r * 0.17} ${r * 0.1} Z" fill="#F3EBDA" ${EDGE}/><path d="M${hx - r * 0.25} ${y} h${r * 0.5}" stroke="#2B2621" stroke-width="3"/>`;
      default: return "";
    }
  }
  // Item held at (x, y) in the front hand.
  function item(kind, x, y) {
    switch (kind) {
      case "club": return `<g transform="rotate(20 ${x} ${y})"><rect x="${x - 6}" y="${y - 90}" width="12" height="100" rx="5" fill="#6B4A2E" ${EDGE}/><ellipse cx="${x}" cy="${y - 96}" rx="20" ry="28" fill="#8A6A48" ${EDGE}/></g>`;
      case "dagger": return `<path d="M${x - 4} ${y} L${x} ${y - 50} L${x + 4} ${y} Z" fill="#C9CCD4" ${EDGE}/><rect x="${x - 10}" y="${y - 2}" width="20" height="6" fill="#5B3A22"/>`;
      case "staff": return `<rect x="${x - 4}" y="${y - 130}" width="8" height="160" rx="4" fill="#4A3A2E" ${EDGE}/><circle cx="${x}" cy="${y - 136}" r="13" fill="#6FE0FF" opacity=".85" ${EDGE}/><circle cx="${x}" cy="${y - 136}" r="24" fill="#6FE0FF" opacity=".16"/>`;
      case "shield": return `<path d="M${x - 30} ${y - 60} H${x + 30} V${y - 10} Q${x} ${y + 24} ${x - 30} ${y - 10} Z" fill="#6E7A8C" ${EDGE}/><path d="M${x} ${y - 52} V${y + 6} M${x - 22} ${y - 30} H${x + 22}" stroke="#C9A04A" stroke-width="5"/>`;
      case "scythe": return `<rect x="${x - 4}" y="${y - 130}" width="8" height="160" rx="4" fill="#3A2E28" ${EDGE}/><path d="M${x} ${y - 128} C${x - 60} ${y - 140}, ${x - 80} ${y - 100}, ${x - 70} ${y - 80} C${x - 58} ${y - 110}, ${x - 30} ${y - 118}, ${x} ${y - 112} Z" fill="#C9CCD4" ${EDGE}/>`;
      case "sword": return `<g transform="rotate(15 ${x} ${y})"><path d="M${x - 6} ${y - 18} L${x - 6} ${y - 120} L${x} ${y - 134} L${x + 6} ${y - 120} L${x + 6} ${y - 18} Z" fill="#D8DBE2" ${EDGE}/><rect x="${x - 20}" y="${y - 20}" width="40" height="8" rx="3" fill="#C9A04A" ${EDGE}/><rect x="${x - 4}" y="${y - 12}" width="8" height="24" fill="#5B3A22"/></g>`;
      case "axe": return `<g transform="rotate(15 ${x} ${y})"><rect x="${x - 4}" y="${y - 110}" width="8" height="130" rx="4" fill="#6B4A2E" ${EDGE}/><path d="M${x + 2} ${y - 104} C${x + 44} ${y - 118}, ${x + 50} ${y - 70}, ${x + 2} ${y - 72} Z" fill="#C9CCD4" ${EDGE}/></g>`;
      case "trident": return `<rect x="${x - 4}" y="${y - 120}" width="8" height="150" rx="4" fill="#8C6A3E" ${EDGE}/><path d="M${x - 22} ${y - 150} V${y - 118} H${x + 22} V${y - 150} M${x} ${y - 160} V${y - 118}" stroke="#C9CCD4" stroke-width="7" fill="none" stroke-linecap="round"/>`;
      case "orb": return `<circle cx="${x}" cy="${y - 26}" r="20" fill="#B48CE0" opacity=".9" ${EDGE}/><circle cx="${x}" cy="${y - 26}" r="34" fill="#B48CE0" opacity=".18"/><circle cx="${x - 6}" cy="${y - 32}" r="6" fill="#fff" opacity=".6"/>`;
      case "bow": return `<path d="M${x} ${y - 90} C${x - 40} ${y - 50}, ${x - 40} ${y + 20}, ${x} ${y + 50}" fill="none" stroke="#7A5230" stroke-width="8" stroke-linecap="round"/><path d="M${x} ${y - 90} L${x} ${y + 50}" stroke="#EDE6D6" stroke-width="2"/>`;
      default: return "";
    }
  }

  // Drawn behind the body: wings, a tail, tentacles, or a glowing aura.
  function extra(kind, w, a) {
    const c = shade(a.accent, -0.05), cx = w / 2;
    switch (kind) {
      case "wings": return [-1, 1].map((s) => `<path d="M${cx + s * 30} 130 C${cx + s * 120} 40, ${cx + s * 150} 120, ${cx + s * 128} 190 C${cx + s * 110} 160, ${cx + s * 90} 176, ${cx + s * 70} 160 C${cx + s * 60} 180, ${cx + s * 44} 170, ${cx + s * 30} 170 Z" fill="${c}" opacity=".92" ${EDGE}/>`).join("");
      case "tail": return `<path d="M${cx + 40} 200 C${cx + 110} 210, ${cx + 130} 150, ${cx + 104} 120" stroke="${a.color}" stroke-width="16" fill="none" stroke-linecap="round"/><path d="M${cx + 96} 118 l14 -22 l8 26 Z" fill="${c}" ${EDGE}/>`;
      case "tentacles": return [-60, -25, 25, 60].map((o, i) => `<path d="M${cx + o * 0.6} 190 C${cx + o} 230, ${cx + o * 1.6} 220, ${cx + o * 1.5} ${250 - i % 2 * 14}" stroke="${shade(a.color, -0.1)}" stroke-width="13" fill="none" stroke-linecap="round"/>`).join("");
      case "aura": return `<ellipse cx="${cx}" cy="160" rx="${w * 0.55}" ry="130" fill="${a.accent}" opacity=".18"/><ellipse cx="${cx}" cy="160" rx="${w * 0.45}" ry="112" fill="none" stroke="${a.accent}" stroke-width="3" stroke-dasharray="6 8" opacity=".6"/>`;
      default: return "";
    }
  }

  // Each body returns the drawing plus where the head and hand go.
  function body(kind, a) {
    const c = a.color, d = shade(c, -0.14), acc = a.accent;
    switch (kind) {
      case "beast": return { svg: `<path d="M150 ${170} Q190 150 200 120" stroke="${c}" stroke-width="12" fill="none" stroke-linecap="round"/>
        <rect x="52" y="188" width="18" height="44" rx="7" fill="${d}" ${EDGE}/><rect x="80" y="192" width="18" height="40" rx="7" fill="${d}" ${EDGE}/><rect x="128" y="192" width="18" height="40" rx="7" fill="${d}" ${EDGE}/><rect x="152" y="188" width="18" height="44" rx="7" fill="${d}" ${EDGE}/>
        <ellipse cx="112" cy="170" rx="72" ry="38" fill="${c}" ${EDGE}/><path d="M60 150 Q112 130 164 150" stroke="${acc}" stroke-width="7" fill="none"/>`, head: [44, 140, 34], hand: null, w: 220 };
      case "blob": return { svg: `<path d="M30 232 C20 160, 60 90, 120 88 C180 90, 220 160, 210 232 Z" fill="${c}" opacity=".92" ${EDGE}/><ellipse cx="90" cy="130" rx="20" ry="12" fill="#fff" opacity=".25"/><path d="M40 232 q20 -14 40 0 q20 -14 40 0 q20 -14 40 0 q20 -14 40 0" fill="${d}"/>`, head: [120, 150, 40], hand: null, bare: true, w: 240 };
      case "bug": return { svg: `<g stroke="#2B2621" stroke-width="5" stroke-linecap="round"><path d="M90 196 l-26 36 M120 200 l-8 34 M170 200 l8 34 M200 196 l26 36"/></g>
        <ellipse cx="170" cy="170" rx="62" ry="40" fill="${d}" ${EDGE}/><ellipse cx="120" cy="174" rx="54" ry="38" fill="${c}" ${EDGE}/><path d="M160 134 q18 36 0 72" stroke="${acc}" stroke-width="5" fill="none"/>`, head: [70, 168, 34], hand: null, w: 240 };
      case "ghost": return { svg: `<path d="M120 60 C70 60 62 110 64 160 L54 236 L78 220 L94 238 L110 220 L126 238 L142 220 L158 238 L176 220 L186 236 L176 160 C178 110 170 60 120 60 Z" fill="${c}" opacity=".9" stroke="${acc}" stroke-width="3"/>`, head: [120, 110, 38], hand: [176, 170], bare: true, w: 240 };
      case "construct": return { svg: `<rect x="70" y="200" width="36" height="36" fill="${d}" ${EDGE}/><rect x="134" y="200" width="36" height="36" fill="${d}" ${EDGE}/>
        <rect x="52" y="112" width="136" height="96" rx="10" fill="${c}" ${EDGE}/><path d="M70 130 h100 M70 150 h100 M70 170 h100" stroke="${acc}" stroke-width="5"/><circle cx="120" cy="160" r="14" fill="${acc}" ${EDGE}/>
        <rect x="24" y="118" width="30" height="80" rx="10" fill="${d}" ${EDGE}/><rect x="186" y="118" width="30" height="80" rx="10" fill="${d}" ${EDGE}/>`, head: [120, 84, 34], hand: [201, 200], w: 240 };
      case "bigboss": return { svg: `<rect x="80" y="236" width="36" height="50" rx="12" fill="${d}" ${EDGE}/><rect x="144" y="236" width="36" height="50" rx="12" fill="${d}" ${EDGE}/>
        <ellipse cx="130" cy="190" rx="100" ry="76" fill="${c}" ${EDGE}/><path d="M40 176 Q130 146 220 176 L216 200 Q130 174 44 200 Z" fill="${acc}" ${EDGE}/>
        <rect x="18" y="150" width="40" height="92" rx="16" fill="${d}" ${EDGE}/>`, head: [130, 96, 58], hand: [220, 238], w: 260 };
      case "serpent": return { svg: `<path d="M40 226 C40 190, 110 196, 120 214 C130 232, 196 230, 200 196 C204 160, 150 150, 130 170 C116 184, 96 170, 104 146 C110 124, 120 112, 120 100" stroke="${c}" stroke-width="30" fill="none" stroke-linecap="round"/>
        <path d="M40 226 C40 190, 110 196, 120 214 C130 232, 196 230, 200 196" stroke="${acc}" stroke-width="6" fill="none" stroke-dasharray="10 12"/>`, head: [120, 88, 34], hand: null, w: 240 };
      case "plant": return { svg: `<path d="M50 232 Q120 214 190 232 L178 252 H62 Z" fill="#6B4A2E" ${EDGE}/><path d="M120 234 C104 190, 134 160, 120 110" stroke="#4F7D3B" stroke-width="20" fill="none" stroke-linecap="round"/>
        <path d="M116 214 C54 206, 26 150, 40 120 C80 140, 106 170, 116 214 Z M124 190 C186 180, 214 126, 200 98 C160 118, 136 150, 124 190 Z" fill="#6FA14F" ${EDGE}/>
        ${[0, 60, 120, 180, 240, 300].map((d) => `<ellipse cx="120" cy="34" rx="24" ry="44" fill="${c}" transform="rotate(${d} 120 88)" ${EDGE}/>`).join("")}`, head: [120, 88, 40], hand: null, w: 240 };
      default: return { svg: `<rect x="86" y="182" width="24" height="52" rx="9" fill="${d}" ${EDGE}/><rect x="130" y="182" width="24" height="52" rx="9" fill="${d}" ${EDGE}/>
        <path d="M70 124 Q120 110 170 124 L176 200 Q120 214 64 200 Z" fill="${acc}" ${EDGE}/><rect x="64" y="178" width="112" height="10" fill="${shade(acc, -0.2)}"/>
        <rect x="46" y="124" width="24" height="64" rx="11" fill="${c}" ${EDGE}/><rect x="170" y="124" width="24" height="64" rx="11" fill="${c}" ${EDGE}/>`, head: [120, 84, 42], hand: [182, 192], w: 240 };
    }
  }

  function render(artIn, opts = {}) {
    const a = { body: "humanoid", color: "#8DB85A", accent: "#8C6A3E", eyes: "two", head: "round", horns: "none", teeth: "none", item: "none", size: 1, ...(artIn || {}) };
    const b = body(a.body, a);
    const [hx, hy, r] = b.head;
    const faceOnly = b.bare && a.head === "round";  // blobs and ghosts wear their face on the body
    const headSvg = faceOnly ? "" : head(a.head, hx, hy, r, a);
    const itemSvg = b.hand && a.item !== "none" ? item(a.item, b.hand[0], b.hand[1]) : "";
    const hand = b.hand ? `<circle cx="${b.hand[0]}" cy="${b.hand[1]}" r="12" fill="${a.color}" ${EDGE}/>` : "";
    const h = Math.round((opts.height || 180) * Math.max(0.6, Math.min(1.5, a.size || 1)));
    const vb = b.w;
    return `<svg viewBox="0 -30 ${vb} 300" height="${h}" width="${Math.round((h * vb) / 300)}" style="overflow:visible" role="img" aria-label="${a.name || "monster"}">
      ${extra(a.extra, vb, a)}${b.svg}${horns(a.horns, hx, hy, r, a)}${headSvg}${a.head === "none" && !b.bare ? "" : eyes(a.eyes, hx, hy, r, a.head === "hood")}${teeth(a.teeth, hx, hy, r)}${itemSvg}${hand}</svg>`;
  }

  window.MonsterArt = { render, BODIES, HEADS, EYES, HORNS, TEETH, ITEMS, EXTRAS };
})();
