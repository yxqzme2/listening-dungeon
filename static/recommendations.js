const statusEl = document.getElementById('rec-status');
const listEl = document.getElementById('rec-list');
const selectEl = document.getElementById('user-select');
const tagPanel = document.getElementById('tag-panel');
const seriesDatalist = document.getElementById('series-datalist');
const tagSeriesInput = document.getElementById('tag-series-input');
const tagValueInput = document.getElementById('tag-value-input');
const tagSubmitBtn = document.getElementById('tag-submit-btn');
const tagFormStatus = document.getElementById('tag-form-status');
const tagChecklistEl = document.getElementById('tag-checklist');
const tagClearBtn = document.getElementById('tag-clear-btn');
const popoverEl = document.getElementById('cover-popover');
const popoverImg = document.getElementById('cover-popover-img');
const popoverTitle = document.getElementById('cover-popover-title');
const popoverDesc = document.getElementById('cover-popover-desc');
const tagPopoverEl = document.getElementById('tag-popover');
const tagPopoverTitle = document.getElementById('tag-popover-title');
const tagPopoverDesc = document.getElementById('tag-popover-desc');
const freshToggle = document.getElementById('fresh-toggle-input');
const tagSidebarEl = document.getElementById('tag-sidebar');
const tagSidebarToggle = document.getElementById('tag-sidebar-toggle');
const tagSidebarClose = document.getElementById('tag-sidebar-close');
const tagSidebarBackdrop = document.getElementById('tag-sidebar-backdrop');
const tasteProfileTotal = document.getElementById('taste-profile-total');
const tasteProfileTotalWrap = document.getElementById('taste-profile-total-wrap');
const tasteProfileTiers = document.getElementById('taste-profile-tiers');
const tasteProfileStatus = document.getElementById('taste-profile-status');
const tasteProfileBars = document.getElementById('taste-profile-bars');
const playlistDialog = document.getElementById('playlist-dialog');
const playlistDialogTitle = document.getElementById('playlist-dialog-title');
const playlistDialogSummary = document.getElementById('playlist-dialog-summary');
const playlistChoiceWrap = document.getElementById('playlist-choice-wrap');
const playlistChoice = document.getElementById('playlist-choice');
const playlistPin = document.getElementById('playlist-pin');
const playlistDialogStatus = document.getElementById('playlist-dialog-status');
const playlistConfirm = document.getElementById('playlist-confirm');
const playlistCancel = document.getElementById('playlist-cancel');
const playlistDialogClose = document.getElementById('playlist-dialog-close');

const checkedBoostTags = new Set();
let recsByKey = {};
let tagDefinitions = {};
let playlistDialogContext = null;

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  })[char]);
}

function setStatus(msg, isError) {
  statusEl.textContent = msg || '';
  statusEl.classList.toggle('error', !!isError);
}

function currentUserId() {
  return selectEl.value || '';
}

async function loadUsers() {
  try {
    const resp = await fetch('/awards/api/usernames');
    const data = await resp.json();
    const users = Array.isArray(data.users) ? data.users : [];
    if (!users.length) {
      selectEl.innerHTML = '<option value="">No users found</option>';
      return;
    }
    selectEl.innerHTML = users
      .map(u => `<option value="${u.id}">${u.username}</option>`)
      .join('');
    tagPanel.style.display = 'block';
    loadUserView();
  } catch (e) {
    selectEl.innerHTML = '<option value="">Failed to load users</option>';
    setStatus('Could not load the user list.', true);
  }
}

