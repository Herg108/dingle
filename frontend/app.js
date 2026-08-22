const playBtn = document.getElementById("playBtn");
const playIcon = document.getElementById("playIcon");
const guessInput = document.getElementById("guessInput");
const suggestionsEl = document.getElementById("suggestions");
const actionBtn = document.getElementById("actionBtn");
const revealSectionEl = document.getElementById("revealSection");
const revealEl = document.getElementById("reveal");
const revealCover = document.getElementById("revealCover");
const revealTitle = document.getElementById("revealTitle");
const revealArtist = document.getElementById("revealArtist");
const removeSongBtn = document.getElementById("removeSongBtn");
const retryAudioBtn = document.getElementById("retryAudioBtn");
const offsetValueEl = document.getElementById("offsetValue");
const offsetMinusBigBtn = document.getElementById("offsetMinusBig");
const offsetMinusBtn = document.getElementById("offsetMinus");
const offsetPlusBtn = document.getElementById("offsetPlus");
const offsetPlusBigBtn = document.getElementById("offsetPlusBig");
const previewFirstHintBtn = document.getElementById("previewFirstHintBtn");
const actionLabel = document.getElementById("actionLabel");
const guessRow = document.getElementById("guessRow");
const cardEl = document.querySelector(".card");
const progressFill = document.getElementById("progressFill");
const progressTicks = document.getElementById("progressTicks");
const progressTarget = document.getElementById("progressTarget");

let state = null;
let suggestionDebounce = null;
let snippetTarget = 0;
// Whether real playback has actually begun for this round yet. Tracked
// explicitly rather than inferred from currentTime: on a fresh round the
// playhead may still be sitting at 0 (priming can be dropped or throttled by
// the embed), and inferring "we're mid-clip, just resume" from that would
// play the song from its true beginning instead of from its start offset.
let snippetStarted = false;
// Where audio genuinely began for the current hint. A cold first press has to
// buffer, and YouTube resumes a little past where we seeked (e.g. 3.86 when
// the offset is 3.80) — anchoring the cutoff here instead of at the nominal
// offset keeps the hint the same length every press, warm or cold.
let snippetPlayFrom = null;
// After a hint finishes we rewind the playhead to the snippet start and leave
// it paused there ("parked"), so the next press is a plain resume with no
// backward seek. A backward seek costs ~300ms and lands ~55ms late, which is
// what made replays sound different from the first press. While parked, the
// progress bar is pinned to the hint length rather than following the
// rewound playhead. lastCutoff remembers where the hint actually ended, so a
// wrong guess can still continue onward instead of restarting.
let parkedAtStart = false;
let lastCutoff = null;
// True while the deliberate drain-out animation owns the fill, so the
// per-frame redraw doesn't fight it by writing a live width back.
let draining = false;
// Fires once the reveal's expand animation is done, to drop the overflow clip
// that would otherwise slice the cover art's pop-in.
let settleTimer = null;
let revealAt = 0;
let currentSongId = null;

let ytPlayer = null;
let playerReady = false;
let pendingVideoId = null;
let previewTimer = null;
let priming = false;

// Curation tools stay hidden unless the page is opened with ?test, so the
// public UI is just the player and the guess box (see style.css).
if (new URLSearchParams(location.search).has("test")) {
  document.body.classList.add("dev");
}

// ---------------------------------------------------------------------------
// Volume
//
// Deliberately implemented as setVolume(0) rather than the player's mute(),
// because the offset priming routine mutes and unmutes around its silent
// warm-up play — a real mute would be clobbered by that unMute(), whereas a
// volume of 0 survives it untouched.
// ---------------------------------------------------------------------------
const VOLUME_KEY = "dingle.volume";
const volumeBtn = document.getElementById("volumeBtn");
const volumeIcon = document.getElementById("volumeIcon");
const volumeSlider = document.getElementById("volumeSlider");

let volume = loadSavedVolume();
let volumeBeforeMute = volume || 100; // what the speaker toggle restores to

function loadSavedVolume() {
  // Guard the empty cases explicitly: getItem() returns null when nothing has
  // been stored, and Number(null) is 0 — which is a perfectly valid volume, so
  // a plain range check would hand a first-time visitor a silent game.
  const raw = localStorage.getItem(VOLUME_KEY);
  if (raw === null || raw === "") return 100;
  const saved = Number(raw);
  return Number.isFinite(saved) && saved >= 0 && saved <= 100 ? saved : 100;
}

function applyVolume() {
  if (ytPlayer && playerReady && ytPlayer.setVolume) ytPlayer.setVolume(volume);
  volumeSlider.value = String(volume);
  volumeSlider.style.setProperty("--vol", `${volume}%`);
  // 0 = slashed, 1 = one wave, 2 = both. The classes drive the SVG rather than
  // swapping glyphs, so the waves can animate in and out as the slider moves.
  const level = volume === 0 ? 0 : volume <= 50 ? 1 : 2;
  volumeIcon.classList.remove("level-0", "level-1", "level-2");
  volumeIcon.classList.add(`level-${level}`);
  volumeBtn.setAttribute("aria-label", volume === 0 ? "Unmute" : "Mute");
  try {
    localStorage.setItem(VOLUME_KEY, String(volume));
  } catch {
    /* private mode / storage full — volume just won't persist */
  }
}

function setVolume(next) {
  volume = Math.max(0, Math.min(100, Math.round(next)));
  applyVolume();
}

volumeSlider.addEventListener("input", () => setVolume(Number(volumeSlider.value)));

volumeBtn.addEventListener("click", () => {
  if (volume > 0) {
    volumeBeforeMute = volume;
    setVolume(0);
  } else {
    setVolume(volumeBeforeMute || 100);
  }
});

applyVolume(); // paint the saved level right away, long before the player exists

