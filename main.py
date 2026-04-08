import asyncio
import json
from datetime import timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import os
import sys
from urllib.parse import urlparse, parse_qs


CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "theme": "dark",
    "custom": {
        "bg_color_1": "#1a1a1a",
        "bg_color_2": "#000000",
        "text_color": "#ffffff",
        "secondary_text_color": "#b3b3b3",
        "accent_color": "#1ed760",
        "progress_bg_color": "#282828",
    },
    "layout": {
        "show_cover": True,
        "cover_size": 120,
        "show_album": True,
        "show_progress": True,
        "show_time": True,
        "horizontal": True,
        "slim_mode": False,
        "transparent_bg": True,
    },
    "fonts": {
        "title_size": 24,
        "artist_size": 18,
        "album_size": 16,
        "time_size": 14,
    },
    "discord": {
        "enabled": True,
        "client_id": "802047772156305438",
        "bot_token": "",
        "show_cover": True,
        "show_album": True,
        "show_progress": True,
        "github_url": "https://github.com/mirsman47-pixel/SpicyRPC",
    },
}

try:
    from pypresence import Presence

    PYPRRESENCE_AVAILABLE = True
except ImportError:
    PYPRRESENCE_AVAILABLE = False


class DiscordRPC:
    _instance = None
    _rpc = None
    _connected = False
    _last_track = ""
    _config = {}
    _update_thread = None
    _running = False
    _pending_data = None
    _lock = threading.Lock()

    @classmethod
    def init(cls, config):
        cls._config = config
        if not config.get("discord", {}).get("enabled", False):
            cls.shutdown()
            return
        if not PYPRRESENCE_AVAILABLE:
            print("  [Discord] pypresence not installed. Run: pip install pypresence")
            return
        cls._connect()

    @classmethod
    def _connect(cls):
        if cls._connected:
            return
        client_id = cls._config.get("discord", {}).get(
            "client_id", "802047772156305438"
        )
        if not client_id:
            client_id = "802047772156305438"
        bot_token = cls._config.get("discord", {}).get("bot_token", "")
        try:
            if bot_token:
                cls._rpc = Presence(client_id, token=bot_token)
            else:
                cls._rpc = Presence(client_id)
            cls._rpc.connect()
            cls._connected = True
            print(f"  [Discord] RPC connected (Client ID: {client_id})")
        except Exception as e:
            cls._connected = False
            print(f"  [Discord] RPC connection failed: {e}")

    @classmethod
    def update(cls, data):
        if not cls._config.get("discord", {}).get("enabled", False):
            return
        if not cls._connected:
            cls._connect()
        if not cls._connected:
            return
        with cls._lock:
            cls._pending_data = data
        if cls._update_thread is None or not cls._update_thread.is_alive():
            cls._update_thread = threading.Thread(target=cls._do_update, daemon=True)
            cls._update_thread.start()

    @classmethod
    def _do_update(cls):
        time.sleep(0.3)
        with cls._lock:
            data = cls._pending_data
        if data is None:
            return
        try:
            discord_cfg = cls._config.get("discord", {})
            title = data.get("title", "")
            artist = data.get("artist", "")
            album = data.get("album", "")
            cover = data.get("cover", "")
            duration_ms = data.get("duration_ms", 0)
            position_ms = data.get("position_ms", 0)
            is_playing = data.get("is_playing", False)

            if not title:
                cls.clear()
                return

            if not is_playing:
                cls.clear()
                return

            track_key = f"{title}|{artist}|{album}|{cover[:20]}"
            cls._last_track = track_key

            large_image = None
            large_text = None

            if discord_cfg.get("show_cover", True) and cover:
                if cover.startswith("https://i.scdn.co/image/"):
                    img_id = cover.replace("https://i.scdn.co/image/", "")
                    large_image = img_id
                elif cover.startswith("spotify:image:"):
                    img_id = cover.replace("spotify:image:", "")
                    large_image = img_id
                elif cover:
                    large_image = cover
                large_text = f"{album}" if album else f"{title} — {artist}"

            start_time = None
            end_time = None
            if (
                discord_cfg.get("show_progress", True)
                and duration_ms > 0
                and is_playing
            ):
                start_time = int(time.time()) - int(position_ms / 1000)
                end_time = start_time + int(duration_ms / 1000)

            state_parts = []
            if artist:
                state_parts.append(artist)
            if album and discord_cfg.get("show_album", True):
                state_parts.append(album)
            state = " - ".join(state_parts) if state_parts else ""

            presence_kwargs = {
                "details": title[:128] if title else "",
                "state": state[:128] if state else "",
                "large_image": large_image[:128]
                if large_image
                else "spotify:ab67616d00001e02",
                "large_text": large_text[:128] if large_text else None,
                "start": start_time,
                "end": end_time,
                "buttons": [
                    {
                        "label": "View on GitHub",
                        "url": discord_cfg.get(
                            "github_url", "https://github.com/mirsman47-pixel/SpicyRPC"
                        ),
                    }
                ],
            }

            presence_kwargs = {
                k: v for k, v in presence_kwargs.items() if v is not None
            }

            if cls._rpc and cls._connected:
                cls._rpc.update(**presence_kwargs)

        except Exception as e:
            pass

    @classmethod
    def clear(cls):
        if not cls._connected:
            return
        cls._last_track = ""
        try:
            if cls._rpc and cls._connected:
                cls._rpc.clear()
        except Exception:
            pass

    @classmethod
    def shutdown(cls):
        cls._connected = False
        cls._last_track = ""
        try:
            if cls._rpc:
                cls._rpc.close()
                cls._rpc = None
        except Exception:
            pass


