import json
import os
import re
from pathlib import Path

import requests

BASE_URL = "https://www.googleapis.com/youtube/v3"
CACHE_PATH = Path(__file__).resolve().parent.parent / "cache" / "youtube_video_ids.json"

# Each free Google Cloud project gets its own independent 100-searches/day
# quota, so multiple keys (from separate projects) let us rotate to a fresh
# one once the current one is exhausted instead of waiting a full day.
_current_key_index = 0


class YouTubeError(Exception):
    pass


def _api_keys():
    raw = os.environ.get("YOUTUBE_API_KEYS") or os.environ.get("YOUTUBE_API_KEY", "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        raise YouTubeError("no YouTube API key configured")
    return keys


def _load_cache():
    if not CACHE_PATH.exists():
        return {}
    return json.loads(CACHE_PATH.read_text())


def _write_cache(cache):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache))


def _raw_search(query):
    global _current_key_index
    keys = _api_keys()

    last_error = None
    for _ in range(len(keys)):
        key = keys[_current_key_index % len(keys)]
        resp = requests.get(
            f"{BASE_URL}/search",
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "videoCategoryId": "10",
                "maxResults": 10,
                "key": key,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("items", [])
        if resp.status_code == 429:
            # this key's daily quota is exhausted — rotate to the next one
            last_error = f"YouTube search returned status {resp.status_code}"
            _current_key_index += 1
            continue
        raise YouTubeError(f"YouTube search returned status {resp.status_code}")

    raise YouTubeError(last_error or "all YouTube API keys exhausted")


_LIVE_PATTERN = re.compile(r"\blive\b", re.IGNORECASE)


def _is_live(item):
    # Word-boundary match so "Live" is excluded but "Alive"/"Delivery" aren't.
    # Live recordings have different arrangements, crowd noise, count-ins,
    # etc. — never an acceptable match even if otherwise "official audio".
    return bool(_LIVE_PATTERN.search(item["snippet"]["title"]))


def _is_audio_only(item):
    channel = item["snippet"]["channelTitle"]
    video_title = item["snippet"]["title"].lower()
    # "<Artist> - Topic" channels are YouTube's auto-generated home for clean
    # label audio (no video, just a static image) — structurally can't have
    # music-video intro padding. "(Official Audio)" uploads are the same idea
    # from the artist's own channel. Lyric videos are also almost always just
    # the real studio track with text synced over it from 0:00 — not repadded
    # with a movie-style intro the way a full music video usually is. All far
    # more reliable than whatever else ranks first (the official music video).
    return (
        channel.endswith(" - Topic")
        or "official audio" in video_title
        or "lyric" in video_title
    )


def _valid_candidates(raw_items, exclude_video_id):
    # Some search results (e.g. certain live streams or region-restricted
    # items) don't have the usual id.videoId shape even with type=video set —
    # skip anything malformed instead of crashing on it.
    out = []
    for item in raw_items:
        video_id = item.get("id", {}).get("videoId")
        if not video_id or video_id == exclude_video_id:
            continue
        if _is_live(item):
            continue
        out.append(item)
    return out


def _search_video_id(artist, title, exclude_video_id=None):
    items = _valid_candidates(_raw_search(f"{artist} {title}"), exclude_video_id)
    if not items:
        return None

    audio_match = next((item for item in items if _is_audio_only(item)), None)
    if audio_match:
        return audio_match["id"]["videoId"]

    # No clean audio upload in the first pass — try again biased toward one
    # before settling for whatever ranks first (likely a padded music video).
    retry_items = _valid_candidates(_raw_search(f"{artist} {title} audio"), exclude_video_id)
    audio_match = next((item for item in retry_items if _is_audio_only(item)), None)
    if audio_match:
        return audio_match["id"]["videoId"]

    return items[0]["id"]["videoId"]


def video_id_for_track(track_id, artist, title):
    cache = _load_cache()
    key = str(track_id)
    if key in cache:
        return cache[key]

    video_id = _search_video_id(artist, title)
    if video_id:
        cache[key] = video_id
        _write_cache(cache)
    return video_id


def retry_video_id(track_id, artist, title, exclude_video_id):
    video_id = _search_video_id(artist, title, exclude_video_id=exclude_video_id)
    if video_id:
        cache = _load_cache()
        cache[str(track_id)] = video_id
        _write_cache(cache)
    return video_id