// ---------------------------------------------------------------------------
// Song filters (era / genre)
//
// A player-side preference, deliberately separate from the ✕ curation tool:
// filters only narrow what *this* browser is served and are reversible at any
// time, whereas removing takes a song out of the pool for everyone. Stored in
// localStorage so a chosen mix survives a reload.
// ---------------------------------------------------------------------------
const FILTER_KEY = "dingle.filters";
const filtersBtn = document.getElementById("filtersBtn");
const filtersCountEl = document.getElementById("filtersCount");
const filterPanel = document.getElementById("filterPanel");
const eraChipsEl = document.getElementById("eraChips");
const genreChipsEl = document.getElementById("genreChips");
const filterSummaryEl = document.getElementById("filterSummary");
const filterNoteEl = document.getElementById("filterNote");

// null = "not yet loaded"; a Set = the ids currently switched on.
let allEras = [];
let allGenres = [];
let selectedEras = new Set();
let selectedGenres = new Set();

function loadSavedFilters() {
  try {
    const raw = JSON.parse(localStorage.getItem(FILTER_KEY) || "{}");
    return {
      eras: Array.isArray(raw.eras) ? raw.eras : null,
      genres: Array.isArray(raw.genres) ? raw.genres : null,
    };
  } catch {
    return { eras: null, genres: null };
  }
}

function saveFilters() {
  try {
    localStorage.setItem(FILTER_KEY, JSON.stringify({
      eras: [...selectedEras],
      genres: [...selectedGenres],
    }));
  } catch {
    /* private mode / storage full — filters just won't persist */
  }
}

// Everything selected means "no restriction", so send nothing at all rather
// than a list naming every option.
function filterQuery() {
  const params = new URLSearchParams();
  if (selectedEras.size && selectedEras.size < allEras.length) {
    params.set("eras", [...selectedEras].join(","));
  }
  if (selectedGenres.size && selectedGenres.size < allGenres.length) {
    params.set("genres", [...selectedGenres].join(","));
  }
  const q = params.toString();
  return q ? `?${q}` : "";
}

function isFiltering() {
  return (selectedEras.size && selectedEras.size < allEras.length) ||
         (selectedGenres.size && selectedGenres.size < allGenres.length);
}

function renderChips(container, options, selected, onToggle) {
  container.innerHTML = "";
  options.forEach((opt) => {
    const chip = document.createElement("button");
    chip.className = "chip" + (selected.has(opt.id) ? " on" : "");
    chip.textContent = opt.label || opt.id;
    chip.title = `${opt.count} song${opt.count === 1 ? "" : "s"}`;
    chip.addEventListener("click", () => onToggle(opt.id));
    container.appendChild(chip);
  });
}

function eraLabel(id) {
  return id === "1960s-70s" ? "60s–70s" : id.replace(/^(\d\d)(\d\ds)$/, "$2");
}

function renderFilters() {
  renderChips(
    eraChipsEl,
    allEras.map((e) => ({ ...e, label: eraLabel(e.id) })),
    selectedEras,
    (id) => toggleFilter(selectedEras, id, allEras),
  );
  renderChips(genreChipsEl, allGenres, selectedGenres, (id) =>
    toggleFilter(selectedGenres, id, allGenres));

  const filtering = isFiltering();
  filtersBtn.classList.toggle("active", !!filtering);
  filtersCountEl.classList.toggle("hidden", !filtering);
  refreshFilterSummary();
}

function toggleFilter(set, id, all) {
  if (set.has(id)) set.delete(id);
  else set.add(id);
  // Emptying an axis means "no preference here" rather than "nothing" — the
  // backend treats it the same way, so the game can never be filtered into
  // having no songs at all.
  if (set.size === 0) all.forEach((o) => set.add(o.id));
  saveFilters();
  renderFilters();
}

async function refreshFilterSummary() {
  try {
    const res = await fetch(`/api/filters${filterQuery()}`);
    const data = await res.json();
    allEras = data.eras;
    allGenres = data.genres;
    filterSummaryEl.textContent = `${data.matching} of ${data.total} songs`;
    filtersCountEl.textContent = data.matching;
    // A combination with no songs at all (say 60s K-Pop) still has to play
    // something, so the backend widens rather than failing — say so plainly
    // instead of letting it look like the filters were ignored.
    const impossible = isFiltering() && data.matching === 0;
    filterNoteEl.textContent = impossible
      ? "No songs match — showing the closest set instead"
      : "";
  } catch {
    filterSummaryEl.textContent = "";
  }
}

async function initFilters() {
  const res = await fetch("/api/filters");
  const data = await res.json();
  allEras = data.eras;
  allGenres = data.genres;

  const saved = loadSavedFilters();
  const validEras = new Set(allEras.map((e) => e.id));
  const validGenres = new Set(allGenres.map((g) => g.id));
  // Drop anything stale (a genre that no longer exists) and default to
  // everything on, which is the same as no filtering.
  selectedEras = new Set((saved.eras || [...validEras]).filter((e) => validEras.has(e)));
  selectedGenres = new Set((saved.genres || [...validGenres]).filter((g) => validGenres.has(g)));
  if (!selectedEras.size) selectedEras = new Set(validEras);
  if (!selectedGenres.size) selectedGenres = new Set(validGenres);

  renderFilters();
}

filtersBtn.addEventListener("click", () => {
  const open = filterPanel.classList.toggle("open");
  filtersBtn.setAttribute("aria-expanded", String(open));
});

document.querySelectorAll(".filter-all").forEach((btn) => {
  btn.addEventListener("click", () => {
    const group = btn.dataset.group;
    if (group === "era") allEras.forEach((o) => selectedEras.add(o.id));
    else allGenres.forEach((o) => selectedGenres.add(o.id));
    saveFilters();
    renderFilters();
  });
});