function renderTasteProfile(data) {
  const traits = Array.isArray(data.traits) ? data.traits : [];
  const likedCount = Number(data.liked_series_count) || 0;
  const tierCounts = data.tier_counts || {};

  tasteProfileTotal.textContent = likedCount;
  tasteProfileTotalWrap.setAttribute('aria-label', `${likedCount} liked series`);
  tasteProfileTiers.replaceChildren();
  ['S', 'A', 'B'].forEach((tier) => {
    const item = document.createElement('span');
    item.textContent = `${tier} ${Number(tierCounts[tier]) || 0}`;
    tasteProfileTiers.appendChild(item);
  });

  if (data.reason === 'no_tier_list') {
    tasteProfileStatus.textContent = 'No saved Tier List yet.';
    tasteProfileBars.replaceChildren();
    return;
  }
  if (!traits.length) {
    tasteProfileStatus.textContent = likedCount
      ? 'No tag data found for liked series yet.'
      : 'Rate a series B or better to build this profile.';
    tasteProfileBars.replaceChildren();
    return;
  }

  tasteProfileStatus.textContent = '';
  tasteProfileBars.replaceChildren();
  traits.forEach((trait) => {
    const count = Number(trait.count) || 0;
    const percentage = Math.max(0, Math.min(100, Number(trait.percentage) || 0));
    const row = document.createElement('div');
    row.className = 'taste-row';
    row.title = trait.description || '';
    row.setAttribute('aria-label', `${trait.tag}: ${count} series`);

    const label = document.createElement('div');
    label.className = 'taste-row-label';
    label.textContent = trait.tag;
    const value = document.createElement('div');
    value.className = 'taste-row-value';
    value.textContent = count;
    const track = document.createElement('div');
    track.className = 'taste-row-track';
    const bar = document.createElement('div');
    bar.className = 'taste-row-bar';
    bar.style.setProperty('--taste-level', `${percentage}%`);
    track.appendChild(bar);
    row.append(label, value, track);
    tasteProfileBars.appendChild(row);
  });
}

async function loadTasteProfile() {
  const uid = currentUserId();
  if (!uid) return;
  tasteProfileStatus.textContent = 'Loading profile…';
  tasteProfileBars.replaceChildren();
  try {
    const resp = await fetch(`/awards/api/taste-profile/${encodeURIComponent(uid)}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    renderTasteProfile(await resp.json());
  } catch (e) {
    tasteProfileStatus.textContent = 'Could not load this profile.';
    tasteProfileTotal.textContent = '0';
    tasteProfileTiers.replaceChildren();
  }
}

function loadUserView() {
  loadRecommendations();
  loadTasteProfile();
}

async function loadSeriesDatalist() {
  try {
    const resp = await fetch('/awards/api/series-names');
    const data = await resp.json();
    const names = Array.isArray(data.series) ? data.series : [];
    seriesDatalist.innerHTML = names.map(n => `<option value="${n.replace(/"/g, '&quot;')}">`).join('');
  } catch (e) {
    // Non-critical: the tag form still works with free typing, just no autocomplete.
  }
}

