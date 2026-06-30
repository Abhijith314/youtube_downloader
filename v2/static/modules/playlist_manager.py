import yt_dlp
import config

def _cookie_opts() -> dict:
    opts = {}
    if config.COOKIE_FILE:
        opts["cookiefile"] = config.COOKIE_FILE
    elif config.COOKIE_BROWSER:
        opts["cookiesfrombrowser"] = (config.COOKIE_BROWSER,)
    return opts

def get_youtube_playlist(url: str) -> dict:
    ydl_opts = {
        "quiet"        : True,
        "extract_flat" : "in_playlist",
        "skip_download": True,
        "no_warnings"  : True,
        **_cookie_opts(),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    tracks = []
    for entry in info.get("entries", []):
        if not entry:
            continue
        dur    = entry.get("duration", 0)
        vid_id = entry.get("id", "")
        tracks.append({
            "title"      : entry.get("title", "Unknown"),
            "artist"     : entry.get("uploader", entry.get("channel", "")),
            "album"      : info.get("title", ""),
            "duration_ms": int(dur * 1000) if dur else 0,
            "url"        : f"https://www.youtube.com/watch?v={vid_id}",
            "cover_url"  : entry.get("thumbnail", ""),
            "search_q"   : None,
        })
    return {
        "name"     : info.get("title", "Playlist"),
        "cover_url": info.get("thumbnail", ""),
        "tracks"   : tracks,
    }