const RESET_BLANK_MS = 120; // a deliberate blank beat so replays feel like a real reset
// How long to wait after a +/- nudge before auditioning it, so a run of taps
// plays the value you land on instead of every value on the way there.
const OFFSET_PREVIEW_MS = 160;

// Loading covers both the round fetch and the offset-priming warm-up — the
// button shows a spinner instead of just going dim/disabled for that whole
// stretch, so it reads as "working" rather than "broken."
function setPlayLoading(loading) {
  playBtn.disabled = loading;
  playBtn.classList.toggle("loading", loading);
}

// A single button carries the round through three roles: Skip while guesses
// remain, Give up on the final one (where skipping ends the round anyway, so
// calling it "Skip" would undersell it), and Next song once it's over.
function actionState() {
  const over = !!state && state.gameOver;
  if (over) return { label: "Next song", cls: "primary-btn", over };
  const attemptsLeft = state ? state.maxAttempts - state.attemptsUsed : 0;
  return { label: attemptsLeft <= 1 ? "Give up" : "Skip", cls: "secondary-btn", over };
}

// Instant — only safe while the row is faded out, since it also rearranges
// the layout (guess field, width, order).
function applyActionState() {
  const s = actionState();
  actionLabel.textContent = s.label;
  actionBtn.className = s.cls;
  cardEl.classList.toggle("game-over", s.over);
}

// Skip → Give up: layout is unchanged, so just crossfade the word itself.
async function morphActionLabel() {
  const s = actionState();
  if (actionLabel.textContent === s.label) return;
  actionBtn.classList.add("label-swap");
  await new Promise((r) => setTimeout(r, 120));
  actionLabel.textContent = s.label;
  actionBtn.classList.remove("label-swap");
}

function isPlaying() {
  return !!ytPlayer && playerReady && ytPlayer.getPlayerState() === YT.PlayerState.PLAYING;
}

// The playhead keeps moving while the player is BUFFERING even though the
// state isn't PLAYING, so a cutoff that only runs while PLAYING is blind for
// as long as the buffer takes (~130ms on a resume). At the start of a clip
// that's harmless — the buffer happens nowhere near the cutoff. But resuming a
// pause taken just before the cutoff spends that entire blind window past it,
// which is audible. Gated on snippetStarted so it can't fire while a round is
// still being cued.
function isAdvancing() {
  if (!ytPlayer || !playerReady) return false;
  const st = ytPlayer.getPlayerState();
  return st === YT.PlayerState.PLAYING ||
    (st === YT.PlayerState.BUFFERING && snippetStarted);
}

function maxDuration() {
  return state ? Math.max(...state.durations) : 0;
}

function updateTargetIndicator() {
  const max = maxDuration();
  const pct = max ? Math.min((snippetTarget / max) * 100, 100) : 0;
  progressTarget.style.width = `${pct}%`;
}

function updateProgressFill() {
  if (draining) return; // the drain-out animation is driving the fill
  if (performance.now() < revealAt) {
    progressFill.style.width = "0%";
    progressFill.classList.remove("full");
    return;
  }
  const max = maxDuration();
  // Parked: the playhead is rewound to the start ready for a replay, but the
  // hint has been heard — show the hint length, not the rewound position.
  const elapsed = parkedAtStart && Number.isFinite(snippetTarget)
    ? snippetTarget
    : (ytPlayer ? Math.max(0, ytPlayer.getCurrentTime() - snippetBase()) : 0);
  const pct = max ? Math.min((elapsed / max) * 100, 100) : 0;
  progressFill.style.width = `${pct}%`;
  progressFill.classList.toggle("full", pct >= 100);
}

// The point the current hint is measured from. Both the cutoff and the
// progress bar must use this same anchor — measuring the bar from the nominal
// offset while cutting off from the real playback start makes the fill
// overshoot the tick marks by exactly the drift between them.
function snippetBase() {
  return snippetPlayFrom !== null ? snippetPlayFrom : (state ? state.startOffset : 0);
}

function snippetCutoffAt() {
  return snippetBase() + snippetTarget;
}

function enforceSnippetCutoff() {
  if (!isAdvancing()) return false;
  const now = ytPlayer.getCurrentTime();
  // First frame of real playback for this hint — anchor the cutoff here so a
  // cold, buffered start still gets its full duration instead of a clipped one.
  if (snippetPlayFrom === null) snippetPlayFrom = now;
  const cutoffAt = snippetCutoffAt();
  if (now >= cutoffAt) {
    ytPlayer.pauseVideo();
    // Rewind to the snippet start and park there, so a replay needs no seek.
    lastCutoff = cutoffAt;
    parkedAtStart = true;
    ytPlayer.seekTo(state ? state.startOffset : 0, true);
    return true;
  }
  return false;
}

function renderTicks() {
  progressTicks.innerHTML = "";
  const max = maxDuration();
  if (!max) return;
  state.durations.forEach((d) => {
    const pct = Math.min((d / max) * 100, 100);
    if (pct <= 0 || pct >= 100) return; // skip only the truly redundant start/end
    const tick = document.createElement("div");
    tick.className = "progress-tick";
    tick.style.left = `${pct}%`;
    progressTicks.appendChild(tick);
  });
}

// YouTube's player has no per-frame "timeupdate" event, so a single
// self-perpetuating loop drives both the cutoff check and the fill redraw.
function tick() {
  if (!priming && isAdvancing()) {
    enforceSnippetCutoff();
    updateProgressFill();
  }
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);

// The fill only needs to be redrawn once per frame, but the cutoff wants to be
// caught as close to the exact moment as possible: at 60fps a frame is ~16.7ms,
// which on a 0.2s hint is 8% of the whole clip, arriving at a random point in
// the frame every press. A separate fine-grained check keeps the end tight
// without redrawing anything.
setInterval(() => {
  if (!priming && isAdvancing()) enforceSnippetCutoff();
}, 4);

