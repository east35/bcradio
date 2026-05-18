# UI State Contract

The Python backend is authoritative and publishes JSON over `/ws`.

```json
{
  "mode": "idle | station_select | playback | paused | no_connection | soft_off_pending",
  "genre": "Indie",
  "showTitle": "Indie Radio",
  "showDate": "Demo",
  "artistName": "Bandcamp Radio",
  "trackTitle": "signal check",
  "albumArtUrl": "/assets/album art fallback/Art=No.png",
  "trackIndex": 0,
  "trackTotal": 2,
  "elapsedSeconds": 0,
  "durationSeconds": 180,
  "volume": 70,
  "volumeOverlayVisible": false,
  "connectionStatus": "online | offline_cached | offline_unavailable",
  "errorMessage": "",
  "playbackStatus": "playing | paused | fading_in | fading_out | stopped",
  "theme": "light | dark"
}
```

Development keyboard events are sent to the same event interface:

- Left/Right arrows: tuning knob
- Enter: tuning knob push
- Up/Down arrows: volume knob
- Space: volume knob push
- P: power button
