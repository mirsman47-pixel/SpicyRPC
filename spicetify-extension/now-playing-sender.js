// ==SPICETIFY_EXPORTS==
// @source now-playing-sender
// ==/SPICETIFY_EXPORTS==

(function () {
  const SERVER_URL = "http://localhost:8765/update";

  function log() {
    console.log("[Now Playing Sender]", ...arguments);
  }

  function convertSpotifyImageUri(uri) {
    if (!uri) return "";
    // Convert spotify:image:ab67616d... to https://i.scdn.co/image/ab67616d...
    if (uri.startsWith("spotify:image:")) {
      return "https://i.scdn.co/image/" + uri.substring(14);
    }
    // If it's already a full URL, return as-is
    if (uri.startsWith("http://") || uri.startsWith("https://")) {
      return uri;
    }
    return "";
  }

  function sendTrackData() {
    try {
      const data = Spicetify.Player.data;
      if (!data || !data.item) {
        log("No data or item available");
        return;
      }

      const item = data.item;
      // Process cover images
      let coverUrl = "";
      if (item.album && item.album.images && item.album.images.length > 0) {
        // Prefer larger images, but take the first one (usually standard size)
        // Convert Spotify URI to direct URL
        coverUrl = convertSpotifyImageUri(item.album.images[0].url);
      }

      const payload = {
        title: item.name || "Unknown",
        artist: item.artists
          ? item.artists.map((a) => a.name).join(", ")
          : "Unknown",
        album: item.album ? item.album.name : "Unknown",
        cover: coverUrl,
        duration_ms: item.duration.milliseconds || 0,
        position_ms: data.positionAsOfTimestamp + (Date.now() - data.timestamp),
        is_playing: !data.isPaused,
        timestamp: Date.now(),
      };

      log("Sending:", {
        title: payload.title,
        artist: payload.artist,
        position_ms: payload.position_ms,
        duration_ms: payload.duration_ms,
        is_playing: payload.is_playing,
        cover: payload.cover
      });

      fetch(SERVER_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
        .then((response) => {
          if (!response.ok) {
            log("Server error:", response.status, response.statusText);
          }
        })
        .catch((error) => {
          log("Fetch failed:", error);
        });
    } catch (error) {
      log("Error in sendTrackData:", error);
    }
  }

  // Wait for Spicetify.Player to initialize
  function init() {
    if (typeof Spicetify !== "undefined" && Spicetify.Player) {
      log("Spicetify Player found, initializing...");
      Spicetify.Player.addEventListener("songchange", sendTrackData);
      Spicetify.Player.addEventListener("onplaypause", sendTrackData);
      setTimeout(sendTrackData, 1000);
      setInterval(sendTrackData, 1000);
    } else {
      log("Waiting for Spicetify Player...");
      setTimeout(init, 200);
    }
  }

  init();
  log("Extension script loaded");
})();