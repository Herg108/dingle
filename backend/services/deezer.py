import json
import random
import time
from pathlib import Path

import requests

BASE_URL = "https://api.deezer.com"
CACHE_PATH = Path(__file__).resolve().parent.parent / "cache" / "song_pool.json"
CACHE_MAX_AGE_SECONDS = 7 * 24 * 60 * 60  # rebuild pool weekly
CHART_LIMIT = 200

DECADE_PLAYLIST_QUERIES = [
    "60s Hits", "70s Hits", "80s Hits", "90s Hits",
    "00s Hits", "10s Hits", "20s Hits", "Top Hits",
]


def _get(path, params=None):
    resp = requests.get(f"{BASE_URL}{path}", params=params or {}, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _slim_track(track):
    if not track.get("preview"):
        return None
    return {
        "id": track["id"],
        "title": track["title"],
        "title_short": track.get("title_short", track["title"]),
        "artist": track["artist"]["name"],
        "preview": track["preview"],
        "cover": track.get("album", {}).get("cover_medium", ""),
    }


def _genre_ids():
    data = _get("/genre")
    return [g["id"] for g in data.get("data", [])]


def _chart_tracks(genre_id, limit=CHART_LIMIT):
    data = _get(f"/chart/{genre_id}/tracks", {"limit": limit})
    return data.get("data", [])


def _playlist_tracks(playlist_id, limit=100):
    data = _get(f"/playlist/{playlist_id}/tracks", {"limit": limit})
    return data.get("data", [])


def _decade_playlist_ids():
    ids = []
    for query in DECADE_PLAYLIST_QUERIES:
        data = _get("/search/playlist", {"q": query, "limit": 3})
        for playlist in data.get("data", []):
            ids.append(playlist["id"])
    return ids


def _build_pool():
    pool = {}

    for genre_id in [0] + _genre_ids():
        for track in _chart_tracks(genre_id):
            slim = _slim_track(track)
            if slim:
                pool[slim["id"]] = slim

    for playlist_id in _decade_playlist_ids():
        for track in _playlist_tracks(playlist_id):
            slim = _slim_track(track)
            if slim:
                pool[slim["id"]] = slim

    return list(pool.values())


def _load_cache():
    if not CACHE_PATH.exists():
        return None
    payload = json.loads(CACHE_PATH.read_text())
    if time.time() - payload["built_at"] > CACHE_MAX_AGE_SECONDS:
        return None
    return payload["tracks"]


def _write_cache(tracks):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps({"built_at": time.time(), "tracks": tracks}))


def get_pool(force_rebuild=False):
    if not force_rebuild:
        cached = _load_cache()
        if cached:
            return cached
    tracks = _build_pool()
    _write_cache(tracks)
    return tracks


def _fresh_preview_url(track_id):
    data = _get(f"/track/{track_id}")
    return data["preview"]


def random_track():
    # Deezer's preview URLs are signed with a short-lived token, so the
    # cached pool's URL is likely stale by play time — always refetch it.
    pool = get_pool()
    track = dict(random.choice(pool))
    track["preview"] = _fresh_preview_url(track["id"])
    return track


def search_titles(query, limit=8):
    data = _get("/search/track", {"q": query, "limit": limit})
    results = []
    for track in data.get("data", []):
        slim = _slim_track(track)
        if slim:
            results.append({
                "title": slim["title"],
                "artist": slim["artist"],
                "cover": slim["cover"],
            })
    return results
