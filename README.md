# **VIBE-CODED, PLEASE TAKE IT NOT AS SERIOUS AS IT SEEMS TO BE**

# Spotify Now Playing

A local Spotify "Now Playing" overlay for OBS, with optional Discord Rich Presence support.

- **OBS Overlay** — responsive, web-based, works as an OBS Browser Source
- **Discord RPC** — shows current track with album art and progress bar
- **Works with Spotify Free** — no Premium or Spotify Web API keys needed

## How It Works

1. **Spicetify extension** reads `Spicetify.Player.data` from Spotify Desktop and sends it to a local Python HTTP server every 500ms
2. **Python server** receives the data, serves the OBS overlay, and updates Discord Rich Presence
3. **OBS Browser Source** displays the overlay via `http://localhost:8765/overlay`
4. **Web config page** at `http://localhost:8765` lets you customize themes, colors, layout, fonts, and Discord settings in real-time

## Requirements

- Windows 10/11
- Python 3.9+
- Spotify Desktop (Win32, not UWP from Microsoft Store)
- [Spicetify](https://spicetify.app/) installed

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Install the Spicetify extension

Run 
```bash
spicetify enable-devtools
```

Copy the extension to Spicetify's Extensions directory:

```bash
copy /E spicetify-extension %APPDATA%\spicetify\Extensions\
```

Enable it in `config-xpui.json`:
- Run: `spicetify config extensions now-playing-sender.js`
- Run: `spicetify apply`

### 3. Run the server

```bash
python main.py
```

### 4. OBS Setup

Add a **Browser Source** in OBS:
- URL: `http://localhost:8765/overlay`
- Width: `650`, Height: `250` (or your preferred size)
- Custom CSS: `body { margin: 0; padding: 0; background: transparent; }`

### 5. Configure

Open `http://localhost:8765` in your browser to:
- Choose themes (Dark, Light, Neon, Minimal, Spotify, Custom)
- Adjust layout (cover size, show/hide album, progress, time)
- Change fonts and colors
- Enable and configure Discord Rich Presence

## Features

### OBS Overlay
- Fully responsive — adapts to any OBS Browser Source size
- Transparent background option
- Slim/compact mode
- 6 themes: Dark, Light, Neon, Minimal, Spotify, Custom colors
- Live preview in config page

### Discord Rich Presence 
- i did it 'cause in russia we cant use rpc from spotify, idk i was lazy to do it in another project soo..
- Shows song name, artist, album
- Album art (requires registering images in your Discord app)
- Live progress bar with timestamps
- Auto-clears when playback stops
- Custom app name via your own Discord application

### Discord App Setup (for custom name + images)
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application (sets the name shown in Discord)
3. Go to **Rich Presence** → **Add Image(s)** — enter Spotify cover URLs (format: `https://i.scdn.co/image/ab67616d...`)
4. Go to **Bot** → **Reset Token** — copy the bot token
5. In the config page, enter your **Application ID** and **Bot Token**


## Troubleshooting

### No data in overlay?
1. Make sure Spotify Desktop is playing a track
2. Verify Spicetify is loaded: open Spotify DevTools (Ctrl+Shift+I), type `Spicetify.Player.data`
3. Check `spicetify config extensions` shows `now-playing-sender`
4. Run `spicetify apply`

### Discord RPC not working?
1. Enable Discord RPC in the config page
2. For custom app name, you need a bot token (see Discord App Setup above)
3. For album art, you must register images in your Discord app's Rich Presence section as avatar of your app

### Server won't start?
1. Make sure port 8765 is not in use
2. Check firewall allows Python inbound connections

### Other issues?
1. cry
