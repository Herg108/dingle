import re
import uuid

from services import deezer

MAX_ATTEMPTS = 6
SNIPPET_DURATIONS = [1, 2, 4, 7, 11, 16]

_rounds = {}


class RoundNotFoundError(Exception):
    pass


def _normalize(text):
    text = text.lower()
    text = re.sub(r"\(.*?\)|\[.*?\]", " ", text)
    text = re.sub(r"\bfeat\.?.*", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return text.strip()


def start_round():
    track = deezer.random_track()
    round_id = str(uuid.uuid4())
    _rounds[round_id] = {"track": track, "attempts_used": 0}
    return {
        "round_id": round_id,
        "preview_url": track["preview"],
        "snippet_durations": SNIPPET_DURATIONS,
        "max_attempts": MAX_ATTEMPTS,
    }


def _reveal(track):
    return {
        "title": track["title"],
        "artist": track["artist"],
        "cover": track["cover"],
    }


def submit_guess(round_id, guess):
    round_state = _rounds.get(round_id)
    if round_state is None:
        raise RoundNotFoundError(round_id)
    track = round_state["track"]
    round_state["attempts_used"] += 1

    correct = _normalize(guess) == _normalize(track["title_short"])
    attempts_left = MAX_ATTEMPTS - round_state["attempts_used"]
    game_over = correct or attempts_left <= 0

    response = {
        "correct": correct,
        "attempts_left": max(attempts_left, 0),
        "game_over": game_over,
    }
    if game_over:
        response["reveal"] = _reveal(track)
        del _rounds[round_id]
    return response
