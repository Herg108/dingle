import requests

BASE_URL = "https://api.deezer.com"


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