THEMES = {
    "dark": {
        "bg_color_1": "#1a1a1a",
        "bg_color_2": "#000000",
        "text_color": "#ffffff",
        "secondary_text_color": "#b3b3b3",
        "accent_color": "#1ed760",
        "progress_bg_color": "#282828",
    },
    "light": {
        "bg_color_1": "#f5f5f5",
        "bg_color_2": "#ffffff",
        "text_color": "#191414",
        "secondary_text_color": "#535353",
        "accent_color": "#1ed760",
        "progress_bg_color": "#dcdcdc",
    },
    "neon": {
        "bg_color_1": "#0a0a0a",
        "bg_color_2": "#1a0a2e",
        "text_color": "#00ffff",
        "secondary_text_color": "#ff00ff",
        "accent_color": "#00ff00",
        "progress_bg_color": "#2a0a4e",
    },
    "minimal": {
        "bg_color_1": "transparent",
        "bg_color_2": "transparent",
        "text_color": "#ffffff",
        "secondary_text_color": "#cccccc",
        "accent_color": "#ffffff",
        "progress_bg_color": "rgba(255,255,255,0.2)",
    },
    "spotify": {
        "bg_color_1": "#181818",
        "bg_color_2": "#121212",
        "text_color": "#ffffff",
        "secondary_text_color": "#b3b3b3",
        "accent_color": "#1ed760",
        "progress_bg_color": "#404040",
    },
}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