function onPlayerStateChange(event) {
  if (priming) return; // silent warm-up play/pause, not a real playback state
  if (event.data === YT.PlayerState.PLAYING) {
    playIcon.textContent = "⏸";
    playBtn.classList.add("playing");
    progressFill.classList.add("smooth"); // eases over any re-buffering stutter after a resume
  } else if (event.data === YT.PlayerState.PAUSED || event.data === YT.PlayerState.ENDED) {
    playIcon.textContent = "▶";
    playBtn.classList.remove("playing");
    updateProgressFill();
  }
}

window.onYouTubeIframeAPIReady = function () {
  ytPlayer = new YT.Player("ytPlayer", {
    height: "1",
    width: "1",
    playerVars: { controls: 0, disablekb: 1, modestbranding: 1, playsinline: 1 },
    events: {
      onReady: () => {
        playerReady = true;
        applyVolume(); // setVolume() only works once the player is ready
        if (pendingVideoId) {
          const videoId = pendingVideoId;
          pendingVideoId = null;
          ytPlayer.cueVideoById(videoId);
          primeOffset(state ? state.startOffset : 0).then(() => {
            if (state) setPlayLoading(false);
          });
          return;
        }
        // startRound() may have already finished (and left playBtn disabled
        // on purpose, since the player wasn't ready yet at that point) —
        // now that it genuinely is ready, let Play actually become clickable.
        if (state) setPlayLoading(false);
      },
      onStateChange: onPlayerStateChange,
    },
  });
};

// Bumped every time a new round starts, so an in-flight primeOffset() from
// the *previous* round can tell it's been superseded. This matters because a
// browser tab that gets backgrounded (user alt-tabs away mid-load) throttles
// its timers hard — the poll loop below can end up finishing seconds late,
// long after the user has moved on. Without this guard, that stale call
// would still land its final pause/seek/unmute on whatever the player is
// doing *now*, yanking real playback out from under the user.
let primeGeneration = 0;

// Move the playhead to the song's real start offset as soon as it's cued, so
// the region the hint plays from is buffered and the playhead is already in
// position before the user's first press. Purely a warm-up: playSnippet()
// seeks and settles again before anything actually plays, so this failing or
// being cut short costs nothing but a little buffering on that first press.
async function primeOffset(offset) {
  const myGeneration = primeGeneration;
  await waitUntilPlayable();
  offset = offset || 0;
  if (myGeneration !== primeGeneration) {
    return; // superseded by a newer round while we were waiting
  }
  // Independent of the main flow below: no matter what happens (an
  // exception, a stalled poll, a browser tab getting backgrounded mid-await),
  // `priming` must not get stuck true forever — that would silently disable
  // the snippet cutoff and progress bar for the rest of the session.
  const safety = setTimeout(() => {
    if (myGeneration === primeGeneration) priming = false;
  }, 2000);
  priming = true;
  try {
    // Muted throughout. Two reasons: seekTo() on a freshly cued player can make
    // YouTube start playing on its own, and the warm-up below plays on purpose
    // — neither should be audible.
    ytPlayer.mute();
    await seekAndSettle(offset, 600);
    if (myGeneration !== primeGeneration) return;

    // Actually play for a moment, then park. This is the part that makes the
    // first press feel like every other press: a player sitting in UNSTARTED
    // has to cold-start its media pipeline (~900ms before any sound), whereas
    // one resuming from PAUSED is effectively instant. Playing briefly here
    // pays that cost silently, up front, and leaves the player warm and
    // parked exactly where the hint begins.
    ytPlayer.playVideo();
    let warmed = false;
    for (let i = 0; i < 25; i++) {
      const st = ytPlayer.getPlayerState();
      if (st === YT.PlayerState.PLAYING) { warmed = true; break; }
      // Autoplay refused (no user gesture yet) parks in CUED and never budges;
      // don't burn the rest of the timer waiting for something that won't come.
      if (i >= 8 && st === YT.PlayerState.CUED) break;
      await new Promise((r) => setTimeout(r, 20));
      if (myGeneration !== primeGeneration) return;
    }
    if (warmed) {
      await new Promise((r) => setTimeout(r, 120)); // let it genuinely decode
      if (myGeneration !== primeGeneration) return;
    }

    // Park: stop, confirm stopped, then rewind to the offset so the next real
    // press is a plain resume from exactly the right spot.
    ytPlayer.pauseVideo();
    for (let i = 0; i < 25 && ytPlayer.getPlayerState() === YT.PlayerState.PLAYING; i++) {
      await new Promise((r) => setTimeout(r, 20));
      if (myGeneration !== primeGeneration) return;
    }
    if (myGeneration !== primeGeneration) return;
    await seekAndSettle(offset, 400);
    if (myGeneration !== primeGeneration) return;
    // Only ever unmute once it has genuinely stopped — unmuting while a play
    // command is still in flight is what used to leak an audible blip.
    ytPlayer.unMute();
  } finally {
    clearTimeout(safety);
    if (myGeneration === primeGeneration) priming = false;
  }
}

