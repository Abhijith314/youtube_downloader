import re

PATTERNS = {
    "youtube_playlist" : r"(?:youtube\.com|youtu\.be).*(list=[A-Za-z0-9_\-]+)",
    "youtube_video"    : r"(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_\-]{11})",
    "ytmusic_playlist" : r"music\.youtube\.com.*(list=[A-Za-z0-9_\-]+)",
    "ytmusic_track"    : r"music\.youtube\.com/watch\?v=([A-Za-z0-9_\-]{11})",
    "spotify_playlist" : r"open\.spotify\.com/playlist/([A-Za-z0-9]+)",
    "spotify_album"    : r"open\.spotify\.com/album/([A-Za-z0-9]+)",
    "spotify_track"    : r"open\.spotify\.com/track/([A-Za-z0-9]+)",
}

def detect(url: str) -> dict:
    url = url.strip()
    for kind, pattern in PATTERNS.items():
        m = re.search(pattern, url)
        if m:
            return {"type": kind, "id": m.group(1), "url": url}
    return {"type": "unknown", "id": None, "url": url}

def is_playlist(url_type: str) -> bool:
    return "playlist" in url_type or "album" in url_type
