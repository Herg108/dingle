# dingle

A Heardle-style song guessing game.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Get a free YouTube Data API v3 key (console.cloud.google.com → enable "YouTube Data API v3" → Credentials → Create API Key) and add it to `.env`:

```
YOUTUBE_API_KEY=your_key_here
```

## Run

```bash
python backend/app.py
```

Open http://localhost:5000

## How it works

- The song pool (titles/artists/cover art) is built from Deezer's public API (no key needed) — Deezer's overall top chart plus curated "hits" playlists (decades, party, wedding, classic rock, etc.), cached locally and refreshed weekly.
- Actual audio playback comes from YouTube instead of Deezer's preview clips, since Deezer (like Spotify/Apple Music) only gives a pre-cut ~30s highlight that isn't guaranteed to start at the true beginning of the song. Each picked track is searched on YouTube once (preferring official "Artist - Topic" channels), and the resulting video ID is cached permanently so the same song never needs re-searching.
- Each round plays a growing snippet from the true 0:00 of that video; running out of guesses (or a correct one) reveals the song and lets it keep playing.

## Deploying (Railway)

1. Connect this repo in Railway.
2. Set the `YOUTUBE_API_KEY` environment variable in the project settings.
3. Point your custom domain at the Railway deployment (Settings → Domains).