async function loadRecommendations() {
  const uid = currentUserId();
  if (!uid) return;
  listEl.innerHTML = '';
  setStatus('Loading recommendations…');
  const fresh = freshToggle.checked;
  if (fresh && !checkedBoostTags.size) {
    listEl.innerHTML = '';
    setStatus('Check at least one tag on the right to discover something new.');
    return;
  }

  try {
    const params = new URLSearchParams();
    if (checkedBoostTags.size) params.set('boost', Array.from(checkedBoostTags).join(','));
    if (fresh) params.set('fresh', '1');
    const qs = params.toString() ? `?${params.toString()}` : '';
    const resp = await fetch(`/awards/api/recommendations/${encodeURIComponent(uid)}${qs}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    const recs = Array.isArray(data.recommendations) ? data.recommendations : [];

    if (data.reason === 'no_tier_list') {
      setStatus('This user has no saved Tier List yet. Rate some series first, or check "Start from scratch" to browse by tag instead.');
      return;
    }
    if (!recs.length) {
      setStatus(fresh
        ? 'No series found with all the checked tags. Try unchecking a few.'
        : 'No recommendations yet. Not enough tag data overlaps with this Tier List.');
      return;
    }

    setStatus('');
    recsByKey = {};
    recs.forEach(r => { recsByKey[r.series_key] = r; });

    listEl.innerHTML = recs.map((r, i) => {
      const boosted = new Set(r.boosted_tags || []);
      const seriesName = escapeHtml(r.series_name);
      const seriesKey = escapeHtml(r.series_key);
      const bookCount = Math.max(0, Number(r.book_count) || 0);
      const bookCountLabel = `${bookCount} ${bookCount === 1 ? 'book' : 'books'}`;
      return `
      <div class="rec-card">
        <div class="rec-rank">#${i + 1}</div>
        <img class="rec-cover" src="${escapeHtml(r.cover_url)}" alt="" loading="lazy"
             data-series-key="${seriesKey}"
             onerror="this.style.visibility='hidden'">
        <div class="rec-body">
          <div class="rec-series-line">
            <div class="rec-series-name">${seriesName}</div>
            <div class="rec-book-count" aria-label="${bookCountLabel} in series">${bookCountLabel}</div>
          </div>
          <div class="rec-tags">
            ${r.matching_tags.map(t => `<span class="rec-tag-chip${boosted.has(t) ? ' boosted' : ''}">${escapeHtml(t)}</span>`).join('')}
          </div>
        </div>
        <div class="rec-score">match score ${escapeHtml(r.score)}</div>
        <button class="rec-playlist-add" type="button" data-series-key="${seriesKey}"
                aria-label="Add ${seriesName} to playlist" title="Add entire series to playlist">+</button>
      </div>
    `;
    }).join('');
  } catch (e) {
    setStatus('Could not load recommendations: ' + e.message, true);
  }
}

async function loadTagChecklist() {
  try {
    const resp = await fetch('/awards/api/tags/all');
    const data = await resp.json();
    const tags = Array.isArray(data.tags) ? data.tags : [];
    if (!tags.length) {
      tagChecklistEl.innerHTML = '<div class="tag-sidebar-hint">No tags yet. Run the admin tag backfill first.</div>';
      return;
    }
    tagDefinitions = {};
    tags.forEach(t => { tagDefinitions[t.tag] = t.description; });

    tagChecklistEl.innerHTML = tags.map(t => `
      <label data-tag="${t.tag}">
        <input type="checkbox" value="${t.tag}">
        <span>${t.tag}</span>
      </label>
    `).join('');

    tagChecklistEl.addEventListener('change', (e) => {
      if (e.target.tagName !== 'INPUT') return;
      if (e.target.checked) checkedBoostTags.add(e.target.value);
      else checkedBoostTags.delete(e.target.value);
      loadRecommendations();
    });

    tagChecklistEl.addEventListener('mouseover', (e) => {
      const label = e.target.closest('label[data-tag]');
      if (label) showTagPopover(label);
    });
    tagChecklistEl.addEventListener('mouseout', (e) => {
      const label = e.target.closest('label[data-tag]');
      if (label) hideTagPopover();
    });
  } catch (e) {
    tagChecklistEl.innerHTML = '<div class="tag-sidebar-hint">Could not load tags.</div>';
  }
}

function showTagPopover(label) {
  const tag = label.dataset.tag;
  tagPopoverTitle.textContent = tag;
  tagPopoverDesc.textContent = tagDefinitions[tag] || 'No description available.';
  tagPopoverEl.style.display = 'block';

  const rect = label.getBoundingClientRect();
  tagPopoverEl.style.visibility = 'hidden';
  tagPopoverEl.style.display = 'block';
  const popRect = tagPopoverEl.getBoundingClientRect();
  let left = rect.left - popRect.width - 14;
  if (left < 10) left = rect.left; // not enough room to the left either; overlap slightly rather than vanish
  let top = rect.top - 4;
  if (top + popRect.height > window.innerHeight - 10) top = window.innerHeight - popRect.height - 10;
  if (top < 10) top = 10;
  tagPopoverEl.style.left = left + 'px';
  tagPopoverEl.style.top = top + 'px';
  tagPopoverEl.style.visibility = 'visible';
}

function hideTagPopover() {
  tagPopoverEl.style.display = 'none';
}

freshToggle.addEventListener('change', loadRecommendations);

function showCoverPopover(coverImg) {
  const key = coverImg.dataset.seriesKey;
  const r = recsByKey[key];
  if (!r) return;

  popoverImg.src = r.cover_url;
  popoverTitle.textContent = r.series_name;
  popoverDesc.textContent = r.description && r.description.trim()
    ? r.description.trim()
    : 'No description available yet for this series.';

  popoverEl.style.display = 'flex';
  positionPopover(coverImg);
}

function positionPopover(coverImg) {
  const rect = coverImg.getBoundingClientRect();
  const popRect = popoverEl.getBoundingClientRect();
  let left = rect.right + 14;
  let top = rect.top;

  // Flip to the left of the cover if there's not enough room on the right
  // (the fixed tag sidebar occupies the far right, so this matters here
  // more than on a typical page).
  if (left + popRect.width > window.innerWidth - 20) {
    left = rect.left - popRect.width - 14;
  }
  if (left < 10) left = 10;

  // Clamp vertically so it never runs off the bottom of the viewport.
  if (top + popRect.height > window.innerHeight - 10) {
    top = window.innerHeight - popRect.height - 10;
  }
  if (top < 10) top = 10;

  popoverEl.style.left = left + 'px';
  popoverEl.style.top = top + 'px';
}

function hideCoverPopover() {
  popoverEl.style.display = 'none';
}

listEl.addEventListener('mouseenter', (e) => {
  if (e.target.classList && e.target.classList.contains('rec-cover')) {
    showCoverPopover(e.target);
  }
}, true);

listEl.addEventListener('mouseleave', (e) => {
  if (e.target.classList && e.target.classList.contains('rec-cover')) {
    hideCoverPopover();
  }
}, true);

async function openPlaylistDialog(button) {
  const userId = currentUserId();
  const seriesKey = button.dataset.seriesKey || '';
  const recommendation = recsByKey[seriesKey];
  if (!userId || !recommendation) return;

  button.disabled = true;
  button.setAttribute('aria-busy', 'true');
  try {
    const response = await fetch(`/awards/api/playlists/${encodeURIComponent(userId)}`);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    if (currentUserId() !== userId) return;

    const playlists = Array.isArray(data.playlists) ? data.playlists : [];
    if (!playlists.length) {
      setStatus('No existing playlist found for this listener. Create one in Audiobookshelf first.', true);
      return;
    }

    playlistDialogContext = { userId, seriesKey, recommendation, button };
    playlistChoice.replaceChildren(...playlists.map((playlist) => {
      const option = document.createElement('option');
      option.value = playlist.id;
      option.textContent = playlist.name;
      return option;
    }));
    playlistChoiceWrap.hidden = playlists.length === 1;
    const bookCount = Number(recommendation.book_count) || 0;
    const bookLabel = bookCount === 1 ? 'book' : 'books';
    const destination = playlists.length === 1 ? ` to “${playlists[0].name}”` : '';
    playlistDialogTitle.textContent = recommendation.series_name;
    playlistDialogSummary.textContent = `Add all ${bookCount} ${bookLabel}${destination}. Books already there will be skipped.`;
    playlistPin.value = '';
    playlistDialogStatus.textContent = '';
    playlistDialogStatus.className = 'playlist-dialog-status';
    playlistConfirm.disabled = false;
    playlistDialog.showModal();
    playlistPin.focus();
  } catch (error) {
    setStatus(`Could not load this listener's playlists: ${error.message}`, true);
  } finally {
    button.disabled = false;
    button.removeAttribute('aria-busy');
  }
}

function closePlaylistDialog() {
  if (playlistDialog.open) playlistDialog.close();
  playlistPin.value = '';
  playlistDialogContext = null;
}

async function addSeriesToPlaylist() {
  const context = playlistDialogContext;
  const pin = playlistPin.value.trim();
  const playlistId = playlistChoice.value;
  if (!context || !playlistId) return;
  if (!pin) {
    playlistDialogStatus.textContent = 'Enter this listener’s profile PIN.';
    playlistPin.focus();
    return;
  }

  playlistConfirm.disabled = true;
  playlistCancel.disabled = true;
  playlistDialogStatus.className = 'playlist-dialog-status';
  playlistDialogStatus.textContent = 'Adding books…';
  try {
    const response = await fetch(`/awards/api/playlists/${encodeURIComponent(context.userId)}/add-series`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        pin,
        playlist_id: playlistId,
        series_key: context.seriesKey,
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);

    const added = Number(data.added) || 0;
    const alreadyPresent = Number(data.alreadyPresent) || 0;
    const failed = Number(data.failed) || 0;
    const playlistName = data.playlist?.name || 'the playlist';
    let message;
    if (failed) {
      message = `Added ${added} books to ${playlistName}. ${failed} could not be added.`;
      playlistDialogStatus.textContent = message;
      setStatus(message, true);
    } else if (!added && alreadyPresent) {
      message = `Every book in this series is already in ${playlistName}.`;
      playlistDialogStatus.classList.add('ok');
      playlistDialogStatus.textContent = message;
      setStatus(message, false);
    } else {
      message = `Added ${added} ${added === 1 ? 'book' : 'books'} to ${playlistName}.`;
      playlistDialogStatus.classList.add('ok');
      playlistDialogStatus.textContent = message;
      setStatus(message, false);
    }
    if (added || alreadyPresent) {
      context.button.textContent = '✓';
      context.button.classList.add('added');
      context.button.title = `Series added to ${playlistName}`;
      context.button.setAttribute('aria-label', `Series added to ${playlistName}`);
    }
    if (!failed) window.setTimeout(closePlaylistDialog, 700);
  } catch (error) {
    playlistDialogStatus.textContent = error.message;
    playlistPin.select();
  } finally {
    playlistConfirm.disabled = false;
    playlistCancel.disabled = false;
  }
}

listEl.addEventListener('click', (event) => {
  const button = event.target.closest('.rec-playlist-add');
  if (button) openPlaylistDialog(button);
});
playlistConfirm.addEventListener('click', addSeriesToPlaylist);
playlistCancel.addEventListener('click', closePlaylistDialog);
playlistDialogClose.addEventListener('click', closePlaylistDialog);
playlistPin.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') addSeriesToPlaylist();
});
playlistDialog.addEventListener('click', (event) => {
  if (event.target === playlistDialog) closePlaylistDialog();
});

