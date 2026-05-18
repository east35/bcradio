#!/usr/bin/env bash
# Sets up the labwc autostart entry that launches the Chromium kiosk
# pointing at the local bc-radio backend, and disables the legacy
# X11-based bc-radio-kiosk.service.
set -euo pipefail

# The systemd kiosk unit assumes X11; on Wayland (Pi OS Trixie default)
# the compositor's autostart hook is the right place.
if systemctl is-enabled --quiet bc-radio-kiosk 2>/dev/null; then
  sudo systemctl disable bc-radio-kiosk
fi
sudo systemctl stop bc-radio-kiosk 2>/dev/null || true

mkdir -p ~/.config/labwc

cat > ~/.config/labwc/autostart <<'AUTOSTART'
#!/bin/sh
until curl -sf http://127.0.0.1:8765/api/state >/dev/null; do
  sleep 1
done
chromium --kiosk --noerrdialogs --disable-infobars --disable-features=Translate --no-first-run --check-for-update-interval=31536000 --password-store=basic --use-mock-keychain --disable-pinch --overscroll-history-navigation=0 http://127.0.0.1:8765 &
AUTOSTART

chmod +x ~/.config/labwc/autostart

echo "Installed autostart:"
cat ~/.config/labwc/autostart
echo
echo "Done. Reboot to bring up the kiosk: sudo reboot"
