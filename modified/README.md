# MediaFlow

A no-ads, self-hosted media downloader for YouTube, YouTube Music, and Spotify.

---

## Setup

### 1. Install FFmpeg

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows: download from https://ffmpeg.org and add to PATH
```

### 2. Install Python packages

```bash
pip install -r requirements.txt
```

### 3. Spotify API keys (free)

1. Go to https://developer.spotify.com/dashboard
2. Click Create App, set Redirect URI to http://localhost:8888
3. Copy Client ID and Client Secret

```bash
export SPOTIFY_CLIENT_ID="your_client_id"
export SPOTIFY_CLIENT_SECRET="your_client_secret"
```

### 4. Place files in correct folders

```
mediaflow/
├── app.py
├── config.py
├── requirements.txt
├── modules/
│   ├── __init__.py          <- rename modules_init.py to __init__.py
│   ├── url_detector.py
│   ├── format_fetcher.py
│   ├── spotify_handler.py
│   ├── playlist_manager.py
│   └── download_queue.py
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── main.js
│       └── progress.js
├── templates/
│   └── index.html
└── downloads/               <- create this empty folder
```

### 5. Run

```bash
python app.py
```

Open http://127.0.0.1:5000

---

## Troubleshooting

- MP3 broken: run `ffmpeg -version` and set FFMPEG_LOCATION in config.py
- Spotify 401: check your Client ID and Secret
- Thumbnail not embedded: run `pip install mutagen`
