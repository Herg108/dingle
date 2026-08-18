const lyricsInput = document.getElementById("lyricsInput");
const lyricsSearchBtn = document.getElementById("lyricsSearchBtn");
const lyricsResults = document.getElementById("lyricsResults");

async function search() {
  const query = lyricsInput.value.trim();
  lyricsResults.innerHTML = "";
  if (!query) return;

  lyricsSearchBtn.disabled = true;
  try {
    const res = await fetch(`/api/lyrics-search?q=${encodeURIComponent(query)}`);
    const results = await res.json();
    if (results.length === 0) {
      const li = document.createElement("li");
      li.textContent = "No matches found.";
      lyricsResults.appendChild(li);
      return;
    }
    results.forEach((track) => {
      const li = document.createElement("li");
      const img = document.createElement("img");
      img.src = track.cover;
      img.alt = "";
      const info = document.createElement("div");
      const title = document.createElement("div");
      title.className = "reveal-title";
      title.textContent = track.title;
      const artist = document.createElement("div");
      artist.className = "reveal-artist";
      artist.textContent = track.artist;
      info.appendChild(title);
      info.appendChild(artist);
      li.appendChild(img);
      li.appendChild(info);
      lyricsResults.appendChild(li);
    });
  } finally {
    lyricsSearchBtn.disabled = false;
  }
}

lyricsSearchBtn.addEventListener("click", search);
lyricsInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") search();
});
