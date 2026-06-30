import yt_dlp
import config


def _size_mb(bytes_val, bitrate_kbps=None, duration_s=None):
    if bytes_val:
        return round(bytes_val / 1_048_576, 1)
    if bitrate_kbps and duration_s:
        return round((bitrate_kbps * 1000 * duration_s) / 8 / 1_048_576, 1)
    return None


def _cookie_opts() -> dict:
    opts = {}
    if config.COOKIE_FILE:
        opts["cookiefile"] = config.COOKIE_FILE
    elif config.COOKIE_BROWSER:
        opts["cookiesfrombrowser"] = (config.COOKIE_BROWSER,)
    return opts


def _resolve_info(url: str, ydl_opts: dict) -> dict:
    """
    Extract raw info WITHOUT format selection using process=False.
    This completely avoids "Requested format is not available" errors
    because yt-dlp never runs its format-selection pipeline.
    The full formats[] list from the extractor is still returned.
    """
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False, process=False)

    if info is None:
        raise ValueError("Could not extract video information.")

    kind = info.get("_type", "video")

    # youtu.be short links and some YT Music URLs resolve to a url-type entry
    if kind in ("url", "url_transparent"):
        resolved = info.get("url", url)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(resolved, download=False, process=False)
        if info is None:
            raise ValueError("Could not resolve redirected URL.")

    # YT Music sometimes returns a single-entry playlist wrapper
    if kind == "playlist" or "entries" in info:
        entries = info.get("entries") or []
        # entries may be a generator — consume the first item only
        first = None
        for entry in entries:
            first = entry
            break
        if first:
            if first.get("_type") in ("url", "url_transparent"):
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(
                        first.get("url", url), download=False, process=False
                    )
            else:
                info = first

    return info


def get_formats(url: str) -> dict:
    ydl_opts = {
        "quiet"      : True,
        "no_warnings": True,
        **_cookie_opts(),
    }

    info = _resolve_info(url, ydl_opts)

    duration = info.get("duration", 0) or 0
    video_formats, audio_formats = [], []
    seen_res, seen_abr = set(), set()

    for f in info.get("formats") or []:
        vcodec = f.get("vcodec") or "none"
        acodec = f.get("acodec") or "none"
        size   = _size_mb(
            f.get("filesize") or f.get("filesize_approx"),
            f.get("tbr"), duration
        )

        # ── Video stream ───────────────────────────────────────────────────
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

        # ── Audio-only stream ──────────────────────────────────────────────
        elif acodec != "none" and vcodec == "none":
            abr = f.get("abr") or f.get("tbr")
            if not abr:
                continue
            abr_key = round(float(abr) / 16) * 16
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

    # If no audio formats detected (e.g., all formats are muxed), generate defaults
    if not audio_formats and duration:
        for kbps in [128, 192, 256, 320]:
            audio_formats.append({
                "format_id": str(kbps),
                "quality"  : f"{kbps} kbps",
                "abr"      : kbps,
                "ext"      : "mp3",
                "size_mb"  : _size_mb(None, kbps, duration),
            })

    return {
        "title"        : info.get("title", ""),
        "channel"      : info.get("uploader") or info.get("channel", ""),
        "duration"     : duration,
        "thumbnail"    : info.get("thumbnail", ""),
        "video_formats": video_formats,
        "audio_formats": audio_formats,
    }
