const player = document.getElementById("player");
const playBtn = document.getElementById("playBtn");
const guessInput = document.getElementById("guessInput");
const suggestionsEl = document.getElementById("suggestions");
const skipBtn = document.getElementById("skipBtn");
const feedbackEl = document.getElementById("feedback");
const attemptsEl = document.getElementById("attempts");
const revealEl = document.getElementById("reveal");
const revealCover = document.getElementById("revealCover");
const revealTitle = document.getElementById("revealTitle");
const revealArtist = document.getElementById("revealArtist");
const nextBtn = document.getElementById("nextBtn");

let state = null;
let suggestionDebounce = null;

async function startRound() {
  const res = await fetch("/api/round/new");
  const round = await res.json();
  state = {
    roundId: round.round_id,
    durations: round.snippet_durations,
    maxAttempts: round.max_attempts,
    attemptsUsed: 0,
    gameOver: false,
  };

  player.src = round.preview_url;
  guessInput.value = "";
  guessInput.disabled = false;
  skipBtn.disabled = false;
  playBtn.disabled = false;
  feedbackEl.textContent = "";
  feedbackEl.className = "feedback";
  revealEl.classList.add("hidden");
  nextBtn.classList.add("hidden");
  suggestionsEl.classList.add("hidden");
  renderPips();
}

function renderPips() {
  attemptsEl.innerHTML = "";
  for (let i = 0; i < state.maxAttempts; i++) {
    const pip = document.createElement("div");
    pip.className = "pip";
    if (i < state.attemptsUsed) pip.classList.add("used");
    attemptsEl.appendChild(pip);
  }
}

function playSnippet() {
  if (!state || state.gameOver) return;
  const durationSec = state.durations[Math.min(state.attemptsUsed, state.durations.length - 1)];
  player.currentTime = 0;
  player.play();
  setTimeout(() => player.pause(), durationSec * 1000);
}

async function fetchSuggestions(query) {
  if (!query) {
    suggestionsEl.classList.add("hidden");
    return;
  }
  const res = await fetch(`/api/search-titles?q=${encodeURIComponent(query)}`);
  const results = await res.json();
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
  const res = await fetch("/api/round/guess", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ round_id: state.roundId, guess }),
  });
  const result = await res.json();

  state.attemptsUsed = state.maxAttempts - result.attempts_left;
  state.gameOver = result.game_over;
  renderPips();

  if (result.correct) {
    feedbackEl.textContent = "Correct!";
    feedbackEl.className = "feedback correct";
  } else if (result.game_over) {
    feedbackEl.textContent = "Out of guesses!";
    feedbackEl.className = "feedback wrong";
  } else {
    feedbackEl.textContent = `Not quite — ${result.attempts_left} guess${result.attempts_left === 1 ? "" : "es"} left`;
    feedbackEl.className = "feedback wrong";
  }

  if (result.game_over) {
    revealCover.src = result.reveal.cover;
    revealTitle.textContent = result.reveal.title;
    revealArtist.textContent = result.reveal.artist;
    revealEl.classList.remove("hidden");
    nextBtn.classList.remove("hidden");
    guessInput.disabled = true;
    skipBtn.disabled = true;
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

nextBtn.addEventListener("click", startRound);

document.addEventListener("click", (e) => {
  if (!e.target.closest(".guess-field")) suggestionsEl.classList.add("hidden");
});

startRound();
