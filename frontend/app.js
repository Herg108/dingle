const playBtn = document.getElementById("playBtn");
const guessInput = document.getElementById("guessInput");
const suggestionsEl = document.getElementById("suggestions");
const skipBtn = document.getElementById("skipBtn");
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
const nextBtn = document.getElementById("nextBtn");
const progressBarEl = document.getElementById("progressBar");
const progressFill = document.getElementById("progressFill");
const progressTicks = document.getElementById("progressTicks");
const progressTarget = document.getElementById("progressTarget");

let state = null;
let suggestionDebounce = null;
let snippetTarget = 0;
let revealAt = 0;
let currentSongId = null;

let ytPlayer = null;
let playerReady = false;
let pendingVideoId = null;
let previewTimer = null;

const RESET_BLANK_MS = 120; // a deliberate blank beat so replays feel like a real reset

function isPlaying() {
  return !!ytPlayer && playerReady && ytPlayer.getPlayerState() === YT.PlayerState.PLAYING;
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
  if (performance.now() < revealAt) {
    progressFill.style.width = "0%";
    progressFill.classList.remove("full");
    return;
  }
  const max = maxDuration();
  const startOffset = state ? state.startOffset : 0;
  const currentTime = ytPlayer ? Math.max(0, ytPlayer.getCurrentTime() - startOffset) : 0;
  const pct = max ? Math.min((currentTime / max) * 100, 100) : 0;
  progressFill.style.width = `${pct}%`;
  progressFill.classList.toggle("full", pct >= 100);
}

function enforceSnippetCutoff() {
  const startOffset = state ? state.startOffset : 0;
  const cutoffAt = startOffset + snippetTarget;
  if (isPlaying() && ytPlayer.getCurrentTime() >= cutoffAt) {
    ytPlayer.pauseVideo();
    ytPlayer.seekTo(cutoffAt, true);
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
  if (isPlaying()) {
    enforceSnippetCutoff();
    updateProgressFill();
  }
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);

function onPlayerStateChange(event) {
  if (event.data === YT.PlayerState.PLAYING) {
    playBtn.textContent = "⏸";
    playBtn.classList.add("playing");
    progressFill.classList.add("smooth"); // eases over any re-buffering stutter after a resume
  } else if (event.data === YT.PlayerState.PAUSED || event.data === YT.PlayerState.ENDED) {
    playBtn.textContent = "▶";
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
        if (pendingVideoId) {
          ytPlayer.cueVideoById(pendingVideoId);
          pendingVideoId = null;
        }
        // startRound() may have already finished (and left playBtn disabled
        // on purpose, since the player wasn't ready yet at that point) —
        // now that it genuinely is ready, let Play actually become clickable.
        if (state) playBtn.disabled = false;
      },
      onStateChange: onPlayerStateChange,
    },
  });
};

async function startRound() {
  if (playerReady) ytPlayer.stopVideo();
  playBtn.textContent = "▶";
  playBtn.classList.remove("playing");
  // Disabled (not just logically ignored) so a click during this async gap
  // can't fire at all — prevents playSnippet() from ever running against the
  // previous round's now-stale state while this fetch is still in flight.
  playBtn.disabled = true;
  skipBtn.disabled = true;
  guessInput.disabled = true;
  snippetTarget = 0;
  revealAt = 0;
  const res = await fetch("/api/round/new");
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

  if (playerReady) {
    ytPlayer.cueVideoById(state.videoId);
  } else {
    pendingVideoId = state.videoId;
  }

  guessInput.value = "";
  guessInput.disabled = false;
  skipBtn.disabled = false;
  // Only enable Play if the YouTube player has actually finished
  // initializing — otherwise the first click would silently no-op (playSnippet
  // bails out when !playerReady). The onReady handler enables it once truly ready.
  playBtn.disabled = !playerReady;
  revealSectionEl.classList.remove("expanded");
  suggestionsEl.classList.add("hidden");
  progressFill.classList.remove("smooth");
  progressFill.style.width = "0%";
  progressFill.classList.remove("full");
  progressTarget.style.width = "0%";
  progressBarEl.classList.remove("leaving"); // fades back in now that it's genuinely reset
  renderTicks();
}

