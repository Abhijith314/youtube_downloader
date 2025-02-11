from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
from pathlib import Path

app = Flask(__name__)

DOWNLOAD_FOLDER = Path("downloads")
DOWNLOAD_FOLDER.mkdir(exist_ok=True)

def get_video_info(url):
    """Fetch video details including available formats."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "no_color": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats", [])
            video_formats = {}
            audio_formats = {}

            # Filter formats
            for f in formats:
                format_id = f.get("format_id", "")
                filesize = f.get("filesize", 0)
                filesize_mb = f"{round(filesize / (1024 * 1024), 1)}MB" if filesize else "Unknown size"
                ext = f.get("ext", "")

                # Handle video formats
                if f.get("vcodec") != "none":
                    height = f.get("height", 0)
                    if height and ext in ['mp4', 'webm']:
                        key = f"{height}p ({ext}) {filesize_mb}"
                        video_formats[key] = format_id

                # Handle audio formats
                elif f.get("acodec") != "none":
                    abr = f.get("abr", 0)
                    if abr and ext in ['m4a', 'webm']:
                        quality = "low" if abr < 128 else "medium" if abr < 256 else "high"
                        key = f"{int(abr)}kbps ({quality}) {filesize_mb}"
                        audio_formats[key] = format_id

            return {
                "title": info.get("title", "Unknown Title"),
                "thumbnail": info.get("thumbnail", ""),
                "duration": info.get("duration", 0),
                "videos": dict(sorted(video_formats.items(), key=lambda x: int(x[0].split('p')[0]), reverse=True)),
                "audios": dict(sorted(audio_formats.items(), key=lambda x: int(x[0].split('kbps')[0]), reverse=True))
            }
        except Exception as e:
            print(f"Error in get_video_info: {str(e)}")
            raise

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_formats", methods=["POST"])
def get_formats():
    url = request.form.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        video_info = get_video_info(url)
        return jsonify(video_info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download", methods=["POST"])
def download():
    try:
        url = request.form.get("url")
        format_type = request.form.get("format")
        format_id = request.form.get("quality")

        if not url or not format_type or not format_id:
            return "Missing parameters", 400

        output_template = str(DOWNLOAD_FOLDER / "%(title)s.%(ext)s")
        
        ydl_opts = {
            "outtmpl": output_template,
            "format": format_id,
            "quiet": False,
            "no_warnings": True,
            "no_color": True,
            # Add cookie handling and other options to avoid throttling
            "nocheckcertificate": True,
            "ignoreerrors": False,
            # Add user-agent to avoid 403 errors
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        }

        if format_type == "mp3":
            ydl_opts.update({
                "postprocessors": [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '320',
                }]
            })
        else:
            # For video, always try to merge with best audio
            ydl_opts.update({
                "format": f"{format_id}+bestaudio",
                "merge_output_format": "mp4"
            })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url)
            filename = ydl.prepare_filename(info)
            
            if format_type == "mp3":
                filename = str(Path(filename).with_suffix('.mp3'))
            else:
                filename = str(Path(filename).with_suffix('.mp4'))

            # Verify file exists
            if not os.path.exists(filename):
                raise Exception("Download failed: File not created")

        return send_file(
            filename,
            as_attachment=True,
            download_name=Path(filename).name
        )

    except Exception as e:
        error_message = str(e)
        print(f"Download error: {error_message}")
        return f"Download failed: {error_message}", 500

if __name__ == "__main__":
    app.run(debug=True)