async function startRound() {
  // Invalidate any in-flight primeOffset() from the previous round (see the
  // comment on primeGeneration) — and don't wait for it to notice on its own;
  // reset the state it owns right now so a stale/throttled call can never
  // leave this fresh round blocked or muted.
  primeGeneration++;
  priming = false;
  if (playerReady) {
    ytPlayer.stopVideo();
    ytPlayer.unMute();
  }
  playIcon.textContent = "▶";
  playBtn.classList.remove("playing");
  // Disabled (not just logically ignored) so a click during this async gap
  // can't fire at all — prevents playSnippet() from ever running against the
  // previous round's now-stale state while this fetch is still in flight.
  setPlayLoading(true);
  actionBtn.disabled = true;
  guessInput.disabled = true;
  snippetTarget = 0;
  snippetStarted = false;
  snippetPlayFrom = null;
  parkedAtStart = false;
  lastCutoff = null;
  revealAt = 0;
  const res = await fetch(`/api/round/new${filterQuery()}`);
  const round = await res.json();
  state = {
    roundId: round.round_id,
    videoId: round.youtube_video_id,
    durations: round.snippet_durations,
    maxAttempts: round.max_attempts,
    startOffset: round.start_offset || 0,
    attemptsUsed: 0,
    gameOver: false,
  };

  guessInput.value = "";
  guessInput.disabled = false;
  actionBtn.disabled = false;
  // Rearrange back to the guessing layout while the row is still faded out
  // (from the Next click), then fade it in as "Skip".
  applyActionState();
  guessRow.classList.remove("swapping");

  if (playerReady) {
    ytPlayer.cueVideoById(state.videoId);
    // Keep Play disabled (spinner showing) until the offset warm-up finishes
    // — otherwise a real click could land mid-priming and race it for the
    // same player.
    setPlayLoading(true);
    primeOffset(state.startOffset).then(() => {
      setPlayLoading(false);
    });
  } else {
    pendingVideoId = state.videoId;
    // Player isn't ready yet at all — the onReady handler cues, primes, and
    // enables Play once it genuinely is (see onYouTubeIframeAPIReady above).
    setPlayLoading(true);
  }
  clearTimeout(settleTimer);
  revealSectionEl.classList.remove("expanded", "settled");
  suggestionsEl.classList.add("hidden");
  // Drop the drain animation and hand the fill back to the live redraw. It's
  // already at 0% by now, so clearing the class can't cause a visible jump.
  draining = false;
  progressFill.classList.remove("draining", "smooth", "full");
  progressFill.style.width = "0%";
  progressTarget.style.width = "0%";
  renderTicks();
}

// cueVideoById() returns before the video has actually finished loading, so a
// playVideo() call that lands too soon after can get silently dropped —
// wait for a real ready state (not just UNSTARTED) before issuing play commands.
// ---------------------------------------------------------------------------
// Review queue (dev only)
//
// A song joins the master list unapproved and stays out of rotation until its
// snippet start has been checked by hand. Review mode serves that queue one
// song at a time with the answer already on screen — there is nothing to
// guess here, the job is to audition the first hint and nudge the offset until
// it starts somewhere recognisable, then approve it into rotation.
// ---------------------------------------------------------------------------
const reviewBtn = document.getElementById("reviewBtn");
const reviewBadge = document.getElementById("reviewBadge");
const reviewProgressEl = document.getElementById("reviewProgress");
const reviewApproveBtn = document.getElementById("reviewApproveBtn");
const reviewSkipBtn = document.getElementById("reviewSkipBtn");

let reviewMode = false;
let reviewQueue = [];
let reviewIndex = 0;
let reviewPending = 0;
let reviewDurations = [0.2, 1, 3, 6, 10];

function updateReviewBadge() {
  reviewBadge.textContent = reviewPending ? ` ${reviewPending}` : "";
}

async function loadReviewQueue() {
  const res = await fetch("/api/review/queue?limit=50");
  const data = await res.json();
  reviewQueue = data.songs || [];
  reviewIndex = 0;
  reviewPending = data.pending || 0;
  if (data.snippet_durations) reviewDurations = data.snippet_durations;
  updateReviewBadge();
  return data;
}

async function showReviewSong() {
  // The batch is a window onto a longer queue — top it up when it runs out.
  if (reviewIndex >= reviewQueue.length) {
    await loadReviewQueue();
    if (!reviewQueue.length) {
      reviewProgressEl.textContent = "queue empty";
      exitReview();
      return;
    }
  }
  const song = reviewQueue[reviewIndex];

  // Same teardown a new round does, so a half-finished prime from the previous
  // song can't leave this one blocked or muted.
  primeGeneration++;
  priming = false;
  if (playerReady) {
    ytPlayer.stopVideo();
    ytPlayer.unMute();
  }
  playIcon.textContent = "\u25B6";
  playBtn.classList.remove("playing");
  setPlayLoading(true);
  snippetTarget = 0;
  snippetStarted = false;
  snippetPlayFrom = null;
  parkedAtStart = false;
  lastCutoff = null;
  revealAt = 0;
  draining = false;
  progressFill.classList.remove("draining", "smooth", "full");
  progressFill.style.width = "0%";
  progressTarget.style.width = "0%";

  state = {
    roundId: null,
    videoId: song.youtube_video_id,
    durations: reviewDurations,
    maxAttempts: reviewDurations.length,
    startOffset: song.start_offset || 0,
    // Presented exactly as a round you've already played to the end: every
    // attempt spent, answer on screen, Play running the song through. The
    // "0.2s hint" button is there when you want the snippet itself.
    attemptsUsed: reviewDurations.length,
    gameOver: true,
    review: true,
  };
  currentSongId = song.song_id;
  renderTicks();

  revealTitle.textContent = song.title;
  revealArtist.textContent = song.artist;
  offsetValueEl.textContent = `${state.startOffset.toFixed(1)}s`;
  removeSongBtn.disabled = false;
  removeSongBtn.textContent = "\u2715";
  retryAudioBtn.disabled = false;
  retryAudioBtn.textContent = "\u{1F504}";
  reviewProgressEl.textContent = `${reviewPending} left`;
  reviewApproveBtn.disabled = false;
  reviewSkipBtn.disabled = false;
  guessInput.value = "";

  await preloadRevealCover(song.cover);
  revealSectionEl.classList.add("expanded");
  clearTimeout(settleTimer);
  settleTimer = setTimeout(() => revealSectionEl.classList.add("settled"), 380);

  if (playerReady) {
    ytPlayer.cueVideoById(state.videoId);
    primeOffset(state.startOffset).then(() => setPlayLoading(false));
  } else {
    pendingVideoId = state.videoId;
  }
}

