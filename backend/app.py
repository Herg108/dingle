import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from services import curation, deezer, game, youtube  # noqa: E402

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = Flask(__name__, static_folder=None)


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:filename>")
def frontend_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


def _csv_param(name):
    raw = request.args.get(name, "")
    return [v for v in (p.strip() for p in raw.split(",")) if v]


@app.get("/api/filters")
def filters():
    return jsonify(curation.filter_counts(
        eras=_csv_param("eras"),
        genres=_csv_param("genres"),
    ))


@app.get("/api/round/new")
def round_new():
    try:
        return jsonify(game.start_round(
            eras=_csv_param("eras"),
            genres=_csv_param("genres"),
        ))
    except game.NoPlayableTrackError:
        return jsonify({"error": "no playable track found, try again"}), 502
    except youtube.YouTubeError as e:
        return jsonify({"error": str(e)}), 502


@app.post("/api/round/guess")
def round_guess():
    payload = request.get_json(force=True)
    try:
        result = game.submit_guess(payload["round_id"], payload["guess"])
    except game.RoundNotFoundError:
        return jsonify({"error": "round not found"}), 404
    return jsonify(result)


@app.post("/api/songs/<song_id>/remove")
def remove_song(song_id):
    try:
        curation.remove_song(song_id)
    except KeyError:
        return jsonify({"error": "song not found"}), 404
    return jsonify({"ok": True})


@app.post("/api/songs/<song_id>/retry-video")
def retry_song_video(song_id):
    try:
        entry = curation.retry_video(song_id)
    except KeyError:
        return jsonify({"error": "song not found"}), 404
    except youtube.YouTubeError as e:
        return jsonify({"error": str(e)}), 502
    return jsonify({"video_id": entry["video_id"]})


@app.post("/api/songs/<song_id>/start-offset")
def set_song_start_offset(song_id):
    payload = request.get_json(force=True)
    try:
        entry = curation.set_start_offset(song_id, payload["offset"])
    except KeyError:
        return jsonify({"error": "song not found"}), 404
    except (TypeError, ValueError):
        return jsonify({"error": "invalid offset"}), 400
    return jsonify({"start_offset": entry["start_offset"]})


@app.get("/api/search-titles")
def search_titles():
    query = request.args.get("q", "")
    if not query:
        return jsonify([])
    return jsonify(deezer.search_titles(query))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=bool(os.environ.get("FLASK_DEBUG")))
