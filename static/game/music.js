/* The Listening Dungeon — music and sound effects, made by the browser.
 *
 *   Music.play(mode, seed, theme)  mode: hub | explore | battle | boss | regent
 *   Music.sting(kind)              win | fall | level | chest
 *   Music.sfx(kind)                hit | crit | hurt | heal | guard | door | cascade | purge | poison | coin
 *   Music.stop()
 *
 * Nothing is recorded: every tune is composed on the spot with the Web Audio
 * API. The `seed` (the book's title) picks the melody, chords and key, so a
 * book always has its own theme; the `theme` (the dungeon look) picks the
 * mood: scale, speed and instruments. Each loop changes a few notes.
 * The Null Regent has a fixed theme of his own.
 *
 * Both music and sound effects start OFF (players often have an audiobook
 * playing) and each player's choice is remembered on their device.
 */
(function () {
  const KEY = "ld-audio";
  let prefs = { music: false, sfx: false };
  try { prefs = { ...prefs, ...JSON.parse(localStorage.getItem(KEY) || "{}") }; } catch { /* private mode: defaults */ }
  const savePrefs = () => { try { localStorage.setItem(KEY, JSON.stringify(prefs)); } catch { /* ignore */ } };

  let ctx = null, master, musicBus, sfxBus, delay, noise;
  function audio() {
    if (ctx) return ctx;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    ctx = new AC();
    const comp = ctx.createDynamicsCompressor();
    comp.connect(ctx.destination);
    master = ctx.createGain(); master.gain.value = 0.9; master.connect(comp);
    musicBus = ctx.createGain(); musicBus.gain.value = 0; musicBus.connect(master);
    sfxBus = ctx.createGain(); sfxBus.gain.value = 0.55; sfxBus.connect(master);
    // a little echo on the lead line
    delay = ctx.createDelay(1); delay.delayTime.value = 0.28;
    const fb = ctx.createGain(); fb.gain.value = 0.25;
    const wet = ctx.createGain(); wet.gain.value = 0.22;
    delay.connect(fb); fb.connect(delay); delay.connect(wet); wet.connect(musicBus);
    noise = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
    const d = noise.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    document.addEventListener("visibilitychange", () => { if (!ctx) return; document.hidden ? ctx.suspend() : wantSound() && ctx.resume(); });
    return ctx;
  }
  const wantSound = () => prefs.music || prefs.sfx;

  // iPhones treat Web Audio like a ringtone: silent when the ring/silent
  // switch is on, and only allowed after a tap. Playing a silent <audio>
  // loop (and, on newer iOS, asking for a "playback" audio session) makes the
  // phone treat the game like music instead. Called from every tap.
  let keepAlive = null;
  function silentWav() {
    const rate = 8000, n = rate / 2, buf = new ArrayBuffer(44 + n * 2), v = new DataView(buf);
    const w = (o, str) => [...str].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
    w(0, "RIFF"); v.setUint32(4, 36 + n * 2, true); w(8, "WAVE"); w(12, "fmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true);
    v.setUint16(22, 1, true); v.setUint32(24, rate, true); v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
    w(36, "data"); v.setUint32(40, n * 2, true);
    return URL.createObjectURL(new Blob([buf], { type: "audio/wav" }));
  }
  function unlock() {
    if (!wantSound() || !audio()) return;
    try { if (navigator.audioSession) navigator.audioSession.type = "playback"; } catch { /* older browsers */ }
    if (!keepAlive) {
      keepAlive = document.createElement("audio");
      keepAlive.src = silentWav(); keepAlive.loop = true; keepAlive.setAttribute("playsinline", "");
    }
    keepAlive.play().catch(() => {});
    if (ctx.state !== "running") ctx.resume().catch(() => {});
    const b = ctx.createBufferSource();  // a one-sample blip: the classic iOS unlock
    b.buffer = ctx.createBuffer(1, 1, 22050); b.connect(ctx.destination); b.start(0);
  }

  // ── seeded randomness: the same book always composes the same tune ─────
  function hash(str) { let h = 2166136261; for (const ch of String(str)) { h ^= ch.charCodeAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }
  function rng(seed) { let a = hash(seed); return () => { a |= 0; a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  const pickR = (r, xs) => xs[Math.floor(r() * xs.length)];

  // ── moods, by dungeon look ────────────────────────────────────────────
  const MODES = {
    major: [0, 2, 4, 5, 7, 9, 11], dorian: [0, 2, 3, 5, 7, 9, 10], aeolian: [0, 2, 3, 5, 7, 8, 10], phrygian: [0, 1, 3, 5, 7, 8, 10],
    harmonic: [0, 2, 3, 5, 7, 8, 11], lydian: [0, 2, 4, 6, 7, 9, 11], mixolydian: [0, 2, 4, 5, 7, 9, 10], phrygianDom: [0, 1, 4, 5, 7, 8, 10],
  };
  // mode, tempo, lead / bass waves, pentatonic melody, pad, swing, drums (0 none, 1 light, 2 full)
  const MOODS = {
    dungeon: { mode: "dorian", tempo: 100, lead: "square", bass: "triangle", drums: 1 },
    crypt: { mode: "harmonic", tempo: 80, lead: "triangle", bass: "sine", pad: true, drums: 0 },
    void: { mode: "phrygian", tempo: 76, lead: "sine", bass: "sine", pad: true, drums: 0 },
    halls: { mode: "aeolian", tempo: 84, lead: "triangle", bass: "triangle", pad: true, drums: 1 },
    digital: { mode: "aeolian", tempo: 128, lead: "square", bass: "square", pent: true, drums: 2, arp: true },
    backrooms: { mode: "lydian", tempo: 90, lead: "sine", bass: "sine", pad: true, drums: 0 },
    sect: { mode: "major", tempo: 96, lead: "triangle", bass: "triangle", pent: true, drums: 1 },
    ruins: { mode: "aeolian", tempo: 92, lead: "sawtooth", bass: "triangle", drums: 1 },
    station: { mode: "aeolian", tempo: 108, lead: "sawtooth", bass: "square", pad: true, drums: 1 },
    bridge: { mode: "lydian", tempo: 104, lead: "triangle", bass: "square", pad: true, drums: 1 },
    city: { mode: "dorian", tempo: 104, lead: "square", bass: "triangle", swing: 0.18, drums: 2 },
    academy: { mode: "harmonic", tempo: 100, lead: "triangle", bass: "triangle", drums: 1 },
    tower: { mode: "harmonic", tempo: 92, lead: "triangle", bass: "sine", pad: true, drums: 1 },
    wilds: { mode: "mixolydian", tempo: 112, lead: "triangle", bass: "triangle", pent: true, drums: 1 },
    forest: { mode: "dorian", tempo: 96, lead: "triangle", bass: "triangle", pent: true, drums: 1 },
    camp: { mode: "major", tempo: 108, lead: "triangle", bass: "triangle", swing: 0.15, drums: 1 },
    farm: { mode: "major", tempo: 116, lead: "square", bass: "triangle", swing: 0.2, drums: 1 },
    oasis: { mode: "phrygianDom", tempo: 96, lead: "sawtooth", bass: "triangle", drums: 1 },
    tavern: { mode: "mixolydian", tempo: 124, lead: "square", bass: "triangle", swing: 0.22, drums: 2 },
    hub: { mode: "major", tempo: 84, lead: "triangle", bass: "sine", pent: true, pad: true, drums: 0 },
    regent: { mode: "phrygian", tempo: 136, lead: "square", bass: "sawtooth", drums: 2, arp: true },
  };
  const PROGRESSIONS = [[0, 5, 3, 4], [0, 3, 4, 0], [0, 6, 5, 6], [0, 4, 5, 3], [0, 2, 3, 4], [0, 5, 1, 4], [0, 3, 0, 4], [0, 5, 6, 4]];
  function moodFor(theme) {
    const S = window.DungeonThemes && DungeonThemes.SERIES;
    const base = S && S[theme] ? S[theme].base : theme;
    return MOODS[base] || MOODS.dungeon;
  }

  // ── composing ─────────────────────────────────────────────────────────
  function compose(seed, mood) {
    const r = rng(seed);
    const scale = MODES[mood.mode];
    const root = 40 + Math.floor(r() * 8);          // E2..B2 for the bass
    const pent = mood.pent ? (scale[2] === 4 ? [0, 1, 2, 4, 5] : [0, 2, 3, 4, 6]) : null;  // scale steps allowed in the melody
    const melodyBar = (deg, prevIn) => {
      const chord = [deg, deg + 2, deg + 4];
      let prev = prevIn, notes = [];
      for (let s = 0; s < 8; s++) {
        let n;
        if (s === 0 || s === 4) n = 7 + pickR(r, chord) + (r() < 0.3 ? 7 : 0);
        else if (r() < 0.2) { notes.push(null); continue; }
        else if (r() < 0.15 && notes.length && notes[notes.length - 1] !== null) { notes.push("hold"); continue; }
        else n = prev + pickR(r, [-2, -1, -1, 1, 1, 2]);
        n = Math.max(5, Math.min(18, n));
        if (pent && !pent.includes(((n % 7) + 7) % 7)) n += 1;
        notes.push(n); prev = n;
      }
      return { notes, last: prev };
    };
    const progA = pickR(r, PROGRESSIONS), progB = pickR(r, PROGRESSIONS);
    const bars = [];
    let prev = 9;
    for (const deg of [...progA, ...progB]) { const m = melodyBar(deg, prev); prev = m.last; bars.push({ deg, notes: m.notes }); }
    // A A' B A: the second A differs a little
    const song = [...bars.slice(0, 4), ...bars.slice(0, 4).map((b) => ({ ...b, notes: vary(b.notes, r, 0.25) })), ...bars.slice(4), ...bars.slice(0, 4)];
    return { scale, root, bars: song, r };
  }
  function vary(notes, r, amount) {
    return notes.map((n) => (typeof n === "number" && r() < amount ? Math.max(5, Math.min(18, n + pickR(r, [-2, -1, 1, 2]))) : n));
  }
  const midi = (scale, root, step) => root + 12 * Math.floor(step / 7) + scale[((step % 7) + 7) % 7];
  const hz = (m) => 440 * Math.pow(2, (m - 69) / 12);

  // ── instruments ───────────────────────────────────────────────────────
  function tone(t, freq, dur, { type = "square", vol = 0.1, attack = 0.01, release = 0.08, bus = musicBus, echo = false, slide = 0 } = {}) {
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = type; o.frequency.setValueAtTime(freq, t);
    if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(20, freq * slide), t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + attack);
    g.gain.setValueAtTime(vol, t + Math.max(attack, dur - release));
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(bus);
    if (echo) g.connect(delay);
    o.start(t); o.stop(t + dur + 0.05);
  }
  function hiss(t, dur, { vol = 0.08, freq = 8000, type = "highpass", bus = musicBus } = {}) {
    const s = ctx.createBufferSource(), f = ctx.createBiquadFilter(), g = ctx.createGain();
    s.buffer = noise; f.type = type; f.frequency.value = freq;
    g.gain.setValueAtTime(vol, t); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    s.connect(f); f.connect(g); g.connect(bus);
    s.start(t); s.stop(t + dur + 0.02);
  }
  const kick = (t, vol = 0.5) => tone(t, 120, 0.22, { type: "sine", vol, attack: 0.002, release: 0.18, slide: 0.35 });
  const snare = (t, vol = 0.14) => { hiss(t, 0.14, { vol, freq: 1800, type: "bandpass" }); tone(t, 190, 0.08, { type: "triangle", vol: vol * 0.6 }); };
  const hat = (t, vol = 0.035) => hiss(t, 0.04, { vol, freq: 7000 });

  // ── the player (a look-ahead scheduler) ───────────────────────────────
  const MODE_FEEL = {
    hub: { tempo: 1, drums: 0, octave: 0 },
    explore: { tempo: 1, drums: null, octave: 0 },
    battle: { tempo: 1.18, drums: 2, octave: 0, drive: true },
    boss: { tempo: 1.1, drums: 3, octave: -12, drive: true },
    regent: { tempo: 1, drums: 3, octave: 0, drive: true },
  };
  let song = null, key = "", step = 0, nextAt = 0, timer = null, loops = 0;
  function schedule() {
    if (!song || !ctx) return;
    while (nextAt < ctx.currentTime + 0.12) { playStep(nextAt); advanceStep(); }
  }
  function advanceStep() {
    const beat = 60 / song.tempo / 2;
    const swing = (step % 2 === 0 ? 1 : -1) * (song.mood.swing || 0) * beat;
    nextAt += beat + swing;
    step++;
    if (step >= song.bars.length * 8) {  // end of the song: it evolves a little each time round
      step = 0; loops++;
      song.bars = song.bars.map((b) => ({ ...b, notes: vary(b.notes, song.r, 0.08) }));
    }
  }
  function playStep(t) {
    const bar = song.bars[Math.floor(step / 8)], s = step % 8, beat = 60 / song.tempo / 2;
    const { scale, root, mood, feel } = song;
    // lead
    const n = bar.notes[s];
    if (typeof n === "number") {
      let len = 1;
      while (bar.notes[s + len] === "hold") len++;
      const note = midi(scale, root + 12 + feel.octave, n);
      tone(t, hz(note), beat * len * 0.95, { type: mood.lead, vol: mood.lead === "sawtooth" || mood.lead === "square" ? 0.045 : 0.08, echo: true });
      if (feel.octave < 0) tone(t, hz(note + 12), beat * len * 0.9, { type: "sawtooth", vol: 0.02 });
    }
    // arpeggio shimmer (digital looks, the Regent)
    if (mood.arp && (feel.drive || s % 2 === 0)) {
      const tones = [0, 2, 4, 7].map((x) => midi(scale, root + 24, bar.deg + x));
      tone(t, hz(tones[s % 4] + (song.name === "regent" && song.r() < 0.12 ? 12 : 0)), beat * 0.5, { type: "square", vol: 0.018 });
    }
    // bass
    const bassNote = midi(scale, root, bar.deg);
    if (feel.drive ? true : s % 4 === 0) tone(t, hz(bassNote + (feel.drive && s % 2 ? 12 : 0)), beat * (feel.drive ? 0.9 : 3.6), { type: mood.bass, vol: 0.12 });
    // pad: the chord, held for the bar
    if (mood.pad && s === 0) for (const x of [0, 2, 4]) tone(t, hz(midi(scale, root + 12, bar.deg + x)), beat * 7.8, { type: "sine", vol: 0.025, attack: 0.4, release: 0.8 });
    // drums
    const drums = feel.drums === null ? mood.drums : Math.max(mood.drums ? 1 : 0, feel.drums);
    if (drums >= 1) { if (s === 0) kick(t); if (s === 4) snare(t, 0.1); if (s % 2 === 0) hat(t); }
    if (drums >= 2) { if (s === 3 || s === 6) kick(t, 0.4); if (s === 4) snare(t); hat(t, 0.025); }
    if (drums >= 3) { if (s === 2 || s === 5) kick(t, 0.45); if (s === 6) snare(t, 0.12); if (s === 0 && step % 32 === 0) hiss(t, 0.8, { vol: 0.06, freq: 5000 }); }
  }

  function play(mode, seed, theme) {
    if (!prefs.music || !audio()) { key = [mode, seed, theme].join("|"); return; }
    const k = [mode, seed, theme].join("|");
    if (k === key && song) return;
    key = k;
    ctx.resume();
    const moodName = mode === "regent" ? "regent" : mode === "hub" ? "hub" : null;
    const mood = moodName ? MOODS[moodName] : moodFor(theme);
    const feel = MODE_FEEL[mode] || MODE_FEEL.explore;
    const bossy = mode === "boss" ? { ...mood, mode: mood.mode === "major" || mood.mode === "lydian" || mood.mode === "mixolydian" ? "aeolian" : mood.mode } : mood;
    const c = compose(mode === "regent" ? "the-null-regent" : mode === "hub" ? "the-waystone-hub" : `${seed}|${mode === "boss" ? "boss" : "book"}`, bossy);
    const next = { ...c, mood: bossy, feel, name: moodName || "book", tempo: bossy.tempo * feel.tempo };
    // fade out, swap, fade in
    const now = ctx.currentTime;
    musicBus.gain.cancelScheduledValues(now);
    musicBus.gain.setValueAtTime(musicBus.gain.value, now);
    musicBus.gain.linearRampToValueAtTime(0, now + 0.25);
    setTimeout(() => {
      song = next; step = 0; loops = 0; nextAt = ctx.currentTime + 0.05;
      musicBus.gain.linearRampToValueAtTime(0.32, ctx.currentTime + 0.6);
      if (!timer) timer = setInterval(schedule, 25);
    }, 260);
  }
  function stop() {
    song = null; key = "";
    if (timer) { clearInterval(timer); timer = null; }
    if (ctx) { musicBus.gain.cancelScheduledValues(ctx.currentTime); musicBus.gain.setValueAtTime(0, ctx.currentTime); }
  }

  // ── jingles and sound effects (tiny, generated) ───────────────────────
  const STINGS = {
    win: [[72, 0], [76, 0.1], [79, 0.2], [84, 0.3]], level: [[67, 0], [72, 0.08], [76, 0.16], [79, 0.24], [84, 0.32], [88, 0.4]],
    fall: [[64, 0], [60, 0.18], [57, 0.36], [52, 0.6]], chest: [[79, 0], [83, 0.06], [86, 0.12], [91, 0.18]],
  };
  function sting(kind) {
    if (!prefs.music && !prefs.sfx) return;
    if (!audio()) return;
    ctx.resume();
    const t = ctx.currentTime + 0.02, notes = STINGS[kind] || [];
    for (const [m, at] of notes) tone(t + at, hz(m), kind === "fall" ? 0.3 : 0.18, { type: kind === "fall" ? "triangle" : "square", vol: 0.07, bus: sfxBus });
  }
  function sfx(kind) {
    if (!prefs.sfx || !audio()) return;
    ctx.resume();
    const t = ctx.currentTime + 0.005;
    switch (kind) {
      case "hit": hiss(t, 0.08, { vol: 0.25, freq: 1200, type: "bandpass", bus: sfxBus }); tone(t, 180, 0.08, { type: "square", vol: 0.06, slide: 0.5, bus: sfxBus }); break;
      case "crit": hiss(t, 0.14, { vol: 0.3, freq: 2200, type: "bandpass", bus: sfxBus }); tone(t, 880, 0.14, { type: "square", vol: 0.06, slide: 1.6, bus: sfxBus }); break;
      case "hurt": hiss(t, 0.12, { vol: 0.25, freq: 500, type: "lowpass", bus: sfxBus }); tone(t, 140, 0.14, { type: "sawtooth", vol: 0.07, slide: 0.6, bus: sfxBus }); break;
      case "heal": tone(t, 523, 0.12, { type: "sine", vol: 0.1, bus: sfxBus }); tone(t + 0.08, 784, 0.18, { type: "sine", vol: 0.1, bus: sfxBus }); break;
      case "guard": tone(t, 300, 0.1, { type: "triangle", vol: 0.12, slide: 1.3, bus: sfxBus }); hiss(t, 0.06, { vol: 0.12, freq: 3000, bus: sfxBus }); break;
      case "door": tone(t, 110, 0.25, { type: "triangle", vol: 0.12, slide: 0.8, bus: sfxBus }); hiss(t, 0.2, { vol: 0.05, freq: 600, type: "lowpass", bus: sfxBus }); break;
      case "cascade": for (let i = 0; i < 4; i++) tone(t + i * 0.05, 400 - i * 70, 0.12, { type: "square", vol: 0.06, bus: sfxBus }); hiss(t, 0.35, { vol: 0.2, freq: 800, type: "lowpass", bus: sfxBus }); break;
      case "purge": tone(t, 900, 0.3, { type: "sawtooth", vol: 0.05, slide: 0.1, bus: sfxBus }); break;
      case "poison": tone(t, 220, 0.2, { type: "sine", vol: 0.08, slide: 0.7, bus: sfxBus }); break;
      case "coin": tone(t, 988, 0.06, { type: "square", vol: 0.05, bus: sfxBus }); tone(t + 0.06, 1319, 0.12, { type: "square", vol: 0.05, bus: sfxBus }); break;
    }
  }

  // ── the switches ──────────────────────────────────────────────────────
  let lastPlay = ["hub", "", "hub"];  // until a screen says otherwise (e.g. the login screen), play the hub theme
  function remember(mode, seed, theme) { lastPlay = [mode, seed, theme]; }
  function set(kind, on) {
    prefs[kind] = !!on; savePrefs();
    if (on) unlock();
    else if (!wantSound() && keepAlive) keepAlive.pause();
    if (kind === "music") {
      if (on) { audio(); key = ""; if (lastPlay) play(...lastPlay); }
      else stop();
    }
    if (kind === "sfx" && on) { audio(); sfx("coin"); }
    render();
  }
  function render() {
    const el = document.getElementById("audio-ctl");
    if (!el) return;
    el.innerHTML = `<button type="button" data-k="music" aria-pressed="${prefs.music}" title="Music">♪ Music ${prefs.music ? "on" : "off"}</button>`
      + `<button type="button" data-k="sfx" aria-pressed="${prefs.sfx}" title="Sound effects">🔊 Sounds ${prefs.sfx ? "on" : "off"}</button>`;
    el.querySelectorAll("button").forEach((b) => { b.onclick = () => set(b.dataset.k, !prefs[b.dataset.k]); });
  }
  // Browsers only allow sound after a tap: start the music on the first one.
  // iOS only counts touchend/click as a tap that may start sound.
  const onTap = () => {
    if (!wantSound()) return;
    unlock();
    if (prefs.music && !song && lastPlay) { key = ""; play(...lastPlay); }
  };
  document.addEventListener("touchend", onTap, { passive: true });
  document.addEventListener("click", onTap);
  document.addEventListener("DOMContentLoaded", render);
  if (document.readyState !== "loading") render();

  window.Music = {
    play: (mode, seed = "", theme = "dungeon") => { remember(mode, seed, theme); play(mode, seed, theme); },
    stop, sting, sfx, set, prefs: () => ({ ...prefs }),
  };
})();
