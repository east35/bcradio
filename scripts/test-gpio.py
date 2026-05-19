"""Standalone GPIO smoke test for the bc-radio encoders + power button.

Run this BEFORE wiring the encoders into the bc-radio backend. It prints an
event line for every encoder tick / push / power press. Use it to confirm
each physical input maps to the GPIO pin you think it does.

Usage:
    .venv/bin/python scripts/test-gpio.py

Press Ctrl+C to exit.
"""
from __future__ import annotations

import signal
from datetime import datetime

from gpiozero import Button, RotaryEncoder


def stamp() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def log(label: str, msg: str) -> None:
    print(f"{stamp()}  {label:<12}  {msg}", flush=True)


# Pin map — change here if you wired differently.
TUNING_A, TUNING_B, TUNING_SW = 23, 16, 25
VOLUME_A, VOLUME_B, VOLUME_SW = 5, 6, 13
POWER_BTN = 26

tuning = RotaryEncoder(TUNING_A, TUNING_B, max_steps=0)
volume = RotaryEncoder(VOLUME_A, VOLUME_B, max_steps=0)
tuning_sw = Button(TUNING_SW, pull_up=True, bounce_time=0.05)
volume_sw = Button(VOLUME_SW, pull_up=True, bounce_time=0.05)
power_btn = Button(POWER_BTN, pull_up=True, bounce_time=0.05)

tuning.when_rotated_clockwise = lambda: log("TUNING", "→  clockwise")
tuning.when_rotated_counter_clockwise = lambda: log("TUNING", "←  counter")
volume.when_rotated_clockwise = lambda: log("VOLUME", "↑  clockwise")
volume.when_rotated_counter_clockwise = lambda: log("VOLUME", "↓  counter")
tuning_sw.when_pressed = lambda: log("TUNING", "push")
volume_sw.when_pressed = lambda: log("VOLUME", "push")
power_btn.when_pressed = lambda: log("POWER", "press")

print(f"Listening on GPIO. Pin map:")
print(f"  Tuning encoder:  A=GPIO {TUNING_A}, B=GPIO {TUNING_B}, SW=GPIO {TUNING_SW}")
print(f"  Volume encoder:  A=GPIO {VOLUME_A}, B=GPIO {VOLUME_B}, SW=GPIO {VOLUME_SW}")
print(f"  Power button:    GPIO {POWER_BTN}")
print(f"Turn / push each input. Ctrl+C to exit.")
print()

signal.pause()