tagClearBtn.addEventListener('click', () => {
  checkedBoostTags.clear();
  tagChecklistEl.querySelectorAll('input[type="checkbox"]').forEach(cb => cb.checked = false);
  loadRecommendations();
});

async function submitTag() {
  const uid = currentUserId();
  const seriesName = tagSeriesInput.value.trim();
  const tag = tagValueInput.value.trim();
  tagFormStatus.className = '';
  if (!uid || !seriesName || !tag) {
    tagFormStatus.textContent = 'Pick a user, a series, and a tag.';
    tagFormStatus.className = 'error';
    return;
  }
  tagSubmitBtn.disabled = true;
  try {
    const resp = await fetch('/awards/api/series-tags', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: uid, series_name: seriesName, tag }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      tagFormStatus.textContent = data.detail || `Could not add tag (HTTP ${resp.status}).`;
      tagFormStatus.className = 'error';
      return;
    }
    tagFormStatus.textContent = data.already_existed
      ? 'You already tagged this series with that tag.'
      : `Tagged "${seriesName}" with "${tag}".`;
    tagFormStatus.className = 'ok';
    tagValueInput.value = '';
    loadUserView();
  } catch (e) {
    tagFormStatus.textContent = 'Network error: ' + e.message;
    tagFormStatus.className = 'error';
  } finally {
    tagSubmitBtn.disabled = false;
  }
}

selectEl.addEventListener('change', loadUserView);
tagSubmitBtn.addEventListener('click', submitTag);

function openTagSidebar() {
  tagSidebarEl.classList.add('open');
  tagSidebarBackdrop.classList.add('show');
  tagSidebarToggle.setAttribute('aria-expanded', 'true');
}
function closeTagSidebar() {
  tagSidebarEl.classList.remove('open');
  tagSidebarBackdrop.classList.remove('show');
  tagSidebarToggle.setAttribute('aria-expanded', 'false');
}
tagSidebarToggle.addEventListener('click', openTagSidebar);
tagSidebarClose.addEventListener('click', closeTagSidebar);
tagSidebarBackdrop.addEventListener('click', closeTagSidebar);

loadUsers();
loadSeriesDatalist();
loadTagChecklist();
