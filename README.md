# dingle

A Heardle-style song guessing game, plus a lyric finder for when you remember the words but not the title.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Get a free Genius Client Access Token (genius.com/api-clients) and add it to `.env`.

## Run

```bash
python backend/app.py
```

Open http://localhost:5000

## How it works

- Song audio comes from Deezer's public search/chart/playlist API (no key needed) — a pool of tracks is built by aggregating Deezer's genre charts and decade playlists, cached locally, and refreshed weekly.
- Each round plays a growing snippet of a random track from that pool; six wrong guesses (or a correct one) reveals the song.
- The Lyric Finder page searches Genius by lyric snippet to identify a song by its words.

## Deploying (Railway)

1. Connect this repo in Railway.
2. Set the `GENIUS_ACCESS_TOKEN` environment variable in the project settings.
3. Point your custom domain at the Railway deployment (Settings → Domains).
