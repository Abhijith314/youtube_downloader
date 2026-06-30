from flask import Flask, request, jsonify, render_template, Response, stream_with_context
import json, time, os, re
from modules.url_detector     import detect
from modules.format_fetcher   import get_formats
from modules.playlist_manager import get_youtube_playlist
from modules.spotify_handler  import get_track, get_playlist, get_album
from modules.download_queue   import enqueue, get_status, get_all_statuses
import config

app = Flask(__name__)
os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)

# Strip ANSI terminal color codes that yt-dlp injects into error strings
_ANSI = re.compile(r'(?:\x1b|\\\[)\[[0-9;]*m|\[0m')

def clean_error(msg: str) -> str:
    msg = _ANSI.sub("", str(msg))
    msg = re.sub(r'^(ERROR:\s*)+', '', msg).strip()
    return msg or "Unknown error"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/fetch-info", methods=["POST"])
def fetch_info():
    data = request.get_json(silent=True) or {}
    url  = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "Please enter a URL"}), 400

    info = detect(url)
    kind = info["type"]

    if kind == "unknown":
        return jsonify({
            "error": "Unrecognized URL. Paste a YouTube, YouTube Music, or Spotify link."
        }), 400

    try:
        if kind == "spotify_track":
            track = get_track(info["id"])
            return jsonify({"type": "single", "source": "spotify", **track})

        elif kind in ("spotify_playlist", "spotify_album"):
            fn = get_playlist if kind == "spotify_playlist" else get_album
            return jsonify({"type": "playlist", "source": "spotify", **fn(info["id"])})

        elif kind in ("youtube_playlist", "ytmusic_playlist"):
            pl = get_youtube_playlist(url)
            return jsonify({"type": "playlist", "source": "youtube", **pl})

        elif kind in ("youtube_video", "ytmusic_track"):
            fmts = get_formats(url)
            return jsonify({"type": "single", "source": "youtube", "url": url, **fmts})

    except Exception as e:
        return jsonify({"error": clean_error(str(e))}), 500

    return jsonify({"error": "Unexpected error"}), 500


@app.route("/api/download-single", methods=["POST"])
def download_single():
    task_id = enqueue(request.json)
    return jsonify({"task_id": task_id})


@app.route("/api/download-playlist", methods=["POST"])
def download_playlist():
    data   = request.json
    tracks = data.get("tracks", [])
    ids    = []
    for track in tracks:
        task = {
            "url"     : track.get("url") or track.get("search_q", ""),
            "source"  : data.get("source", "youtube"),
            "mode"    : data.get("mode", "audio"),
            "quality" : data.get("quality", "320"),
            "metadata": track,
        }
        ids.append(enqueue(task))
    return jsonify({"task_ids": ids})


@app.route("/api/status")
def status_all():
    return jsonify(get_all_statuses())


@app.route("/api/status/<task_id>")
def status_one(task_id):
    return jsonify(get_status(task_id))


@app.route("/api/progress")
def progress_sse():
    def generate():
        while True:
            yield f"data: {json.dumps(get_all_statuses())}\n\n"
            time.sleep(1)
    return Response(
        stream_with_context(generate()),
        content_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    app.run(debug=True, threaded=True)
