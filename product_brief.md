# Bandcamp Radio Radio — Product Brief

**One-line:** A purpose-built physical radio that plays Bandcamp Radio shows, controlled entirely by two knobs and a power button.

---

## Problem

Bandcamp Radio is genuinely great curated music programming — genre shows hosted by artists, new episodes weekly — but it lives buried in a browser tab. There's no dedicated listening experience, no way to just turn it on like a radio.

---

## Product

A handmade desktop radio device. You turn the tuning knob to pick a genre, push it to tune in, and music plays. That's it. No screen to look at, no app to open, no algorithm to fight. It sits on your desk and plays music the way a radio does.

**Genres:** Electronic, Selects, Hip-Hop, Indie, Metal, Games

---

## Controls

| Input | Action |
|---|---|
| Tuning knob turn | Change track |
| Tuning knob push | Enter / confirm station selection |
| Volume knob turn | Adjust volume |
| Volume knob push | Play / pause |
| Power button | Stop playback, sleep |

---

## Display

Small LCD panel showing current state. Five screens:

- **Idle** — clock
- **Station select** — genre name scrolls as you turn, dim neighbors visible either side
- **Playback** — genre, track name, track N of total, progress bar
- **Paused** — same as playback, paused indicator
- **Volume overlay** — transient toast over current screen, auto-dismisses

---

## Aesthetic

Warm, tactile, analog-feeling. Inspired by vintage hi-fi — walnut or painted enclosure, waffle foam grille (Quadrex style), machined knobs, off-white control panel. Looks like something that belongs next to a turntable, not a laptop.

---

## Hardware

| Component | Part |
|---|---|
| Compute | Raspberry Pi 3 Model b V1.2 |
| Display | Waveshare 4" HDMI LCD |
| Controls | 2× Bourns PEC11R encoders |
| Headphone out | 3.5mm jack |
| Enclosure | 3D printed (Bambu P1S)|

*Current test rig uses Pi 3B + Waveshare 4" HDMI display while Pi Zero 2W is sourced.*

---

## Software Stack (Open to suggestion)

```
Bandcamp Radio API  →  Python backend (player.py)
                              ↕ websocket
                       React UI (kiosk mode)
                              ↕ mpv IPC socket
                           mpv (audio)
                              ↕ GPIO
                       Rotary encoders
```

- Python state machine is authoritative — GPIO, keyboard, and touch all feed into it. We may need to wire the encoders via usb due to physical constraints (screen occupies most GPIO pins on pi, want to avoid soldering directly to pi)
- Browser is a pure renderer, receives state pushes over websocket
- mpv controlled via IPC socket for clean pause/resume and live volume
- Runs as a systemd service, boots directly into kiosk mode
- Episode lists cached locally with 1hr TTL

---

## Principles

- **Radio, not a player** — you tune in, not browse. The interaction model is deliberately minimal.
- **Offline-capable** — cached episode lists mean it works through brief network drops
- **No engagement mechanics** — no recommendations, no history, no streaks. It plays music.
- **Built, not bought** — handmade object with real material choices, not a commodity device
