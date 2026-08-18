import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from services import deezer, game, genius  # noqa: E402

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = Flask(__name__, static_folder=None)


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:filename>")
def frontend_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


@app.get("/api/round/new")
def round_new():
    return jsonify(game.start_round())


@app.post("/api/round/guess")
def round_guess():
    payload = request.get_json(force=True)
    try:
        result = game.submit_guess(payload["round_id"], payload["guess"])
    except game.RoundNotFoundError:
        return jsonify({"error": "round not found"}), 404
    return jsonify(result)


@app.get("/api/search-titles")
def search_titles():
    query = request.args.get("q", "")
    if not query:
        return jsonify([])
    return jsonify(deezer.search_titles(query))


@app.get("/api/lyrics-search")
def lyrics_search():
    query = request.args.get("q", "")
    if not query:
        return jsonify([])
    try:
        return jsonify(genius.search_by_lyrics(query))
    except genius.GeniusError as e:
        return jsonify({"error": str(e)}), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
