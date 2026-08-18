import os

import requests

BASE_URL = "https://api.genius.com"


class GeniusError(Exception):
    pass


def search_by_lyrics(snippet, limit=8):
    access_token = os.environ["GENIUS_ACCESS_TOKEN"]
    resp = requests.get(
        f"{BASE_URL}/search",
        params={"q": snippet},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if resp.status_code != 200:
        raise GeniusError(f"Genius returned status {resp.status_code}")

    hits = resp.json()["response"]["hits"][:limit]
    results = []
    for hit in hits:
        song = hit["result"]
        results.append({
            "title": song["title"],
            "artist": song["primary_artist"]["name"],
            "cover": song.get("song_art_image_thumbnail_url", ""),
        })
    return results
