import re
import uuid

from services import curation

SNIPPET_DURATIONS = [0.2, 1, 3, 6, 10]
MAX_ATTEMPTS = len(SNIPPET_DURATIONS)

_rounds = {}


class RoundNotFoundError(Exception):
    pass


class NoPlayableTrackError(Exception):
    pass


def _normalize(text):
    text = text.lower()
    text = re.sub(r"\bfeat\.?.*", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text.strip()


def start_round():
    try:
        song = curation.random_playable_song()
    except IndexError:
        raise NoPlayableTrackError()
    round_id = str(uuid.uuid4())
    _rounds[round_id] = {"song": song, "attempts_used": 0}
    return {
        "round_id": round_id,
        "youtube_video_id": song["video_id"],
        "snippet_durations": SNIPPET_DURATIONS,
        "max_attempts": MAX_ATTEMPTS,
    }


def _reveal(song):
    return {
        "song_id": song["id"],
        "title": song["title"],
        "artist": song["artist"],
        "cover": song["cover"],
    }


def submit_guess(round_id, guess):
    round_state = _rounds.get(round_id)
    if round_state is None:
        raise RoundNotFoundError(round_id)
    song = round_state["song"]
    round_state["attempts_used"] += 1

    correct = _normalize(guess) == _normalize(song["title"])
    attempts_left = MAX_ATTEMPTS - round_state["attempts_used"]
    game_over = correct or attempts_left <= 0

    response = {
        "correct": correct,
        "attempts_left": max(attempts_left, 0),
        "game_over": game_over,
    }
    if game_over:
        response["reveal"] = _reveal(song)
        del _rounds[round_id]
    return response
