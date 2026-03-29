import threading, queue, uuid, os, requests, yt_dlp
import config

_tasks = {}
_q     = queue.Queue()
_lock  = threading.Lock()


def _cookie_opts() -> dict:
    """Return yt-dlp cookie options based on config."""
    opts = {}
    if config.COOKIE_FILE:
        opts["cookiefile"] = config.COOKIE_FILE
    elif config.COOKIE_BROWSER:
        opts["cookiesfrombrowser"] = (config.COOKIE_BROWSER,)
    return opts


def _progress_hook(task_id, d):
    with _lock:
        t = _tasks.get(task_id)
        if not t:
            return
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            down  = d.get("downloaded_bytes", 0)
            speed = d.get("speed") or 0
            t["progress"]   = int(down / total * 100) if total else 0
            t["speed_kbps"] = round(speed / 1024, 1) if speed else 0
            t["status"]     = "downloading"
        elif d["status"] == "finished":
            t["progress"] = 99
            t["status"]   = "processing"
        elif d["status"] == "error":
            t["status"] = "error"


def _build_ydl_opts(task):
    out_tmpl = os.path.join(config.DOWNLOAD_DIR, "%(title)s.%(ext)s")
    base = {
        "outtmpl"        : out_tmpl,
        "quiet"          : True,
        "no_warnings"    : True,
        "progress_hooks" : [lambda d: _progress_hook(task["id"], d)],
        **_cookie_opts(),
    }
    if config.FFMPEG_LOCATION:
        base["ffmpeg_location"] = config.FFMPEG_LOCATION

    if task.get("mode", "audio") == "audio":
        quality = str(task.get("quality", "320")).replace("kbps", "").strip()
        base.update({
            "format"         : "bestaudio/best",
            "writethumbnail" : True,
            "postprocessors" : [
                {
                    "key"              : "FFmpegExtractAudio",
                    "preferredcodec"   : "mp3",
                    "preferredquality" : quality,
                },
                {"key": "FFmpegMetadata", "add_metadata": True},
                {"key": "EmbedThumbnail", "already_have_thumbnail": False},
            ],
        })
        meta = task.get("metadata", {})
        if meta:
            base["parse_metadata"] = [
                f":{k}={v}" for k, v in {
                    "title" : meta.get("title", ""),
                    "artist": meta.get("artist", ""),
                    "album" : meta.get("album", ""),
                }.items() if v
            ]
    else:
        base.update({
            "format"              : task.get("format_id", "bestvideo+bestaudio/best"),
            "merge_output_format" : "mp4",
        })
    return base


def _inject_cover(mp3_path, cover_path):
    try:
        from mutagen.id3 import ID3, APIC
        from mutagen.mp3 import MP3
        audio = MP3(mp3_path, ID3=ID3)
        try:
            audio.add_tags()
        except Exception:
            pass
        with open(cover_path, "rb") as img:
            audio.tags.add(APIC(
                encoding=3, mime="image/jpeg",
                type=3, desc="Cover", data=img.read()
            ))
        audio.save()
    except Exception as e:
        print(f"Cover inject error: {e}")


def _download_spotify_track(task):
    meta      = task.get("metadata", {})
    title     = meta.get("title", "track")
    artist    = meta.get("artist", "")
    search_q  = meta.get("search_q") or f"{title} {artist} audio"
    cover_url = meta.get("cover_url", "")

    cover_path = None
    if cover_url:
        cover_path = os.path.join(config.DOWNLOAD_DIR, f"_cover_{task['id']}.jpg")
        try:
            r = requests.get(cover_url, timeout=10)
            with open(cover_path, "wb") as img:
                img.write(r.content)
        except Exception:
            cover_path = None

    safe_name = "".join(c for c in f"{title} - {artist}" if c.isalnum() or c in " -_")
    out_tmpl  = os.path.join(config.DOWNLOAD_DIR, f"{safe_name}.%(ext)s")
    quality   = str(task.get("quality", "320")).replace("kbps", "").strip()

    ydl_opts = {
        "default_search" : "ytsearch1",
        "outtmpl"        : out_tmpl,
        "quiet"          : True,
        "no_warnings"    : True,
        "format"         : "bestaudio/best",
        "writethumbnail" : not bool(cover_path),
        "progress_hooks" : [lambda d: _progress_hook(task["id"], d)],
        "postprocessors" : [
            {
                "key"              : "FFmpegExtractAudio",
                "preferredcodec"   : "mp3",
                "preferredquality" : quality,
            },
            {"key": "FFmpegMetadata", "add_metadata": True},
            {"key": "EmbedThumbnail", "already_have_thumbnail": False},
        ],
        "parse_metadata" : [
            f":{k}={v}" for k, v in {
                "title" : title,
                "artist": artist,
                "album" : meta.get("album", ""),
            }.items() if v
        ],
        **_cookie_opts(),
    }
    if config.FFMPEG_LOCATION:
        ydl_opts["ffmpeg_location"] = config.FFMPEG_LOCATION

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([search_q])

    mp3_path = out_tmpl.replace(".%(ext)s", ".mp3")
    if cover_path and os.path.exists(cover_path):
        if os.path.exists(mp3_path):
            _inject_cover(mp3_path, cover_path)
        os.remove(cover_path)


def _worker():
    while True:
        task = _q.get()
        if task is None:
            break
        with _lock:
            _tasks[task["id"]]["status"] = "downloading"
        try:
            if task.get("source") == "spotify":
                _download_spotify_track(task)
            else:
                opts = _build_ydl_opts(task)
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([task["url"]])
            with _lock:
                _tasks[task["id"]]["progress"] = 100
                _tasks[task["id"]]["status"]   = "done"
        except Exception as e:
            with _lock:
                _tasks[task["id"]]["status"] = "error"
                _tasks[task["id"]]["error"]  = str(e)
        finally:
            _q.task_done()


for _ in range(config.MAX_CONCURRENT_DOWNLOADS):
    threading.Thread(target=_worker, daemon=True).start()


def enqueue(task_data: dict) -> str:
    task_id = str(uuid.uuid4())[:8]
    task    = {**task_data, "id": task_id, "status": "queued",
               "progress": 0, "speed_kbps": 0, "error": ""}
    with _lock:
        _tasks[task_id] = task
    _q.put(task)
    return task_id


def get_status(task_id: str) -> dict:
    with _lock:
        return dict(_tasks.get(task_id, {}))


def get_all_statuses() -> list:
    with _lock:
        return list(_tasks.values())
