import yt_dlp
import config

def _size_mb(bytes_val, bitrate_kbps=None, duration_s=None):
    if bytes_val:
        return round(bytes_val / 1_048_576, 1)
    if bitrate_kbps and duration_s:
        return round((bitrate_kbps * 1000 * duration_s) / 8 / 1_048_576, 1)
    return None


def _cookie_opts() -> dict:
    """Return yt-dlp cookie options based on config."""
    opts = {}
    if config.COOKIE_FILE:
        opts["cookiefile"] = config.COOKIE_FILE
    elif config.COOKIE_BROWSER:
        opts["cookiesfrombrowser"] = (config.COOKIE_BROWSER,)
    return opts


def get_formats(url: str) -> dict:
    ydl_opts = {
        "quiet"       : True,
        "no_warnings" : True,
        "skip_download": True,
        **_cookie_opts(),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    duration = info.get("duration", 0)
    video_formats, audio_formats = [], []
    seen_res, seen_abr = set(), set()

    for f in info.get("formats", []):
        vcodec = f.get("vcodec", "none")
        acodec = f.get("acodec", "none")
        size   = _size_mb(
            f.get("filesize") or f.get("filesize_approx"),
            f.get("tbr"), duration
        )

        if vcodec != "none":
            height = f.get("height")
            if not height or height in seen_res:
                continue
            seen_res.add(height)
            video_formats.append({
                "format_id": f["format_id"],
                "quality"  : f"{height}p",
                "ext"      : f.get("ext", "mp4"),
                "size_mb"  : size,
                "fps"      : f.get("fps"),
            })

        elif acodec != "none" and vcodec == "none":
            abr = f.get("abr") or f.get("tbr")
            if not abr:
                continue
            abr_key = round(abr / 16) * 16
            if abr_key in seen_abr:
                continue
            seen_abr.add(abr_key)
            audio_formats.append({
                "format_id": f["format_id"],
                "quality"  : f"{int(abr)} kbps",
                "abr"      : int(abr),
                "ext"      : f.get("ext", "webm"),
                "size_mb"  : size,
            })

    video_formats.sort(key=lambda x: int(x["quality"].replace("p", "")))
    audio_formats.sort(key=lambda x: x["abr"])

    return {
        "title"        : info.get("title", ""),
        "channel"      : info.get("uploader", info.get("channel", "")),
        "duration"     : duration,
        "thumbnail"    : info.get("thumbnail", ""),
        "video_formats": video_formats,
        "audio_formats": audio_formats,
    }