async function enterReview() {
  await loadReviewQueue();
  if (!reviewQueue.length) {
    reviewBadge.textContent = " 0";
    return; // nothing waiting — stay in the normal game
  }
  reviewMode = true;
  document.body.classList.add("reviewing");
  await showReviewSong();
}

function exitReview() {
  reviewMode = false;
  document.body.classList.remove("reviewing");
  revealSectionEl.classList.remove("expanded", "settled");
  startRound();
}

async function approveCurrentReview() {
  const song = reviewQueue[reviewIndex];
  // Outside a review session the queue cursor points at some other song than
  // the one on screen, so approving would sign off the wrong track.
  if (!reviewMode || !song || song.song_id !== currentSongId) return;
  reviewApproveBtn.disabled = true;
  const res = await fetch(`/api/songs/${encodeURIComponent(song.song_id)}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved: true }),
  });
  const data = await res.json();
  if (typeof data.pending === "number") {
    reviewPending = data.pending;
    updateReviewBadge();
  }
  reviewIndex++;
  await showReviewSong();
}

reviewBtn.addEventListener("click", () => {
  if (reviewMode) exitReview();
  else enterReview();
});

reviewApproveBtn.addEventListener("click", approveCurrentReview);

reviewSkipBtn.addEventListener("click", async () => {
  if (!reviewMode) return;
  reviewSkipBtn.disabled = true;
  reviewIndex++;
  await showReviewSong();
});

if (document.body.classList.contains("dev")) {
  loadReviewQueue(); // just to populate the badge
}

// Wait until the player can actually accept a play/seek.
//
// This used to poll for the state leaving UNSTARTED (-1), which looks like a
// "still loading" signal but isn't: after a cue followed by a seek, UNSTARTED
// is the player's *resting* state, and it only leaves it once playback truly
// begins. So the check could never be satisfied by waiting, and every first
// press on an offset song burned the full ~3s timeout before doing anything —
// which is exactly why that press felt different from all the ones after it.
//
// getDuration() is the honest readiness signal: 0 until metadata has loaded,
// non-zero once the video is ready to play or seek.
async function waitUntilPlayable() {
  for (let i = 0; i < 100 && !(ytPlayer.getDuration() > 0); i++) {
    await new Promise((r) => setTimeout(r, 20));
  }
}

// seekTo() is async, and over a region the player hasn't buffered yet YouTube
// lands on the nearest preceding keyframe rather than the exact timestamp —
// often all the way back at 0. Calling playVideo() straight after the seek
// therefore starts the hint from the wrong place (and, since the cutoff is a
// fixed video-time position, gives it the wrong length too). Wait for the
// playhead to actually report the target before playing, so the very first
// press on an offset song sounds identical to every later one.
// Assigning img.src starts an async fetch — the element keeps rendering the
// *previous* song's artwork until the new file arrives, which lands right in
// the middle of the reveal animation. Decode it off-screen first, then swap,
// so the card never animates in showing the wrong cover. Capped so a slow or
// dead image URL can't hold the reveal hostage; on failure we show nothing
// rather than something stale and misleading.
function preloadRevealCover(url) {
  revealCover.removeAttribute("src"); // never let the old art linger
  if (!url) return Promise.resolve();
  return new Promise((resolve) => {
    let settled = false;
    const finish = (ok) => {
      if (settled) return;
      settled = true;
      if (ok) revealCover.src = url;
      resolve();
    };
    const img = new Image();
    img.onload = () => finish(true);
    img.onerror = () => finish(false);
    img.src = url;
    // Already cached? Some browsers resolve complete synchronously.
    if (img.complete && img.naturalWidth) finish(true);
    setTimeout(() => finish(img.complete && img.naturalWidth > 0), 1200);
  });
}

async function seekAndSettle(target, maxMs = 800) {
  ytPlayer.seekTo(target, true);
  for (let i = 0; i < Math.ceil(maxMs / 20); i++) {
    if (Math.abs(ytPlayer.getCurrentTime() - target) < 0.05) return;
    await new Promise((r) => setTimeout(r, 20));
  }
}

async function playSnippet() {
  if (!state || !playerReady) return;
  if (isPlaying()) {
    ytPlayer.pauseVideo(); // acts like a normal player's pause — freezes in place, no seek
    return;
  }
  await waitUntilPlayable();

  // Paused mid-clip (manually) vs. parked at the start after a finished hint
  // mean different things: mid-clip should just continue, whereas parked is a
  // fresh replay. Only ever a "continue" once playback has genuinely started
  // this round — otherwise a still-at-zero playhead looks identical to being
  // mid-clip and we'd resume from the song's real beginning.
  if (snippetStarted && !parkedAtStart && ytPlayer.getCurrentTime() < snippetCutoffAt()) {
    ytPlayer.playVideo();
    return;
  }

  const replayingFromPark = parkedAtStart;
  parkedAtStart = false;

  if (state.gameOver) {
    snippetTarget = Infinity; // round's over — let it play through in full, no attempt cutoff
  } else {
    snippetTarget = state.durations[Math.min(state.attemptsUsed, state.durations.length - 1)];
    updateTargetIndicator();
  }
  // Already sitting exactly at the snippet start, warm and ready — seeking
  // again would only re-introduce the backward-seek lag this parking avoids.
  if (!replayingFromPark) {
    await seekAndSettle(state.startOffset);
  }
  revealAt = performance.now() + RESET_BLANK_MS;
  progressFill.classList.remove("smooth");
  progressFill.style.width = "0%";
  progressFill.classList.remove("full");
  // Re-anchor: this is a fresh start, not a resume. Anchor to the offset
  // itself rather than letting enforceSnippetCutoff() infer it from the first
  // frame that reports PLAYING — that report lands late by a variable 20-60ms,
  // and since parking guarantees playback resumes from exactly the offset, an
  // inferred anchor only ever adds jitter to where the hint ends.
  snippetPlayFrom = state.startOffset;
  ytPlayer.playVideo();
  snippetStarted = true;
  setTimeout(updateProgressFill, RESET_BLANK_MS);
}

async function fetchSuggestions(query) {
  if (!query || !state || state.gameOver) {
    suggestionsEl.classList.add("hidden");
    return;
  }
  const res = await fetch(`/api/search-titles?q=${encodeURIComponent(query)}`);
  const results = await res.json();
  // A guess (and possibly a game-over reveal) may have landed while this
  // fetch was in flight — don't let a stale response reopen the dropdown.
  if (!state || state.gameOver) {
    suggestionsEl.classList.add("hidden");
    return;
  }
  suggestionsEl.innerHTML = "";
  results.forEach((track) => {
    const li = document.createElement("li");
    li.textContent = `${track.title} — ${track.artist}`;
    li.addEventListener("click", () => {
      guessInput.value = track.title;
      suggestionsEl.classList.add("hidden");
      submitGuess(track.title);
    });
    suggestionsEl.appendChild(li);
  });
  suggestionsEl.classList.toggle("hidden", results.length === 0);
}

async function submitGuess(guess) {
  if (!state || state.gameOver) return;
  clearTimeout(suggestionDebounce); // don't let a pending autocomplete fetch reopen the list after this
  suggestionsEl.classList.add("hidden");
  const res = await fetch("/api/round/guess", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ round_id: state.roundId, guess }),
  });
  const result = await res.json();

  state.attemptsUsed = state.maxAttempts - result.attempts_left;
  state.gameOver = result.game_over;
  if (result.game_over) {
    // Role change (and layout change) — hide the row before rearranging it.
    guessRow.classList.add("swapping");
  } else {
    morphActionLabel(); // Skip → Give up, layout stays put
  }

  if (!result.game_over) {
    snippetTarget = state.durations[Math.min(state.attemptsUsed, state.durations.length - 1)];
    updateTargetIndicator();
    // Only pick up where they left off if they were actually listening.
    // Skipping without ever pressing play shouldn't start audio unprompted —
    // the longer hint is simply armed, and plays when they choose to.
    if (snippetStarted && !isPlaying() && playerReady) {
      // The playhead was parked back at the snippet start ready for a replay,
      // but a wrong guess should carry on into the newly revealed stretch
      // rather than replay what's already been heard — so jump forward to
      // where the last hint actually ended before resuming.
      if (parkedAtStart && lastCutoff !== null) {
        parkedAtStart = false;
        await seekAndSettle(lastCutoff);
      }
      ytPlayer.playVideo(); // resume from wherever it sits, no restart
    }
  }

  if (result.game_over) {
    currentSongId = result.reveal.song_id;
    removeSongBtn.disabled = false;
    removeSongBtn.textContent = "✕";
    retryAudioBtn.disabled = false;
    retryAudioBtn.textContent = "🔄";
    revealTitle.textContent = result.reveal.title;
    revealArtist.textContent = result.reveal.artist;
    offsetValueEl.textContent = `${state.startOffset.toFixed(1)}s`;
    // Wait for the artwork before expanding, so the card animates in with the
    // correct cover already in place rather than swapping it mid-animation.
    await preloadRevealCover(result.reveal.cover);
    // The row has had time to fade out by now (cover preload + the 0.2s
    // transition), so switch it to "Next song" while it's invisible, then let
    // it fade back in — sliding down naturally as the reveal expands beneath.
    await new Promise((r) => setTimeout(r, 200));
    applyActionState();
    revealSectionEl.classList.add("expanded");
    guessRow.classList.remove("swapping");
    // Release the clip once the height animation has finished, so the cover's
    // pop-in (which overshoots its box) isn't cut off at the section edge.
    clearTimeout(settleTimer);
    // Timed to land just after the 360ms row expand and before the cover's
    // pop peaks (~485ms), so the overshoot is unclipped without releasing so
    // early that content spills outside the card while the row is growing.
    settleTimer = setTimeout(() => revealSectionEl.classList.add("settled"), 380);
    guessInput.disabled = true;

    snippetTarget = Infinity; // no more cutoff — let it keep playing through the reveal
    // The hint may well have finished and parked before the answer was typed.
    // Leaving that flag set makes the bar read the parked branch below, where
    // "elapsed" is the hint length — now Infinity — so it would snap to full
    // and stay there instead of tracking the song playing out.
    parkedAtStart = false;
    if (!isPlaying() && playerReady) {
      await seekAndSettle(state.startOffset);
      revealAt = 0;
      ytPlayer.playVideo();
      snippetStarted = true;
    }
  } else {
    guessInput.value = "";
  }
  suggestionsEl.classList.add("hidden");
}

playBtn.addEventListener("click", playSnippet);

guessInput.addEventListener("input", () => {
  clearTimeout(suggestionDebounce);
  suggestionDebounce = setTimeout(() => fetchSuggestions(guessInput.value.trim()), 250);
});

guessInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && guessInput.value.trim()) {
    submitGuess(guessInput.value.trim());
  }
});

actionBtn.addEventListener("click", async () => {
  // Mid-round this is Skip/Give up — both are just an empty guess.
  if (!state || !state.gameOver) {
    submitGuess("");
    return;
  }
  // Round's over, so it's the Next song button. Fade the button away along
  // with everything else, rather than leaving it sitting there through the
  // collapse and then snapping back into "Skip".
  guessRow.classList.add("swapping");
  // Clip again before collapsing — the row is about to animate its height.
  clearTimeout(settleTimer);
  revealSectionEl.classList.remove("settled");
  revealSectionEl.classList.remove("expanded"); // collapses height + fades out together
  // Drain the green progress away while the card collapses. The track itself
  // stays put — only the fill animates out.
  draining = true;
  progressFill.classList.remove("smooth", "full");
  progressFill.classList.add("draining");
  progressFill.style.width = "0%";
  await new Promise((r) => setTimeout(r, 360)); // let the collapse play before the round swap
  startRound();
});

// Some songs' YouTube audio has a beat of dead air before the track actually
// starts, which wastes the whole 0.2s first hint. This lets the offset be
// nudged and instantly previewed from the reveal screen, and persists per
// song so every future round for that track starts in the right place.
async function adjustStartOffset(delta) {
  if (!currentSongId || !state) return;
  const newOffset = Math.max(0, Math.round((state.startOffset + delta) * 10) / 10);
  state.startOffset = newOffset;
  offsetValueEl.textContent = `${newOffset.toFixed(1)}s`;

  fetch(`/api/songs/${encodeURIComponent(currentSongId)}/start-offset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ offset: newOffset }),
  });

  if (!playerReady) return;
  // Audition exactly what was just changed: the first hint, heard from the new
  // offset. Debounced so holding +0.1 down auditions the value you land on
  // rather than firing a clip for every value on the way there.
  clearTimeout(previewTimer);
  // Blank the bar the moment the offset moves and hold it blank through the
  // debounce and the seek. Without this it keeps redrawing against the old
  // anchor for a beat before the audition resets it, which shows up as a
  // flick of fill at the wrong width.
  progressFill.classList.remove("smooth", "full");
  progressFill.style.width = "0%";
  // Generous ceiling, not a guess at the seek time: previewFirstHint() replaces
  // this the moment its seek lands, so the bar is never actually blank this
  // long. Too short a window and the fill redraws at the old width for a frame
  // before the audition resets it.
  revealAt = performance.now() + OFFSET_PREVIEW_MS + 1500;
  previewTimer = setTimeout(previewFirstHint, OFFSET_PREVIEW_MS);
}

