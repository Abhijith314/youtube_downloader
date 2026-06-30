import spotipy, time
from spotipy.oauth2 import SpotifyClientCredentials
import config

def _sp():
    auth = SpotifyClientCredentials(
        client_id=config.SPOTIFY_CLIENT_ID,
        client_secret=config.SPOTIFY_CLIENT_SECRET,
    )
    return spotipy.Spotify(auth_manager=auth)

def _normalize_track(item) -> dict:
    track = item.get("track") or item
    if not track or track.get("type") == "episode":
        return None
    artists = ", ".join(a["name"] for a in track.get("artists", []))
    album   = track.get("album", {})
    images  = album.get("images", [])
    cover   = images[0]["url"] if images else ""
    title   = track.get("name", "")
    return {
        "title"      : title,
        "artist"     : artists,
        "album"      : album.get("name", ""),
        "cover_url"  : cover,
        "duration_ms": track.get("duration_ms", 0),
        "search_q"   : f"{title} {artists} official audio",
    }

def get_track(track_id: str) -> dict:
    return _normalize_track(_sp().track(track_id))

def get_playlist(playlist_id: str) -> dict:
    sp     = _sp()
    meta   = sp.playlist(playlist_id, fields="name,images")
    tracks = []
    offset = 0
    while True:
        results = sp.playlist_items(
            playlist_id, limit=100, offset=offset,
            fields="items(track(name,artists,album,duration_ms,type)),next"
        )
        for item in results["items"]:
            t = _normalize_track(item)
            if t:
                tracks.append(t)
        if not results.get("next"):
            break
        offset += 100
        time.sleep(0.2)
    images = meta.get("images", [])
    return {
        "name"     : meta["name"],
        "cover_url": images[0]["url"] if images else "",
        "tracks"   : tracks,
    }

def get_album(album_id: str) -> dict:
    sp    = _sp()
    album = sp.album(album_id)
    images= album.get("images", [])
    cover = images[0]["url"] if images else ""
    tracks = []
    for item in album["tracks"]["items"]:
        artists = ", ".join(a["name"] for a in item.get("artists", []))
        name    = item.get("name", "")
        tracks.append({
            "title"      : name,
            "artist"     : artists,
            "album"      : album["name"],
            "cover_url"  : cover,
            "duration_ms": item.get("duration_ms", 0),
            "search_q"   : f"{name} {artists} official audio",
        })
    return {"name": album["name"], "cover_url": cover, "tracks": tracks}
