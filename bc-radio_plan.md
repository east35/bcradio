# Bandcamp Radio Radio Pi Prototype Plan

## Summary

Build a v1 Raspberry Pi prototype that turns the current brief, interaction flow, and UX reference assets into a working kiosk radio: Python owns state, mpv owns audio playback, React renders the LCD UI, and controls can be driven by GPIO or simulated keyboard input during development.

The prototype should feel like a radio, not a browser player. Playback transitions must be softened with short fades, station selection should not interrupt current music until confirmed, and the power button should put the Pi into a safe-to-unplug state.

## Key Changes

- Create a Python backend with an explicit state machine for `off`, `idle`, `station_select`, `playback`, `paused`, and `no_connection`.
- Treat the volume display as transient UI overlay metadata, not a top-level playback state.
- Implement power button behavior as soft off: fade out audio over 0.5 seconds, stop playback, flush any needed state/cache writes, then shut down the Pi so it is safe to unplug from wall power.
- Apply 0.5 second fade transitions for all music changes: play, pause, stop, track change, station change, and power off.
- Add Bandcamp Radio episode fetching for the six genres: Electronic, Selects, Hip-Hop, Indie, Metal, Games.
- Cache episode lists locally with a 1 hour TTL and tolerate brief network failures by using the most recent cache.
- Keep playback resume state only for the current powered session. After shutdown/off, the next boot should start from the latest episode instead of restoring old playback position.
- Control mpv through IPC for load, play, pause, stop, previous/next track, progress, volume, and fade orchestration.
- Expose backend state to the React kiosk UI over WebSocket; the browser remains render-only.
- Support keyboard controls first for development, then add encoder adapters for Raspberry Pi GPIO or USB encoder input behind the same event interface.
- Build the 4 inch LCD UI around the briefed screens and provided assets: clock idle, station select, playback, paused, no-wifi error, volume toast, and time-based light/dark LCD themes.

## Interaction Rules

- Tuning knob turn supports both directions.
- In station select, tuning left/right moves through genres; existing music keeps playing until the selected station is confirmed.
- Tuning knob push enters station select from idle/playback and confirms the selected station from station select.
- Confirming a different station fades out the current show, loads the selected station, then fades in.
- Confirming the same station returns to playback and resumes the current in-session position.
- In playback, tuning right advances to the next track and tuning left restarts the current track.
- In paused, tuning right advances to the next track and tuning left restarts the current track, while remaining paused.
- Volume knob turn adjusts volume and shows a transient overlay over the current screen.
- Volume knob push toggles play/pause using a 0.5 second fade.
- Power button starts the soft-off shutdown flow from any active state.
- If there is no network connection and no usable cached episode data for the requested action, show the no-connection state from `assets/screenshots/UI state=No Wifi.png`.
- If there is no network connection but cached episode data is usable, keep the radio playable from cache and avoid showing the no-connection state unless playback cannot continue.

## UI Data Contract

Backend state sent to the React UI should include enough metadata to render the provided reference screens:

- `mode`: `idle`, `station_select`, `playback`, `paused`, `no_connection`, or `soft_off_pending`
- `genre`: display station, such as Indie or Metal
- `showTitle`
- `showDate`
- `artistName`
- `trackTitle`
- `albumArtUrl`
- `trackIndex`
- `trackTotal`
- `elapsedSeconds`
- `durationSeconds`
- `volume`
- `volumeOverlayVisible`
- `connectionStatus`: `online`, `offline_cached`, or `offline_unavailable`
- `errorMessage`: short display-safe message for no-connection state, such as `no connection`
- `playbackStatus`: `playing`, `paused`, `fading_in`, `fading_out`, or `stopped`
- `theme`: `light` between 8:00 AM and 7:00 PM local time, otherwise `dark`

Album art should come from Bandcamp track metadata whenever available. If artwork is unavailable, use `assets/album art fallback/Art=No.png`.

Use the local Pixelify Sans font files and the provided play/pause SVG icons. Use `assets/screenshots/UI state=No Wifi.png` as the visual reference for the no-connection state. Normalize the UI to the actual Waveshare display resolution during implementation; current reference screenshots are 800px wide, with playback represented at 800x480 and other states at 800x400.

## UI Theme Rules

- Theme is selected from local device time.
- Use light mode from 8:00 AM through 6:59 PM.
- Use dark mode from 7:00 PM through 7:59 AM.
- Light mode:
  - Fonts, icons, and fills use `#171717`.
  - Background uses `#C8C8C8`.
  - All fonts and icons use a drop shadow to emulate an old LCD screen: `x: 0`, `y: 4`, `blur: 2`, `spread: 0`, color `#000000` at 16% opacity.
  - The background uses an inner shadow to emulate an old LCD screen: `x: 0`, `y: 0`, `blur: 4`, `spread: 0`.
  - Album artwork renders grayscale with a pixelated overlay to emulate an old LCD screen.
- Dark mode:
  - Fonts, icons, and fills use `#E4E4E4`.
  - Background uses `#222222`.

## Implementation Order

1. Scaffold the app structure: Python backend, React frontend, shared state/event contract, local config, and run scripts.
2. Implement the backend state machine, session-only playback memory, and input event normalization.
3. Add mpv IPC integration with 0.5 second fade helpers and fake/static episode data to validate playback flow.
4. Spike and implement Bandcamp episode discovery, including show metadata, track metadata, artwork URLs, local cache, and no-connection detection/fallback behavior.
5. Build the React kiosk UI against mocked WebSocket state using the assets in `assets/`, including light/dark theme behavior, then connect it to the backend.
6. Add Raspberry Pi runtime setup: kiosk browser launch, systemd service, mpv dependency notes, shutdown command, and hardware input adapter.
7. Tune the prototype on the Pi 3B + Waveshare display for legibility, boot behavior, shutdown behavior, and control latency.

## Test Plan

- Unit test state transitions for all documented knob, push, and power actions.
- Unit test session-only resume behavior: resume within a power session, latest episode after shutdown/off.
- Unit test cache freshness, stale-cache fallback, and empty/network failure cases.
- Unit test no-connection behavior for offline with usable cache versus offline with no usable cache.
- Unit test fade orchestration ordering for play, pause, track change, station change, and soft off.
- Integration test backend to mpv IPC with a local or known stream URL.
- Browser test the React UI states, including no connection, at the Waveshare display resolution.
- Browser test light and dark themes, including LCD shadows and grayscale/pixelated album artwork treatment.
- Manual Pi acceptance test: boot to idle, select each station, play/pause, change tracks in both directions, adjust volume, station-select while music continues, soft-off shutdown, safe unplug, and recover after network loss.

## Assumptions

- v1 target is a Raspberry Pi prototype, not a desktop-only simulator or full enclosure build.
- Safe-to-unplug off means OS shutdown on the Pi, not suspend/sleep.
- Waking from off requires restoring wall power or later adding dedicated power-management hardware.
- Python is authoritative for state; React never mutates state directly.
- Keyboard simulation is acceptable before final encoder wiring.
- The current root files are planning artifacts only; implementation will require creating a project structure from scratch.