offsetMinusBigBtn.addEventListener("click", () => adjustStartOffset(-0.5));
offsetMinusBtn.addEventListener("click", () => adjustStartOffset(-0.1));
offsetPlusBtn.addEventListener("click", () => adjustStartOffset(0.1));
offsetPlusBigBtn.addEventListener("click", () => adjustStartOffset(0.5));

// Plays exactly the real first-hint duration from the current offset, via
// the same tick()/enforceSnippetCutoff() machinery a real round uses — so
// this is a true preview of what a player would actually hear, not an
// approximation. The longer nudge preview above is easy to hear regardless
// of precision; this is the one that actually tells you if 0.2s lands right.
async function previewFirstHint() {
  if (!playerReady || !state) return;
  await waitUntilPlayable();
  clearTimeout(previewTimer);
  if (isPlaying()) ytPlayer.pauseVideo(); // cut any clip still running
  snippetTarget = state.durations[0];
  updateTargetIndicator();
  parkedAtStart = false;
  await seekAndSettle(state.startOffset);
  // Anchor only once the seek has landed. Setting it before would leave the
  // cutoff measuring against a position the player hasn't reached yet, and the
  // 4ms check would chop the clip before it started.
  snippetPlayFrom = state.startOffset;
  // Reset the bar exactly the way a real press does. Without this the fill
  // keeps whatever it was showing — including the width the previous audition
  // left pinned when it parked — so nudging the offset looked like the bar had
  // stopped working rather than replaying from the top.
  revealAt = performance.now() + RESET_BLANK_MS;
  progressFill.classList.remove("smooth");
  progressFill.style.width = "0%";
  progressFill.classList.remove("full");
  ytPlayer.playVideo();
  snippetStarted = true;
  setTimeout(updateProgressFill, RESET_BLANK_MS);
}

