/* The Listening Dungeon — fight-scene backdrops by book genre (look only).
 *
 *   DungeonThemes.stage(theme) -> "<svg ...>"   (480×290, floor from y=232)
 *   DungeonThemes.THEMES[theme] -> { name, intro }
 *
 * The server picks the theme (game_rules.pick_theme) from the series' genre
 * tags; an unknown theme falls back to the stone dungeon.
 */
(function () {
  const THEMES = {
    dungeon: { name: "Stone Halls", intro: "Stone walls, one torch, and a smell you'll never forget. Classic." },
    sect: { name: "Mountain Sect", intro: "Mist, pines and a very long staircase. The elders are watching. They are not impressed." },
    station: { name: "Derelict Station", intro: "Life support is at 12%. The lights flicker. Something skitters in the vents." },
    ruins: { name: "Ruined City", intro: "What's left of a city. The System calls it 'urban renewal.'" },
    crypt: { name: "Haunted Crypt", intro: "Candles light themselves as you pass. That's never a good sign." },
    city: { name: "Night City", intro: "Wet streets, neon signs, and a monster that definitely doesn't pay rent." },
    academy: { name: "Arcane Academy", intro: "The library is open after hours. So are the things that live in it." },
    digital: { name: "Glitched Server", intro: "Reality is rendering at low settings. Please do not clip through the floor." },
    wilds: { name: "Wild Frontier", intro: "Fresh air, tall pines, and something large moving in the trees." },
  };

  const torch = (x, id) => `<defs><radialGradient id="${id}"><stop offset="0" stop-color="#F4C766" stop-opacity=".35"/><stop offset="1" stop-color="#F4C766" stop-opacity="0"/></radialGradient></defs>
    <circle cx="${x}" cy="80" r="130" fill="url(#${id})"/>
    <g><rect x="${x - 7}" y="84" width="14" height="46" fill="#6B4A2E"/><path d="M${x} 52 C${x - 15} 72 ${x - 11} 86 ${x} 88 C${x + 11} 86 ${x + 15} 72 ${x} 52 Z" fill="#E3A93B"/><path d="M${x} 64 C${x - 7} 76 ${x - 5} 84 ${x} 85 C${x + 5} 84 ${x + 7} 76 ${x} 64 Z" fill="#F6E3A1"/></g>`;
  const stars = (pts, c = "#FBF8F0") => pts.map(([x, y, r]) => `<circle cx="${x}" cy="${y}" r="${r || 1.6}" fill="${c}"/>`).join("");

  const STAGES = {
    dungeon: `<rect width="480" height="290" fill="#3E4559"/>
      <g fill="#4A5268" stroke="#353B4D" stroke-width="4">
        <rect x="-20" y="10" width="110" height="52" rx="8"/><rect x="96" y="10" width="120" height="52" rx="8"/><rect x="222" y="10" width="100" height="52" rx="8"/><rect x="328" y="10" width="170" height="52" rx="8"/>
        <rect x="30" y="68" width="120" height="52" rx="8"/><rect x="156" y="68" width="110" height="52" rx="8"/><rect x="272" y="68" width="130" height="52" rx="8"/><rect x="408" y="68" width="90" height="52" rx="8"/>
        <rect x="-30" y="126" width="100" height="52" rx="8"/><rect x="76" y="126" width="140" height="52" rx="8"/><rect x="222" y="126" width="100" height="52" rx="8"/><rect x="328" y="126" width="160" height="52" rx="8"/>
      </g>${torch(239, "dg-glow")}
      <rect y="232" width="480" height="58" fill="#6E5A45"/><rect y="230" width="480" height="6" fill="#8C7458"/>`,

    sect: `<defs><linearGradient id="dg-sky-sect" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#CFE3DA"/><stop offset="1" stop-color="#F3E7CF"/></linearGradient></defs>
      <rect width="480" height="290" fill="url(#dg-sky-sect)"/><circle cx="380" cy="60" r="30" fill="#F2BE8A"/>
      <path d="M0 200 L70 110 L130 170 L210 80 L290 170 L350 120 L480 200 Z" fill="#9DB5A8"/>
      <path d="M0 232 L60 170 L140 215 L230 150 L320 212 L400 160 L480 232 Z" fill="#7E9A8E"/>
      <g transform="translate(210 80)"><rect x="-10" y="-6" width="20" height="16" fill="#8C3A2E"/><path d="M-22 -4 L0 -20 L22 -4 Z" fill="#B8453A"/><rect x="-7" y="-26" width="14" height="10" fill="#8C3A2E"/><path d="M-16 -24 L0 -36 L16 -24 Z" fill="#B8453A"/></g>
      <g fill="#FBF8F0" opacity=".7"><ellipse cx="120" cy="178" rx="120" ry="10"/><ellipse cx="370" cy="190" rx="140" ry="9"/></g>
      <g><path d="M40 0 V26" stroke="#2B2621" stroke-width="2"/><ellipse cx="40" cy="38" rx="12" ry="14" fill="#D6503E"/><rect x="34" y="50" width="12" height="4" fill="#E3A93B"/>
        <path d="M440 0 V18" stroke="#2B2621" stroke-width="2"/><ellipse cx="440" cy="30" rx="12" ry="14" fill="#D6503E"/><rect x="434" y="42" width="12" height="4" fill="#E3A93B"/></g>
      <rect y="232" width="480" height="58" fill="#8C5A3A"/><g stroke="#6E4428" stroke-width="3"><path d="M0 250 H480 M0 270 H480"/></g><rect y="228" width="480" height="7" fill="#B8453A"/>`,

    station: `<rect width="480" height="290" fill="#1E2433"/>
      <g fill="#2C3448" stroke="#3E4966" stroke-width="3"><rect x="6" y="10" width="140" height="100" rx="6"/><rect x="334" y="10" width="140" height="100" rx="6"/><rect x="6" y="118" width="140" height="106" rx="6"/><rect x="334" y="118" width="140" height="106" rx="6"/></g>
      <circle cx="240" cy="110" r="84" fill="#0B0F1E" stroke="#8C95AA" stroke-width="10"/>
      ${stars([[200, 70], [262, 58, 2], [290, 120], [214, 150], [250, 170, 1.2], [190, 118, 1.2], [300, 90, 1.2]])}
      <circle cx="268" cy="140" r="24" fill="#D6503E"/><path d="M240 146 Q268 132 298 138" stroke="#F2BE8A" stroke-width="4" fill="none"/>
      <g><circle cx="30" cy="30" r="5" fill="#6FE0FF"/><circle cx="50" cy="30" r="5" fill="#D6503E"/><circle cx="450" cy="30" r="5" fill="#8CFF5A"/>
        <rect x="360" y="140" width="90" height="10" fill="#6FE0FF" opacity=".5"/><rect x="360" y="158" width="60" height="10" fill="#6FE0FF" opacity=".3"/></g>
      <rect y="232" width="480" height="58" fill="#3A4150"/><g stroke="#2C3140" stroke-width="3"><path d="M0 250 H480 M0 268 H480"/><path d="M60 232 V290 M160 232 V290 M260 232 V290 M360 232 V290 M460 232 V290"/></g>
      <g fill="#E3A93B"><path d="M0 226 H480 V234 H0 Z"/></g><g fill="#2B2621"><path d="M0 234 L8 226 H20 L12 234 Z M40 234 L48 226 H60 L52 234 Z M80 234 L88 226 H100 L92 234 Z M120 234 L128 226 H140 L132 234 Z M160 234 L168 226 H180 L172 234 Z M200 234 L208 226 H220 L212 234 Z M240 234 L248 226 H260 L252 234 Z M280 234 L288 226 H300 L292 234 Z M320 234 L328 226 H340 L332 234 Z M360 234 L368 226 H380 L372 234 Z M400 234 L408 226 H420 L412 234 Z M440 234 L448 226 H460 L452 234 Z"/></g>`,

    ruins: `<defs><linearGradient id="dg-sky-ruins" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6E5A7E"/><stop offset=".7" stop-color="#E8A06A"/></linearGradient></defs>
      <rect width="480" height="290" fill="url(#dg-sky-ruins)"/><circle cx="120" cy="170" r="40" fill="#F2BE8A" opacity=".8"/>
      <g fill="#4A4458"><path d="M0 232 V120 H40 L52 100 L60 130 V232 Z"/><path d="M70 232 V80 H130 V110 L118 100 L112 120 L130 130 V232 Z"/><path d="M150 232 V150 H200 L210 138 V232 Z"/>
        <path d="M230 232 V60 H300 V90 L286 76 L280 100 L300 108 V232 Z"/><path d="M320 232 V130 H370 L380 118 L386 150 V232 Z"/><path d="M400 232 V96 H470 V124 L456 110 L450 136 V232 Z"/></g>
      <g fill="#E3A93B" opacity=".8"><rect x="86" y="140" width="8" height="10"/><rect x="250" y="90" width="8" height="10"/><rect x="270" y="150" width="8" height="10"/><rect x="420" y="160" width="8" height="10"/></g>
      <g fill="#352F40"><rect x="80" y="170" width="10" height="12"/><rect x="104" y="190" width="10" height="12"/><rect x="246" y="120" width="10" height="12"/><rect x="436" y="130" width="10" height="12"/></g>
      <rect y="232" width="480" height="58" fill="#6E6458"/><g fill="#57504A"><path d="M20 238 l20 -10 l24 8 l-8 10 Z M170 244 l30 -14 l20 12 l-20 8 Z M330 240 l24 -10 l30 8 l-14 10 Z M420 246 l20 -8 l20 6 l-10 8 Z"/></g>`,

    crypt: `<rect width="480" height="290" fill="#2B2436"/>
      <g fill="#3A3346" stroke="#231D2C" stroke-width="4"><path d="M20 232 V110 Q20 40 100 40 Q180 40 180 110 V232 Z"/><path d="M300 232 V110 Q300 40 380 40 Q460 40 460 110 V232 Z"/></g>
      <g fill="#191420"><path d="M50 232 V120 Q50 76 100 76 Q150 76 150 120 V232 Z"/><path d="M330 232 V120 Q330 76 380 76 Q430 76 430 120 V232 Z"/></g>
      <g stroke="#8C857A" stroke-width="1.5" fill="none" opacity=".6"><path d="M0 0 L60 40 M0 20 L40 0 M0 0 Q30 30 20 60 M480 0 L420 40 M480 20 L440 0"/></g>
      <g><rect x="232" y="150" width="16" height="40" fill="#E3DCC8"/><path d="M240 132 C232 142 234 150 240 152 C246 150 248 142 240 132 Z" fill="#8CFF5A"/>
        <rect x="200" y="170" width="12" height="28" fill="#E3DCC8"/><path d="M206 156 C200 164 202 170 206 172 C210 170 212 164 206 156 Z" fill="#8CFF5A"/>
        <rect x="268" y="166" width="12" height="32" fill="#E3DCC8"/><path d="M274 152 C268 160 270 166 274 168 C278 166 280 160 274 152 Z" fill="#8CFF5A"/></g>
      <circle cx="240" cy="160" r="70" fill="#8CFF5A" opacity=".08"/>
      <rect y="232" width="480" height="58" fill="#3A3346"/><g fill="#4A4458"><path d="M70 232 V214 Q84 200 98 214 V232 Z M390 232 V210 Q406 194 422 210 V232 Z"/></g>`,

    city: `<rect width="480" height="290" fill="#1E2440"/><circle cx="400" cy="50" r="22" fill="#F3EBDA"/><circle cx="392" cy="46" r="20" fill="#1E2440"/>
      ${stars([[40, 30], [120, 20], [200, 44], [300, 24], [460, 90]])}
      <g fill="#2C3354"><rect x="0" y="90" width="80" height="142"/><rect x="90" y="60" width="70" height="172"/><rect x="170" y="110" width="60" height="122"/><rect x="250" y="70" width="90" height="162"/><rect x="350" y="100" width="70" height="132"/><rect x="430" y="80" width="60" height="152"/></g>
      <g fill="#F2D14A"><rect x="14" y="110" width="10" height="12"/><rect x="50" y="140" width="10" height="12"/><rect x="104" y="80" width="10" height="12"/><rect x="130" y="130" width="10" height="12"/><rect x="186" y="150" width="10" height="12"/>
        <rect x="266" y="90" width="10" height="12"/><rect x="300" y="120" width="10" height="12"/><rect x="316" y="170" width="10" height="12"/><rect x="366" y="130" width="10" height="12"/><rect x="444" y="110" width="10" height="12"/></g>
      <g><rect x="208" y="180" width="54" height="18" rx="3" fill="#D6503E"/><text x="235" y="193" font-family="Permanent Marker, sans-serif" font-size="12" fill="#FBF8F0" text-anchor="middle">OPEN</text></g>
      <g><rect x="60" y="150" width="6" height="82" fill="#4A5268"/><path d="M52 150 H74 L68 142 H58 Z" fill="#4A5268"/><circle cx="63" cy="154" r="30" fill="#F2D14A" opacity=".14"/></g>
      <rect y="232" width="480" height="58" fill="#2E3040"/><g fill="#F2D14A" opacity=".18"><rect x="50" y="240" width="26" height="40"/><rect x="210" y="238" width="50" height="20"/></g><rect y="230" width="480" height="4" fill="#4A5268"/>`,

    academy: `<rect width="480" height="290" fill="#6B4A36"/>
      <g><path d="M200 200 V90 Q200 40 240 40 Q280 40 280 90 V200 Z" fill="#22305A" stroke="#4A3222" stroke-width="8"/>${stars([[220, 80], [256, 66, 2], [248, 120], [228, 150, 1.2], [262, 170]])}<path d="M240 40 V200 M200 120 H280" stroke="#4A3222" stroke-width="5"/></g>
      ${[0, 1].map((side) => { const x0 = side ? 310 : 10; return `<rect x="${x0}" y="30" width="160" height="202" fill="#4A3222"/>` +
        [0, 1, 2, 3].map((row) => `<rect x="${x0 + 6}" y="${40 + row * 48}" width="148" height="4" fill="#3A2618"/>` +
          Array.from({ length: 11 }, (_, i) => `<rect x="${x0 + 8 + i * 13}" y="${44 + row * 48 + (i % 3) * 3}" width="11" height="${40 - (i % 3) * 3}" fill="${["#D6503E", "#3F74B5", "#E3A93B", "#4E9A55", "#8A4FB8", "#C9A36B"][(i + row * 2 + side) % 6]}"/>`).join("")).join(""); }).join("")}
      <g>${[[120, 20], [360, 14], [260, 22]].map(([x, y]) => `<rect x="${x - 4}" y="${y}" width="8" height="18" fill="#F3EBDA"/><path d="M${x} ${y - 12} C${x - 5} ${y - 4} ${x - 3} ${y} ${x} ${y + 1} C${x + 3} ${y} ${x + 5} ${y - 4} ${x} ${y - 12} Z" fill="#F2D14A"/>`).join("")}</g>
      <rect y="232" width="480" height="58" fill="#8A2E3A"/><rect y="232" width="480" height="6" fill="#E3A93B"/><rect y="282" width="480" height="4" fill="#E3A93B"/>`,

    digital: `<rect width="480" height="290" fill="#0E1020"/>
      <circle cx="240" cy="130" r="60" fill="#D6508A"/><g fill="#0E1020"><rect x="170" y="130" width="140" height="6"/><rect x="170" y="146" width="140" height="8"/><rect x="170" y="164" width="140" height="10"/></g>
      <g fill="#6FE0FF" opacity=".7"><rect x="40" y="40" width="30" height="8"/><rect x="60" y="52" width="14" height="6"/><rect x="390" y="70" width="40" height="8"/><rect x="400" y="84" width="16" height="6"/></g>
      <g fill="#D6508A" opacity=".7"><rect x="100" y="90" width="22" height="6"/><rect x="350" y="30" width="18" height="6"/></g>
      <path d="M0 200 H480" stroke="#6FE0FF" stroke-width="2" opacity=".6"/>
      <rect y="200" width="480" height="90" fill="#141833"/>
      <g stroke="#6FE0FF" stroke-width="2" opacity=".75"><path d="M0 214 H480 M0 232 H480 M0 256 H480 M0 286 H480"/>
        <path d="M240 200 L240 290 M200 200 L140 290 M280 200 L340 290 M160 200 L40 290 M320 200 L440 290 M120 200 L-60 290 M360 200 L540 290"/></g>`,

    wilds: `<rect width="480" height="290" fill="#BCD4DD"/>
      <g fill="#FBF8F0"><ellipse cx="100" cy="50" rx="46" ry="14"/><ellipse cx="84" cy="42" rx="22" ry="14"/><ellipse cx="370" cy="36" rx="40" ry="12"/></g>
      <path d="M0 190 C 100 150, 200 200, 300 165 S 440 150, 480 170 L480 232 L0 232 Z" fill="#9DB77E"/>
      ${[[40, 150, 1], [110, 170, 0.8], [360, 150, 1.1], [430, 175, 0.8], [300, 185, 0.7]].map(([x, y, s]) => `<g transform="translate(${x} ${y}) scale(${s})"><rect x="-5" y="40" width="10" height="24" fill="#6B4A2E"/><path d="M0 -40 L28 10 H14 L34 44 H-34 L-14 10 H-28 Z" fill="#3E6B34"/></g>`).join("")}
      <rect y="232" width="480" height="58" fill="#4F7D3B"/><rect y="228" width="480" height="8" fill="#C9A36B"/>
      <g fill="#E3A93B"><circle cx="70" cy="252" r="4"/><circle cx="200" cy="264" r="4"/><circle cx="330" cy="250" r="4"/></g><g fill="#FBF8F0"><circle cx="140" cy="270" r="4"/><circle cx="420" cy="262" r="4"/></g>`,
  };

  // ── extra base scenes used by series looks ────────────────────────────
  STAGES.oasis = `<defs><linearGradient id="dg-sky-oasis" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#140F2E"/><stop offset="1" stop-color="#3E2F5A"/></linearGradient></defs>
    <rect width="480" height="290" fill="url(#dg-sky-oasis)"/>
    ${stars([[30, 20], [80, 50, 1.2], [140, 16, 2], [190, 60], [260, 24, 1.2], [310, 48], [360, 14, 2], [420, 40], [455, 70, 1.2], [110, 90, 1.2], [340, 96]])}
    <path d="M60 60 Q240 -10 430 70" stroke="#8A6FD0" stroke-width="18" fill="none" opacity=".18"/>
    <path d="M0 200 C 90 170, 170 190, 240 175 S 400 165, 480 190 L480 232 L0 232 Z" fill="#6E5A45"/>
    <g fill="#8C7458"><path d="M300 232 V150 H330 V140 H350 V150 H380 V232 Z"/><path d="M110 232 V160 L130 146 L150 160 V232 Z"/></g>
    <g fill="#F2D14A" opacity=".7"><rect x="318" y="170" width="8" height="10"/><rect x="352" y="186" width="8" height="10"/><rect x="126" y="178" width="7" height="9"/></g>
    <ellipse cx="240" cy="226" rx="70" ry="10" fill="#2FB57A"/><ellipse cx="240" cy="226" rx="90" ry="16" fill="#2FB57A" opacity=".18"/>
    <rect y="232" width="480" height="58" fill="#C9A36B"/><path d="M0 250 Q120 240 240 252 T480 246" stroke="#B08A58" stroke-width="3" fill="none"/>`;
  STAGES.forest = `<rect width="480" height="290" fill="#2E4A34"/>
    <g fill="#3E6B45">${[0, 60, 130, 200, 280, 350, 420].map((x, i) => `<rect x="${x}" y="0" width="${40 + (i % 3) * 8}" height="232"/>`).join("")}</g>
    <g fill="#24392A">${[30, 100, 170, 250, 320, 400, 460].map((x) => `<rect x="${x}" y="0" width="14" height="232"/>`).join("")}</g>
    <g fill="#4E8A52" opacity=".85"><ellipse cx="60" cy="10" rx="120" ry="40"/><ellipse cx="260" cy="0" rx="150" ry="36"/><ellipse cx="440" cy="14" rx="110" ry="40"/></g>
    <g fill="#F2E7A0" opacity=".12"><path d="M150 0 L200 0 L260 232 L180 232 Z"/><path d="M330 0 L360 0 L400 232 L350 232 Z"/></g>
    <rect y="232" width="480" height="58" fill="#3E5A2E"/><rect y="228" width="480" height="8" fill="#5A7A3A"/>`;
  STAGES.tower = `<defs><linearGradient id="dg-sky-tower" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2B2240"/><stop offset="1" stop-color="#6E5A7E"/></linearGradient></defs>
    <rect width="480" height="290" fill="url(#dg-sky-tower)"/>
    ${stars([[40, 30], [120, 20, 1.2], [200, 50], [410, 26], [450, 80, 1.2]])}
    <g transform="translate(360 70)"><circle r="34" fill="#E8E1D2"/><path d="M-6 -34 L4 -8 L-8 8 L6 34" stroke="#2B2240" stroke-width="4" fill="none"/></g>
    <g fill="#3A3150"><path d="M20 232 V150 H60 V120 H80 V150 H110 V232 Z"/><path d="M330 232 V170 H360 V140 H380 V170 H420 V232 Z"/><path d="M430 232 V190 H480 V232 Z"/></g>
    <g fill="#4A4060" stroke="#2B2240" stroke-width="3"><rect x="150" y="190" width="180" height="42"/><rect x="170" y="150" width="140" height="40"/><rect x="190" y="110" width="100" height="40"/><rect x="208" y="70" width="64" height="40"/><rect x="224" y="36" width="32" height="34"/></g>
    <g fill="#F2D14A" opacity=".75"><rect x="232" y="48" width="6" height="8"/><rect x="214" y="124" width="8" height="10"/><rect x="258" y="124" width="8" height="10"/><rect x="200" y="164" width="8" height="10"/><rect x="272" y="164" width="8" height="10"/></g>
    <rect y="232" width="480" height="58" fill="#4A4458"/><rect y="228" width="480" height="6" fill="#6E6480"/>`;

  // ── characters and props (drawn small, in the background) ─────────────
  const EDGE = 'stroke="rgba(40,25,15,.3)" stroke-width="1.5" stroke-linejoin="round"';
  const sticker = (inner) => `<g style="filter:drop-shadow(2px 0 0 #fff) drop-shadow(-2px 0 0 #fff) drop-shadow(0 2px 0 #fff) drop-shadow(0 -2px 0 #fff)">${inner}</g>`;
  const PROPS = {
    // Princess Donut: a fluffy Persian cat with a tiara
    donut: (x, y) => sticker(`<g transform="translate(${x} ${y})"><ellipse cx="0" cy="18" rx="22" ry="16" fill="#F2E3C8" ${EDGE}/><circle cx="0" cy="-4" r="16" fill="#F7EBD6" ${EDGE}/>
      <path d="M-14 -12 L-12 -26 L-4 -16 Z M14 -12 L12 -26 L4 -16 Z" fill="#F7EBD6" ${EDGE}/><path d="M-12 -20 L-8 -30 L-3 -22 L0 -32 L3 -22 L8 -30 L12 -20 Z" fill="#E3A93B" ${EDGE}/>
      <circle cx="0" cy="-26" r="2.4" fill="#D6508A"/><ellipse cx="-6" cy="-5" rx="3" ry="3.4" fill="#3F74B5"/><ellipse cx="6" cy="-5" rx="3" ry="3.4" fill="#3F74B5"/>
      <path d="M-2 2 L2 2 L0 4 Z" fill="#D6508A"/><path d="M20 22 Q34 10 28 -2" stroke="#F2E3C8" stroke-width="8" fill="none" stroke-linecap="round"/></g>`),
    // Mongo: a small blue baby dinosaur
    mongo: (x, y) => sticker(`<g transform="translate(${x} ${y})"><path d="M-20 20 Q-26 0 -8 -2 L6 -18 Q18 -24 22 -12 Q22 -4 12 -2 L12 18 Z" fill="#5A8FD0" ${EDGE}/>
      <path d="M-20 20 Q-36 18 -40 6" stroke="#5A8FD0" stroke-width="7" fill="none" stroke-linecap="round"/><circle cx="14" cy="-13" r="2.4" fill="#2B2621"/>
      <path d="M-8 -2 l4 -6 l3 5 l4 -6 l3 5" stroke="#3F6FB0" stroke-width="3" fill="none"/><rect x="-12" y="18" width="6" height="10" fill="#3F6FB0"/><rect x="4" y="18" width="6" height="10" fill="#3F6FB0"/></g>`),
    // Shade: a faceless shadow in a tall hat and cloak
    shade: (x, y) => `<g transform="translate(${x} ${y})" style="filter:drop-shadow(0 0 3px #B79BFF) drop-shadow(0 0 1px #B79BFF)"><path d="M-18 40 Q-20 0 0 -6 Q20 0 18 40 Z" fill="#141022"/><circle cx="0" cy="-14" r="11" fill="#141022"/>
      <rect x="-9" y="-40" width="18" height="20" fill="#141022"/><rect x="-15" y="-22" width="30" height="4" fill="#141022"/><circle cx="-4" cy="-14" r="1.6" fill="#8A6FD0"/><circle cx="4" cy="-14" r="1.6" fill="#8A6FD0"/></g>`,
    // Gordon: a floating orb covered in little eyes
    gordon: (x, y) => sticker(`<g transform="translate(${x} ${y})"><circle r="16" fill="#3E2F5A" ${EDGE}/>${[[-6, -6], [6, -4], [0, 6], [-9, 5], [9, 7]].map(([a, b]) => `<circle cx="${a}" cy="${b}" r="3" fill="#F2D14A"/><circle cx="${a}" cy="${b}" r="1.2" fill="#2B2621"/>`).join("")}
      <circle r="24" fill="#F2D14A" opacity=".12"/></g>`),
    // Sylphie: a small, very smug green hawk
    sylphie: (x, y) => sticker(`<g transform="translate(${x} ${y})"><path d="M0 0 Q-26 -20 -40 -8 Q-24 -4 -12 8 Z M0 0 Q26 -20 40 -8 Q24 -4 12 8 Z" fill="#4FBF6A" ${EDGE}/>
      <ellipse cx="0" cy="6" rx="10" ry="13" fill="#6FD68A" ${EDGE}/><circle cx="0" cy="-8" r="7" fill="#6FD68A" ${EDGE}/><path d="M0 -7 l6 3 l-6 2 Z" fill="#E3A93B"/><circle cx="-2" cy="-10" r="1.4" fill="#2B2621"/></g>`),
    // Frank: a gleaming axe with a very handsome face
    frank: (x, y) => sticker(`<g transform="translate(${x} ${y}) rotate(-12)"><rect x="-3" y="-10" width="6" height="70" rx="2" fill="#6B4A2E" ${EDGE}/>
      <path d="M-4 -30 Q-44 -30 -40 6 Q-24 -4 -4 -2 Z" fill="#C9CCD4" ${EDGE}/><path d="M4 -24 Q24 -22 22 0 L4 -4 Z" fill="#AEB2BC" ${EDGE}/>
      <circle cx="-26" cy="-16" r="1.8" fill="#2B2621"/><circle cx="-16" cy="-16" r="1.8" fill="#2B2621"/><path d="M-27 -10 Q-21 -6 -15 -10" stroke="#2B2621" stroke-width="1.6" fill="none"/>
      <path d="M-28 -21 l5 -1 M-18 -22 l5 1" stroke="#2B2621" stroke-width="1.4"/><path d="M-30 -8 Q-21 -2 -12 -8" stroke="#6B4A2E" stroke-width="2" fill="none"/>
      <path d="M-34 -28 l3 3 M-10 -30 l2 4" stroke="#FBF8F0" stroke-width="2"/></g>`),
    // Ilea: a silhouetted fighter with green healing fists and ash drifting off her
    ilea: (x, y) => `<g transform="translate(${x} ${y})" style="filter:drop-shadow(0 0 2px #FBF8F0) drop-shadow(0 0 1px #FBF8F0)"><path d="M-8 40 L-6 6 L-14 22 M8 40 L6 6 L14 20" stroke="#2A2A30" stroke-width="6" stroke-linecap="round" fill="none"/>
      <path d="M-9 8 Q0 -2 9 8 L7 -14 Q0 -20 -7 -14 Z" fill="#2A2A30"/><circle cx="0" cy="-24" r="8" fill="#2A2A30"/><path d="M-8 -26 Q-18 -10 -12 0" stroke="#2A2A30" stroke-width="4" fill="none"/>
      <circle cx="-15" cy="22" r="5" fill="#6FD68A"/><circle cx="15" cy="20" r="5" fill="#6FD68A"/><circle cx="-15" cy="22" r="10" fill="#6FD68A" opacity=".25"/><circle cx="15" cy="20" r="10" fill="#6FD68A" opacity=".25"/>
      ${[[-20, -30], [18, -36], [26, -20], [-26, -12]].map(([a, b]) => `<rect x="${a}" y="${b}" width="4" height="4" fill="#8C857A" opacity=".7" transform="rotate(30 ${a} ${b})"/>`).join("")}</g>`,
    // the Undying Lord on his bone throne
    undying: (x, y) => `<g transform="translate(${x} ${y})"><path d="M-40 60 V0 Q-40 -30 -26 -40 L-22 -20 L-12 -46 L0 -24 L12 -46 L22 -20 L26 -40 Q40 -30 40 0 V60 Z" fill="#E3DCC8" opacity=".85"/>
      <path d="M-14 60 V10 Q0 -2 14 10 V60 Z" fill="#1E1A22"/><circle cx="0" cy="-2" r="11" fill="#1E1A22"/><circle cx="-4" cy="-3" r="2" fill="#8CFF5A"/><circle cx="4" cy="-3" r="2" fill="#8CFF5A"/>
      <path d="M-8 -12 L-6 -20 L-2 -13 L0 -22 L2 -13 L6 -20 L8 -12 Z" fill="#E3A93B"/></g>`,
    // a red-eyed killer bunny
    bunny: (x, y) => sticker(`<g transform="translate(${x} ${y})"><ellipse cx="0" cy="12" rx="16" ry="13" fill="#F3EBDA" ${EDGE}/><circle cx="0" cy="-6" r="11" fill="#F3EBDA" ${EDGE}/>
      <ellipse cx="-5" cy="-24" rx="4" ry="12" fill="#F3EBDA" ${EDGE}/><ellipse cx="5" cy="-24" rx="4" ry="12" fill="#F3EBDA" ${EDGE}/><circle cx="-4" cy="-7" r="2.4" fill="#D6503E"/><circle cx="4" cy="-7" r="2.4" fill="#D6503E"/>
      <path d="M-3 -1 l1.5 4 l1.5 -4 M0 -1 l1.5 4 l1.5 -4" fill="#FBF8F0" stroke="#2B2621" stroke-width=".8"/></g>`),
    // a coiled serpent carved into a stone gate (the Viper's challenge dungeon)
    vipergate: (x, y) => `<g transform="translate(${x} ${y})"><path d="M-60 0 V-110 Q-60 -150 0 -154 Q60 -150 60 -110 V0 Z" fill="#5A6070"/><path d="M-38 0 V-96 Q-38 -124 0 -126 Q38 -124 38 -96 V0 Z" fill="#101418"/>
      <path d="M-50 -20 Q-56 -80 -30 -120 Q0 -146 30 -120 Q52 -90 44 -40" stroke="#4FBF6A" stroke-width="9" fill="none" stroke-linecap="round"/><path d="M44 -40 l-8 10 l14 -2 Z" fill="#4FBF6A"/><circle cx="46" cy="-44" r="2" fill="#F2D14A"/>
      <circle cx="0" cy="-70" r="30" fill="#4FBF6A" opacity=".08"/></g>`,
    alchemy: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-34" y="0" width="68" height="8" fill="#6B4A2E"/><rect x="-30" y="8" width="6" height="30" fill="#6B4A2E"/><rect x="24" y="8" width="6" height="30" fill="#6B4A2E"/>
      <path d="M-22 0 V-12 L-28 -24 H-14 L-20 -12 V0 Z" fill="#8CFF5A" opacity=".85"/><circle cx="4" cy="-9" r="9" fill="#6FE0FF" opacity=".8"/><rect x="2" y="-22" width="4" height="6" fill="#C9CCD4"/>
      <path d="M20 0 V-16 H28 V0 Z" fill="#D6508A" opacity=".8"/><circle cx="4" cy="-26" r="2" fill="#8CFF5A"/><circle cx="-20" cy="-30" r="1.6" fill="#8CFF5A"/></g>`,
    saveSign: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-44" y="-16" width="88" height="30" rx="4" fill="#0E1020" stroke="#8CFF5A" stroke-width="3"/>
      <text x="0" y="5" font-family="Permanent Marker, sans-serif" font-size="14" fill="#8CFF5A" text-anchor="middle">SAVE POINT</text><rect x="-3" y="14" width="6" height="40" fill="#4A5268"/></g>`,
    colosseum: (x, y) => `<g transform="translate(${x} ${y})"><path d="M-110 0 V-70 Q0 -96 110 -70 V0 Z" fill="#8C7A5A"/>${[0, 1].map((r) => Array.from({ length: 9 }, (_, i) => `<path d="M${-96 + i * 22} ${-8 - r * 30} v-16 q7 -8 14 0 v16 Z" fill="#4A3A2A"/>`).join("")).join("")}
      <rect x="-80" y="-86" width="56" height="20" fill="#D6508A"/><text x="-52" y="-72" font-family="sans-serif" font-size="9" fill="#FBF8F0" text-anchor="middle">DYNAMIS</text>
      <rect x="30" y="-90" width="60" height="22" fill="#6FE0FF"/><text x="60" y="-75" font-family="sans-serif" font-size="9" fill="#0E1020" text-anchor="middle">LIVE HEROES</text></g>`,
    lightning: (x, y) => `<path transform="translate(${x} ${y})" d="M0 0 L-12 30 L2 28 L-10 62 L20 20 L6 22 L16 0 Z" fill="#E8456A" opacity=".85"/>`,
    invaderShip: (x, y) => `<g transform="translate(${x} ${y})"><ellipse rx="80" ry="16" fill="#4A5268"/><ellipse cy="-8" rx="36" ry="14" fill="#6E7A8C"/>${[-60, -30, 0, 30, 60].map((a) => `<circle cx="${a}" cy="4" r="4" fill="#8CFF5A"/>`).join("")}
      <path d="M-20 16 L-40 80 H40 L20 16 Z" fill="#8CFF5A" opacity=".08"/></g>`,
    trialArch: (x, y) => `<g transform="translate(${x} ${y})"><path d="M-40 0 V-80 Q0 -120 40 -80 V0 H26 V-76 Q0 -104 -26 -76 V0 Z" fill="#6E6A7E"/><path d="M-26 0 V-76 Q0 -104 26 -76 V0 Z" fill="#8A6FD0" opacity=".5"/>
      <path d="M-20 -10 Q0 -60 20 -10" stroke="#E8E1D2" stroke-width="2" fill="none" opacity=".6"/></g>`,
    guardBanner: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-2" y="-60" width="4" height="90" fill="#4A3A2E"/><path d="M2 -58 H40 V-10 L21 -20 L2 -10 Z" fill="#3F74B5"/><path d="M21 -50 L28 -34 L21 -28 L14 -34 Z" fill="#E3A93B"/></g>`,
    safeRoom: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-36" y="-14" width="72" height="26" rx="3" fill="#0E3A1E" stroke="#8CFF5A" stroke-width="3"/><text x="0" y="5" font-family="Permanent Marker, sans-serif" font-size="12" fill="#8CFF5A" text-anchor="middle">SAFE ROOM</text></g>`,
    desperado: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-58" y="-18" width="116" height="34" rx="6" fill="#1E1030" stroke="#D6508A" stroke-width="3"/><text x="0" y="-1" font-family="Permanent Marker, sans-serif" font-size="12" fill="#F2D14A" text-anchor="middle">DESPERADO</text>
      <text x="0" y="12" font-family="Permanent Marker, sans-serif" font-size="9" fill="#D6508A" text-anchor="middle">CLUB</text></g>`,
    viewers: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-40" y="-26" width="80" height="50" rx="4" fill="#2B2621" stroke="#8C857A" stroke-width="3"/><rect x="-34" y="-20" width="68" height="38" fill="#22305A"/>
      <text x="0" y="-4" font-family="sans-serif" font-size="8" fill="#FBF8F0" text-anchor="middle">VIEWERS</text><text x="0" y="10" font-family="Permanent Marker, sans-serif" font-size="12" fill="#F2D14A" text-anchor="middle">1.2B ▲</text></g>`,
    headStart: (x, y) => `<g transform="translate(${x} ${y})"><path d="M-70 -14 H70 L62 0 L70 14 H-70 L-62 0 Z" fill="#E3A93B"/><text x="0" y="5" font-family="Permanent Marker, sans-serif" font-size="12" fill="#2B2621" text-anchor="middle">HEAD START: 3 DAYS</text></g>`,
    butler: (x, y) => `<g transform="translate(${x} ${y})" opacity=".7"><path d="M-14 30 L-10 0 H10 L14 30 Z" fill="#6FE0FF"/><circle cy="-10" r="10" fill="#6FE0FF"/><path d="M-6 4 L0 10 L6 4" stroke="#0E1020" stroke-width="2" fill="none"/><circle cx="-4" cy="-11" r="1.5" fill="#0E1020"/><circle cx="4" cy="-11" r="1.5" fill="#0E1020"/></g>`,
    centipede: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-2" y="-70" width="4" height="100" fill="#2B2621"/><path d="M2 -68 H44 V-4 L23 -14 L2 -4 Z" fill="#8C2E2A"/>
      <g stroke="#1E1A22" stroke-width="2">${[0, 1, 2, 3, 4].map((i) => `<ellipse cx="23" cy="${-58 + i * 9}" rx="6" ry="4" fill="#1E1A22"/><path d="M14 ${-58 + i * 9} h-4 M32 ${-58 + i * 9} h4"/>`).join("")}</g></g>`,
    timeout: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-54" y="-14" width="108" height="26" fill="#FBF8F0" stroke="#2B2621" stroke-width="2"/><text x="0" y="4" font-family="Permanent Marker, sans-serif" font-size="11" fill="#D6503E" text-anchor="middle">DUNGEON TIMEOUT</text></g>`,
    runeCircle: (x, y) => `<g transform="translate(${x} ${y})"><ellipse rx="90" ry="14" fill="none" stroke="#8A6FD0" stroke-width="3"/><ellipse rx="66" ry="10" fill="none" stroke="#6FE0FF" stroke-width="2"/>
      ${[-70, -40, 0, 40, 70].map((a) => `<path d="M${a} -3 l4 6 l-8 0 Z" fill="#8A6FD0"/>`).join("")}<ellipse rx="90" ry="14" fill="#8A6FD0" opacity=".12"/></g>`,
    wurthavenCrest: (x, y) => `<g transform="translate(${x} ${y})"><path d="M-22 -26 H22 V6 Q0 26 -22 6 Z" fill="#22305A" stroke="#E3A93B" stroke-width="3"/><path d="M0 -18 L6 -4 L0 10 L-6 -4 Z" fill="#E3A93B"/><circle cy="-4" r="3" fill="#FBF8F0"/></g>`,
    spiritOrb: (x, y) => `<g transform="translate(${x} ${y})"><path d="M-12 -30 Q0 -40 12 -30 V6 H-12 Z" fill="none" stroke="#C9A04A" stroke-width="2"/>${[-8, -3, 2, 7].map((a) => `<path d="M${a} -34 V6" stroke="#C9A04A" stroke-width="1.5"/>`).join("")}<circle cy="-10" r="6" fill="#6FE0FF"/><circle cy="-10" r="12" fill="#6FE0FF" opacity=".2"/></g>`,
    riverwatch: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-120" y="-40" width="240" height="40" fill="#7A7068"/>${Array.from({ length: 12 }, (_, i) => `<rect x="${-120 + i * 20}" y="-50" width="12" height="10" fill="#7A7068"/>`).join("")}
      <rect x="-20" y="-60" width="40" height="60" fill="#6A6058"/><path d="M-12 0 V-30 Q0 -40 12 -30 V0 Z" fill="#3A342E"/></g>`,
    ash: () => `<g fill="#B9B1A2" opacity=".6">${[[40, 30], [90, 80], [150, 40], [210, 110], [270, 60], [330, 20], [380, 100], [440, 50], [120, 150], [300, 140]].map(([a, b]) => `<rect x="${a}" y="${b}" width="4" height="3" transform="rotate(25 ${a} ${b})"/>`).join("")}</g>`,
    fistEmblem: (x, y) => `<g transform="translate(${x} ${y})"><circle r="18" fill="#3E4A3E" stroke="#6FD68A" stroke-width="3"/><path d="M-8 6 V-6 Q-8 -10 -4 -10 H8 Q10 -10 10 -6 V6 Q10 10 6 10 H-4 Q-8 10 -8 6 Z" fill="#6FD68A"/><path d="M-4 -10 V2 M1 -10 V2 M6 -10 V2" stroke="#3E4A3E" stroke-width="1.5"/></g>`,
    hedge: () => `<g fill="#2E5A34"><rect x="0" y="120" width="60" height="112"/><rect x="420" y="130" width="60" height="102"/><rect x="0" y="120" width="120" height="30"/></g><g fill="#3E6B45"><circle cx="20" cy="124" r="14"/><circle cx="60" cy="118" r="16"/><circle cx="100" cy="126" r="12"/><circle cx="440" cy="132" r="14"/><circle cx="470" cy="126" r="12"/></g>`,
    starCloak: (x, y) => `<g transform="translate(${x} ${y})"><path d="M-30 0 Q-20 -40 0 -44 Q20 -40 30 0 Q0 8 -30 0 Z" fill="#1E1440"/>${stars([[-14, -20, 1.2], [4, -30, 1.4], [14, -12, 1.2], [-4, -8, 1], [20, -26, 1]])}</g>`,
  };
  const P = (name, x, y, ...rest) => PROPS[name](x, y, ...rest);

  // ── series looks (Round 1: series two or more readers have finished) ──
  // Look and words only: monsters, stats and rewards are unchanged. The
  // boss keeps its stats but takes a villain's name from the books.
  const SERIES = {
    hwfwm: { name: "The Astral Oasis", base: "oasis",
      props: () => P("hedge") + P("starCloak", 280, 196) + P("shade", 200, 158) + P("gordon", 290, 80),
      intro: "An astral space has opened. Everyone is very calm about this. Too calm.",
      quips: ["Someone nearby is monologuing. Stab them while they're distracted.", "The System has noted that you are being a bit much. As usual.", "A shadow is watching you. It seems supportive, in a creepy way."],
      boss: { name: "Garth Larosse, Priest of Undeath", appear: "Garth Larosse rises, rattling with the blessings of Undeath. He has a speech prepared. Nobody asked." } },
    dcc: { name: "The World Dungeon", base: "dungeon",
      props: () => P("safeRoom", 90, 30) + P("desperado", 370, 40) + P("viewers", 240, 110) + P("donut", 210, 196) + P("mongo", 272, 200),
      intro: "Welcome, Crawler! The audience is watching. Please die in an entertaining way.",
      quips: ["Viewer numbers are climbing. The sponsors are thrilled. You should be worried.", "A Bronze Box awaits. Probably. The AI is feeling generous today.", "Reminder: the stairwells close eventually. No pressure."],
      boss: { name: "The Hoarder", appear: "The Hoarder heaves herself up from a mountain of junk. The cockroaches cheer." } },
    primal: { name: "The Tutorial Forest", base: "forest",
      props: () => P("vipergate", 240, 232) + P("alchemy", 150, 196) + P("sylphie", 330, 100),
      intro: "Somewhere, a very old snake is laughing at your stats.",
      quips: ["Your Bloodline is tingling. That's either danger or indigestion.", "A small green hawk is judging your form. Ree.", "The Malefic Viper is watching. He brought snacks."],
      boss: { name: "Richard, Tutorial Faction Leader", appear: "Richard steps out, all smiles and reasonable offers. The menace is obvious to everyone but his followers." } },
    sysuni: { name: "The Integration Zone", base: "ruins",
      props: () => P("invaderShip", 240, 50) + P("bunny", 220, 208) + P("bunny", 268, 214),
      intro: "Cute bunny detected. Do not pet the bunny.",
      quips: ["The invaders have filed paperwork to own this planet. Contest it with violence.", "Fight. Survive. Adapt. Also, keep an eye on the bunnies.", "A butterfly the size of a car drifts past. Nobody panics anymore."],
      boss: { name: "Jace", appear: "Jace steps out to collect the planet. You are, technically, trespassing on your own world." } },
    infinite: { name: "The Trial", base: "crypt",
      props: () => P("undying", 240, 150) + P("trialArch", 120, 232) + P("guardBanner", 360, 200),
      intro: "Another Trial. The Guard sends its regards, and nothing else.",
      quips: ["The Infinite World shifts again. New monsters. Same you.", "Your master would not care if you died here. Be petty and live.", "Somewhere, a Sergeant is shaking his head."],
      boss: { name: "The Undying Lord", appear: "The Undying Lord rises from his throne of bones. He has done this many times. It never gets old for him." } },
    perfectrun: { name: "New Rome", base: "city",
      props: () => P("colosseum", 240, 232) + P("lightning", 330, 10) + P("saveSign", 120, 80),
      intro: "Checkpoint reached. You may not reload. Yes, we checked.",
      quips: ["In another timeline, you already won this. Not this one.", "The Genomes of New Rome are watching. Most of them want your autograph. Some want your spine.", "Somewhere, a very dramatic man is shooting lightning out of his eyes."],
      boss: { name: "Jupiter Augustus, the Lightning King", appear: "Augustus descends in a storm of crimson lightning. He believes he is a god. He is at least very loud." } },
    ripple: { name: "Earth Blood Online", base: "wilds",
      props: () => P("headStart", 240, 30) + P("frank", 240, 170) + P("butler", 380, 150),
      intro: "Head start active. You bought every pass, so this dungeon is all yours. It's lonely.",
      quips: ["A handsome axe suggests you kill everything in the bloodiest way possible. Politely decline.", "Every choice makes ripples. This one mostly makes splashes.", "Your house AI would like to remind you to eat something."],
      boss: { name: "Tyrann, Prophet of the Holy War", appear: "Tyrann rises with a congregation of thousands behind him. His god is watching. So is yours." } },
    towerjack: { name: "The Tower", base: "tower",
      props: () => P("centipede", 110, 200) + P("centipede", 400, 205) + P("timeout", 240, 214),
      intro: "Dungeon timeout, again. The gods would like a word about your behavior.",
      quips: ["The Black Centipede would like you to join. The alternative is less fun.", "World's Best Assassin, you say. The dungeon has notes.", "Broken Moon City glows above. Someone has to conquer it. Why not you?"],
      boss: { name: "The Lich of Broken Moon City", appear: "The immortal lich of Broken Moon City rises. He has outlived every would-be king. He intends to outlive you." } },
    adept: { name: "Wurthaven", base: "academy",
      props: () => P("runeCircle", 240, 236) + P("wurthavenCrest", 240, 120) + P("spiritOrb", 150, 80),
      intro: "Wizards are considered support staff here. The dungeon disagrees.",
      quips: ["Sorcery is supreme, they say. Prove them wrong, one spell at a time.", "The old wizards lifted the world out of superstition. You're lifting it out of this dungeon.", "A caged spirit whispers something about the true cost of sorcery."],
      boss: { name: "The Vengeful Lich", appear: "An ancient lich rises, driven by a vengeance older than the kingdom. He remembers what wizards used to be." } },
    azarinth: { name: "The Wilds of Elos", base: "forest",
      props: () => P("ash") + P("riverwatch", 240, 200) + P("fistEmblem", 380, 80) + P("ilea", 240, 150),
      intro: "Punch it. Heal. Punch it again. The Battle Healer method is very simple.",
      quips: ["Ash drifts down like snow. Something out there burns very hot.", "Healing is just punching with extra steps.", "Riverwatch's walls look sturdy. The monsters look sturdier."],
      boss: { name: "The Eldritch Horror of Elos", appear: "Something that shouldn't exist unfolds in the dark. Every instinct says run. Punch it anyway." } },
  };
  // ── Round 2 base scenes ───────────────────────────────────────────────
  STAGES.tavern = `<rect width="480" height="290" fill="#5A3E2B"/>
    <g stroke="#4A3222" stroke-width="3">${Array.from({ length: 12 }, (_, i) => `<path d="M${i * 40} 0 V232"/>`).join("")}</g>
    <rect y="0" width="480" height="16" fill="#3A2618"/><rect y="40" width="480" height="10" fill="#3A2618"/>
    <g transform="translate(90 120)"><rect x="-54" y="-60" width="108" height="112" fill="#6E6458"/><rect x="-44" y="-40" width="88" height="92" fill="#2B2018"/><path d="M-30 52 Q-20 20 0 34 Q20 18 30 52 Z" fill="#E86A3A"/><path d="M-18 52 Q-8 34 0 42 Q8 32 18 52 Z" fill="#F2D14A"/><circle cy="30" r="46" fill="#E86A3A" opacity=".12"/><rect x="-62" y="-68" width="124" height="10" fill="#8C7A68"/></g>
    <g transform="translate(360 150)"><rect x="-90" y="0" width="180" height="82" fill="#6B4A2E"/><rect x="-96" y="-8" width="192" height="12" fill="#8C5A3A"/>${[-60, -30, 0, 30, 60].map((a) => `<rect x="${a - 8}" y="-80" width="16" height="22" rx="3" fill="#B98A5A" opacity=".85"/>`).join("")}<rect x="-90" y="-90" width="180" height="6" fill="#4A3222"/><rect x="-90" y="-56" width="180" height="6" fill="#4A3222"/></g>
    <g fill="#F2D14A">${[160, 250, 330].map((x) => `<circle cx="${x}" cy="70" r="5"/><path d="M${x} 50 v14" stroke="#2B2621" stroke-width="2"/>`).join("")}</g>
    <rect y="232" width="480" height="58" fill="#6B4A2E"/><g stroke="#4A3222" stroke-width="3">${Array.from({ length: 8 }, (_, i) => `<path d="M0 ${236 + i * 7} H480"/>`).join("")}</g>`;
  STAGES.camp = `<rect width="480" height="290" fill="#C9D9E0"/><g fill="#FBF8F0"><ellipse cx="120" cy="40" rx="50" ry="14"/><ellipse cx="380" cy="60" rx="40" ry="12"/></g>
    <path d="M0 200 C 120 180, 300 196, 480 184 L480 232 L0 232 Z" fill="#9DB77E"/>
    <g fill="#8C6A3E">${Array.from({ length: 24 }, (_, i) => `<path d="M${i * 20} 232 V${170 + (i % 2) * 6} l10 -12 l10 12 V232 Z"/>`).join("")}</g>
    <g><path d="M170 190 L220 140 L270 190 Z" fill="#E3DCC8" stroke="#8C7458" stroke-width="3"/><path d="M220 140 V190" stroke="#8C7458" stroke-width="2"/><path d="M300 196 L336 160 L372 196 Z" fill="#E3DCC8" stroke="#8C7458" stroke-width="3"/></g>
    <rect y="232" width="480" height="58" fill="#8C7458"/><rect y="228" width="480" height="6" fill="#6E5A45"/>`;
  STAGES.farm = `<defs><linearGradient id="dg-sky-farm" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F3D9B0"/><stop offset="1" stop-color="#CFE3DA"/></linearGradient></defs>
    <rect width="480" height="290" fill="url(#dg-sky-farm)"/><path d="M0 170 L80 90 L150 150 L240 70 L330 150 L400 100 L480 160 V232 H0 Z" fill="#A9BFB0"/>
    <g fill="#FBF8F0" opacity=".7"><ellipse cx="160" cy="140" rx="120" ry="8"/><ellipse cx="380" cy="150" rx="110" ry="7"/></g>
    <rect y="176" width="480" height="56" fill="#9DC27E"/><g stroke="#7FA85A" stroke-width="3">${Array.from({ length: 16 }, (_, i) => `<path d="M${i * 30} 182 v10 M${i * 30 + 8} 196 v10 M${i * 30 + 16} 210 v10"/>`).join("")}</g>
    <g transform="translate(380 150)"><rect x="-40" y="0" width="80" height="44" fill="#B98A5A"/><path d="M-52 2 L0 -30 L52 2 Z" fill="#8C3A2E"/><rect x="-8" y="16" width="16" height="28" fill="#5B3A22"/></g>
    <rect y="232" width="480" height="58" fill="#8C6A3E"/><g stroke="#6B4A2E" stroke-width="4"><path d="M0 226 H480"/>${Array.from({ length: 13 }, (_, i) => `<path d="M${i * 40} 214 V240"/>`).join("")}</g>`;
  STAGES.backrooms = `<rect width="480" height="290" fill="#D8C872"/>
    <g stroke="#C4B35E" stroke-width="2">${Array.from({ length: 24 }, (_, i) => `<path d="M${i * 20} 0 V232"/>`).join("")}</g>
    <g fill="#B8A850">${[40, 150, 300, 410].map((x) => `<rect x="${x}" y="70" width="${x === 150 ? 110 : 60}" height="162"/>`).join("")}</g>
    <g fill="#E8E4C8">${[60, 200, 340, 460].map((x) => `<rect x="${x - 30}" y="6" width="60" height="10"/>`).join("")}</g><g fill="#FFF9D0" opacity=".25">${[60, 200, 340, 460].map((x) => `<path d="M${x - 30} 16 H${x + 30} L${x + 60} 120 H${x - 60} Z"/>`).join("")}</g>
    <rect y="232" width="480" height="58" fill="#A89A5A"/><g fill="#968848">${Array.from({ length: 30 }, (_, i) => `<circle cx="${(i * 37) % 480}" cy="${240 + (i * 13) % 44}" r="2"/>`).join("")}</g>`;
  STAGES.bridge = `<rect width="480" height="290" fill="#161B2A"/>
    <path d="M60 20 H420 L400 150 H80 Z" fill="#050814" stroke="#6E7A8C" stroke-width="6"/>${stars([[110, 50], [160, 90], [220, 40, 2], [270, 110], [330, 60], [380, 100, 1.2], [140, 130, 1.2], [300, 136]])}
    <g fill="#6FE0FF" opacity=".75">${[[150, 70], [170, 80], [190, 70], [210, 82], [230, 72]].map(([x, y]) => `<path d="M${x} ${y} l8 3 l-8 3 Z"/>`).join("")}</g>
    <g fill="#D6503E" opacity=".75">${[[320, 90], [340, 100], [360, 92]].map(([x, y]) => `<path d="M${x} ${y} l-8 3 l8 3 Z"/>`).join("")}</g>
    <g fill="#2C3448" stroke="#3E4966" stroke-width="3"><rect x="0" y="160" width="140" height="72"/><rect x="340" y="160" width="140" height="72"/></g>
    <g fill="#6FE0FF" opacity=".6"><rect x="16" y="176" width="40" height="8"/><rect x="16" y="192" width="70" height="6"/><rect x="360" y="178" width="60" height="8"/><rect x="360" y="194" width="40" height="6"/></g>
    <rect y="232" width="480" height="58" fill="#2C3140"/><rect y="228" width="480" height="6" fill="#6E7A8C"/>`;
  STAGES.halls = `<rect width="480" height="290" fill="#14110F"/>
    <g fill="#2E2822">${[20, 110, 200, 290, 380].map((x) => `<rect x="${x}" y="0" width="44" height="232"/><rect x="${x - 6}" y="0" width="56" height="16"/><rect x="${x - 6}" y="214" width="56" height="18"/>`).join("")}</g>
    <g fill="#3A322A">${[20, 110, 200, 290, 380].map((x) => `<rect x="${x + 6}" y="16" width="8" height="198"/>`).join("")}</g>
    <rect y="232" width="480" height="58" fill="#2E2822"/><g stroke="#221D18" stroke-width="3">${Array.from({ length: 12 }, (_, i) => `<path d="M${i * 44} 232 V290"/>`).join("")}</g>`;
  STAGES.void = `<rect width="480" height="290" fill="#0B0A14"/>${stars([[40, 40, 1], [90, 150, 1], [160, 60, 1.4], [230, 180, 1], [300, 30, 1], [360, 130, 1.4], [430, 70, 1], [200, 110, 1]], "#8A6FD0")}
    <g fill="none" stroke="#8A6FD0" stroke-width="2" opacity=".3"><circle cx="240" cy="110" r="60"/><circle cx="240" cy="110" r="100"/><circle cx="240" cy="110" r="140"/></g>
    <path d="M0 232 L60 220 L130 236 L220 222 L300 238 L380 220 L480 232 V290 H0 Z" fill="#1E1A30"/>`;

  // ── Round 2 characters and props ──────────────────────────────────────
  const sign = (x, y, text, bg = "#FBF8F0", fg = "#2B2621", w = 110) => `<g transform="translate(${x} ${y})"><rect x="${-w / 2}" y="-14" width="${w}" height="26" fill="${bg}" stroke="#2B2621" stroke-width="2"/><text x="0" y="4" font-family="Permanent Marker, sans-serif" font-size="11" fill="${fg}" text-anchor="middle">${text}</text></g>`;
  const banner = (x, y, color, emblem = "") => `<g transform="translate(${x} ${y})"><rect x="-2" y="-60" width="4" height="90" fill="#4A3A2E"/><path d="M2 -58 H40 V-6 L21 -16 L2 -6 Z" fill="${color}"/>${emblem}</g>`;
  Object.assign(PROPS, {
    eagle: (x, y) => banner(x, y, "#B8453A", `<path d="M21 -48 L30 -40 L25 -34 L21 -40 L17 -34 L12 -40 Z" fill="#E3A93B"/>`),
    rooster: (x, y) => sticker(`<g transform="translate(${x} ${y})"><ellipse cx="0" cy="8" rx="16" ry="13" fill="#FBF8F0" ${EDGE}/><path d="M-14 6 Q-30 -10 -24 -22 Q-18 -8 -10 -2 Z" fill="#2E6B3A" ${EDGE}/><path d="M-16 0 Q-34 -4 -30 -18" stroke="#8C3A2E" stroke-width="5" fill="none"/>
      <circle cx="10" cy="-8" r="8" fill="#FBF8F0" ${EDGE}/><path d="M6 -16 l2 -6 l3 5 l3 -6 l2 7 Z" fill="#D6503E"/><path d="M17 -8 l7 2 l-7 3 Z" fill="#E3A93B"/><circle cx="12" cy="-10" r="1.5" fill="#2B2621"/><path d="M14 -3 q2 5 -2 6" fill="#D6503E"/>
      <path d="M-4 20 v8 M4 20 v8" stroke="#E3A93B" stroke-width="3"/></g>`),
    pig: (x, y) => sticker(`<g transform="translate(${x} ${y})"><ellipse cx="0" cy="6" rx="24" ry="16" fill="#F2B8B0" ${EDGE}/><circle cx="20" cy="0" r="11" fill="#F2B8B0" ${EDGE}/><ellipse cx="28" cy="2" rx="5" ry="4" fill="#E89A92"/><circle cx="18" cy="-4" r="1.6" fill="#2B2621"/>
      <path d="M14 -10 l4 -6 l3 6 Z" fill="#F2B8B0"/><path d="M-14 20 v8 M-4 22 v8 M8 22 v8 M16 20 v8" stroke="#E89A92" stroke-width="4"/><path d="M-24 2 q-8 -2 -6 -8" stroke="#E89A92" stroke-width="2" fill="none"/></g>`),
    dove: (x, y) => `<g transform="translate(${x} ${y})" opacity=".85"><path d="M-14 30 Q-16 -10 0 -14 Q16 -10 14 30 L8 24 L2 32 L-4 24 L-10 32 Z" fill="#CFE8F5"/><circle cx="-4" cy="-2" r="2" fill="#22305A"/><circle cx="4" cy="-2" r="2" fill="#22305A"/><circle r="30" fill="#CFE8F5" opacity=".15"/></g>`,
    skeletonRack: (x, y) => `<g transform="translate(${x} ${y})">${[-30, 0, 30].map((a) => `<g transform="translate(${a} 0)"><circle cy="-40" r="8" fill="#E3DCC8"/><path d="M0 -32 V0 M-10 -24 H10 M-8 -16 H8 M0 0 l-8 20 M0 0 l8 20" stroke="#E3DCC8" stroke-width="4" stroke-linecap="round"/></g>`).join("")}<rect x="-46" y="22" width="92" height="6" fill="#4A3A2E"/></g>`,
    goblin: (x, y) => sticker(`<g transform="translate(${x} ${y})"><path d="M-12 30 L-8 4 H8 L12 30 Z" fill="#8C6A3E" ${EDGE}/><circle cy="-6" r="12" fill="#8DB85A" ${EDGE}/><path d="M-10 -8 L-24 -14 L-10 -2 Z M10 -8 L24 -14 L10 -2 Z" fill="#8DB85A" ${EDGE}/><circle cx="-4" cy="-7" r="2.4" fill="#F2D14A"/><circle cx="4" cy="-7" r="2.4" fill="#F2D14A"/><path d="M-4 0 q4 3 8 0" stroke="#2B2621" stroke-width="1.5" fill="none"/></g>`),
    fog: () => `<g fill="#FBF8F0" opacity=".35"><ellipse cx="100" cy="200" rx="160" ry="20"/><ellipse cx="360" cy="190" rx="170" ry="22"/><ellipse cx="240" cy="150" rx="200" ry="14"/></g>`,
    villageWall: (x, y, label = "MIST VILLAGE") => `<g transform="translate(${x} ${y})">${Array.from({ length: 11 }, (_, i) => `<path d="M${-110 + i * 20} 0 V-40 l10 -10 l10 10 V0 Z" fill="#8C6A3E"/>`).join("")}${sign(0, -60, label, "#FBF8F0", "#2E5A34", 100)}</g>`,
    dross: (x, y) => sticker(`<g transform="translate(${x} ${y})"><path d="M-18 10 Q-22 -20 0 -22 Q22 -20 18 10 Q10 22 0 18 Q-10 22 -18 10 Z" fill="#8A4FB8" ${EDGE}/><circle cy="-4" r="9" fill="#FBF8F0"/><circle cy="-4" r="5" fill="#2B2621"/><circle cx="2" cy="-6" r="1.6" fill="#FBF8F0"/><path d="M-6 8 q6 4 12 0" stroke="#2B2621" stroke-width="1.5" fill="none"/></g>`),
    orthos: (x, y) => `<g transform="translate(${x} ${y})"><ellipse cx="0" cy="0" rx="60" ry="30" fill="#2B2621"/><path d="M-50 -6 Q0 -44 50 -6" fill="#3A322A"/>${[-30, -10, 10, 30].map((a) => `<path d="M${a - 8} -18 l8 -8 l8 8 Z" fill="#E8456A" opacity=".8"/>`).join("")}<circle cx="64" cy="-4" r="14" fill="#2B2621"/><circle cx="68" cy="-8" r="3" fill="#E8456A"/></g>`,
    blackflame: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-10" y="0" width="20" height="30" fill="#4A4458"/><path d="M0 -40 C-16 -20 -12 -4 0 0 C12 -4 16 -20 0 -40 Z" fill="#1E1A22"/><path d="M0 -26 C-8 -14 -6 -4 0 -2 C6 -4 8 -14 0 -26 Z" fill="#E8456A"/></g>`,
    labWindow: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-50" y="-26" width="100" height="52" fill="#8CD6E8" stroke="#6E7A8C" stroke-width="5" opacity=".85"/>${[-24, 0, 24].map((a) => `<g transform="translate(${a} 14)"><circle cy="-12" r="6" fill="#2B2621" opacity=".6"/><rect x="-7" y="-6" width="14" height="14" fill="#FBF8F0" opacity=".6"/></g>`).join("")}</g>`,
    croc: (x, y) => sticker(`<g transform="translate(${x} ${y})"><ellipse cx="0" cy="8" rx="22" ry="12" fill="#B98A5A" ${EDGE}/><circle cx="20" cy="-4" r="10" fill="#B98A5A" ${EDGE}/><path d="M24 2 Q36 8 34 -2 L28 -2 Z" fill="#8C3A2E"/><path d="M26 0 l2 3 l2 -3 l2 3" stroke="#FBF8F0" stroke-width="1.5" fill="none"/>
      <circle cx="18" cy="-7" r="2.4" fill="#2B2621"/><circle cx="10" cy="-6" r="1.6" fill="#2B2621"/><path d="M14 -12 l-4 -8 l8 4 Z" fill="#8C6A3E"/><path d="M-12 18 v8 M-2 18 v8 M8 18 v8 M16 18 v8" stroke="#8C6A3E" stroke-width="4"/><path d="M-22 4 q-8 -8 -4 -14" stroke="#B98A5A" stroke-width="4" fill="none"/></g>`),
    vallenwood: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-16" y="-120" width="32" height="120" fill="#6B4A2E"/><ellipse cy="-150" rx="80" ry="46" fill="#3E6B34"/><rect x="-44" y="-128" width="88" height="34" fill="#B98A5A"/><path d="M-50 -126 L0 -150 L50 -126 Z" fill="#8C3A2E"/><rect x="-30" y="-120" width="12" height="10" fill="#F2D14A"/><rect x="18" y="-120" width="12" height="10" fill="#F2D14A"/></g>`,
    draconian: (x, y) => `<g transform="translate(${x} ${y})"><path d="M-12 40 L-8 0 H8 L12 40 Z" fill="#6E7A5A"/><path d="M-8 0 L-40 -20 L-26 6 Z M8 0 L40 -20 L26 6 Z" fill="#8C9A6E"/><path d="M-8 -2 Q0 -26 8 -2 Z" fill="#6E7A5A"/><path d="M0 -24 l6 -8 v8 Z" fill="#6E7A5A"/><circle cx="-2" cy="-12" r="1.6" fill="#E8456A"/></g>`,
    staffMagius: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-3" y="-80" width="6" height="110" fill="#4A3A2E"/><path d="M-8 -80 L0 -96 L8 -80 Z" fill="#6E5A8C"/><circle cy="-100" r="8" fill="#CFE8F5"/><circle cy="-100" r="20" fill="#CFE8F5" opacity=".25"/></g>`,
    blackTower: (x, y) => `<g transform="translate(${x} ${y})"><path d="M-26 0 V-150 L-34 -160 H34 L26 -150 V0 Z" fill="#141018"/><path d="M-34 -160 L-26 -176 L-18 -160 L-10 -176 L-2 -160 L6 -176 L14 -160 L22 -176 L34 -160 Z" fill="#141018"/><rect x="-6" y="-120" width="12" height="16" fill="#E8456A" opacity=".8"/></g>`,
    raistlin: (x, y) => `<g transform="translate(${x} ${y})" style="filter:drop-shadow(0 0 2px #E3A93B)"><path d="M-16 44 L-10 -2 Q0 -12 10 -2 L16 44 Z" fill="#1A1420"/><path d="M-12 -2 Q0 -34 12 -2 Z" fill="#1A1420"/><path d="M-5 -12 h3 l-3 5 h3 M3 -12 h3 l-3 5 h3" stroke="#E3A93B" stroke-width="1.4" fill="none"/></g>`,
    hourglass: (x, y) => `<g transform="translate(${x} ${y})"><path d="M-14 -20 H14 L2 0 L14 20 H-14 L-2 0 Z" fill="none" stroke="#E3A93B" stroke-width="3"/><path d="M-8 -16 H8 L0 -4 Z M-10 18 H10 L0 10 Z" fill="#E3A93B"/></g>`,
    redMoon: (x, y) => `<g transform="translate(${x} ${y})"><circle r="30" fill="#C8303A"/><circle r="60" fill="#C8303A" opacity=".12"/><circle cx="-8" cy="-6" r="5" fill="#A0242E"/><circle cx="10" cy="8" r="4" fill="#A0242E"/></g>`,
    dome: () => `<path d="M-10 232 Q240 -40 490 232" fill="#8CD6E8" opacity=".28" stroke="#6FC4DC" stroke-width="5"/><path d="M60 180 Q240 10 420 180" fill="none" stroke="#FBF8F0" stroke-width="2" opacity=".6"/>`,
    dragonSkull: (x, y) => `<g transform="translate(${x} ${y})"><path d="M-40 0 Q-40 -30 0 -34 Q40 -30 44 0 L30 10 L20 2 L10 12 L0 2 L-10 12 L-20 2 L-30 10 Z" fill="#E3DCC8"/><circle cx="-14" cy="-14" r="7" fill="#2B2621"/><circle cx="14" cy="-14" r="7" fill="#2B2621"/><path d="M-30 -30 L-44 -56 L-20 -34 Z M30 -30 L44 -56 L20 -34 Z" fill="#E3DCC8"/></g>`,
    splitSky: () => `<path d="M240 0 L480 0 L480 150 Z" fill="#8A4FB8" opacity=".35"/><path d="M240 0 L480 150" stroke="#FBF8F0" stroke-width="3" stroke-dasharray="8 6"/>`,
    gamePod: (x, y) => `<g transform="translate(${x} ${y})"><ellipse cx="0" cy="0" rx="50" ry="22" fill="#6E7A8C"/><path d="M-44 -4 Q0 -46 44 -4 Z" fill="#6FE0FF" opacity=".5"/><rect x="-30" y="16" width="60" height="10" fill="#4A5268"/><text x="0" y="-10" font-family="sans-serif" font-size="8" fill="#0E1020" text-anchor="middle">ENDLESS</text></g>`,
    blaster: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-20" y="-6" width="40" height="12" rx="3" fill="#4A5268"/><rect x="10" y="-3" width="20" height="6" fill="#6E7A8C"/><rect x="-14" y="6" width="10" height="16" fill="#4A5268"/><circle cx="30" cy="0" r="3" fill="#6FE0FF"/></g>`,
    brokenPortal: (x, y) => `<g transform="translate(${x} ${y})"><path d="M-40 0 V-70 Q0 -110 40 -70 V0" fill="none" stroke="#6E6A7E" stroke-width="10"/><path d="M-36 -50 L-20 -60 L-28 -40 M30 -60 L20 -44 L34 -40" stroke="#0B0A14" stroke-width="4"/><path d="M-28 0 V-66 Q0 -96 28 -66 V0 Z" fill="#8A6FD0" opacity=".25"/></g>`,
    manor: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-80" y="-60" width="160" height="60" fill="#E8E1D2"/><path d="M-90 -58 L0 -100 L90 -58 Z" fill="#3F74B5"/><circle cy="-76" r="10" fill="#E3A93B"/>${[-60, -30, 30, 60].map((a) => `<rect x="${a - 7}" y="-44" width="14" height="20" fill="#3F74B5"/>`).join("")}<rect x="-10" y="-30" width="20" height="30" fill="#5B3A22"/></g>`,
    breach: (x, y) => `<g transform="translate(${x} ${y})"><path d="M0 -50 L10 -20 L4 0 L14 30 L0 50 L-10 20 L-4 0 L-14 -30 Z" fill="#E8456A"/><path d="M0 -50 L10 -20 L4 0 L14 30 L0 50 L-10 20 L-4 0 L-14 -30 Z" fill="none" stroke="#FBF8F0" stroke-width="2"/><ellipse rx="40" ry="60" fill="#E8456A" opacity=".12"/></g>`,
    workshop: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-40" y="-40" width="80" height="40" fill="#8C6A3E"/><path d="M-46 -38 L0 -62 L46 -38 Z" fill="#5B3A22"/><circle cx="20" cy="-20" r="10" fill="#6FE0FF"/><circle cx="20" cy="-20" r="16" fill="#6FE0FF" opacity=".2"/><path d="M-26 -30 h20 v20 h-20 Z" fill="#E3A93B"/></g>`,
    heroStatue: (x, y) => `<g transform="translate(${x} ${y})"><path d="M-60 -200 L60 -200 L30 0 H-30 Z" fill="#FFF3B0" opacity=".25"/><rect x="-24" y="-20" width="48" height="20" fill="#A9A49A"/><path d="M-14 -20 L-10 -70 H10 L14 -20 Z" fill="#C9C3B6"/><circle cy="-80" r="12" fill="#C9C3B6"/><path d="M10 -64 L40 -110" stroke="#C9C3B6" stroke-width="6"/><path d="M40 -110 l6 -10" stroke="#E8E1D2" stroke-width="4"/></g>`,
    trainingPost: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-4" y="-60" width="8" height="60" fill="#6B4A2E"/><rect x="-20" y="-50" width="40" height="8" fill="#8C6A3E"/><circle cy="-66" r="10" fill="#C9A36B"/></g>`,
    well: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-26" y="-24" width="52" height="24" fill="#7A7068"/><path d="M-30 -24 V-60 M30 -24 V-60" stroke="#6B4A2E" stroke-width="5"/><path d="M-36 -60 L0 -76 L36 -60 Z" fill="#8C3A2E"/></g>`,
    captainChair: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-20" y="-40" width="40" height="44" rx="6" fill="#3E4966"/><rect x="-26" y="-6" width="52" height="10" fill="#4A5268"/><rect x="-4" y="4" width="8" height="24" fill="#4A5268"/><text x="0" y="-18" font-family="sans-serif" font-size="7" fill="#E3A93B" text-anchor="middle">DAUNTLESS</text></g>`,
    foolCard: (x, y) => `<g transform="translate(${x} ${y}) rotate(-6)"><rect x="-22" y="-34" width="44" height="68" rx="4" fill="#FBF8F0" stroke="#E3A93B" stroke-width="3"/><circle cy="-6" r="10" fill="#D6503E"/><path d="M-10 -14 L0 -30 L10 -14" fill="#8A4FB8"/><text x="0" y="26" font-family="Permanent Marker, sans-serif" font-size="9" fill="#2B2621" text-anchor="middle">THE FOOL</text></g>`,
    ravener: (x, y) => `<g transform="translate(${x} ${y})" opacity=".55"><path d="M-80 0 Q-60 -60 0 -70 Q60 -60 80 0 Q40 -20 0 -10 Q-40 -20 -80 0 Z" fill="#141018"/><circle cx="-16" cy="-40" r="4" fill="#E8456A"/><circle cx="16" cy="-40" r="4" fill="#E8456A"/></g>`,
    mimicChest: (x, y) => sticker(`<g transform="translate(${x} ${y})"><rect x="-26" y="-4" width="52" height="30" fill="#8C5A3A" ${EDGE}/><path d="M-26 -4 Q0 -34 26 -4" fill="#A86E48" ${EDGE}/><path d="M-22 -2 l4 6 l4 -6 l4 6 l4 -6 l4 6 l4 -6 l4 6 l4 -6 l4 6" stroke="#FBF8F0" stroke-width="2" fill="#2B2621"/>
      <path d="M-6 6 Q0 26 10 16" stroke="#D6508A" stroke-width="7" fill="none" stroke-linecap="round"/><circle cx="-10" cy="-14" r="3" fill="#F2D14A"/><circle cx="10" cy="-14" r="3" fill="#F2D14A"/><rect x="-26" y="10" width="52" height="4" fill="#E3A93B"/></g>`),
    cake: (x, y) => sticker(`<g transform="translate(${x} ${y})"><rect x="-22" y="-10" width="44" height="22" fill="#F2B8B0" ${EDGE}/><rect x="-18" y="-26" width="36" height="16" fill="#FBF8F0" ${EDGE}/><path d="M-22 -10 q6 6 11 0 q6 6 11 0 q6 6 11 0 q6 6 11 0" stroke="#FBF8F0" stroke-width="4" fill="none"/><rect x="-2" y="-38" width="4" height="12" fill="#3F74B5"/><path d="M0 -44 c-3 3 -2 6 0 6 c2 0 3 -3 0 -6" fill="#E3A93B"/></g>`),
    plushDemon: (x, y) => sticker(`<g transform="translate(${x} ${y})"><ellipse cy="8" rx="14" ry="12" fill="#D6503E" ${EDGE}/><circle cy="-8" r="11" fill="#D6503E" ${EDGE}/><path d="M-8 -16 L-12 -28 L-3 -18 Z M8 -16 L12 -28 L3 -18 Z" fill="#2B2621"/><path d="M-6 -10 l4 2 M6 -10 l-4 2" stroke="#2B2621" stroke-width="2"/><path d="M-4 -2 q4 -3 8 0" stroke="#2B2621" stroke-width="1.6" fill="none"/><path d="M12 12 q12 2 10 -8 l4 -2 l-2 6" stroke="#D6503E" stroke-width="3" fill="none"/></g>`),
    rift: (x, y) => `<g transform="translate(${x} ${y})"><path d="M0 -60 Q20 -20 6 0 Q24 30 0 60 Q-18 20 -4 0 Q-22 -30 0 -60 Z" fill="#6FE0FF"/><path d="M0 -60 Q20 -20 6 0 Q24 30 0 60 Q-18 20 -4 0 Q-22 -30 0 -60 Z" fill="none" stroke="#FBF8F0" stroke-width="2"/><ellipse rx="44" ry="70" fill="#6FE0FF" opacity=".14"/></g>`,
    tierTower: (x, y) => `<g transform="translate(${x} ${y})">${[0, 1, 2, 3, 4].map((i) => `<rect x="${-30 + i * 5}" y="${-24 - i * 22}" width="${60 - i * 10}" height="22" fill="${["#8C857A", "#4E9A55", "#3F74B5", "#8A4FB8", "#E3A93B"][i]}" stroke="#2B2621" stroke-width="2"/>`).join("")}</g>`,
    shed: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-40" y="-50" width="80" height="50" fill="#8C6A3E"/><path d="M-46 -48 L0 -76 L46 -48 Z" fill="#5B3A22"/><rect x="-14" y="-38" width="28" height="38" fill="#2B2621"/><circle cy="-20" r="10" fill="#6FE0FF"/><circle cy="-20" r="20" fill="#6FE0FF" opacity=".2"/></g>`,
    scoreboard: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-56" y="-44" width="112" height="84" fill="#0E1020" stroke="#6E7A8C" stroke-width="4"/>${["1 ZENTHA", "2 KORRIN", "3 VALDA", "4 EARTH", "5 MOOK"].map((t, i) => `<text x="-46" y="${-26 + i * 15}" font-family="sans-serif" font-size="10" fill="${t.includes("EARTH") ? "#F2D14A" : "#6FE0FF"}">${t}</text>`).join("")}</g>`,
    countdown: (x, y) => sign(x, y, "364 DAYS LEFT", "#0E1020", "#E8456A", 120),
    eyeTower: (x, y) => `<g transform="translate(${x} ${y})"><path d="M-10 0 L-6 -80 L6 -80 L10 0 Z" fill="#1A1410"/><path d="M-8 -80 L-14 -96 M8 -80 L14 -96" stroke="#1A1410" stroke-width="4"/><ellipse cy="-90" rx="12" ry="6" fill="#E3A93B"/><ellipse cy="-90" rx="3" ry="6" fill="#1A1410"/><circle cy="-90" r="24" fill="#E3A93B" opacity=".15"/></g>`,
    balrogGlow: () => `<ellipse cx="240" cy="200" rx="120" ry="40" fill="#E8456A" opacity=".18"/><path d="M200 232 Q220 180 240 200 Q260 170 280 232 Z" fill="#E86A3A" opacity=".5"/>`,
    goldVault: (x, y) => `<g transform="translate(${x} ${y})"><circle r="44" fill="#6E7A8C" stroke="#4A5268" stroke-width="8"/><circle r="10" fill="#4A5268"/>${[0, 60, 120, 180, 240, 300].map((a) => `<rect x="-3" y="-34" width="6" height="18" fill="#4A5268" transform="rotate(${a})"/>`).join("")}${[[56, 34], [74, 34], [65, 22]].map(([a, b]) => `<rect x="${a - 8}" y="${b - 4}" width="16" height="8" fill="#E3A93B"/>`).join("")}</g>`,
    seedPod: (x, y) => `<g transform="translate(${x} ${y})"><path d="M0 -30 Q-20 -10 -14 10 Q0 22 14 10 Q20 -10 0 -30 Z" fill="#6E8A3E"/><path d="M0 -26 V14" stroke="#4E6A2E" stroke-width="2"/><path d="M-10 14 Q-18 24 -24 20 M10 14 Q18 24 24 20" stroke="#4E6A2E" stroke-width="3" fill="none"/></g>`,
    inn: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-60" y="-50" width="120" height="50" fill="#B98A5A"/><path d="M-70 -48 L0 -84 L70 -48 Z" fill="#6B4A2E"/><rect x="-40" y="-36" width="16" height="14" fill="#F2D14A"/><rect x="24" y="-36" width="16" height="14" fill="#F2D14A"/><rect x="-10" y="-30" width="20" height="30" fill="#5B3A22"/></g>`,
    barrels: (x, y) => `<g transform="translate(${x} ${y})">${[[-20, 0], [20, 0], [0, -30]].map(([a, b]) => `<g transform="translate(${a} ${b})"><ellipse rx="16" ry="14" fill="#8C5A3A"/><path d="M-16 -4 H16 M-16 6 H16" stroke="#4A3222" stroke-width="3"/></g>`).join("")}</g>`,
    scorch: (x, y) => `<g transform="translate(${x} ${y})"><path d="M-40 0 Q-30 -60 0 -70 Q30 -60 40 0 Z" fill="#2B2621" opacity=".45"/><path d="M-20 0 L-10 -40 L0 -10 L10 -50 L20 0 Z" fill="#E86A3A" opacity=".4"/></g>`,
    castleRuin: (x, y) => `<g transform="translate(${x} ${y})"><path d="M-100 0 V-90 H-80 V-100 H-60 V-90 H-40 V-60 L-20 -80 L0 -50 V0 Z" fill="#3A3346"/><path d="M20 0 V-70 H40 V-80 H60 V-70 H80 V-110 H100 V0 Z" fill="#3A3346"/></g>`,
    apothecary: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-40" y="-60" width="80" height="60" fill="#4A3222"/>${[0, 1, 2].map((r) => `<rect x="-36" y="${-56 + r * 20}" width="72" height="3" fill="#2B2018"/>` + [0, 1, 2, 3].map((c) => `<rect x="${-32 + c * 18}" y="${-52 + r * 20}" width="8" height="14" fill="${["#8CFF5A", "#D6508A", "#6FE0FF", "#E3A93B"][(r + c) % 4]}" opacity=".8"/>`).join("")).join("")}</g>`,
    jobBoard: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-44" y="-40" width="88" height="56" fill="#8C6A3E" stroke="#5B3A22" stroke-width="3"/>${[[-30, -30], [-4, -32], [18, -28], [-24, -8], [4, -6]].map(([a, b]) => `<rect x="${a}" y="${b}" width="20" height="16" fill="#FBF8F0" transform="rotate(${(a % 5)} ${a} ${b})"/>`).join("")}<text x="0" y="12" font-family="Permanent Marker, sans-serif" font-size="8" fill="#FBF8F0" text-anchor="middle">JOBS · COIN</text><rect x="-4" y="16" width="8" height="26" fill="#5B3A22"/></g>`,
    dragonEgg: (x, y) => sticker(`<g transform="translate(${x} ${y})"><ellipse rx="14" ry="18" fill="#8C95AA" ${EDGE}/><path d="M-10 -6 l6 4 l6 -6 l6 4" stroke="#4A5268" stroke-width="2" fill="none"/><circle cx="-4" cy="6" r="3" fill="#6FE0FF" opacity=".7"/></g>`),
    carWreck: (x, y) => `<g transform="translate(${x} ${y})"><path d="M-50 0 V-20 L-30 -36 H20 L40 -20 H50 V0 Z" fill="#6E7A8C" transform="rotate(8)"/><circle cx="-30" cy="4" r="10" fill="#2B2621"/><circle cx="30" cy="10" r="10" fill="#2B2621"/><path d="M-20 -30 L0 -20 L-10 -34" stroke="#FBF8F0" stroke-width="1.5" fill="none"/></g>`,
    ruinsStack: () => `<g fill="#5A4E6E" opacity=".8"><path d="M100 120 L140 60 L180 120 Z"/><rect x="300" y="50" width="70" height="70"/><path d="M200 60 Q240 20 280 60 V80 H200 Z" fill="#6E5A8C"/></g><g fill="#8A6FD0" opacity=".5"><circle cx="336" cy="80" r="8"/><circle cx="140" cy="100" r="6"/></g>`,
    dynastyBanner: (x, y) => banner(x, y, "#E3A93B", `<circle cx="21" cy="-38" r="9" fill="none" stroke="#8C2E2A" stroke-width="3"/><path d="M21 -44 V-32" stroke="#8C2E2A" stroke-width="3"/>`),
  });

  Object.assign(SERIES, {
    soldier: { name: "The Legion Camp", base: "camp", props: () => P("eagle", 110, 200) + P("eagle", 380, 200) + P("trainingPost", 250, 212),
      intro: "The Legion doesn't ask. It assigns. Today it assigns you to this dungeon.",
      quips: ["A centurion is watching your footwork. It's bad.", "North Dakota never prepared you for this. Nothing did."],
      boss: { name: "The Telhian Emperor", appear: "The Emperor of the Telhian Empire takes the field himself. The Legion kneels. You are expected to do the same." } },
    ajax: { name: "Gryndor", base: "wilds", props: () => P("inn", 150, 200) + P("scorch", 150, 200) + sign(360, 90, "TO THE CAPITAL →", "#FBF8F0", "#22305A", 130),
      intro: "No regrets. Fight every monster, plunder every treasure. The System approves.",
      quips: ["Humans are one of the weakest races, they say. Make them take it back.", "A spoiled noble somewhere is about to regret everything."],
      boss: { name: "The Baron of the Duchy", appear: "The Baron arrives with the whole Duchy's backing and none of its manners. He remembers your village. Barely." } },
    battleforged: { name: "The Billion-Credit Vault", base: "ruins", props: () => P("goldVault", 240, 120) + P("seedPod", 140, 214) + P("seedPod", 330, 210),
      intro: "Ninety percent mortality. Ten percent heist. The odds are thrilling.",
      quips: ["That pod is staring at you. Do not climb into the pod.", "The gold is right there. So is everything that wants to kill you."] },
    ashwood: { name: "The Brewer's Road", base: "wilds", props: () => P("inn", 240, 210) + P("barrels", 130, 222) + P("scorch", 360, 220),
      intro: "You were a brewer this morning. Adventure is one long hangover.",
      quips: ["Heroes are made, not born. Mostly they're made of bruises.", "Somewhere a demon is looking for your sister. Walk faster."],
      boss: { name: "The High Mage of the Sanctuary", appear: "The High Mage of the Sanctuary descends, robes spotless and hands anything but. The Sanctuary protects mankind. From everyone but itself." } },
    chicken: { name: "The Fa Ram", base: "farm", props: () => P("rooster", 220, 170) + P("pig", 280, 180),
      intro: "The rooster has claimed this dungeon. Respect the rooster.",
      quips: ["A very proud chicken is supervising. Try to look worthy.", "The rice needs planting after this. Hurry up.", "Somewhere, a cultivator is shouting about face. Ignore him."] },
    bookdead: { name: "The Necromancer's Cellar", base: "crypt", props: () => P("skeletonRack", 240, 196) + P("dove", 330, 90),
      intro: "Forbidden class detected. We won't tell anyone. Probably.",
      quips: ["Your skeletons stand a little straighter when you look at them.", "A friendly ghost reminds you to eat and plan your revenge."] },
    chaos: { name: "Mist Village", base: "forest", props: () => P("fog") + P("villageWall", 240, 214) + P("goblin", 150, 196),
      intro: "A Place of Power. Currently powered by goblins.",
      quips: ["Chaos stirs in your soul. It wants snacks.", "The Land is old and angry. So are its goblins."] },
    cradle: { name: "Sacred Valley", base: "sect", props: () => P("orthos", 330, 206) + P("dross", 160, 110) + P("blackflame", 250, 190),
      intro: "Your advancement is… adequate. For Copper.",
      quips: ["A purple, one-eyed spirit has opinions about your technique. Many opinions.", "Somewhere, a very large turtle is proud of you.", "Unsouled? Not for long."] },
    descend: { name: "The Experiment", base: "dungeon", props: () => P("labWindow", 240, 90),
      intro: "This experiment is going great. For us.",
      quips: ["The observers are taking notes. Mostly about how you scream.", "Conquer the dungeon or die. Those are the options on the form."] },
    discountdan: { name: "The Backrooms", base: "backrooms", props: () => sign(240, 70, "BACKROOM BARGAINS", "#D6503E", "#FBF8F0", 160) + P("croc", 240, 206),
      intro: "You noclipped. Everyone noclips once. Most people only once.",
      quips: ["A dog that is definitely a mimic wags its… tongue.", "The fluorescent lights buzz. So does something else.", "Store hours: whenever you survive."],
      boss: { name: "The Flayed Monarch", appear: "The Flayed Monarch of the 999th floor descends from the Skinless Court. You have been marked. Nobody walks away with their hide." } },
    dlchronicles: { name: "Solace", base: "wilds", props: () => P("vallenwood", 240, 232) + P("draconian", 380, 196) + P("staffMagius", 110, 210),
      intro: "The inn is closed. The dragons are open.",
      quips: ["A draconian statue watches you. It was never a statue.", "Somewhere, a very old gnome is inventing something that will explode."] },
    dllegends: { name: "The Tower of High Sorcery", base: "tower", props: () => P("blackTower", 240, 232) + P("raistlin", 330, 180) + P("hourglass", 140, 70),
      intro: "Time travel is strictly for professionals. You are not one.",
      quips: ["A figure in black robes coughs politely. Do not make eye contact.", "The hourglass eyes see everything wither. Including your stats."] },
    dlwar: { name: "The Shielded Forest", base: "wilds", props: () => P("dome") + P("dragonSkull", 240, 210),
      intro: "A shield keeps the dragons out. And you in.",
      quips: ["The dragon overlords are fighting over the map. You're standing on it.", "A young woman speaks of the One God. The monsters are listening."] },
    dualclass: { name: "The Merged Worlds", base: "ruins", props: () => P("splitSky") + sign(240, 190, "TUTORIAL →", "#FBF8F0", "#8A4FB8", 100),
      intro: "Worlds merging. Please mind the seam.",
      quips: ["The tutorial was ridiculous. This is worse.", "Two worlds, one System, zero patience."] },
    endless: { name: "The Game That Isn't", base: "bridge", props: () => P("gamePod", 240, 206) + P("blaster", 120, 180),
      intro: "Log out? What a charming idea.",
      quips: ["It's not a game. Earth is the prize. Play well.", "Blasters, spaceships and magic. The corporation calls it 'immersive.'"] },
    murderhobo: { name: "The Plane That Shouldn't Exist", base: "void", props: () => P("brokenPortal", 240, 232) + banner(120, 200, "#22305A"),
      intro: "No class trainer. No problem. No mercy.",
      quips: ["Your humanity is optional down here. So is mercy.", "Something hollow is watching from the Hollow Kingdom."] },
    healersway: { name: "The Bulatov Estate", base: "wilds", props: () => P("manor", 240, 200) + P("breach", 380, 120),
      intro: "A healer from another world. The nobles will regret this.",
      quips: ["The local aristocrats are plotting again. Heal them. Then humiliate them.", "Offworlders stir beyond the breach. They look unfriendly."] },
    magicempire: { name: "The Frontier Barony", base: "wilds", props: () => P("villageWall", 240, 214, "THE BARONY") + P("workshop", 370, 190),
      intro: "Your barony: one village, many monsters. Build something.",
      quips: ["Magic is in its infancy here. You are its very strict teacher.", "The treasury is empty again. The monsters are not."] },
    nothero: { name: "The Hero's Shadow", base: "dungeon", props: () => P("heroStatue", 240, 214),
      intro: "The Hero is over there. You're… also here.",
      quips: ["The spotlight is on someone else. Use the shadows.", "Not the Hero. Just the one who keeps saving him."] },
    omens: { name: "The Elven Academy", base: "sect", props: () => P("trainingPost", 180, 214) + P("trainingPost", 300, 214) + P("well", 240, 214),
      intro: "The elves are unimpressed. Change that.",
      quips: ["You woke up at the bottom of a well. This is an improvement.", "The language of steel is clear. Speak it louder."] },
    lostfleet: { name: "The Dauntless", base: "bridge", props: () => P("captainChair", 240, 210),
      intro: "Captain on the bridge. A hundred years late, but on the bridge.",
      quips: ["The Syndics have ambushed us again. Form up.", "Black Jack would have a plan. You have a sword."] },
    fool: { name: "The University of Generasi", base: "academy", props: () => P("foolCard", 130, 90) + P("ravener", 240, 70),
      intro: "The Mark says no spells. The Mark didn't say no cheating.",
      quips: ["The Mark of the Fool twitches. Exploit it.", "Somewhere, the Ravener stirs. Study faster."],
      boss: { name: "The Ravener", appear: "The Ravener rises, the great enemy the Heroes were Marked to fight. It did not expect the Fool to show up." } },
    mimic: { name: "The Cake Vault", base: "dungeon", props: () => P("mimicChest", 180, 206) + P("cake", 290, 206) + P("cake", 330, 212),
      intro: "Something in this room is hungry. It wants cake. Or you.",
      quips: ["One of those chests is smiling. Don't open that one. Or do.", "Your mimic would like to know if the monster tastes like cake."] },
    noobtown: { name: "Noobtown", base: "wilds", props: () => sign(150, 180, "NEWBIE ZONE", "#FBF8F0", "#4F7D3B") + sign(330, 90, "MAYOR'S OFFICE", "#22305A", "#FBF8F0", 120) + P("plushDemon", 240, 206),
      intro: "Welcome to the starter zone. Population: you and one very small demon.",
      quips: ["The plush demon promises to kill you later. For now it's helping.", "Every class is available. None of them are free."],
      boss: { name: "Charles", appear: "Charles strolls into the starter zone like he owns it. He very much wants to." } },
    berserker: { name: "The Red Moon", base: "ruins", props: () => P("redMoon", 360, 60) + P("dynastyBanner", 120, 200),
      intro: "Qi is optional. Rage is not.",
      quips: ["The Dynasty's bureaucrats would like you to fill out a form. Rip it up.", "Blood, rage and pain. The goddess approves of your progress."] },
    savage: { name: "The Superdungeon", base: "ruins", props: () => P("ruinsStack") + P("carWreck", 140, 220),
      intro: "Dungeons everywhere. You seem… happy about it.",
      quips: ["The more it hurts, the stronger you get. Please stop enjoying this.", "The ruins of lost realms stack forever. So do the monsters."] },
    darkhealer: { name: "The Forgotten Castle", base: "crypt", props: () => P("castleRuin", 240, 160) + P("apothecary", 340, 214),
      intro: "Necromancers are fairy tales now. Fairy tales heal now.",
      quips: ["The world is sick. Strong medicine is on the way.", "Your zombies are very well behaved patients."] },
    hedgewizard: { name: "Bledsbury Dungeon", base: "dungeon", props: () => P("jobBoard", 150, 196) + P("dragonEgg", 330, 214),
      intro: "No chosen ones here. Just a wizard who needs rent money.",
      quips: ["The gods scorn wizards. The landlord scorns late rent more.", "Something small and dragon-shaped is judging your spellcraft."] },
    lotr: { name: "The Deep Halls", base: "halls", props: () => P("balrogGlow") + P("eyeTower", 440, 232),
      intro: "Speak, friend, and enter. Or just fight. Fighting works too.",
      quips: ["Drums in the deep. They are coming.", "One does not simply walk out of this dungeon.", "Far away, a great eye glances your way. Keep moving."] },
    ascension: { name: "The Rift", base: "dungeon", props: () => P("rift", 240, 100) + P("tierTower", 400, 220),
      intro: "Detrimental Talent. Excellent. The underdog discount applies.",
      quips: ["The rifts made the monsters. You'll make the rifts regret it.", "Tier by tier, legends are built. This is tier… one."] },
    multiverse: { name: "The Competition", base: "wilds", props: () => P("shed", 130, 214) + P("scoreboard", 330, 110) + P("countdown", 240, 30),
      intro: "Earth is in fourth place. Please improve.",
      quips: ["The multiverse considers Earth a mining prospect. Object loudly.", "Forerunner duties include this. Sorry."] },
  });

  // ── S-tier favorites from the family's tier lists (2026-09-29) ───────
  Object.assign(PROPS, {
    camDrone: (x, y) => sticker(`<g transform="translate(${x} ${y})"><rect x="-14" y="-8" width="28" height="16" rx="4" fill="#4A5268" ${EDGE}/><circle cx="0" cy="0" r="5" fill="#0E1020"/><circle cx="0" cy="0" r="2" fill="#E8456A"/><path d="M-26 -12 H-8 M8 -12 H26" stroke="#6E7A8C" stroke-width="3"/><circle cx="-17" cy="-14" r="6" fill="none" stroke="#C9CCD4" stroke-width="1.5"/><circle cx="17" cy="-14" r="6" fill="none" stroke="#C9CCD4" stroke-width="1.5"/><circle cx="10" cy="-4" r="2" fill="#E8456A"/></g>`),
    lichShadow: (x, y) => `<g transform="translate(${x} ${y})" opacity=".55"><path d="M-50 60 Q-40 -10 0 -20 Q40 -10 50 60 Z" fill="#141018"/><circle cy="-30" r="20" fill="#141018"/><path d="M-16 -44 L-10 -62 L-4 -48 L0 -66 L4 -48 L10 -62 L16 -44 Z" fill="#141018"/><circle cx="-7" cy="-32" r="3" fill="#8CFF5A"/><circle cx="7" cy="-32" r="3" fill="#8CFF5A"/></g>`,
    monsterParty: (x, y) => sticker(`<g transform="translate(${x} ${y})"><g transform="translate(-24 0)"><circle cy="-40" r="8" fill="#E3DCC8" ${EDGE}/><path d="M0 -32 V-6 M-9 -24 H9 M0 -6 l-7 14 M0 -6 l7 14" stroke="#E3DCC8" stroke-width="4" stroke-linecap="round"/><rect x="6" y="-30" width="4" height="22" fill="#8C857A"/></g>
      <g transform="translate(16 0)"><path d="M-12 8 C-14 -24 14 -24 12 8 Z" fill="#8FB86A" opacity=".85" ${EDGE}/><circle cx="-4" cy="-8" r="2" fill="#2B2621"/><circle cx="4" cy="-8" r="2" fill="#2B2621"/></g></g>`),
    lute: (x, y) => `<g transform="translate(${x} ${y}) rotate(-20)"><ellipse cx="0" cy="12" rx="14" ry="18" fill="#B98A5A"/><circle cx="0" cy="10" r="4" fill="#4A3222"/><rect x="-3" y="-38" width="6" height="36" fill="#6B4A2E"/><rect x="-5" y="-46" width="10" height="10" fill="#4A3222"/></g>`,
    follySword: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-50" y="-20" width="100" height="30" fill="#4A3222"/><path d="M-40 -5 H30 L40 -5 L30 1 H-40 Z" fill="#C9CCD4"/><rect x="-46" y="-9" width="6" height="14" fill="#6B4A2E"/><text x="0" y="18" font-family="serif" font-size="8" fill="#E3A93B" text-anchor="middle">FOLLY</text></g>`,
    blueCandles: (x, y) => `<g transform="translate(${x} ${y})">${[-24, 0, 24].map((a, i) => `<rect x="${a - 4}" y="${-18 + (i % 2) * 6}" width="8" height="${18 - (i % 2) * 6}" fill="#E3DCC8"/><path d="M${a} ${-30 + (i % 2) * 6} c-5 6 -3 10 0 11 c3 -1 5 -5 0 -11" fill="#4F8CFF"/>`).join("")}<circle cy="-20" r="36" fill="#4F8CFF" opacity=".12"/></g>`,
    redHair: (x, y) => `<g transform="translate(${x} ${y})" style="filter:drop-shadow(0 0 2px #FBF8F0)"><path d="M-14 40 L-10 0 H10 L14 40 Z" fill="#2B2621"/><circle cy="-10" r="10" fill="#E8C4A0"/><path d="M-12 -12 Q-12 -26 0 -26 Q14 -26 12 -10 Q8 -18 0 -18 Q-6 -16 -12 -12 Z" fill="#C8403A"/><path d="M10 6 L28 -10" stroke="#B98A5A" stroke-width="4"/></g>`,
    goldenEgg: (x, y) => sticker(`<g transform="translate(${x} ${y})"><ellipse rx="16" ry="21" fill="#E3A93B" ${EDGE}/><ellipse cx="-5" cy="-8" rx="5" ry="7" fill="#F6E3A1"/><circle r="32" fill="#F2D14A" opacity=".2"/></g>`),
    sixers: (x, y) => `<g transform="translate(${x} ${y})"><rect x="-40" y="-24" width="80" height="48" fill="#0E1020" stroke="#6FE0FF" stroke-width="2"/><text x="0" y="-4" font-family="sans-serif" font-size="14" fill="#6FE0FF" text-anchor="middle" font-weight="bold">IOI</text><text x="0" y="14" font-family="sans-serif" font-size="8" fill="#6FE0FF" text-anchor="middle">SIXERS WANTED</text></g>`,
    retroCar: (x, y) => `<g transform="translate(${x} ${y})"><path d="M-50 0 V-14 L-36 -28 H24 L44 -14 H54 V0 Z" fill="#AEB2BC"/><path d="M-30 -26 H20 L34 -14 H-40 Z" fill="#22305A"/><circle cx="-30" cy="2" r="9" fill="#2B2621"/><circle cx="34" cy="2" r="9" fill="#2B2621"/><path d="M-50 -6 H54" stroke="#6FE0FF" stroke-width="2"/><path d="M-60 4 H-80 M-60 -4 H-90" stroke="#E8456A" stroke-width="3" opacity=".7"/></g>`,
  });
  Object.assign(SERIES, {
    manarunners: { name: "The Endless Dungeon", base: "dungeon", props: () => sign(240, 40, "MANA RUNNERS · LIVE", "#E8456A", "#FBF8F0", 150) + P("camDrone", 360, 100) + P("lichShadow", 240, 170) + P("monsterParty", 150, 214),
      intro: "Welcome back to Mana Runners, the world's favorite dungeon show! Tonight: can the level 1 Necrolord survive?",
      quips: ["The sponsors love you. The comments section wants to be undead minions. Both concerning.", "Allergic to magic, possessed by a lich, somehow still here. Ratings are through the roof.", "Copper Runners aren't supposed to know the dungeon's secrets. Oops."],
      boss: { name: "Zavrak the Malevolent", appear: "The dungeon echoes with Zavrak the Malevolent's laughter. History's most infamous overlord would like his powers back." } },
    kingkiller: { name: "The Waystone Inn", base: "tavern", props: () => P("follySword", 240, 60) + P("blueCandles", 330, 214) + P("lute", 150, 200) + P("redHair", 250, 180),
      intro: "A silence of three parts hangs over this dungeon. You are about to break it.",
      quips: ["Somewhere, a red-haired innkeeper is pretending to be ordinary. Badly.", "The candles just burned blue. Nobody say their name.", "Words are pale shadows of forgotten names. Hit harder anyway."],
      boss: { name: "Cinder of the Chandrian", appear: "The flames gutter blue and the wood rots. Cinder of the Chandrian smiles like he has already won." } },
    rpo: { name: "The OASIS", base: "digital", props: () => P("goldenEgg", 240, 80) + P("sixers", 110, 110) + P("retroCar", 330, 214),
      intro: "Welcome to the OASIS. Somewhere in here is a golden egg. And a lot of Sixers.",
      quips: ["Easter egg hunters are everywhere. Stay frosty, gunter.", "The Sixers have a whole department for this. You have you.", "Extra lives are not included in this dungeon."],
      boss: { name: "Nolan Sorrento", appear: "Nolan Sorrento logs in with a legion of Sixers and a very expensive avatar. IOI would like to own this dungeon." } },
  });

  for (const [k, v] of Object.entries(SERIES)) THEMES[k] = { name: v.name, intro: v.intro, quips: v.quips, boss: v.boss, series: true };

  // The Null Regent's throne room (December boss): server racks and a wall of screens.
  STAGES.regent = `<rect width="480" height="290" fill="#0E1226"/>
    <g fill="#161C38">${[0, 1, 2, 3, 4, 5].map((i) => `<rect x="${130 + i * 38}" y="18" width="32" height="24" rx="2"/><rect x="${130 + i * 38}" y="48" width="32" height="24" rx="2"/>`).join("")}</g>
    <g fill="#6FE0FF" opacity=".5">${[0, 1, 2, 3, 4, 5].map((i) => `<rect x="${134 + i * 38}" y="${24 + (i % 2) * 30}" width="${12 + (i * 7) % 14}" height="3"/><rect x="${134 + i * 38}" y="${31 + (i % 2) * 30}" width="${18 - (i * 5) % 9}" height="3"/>`).join("")}</g>
    <rect x="130" y="48" width="32" height="24" rx="2" fill="#D6503E" opacity=".55"/>
    ${[[14, 70], [62, 90], [396, 90], [436, 70]].map(([x, y]) => `<rect x="${x}" y="${y}" width="36" height="${250 - y}" fill="#1B2140" stroke="#05070F" stroke-width="3"/>
      ${[0, 1, 2, 3, 4, 5, 6].filter((j) => y + 12 + j * 24 < 236).map((j) => `<rect x="${x + 5}" y="${y + 10 + j * 24}" width="26" height="14" fill="#10152C"/><circle cx="${x + 11}" cy="${y + 17 + j * 24}" r="2" fill="${(j + x) % 3 ? "#6FE0FF" : "#E3A93B"}"/>`).join("")}`).join("")}
    <rect x="0" y="240" width="480" height="50" fill="#171C33"/>
    <path d="M0 240 H480" stroke="#6FE0FF" stroke-width="2" opacity=".6"/>
    <g stroke="#6FE0FF" stroke-width="1.5" opacity=".25">${[60, 140, 220, 300, 380, 460].map((x) => `<path d="M240 240 L${x - 240 + x} 290"/>`).join("")}</g>`;
  THEMES.regent = { name: "The Admin Console", intro: "", quips: [] };

  function stage(theme) {
    const sr = SERIES[theme];
    const base = sr ? STAGES[sr.base] : STAGES[theme];
    return `<svg class="dg-bg" viewBox="0 0 480 290" preserveAspectRatio="xMidYMid slice" aria-hidden="true">${base || STAGES.dungeon}${sr ? sr.props() : ""}</svg>`;
  }
  window.DungeonThemes = { stage, THEMES, SERIES };
})();
