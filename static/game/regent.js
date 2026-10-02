/* The Null Regent, System Administrator: the December boss, in paper-craft.
 *   Regent.art({ height })  -> SVG string (fight screen, hub panel)
 */
(function () {
  const EDGE = 'stroke="rgba(40,25,15,.3)" stroke-width="2.5" stroke-linejoin="round"';
  // Floating "windows" that orbit his head like a crown: [x, y, w, h, tilt]
  const WINDOWS = [[18, 40, 34, 26, -14], [56, 8, 30, 22, -6], [104, 0, 32, 24, 0], [152, 8, 30, 22, 6], [188, 40, 34, 26, 14]];
  const win = ([x, y, w, h, r], i) => `<g transform="rotate(${r} ${x + w / 2} ${y + h / 2})">
      <rect x="${x}" y="${y}" width="${w}" height="${h}" rx="2" fill="#FBF8F0" ${EDGE}/>
      <rect x="${x}" y="${y}" width="${w}" height="6" rx="2" fill="${i % 2 ? "#D6503E" : "#E3A93B"}"/>
      <path d="M${x + 5} ${y + 12} h${w - 12} M${x + 5} ${y + 18} h${w - 18}" stroke="#2B2621" stroke-width="2" opacity=".55"/></g>`;
  function art(opts = {}) {
    const h = opts.height || 240;
    return `<svg class="regent" viewBox="0 0 240 300" height="${h}" width="${Math.round(h * 0.8)}" role="img" aria-label="The Null Regent">
      <!-- glitched cape: slices knocked out of line -->
      <path d="M58 110 L20 292 L220 292 L182 110 Z" fill="#22305A" ${EDGE}/>
      <rect x="22" y="200" width="60" height="10" fill="#6FE0FF" opacity=".75"/><rect x="160" y="236" width="56" height="8" fill="#D6503E" opacity=".8"/>
      <rect x="34" y="258" width="44" height="7" fill="#D6503E" opacity=".7"/><rect x="172" y="168" width="36" height="7" fill="#6FE0FF" opacity=".7"/>
      <!-- robe -->
      <path d="M120 84 C82 84 70 120 72 160 L58 292 L182 292 L168 160 C170 120 158 84 120 84 Z" fill="#11162B" ${EDGE}/>
      <path d="M120 150 V288 M120 190 H96 V224 M120 236 H146 V262 M120 170 H144" stroke="#6FE0FF" stroke-width="3" fill="none" opacity=".8"/>
      <circle cx="96" cy="224" r="4" fill="#6FE0FF"/><circle cx="146" cy="262" r="4" fill="#6FE0FF"/><circle cx="144" cy="170" r="4" fill="#6FE0FF"/>
      <path d="M86 132 L120 160 L154 132" fill="none" stroke="#E3A93B" stroke-width="7" stroke-linejoin="round"/>
      <!-- arm and scepter: a giant mouse pointer -->
      <path d="M166 150 Q196 160 200 196" stroke="#11162B" stroke-width="20" fill="none" stroke-linecap="round"/>
      <circle cx="200" cy="200" r="11" fill="#E3DCC8" ${EDGE}/>
      <path d="M200 120 L200 176 L212 164 L222 186 L230 182 L220 160 L236 158 Z" fill="#FBF8F0" ${EDGE}/>
      <rect x="196" y="196" width="8" height="84" rx="3" fill="#E3A93B" ${EDGE}/>
      <path d="M74 150 Q50 170 58 204" stroke="#11162B" stroke-width="20" fill="none" stroke-linecap="round"/>
      <circle cx="58" cy="208" r="11" fill="#E3DCC8" ${EDGE}/>
      <!-- hood and the void where a face should be -->
      <path d="M120 44 C86 44 76 80 80 118 L160 118 C164 80 154 44 120 44 Z" fill="#22305A" ${EDGE}/>
      <ellipse cx="120" cy="92" rx="28" ry="30" fill="#05070F"/>
      <rect x="102" y="84" width="13" height="7" fill="#6FE0FF"/><rect x="125" y="84" width="13" height="7" fill="#6FE0FF"/>
      <rect class="regent-cursor" x="114" y="104" width="12" height="4" fill="#6FE0FF"/>
      ${WINDOWS.map(win).join("")}
    </svg>`;
  }
  window.Regent = { art };
})();