previewFirstHintBtn.addEventListener("click", previewFirstHint);

removeSongBtn.addEventListener("click", async () => {
  if (!currentSongId) return;
  removeSongBtn.disabled = true;
  removeSongBtn.textContent = "…";
  const res = await fetch(`/api/songs/${encodeURIComponent(currentSongId)}/remove`, { method: "POST" });
  removeSongBtn.textContent = "✓";
  // A removed song leaves the queue as surely as an approved one does, so the
  // remaining count has to follow — otherwise it reads one too many until the
  // next batch is fetched.
  const data = await res.json().catch(() => ({}));
  if (typeof data.pending === "number") {
    reviewPending = data.pending;
    updateReviewBadge();
    if (reviewMode) reviewProgressEl.textContent = `${reviewPending} left`;
  }
});

retryAudioBtn.addEventListener("click", async () => {
  if (!currentSongId) return;
  retryAudioBtn.disabled = true;
  retryAudioBtn.textContent = "…";
  const res = await fetch(`/api/songs/${encodeURIComponent(currentSongId)}/retry-video`, { method: "POST" });
  if (res.ok) {
    retryAudioBtn.textContent = "✓";
  } else {
    retryAudioBtn.textContent = "!";
    retryAudioBtn.disabled = false;
  }
});

document.addEventListener("click", (e) => {
  if (!e.target.closest(".guess-field")) suggestionsEl.classList.add("hidden");
});

// Filters load before the first round, so a previously saved selection is
// honoured immediately instead of serving one unfiltered song first.
initFilters().catch(() => {}).then(startRound);
