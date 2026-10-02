/* The Listening Dungeon — front page: login, character builder, class pick, hub.
 * Talks to /api/game (app/game_api.py). Characters are drawn by crawler-art.js. */
(function () {
  const $ = (id) => document.getElementById(id);
  const A = window.CrawlerArt;
  const SLOTS = ["Weapon", "Head", "Chest", "Neck", "Ring", "Trinket"];
  const SCREENS = ["title", "builder", "classpick", "hub", "dungeon", "bag", "bindery", "store", "party", "wardrobe", "arena"];
  // Wardrobe nameplate colors: [background, text]
  const PLATES = { red: ["#D6503E", "#FBF8F0"], mustard: ["#E3A93B", "#2B2621"], navy: ["#22305A", "#FBF8F0"],
    forest: ["#4F7D3B", "#FBF8F0"], royal: ["#8A4FB8", "#FBF8F0"], ink: ["#2B2621", "#FBF8F0"] };
  const nameTag = (name, worn) => {
    const pl = PLATES[(worn || {}).plate];
    return pl ? `<span class="plate" style="background:${pl[0]};color:${pl[1]}">${esc(name.toUpperCase())}</span>` : esc(name.toUpperCase());
  };
  let me = null;
  let sortMode = "new";
  let shelfStatus = "waiting";
  let noticeQueue = [];  // welcome chest, book-finished bonuses: shown once on the hub

  // ── helpers ──────────────────────────────────────────────────────────
  async function api(path, opts = {}) {
    const res = await fetch("/api/game" + path, {
      method: opts.method || "GET",
      headers: opts.body ? { "Content-Type": "application/json" } : {},
      body: opts.body ? JSON.stringify(opts.body) : undefined,
      credentials: "same-origin",
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw Object.assign(new Error(data.detail || "Something went wrong."), { status: res.status });
    return data;
  }
  function show(id) { for (const k of SCREENS) $(k).hidden = k !== id; window.scrollTo(0, 0); }
  let toastTimer;
  function toast(text) {
    const t = $("toast"); t.textContent = text; t.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 3200);
  }
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  // Drop marketing subtitles ("Title: A LitRPG Adventure") for display.
  const shortTitle = (t) => t.replace(/\s*\((un)?abridged\)\s*$/i, "").split(/: (?=an? [a-z]|the [a-z]|a litrpg|book \d)/i)[0];
  const lootBadge = (h) => h >= 20 ? ["2 chests", "two"] : h >= 12 ? ["Rare odds", ""] : h >= 6 ? ["Better odds", ""] : ["1 chest", ""];
  // A dungeon that would catch you up on a 5+ book series trumps the length badge.
  // A book that finishes a series: its chip says what that pays (5+ book series also get a chest).
  const seriesChip = (sr, long) => {
    const what = sr.kind === "finale" ? (long ? "Series finale" : "Finale") : "Caught up";
    const prize = sr.chest ? (sr.kind === "finale" ? "Epic" : "Rare") : `+${sr.bookmarks} ◆`;
    return long ? `${what}: ${sr.chest ? `guaranteed ${prize} + ${sr.bookmarks} bookmarks` : `${sr.bookmarks} bookmarks`}` : `${what} · ${prize}`;
  };
  const bookBadge = (b) => b.series_reward ? [seriesChip(b.series_reward, false), "finale"] : lootBadge(b.hours);

  // ── title screen ─────────────────────────────────────────────────────
  const GENERIC_CREW = [
    [{ ancestry: "dwarf", skin: 1, hair: "bald", hairColor: 3, beard: "braided", face: "grumpy", accent: 1 }, "brawler"],
    [{ ancestry: "human", skin: 2, hair: "short", hairColor: 0, beard: "full", face: "determined", accent: 2 }, "runeblade"],
    [{ ancestry: "darkelf", skin: 0, hair: "long", hairColor: 5, beard: "none", face: "glowing", accent: 3 }, "hexcaster"],
    [{ ancestry: "orc", skin: 0, hair: "mohawk", hairColor: 0, beard: "none", face: "determined", accent: 0 }, "paladin"],
  ];
  function drawRansom() {
    const colors = [["#D6503E", "#FBF8F0"], ["#A8C6D8", "#2B2621"], ["#E3A93B", "#22305A"], ["#F3EBDA", "#2B2621"], ["#22305A", "#FBF8F0"], ["#8FB3A0", "#FBF8F0"], ["#C6A06F", "#2B2621"]];
    const fonts = ["Alfa Slab One", "Abril Fatface", "Rubik Mono One", "Ultra"];
    let n = 0;
    $("ransom").innerHTML = ["THE", "LISTENING", "DUNGEON"].map((w) => `<div class="row">${[...w].map((ch) => {
      const r = Math.sin(++n * 91.7) * 1e4 % 1, c = colors[Math.abs(Math.floor(r * 7)) % 7], f = fonts[n % 4];
      return `<span class="t" style="background:${c[0]};color:${c[1]};font-family:'${f}',serif;font-size:${f === "Rubik Mono One" ? ".8em" : "1em"};transform:rotate(${(r * 12).toFixed(1)}deg);animation-delay:${n * 45}ms">${n % 5 === 3 ? ch.toLowerCase() : ch}</span>`;
    }).join("")}</div>`).join("");
    $("crew").innerHTML = GENERIC_CREW.map(([look, cls]) => `<div class="sticker">${A.render(look, cls, { height: 150 })}</div>`).join("");
  }
  async function showTitle() {
    show("title");
    window.Music && Music.play("hub");
    $("who").innerHTML = `<h2>Who's crawling?</h2><p style="color:var(--card);text-align:center">Loading readers…</p>`;
    try {
      const { players } = await api("/players");
      $("who").innerHTML = `<h2>Who's crawling?</h2><div class="readers">${players.map((p, i) => `
        <button class="reader" data-u="${esc(p.username)}" data-pin="${p.has_pin ? 1 : 0}">
          <div class="sticker">${p.look && p.cls ? A.render(p.look, p.cls, { height: 70 }) : A.render(GENERIC_CREW[i % 4][0], GENERIC_CREW[i % 4][1], { height: 70 })}</div>
          <strong>${esc(p.username.toUpperCase())}</strong>${p.cls && p.level ? `<em class="rlvl">${A.CLASSES[p.cls].name} · Level ${p.level}</em>` : ""}<span><b>${p.dungeons_open}</b> dungeons waiting</span>
        </button>`).join("")}</div>
        <button class="btn alt title-lib" id="title-lib">📚 The Library</button>`;
      $("title-lib").onclick = openTitleLibrary;
      $("who").querySelectorAll(".reader").forEach((b) => b.addEventListener("click", (e) => {
        const now = e.target.closest("[data-now]");
        if (now) return showListening(b.dataset.u, listening[now.dataset.now]);
        showPin(b.dataset.u, b.dataset.pin === "1");
      }));
      // The listening data is slow (a few seconds): add each book when it arrives.
      nowListening().then((got) => {
        listening = got;
        $("who").querySelectorAll(".reader").forEach((b) => {
          const key = b.dataset.u.toLowerCase(), book = listening[key];
          if (book && !b.querySelector(".now")) b.insertAdjacentHTML("beforeend", `<span class="now" role="button" tabindex="0" data-now="${esc(key)}" title="What they're listening to">🎧 ${esc(shortTitle(book.title || ""))}</span>`);
        });
      });
    } catch (e) {
      $("who").innerHTML = `<h2>Who's crawling?</h2><div class="pin"><p>${esc(e.message)}</p><button class="btn" id="retry">Try again</button></div>`;
      $("retry").onclick = showTitle;
    }
  }

  // ── what everyone is listening to (the Stats page's data, on the title screen) ──
  let listening = {};
  async function nowListening() {
    try {
      const d = await fetch("/awards/api/users", { cache: "no-store" }).then((r) => r.json());
      const out = {};
      for (const u of d.users || d || []) if (u && u.username && u.currentlyReading && u.currentlyReading.title) out[u.username.toLowerCase()] = u.currentlyReading;
      return out;
    } catch { return {}; }
  }
  function showListening(name, b) {
    const pct = Math.max(0, Math.min(100, Math.round((Number(b.progress) || 0) * 100)));
    const hm = (sec) => { const m = Math.round((Number(sec) || 0) / 60); return m >= 60 ? `${Math.floor(m / 60)}h ${m % 60}m` : `${m}m`; };
    const left = Math.max(0, (Number(b.duration) || 0) - (Number(b.currentTime) || 0));
    const s = b.lastSession || {};
    const when = s.startedAt ? new Date(s.startedAt).toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "";
    $("nr-title").textContent = `${name.toUpperCase()} is listening to`;
    $("nr-body").innerHTML = `<div class="nowbook"><img src="/awards/api/cover/${encodeURIComponent(b.libraryItemId || "")}" alt="" onerror="this.style.visibility='hidden'">
      <div><h3>${esc(b.title)}</h3>${b.subtitle ? `<div class="by">${esc(b.subtitle)}</div>` : ""}${b.authorText ? `<div class="by">by ${esc(b.authorText)}</div>` : ""}
      <div class="pbar"><i style="width:${pct}%"></i><b>${pct}%</b></div>
      <div class="meta">${hm(left)} left of ${hm(b.duration)}${when ? `<br>Last listened ${esc(when)}${s.timeListening ? ` for ${hm(s.timeListening)}` : ""}` : ""}${s.device ? ` on ${esc(s.device)}` : ""}</div></div></div>`;
    $("nowreading").hidden = false; $("nr-ok").focus();
  }
  $("nr-ok").onclick = () => { $("nowreading").hidden = true; };

  // ── PIN pad: first login asks twice so a typo can't lock someone out ──
  function showPin(user, hasPin) {
    let pin = "", first = null, msg = "", busy = false;
    const prompt = () => hasPin ? "Enter your PIN" : first === null ? "Pick a 4-digit PIN" : "Type it again to confirm";
    const draw = (shake = false) => {
      $("who").innerHTML = `<h2>${esc(user.toUpperCase())}</h2>
        <div class="pin${shake ? " shake" : ""}"><p>${prompt()}</p>
          <div class="dots">${[0, 1, 2, 3].map((i) => `<i class="${i < pin.length ? "on" : ""}"></i>`).join("")}</div>
          <p class="pin-msg">${esc(msg)}</p>
          <div class="keys">${[1, 2, 3, 4, 5, 6, 7, 8, 9, "←", 0, "OK"].map((k) => `<button class="key" data-k="${k}" aria-label="${k === "←" ? "Delete" : k === "OK" ? "Enter" : k}">${k}</button>`).join("")}</div>
          <button class="btn" style="background:transparent;color:var(--muted);box-shadow:none;font-family:var(--hand);font-size:17px;min-height:40px" id="notme">Not you? Go back</button></div>`;
      $("who").querySelectorAll(".key").forEach((b) => b.addEventListener("click", () => press(b.dataset.k)));
      $("notme").onclick = showTitle;
    };
    const press = (k) => {
      if (busy) return;
      if (k === "←") pin = pin.slice(0, -1);
      else if (k !== "OK" && pin.length < 4) pin += k;
      msg = "";
      draw();
      if (pin.length === 4) submit();
    };
    const submit = async () => {
      if (!hasPin && first === null) { first = pin; pin = ""; return draw(); }
      if (!hasPin && pin !== first) { first = null; pin = ""; msg = "Those didn't match. Pick one again."; return draw(true); }
      busy = true;
      try {
        const res = await api("/login", { method: "POST", body: { username: user, pin } });
        me = res.me; noticeQueue.push(...(me.notices || []));
        if (res.first_time) toast("PIN set. Welcome to the dungeon.");
        route();
      } catch (e) {
        pin = ""; msg = e.message; busy = false; draw(true);
      }
    };
    document.onkeydown = (e) => {
      if ($("title").hidden || !$("who").querySelector(".keys")) return;
      if (/^\d$/.test(e.key)) press(e.key);
      else if (e.key === "Backspace") press("←");
    };
    draw();
  }

  // ── builder ──────────────────────────────────────────────────────────
  let draft = null;
  function openBuilder() {
    draft = { ...(me.look || A.DEFAULT_LOOK) };
    $("b-name").textContent = me.username.toUpperCase();
    // Editing an existing crawler: Cancel goes back untouched; Save costs the look-change fee.
    const editing = !!(me.look && me.cls);
    $("b-cancel").hidden = !editing;
    $("b-next").textContent = editing ? `Save look${me.look_change_cost ? ` (${me.look_change_cost} bookmarks)` : ""}` : me.cls ? "Save look" : "Next: pick a class";
    show("builder"); drawBuilder();
  }
  $("b-cancel").onclick = () => route();
  function drawBuilder() {
    const L = draft, anc = A.ANCESTRIES[L.ancestry];
    if (L.skin >= anc.skins.length) L.skin = 0;
    if (anc.noBeard) L.beard = "none";
    $("b-fig").innerHTML = A.render(L, me.cls || "brawler", { height: 250 });
    const locked = (key, k) => key === "beard" && anc.noBeard && k !== "none";
    const chips = (key, map) => Object.entries(map).map(([k, v]) => `<button class="choice" data-k="${key}" data-v="${k}" aria-pressed="${L[key] === k}" ${locked(key, k) ? "disabled" : ""}>${typeof v === "string" ? v : v.name}</button>`).join("");
    const swatches = (key, list, label) => list.map((c, i) => `<button class="swatch" style="background:${c}" data-k="${key}" data-v="${i}" data-num="1" aria-pressed="${L[key] === i}" aria-label="${label} ${i + 1}"></button>`).join("");
    const note = (t) => `<span style="font-family:var(--hand);font-size:15px;color:var(--muted)">${t}</span>`;
    $("b-opts").innerHTML = `
      <div class="opt"><h3>Ancestry</h3><div class="choices">${chips("ancestry", A.ANCESTRIES)}</div></div>
      <div class="opt"><h3>Skin</h3><div class="choices">${swatches("skin", anc.skins, "Skin tone")}</div></div>
      <div class="opt"><h3>Hair</h3><div class="choices">${chips("hair", A.HAIR_STYLES)}</div><div class="choices" style="margin-top:8px">${swatches("hairColor", A.HAIR_COLORS, "Hair color")}</div></div>
      <div class="opt"><h3>Beard ${anc.noBeard ? note("(elves can't grow beards)") : ""}</h3><div class="choices">${chips("beard", A.BEARDS)}</div></div>
      <div class="opt"><h3>Face</h3><div class="choices">${chips("face", A.FACES)}</div></div>
      <div class="opt"><h3>Accent color ${note("(cape, trim, sash)")}</h3><div class="choices">${swatches("accent", A.ACCENTS, "Accent")}</div></div>`;
    $("b-opts").querySelectorAll("[data-k]").forEach((b) => b.addEventListener("click", () => {
      L[b.dataset.k] = b.dataset.num ? Number(b.dataset.v) : b.dataset.v;
      if (b.dataset.k === "ancestry") { L.skin = 0; if (b.dataset.v === "darkelf" && L.hairColor < 5) L.hairColor = 5; }
      drawBuilder();
    }));
    $("b-next").textContent = !me.look ? "Next: pick a class" : me.look_change_cost ? `Save look (${me.look_change_cost} bookmarks)` : "Save look";
  }
  $("b-rand").onclick = () => { draft = A.randomLook(); drawBuilder(); };
  $("b-next").onclick = async () => {
    try {
      const res = await api("/me/look", { method: "PUT", body: { look: draft } });
      me = { ...me, ...res.me };
      route(); badgesNow();
    } catch (e) { toast(e.message); }
  };

  // ── class pick ───────────────────────────────────────────────────────
  const CLASS_TEXT = {
    brawler: "Hits hard, takes a beating. Highest health.",
    runeblade: "Builds energy fast, then Overcharges for a 4× hit.",
    hexcaster: "Stacks curses that burn every turn.",
    ranger: "Free opening shot every fight. Frequent crits.",
    paladin: "Guarding heals. Smite hits and heals.",
    beastmaster: "Summons a random wolf, hawk or bear to fight beside you.",
    necromancer: "Raises skeletons, ghouls and wraiths. Shields and heals them.",
  };
  let chosen = null;
  function openClassPick() {
    chosen = me.cls; show("classpick");
    $("c-back").textContent = me.cls ? "Cancel" : "Back to your look";
    $("c-grid").innerHTML = Object.entries(A.CLASSES).map(([k, c]) => `<button class="clscard sticker" data-c="${k}" aria-pressed="${k === chosen}">
        ${A.render(me.look, k, { height: 120 })}
        <div><span class="role">${c.role}</span>${k === "beastmaster" || k === "necromancer" ? '<span class="new">pets</span>' : ""}<h3>${c.name}</h3><p>${CLASS_TEXT[k]}</p></div></button>`).join("");
    $("c-grid").querySelectorAll(".clscard").forEach((b) => b.addEventListener("click", () => {
      chosen = b.dataset.c;
      $("c-grid").querySelectorAll(".clscard").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      setGo();
    }));
    $("c-back").textContent = me.cls ? "Back to the hub" : "Back to your look";
    setGo();
  }
  function setGo() {
    const cost = me.cls && chosen !== me.cls ? me.class_change_cost : 0;
    $("c-go").disabled = !chosen;
    $("c-go").textContent = !chosen ? "Pick a class" : chosen === me.cls ? `Keep ${A.CLASSES[chosen].name}` : `Play as ${A.CLASSES[chosen].name}${cost ? ` (${cost} bookmarks)` : ""}`;
  }
  $("c-back").onclick = () => (me.cls ? route() : openBuilder());
  $("c-go").onclick = async () => {
    if (!chosen) return;
    try {
      if (chosen !== me.cls) {
        // A dungeon in progress was started as the old class: it restarts (no penalty).
        const r = me.active_run;
        if (r && !confirmTap("class-restart", `Changing class restarts ${shortTitle(r.title)} from floor 1 (no penalty). Tap again to change.`)) return;
        const res = await api("/me/class", { method: "PUT", body: { cls: chosen, restart_run: !!r } });
        me = { ...me, ...res.me };
        if (r) toast(`${shortTitle(r.title)} will start fresh as a ${A.CLASSES[chosen].name}.`);
      }
      route(); badgesNow();
    } catch (e) { toast(e.message); }
  };

  // ── hub ──────────────────────────────────────────────────────────────
  // Tier List reminder under the character (game_store.settle_tier_rewards).
  function renderTierChip() {
    const t = me.tier;
    const n = t ? t.to_rank.length : 0;
    $("tier-chip").innerHTML = n ? `<a href="/tier?mine=1">🏆 <b>${n} series to rank</b><br>${t.fresh ? "+5 bookmarks for each new series you rank." : "Rank your finished series for bookmarks."}</a>` : "";
  }
  function renderCharacter() {
    renderTierChip();
    $("char-art").innerHTML = A.render(me.look, me.cls, { height: 150 });
    $("char-name").innerHTML = nameTag(me.username, me.worn) + (me.title ? `<div class="ctitle">${esc(me.title)}</div>` : "");
    $("char-cls").textContent = `${A.CLASSES[me.cls].name} · Level ${me.level}`;
    $("char-xpbar").style.width = `${Math.min(100, (100 * me.xp) / me.xp_next)}%`;
    $("char-xp").textContent = `${me.xp} / ${me.xp_next} XP to level ${me.level + 1}`;
    $("char-stats").innerHTML = [["Health", me.stats.hp], ["Attack", me.stats.atk], ["Defense", me.stats.def]]
      .map(([k, v]) => `<div><strong>${v}</strong>${k}</div>`).join("");
    $("char-bm").textContent = me.bookmarks;
    $("char-bm").setAttribute("aria-label", `${me.bookmarks} bookmarks`);
    $("open-bag").textContent = me.pending_loot ? "Bag · loot!" : `Bag ${me.bag_count}/${me.bag_capacity}`;
    const clears = me.dungeons.cleared, unlockAt = me.store_unlock_at || 10;
    $("open-store").textContent = clears >= unlockAt ? "Store" : `Store ${clears}/${unlockAt}`;
    $("char-gear").innerHTML = SLOTS.map((slot) => {
      const it = me.gear[slot];
      return it ? `<div class="gslot" style="border-color:var(--r-${it.rarity.toLowerCase()})" title="${esc(it.rarity + " " + slot + ": " + it.name)}"><img src="${esc(it.icon)}" alt="${esc(it.name)}"></div>`
        : `<div class="gslot">${slot}</div>`;
    }).join("");
  }
  async function renderShelf() {
    $("next").innerHTML = `<p class="empty">Checking your finished books…</p>`; $("shelf").innerHTML = "";
    try {
      const { counts, dungeons } = await api(`/me/dungeons?status=${shelfStatus}&sort=${sortMode}&limit=40`);
      $("n-waiting").textContent = counts.waiting; $("n-fallen").textContent = counts.fallen; $("n-cleared").textContent = counts.cleared;
      if (!dungeons.length) {
        $("next").innerHTML = `<p class="empty">${{
          waiting: "No dungeons waiting. Finish a book in Audiobookshelf and one appears here within a few minutes.",
          fallen: "Nothing on the Fallen shelf. Keep it that way.",
          cleared: "No cleared dungeons yet. Go crawl one.",
        }[shelfStatus]}</p>`;
        return;
      }
      if (shelfStatus === "waiting" && me.active_run) {
        const r = me.active_run;
        $("next").innerHTML = `<img src="/awards/api/cover/${encodeURIComponent(r.item_id)}" alt="">
          <div><span class="stamp" style="font-size:14px;background:var(--navy)">In progress</span><h3 style="margin-top:6px">${esc(shortTitle(r.title))}</h3>
            <div class="meta">You left off on floor ${Math.min(r.floor, 3)}.</div>
            <div class="split-actions"><button class="btn" id="resume">Resume</button><button class="btn ghost" id="giveup">Give up</button></div></div>`;
        $("resume").onclick = resumeDungeon;
        $("giveup").onclick = giveUp;
        $("shelf").innerHTML = dungeons.filter((b) => b.item_id !== r.item_id).map((b, i) => bookTile(b, bookBadge(b), i)).join("");
        $("shelf").querySelectorAll(".book").forEach((el) => el.addEventListener("click", () => toast(`Finish or give up ${shortTitle(r.title)} first.`)));
      } else if (shelfStatus === "waiting") {
        const [first, ...rest] = dungeons;
        const [lb, cls] = lootBadge(first.hours);
        const sr = first.series_reward;
        $("next").innerHTML = `<img src="/awards/api/cover/${encodeURIComponent(first.item_id)}" alt="">
          <div><span class="stamp" style="font-size:14px">Next dungeon</span><h3 style="margin-top:6px">${esc(shortTitle(first.title))}</h3>
            <div class="meta">${esc(first.series || "Standalone")} · ${first.hours.toFixed(1)} hr book</div>
            <div class="chips" style="margin-bottom:12px">${sr ? `<span class="chip finale">${seriesChip(sr, true)}</span>` : ""}<span class="chip ${cls ? "big" : "loot"}">${lb}</span><span class="chip">${esc((DungeonThemes.THEMES[first.theme] || DungeonThemes.THEMES.dungeon).name)}</span></div>
            <button class="btn" id="enter">Enter dungeon</button></div>`;
        $("enter").onclick = () => enterDungeon(first);
        $("shelf").innerHTML = rest.map((b, i) => bookTile(b, bookBadge(b), i)).join("");
        $("shelf").querySelectorAll(".book").forEach((el) => el.addEventListener("click", () => enterDungeon(rest[el.dataset.i])));
      } else {
        $("next").innerHTML = shelfStatus === "fallen"
          ? `<p class="empty">Books you fell in. Revive one to try it again.</p>` : `<p class="empty">Dungeons you've conquered.</p>`;
        $("shelf").innerHTML = dungeons.map((b, i) => bookTile(b, shelfStatus === "fallen" ? [`Revive ${b.revive_cost}`, "two"] : ["Cleared", ""], i)).join("");
        if (shelfStatus === "fallen") $("shelf").querySelectorAll(".book").forEach((el) => el.addEventListener("click", () => revive(dungeons[el.dataset.i])));
      }
    } catch (e) {
      $("next").innerHTML = `<p class="empty">${esc(e.message)}</p>`;
    }
  }
  const bookTile = (b, [t, c], i) => `<button class="book" data-i="${i}"><div class="cv"><img loading="lazy" src="/awards/api/cover/${encodeURIComponent(b.item_id)}" alt="" ${shelfStatus === "fallen" ? 'style="filter:grayscale(1)"' : ""}><span class="badge ${c}">${t}</span></div>
      <span class="t">${esc(shortTitle(b.title))}</span><span class="h">${b.hours.toFixed(1)} hrs</span></button>`;
  document.querySelectorAll("#shelf-tabs button").forEach((b) => b.addEventListener("click", () => {
    shelfStatus = b.dataset.status;
    document.querySelectorAll("#shelf-tabs button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    renderShelf();
  }));
  async function revive(book) {
    if (!confirmTap(`revive-${book.item_id}`, `Tap again to revive ${shortTitle(book.title)} for ${book.revive_cost} bookmarks.`)) return;
    try {
      const res = await api(`/me/dungeons/${encodeURIComponent(book.item_id)}/revive`, { method: "POST" });
      me = { ...me, ...res.me };
      toast(`${shortTitle(book.title)} is back on your shelf.`);
      renderCharacter(); renderShelf(); badgesNow();
    } catch (e) { toast(e.message); }
  }
  // Two taps confirm anything that costs bookmarks or destroys an item.
  let armed = null, armedTimer;
  function confirmTap(key, message) {
    if (armed === key) { armed = null; return true; }
    armed = key; toast(message);
    clearTimeout(armedTimer); armedTimer = setTimeout(() => { armed = null; }, 4000);
    return false;
  }

  // ── dungeon runs ─────────────────────────────────────────────────────
  function playRun(run) {
    show("dungeon");
    Dungeon.start({ ...run, username: me.username.toUpperCase(), xp: me.xp, xp_next: me.xp_next }, {
      onFinish: async (report) => {
        const res = await api(`/runs/${run.run_id}/finish`, { method: "POST", body: report });
        me = { ...me, ...res.me };
        return res.result;
      },
      onDone: async (result, pending) => { await pullNotices(); pending ? openBag() : showHub(); },
      onSave: (progress) => api(`/runs/${run.run_id}/progress`, { method: "PUT", body: { progress } }).catch(() => {}),
      onLeave: async () => { await pullNotices(); showHub(); },
    });
  }
  // Fresh character + any unseen notices (badges, book bonuses).
  async function pullNotices() {
    try { me = await api("/me"); noticeQueue.push(...(me.notices || [])); } catch { /* keep what we have */ }
  }
  // After spending bookmarks: show a badge it earned (Big Spender, It's Orange!…)
  // right away, instead of waiting for the next dungeon to finish (bug, 2026-10-02).
  async function badgesNow() { await pullNotices(); showNotices(); }

  // ── practice: a random dungeon that pays nothing ─────────────────────
  let practice = { difficulty: "normal", tier: null, opts: null };
  async function renderPractice() {
    try {
      if (!practice.opts) { practice.opts = await api("/practice"); practice.tier = practice.opts.your_tier; }
    } catch { return; }
    const o = practice.opts;
    const chips = (list, key, cur, label) => list.map((x) => `<button class="choice" data-${key}="${x[key === "diff" ? "key" : "tier"]}" aria-pressed="${String(x[key === "diff" ? "key" : "tier"]) === String(cur)}">${esc(x[label])}</button>`).join("");
    $("pr-diff").innerHTML = chips(o.difficulties, "diff", practice.difficulty, "name");
    $("pr-theme").innerHTML = chips(o.themes, "tier", practice.tier, "name");
    $("pr-diff").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => { practice.difficulty = b.dataset.diff; renderPractice(); }));
    $("pr-theme").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => { practice.tier = Number(b.dataset.tier); renderPractice(); }));
  }
  async function startPractice() {
    try {
      const cfg = await api("/practice", { method: "POST", body: { difficulty: practice.difficulty, tier: practice.tier } });
      show("dungeon");
      Dungeon.start({ ...cfg, username: me.username.toUpperCase(), xp: me.xp, xp_next: me.xp_next }, {
        onFinish: async () => ({ xp: 0, bookmarks: 0, loot: [], level: me.level, levels_gained: 0 }),
        onDone: () => showHub(),
        onAgain: startPractice,
        onLeave: () => showHub(),
      });
    } catch (e) { toast(e.message); }
  }
  $("pr-go").onclick = startPractice;

  // ── monster ideas for the Workshop ───────────────────────────────────
  const IDEA_STATUS = { new: "waiting", building: "being built", live: "in the dungeon!", dismissed: "passed on" };
  async function openSuggest() {
    $("suggest").hidden = false; $("sg-msg").textContent = "";
    if (practice.opts && $("sg-tier").options.length < 2) $("sg-tier").insertAdjacentHTML("beforeend", practice.opts.themes.map((t) => `<option value="${t.tier}">${esc(t.name)}</option>`).join(""));
    $("sg-name").focus();
    try {
      const { suggestions } = await api("/suggestions/mine");
      $("sg-mine").innerHTML = suggestions.length ? `<p class="sg-mine">Your ideas: ${suggestions.slice(0, 5).map((x) => `<b>${esc(x.name)}</b> (${IDEA_STATUS[x.status] || x.status})`).join(", ")}</p>` : "";
    } catch { $("sg-mine").innerHTML = ""; }
  }
  $("sg-cancel").onclick = () => { $("suggest").hidden = true; };
  $("sg-send").onclick = async () => {
    try {
      await api("/suggestions", { method: "POST", body: { name: $("sg-name").value, idea: $("sg-idea").value, tier: Number($("sg-tier").value) } });
      $("sg-name").value = ""; $("sg-idea").value = "";
      $("suggest").hidden = true; toast("Idea sent to the Monster Workshop.");
    } catch (e) { $("sg-msg").textContent = e.message; }
  };
  async function enterDungeon(book) {
    if (me.pending_loot) { toast("You have loot waiting. Sort your bag first."); return openBag(); }
    try {
      const run = await api("/runs", { method: "POST", body: { item_id: book.item_id } });
      me.active_run = { run_id: run.run_id, item_id: run.item_id, title: run.title, floor: 1 };
      playRun(run);
    } catch (e) { toast(e.message); }
  }
  async function resumeDungeon() {
    try { playRun(await api("/runs/active")); } catch (e) { toast(e.message); me.active_run = null; renderShelf(); }
  }
  async function giveUp() {
    const r = me.active_run;
    if (!confirmTap("giveup", `Tap Give up again. ${shortTitle(r.title)} goes to your Fallen shelf.`)) return;
    try {
      const res = await api(`/runs/${r.run_id}/abandon`, { method: "POST" });
      me = { ...me, ...res.me };
      toast(`${shortTitle(r.title)} went to your Fallen shelf.`);
      renderCharacter(); renderShelf();
    } catch (e) { toast(e.message); }
  }

  document.querySelectorAll(".sort button").forEach((b) => b.addEventListener("click", () => {
    sortMode = b.dataset.sort;
    document.querySelectorAll(".sort button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    renderShelf();
  }));
  async function renderFeed() {
    try {
      const { feed } = await api("/feed?limit=10");
      $("feed").innerHTML = feed.length ? feed.map((f) => `<li><span class="av sticker">${f.look && f.cls ? A.render(f.look, f.cls, { height: 44 }) : ""}</span><span class="txt"><b>${esc(f.username.toUpperCase())}</b> ${esc(f.payload.text || f.kind)}</span><span class="when">${new Date(f.created_at * 1000).toLocaleDateString()}</span></li>`).join("")
        : `<li class="empty">Nothing yet. Clears, loot and level-ups from the whole party show up here.</li>`;
    } catch { $("feed").innerHTML = ""; }
  }
  const ICON = {
    party: '<svg viewBox="0 0 40 40"><circle cx="13" cy="14" r="6" fill="#D6503E"/><circle cx="27" cy="14" r="6" fill="#22305A"/><path d="M3 34c0-8 5-12 10-12s10 4 10 12zM17 34c0-8 5-12 10-12s10 4 10 12z" fill="#E3A93B"/></svg>',
    chronicle: '<svg viewBox="0 0 40 40"><rect x="7" y="5" width="26" height="30" rx="2" fill="#C6A06F"/><path d="M12 12h16M12 18h16M12 24h10" stroke="#2B2621" stroke-width="3"/></svg>',
    stats: '<svg viewBox="0 0 40 40"><rect x="6" y="20" width="7" height="14" fill="#A8C6D8"/><rect x="16" y="10" width="7" height="24" fill="#D6503E"/><rect x="26" y="15" width="7" height="19" fill="#E3A93B"/></svg>',
    tier: '<svg viewBox="0 0 40 40"><rect x="4" y="6" width="32" height="8" fill="#D6503E"/><rect x="4" y="16" width="24" height="8" fill="#E3A93B"/><rect x="4" y="26" width="16" height="8" fill="#9DB77E"/></svg>',
    recs: '<svg viewBox="0 0 40 40"><path d="M20 4l5 10 11 2-8 8 2 11-10-5-10 5 2-11-8-8 11-2z" fill="#E3A93B" stroke="#2B2621" stroke-width="2"/></svg>',
    radar: '<svg viewBox="0 0 40 40"><circle cx="20" cy="20" r="15" fill="none" stroke="#22305A" stroke-width="3"/><circle cx="20" cy="20" r="8" fill="none" stroke="#22305A" stroke-width="3"/><path d="M20 20L32 10" stroke="#D6503E" stroke-width="4"/></svg>',
    maker: '<svg viewBox="0 0 40 40"><path d="M20 6 C10 6 7 15 8 24 L5 35 H35 L32 24 C33 15 30 6 20 6 Z" fill="#8FB3A0" stroke="#2B2621" stroke-width="2.5"/><circle cx="15" cy="19" r="3" fill="#2B2621"/><circle cx="25" cy="19" r="3" fill="#2B2621"/><path d="M27 4 L33 10 L22 21 L18 22 L19 18 Z" fill="#E3A93B" stroke="#2B2621" stroke-width="2"/></svg>',
    bestiary: '<svg viewBox="0 0 40 40"><rect x="6" y="5" width="28" height="31" rx="2" fill="#8C3A2E"/><rect x="9" y="8" width="22" height="25" fill="#E3DCC8"/><path d="M20 14 L25 18 L23 26 H17 L15 18 Z" fill="#2B2621"/><circle cx="18" cy="19" r="1.5" fill="#E3A93B"/><circle cx="22" cy="19" r="1.5" fill="#E3A93B"/></svg>',
    request: '<svg viewBox="0 0 40 40"><rect x="4" y="9" width="32" height="22" fill="#FBF8F0" stroke="#2B2621" stroke-width="2.5"/><path d="M4 10l16 12 16-12" fill="none" stroke="#D6503E" stroke-width="3"/></svg>',
  };
  // [icon, name, what it is, link, needs a game login]
  const LIB_TILES = [["party", "Party", "Everyone's crawler, level and gear", "#party", true], ["chronicle", "Chronicle", "Your reading history", "/chronicle"],
    ["stats", "Stats", "Listening numbers", "/archives"], ["tier", "Tier List", "Rank your series", "/tier"], ["recs", "Recommendations", "What to listen to next", "/recommendations"],
    ["radar", "Release Radar", "Upcoming books", "/radar"], ["bestiary", "Monster Bestiary", "Every monster you've faced", "/static/game/bestiary.html", true], ["maker", "Monster Maker", "Build a monster for the dungeons", "/static/game/maker.html", true], ["request", "Request", "Ask for a new series", "/request"]];
  const libTiles = (tiles) => tiles.map(([k, t, d, href]) => `<a class="tile" href="${href}">${ICON[k]}<strong>${t}</strong><span>${d}</span></a>`).join("");
  function renderLibrary() {
    $("lib").innerHTML = libTiles(LIB_TILES);
    $("lib").querySelector('a[href="#party"]').onclick = (e) => { e.preventDefault(); openParty(); };
  }
  // The title screen's Library button: the pages that work without logging in.
  function openTitleLibrary() {
    $("tl-lib").innerHTML = libTiles(LIB_TILES.filter((t) => !t[4]));
    $("title-library").hidden = false;
  }
  $("tl-ok").onclick = () => { $("title-library").hidden = true; };
  // ── the December boss panel ──────────────────────────────────────────
  let boss = null, bossAt = 0;
  const bossNow = () => boss.now + (Date.now() - bossAt) / 1000;  // server's boss clock (can be a preview date)
  function tick() {
    const el = $("countdown");
    if (!el || !boss) return;
    const ms = (boss.starts_at - bossNow()) * 1000;
    const d = Math.max(0, Math.floor(ms / 864e5)), h = Math.max(0, Math.floor(ms / 36e5) % 24), m = Math.max(0, Math.floor(ms / 6e4) % 60);
    el.innerHTML = [[d, "days"], [h, "hours"], [m, "min"]].map(([v, l]) => `<div><strong>${v}</strong><span>${l}</span></div>`).join("");
  }
  const day = (t) => new Date(t * 1000).toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
  async function renderBoss() {
    try { boss = await api("/boss"); bossAt = Date.now(); } catch { return; }
    const b = boss.boss, art = `<div class="boss-art">${window.Regent ? Regent.art({ height: 140 }) : ""}</div>`;
    const bar = (hp, max) => `<div class="boss-bar" role="img" aria-label="Regent health ${Math.round(100 * hp / max)}%"><i style="width:${Math.max(0, Math.min(100, 100 * hp / max))}%"></i><b>${hp.toLocaleString()} / ${max.toLocaleString()} · ${(100 * hp / max).toFixed(1)}%</b></div>`;
    const board = (list) => list.length ? `<h3>Damage so far</h3><ol class="boss-board">${list.slice(0, 6).map((t) => `<li class="${t.username === me.username ? "you" : ""}"><span>${esc(t.username.toUpperCase())}</span><span>${t.damage.toLocaleString()} · ${(100 * t.damage / b.max_hp).toFixed(1)}% of his health</span></li>`).join("")}</ol>` : "";
    const nullBox = (n) => !n ? "" : n.active
      ? `<div class="null-meter"><b>The Null spreads.</b> Every dungeon's monsters are 10% stronger until the party finishes ${n.target} books this January.${bar(n.books, n.target).replace(/<b>.*<\/b>/, `<b>${n.books} / ${n.target} books</b>`)}</div>`
      : `<div class="null-meter">The party cleansed the Null. The dungeons are back to normal.</div>`;
    let info = "", more = "";
    if (boss.phase === "before") {
      const last = boss.last;
      info = `<p class="boss-line">Wakes <b>December 1</b>. One boss, one shared health bar, the whole party.</p><div class="countdown" id="countdown"></div>`;
      if (last) more = `<p class="boss-line" style="margin-top:10px">${last.status === "escaped" ? `He escaped last December with <b>${last.pct}%</b> of his health. He's coming back, still wounded.` : last.status === "defeated" ? "The party brought him down last December. The System is… recompiling." : ""}</p>`;
    } else if (!b) {
      info = `<p class="boss-line">Quiet. For now.</p>`;
      more = nullBox(boss.null);
    } else if (b.status === "defeated") {
      info = `<p class="boss-line"><b>Defeated!</b> ${esc((b.killer || "").toUpperCase())} landed the killing blow.</p>${bar(0, b.max_hp)}`;
      more = board(boss.board);
    } else if (b.status === "escaped") {
      info = `<p class="boss-line">He escaped with <b>${Math.round(b.pct)}%</b> of his health. He'll be back next December.</p>${bar(b.hp, b.max_hp)}`;
      more = nullBox(boss.null) + board(boss.board);
    } else {
      const days = Math.max(0, Math.ceil((boss.ends_at - bossNow()) / 86400));
      info = `<p class="boss-line"><b>${Math.round(b.pct)}% left</b>, ${days} day${days === 1 ? "" : "s"} to go.</p>${bar(b.hp, b.max_hp)}`
        + (b.returning_pct ? `<p class="boss-line" style="font-size:14px">He's back, still wounded from last year (he escaped at ${b.returning_pct}%).</p>` : "");
      const m = boss.momentum;
      more = (boss.ready ? `<button class="btn" id="boss-go">Attack the Regent<small>${esc(boss.slot_name)} · a fight to the death</small></button>`
        : `<p class="boss-line" style="margin-top:10px">You've attacked in this window. ${boss.next_at ? `Next attack: <b>${day(boss.next_at)}</b>.` : "That was your last one this year."}</p>`)
        + `<div class="boss-chips"><span>Momentum +${m.bonus}% (${m.clears}/${m.max} dungeons cleared since your last attack)</span></div>`
        + `<h3>Boss Battle Banners</h3><p class="boss-line" style="font-size:14px">Boss fights only. Raise one and it helps every crawler's Regent fights this week (until Monday). Each banner can be raised once a week, and each crawler can raise one.</p>`
        + `<div class="banners">${boss.banners.map((bn) => `<div class="banner ${bn.raised_by ? "up" : ""}"><b>${esc(bn.name)}</b><span>${esc(bn.text)}</span>${bn.raised_by
          ? `<em class="raised">★ Raised by ${esc(bn.raised_by.toUpperCase())}</em>`
          : `<button data-banner="${bn.key}" ${boss.raised_one ? "disabled" : ""}>Raise · ${bn.cost} bookmarks</button>`}</div>`).join("")}</div>`
        + (boss.week_top ? `<p class="boss-line" style="margin-top:8px;font-size:14px">Top damage this week: ${esc(boss.week_top.username.toUpperCase())} (${boss.week_top.damage.toLocaleString()})</p>` : "")
        + board(boss.board);
    }
    $("boss-panel").innerHTML = `<div class="boss-body">${art}<div class="boss-info">${info}</div></div><div class="boss-more">${more}</div>`;
    tick();
    if ($("boss-go")) $("boss-go").onclick = attackBoss;
    document.querySelectorAll("[data-banner]").forEach((btn) => btn.addEventListener("click", async () => {
      const bn = boss.banners.find((x) => x.key === btn.dataset.banner);
      if (!confirmTap("banner:" + bn.key, `Tap again to raise the ${bn.name} for ${bn.cost} bookmarks. It helps everyone's Regent fights this week.`)) return;
      try { const res = await api(`/boss/banners/${bn.key}`, { method: "POST" }); me = { ...me, ...res.me }; badgesNow(); toast(`${bn.name} raised! It helps everyone's Regent fights this week.`); renderCharacter(); renderBoss(); renderFeed(); }
      catch (e) { toast(e.message); }
    }));
  }
  async function attackBoss() {
    try {
      const atk = await api("/boss/attack", { method: "POST" });
      show("dungeon");
      Dungeon.raid({ ...atk, username: me.username.toUpperCase(), xp: me.xp, xp_next: me.xp_next }, {
        onFinish: async (report) => {
          const res = await api(`/boss/attack/${atk.attack_id}/finish`, { method: "POST", body: report });
          me = { ...me, ...res.me };
          return res.result;
        },
        onDone: async (result, pending) => { await pullNotices(); pending ? openBag() : showHub(); },
      });
    } catch (e) { toast(e.message); renderBoss(); }
  }
  function showHub() {
    show("hub");
    window.Music && Music.play("hub");
    renderCharacter(); renderShelf(); renderFeed(); renderLibrary(); renderPractice(); renderBoss();
    if (!me.guide_seen) openGuide(); else showNotices();
  }

  // ── first-time guide (also under "How to play") ──────────────────────
  const G_ICON = {
    books: '<svg viewBox="0 0 120 100"><rect x="10" y="20" width="22" height="70" fill="#D6503E" stroke="#2B2621" stroke-width="3"/><rect x="34" y="12" width="20" height="78" fill="#22305A" stroke="#2B2621" stroke-width="3"/><rect x="56" y="24" width="24" height="66" fill="#E3A93B" stroke="#2B2621" stroke-width="3"/><path d="M84 90 L96 30 L114 34 L102 94 Z" fill="#8FB3A0" stroke="#2B2621" stroke-width="3"/><rect x="4" y="90" width="112" height="6" fill="#6B4A2E"/></svg>',
    doors: '<svg viewBox="0 0 140 100"><path d="M10 96 V40 Q35 8 60 40 V96 Z" fill="#6B4A2E" stroke="#2B2621" stroke-width="3"/><path d="M80 96 V40 Q105 8 130 40 V96 Z" fill="#22305A" stroke="#2B2621" stroke-width="3"/><circle cx="50" cy="68" r="4" fill="#E3A93B"/><circle cx="120" cy="68" r="4" fill="#E3A93B"/><text x="35" y="60" font-size="22" text-anchor="middle" fill="#FBF8F0">?</text><text x="105" y="60" font-size="22" text-anchor="middle" fill="#FBF8F0">!</text></svg>',
    bookmark: '<svg viewBox="0 0 100 100"><path d="M30 8 H70 V92 L50 74 L30 92 Z" fill="#D6503E" stroke="#2B2621" stroke-width="3"/><path d="M40 30 H60 M40 42 H60" stroke="#FBF8F0" stroke-width="4"/></svg>',
    party: '<svg viewBox="0 0 120 100"><circle cx="36" cy="34" r="16" fill="#D6503E"/><circle cx="84" cy="34" r="16" fill="#22305A"/><circle cx="60" cy="26" r="16" fill="#E3A93B"/><path d="M8 96 C8 64 64 64 64 96 Z M56 96 C56 64 112 64 112 96 Z" fill="#8FB3A0" stroke="#2B2621" stroke-width="3"/></svg>',
  };
  function guideSteps() {
    return [
      { art: () => me.look && me.cls ? A.render(me.look, me.cls, { height: 130 }) : "", title: `Welcome, ${me.username.toUpperCase()}`,
        text: `<p>This is your crawler. You level them up by listening.</p><ul><li><b>Every audiobook you finish becomes a dungeon</b> on your shelf.</li><li>Books you finished before the game started are all waiting for you too.</li></ul>` },
      { art: () => G_ICON.books, title: "Your dungeons",
        text: `<ul><li><b>Longer books drop better loot.</b> 20+ hour books give two chests.</li><li>Clear every book of a series for <b>5 bookmarks a book</b>. Series of 5+ books also give a <b>guaranteed Epic</b>.</li><li>Difficulty always matches your level, so any book is a fair fight.</li><li>In your <b>Bag</b>, <b>Best gear</b> puts on the strongest gear for your class; ▲ marks an upgrade.</li></ul>` },
      { art: () => G_ICON.doors, title: "Crawling",
        text: `<ul><li>Pick a door each room: monsters, elites, loot boxes, shrines, traps.</li><li>At the bottom: fight the <b>floor boss</b> for better loot, or take the stairs.</li><li>Fall, and the book goes to your <b>Fallen</b> shelf. Revive it with bookmarks and try again.</li><li>You can leave between rooms; your place is saved.</li></ul>` },
      { art: () => "", title: "Fighting",
        text: `<ul><li><b>Strike</b> builds energy. Spend it on your class's moves: Rage, Judgements, Runes, Hexes, a Volley, or your pets.</li><li>When the monster's next move is in <b style="color:var(--red)">red</b>, <b>Guard</b>.</li><li>Potions heal. Beastmasters and Necromancers bring pets.</li><li>From level 5, <b>Auto battle</b> can fight regular monsters for you (never bosses).</li><li>Practice in the <b>Training grounds</b> any time: it costs and pays nothing.</li></ul>` },
      { art: () => G_ICON.bookmark, title: "Bookmarks",
        text: `<ul><li>Earned from dungeons, finishing books, and badges.</li><li>Spend them in the <b>Forge</b> (permanent upgrades), the <b>Store</b> (opens after 10 clears), the <b>Wardrobe</b>, and on revives.</li></ul>` },
      { art: () => window.Regent ? Regent.art({ height: 130 }) : "", title: "December: the Null Regent",
        text: `<ul><li>One boss, one health bar, <b>the whole party</b>.</li><li>Everyone gets one attack a week, plus Christmas. Each one is a fight to the death.</li><li>Raise <b>Boss Battle Banners</b> to help everyone.</li><li>If he escapes, there are consequences…</li></ul>` },
      { art: () => G_ICON.party, title: "The rest of the party",
        text: `<ul><li>See everyone's crawler, gear and badges on the <b>Party</b> screen.</li><li>Every monster you meet goes in your <b>Bestiary</b>.</li><li>In the <b>Arena</b>, fight a friend's ghost (their real stats and gear). Beat someone above you on the ladder to take their spot. Each week #1 wins an Epic, and the most wins a Rare.</li><li>Build your own monster in the <b>Monster Maker</b>. Once the admin approves it, it lurks in the dungeons for everyone.</li><li>Keep your <b>Tier List</b> current: ranking a series you finished pays bookmarks.</li><li>Music and sounds are off by default: switches are in the bottom corner.</li></ul><p>You can reopen this under <b>How to play</b>.</p>` },
    ];
  }
  let guideAt = 0;
  function openGuide() { guideAt = 0; drawGuide(); $("guide").hidden = false; $("guide-next").focus(); }
  function drawGuide() {
    const steps = guideSteps(), st = steps[guideAt];
    $("guide-art").innerHTML = st.art(); $("guide-art").hidden = !$("guide-art").innerHTML;
    $("guide-title").textContent = st.title; $("guide-text").innerHTML = st.text;
    $("guide-dots").innerHTML = steps.map((_, i) => `<i class="${i === guideAt ? "on" : ""}"></i>`).join("");
    $("guide-back").disabled = guideAt === 0;
    $("guide-next").textContent = guideAt === steps.length - 1 ? "Let's crawl" : "Next";
  }
  function closeGuide() {
    $("guide").hidden = true;
    if (!me.guide_seen) { me.guide_seen = true; api("/me/guide", { method: "POST" }).catch(() => {}); }
    showNotices();
  }
  $("guide-next").onclick = () => { if (guideAt >= guideSteps().length - 1) return closeGuide(); guideAt++; drawGuide(); };
  $("guide-back").onclick = () => { if (guideAt > 0) { guideAt--; drawGuide(); } };
  $("guide-skip").onclick = closeGuide;
  $("open-guide").onclick = openGuide;
  function showNotices() {
    const n = noticeQueue.shift();
    if (!n) return;
    if (n.kind === "achievement") {
      const more = [n];
      while (noticeQueue[0] && noticeQueue[0].kind === "achievement") more.push(noticeQueue.shift());
      const paid = more.reduce((t, b) => t + (b.bookmarks || 0), 0);
      $("notice-big").textContent = paid ? `★ +${paid}` : "★";
      $("notice-title").textContent = more.length > 1 ? `${more.length} badges earned` : `Badge earned: ${n.name}`;
      $("notice-text").textContent = (more.length > 1 ? more.map((b) => b.name).join(" · ") : n.text) + (paid ? ` (+${paid} bookmarks)` : "");
      $("notice").hidden = false; $("notice-ok").focus();
      return;
    }
    const tier = me.tier || { to_rank: [], rerank: [] };
    const unranked = n.kind === "book_finished" && (n.series || []).find((sn) => tier.to_rank.includes(sn));
    $("notice-go").hidden = !(unranked || n.kind === "tier_reward");
    const [big, title, text] = n.kind === "welcome"
      ? [`+${n.bookmarks}`, "Welcome Chest", "Bookmarks are the dungeon's currency. Spend them in the Forge, on revives, and in the Store once it opens."]
      : n.kind === "book_finished" ? [`+${n.bookmarks}`, "You finished a book!", `${shortTitle(n.title)} is now a dungeon on your shelf, and you earned bookmarks for finishing it.`
        + (unranked ? ` Rank ${unranked} in your Tier List for +5 more.` : "")]
      : n.kind === "tier_reward" ? [`+${n.bookmarks}`, "Tier List rewards", `Thanks for ranking ${n.names.join(", ")}${n.count > n.names.length ? ` and ${n.count - n.names.length} more` : ""}. New series you finish pay 5 bookmarks when you rank them.`]
      : n.kind === "series_complete" ? (n.outcome === "caught_up"
        ? [`+${n.bookmarks}`, "Caught up!", `You're caught up on ${n.series} again: ${n.new_books} new book${n.new_books === 1 ? "" : "s"}, ${n.bookmarks} bookmarks.${n.chest_rarity ? ` Your chest: ${n.chest_rarity}.` : ""}`]
        : [`+${n.bookmarks}`, "Series complete!", `You've cleared all ${n.books} books of ${n.series}: ${n.bookmarks} bookmarks.${n.chest_rarity ? ` The finale chest: ${n.chest_rarity}!` : ""}`])
      : n.kind === "arena_week" ? (n.prize === "champion"
        ? ["🏆", "Arena Champion of the week!", `You held #1 on the ladder this week.${n.item ? ` Your prize: ${n.item.rarity} ${n.item.name}. Check your bag.` : ""}`]
        : ["⚔", "Most duel wins this week!", `${n.wins} wins in the Arena this week.${n.item ? ` Your prize: ${n.item.rarity} ${n.item.name}. Check your bag.` : ""}`])
      : n.kind === "duel" ? (n.ghost_won
        ? [`+${n.bookmarks}`, "Your ghost held!", `${n.challenger.toUpperCase()} challenged your ghost in the Arena and lost. You're still #${n.rank}.`]
        : ["⚔", "Your ghost fell", `${n.challenger.toUpperCase()} beat your ghost in the Arena${n.moved ? ` and you dropped to #${n.rank}` : ""}. Revenge is one challenge away.`])
      : n.kind === "forge_refund" ? [`+${n.bookmarks}`, "Forge refund", `${n.name} now stops one energy short of a full bar, so its top rank is gone. Here are your bookmarks back.`]
      : n.kind === "monster_live" ? ["👹", "Your monster is alive!", `The admin approved ${n.name}. It now lurks in ${n.theme}. Good luck to everyone. Especially you.`]
      : n.kind === "boss_won" ? [`+${n.bookmarks}`, "The Null Regent has fallen!", `${n.killer.toUpperCase()} landed the killing blow. Everyone who fought shares the hoard${n.item ? `: you got ${n.item.rarity} ${n.item.name}` : ""}. Check your bag.`]
      : n.kind === "boss_escaped" ? ["⚠", "He escaped", `The Null Regent got away with ${n.pct}% of his health. You earned a scar for fighting him. He'll be back next December, still wounded, and until the party cleanses it, the Null spreads through the dungeons.`]
      : ["!", n.kind, ""];
    $("notice-big").textContent = big; $("notice-title").textContent = title; $("notice-text").textContent = text;
    $("notice").hidden = false; $("notice-ok").focus();
  }
  $("notice-ok").onclick = () => { $("notice").hidden = true; showNotices(); };

  // ── bag ──────────────────────────────────────────────────────────────
  const lv = (it) => (it && it.ilvl ? `Lv ${it.ilvl} ` : "");   // item level
  const RC = { Common: "var(--r-common)", Uncommon: "var(--r-uncommon)", Rare: "var(--r-rare)", Epic: "var(--r-epic)", Legendary: "var(--r-legendary)" };
  let bagData = null, openItem = null;
  async function openBag() {
    show("bag"); bagSel = null; bagFilter = null;
    try { bagData = await api("/me/bag"); drawBag(); } catch (e) { toast(e.message); }
  }
  function statLine(it) { return [["ATK", it.atk], ["DEF", it.def], ["HP", it.hp]].filter(([, v]) => v).map(([k, v]) => `<span>${k} +${v}</span>`).join(""); }
  function compare(it) {
    const worn = bagData.equipped[it.slot];
    if (!worn || worn.id === it.id) return "";
    return ["atk", "def", "hp"].map((k) => {
      const d = (it[k] || 0) - (worn[k] || 0);
      return d ? `<span class="${d > 0 ? "up" : "down"}">${k.toUpperCase()} ${d > 0 ? "▲ +" : "▼ "}${d}</span>` : "";
    }).join("") || "<span>Same stats as what you're wearing.</span>";
  }
  function itemCard(it, kind) {
    const open = openItem === `${kind}-${it.id || it.pending_id}`;
    const scrapV = bagData.scrap_value[it.rarity];
    let actions = "";
    if (open) {
      if (kind === "bag") actions = `<div class="compare">vs. worn: ${compare(it)}</div><div class="item-actions">
          <button class="btn" data-act="equip">Equip</button>
          <button class="btn alt" data-act="lock">${it.locked ? "Unlock" : "Lock"}</button>
          ${it.locked ? "" : `<button class="btn alt" data-act="scrap">Scrap (+${scrapV})</button>`}</div>`;
      if (kind === "worn") actions = `<div class="item-actions"><button class="btn alt" data-act="unequip">Take off</button><button class="btn alt" data-act="lock">${it.locked ? "Unlock" : "Lock"}</button></div>`;
      if (kind === "pending") actions = `<div class="compare">vs. worn: ${compare(it)}</div><div class="item-actions"><button class="btn" data-act="take">Keep it</button><button class="btn alt" data-act="scrap">Scrap (+${scrapV})</button></div>`;
    }
    return `<div class="item" style="--rc:${RC[it.rarity]}" data-kind="${kind}" data-id="${it.id || it.pending_id}" aria-expanded="${open}" role="button" tabindex="0">
      <div class="icon">${it.icon ? `<img src="${esc(it.icon)}" alt="">` : ""}</div>
      <div style="min-width:0"><div class="rar">${lv(it)}${it.rarity} ${it.slot}${it.locked ? '<span class="lockmark">locked</span>' : ""}</div><div class="iname">${esc(it.name)}</div><div class="istats">${statLine(it)}</div></div>
      ${actions}</div>`;
  }
  // The bag: your six slots on top, the bag as a grid below. Drag an item onto
  // its slot to wear it (or a worn item down into the bag to take it off);
  // or tap an item for details and buttons. On touch screens, press and hold
  // an item to drag it, so the page still scrolls normally.
  let bagSel = null, bagFilter = null;   // selected {kind, id}; bag filtered to one slot
  // Your totals, and what they'd become: wearing `it` (from the bag) or taking it off.
  const STAT_NAMES = [["hp", "Health"], ["atk", "Attack"], ["def", "Defense"]];
  function statChanges(it, kind) {
    const cur = me.stats || { hp: 0, atk: 0, def: 0 };
    const worn = kind === "bag" ? bagData.equipped[it.slot] : null;
    return STAT_NAMES.map(([k, label]) => {
      const d = kind === "worn" ? -(it[k] || 0) : (it[k] || 0) - ((worn && worn[k]) || 0);
      return { k, label, cur: cur[k], next: cur[k] + d, d };
    });
  }
  function statsBar(it, kind) {
    const rows = it ? statChanges(it, kind) : STAT_NAMES.map(([k, label]) => ({ k, label, cur: (me.stats || {})[k], d: 0 }));
    return rows.map((r) => `<div class="stat${r.d > 0 ? " up" : r.d < 0 ? " down" : ""}"><span>${r.label}</span>
      <b>${r.cur}${r.d ? ` → ${r.next}` : ""}</b>${r.d ? `<em>${r.d > 0 ? "▲ +" : "▼ −"}${Math.abs(r.d)}</em>` : ""}</div>`).join("");
  }
  function swapLine(it, kind) {
    const ch = statChanges(it, kind).filter((c) => c.d);
    const what = kind === "worn" ? "Taking this off" : bagData.equipped[it.slot] ? "Wearing this instead" : "Wearing this";
    return ch.length ? `<div class="swap">${what}: ${ch.map((c) => `<span class="${c.d > 0 ? "up" : "down"}">${c.d > 0 ? "+" : "−"}${Math.abs(c.d)} ${c.label}</span>`).join(", ")}</div>`
      : `<div class="swap">${what}: no change to your stats.</div>`;
  }
  const tileIcon = (it) => `<span class="ticon" style="--rc:${RC[it.rarity]}">${it.icon ? `<img src="${esc(it.icon)}" alt="" draggable="false">` : ""}${it.locked ? '<i class="tlock" title="Locked">🔒</i>' : ""}${it.ilvl ? `<i class="tlv" title="Item level">${it.ilvl}</i>` : ""}</span>`;
  function drawBag() {
    const d = bagData;
    $("bag-bm").textContent = `${me.bookmarks} bookmarks`;
    const sel = bagSel && (bagSel.kind === "worn" ? Object.values(d.equipped).find((i) => i.id === bagSel.id) : d.bag.find((i) => i.id === bagSel.id));
    const slotsHtml = SLOTS.map((sl) => {
      const it = d.equipped[sl];
      const hot = sel && bagSel.kind === "bag" && sel.slot === sl;
      return `<button class="slot${it ? "" : " empty"}${hot ? " hot" : ""}${bagSel && bagSel.kind === "worn" && it && it.id === bagSel.id ? " picked" : ""}${bagFilter === sl ? " filtering" : ""}"
          data-slot="${sl}" ${it ? `data-drag="worn" data-id="${it.id}"` : ""} aria-label="${sl}: ${it ? esc(it.name) : "empty"}">
        <span class="slabel">${sl}</span>${it ? tileIcon(it) : '<span class="ticon"></span>'}<span class="sname">${it ? esc(it.name) : "Empty"}</span></button>`;
    }).join("");
    const shown = d.bag.filter((i) => !bagFilter || i.slot === bagFilter);
    const bagHtml = shown.map((it) => {
      const up = (d.better || []).includes(it.id);
      return `<button class="btile${bagSel && bagSel.kind === "bag" && bagSel.id === it.id ? " picked" : ""}" data-drag="bag" data-id="${it.id}" aria-label="${esc(lv(it) + it.rarity + " " + it.slot + ": " + it.name)}">
        ${tileIcon(it)}${up ? '<i class="tup" title="Better for your class than what you wear">▲</i>' : ""}</button>`;
    }).join("");
    let detail = `<p class="bag-hint">Drag an item onto its slot to wear it, or tap it for details. Tap a slot to show only that kind of gear.</p>`;
    if (sel) {
      const scrapV = d.scrap_value[sel.rarity];
      const btns = bagSel.kind === "worn"
        ? `<button class="btn alt" data-act="unequip">Take off</button><button class="btn alt" data-act="lock">${sel.locked ? "Unlock" : "Lock"}</button>`
        : `<button class="btn" data-act="equip">Equip</button><button class="btn alt" data-act="lock">${sel.locked ? "Unlock" : "Lock"}</button>${sel.locked ? "" : `<button class="btn alt" data-act="scrap">Scrap (+${scrapV})</button>`}`;
      detail = `<div class="bag-detail" style="--rc:${RC[sel.rarity]}">${tileIcon(sel)}
        <div style="min-width:0"><div class="rar">${lv(sel)}${sel.rarity} ${sel.slot}${bagSel.kind === "worn" ? " · wearing" : ""}</div><div class="iname">${esc(sel.name)}</div>
          <div class="istats">${statLine(sel)}</div>${swapLine(sel, bagSel.kind)}
          ${sel.flavor ? `<div class="flav">“${esc(sel.flavor)}”</div>` : ""}</div>
        <div class="item-actions">${btns}</div></div>`;
    }
    $("bag-body").innerHTML = `
      ${d.pending.length ? `<div class="pending-box"><b>Loot waiting.</b> Your bag is full. Keep it (after scrapping something), or scrap it. You can't start a new dungeon until these are sorted.</div><div class="items">${d.pending.map((i) => itemCard(i, "pending")).join("")}</div>` : ""}
      <div class="bag-stats" id="bag-stats">${statsBar(sel, sel && bagSel.kind)}</div>
      <div class="section-label wear-head">Wearing <button class="btn small" id="bag-best" title="Wear the best gear in your bag for your class">Best gear</button></div>
      <div class="slots" id="slots">${slotsHtml}</div>
      <div id="bag-detail">${detail}</div>
      <div class="section-label bag-head">Bag ${d.bag.length} / ${d.capacity}${bagFilter ? ` · ${bagFilter} <button class="linkish" id="bag-all">show all</button>` : ""}</div>
      <div class="bag-grid" id="bag-grid">${bagHtml || `<p class="empty-bag">${bagFilter ? `No ${bagFilter.toLowerCase()} gear in your bag.` : "Empty."}</p>`}</div>`;
    $("bag-body").querySelectorAll(".items .item").forEach((el) => el.addEventListener("click", (e) => {
      const act = e.target.closest("[data-act]")?.dataset.act;
      if (act) return itemAction(el.dataset.kind, Number(el.dataset.id), act);
      openItem = openItem === `pending-${el.dataset.id}` ? null : `pending-${el.dataset.id}`; drawBag();
    }));
    $("bag-detail").querySelectorAll("[data-act]").forEach((b) => b.addEventListener("click", () => itemAction(bagSel.kind, bagSel.id, b.dataset.act)));
    if ($("bag-all")) $("bag-all").onclick = () => { bagFilter = null; drawBag(); };
    $("bag-best").onclick = equipBest;
    $("slots").querySelectorAll(".slot").forEach((el) => el.addEventListener("click", () => {
      if (dragJustEnded) return;
      const sl = el.dataset.slot, it = bagData.equipped[sl];
      if (bagSel && bagSel.kind === "bag" && bagData.bag.find((i) => i.id === bagSel.id)?.slot === sl) return itemAction("bag", bagSel.id, "equip");
      bagFilter = bagFilter === sl && !it ? null : sl;
      bagSel = it ? { kind: "worn", id: it.id } : null;
      drawBag();
    }));
    $("bag-grid").querySelectorAll(".btile").forEach((el) => el.addEventListener("click", () => {
      if (dragJustEnded) return;
      const id = Number(el.dataset.id);
      bagSel = bagSel && bagSel.kind === "bag" && bagSel.id === id ? null : { kind: "bag", id };
      drawBag();
    }));
    $("bag-body").querySelectorAll("[data-drag]").forEach(enableDrag);
    // On a computer, hovering an item previews what it would do to your stats.
    const resetBar = () => { $("bag-stats").innerHTML = statsBar(sel, sel && bagSel.kind); };
    $("bag-body").querySelectorAll("[data-drag]").forEach((el) => {
      el.addEventListener("pointerenter", (e) => {
        if (e.pointerType !== "mouse" || drag) return;
        const id = Number(el.dataset.id), kind = el.dataset.drag;
        const it = kind === "worn" ? Object.values(bagData.equipped).find((i) => i.id === id) : bagData.bag.find((i) => i.id === id);
        if (it) $("bag-stats").innerHTML = statsBar(it, kind);
      });
      el.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") resetBar(); });
    });
  }

  // ── drag and drop (mouse: drag; touch: press and hold, then drag) ──────
  let drag = null, dragJustEnded = false;
  function enableDrag(el) {
    el.addEventListener("pointerdown", (e) => {
      if (e.button > 0) return;
      const start = { x: e.clientX, y: e.clientY };
      const kind = el.dataset.drag, id = Number(el.dataset.id);
      const item = kind === "worn" ? Object.values(bagData.equipped).find((i) => i.id === id) : bagData.bag.find((i) => i.id === id);
      if (!item) return;
      let holdTimer = null;
      const begin = (x, y) => {
        drag = { kind, id, item, el };
        const g = document.createElement("div");
        g.className = "drag-ghost"; g.innerHTML = tileIcon(item);
        document.body.appendChild(g); drag.ghost = g; moveGhost(x, y);
        el.classList.add("dragging");
        document.querySelectorAll(`.slot[data-slot="${item.slot}"]`).forEach((s) => s.classList.add("drop-ok"));
        if (kind === "worn") $("bag-grid").classList.add("drop-ok");
        if (navigator.vibrate) navigator.vibrate(15);
      };
      const move = (ev) => {
        if (drag) { ev.preventDefault(); moveGhost(ev.clientX, ev.clientY); markOver(ev.clientX, ev.clientY); return; }
        const far = Math.hypot(ev.clientX - start.x, ev.clientY - start.y) > 8;
        if (e.pointerType === "mouse" && far) begin(ev.clientX, ev.clientY);
        else if (far) { clearTimeout(holdTimer); cleanup(); }  // touch moved first: it's a scroll
      };
      const up = (ev) => { clearTimeout(holdTimer); if (drag) finishDrag(ev.clientX, ev.clientY); cleanup(); };
      const cleanup = () => { document.removeEventListener("pointermove", move); document.removeEventListener("pointerup", up); document.removeEventListener("pointercancel", up); };
      document.addEventListener("pointermove", move, { passive: false });
      document.addEventListener("pointerup", up); document.addEventListener("pointercancel", up);
      if (e.pointerType !== "mouse") holdTimer = setTimeout(() => begin(start.x, start.y), 260);
    });
    el.addEventListener("contextmenu", (e) => { if (drag) e.preventDefault(); });
  }
  // While dragging on a phone, stop the page from scrolling under your finger.
  document.addEventListener("touchmove", (e) => { if (drag) e.preventDefault(); }, { passive: false });
  function moveGhost(x, y) { if (drag && drag.ghost) { drag.ghost.style.left = `${x}px`; drag.ghost.style.top = `${y}px`; } }
  function dropTarget(x, y) {
    const el = document.elementFromPoint(x, y);
    if (!el) return null;
    const slot = el.closest(".slot");
    if (slot) return { slot: slot.dataset.slot };
    if (el.closest("#bag-grid")) return { bag: true };
    return null;
  }
  function markOver(x, y) {
    document.querySelectorAll(".drop-over").forEach((n) => n.classList.remove("drop-over"));
    const t = dropTarget(x, y);
    if (t && t.slot === drag.item.slot) document.querySelector(`.slot[data-slot="${t.slot}"]`).classList.add("drop-over");
    if (t && t.bag && drag.kind === "worn") $("bag-grid").classList.add("drop-over");
  }
  function finishDrag(x, y) {
    const d = drag; drag = null;
    d.ghost.remove(); d.el.classList.remove("dragging");
    document.querySelectorAll(".drop-ok, .drop-over").forEach((n) => n.classList.remove("drop-ok", "drop-over"));
    dragJustEnded = true; setTimeout(() => { dragJustEnded = false; }, 50);
    const t = dropTarget(x, y);
    if (!t) return;
    if (t.slot && d.kind === "bag") {
      if (t.slot !== d.item.slot) return toast(`That goes in the ${d.item.slot} slot.`);
      return itemAction("bag", d.id, "equip");
    }
    if (t.bag && d.kind === "worn") return itemAction("worn", d.id, "unequip");
  }
  // Best gear: the server picks the strongest loadout for your class and level
  // (worn and bag together) and swaps it on; the toast says what changed.
  async function equipBest() {
    try {
      const res = await api("/me/equip-best", { method: "POST", body: {} });
      me = { ...me, ...res.me }; bagData = res; bagSel = null; openItem = null;
      if (!res.put_on.length) { toast("You're already wearing your best gear."); drawBag(); return; }
      const ch = STAT_NAMES.map(([k, label]) => [label, res.me.stats[k] - res.before[k]]).filter(([, d]) => d)
        .map(([label, d]) => `${d > 0 ? "+" : "−"}${Math.abs(d)} ${label}`).join(", ");
      toast(`Put on ${res.put_on.length} item${res.put_on.length > 1 ? "s" : ""}${ch ? `: ${ch}` : ""}.`);
      drawBag();
    } catch (e) { toast(e.message); }
  }

  async function itemAction(kind, id, act) {
    try {
      let res;
      if (kind === "pending") {
        if (act === "scrap" && !confirmTap(`p${id}`, "Tap Scrap again to destroy it.")) return;
        res = await api(`/me/pending/${id}/${act}`, { method: "POST" });
      } else if (act === "lock") {
        const it = [...bagData.bag, ...Object.values(bagData.equipped)].find((i) => i.id === id);
        res = await api(`/me/items/${id}/lock`, { method: "POST", body: { locked: !it.locked } });
      } else {
        if (act === "scrap" && !confirmTap(`i${id}`, "Tap Scrap again to destroy it.")) return;
        res = await api(`/me/items/${id}/${act}`, { method: "POST", body: {} });
      }
      me = { ...me, ...res.me }; bagData = res; openItem = null;
      if (act === "equip") { bagSel = { kind: "worn", id }; toast("Equipped."); }
      else if (act === "unequip") { bagSel = { kind: "bag", id }; }
      else if (act === "scrap") { bagSel = null; toast("Scrapped."); }
      drawBag();
    } catch (e) { toast(e.message); }
  }
  $("bag-back").onclick = showHub;
  $("open-bag").onclick = openBag;

  // ── the party ────────────────────────────────────────────────────────
  const rc = (r) => RC[r] || "#B9B1A2";
  // Someone's crawler, laid out like your own "Your crawler" card: art, name,
  // class and level, XP bar, the three stat boxes, a line of extras, gear tiles.
  function crawlerCard(m, { rank = 0, gearNames = false } = {}) {
    const st = m.stats;
    return `<div class="char">
        <div class="sticker">${A.render(m.look, m.cls, { height: 150 })}</div>
        <div>
          <div class="name">${rank ? `<span class="rank">#${rank}</span>` : ""}${nameTag(m.username, m.worn)}${m.title ? `<div class="ctitle">${esc(m.title)}</div>` : ""}</div>
          <div class="cls">${A.CLASSES[m.cls].name} · Level ${m.level}</div>
          <div class="xp"><i style="width:${Math.min(100, (100 * m.xp) / m.xp_next)}%"></i></div>
          <div class="xp-text">${m.xp} / ${m.xp_next} XP to level ${m.level + 1}</div>
        </div>
      </div>
      ${st ? `<div class="stats">${[["Health", st.hp], ["Attack", st.atk], ["Defense", st.def]].map(([k, v]) => `<div><strong>${v}</strong>${k}</div>`).join("")}</div>
      <div class="pmore">${Math.round(st.crit * 100)}% crit · ${st.energy} energy${st.start_energy ? ` (starts with ${st.start_energy})` : ""} · ${st.potions} potions · ${m.clears} cleared${m.badges != null ? ` · ${m.badges} badges` : ""}</div>` : ""}
      <div class="gear">${SLOTS.map((sl) => { const it = m.gear[sl]; return it
        ? `<div class="gslot" style="border-color:var(--r-${it.rarity.toLowerCase()})" title="${esc(it.rarity + " " + sl + ": " + it.name)}"${gearNames ? ` data-gear="${sl}" role="button" tabindex="0"` : ""}><img src="${esc(it.icon)}" alt="${esc(it.name)}"></div>` : `<div class="gslot">${sl}</div>`; }).join("")}</div>
      ${gearNames ? `<div id="pgear-detail"></div><div class="gear-list">${SLOTS.filter((sl) => m.gear[sl]).map((sl) => { const it = m.gear[sl];
        return `<div style="--rc:${rc(it.rarity)}" data-gear="${sl}" role="button" tabindex="0">${esc(it.name)}<small>${lv(it)}${it.rarity} ${sl}</small></div>`; }).join("")}</div>` : ""}`;
  }
  // Tap a piece of someone's gear: the same details card as in your bag, plus
  // how it compares with what you wear in that slot.
  function gearDetail(it, mine) {
    const worn = !mine && me.gear ? me.gear[it.slot] : null;
    const diff = mine ? [] : STAT_NAMES.map(([k, label]) => [label, (it[k] || 0) - ((worn && worn[k]) || 0)]).filter(([, d]) => d);
    const cmp = mine ? "" : `<div class="swap">${worn ? "Compared with yours" : "You have nothing in this slot"}: ${diff.length
      ? diff.map(([label, d]) => `<span class="${d > 0 ? "up" : "down"}">${d > 0 ? "+" : "−"}${Math.abs(d)} ${label}</span>`).join(", ") : "same stats."}</div>`;
    return `<div class="bag-detail" style="--rc:${RC[it.rarity]}">${tileIcon(it)}
      <div style="min-width:0"><div class="rar">${lv(it)}${it.rarity} ${it.slot}</div><div class="iname">${esc(it.name)}</div>
        <div class="istats">${statLine(it)}</div>${cmp}
        ${it.flavor ? `<div class="flav">“${esc(it.flavor)}”</div>` : ""}</div></div>`;
  }
  async function openParty() {
    show("party");
    $("party-title").textContent = "The Party";
    $("party-body").innerHTML = `<p class="empty">Gathering the party…</p>`;
    try {
      const { members } = await api("/party");
      $("party-body").innerHTML = `<p style="color:var(--muted);margin-bottom:10px">Ranked by level. Tap a crawler for their stats, gear, badges and Hall of Fame.</p>
        <div class="party-grid">${members.map((m, i) => `<button class="member pcard${m.you ? " you" : ""}" data-u="${esc(m.username)}">${crawlerCard(m, { rank: i + 1 })}</button>`).join("")}</div>`;
      $("party-body").querySelectorAll(".member").forEach((b) => b.addEventListener("click", () => openMember(b.dataset.u)));
    } catch (e) { $("party-body").innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
  }
  async function openMember(username) {
    show("party");
    $("party-body").innerHTML = `<p class="empty">Loading…</p>`;
    try {
      const m = await api(`/party/${encodeURIComponent(username)}`);
      $("party-title").textContent = m.you ? "Your badges" : m.username.toUpperCase();
      const got = m.achievements.filter((a) => a.earned_at).length;
      const groups = [...new Set(m.achievements.map((a) => a.group))];
      const hof = m.hall_of_fame;
      $("party-body").innerHTML = `<div class="profile">
        <div class="card pcard">${crawlerCard(m, { gearNames: true })}</div>
        <div class="card">
          <h2 style="font-size:22px">Badges <span style="font-family:var(--hand);font-size:17px;color:var(--muted)">${got} / ${m.achievements.length} · each one pays 10 bookmarks</span></h2>
          ${groups.map((g) => `<div class="badge-group">${esc(g)}</div><div class="badges">${m.achievements.filter((a) => a.group === g).map((a) =>
            `<div class="badge-card${a.earned_at ? " got" : ""}"><strong>${esc(a.name)}</strong>${esc(a.text)}</div>`).join("")}</div>`).join("")}
          <h2 style="font-size:22px;margin-top:20px">Hall of Fame <span style="font-family:var(--hand);font-size:17px;color:var(--muted)">${hof.length} from the old journal</span></h2>
          <p style="font-size:15px;color:var(--muted);margin:4px 0 8px">The original listening achievements, frozen when the dungeon opened.</p>
          ${hof.length ? `<div class="hof" id="hof">${hof.slice(0, 24).map(hofRow).join("")}</div>
            ${hof.length > 24 ? `<button class="btn ghost" id="hof-all" style="margin-top:10px">Show all ${hof.length}</button>` : ""}` : '<p class="empty">Nothing from before the dungeon.</p>'}
        </div></div>
        <button class="btn ghost" id="party-list" style="margin-top:14px">See the whole party</button>`;
      $("party-list").onclick = openParty;
      let shown = null;
      $("party-body").querySelectorAll("[data-gear]").forEach((el) => el.addEventListener("click", () => {
        const sl = el.dataset.gear;
        shown = shown === sl ? null : sl;
        $("pgear-detail").innerHTML = shown ? gearDetail(m.gear[sl], m.you) : "";
        $("party-body").querySelectorAll(".gslot[data-gear]").forEach((g) => g.classList.toggle("picked", g.dataset.gear === shown));
        if (shown) $("pgear-detail").scrollIntoView({ block: "nearest", behavior: "smooth" });
      }));
      if ($("hof-all")) $("hof-all").onclick = () => { $("hof").innerHTML = hof.map(hofRow).join(""); $("hof-all").remove(); };
    } catch (e) { $("party-body").innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
  }
  const hofRow = (h) => `<div style="--rc:${rc(h.rarity)}" title="${esc(h.text)}">${h.icon ? `<img loading="lazy" src="${esc(h.icon)}" alt="">` : "<span></span>"}<span><strong>${esc(h.name)}</strong>${esc(h.rarity)}</span></div>`;
  $("party-back").onclick = showHub;

  // ── the Arena: ghost duels and the ladder ─────────────────────────────
  async function openArena() {
    show("arena");
    $("arena-body").innerHTML = `<p class="empty">Opening the gates…</p>`;
    try { drawArena(await api("/arena")); } catch (e) { $("arena-body").innerHTML = `<p class="empty">${esc(e.message)}</p>`; }
  }
  const weekEnds = (t) => new Date(t * 1000 - 1000).toLocaleDateString(undefined, { weekday: "long" }) + " at midnight";
  function drawArena(d) {
    const left = d.challenges_left;
    const ago = (t) => { const m = Math.round((Date.now() / 1000 - t) / 60); return m < 60 ? `${Math.max(1, m)}m ago` : m < 1440 ? `${Math.round(m / 60)}h ago` : `${Math.round(m / 1440)}d ago`; };
    $("arena-body").innerHTML = `
      <p class="arena-note">Fight any crawler's <b>ghost</b>: their real stats and gear, played by the System. Beat someone above you and you swap places.
        A win pays ${d.win_bookmarks} bookmarks. <b>${left} of ${d.daily_limit}</b> challenges left today.</p>
      <div class="arena-prize"><b>This week's prizes</b> (ends ${weekEnds(d.week_ends_at)}):
        <span>🏆 #1 gets a guaranteed <b class="r-epic">Epic</b> (sometimes Legendary), but only if they fight at least one duel this week.${d.ladder[0] && d.ladder[0].you && !d.you_fought_this_week ? " <b>That's you: fight once to qualify!</b>" : ""}</span>
        <span>⚔ Most duel wins this week gets a <b class="r-rare">Rare</b>.</span>
        ${d.last_week.champion || d.last_week.climber ? `<small>Last week: ${[d.last_week.champion && `🏆 ${esc(d.last_week.champion.toUpperCase())}`, d.last_week.climber && `⚔ ${esc(d.last_week.climber.toUpperCase())}`].filter(Boolean).join(" · ")}</small>` : ""}</div>
      <div class="ladder">${d.ladder.map((r) => `<div class="rung${r.you ? " you" : ""}">
          <span class="lrank">#${r.rank}</span>
          <span class="lart">${A.render(r.look, r.cls, { height: 64 })}</span>
          <div class="lwho"><div class="lname">${nameTag(r.username, r.worn)}</div>
            <div class="lcls">${A.CLASSES[r.cls].name} · Level ${r.level}</div>
            <div class="lstats"><span title="Health">❤ ${r.stats.hp}</span><span title="Attack">⚔ ${r.stats.atk}</span><span title="Defense">🛡 ${r.stats.def}</span><span class="lrec">${r.wins}W ${r.losses}L${r.week_wins ? ` · ${r.week_wins} this week` : ""}</span></div></div>
          ${r.you ? `<span class="lyou">You</span>` : `<button class="btn" data-duel="${esc(r.username)}" ${left ? "" : "disabled"}>Challenge</button>`}
        </div>`).join("")}</div>
      ${d.recent.length ? `<div class="section-label">Recent duels</div><div class="duel-log">${d.recent.map((x) =>
        `<div>${x.won ? `<b>${esc(x.challenger.toUpperCase())}</b> beat ${esc(x.defender.toUpperCase())}'s ghost` : `${esc(x.defender.toUpperCase())}'s ghost held off <b>${esc(x.challenger.toUpperCase())}</b>`}<small>${ago(x.at)}</small></div>`).join("")}</div>` : ""}
      ${d.champions.length ? `<div class="section-label">Arena Champions</div><div class="duel-log">${d.champions.map((c) =>
        `<div>🏆 <b>${esc(c.username.toUpperCase())}</b><small>${new Date(c.month + "-15").toLocaleDateString(undefined, { month: "long", year: "numeric" })}</small></div>`).join("")}</div>` : ""}`;
    $("arena-body").querySelectorAll("[data-duel]").forEach((b) => b.addEventListener("click", () => {
      if (!confirmTap("duel:" + b.dataset.duel, `Tap again to challenge ${b.dataset.duel.toUpperCase()}'s ghost (uses 1 of today's ${d.daily_limit}).`)) return;
      startDuel(b.dataset.duel);
    }));
  }
  async function startDuel(username) {
    try {
      const duel = await api(`/arena/duel/${encodeURIComponent(username)}`, { method: "POST" });
      show("dungeon");
      Dungeon.duel({ ...duel, username: me.username.toUpperCase() }, {
        onFinish: async (report) => {
          const res = await api(`/arena/duel/${duel.duel_id}/finish`, { method: "POST", body: report });
          me = { ...me, ...res.me };
          return res.result;
        },
        onDone: async () => { await pullNotices(); openArena(); showNotices(); },
      });
    } catch (e) { toast(e.message); }
  }
  $("arena-back").onclick = showHub;
  $("nav-arena").onclick = (e) => { e.preventDefault(); openArena(); };
  $("nav-party").onclick = (e) => { e.preventDefault(); openParty(); };
  $("my-badges").onclick = () => openMember(me.username);

  // ── the Wardrobe ─────────────────────────────────────────────────────
  let wardrobe = null, trying = null;  // trying = {kind, key} being previewed
  async function openWardrobe() {
    show("wardrobe"); trying = null;
    try { wardrobe = await api("/wardrobe"); drawWardrobe(); } catch (e) { toast(e.message); }
  }
  function drawWardrobe() {
    const w = wardrobe, worn = { ...w.worn };
    if (trying) worn[trying.kind] = trying.key;
    $("wardrobe-bm").textContent = `${w.bookmarks} bookmarks`;
    const title = worn.title ? w.items.title.find((t) => t.key === worn.title).name : "";
    $("wr-name").innerHTML = nameTag(me.username, worn) + (title ? `<div class="ctitle">${esc(title)}</div>` : "");
    const look = { ...me.look }; delete look.cape;
    if (worn.cape) look.cape = worn.cape;
    $("wr-fig").innerHTML = A.render(look, me.cls, { height: 190 });
    const detail = (kind, it) => kind === "plate" ? `<span class="swatch-dot" style="background:${PLATES[it.key][0]}"></span>`
      : kind === "pet" ? `<small>${A.CLASSES[it.cls].name} only${it.cls === w.cls ? "" : " (not your class)"}</small>` : "";
    $("wardrobe-body").innerHTML = Object.entries(w.kinds).map(([kind, label]) => `<div class="section-label">${label}</div>
      <div class="wr-items">${w.items[kind].map((it) => {
        const on = trying && trying.kind === kind && trying.key === it.key;
        return `<button class="wr-item${it.worn ? " worn" : ""}" data-kind="${kind}" data-key="${it.key}" aria-pressed="${on}">
          <strong>${kind === "plate" ? detail(kind, it) : ""}${esc(it.name)}</strong>${kind === "pet" ? detail(kind, it) : ""}
          <small>${it.worn ? "Wearing" : it.owned ? "Owned" : `${it.cost} ◆`}</small></button>`;
      }).join("")}</div>
      ${trying && trying.kind === kind ? wardrobeActions(kind) : ""}`).join("")
      + `<p class="store-note" style="margin-top:10px">Pet skins recolor your Beastmaster's beasts or your Necromancer's minions in every fight.</p>`;
    $("wardrobe-body").querySelectorAll(".wr-item").forEach((b) => b.addEventListener("click", () => {
      const same = trying && trying.kind === b.dataset.kind && trying.key === b.dataset.key;
      trying = same ? null : { kind: b.dataset.kind, key: b.dataset.key };
      drawWardrobe();
    }));
    $("wardrobe-body").querySelectorAll("[data-wr]").forEach((b) => b.addEventListener("click", () => wardrobeAct(b.dataset.wr)));
  }
  function wardrobeActions(kind) {
    const it = wardrobe.items[kind].find((x) => x.key === trying.key);
    const btn = (act, label, cls = "") => `<button class="btn ${cls}" data-wr="${act}">${label}</button>`;
    return `<div class="wr-actions">${it.worn ? btn("off", "Take it off", "ghost") : it.owned ? btn("wear", "Wear it")
      : btn("buy", `Buy for ${it.cost} ◆`) }</div>`;
  }
  async function wardrobeAct(act) {
    const { kind, key } = trying;
    const it = wardrobe.items[kind].find((x) => x.key === key);
    if (act === "buy" && !confirmTap(`wr-${kind}-${key}`, `Tap again to buy ${it.name} for ${it.cost} bookmarks.`)) return;
    try {
      const res = await api(`/wardrobe/${kind}/${key}/${act}`, { method: "POST" });
      wardrobe = res.wardrobe; me = { ...me, ...res.me }; trying = null; drawWardrobe();
      toast(act === "buy" ? `${it.name}: yours, and you're wearing it.` : act === "wear" ? `Wearing ${it.name}.` : "Taken off.");
      if (act === "buy") badgesNow();
    } catch (e) { toast(e.message); }
  }
  $("open-wardrobe").onclick = openWardrobe;
  $("wardrobe-back").onclick = showHub;

  // ── the Forge (permanent upgrades; was "the Bindery") ──────────────────────────────────────────────────────
  async function openBindery() {
    show("bindery");
    try { drawBindery(await api("/bindery")); } catch (e) { toast(e.message); }
  }
  function drawBindery(d) {
    $("bindery-bm").textContent = `${d.bookmarks} bookmarks`;
    const pips = (r, m) => `<span class="pips">${Array.from({ length: m }, (_, i) => `<i class="${i < r ? "on" : ""}"></i>`).join("")}</span>`;
    const row = (key, name, text, rank, max, cost, full, needs) => `<div class="upgrade"><div><strong>${name}</strong>${pips(rank, max)}<small>${text}</small></div>
      <button class="btn" data-buy="${key}" ${cost === null || full || needs || d.bookmarks < cost ? "disabled" : ""}>${cost === null ? "Maxed" : full ? "Full for your class" : needs ? `Level ${needs}` : `${cost} ◆`}</button></div>`;
    $("bindery-body").innerHTML = row("bag", "Bigger Bag", `Bag holds ${d.bag.capacity} items${d.bag.cost !== null ? ` → ${d.bag.next_capacity}` : ""}`, d.bag.rank, d.bag.max, d.bag.cost)
      + d.upgrades.map((u) => row(u.key, u.name, u.text, u.rank, u.max, u.cost, u.full_for_class, u.needs_level)).join("");
    $("bindery-body").querySelectorAll("[data-buy]").forEach((b) => b.addEventListener("click", async () => {
      try {
        const res = await api(`/bindery/${b.dataset.buy}`, { method: "POST" });
        me = { ...me, ...res.me }; drawBindery(res); toast("Upgraded."); badgesNow();
      } catch (e) { toast(e.message); }
    }));
  }
  $("bindery-back").onclick = showHub;

  // ── the System Store ─────────────────────────────────────────────────
  async function openStore() {
    show("store");
    try { drawStore(await api("/store")); } catch (e) { toast(e.message); }
  }
  // What a store piece would change compared with what you wear in its slot.
  function vsWorn(it) {
    const worn = (me.gear || {})[it.slot];
    const diff = STAT_NAMES.map(([k, label]) => [label, (it[k] || 0) - ((worn && worn[k]) || 0)]).filter(([, d]) => d);
    return `<div class="vs-worn">${worn ? "vs. yours" : "Empty slot"}: ${diff.length
      ? diff.map(([label, d]) => `<span class="${d > 0 ? "up" : "down"}">${d > 0 ? "+" : "−"}${Math.abs(d)} ${label}</span>`).join(", ") : "same stats"}</div>`;
  }
  function drawStore(d) {
    $("store-bm").textContent = `${d.bookmarks} bookmarks`;
    if (!d.unlocked) {
      $("store-body").innerHTML = `<div class="store-lock"><div class="big">${d.clears} / ${d.unlock_at}</div>
        <p>The System Store opens after ${d.unlock_at} cleared dungeons. Store-only gear, Mystery Crates, and supplies for the road.</p>
        <div class="xpbar"><i style="width:${Math.min(100, (100 * d.clears) / d.unlock_at)}%"></i></div></div>`;
      return;
    }
    const hrs = Math.max(0, (d.restocks_at * 1000 - Date.now()) / 36e5);
    const restock = hrs < 1 ? "in under an hour" : `in ${Math.floor(hrs)} hour${Math.floor(hrs) === 1 ? "" : "s"}`;
    const stat = (it) => [["ATK", it.atk], ["DEF", it.def], ["HP", it.hp]].filter(([, v]) => v).map(([k, v]) => `<span>${k} +${v}</span>`).join("");
    const can = (cost) => d.bookmarks >= cost;
    $("store-body").innerHTML = `
      <div class="section-label">Today's gear</div>
      <p class="store-note">Store-only, shared by the whole party: once someone buys a piece, it's gone. Restocks at midnight (${restock}).</p>
      <div class="items">${d.stock.map((o) => `<div class="offer${o.sold ? " sold" : ""}" style="--rc:${RC[o.item.rarity]}">
          <div class="icon">${o.item.icon ? `<img src="${esc(o.item.icon)}" alt="">` : ""}</div>
          <div style="min-width:0"><div class="rar">${lv(o.item)}${o.item.rarity} ${o.item.slot}${o.upgrade && !o.sold ? ' <span class="up-tag">▲ Upgrade</span>' : ""}</div><div class="iname">${esc(o.item.name)}</div><div class="istats">${stat(o.item)}</div>
            ${o.sold ? "" : vsWorn(o.item)}
            ${o.sold ? `<div class="sold-by">Bought by ${o.sold.you ? "you" : esc(o.sold.by.toUpperCase())}</div>` : ""}</div>
          <button class="btn" data-stock="${o.idx}" ${o.sold || !can(o.price) ? "disabled" : ""}>${o.sold ? "Sold" : `${o.price} ◆`}</button></div>`).join("")}</div>
      <div class="section-label">Mystery Crate</div>
      <div class="offer"><div class="icon"><span class="crate-art">?</span></div><div><div class="iname">One random piece of gear</div><div class="istats">Any rarity. Usually disappointing. Occasionally legendary.</div></div>
        <button class="btn" data-crate="1" ${can(d.crate_cost) ? "" : "disabled"}>${d.crate_cost} ◆</button></div>
      <div class="section-label">Supplies · carrying ${d.carry}/${d.carry_max}</div>
      <p class="store-note">Packed automatically when you enter a dungeon. Anything you don't use comes back.</p>
      <div class="items">${d.supplies.map((sp) => `<div class="offer"><div class="icon"><span class="crate-art" style="font-size:22px">${sp.owned}</span></div>
          <div><div class="iname">${sp.name}</div><div class="istats">${sp.text}</div></div>
          <button class="btn" data-supply="${sp.key}" ${d.carry >= d.carry_max || !can(sp.cost) ? "disabled" : ""}>${sp.cost} ◆</button></div>`).join("")}</div>`;
    $("store-body").querySelectorAll("[data-stock],[data-crate],[data-supply]").forEach((b) => b.addEventListener("click", async () => {
      const path = b.dataset.stock !== undefined ? `/store/stock/${b.dataset.stock}` : b.dataset.crate ? "/store/crate" : `/store/supply/${b.dataset.supply}`;
      const key = "store" + path;
      if ((b.dataset.stock !== undefined || b.dataset.crate) && !confirmTap(key, "Tap again to buy.")) return;
      try {
        const res = await api(path, { method: "POST" });
        me = { ...me, ...res.me }; drawStore(res.store);
        if (res.got) toast(`${res.got.rarity}: ${res.got.name}. ${res.got.placed === "equipped" ? "Equipped!" : res.got.placed === "bag" ? "In your bag." : "Bag full: sort it in your bag."}`);
        else toast("Packed.");
        badgesNow();
      } catch (e) { toast(e.message); }
    }));
  }
  $("store-back").onclick = showHub;
  $("open-store").onclick = openStore;
  $("open-bindery").onclick = openBindery;
  setInterval(() => { if (!$("hub").hidden) tick(); }, 30000);

  // ── routing ──────────────────────────────────────────────────────────
  function route() {
    if (!me) return showTitle();
    if (!me.look) return openBuilder();
    if (!me.cls) return openClassPick();
    showHub();
    if (location.hash === "#party") { history.replaceState(null, "", "/"); openParty(); }  // linked from the library pages
    if (location.hash === "#arena") { history.replaceState(null, "", "/"); openArena(); }
  }
  $("logout").onclick = async (e) => { e.preventDefault(); await api("/logout", { method: "POST" }).catch(() => {}); me = null; showTitle(); };
  $("edit-look").onclick = openBuilder;
  $("edit-class").onclick = openClassPick;

  drawRansom();
  api("/me").then((m) => { me = m; noticeQueue.push(...(m.notices || [])); route(); }).catch(() => showTitle());
})();