// cueVideoById() returns before the video has actually finished loading, so a
// playVideo() call that lands too soon after can get silently dropped —
// wait for a real ready state (not just UNSTARTED) before issuing play commands.
async function waitUntilCueable() {
  for (let i = 0; i < 100 && ytPlayer.getPlayerState() === YT.PlayerState.UNSTARTED; i++) {
    await new Promise((r) => setTimeout(r, 30));
  }
}

async function playSnippet() {
  if (!state || !playerReady) return;
  if (isPlaying()) {
    ytPlayer.pauseVideo(); // acts like a normal player's pause — freezes in place, no seek
    return;
  }
  await waitUntilCueable();

  // Paused mid-clip (manually) vs. paused at the cutoff mean different things:
  // mid-clip should just continue; at the cutoff there's nothing left to
  // continue toward, so it's a fresh replay of the current hint from the top.
  if (ytPlayer.getCurrentTime() < state.startOffset + snippetTarget) {
    ytPlayer.playVideo();
    return;
  }

  if (state.gameOver) {
    snippetTarget = Infinity; // round's over — let it play through in full, no attempt cutoff
  } else {
    snippetTarget = state.durations[Math.min(state.attemptsUsed, state.durations.length - 1)];
    updateTargetIndicator();
  }
  ytPlayer.seekTo(state.startOffset, true);
  revealAt = performance.now() + RESET_BLANK_MS;
  progressFill.classList.remove("smooth");
  progressFill.style.width = "0%";
  progressFill.classList.remove("full");
  ytPlayer.playVideo();
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

  if (!result.game_over) {
    snippetTarget = state.durations[Math.min(state.attemptsUsed, state.durations.length - 1)];
    updateTargetIndicator();
    if (!isPlaying() && playerReady) {
      ytPlayer.playVideo(); // resume from wherever it currently sits, no restart
    }
  }

  if (result.game_over) {
    currentSongId = result.reveal.song_id;
    removeSongBtn.disabled = false;
    removeSongBtn.textContent = "✕";
    retryAudioBtn.disabled = false;
    retryAudioBtn.textContent = "🔄";
    revealCover.src = result.reveal.cover;
    revealTitle.textContent = result.reveal.title;
    revealArtist.textContent = result.reveal.artist;
    offsetValueEl.textContent = `${state.startOffset.toFixed(1)}s`;
    revealSectionEl.classList.add("expanded");
    guessInput.disabled = true;
    skipBtn.disabled = true;

    snippetTarget = Infinity; // no more cutoff — let it keep playing through the reveal
    if (!isPlaying() && playerReady) {
      ytPlayer.seekTo(state.startOffset, true);
      revealAt = 0;
      ytPlayer.playVideo();
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

skipBtn.addEventListener("click", () => submitGuess(""));

nextBtn.addEventListener("click", async () => {
  revealSectionEl.classList.remove("expanded"); // collapses height + fades out together
  progressBarEl.classList.add("leaving"); // fades out with the reveal instead of snapping to empty
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

  if (playerReady) {
    clearTimeout(previewTimer);
    ytPlayer.seekTo(newOffset, true);
    ytPlayer.playVideo();
    previewTimer = setTimeout(() => {
      if (isPlaying()) ytPlayer.pauseVideo();
    }, 1500);
  }
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
  await waitUntilCueable();
  clearTimeout(previewTimer);
  snippetTarget = state.durations[0];
  updateTargetIndicator();
  revealAt = 0;
  progressFill.classList.remove("smooth");
  ytPlayer.seekTo(state.startOffset, true);
  ytPlayer.playVideo();
}

previewFirstHintBtn.addEventListener("click", previewFirstHint);

removeSongBtn.addEventListener("click", async () => {
  if (!currentSongId) return;
  removeSongBtn.disabled = true;
  removeSongBtn.textContent = "…";
  await fetch(`/api/songs/${encodeURIComponent(currentSongId)}/remove`, { method: "POST" });
  removeSongBtn.textContent = "✓";
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

startRound();