class NowPlayingHandler(BaseHTTPRequestHandler):
    latest_data = {
        "title": "",
        "artist": "",
        "album": "",
        "cover": "",
        "duration_ms": 0,
        "position_ms": 0,
        "is_playing": False,
        "timestamp": 0,
    }

    config = load_config()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/update":
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                NowPlayingHandler.latest_data.update(data)
                NowPlayingHandler.latest_data["timestamp"] = time.time()
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
                threading.Thread(
                    target=DiscordRPC.update, args=(data,), daemon=True
                ).start()
            except Exception as e:
                self.send_response(400)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
        elif parsed.path == "/config":
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            try:
                config = json.loads(body.decode("utf-8"))
                old_enabled = NowPlayingHandler.config.get("discord", {}).get(
                    "enabled", False
                )
                new_enabled = config.get("discord", {}).get("enabled", False)
                old_client_id = NowPlayingHandler.config.get("discord", {}).get(
                    "client_id", "802047772156305438"
                )
                new_client_id = config.get("discord", {}).get(
                    "client_id", "802047772156305438"
                )
                NowPlayingHandler.config = config
                save_config(config)
                if old_enabled != new_enabled or old_client_id != new_client_id:
                    if new_enabled:
                        threading.Thread(
                            target=DiscordRPC.init, args=(config,), daemon=True
                        ).start()
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"status":"saved"}')
            except Exception as e:
                self.send_response(400)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
        elif parsed.path == "/config/get":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(NowPlayingHandler.config).encode("utf-8"))
        elif parsed.path == "/mock":
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode("utf-8"))
                NowPlayingHandler.latest_data.update(data)
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')
            except Exception:
                self.send_response(400)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/current":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(json.dumps(NowPlayingHandler.latest_data).encode("utf-8"))
        elif parsed.path == "/overlay":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            html = self.get_overlay_html()
            self.wfile.write(html.encode("utf-8"))
        elif parsed.path == "/" or parsed.path == "/config":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            html = self.get_config_page_html()
            self.wfile.write(html.encode("utf-8"))
        elif parsed.path == "/themes":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(THEMES).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

    def get_overlay_html(self):
        config = NowPlayingHandler.config
        theme = config.get("theme", "dark")
        if theme != "custom" and theme in THEMES:
            c = THEMES[theme]
        else:
            c = config.get("custom", DEFAULT_CONFIG["custom"])
        layout = config.get("layout", DEFAULT_CONFIG["layout"])
        fonts = config.get("fonts", DEFAULT_CONFIG["fonts"])

        bg_gradient = (
            f"linear-gradient(135deg, {c['bg_color_1']} 0%, {c['bg_color_2']} 100%)"
        )
        if c["bg_color_1"] == "transparent" or c["bg_color_2"] == "transparent":
            bg_gradient = "transparent"

        cover_display = "flex" if layout.get("show_cover", True) else "none"
        album_display = "block" if layout.get("show_album", True) else "none"
        progress_display = "flex" if layout.get("show_progress", True) else "none"
        time_display = "flex" if layout.get("show_time", True) else "none"
        cover_size = layout.get("cover_size", 120)
        direction = "row" if layout.get("horizontal", True) else "column"
        align = "center" if direction == "column" else "center"
        text_align = "left"
        slim_mode = layout.get("slim_mode", False)
        transparent_bg = layout.get("transparent_bg", True)

        # Font sizes (responsive based on slim mode)
        if slim_mode:
            ts = max(10, fonts.get("title_size", 20) // 2)
            as_ = max(9, fonts.get("artist_size", 16) // 2)
            als = max(9, fonts.get("album_size", 14) // 2)
            tls = max(9, fonts.get("time_size", 12) // 2)
        else:
            ts = fonts.get("title_size", 20)
            as_ = fonts.get("artist_size", 16)
            als = fonts.get("album_size", 14)
            tls = fonts.get("time_size", 12)

        if transparent_bg:
            bg = "transparent"
        else:
            bg = bg_gradient

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Spotify Now Playing</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{
            width: 100%;
            height: 100%;
            overflow: hidden;
            background: transparent;
        }}
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            color: {c["text_color"]};
            display: flex;
            align-items: stretch;
            height: 100%;
            width: 100%;
        }}
        .container {{
            display: flex;
            flex-direction: {direction};
            align-items: {align};
            width: 100%;
            height: 100%;
            gap: {"4px" if slim_mode else "12px"};
            padding: {"4px" if slim_mode else "12px"};
        }}
        .cover-wrap {{
            display: {cover_display};
            flex-shrink: 0;
            width: {cover_size}px;
            height: {cover_size}px;
            min-width: {cover_size}px;
            min-height: {cover_size}px;
            align-items: center;
            justify-content: center;
            border-radius: {"4px" if slim_mode else "8px"};
            overflow: hidden;
            background: rgba(40,40,40,0.6);
            {"width: " + str(cover_size) + "vw; height: " + str(cover_size) + "vw; max-width: " + str(cover_size * 2) + "px; max-height: " + str(cover_size * 2) + "px;" if slim_mode else ""}
        }}
        .cover-wrap img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }}
        .info {{
            flex: 1;
            min-width: 0;
            display: flex;
            flex-direction: column;
            justify-content: center;
            text-align: {text_align};
            overflow: hidden;
            gap: {"2px" if slim_mode else "4px"};
        }}
        .title {{
            font-size: {ts}px;
            font-weight: 700;
            line-height: 1.15;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            color: {c["text_color"]};
            font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif;
        }}
        .artist {{
            font-size: {as_}px;
            color: {c["secondary_text_color"]};
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            font-weight: 400;
        }}
        .album {{
            font-size: {als}px;
            color: {c["secondary_text_color"]};
            opacity: 0.65;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            display: {album_display};
        }}
        .progress-row {{
            display: {progress_display};
            align-items: center;
            gap: {"4px" if slim_mode else "8px"};
            width: 100%;
            margin-top: {"2px" if slim_mode else "4px"};
        }}
        .progress-container {{
            flex: 1;
            height: {"3px" if slim_mode else "5px"};
            background: rgba(128,128,128,0.35);
            border-radius: 2px;
            overflow: hidden;
        }}
        .progress-bar {{
            height: 100%;
            background: {c["accent_color"]};
            width: 0%;
            transition: width 0.4s linear;
            border-radius: 2px;
        }}
        .time-display {{
            display: {time_display};
            gap: 0;
            white-space: nowrap;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: {tls}px;
            color: {c["secondary_text_color"]};
        }}
        .time-display span {{
            display: inline-block;
        }}
        .time-current::after {{
            content: ' / ';
        }}
        /* Responsive scaling */
        @media (max-width: 300px) {{
            .title {{ font-size: {max(8, ts - 4)}px; }}
            .artist {{ font-size: {max(7, as_ - 3)}px; }}
            .album {{ font-size: {max(7, als - 3)}px; }}
            .time-display {{ font-size: {max(7, tls - 3)}px; }}
        }}
        @media (max-width: 400px) {{
            .title {{ font-size: {max(9, ts - 3)}px; }}
            .artist {{ font-size: {max(8, as_ - 2)}px; }}
            .album {{ font-size: {max(8, als - 2)}px; }}
            .time-display {{ font-size: {max(8, tls - 2)}px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="cover-wrap" id="cover-wrap">
            <img id="cover-img" src="" alt="" style="display:none;">
        </div>
        <div class="info">
            <div class="title" id="title">Waiting...</div>
            <div class="artist" id="artist">-</div>
            <div class="album" id="album">-</div>
            <div class="progress-row" id="progress-row">
                <div class="progress-container">
                    <div class="progress-bar" id="progress-bar"></div>
                </div>
                <div class="time-display" id="time-display">
                    <span class="time-current" id="current-time">0:00</span>
                    <span id="total-time">0:00</span>
                </div>
            </div>
        </div>
    </div>

    <script>
        const accentColor = '{c["accent_color"]}';
        const secondaryColor = '{c["secondary_text_color"]}';
        const coverWrap = document.getElementById('cover-wrap');
        const coverImg = document.getElementById('cover-img');
        const titleEl = document.getElementById('title');
        const artistEl = document.getElementById('artist');
        const albumEl = document.getElementById('album');
        const progressBar = document.getElementById('progress-bar');
        const progressRow = document.getElementById('progress-row');
        const currentTimeEl = document.getElementById('current-time');
        const totalTimeEl = document.getElementById('total-time');
        const timeDisplay = document.getElementById('time-display');

        function formatTime(ms) {{
            if (!ms || ms < 0) ms = 0;
            const totalSec = Math.floor(ms / 1000);
            const m = Math.floor(totalSec / 60);
            const s = totalSec % 60;
            return m + ':' + String(s).padStart(2, '0');
        }}

        function updateUI(data) {{
            if (!data) return;
            const hasCover = data.cover && data.cover.length > 0;
            if (hasCover) {{
                coverImg.src = data.cover;
                coverImg.style.display = 'block';
            }} else {{
                coverImg.style.display = 'none';
            }}
            titleEl.textContent = data.title || 'Unknown Track';
            artistEl.textContent = data.artist || 'Unknown Artist';
            albumEl.textContent = data.album || '';
            if (data.duration_ms > 0) {{
                const progress = Math.min(100, Math.max(0, (data.position_ms / data.duration_ms) * 100));
                progressBar.style.width = progress + '%';
                currentTimeEl.textContent = formatTime(data.position_ms);
                totalTimeEl.textContent = formatTime(data.duration_ms);
            }} else {{
                progressBar.style.width = '0%';
                currentTimeEl.textContent = '0:00';
                totalTimeEl.textContent = '0:00';
            }}
            progressBar.style.backgroundColor = data.is_playing ? accentColor : secondaryColor;
        }}

        async function fetchData() {{
            try {{
                const resp = await fetch('/current', {{ cache: 'no-store' }});
                if (!resp.ok) return;
                const data = await resp.json();
                updateUI(data);
            }} catch (e) {{}}
        }}

        fetchData();
        setInterval(fetchData, 500);
    </script>
</body>
</html>"""

    def get_config_page_html(self):
        config = NowPlayingHandler.config
        theme = config.get("theme", "dark")
        custom = config.get("custom", DEFAULT_CONFIG["custom"])
        layout = config.get("layout", DEFAULT_CONFIG["layout"])
        fonts = config.get("fonts", DEFAULT_CONFIG["fonts"])

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spotify Now Playing - Config</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0d0d0d;
            color: #ffffff;
            min-height: 100vh;
        }}
        .app {{
            display: grid;
            grid-template-columns: 380px 1fr;
            min-height: 100vh;
        }}
        .sidebar {{
            background: #161616;
            padding: 24px;
            border-right: 1px solid #282828;
            overflow-y: auto;
        }}
        .sidebar h1 {{
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 8px;
            color: #1ed760;
        }}
        .sidebar .subtitle {{
            font-size: 13px;
            color: #b3b3b3;
            margin-bottom: 28px;
        }}
        .section {{
            margin-bottom: 28px;
        }}
        .section-title {{
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #b3b3b3;
            margin-bottom: 14px;
        }}
        .theme-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }}
        .theme-btn {{
            padding: 12px 8px;
            border-radius: 8px;
            border: 2px solid transparent;
            cursor: pointer;
            text-align: center;
            font-size: 13px;
            font-weight: 500;
            transition: all 0.2s;
            color: #fff;
        }}
        .theme-btn:hover {{ border-color: #444; }}
        .theme-btn.active {{ border-color: #1ed760; }}
        .theme-dark {{ background: linear-gradient(135deg, #1a1a1a, #000); }}
        .theme-light {{ background: linear-gradient(135deg, #f5f5f5, #fff); color: #191414; }}
        .theme-neon {{ background: linear-gradient(135deg, #0a0a0a, #1a0a2e); color: #00ffff; }}
        .theme-minimal {{ background: transparent; border: 1px solid #333; }}
        .theme-spotify {{ background: linear-gradient(135deg, #181818, #121212); }}
        .form-group {{
            margin-bottom: 14px;
        }}
        .form-label {{
            display: block;
            font-size: 13px;
            color: #b3b3b3;
            margin-bottom: 6px;
        }}
        .form-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }}
        input[type="text"], input[type="number"] {{
            width: 100%;
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid #333;
            background: #282828;
            color: #fff;
            font-size: 13px;
            outline: none;
        }}
        input[type="text"]:focus, input[type="number"]:focus {{ border-color: #1ed760; }}
        input[type="color"] {{
            width: 100%;
            height: 36px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            background: transparent;
            padding: 0;
        }}
        .toggle-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #222;
        }}
        .toggle-row:last-child {{ border-bottom: none; }}
        .toggle-label {{
            font-size: 13px;
            color: #ddd;
        }}
        .toggle {{
            width: 40px;
            height: 22px;
            border-radius: 11px;
            background: #404040;
            cursor: pointer;
            position: relative;
            transition: background 0.2s;
        }}
        .toggle.on {{ background: #1ed760; }}
        .toggle::after {{
            content: '';
            position: absolute;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: #fff;
            top: 2px;
            left: 2px;
            transition: transform 0.2s;
        }}
        .toggle.on::after {{ transform: translateX(18px); }}
        .btn {{
            width: 100%;
            padding: 12px;
            border-radius: 20px;
            border: none;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            margin-top: 8px;
        }}
        .btn-save {{
            background: #1ed760;
            color: #000;
        }}
        .btn-save:hover {{ background: #1db954; }}
        .btn-reset {{
            background: #282828;
            color: #fff;
        }}
        .btn-reset:hover {{ background: #333; }}
        .preview-area {{
            padding: 24px;
            display: flex;
            flex-direction: column;
            align-items: center;
            overflow-y: auto;
        }}
        .preview-label {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #555;
            margin-bottom: 16px;
            align-self: flex-start;
        }}
        .preview-frame {{
            width: 100%;
            max-width: 640px;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
            resize: vertical;
            overflow: auto;
            min-height: 80px;
            border: 1px solid #2a2a2a;
            background: #000;
        }}
        .preview-frame iframe {{
            width: 100%;
            height: 140px;
            border: none;
            display: block;
        }}
        .preview-label {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #555;
            margin-bottom: 8px;
            align-self: flex-start;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .preview-label span {{
            background: #222;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 10px;
            color: #888;
        }}
        .mock-controls {{
            margin-top: 20px;
            width: 100%;
            max-width: 480px;
            background: #1a1a1a;
            border-radius: 12px;
            padding: 16px;
        }}
        .mock-controls h3 {{
            font-size: 13px;
            color: #b3b3b3;
            margin-bottom: 12px;
        }}
        .mock-row {{
            margin-bottom: 10px;
        }}
        .mock-row label {{
            font-size: 12px;
            color: #888;
            display: block;
            margin-bottom: 4px;
        }}
        .mock-row input {{
            width: 100%;
            padding: 6px 10px;
            border-radius: 6px;
            border: 1px solid #333;
            background: #222;
            color: #fff;
            font-size: 12px;
        }}
        .slider-row {{
            margin-bottom: 12px;
        }}
        .slider-row label {{
            font-size: 12px;
            color: #888;
            display: flex;
            justify-content: space-between;
            margin-bottom: 4px;
        }}
        .slider-row label span {{
            color: #1ed760;
            font-family: monospace;
        }}
        input[type="range"] {{
            width: 100%;
            height: 4px;
            border-radius: 2px;
            background: #333;
            outline: none;
            -webkit-appearance: none;
        }}
        input[type="range"]::-webkit-slider-thumb {{
            -webkit-appearance: none;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: #1ed760;
            cursor: pointer;
        }}
        .slider-group {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }}
        .copy-box {{
            margin-top: 16px;
            background: #1a1a1a;
            border-radius: 8px;
            padding: 12px;
        }}
        .copy-box label {{
            font-size: 11px;
            color: #666;
            display: block;
            margin-bottom: 6px;
        }}
        .copy-url {{
            display: flex;
            gap: 8px;
        }}
        .copy-url input {{
            flex: 1;
            padding: 6px 10px;
            border-radius: 6px;
            border: 1px solid #333;
            background: #222;
            color: #888;
            font-size: 12px;
            font-family: monospace;
        }}
        .copy-url button {{
            padding: 6px 12px;
            border-radius: 6px;
            border: none;
            background: #333;
            color: #fff;
            font-size: 12px;
            cursor: pointer;
        }}
        .copy-url button:hover {{ background: #444; }}
        .toast {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #1ed760;
            color: #000;
            padding: 12px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            transform: translateY(100px);
            opacity: 0;
            transition: all 0.3s;
            z-index: 9999;
        }}
        .toast.show {{
            transform: translateY(0);
            opacity: 1;
        }}
        .status-bar {{
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: #0a0a0a;
            border-top: 1px solid #222;
            padding: 8px 16px;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: #666;
        }}
        .status-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #444;
        }}
        .status-dot.live {{
            background: #1ed760;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        @media (max-width: 700px) {{
            .app {{ grid-template-columns: 1fr; }}
            .sidebar {{ border-right: none; border-bottom: 1px solid #282828; }}
        }}
    </style>
</head>
<body>
    <div class="app">
        <div class="sidebar">
            <h1>Spotify Now Playing</h1>
            <p class="subtitle">Customize your OBS overlay</p>

            <div class="section">
                <div class="section-title">Theme</div>
                <div class="theme-grid">
                    <button class="theme-btn theme-dark {"active" if theme == "dark" else ""}" data-theme="dark">Dark</button>
                    <button class="theme-btn theme-light {"active" if theme == "light" else ""}" data-theme="light">Light</button>
                    <button class="theme-btn theme-neon {"active" if theme == "neon" else ""}" data-theme="neon">Neon</button>
                    <button class="theme-btn theme-minimal {"active" if theme == "minimal" else ""}" data-theme="minimal">Minimal</button>
                    <button class="theme-btn theme-spotify {"active" if theme == "spotify" else ""}" data-theme="spotify">Spotify</button>
                    <button class="theme-btn theme-custom {"active" if theme == "custom" else ""}" data-theme="custom" id="customThemeBtn">Custom</button>
                </div>
            </div>

            <div class="section" id="customColors" style="display: {"block" if theme == "custom" else "none"};">
                <div class="section-title">Custom Colors</div>
                <div class="form-row">
                    <div class="form-group">
                        <label class="form-label">Background 1</label>
                        <input type="color" id="bgColor1" value="{custom["bg_color_1"]}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Background 2</label>
                        <input type="color" id="bgColor2" value="{custom["bg_color_2"]}">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label class="form-label">Text Color</label>
                        <input type="color" id="textColor" value="{custom["text_color"]}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Secondary Text</label>
                        <input type="color" id="secondaryTextColor" value="{custom["secondary_text_color"]}">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label class="form-label">Accent (Progress)</label>
                        <input type="color" id="accentColor" value="{custom["accent_color"]}">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Progress BG</label>
                        <input type="color" id="progressBgColor" value="{custom["progress_bg_color"]}">
                    </div>
                </div>
            </div>

            <div class="section">
                <div class="section-title">Layout</div>
                <div class="toggle-row">
                    <span class="toggle-label">Transparent Background</span>
                    <div class="toggle {"on" if layout.get("transparent_bg", True) else ""}" data-toggle="transparent_bg"></div>
                </div>
                <div class="toggle-row">
                    <span class="toggle-label">Slim Mode (compact)</span>
                    <div class="toggle {"on" if layout.get("slim_mode", False) else ""}" data-toggle="slim_mode"></div>
                </div>
                <div class="toggle-row">
                    <span class="toggle-label">Show Album Cover</span>
                    <div class="toggle {"on" if layout.get("show_cover", True) else ""}" data-toggle="show_cover"></div>
                </div>
                <div class="toggle-row">
                    <span class="toggle-label">Show Album Name</span>
                    <div class="toggle {"on" if layout.get("show_album", True) else ""}" data-toggle="show_album"></div>
                </div>
                <div class="toggle-row">
                    <span class="toggle-label">Show Progress Bar</span>
                    <div class="toggle {"on" if layout.get("show_progress", True) else ""}" data-toggle="show_progress"></div>
                </div>
                <div class="toggle-row">
                    <span class="toggle-label">Show Time</span>
                    <div class="toggle {"on" if layout.get("show_time", True) else ""}" data-toggle="show_time"></div>
                </div>
                <div class="toggle-row">
                    <span class="toggle-label">Horizontal Layout</span>
                    <div class="toggle {"on" if layout.get("horizontal", True) else ""}" data-toggle="horizontal"></div>
                </div>
                <div class="form-group" style="margin-top: 12px;">
                    <label class="form-label">Cover Size (px)</label>
                    <input type="number" id="coverSize" value="{layout.get("cover_size", 120)}" min="40" max="300">
                </div>
            </div>

            <div class="section">
                <div class="section-title">Font Sizes (px)</div>
                <div class="slider-group">
                    <div class="slider-row">
                        <label>Title <span id="titleSizeVal">{fonts.get("title_size", 20)}</span></label>
                        <input type="range" id="titleSize" min="8" max="48" value="{fonts.get("title_size", 20)}">
                    </div>
                    <div class="slider-row">
                        <label>Artist <span id="artistSizeVal">{fonts.get("artist_size", 16)}</span></label>
                        <input type="range" id="artistSize" min="8" max="32" value="{fonts.get("artist_size", 16)}">
                    </div>
                    <div class="slider-row">
                        <label>Album <span id="albumSizeVal">{fonts.get("album_size", 14)}</span></label>
                        <input type="range" id="albumSize" min="8" max="26" value="{fonts.get("album_size", 14)}">
                    </div>
                    <div class="slider-row">
                        <label>Time <span id="timeSizeVal">{fonts.get("time_size", 12)}</span></label>
                        <input type="range" id="timeSize" min="8" max="22" value="{fonts.get("time_size", 12)}">
                    </div>
                </div>
            </div>

            <div class="section">
                <div class="section-title">Discord Rich Presence</div>
                <div class="toggle-row">
                    <span class="toggle-label">Enable Discord RPC</span>
                    <div class="toggle {"on" if config.get("discord", {}).get("enabled", False) else ""}" data-discord="enabled" id="discordEnabled"></div>
                </div>
                <div class="form-group" style="margin-top: 12px;">
                    <label class="form-label">Discord Application ID</label>
                    <input type="text" id="discordClientId" value="{config.get("discord", {}).get("client_id", "802047772156305438")}" placeholder="802047772156305438" style="font-size: 12px;">
                </div>
                <p style="font-size: 11px; color: #666; margin-top: 4px; margin-bottom: 10px;">
                    Use your own app's Application ID from
                    <a href="https://discord.com/developers/applications" target="_blank" style="color: #1ed760;">discord.com/developers</a>
                    to display a custom app name. Also add a Bot and copy the token below.
                </p>
                <div class="form-group" style="margin-top: 12px;">
                    <label class="form-label">Bot Token (optional, for custom app name)</label>
                    <input type="password" id="discordBotToken" value="{config.get("discord", {}).get("bot_token", "")}" placeholder="Bot token from your application's Bot settings" style="font-size: 12px;">
                </div>
                <p style="font-size: 11px; color: #888; margin-top: 4px; margin-bottom: 10px;">
                    Go to your app → Bot → Reset Token. Required for custom app names in RPC.
                </p>
                <div class="form-group" style="margin-top: 12px;">
                    <label class="form-label">GitHub URL (shown in Discord button)</label>
                    <input type="text" id="discordGithubUrl" value="{config.get("discord", {}).get("github_url", "https://github.com/mirsman47-pixel/SpicyRPC")}" placeholder="https://github.com/..." style="font-size: 12px;">
                </div>
                <div class="toggle-row">
                    <span class="toggle-label">Show Album Cover</span>
                    <div class="toggle {"on" if config.get("discord", {}).get("show_cover", True) else ""}" data-discord="show_cover"></div>
                </div>
                <div class="toggle-row">
                    <span class="toggle-label">Show Album Name</span>
                    <div class="toggle {"on" if config.get("discord", {}).get("show_album", True) else ""}" data-discord="show_album"></div>
                </div>
                <div class="toggle-row">
                    <span class="toggle-label">Show Progress Bar</span>
                    <div class="toggle {"on" if config.get("discord", {}).get("show_progress", True) else ""}" data-discord="show_progress"></div>
                </div>
                <div id="discordStatus" style="margin-top: 10px; font-size: 12px; color: #888;"></div>
            </div>

            <button class="btn btn-save" id="saveBtn">Save Settings</button>
            <button class="btn btn-reset" id="resetBtn">Reset to Default</button>

            <div class="copy-box">
                <label>Overlay URL for OBS Browser Source</label>
                <div class="copy-url">
                    <input type="text" value="http://localhost:8765/overlay" readonly id="overlayUrl">
                    <button id="copyBtn">Copy</button>
                </div>
            </div>
        </div>

        <div class="preview-area">
            <div class="preview-label">
                Live Preview
                <span>Resize handle at bottom-right</span>
            </div>
            <div class="preview-frame">
                <iframe id="previewIframe" src="/overlay"></iframe>
            </div>

            <div class="mock-controls">
                <h3>Mock Data Preview (for testing without Spotify)</h3>
                <div class="mock-row">
                    <label>Track Title</label>
                    <input type="text" id="mockTitle" value="Blinding Lights" placeholder="Track title">
                </div>
                <div class="mock-row">
                    <label>Artist</label>
                    <input type="text" id="mockArtist" value="The Weeknd" placeholder="Artist name">
                </div>
                <div class="mock-row">
                    <label>Album</label>
                    <input type="text" id="mockAlbum" value="After Hours" placeholder="Album name">
                </div>
                <div class="mock-row">
                    <label>Cover URL</label>
                    <input type="text" id="mockCover" value="https://i.scdn.co/image/ab67616d00001e02c449b2e5a5d8e4a3c6d7e8f9" placeholder="https://...">
                </div>
                <div class="form-row" style="margin-top: 8px;">
                    <div class="form-group">
                        <label class="form-label">Position (ms)</label>
                        <input type="number" id="mockPosition" value="45000" min="0">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Duration (ms)</label>
                        <input type="number" id="mockDuration" value="200000" min="1">
                    </div>
                </div>
                <div class="toggle-row">
                    <span class="toggle-label">Is Playing</span>
                    <div class="toggle on" id="mockPlaying"></div>
                </div>
                <button class="btn btn-save" id="applyMockBtn" style="margin-top: 12px;">Apply Mock Data</button>
                <button class="btn btn-reset" id="clearMockBtn">Clear Mock Data</button>
            </div>
        </div>
    </div>

    <div class="status-bar">
        <div class="status-dot" id="statusDot"></div>
        <span id="statusText">Waiting for Spotify...</span>
    </div>

    <div class="toast" id="toast">Settings saved!</div>

    <script>
        let currentConfig = {json.dumps(config, ensure_ascii=False)};
        let previewTimer = null;

        // Theme selection
        document.querySelectorAll('.theme-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                document.querySelectorAll('.theme-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const theme = btn.dataset.theme;
                currentConfig.theme = theme;
                document.getElementById('customColors').style.display = theme === 'custom' ? 'block' : 'none';
                refreshPreview();
            }});
        }});

        // Custom color inputs
        document.querySelectorAll('#customColors input[type="color"]').forEach(input => {{
            input.addEventListener('input', () => {{
                if (!currentConfig.custom) currentConfig.custom = {{}};
                currentConfig.custom[input.id.replace('Color', '_color').replace('bg', 'bg_').replace('text', 'text_').replace('secondary', 'secondary_').replace('accent', 'accent_').replace('progress', 'progress_')] = input.value;
                currentConfig.theme = 'custom';
                document.querySelectorAll('.theme-btn').forEach(b => b.classList.remove('active'));
                document.getElementById('customThemeBtn').classList.add('active');
                document.getElementById('customColors').style.display = 'block';
            }});
        }});

        // Discord toggles
        document.querySelectorAll('[data-discord]').forEach(el => {{
            el.addEventListener('click', (e) => {{
                e.stopPropagation();
                if (el.classList.contains('toggle')) {{
                    el.classList.toggle('on');
                    if (!currentConfig.discord) currentConfig.discord = {{}};
                    const key = el.dataset.discord;
                    currentConfig.discord[key] = el.classList.contains('on');
                }}
            }});
        }});

        // Discord Client ID input
        const discordClientIdInput = document.getElementById('discordClientId');
        if (discordClientIdInput) {{
            discordClientIdInput.addEventListener('change', (e) => {{
                if (!currentConfig.discord) currentConfig.discord = {{}};
                currentConfig.discord.client_id = e.target.value.trim();
            }});
        }}

        // Discord Bot Token input
        const discordBotTokenInput = document.getElementById('discordBotToken');
        if (discordBotTokenInput) {{
            discordBotTokenInput.addEventListener('change', (e) => {{
                if (!currentConfig.discord) currentConfig.discord = {{}};
                currentConfig.discord.bot_token = e.target.value.trim();
            }});
        }}

        // Discord GitHub URL input
        const discordGithubUrlInput = document.getElementById('discordGithubUrl');
        if (discordGithubUrlInput) {{
            discordGithubUrlInput.addEventListener('change', (e) => {{
                if (!currentConfig.discord) currentConfig.discord = {{}};
                currentConfig.discord.github_url = e.target.value.trim();
            }});
        }}

        // Init Discord config from loaded config
        if (currentConfig.discord) {{
            const statusEl = document.getElementById('discordStatus');
            if (currentConfig.discord.enabled) {{
                statusEl.innerHTML = '<span style="color:#1ed760;">Discord RPC is enabled.</span><br><span style="color:#666;">Make sure Discord is running.</span>';
            }} else {{
                statusEl.textContent = 'Discord RPC is disabled.';
            }}
        }}

        // Toggles
        document.querySelectorAll('.toggle').forEach(toggle => {{
            if (toggle.dataset.toggle) {{
                toggle.addEventListener('click', () => {{
                    toggle.classList.toggle('on');
                    if (!currentConfig.layout) currentConfig.layout = {{}};
                    const key = toggle.dataset.toggle;
                    currentConfig.layout[key] = toggle.classList.contains('on');
                    if (key === 'cover_size') return;
                    refreshPreview();
                }});
            }}
        }});

        // Cover size
        document.getElementById('coverSize').addEventListener('change', (e) => {{
            if (!currentConfig.layout) currentConfig.layout = {{}};
            currentConfig.layout.cover_size = parseInt(e.target.value);
            refreshPreview();
        }});

        // Font sliders
        ['title', 'artist', 'album', 'time'].forEach(type => {{
            const slider = document.getElementById(type + 'Size');
            const val = document.getElementById(type + 'SizeVal');
            if (slider && val) {{
                slider.addEventListener('input', () => {{
                    val.textContent = slider.value;
                    if (!currentConfig.fonts) currentConfig.fonts = {{}};
                    currentConfig.fonts[type + '_size'] = parseInt(slider.value);
                    refreshPreview();
                }});
            }}
        }});

        // Save
        document.getElementById('saveBtn').addEventListener('click', async () => {{
            try {{
                const resp = await fetch('/config', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(currentConfig)
                }});
                if (resp.ok) {{
                    showToast('Settings saved!');
                }}
            }} catch (e) {{
                showToast('Error saving!');
            }}
        }});

        // Reset
        document.getElementById('resetBtn').addEventListener('click', () => {{
            currentConfig = JSON.parse(JSON.stringify({json.dumps(DEFAULT_CONFIG, ensure_ascii=False)}));
            applyConfigToUI();
            refreshPreview();
            showToast('Reset to defaults!');
        }});

        function applyConfigToUI() {{
            document.querySelectorAll('.theme-btn').forEach(b => b.classList.remove('active'));
            const themeBtn = document.querySelector(`[data-theme="${{currentConfig.theme}}"]`);
            if (themeBtn) themeBtn.classList.add('active');
            document.getElementById('customColors').style.display = currentConfig.theme === 'custom' ? 'block' : 'none';
            const c = currentConfig.theme !== 'custom' && {json.dumps(list(THEMES.keys()))}.includes(currentConfig.theme)
                ? {json.dumps(THEMES)}[currentConfig.theme]
                : currentConfig.custom || {{}};
            if (currentConfig.theme === 'custom' && currentConfig.custom) {{
                document.getElementById('bgColor1').value = currentConfig.custom.bg_color_1 || '#1a1a1a';
                document.getElementById('bgColor2').value = currentConfig.custom.bg_color_2 || '#000000';
                document.getElementById('textColor').value = currentConfig.custom.text_color || '#ffffff';
                document.getElementById('secondaryTextColor').value = currentConfig.custom.secondary_text_color || '#b3b3b3';
                document.getElementById('accentColor').value = currentConfig.custom.accent_color || '#1ed760';
                document.getElementById('progressBgColor').value = currentConfig.custom.progress_bg_color || '#282828';
            }}
            if (currentConfig.layout) {{
                document.querySelectorAll('[data-toggle]').forEach(t => {{
                    t.classList.toggle('on', currentConfig.layout[t.dataset.toggle] !== false);
                }});
                document.getElementById('coverSize').value = currentConfig.layout.cover_size || 120;
            }}
            if (currentConfig.fonts) {{
                ['title', 'artist', 'album', 'time'].forEach(type => {{
                    const val = currentConfig.fonts[type + '_size'];
                    if (val) {{
                        const slider = document.getElementById(type + 'Size');
                        const label = document.getElementById(type + 'SizeVal');
                        if (slider) slider.value = val;
                        if (label) label.textContent = val;
                    }}
                }});
            }}
        }}

        function refreshPreview() {{
            clearTimeout(previewTimer);
            previewTimer = setTimeout(async () => {{
                try {{
                    await fetch('/config', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify(currentConfig)
                    }});
                    const iframe = document.getElementById('previewIframe');
                    iframe.src = '/overlay?t=' + Date.now();
                }} catch (e) {{}}
            }}, 300);
        }}

        // Mock data
        document.getElementById('mockPlaying').addEventListener('click', function() {{
            this.classList.toggle('on');
        }});

        document.getElementById('applyMockBtn').addEventListener('click', async () => {{
            const data = {{
                title: document.getElementById('mockTitle').value,
                artist: document.getElementById('mockArtist').value,
                album: document.getElementById('mockAlbum').value,
                cover: document.getElementById('mockCover').value,
                duration_ms: parseInt(document.getElementById('mockDuration').value) || 200000,
                position_ms: parseInt(document.getElementById('mockPosition').value) || 0,
                is_playing: document.getElementById('mockPlaying').classList.contains('on'),
                timestamp: Date.now()
            }};
            await fetch('/mock', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(data)
            }});
            const iframe = document.getElementById('previewIframe');
            iframe.src = '/overlay?t=' + Date.now();
        }});

        document.getElementById('clearMockBtn').addEventListener('click', async () => {{
            await fetch('/mock', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{
                    title: '', artist: '', album: '', cover: '',
                    duration_ms: 0, position_ms: 0, is_playing: false, timestamp: 0
                }})
            }});
            const iframe = document.getElementById('previewIframe');
            iframe.src = '/overlay?t=' + Date.now();
        }});

        // Copy URL
        document.getElementById('copyBtn').addEventListener('click', () => {{
            navigator.clipboard.writeText(document.getElementById('overlayUrl').value);
            showToast('URL copied!');
        }});

        function showToast(msg) {{
            const toast = document.getElementById('toast');
            toast.textContent = msg;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 2000);
        }}

        // Auto-apply mock data on load so preview always shows something
        (async function initPreview() {{
            try {{
                const resp = await fetch('/current', {{ cache: 'no-store' }});
                const data = await resp.json();
                if (!data.title) {{
                    // No Spotify data — apply mock so preview isn't empty
                    const mockData = {{
                        title: 'Blinding Lights',
                        artist: 'The Weeknd',
                        album: 'After Hours',
                        cover: 'https://i.scdn.co/image/ab67616d00001e02c449b2e5a5d8e4a3c6d7e8f9',
                        duration_ms: 200000,
                        position_ms: 45000,
                        is_playing: true,
                        timestamp: Date.now()
                    }};
                    await fetch('/mock', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify(mockData)
                    }});
                    // Fill mock form fields too
                    document.getElementById('mockTitle').value = mockData.title;
                    document.getElementById('mockArtist').value = mockData.artist;
                    document.getElementById('mockAlbum').value = mockData.album;
                    document.getElementById('mockCover').value = mockData.cover;
                    document.getElementById('mockDuration').value = mockData.duration_ms;
                    document.getElementById('mockPosition').value = mockData.position_ms;
                }}
            }} catch (e) {{}}
        }})();

        // Status polling
        async function checkStatus() {{
            try {{
                const resp = await fetch('/current', {{ cache: 'no-store' }});
                const data = await resp.json();
                const dot = document.getElementById('statusDot');
                const text = document.getElementById('statusText');
                if (data.title) {{
                    dot.classList.add('live');
                    text.textContent = `Now playing: ${{data.title}} - ${{data.artist}}`;
                }} else {{
                    dot.classList.remove('live');
                    text.textContent = 'Waiting for Spotify...';
                }}
            }} catch (e) {{
                document.getElementById('statusDot').classList.remove('live');
                document.getElementById('statusText').textContent = 'Server offline';
            }}
        }}
        checkStatus();
        setInterval(checkStatus, 3000);
    </script>
</body>
</html>"""


def start_server():
    server = HTTPServer(("localhost", 8765), NowPlayingHandler)
    server.serve_forever()


async def main():
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    discord_cfg = NowPlayingHandler.config.get("discord", {})
    if discord_cfg.get("enabled", False):

        def init_discord():
            DiscordRPC.init(NowPlayingHandler.config)

        threading.Thread(target=init_discord, daemon=True).start()

    print("=" * 50)
    print("  Spotify Now Playing Server")
    print("=" * 50)
    print()
    print("  Config Page:  http://localhost:8765")
    print("  Overlay:     http://localhost:8765/overlay")
    print()
    if discord_cfg.get("enabled", False):
        client_id = discord_cfg.get("client_id", "802047772156305438")
        print(f"  Discord RPC:  Enabled (Client ID: {client_id})")
    else:
        print("  Discord RPC:  Disabled (enable in config page)")
    print()
    print("  Make sure Spicetify extension is installed")
    print("  and Spotify Desktop is running.")
    print()
    print("  Press Ctrl+C to stop.")
    print("=" * 50)

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped.")
