# Bandcamp Radio Radio

Raspberry Pi kiosk prototype for a physical Bandcamp Radio receiver.

## Local Development

Install Python and frontend dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
npm install
```

Run the backend and frontend in separate terminals:

```bash
.venv/bin/python -m bcradio.server
npm run dev
```

Open `http://127.0.0.1:5173`. Keyboard simulation:

- Left/Right: tuning knob
- Enter: tuning knob push
- Up/Down: volume knob
- Space: play/pause
- P: soft off

## mpv

Install mpv first:

```bash
brew install mpv
```

On Raspberry Pi OS:

```bash
sudo apt update
sudo apt install -y mpv
```

Start mpv before the backend on hardware:

```bash
mpv --idle=yes --no-video --input-ipc-server=/tmp/bc-radio-mpv.sock
```

If the socket is missing, the backend uses a null player so the UI and state
machine can still be developed.

## Raspberry Pi Deployment

Goal: plug in power, the Pi boots directly into the radio UI. No manual steps.

Hardware target for the prototype: Pi 3B + Waveshare 4" HDMI LCD. Input is a
USB keyboard until encoders are wired (see `KEY_MAP` in
`backend/bcradio/input.py`).

### 1. Image and first boot

Flash **Raspberry Pi OS Bookworm (64-bit, with Desktop)** using the Pi Imager.
Use the imager's "gear" advanced options to pre-set hostname, username `pi`,
Wi-Fi, SSH, and timezone. Boot, then `ssh pi@<hostname>.local`.

### 2. Configure the Waveshare 4" HDMI LCD

Display config goes in `/boot/firmware/config.txt` on Bookworm (note: moved
from `/boot/`). The exact entries depend on the SKU — verify against the
Waveshare wiki for your specific model. Typical entries:

```
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt 800 480 60 6 0 0 0
hdmi_drive=1
```

Reboot. Confirm native resolution. Disable screen blanking via
`sudo raspi-config` → Display Options → Screen Blanking.

### 3. System packages

```bash
sudo apt update
sudo apt install -y mpv chromium git python3-venv python3-pip \
    nodejs npm
```

### 4. Autologin

`sudo raspi-config` → System Options → Boot / Auto Login → **Desktop
Autologin**.

### 5. Deploy the app

```bash
cd /home/pi
git clone <repo-url> bc-radio
cd bc-radio
python3 -m venv .venv
.venv/bin/pip install -e .
npm install
npm run build   # outputs to ./dist (served by the backend at :8765)
```

### 6. Install services

```bash
sudo cp systemd/bc-radio-mpv.service /etc/systemd/system/
sudo cp systemd/bc-radio.service     /etc/systemd/system/
sudo cp systemd/bc-radio-kiosk.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bc-radio-mpv bc-radio bc-radio-kiosk

# Allow the backend to call `sudo shutdown` without a password prompt
echo 'pi ALL=(ALL) NOPASSWD: /sbin/shutdown' | sudo tee /etc/sudoers.d/bc-radio
sudo chmod 440 /etc/sudoers.d/bc-radio

# Hide the mouse cursor in the kiosk
mkdir -p ~/.config/autostart
cat >~/.config/autostart/unclutter.desktop <<'EOF'
[Desktop Entry]
Type=Application
Exec=unclutter -idle 0
EOF

sudo reboot
```

After reboot the Pi boots directly into the chromium kiosk on
`http://127.0.0.1:8765`. The backend (`bc-radio.service`) serves both the
WebSocket and the built React UI from the same port. `bc-radio-mpv.service`
runs the mpv IPC daemon the backend talks to.

### Updating the UI

After pulling new code, rebuild and restart:

```bash
cd /home/pi/bc-radio
git pull
npm run build
sudo systemctl restart bc-radio bc-radio-kiosk
```

### Notes

- The backend only shuts down the Pi when `BC_RADIO_ALLOW_SHUTDOWN=1` is set
  (it is, in `bc-radio.service`).
- If the LCD doesn't show the UI but `curl http://127.0.0.1:8765/` works over
  SSH, the backend is fine — debug the kiosk service with
  `journalctl -u bc-radio-kiosk -f`.
