import os

SPOTIFY_CLIENT_ID     = os.getenv("SPOTIFY_CLIENT_ID",     "YOUR_SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "YOUR_SPOTIFY_CLIENT_SECRET")

DOWNLOAD_DIR             = os.path.join(os.path.dirname(__file__), "downloads")
FFMPEG_LOCATION          = os.getenv("FFMPEG_LOCATION", "")
MAX_CONCURRENT_DOWNLOADS = 3

# ── Cookie settings (fix YouTube bot detection) ────────────────────────────
# Option A: auto-read cookies from your browser (recommended for local use)
# Supported: "chrome", "firefox", "edge", "safari", "brave", "opera"
COOKIE_BROWSER = os.getenv("COOKIE_BROWSER", "chrome")

# Option B: path to a cookies.txt file exported from browser
# Leave empty "" to use browser cookies instead
COOKIE_FILE = os.getenv("COOKIE_FILE", "")
