#!/usr/bin/env bash
# Run this ON the Oracle Cloud VM (Ubuntu 22.04 aarch64 / ARM).
# Installs deps, builds the venv, and enables the daily systemd timer.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Muckmuckmuckmuck/ArbitrageBot.git}"
BRANCH="${BRANCH:-quantbot}"
APP_DIR="$HOME/quantbot"

echo ">>> System packages"
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip git

echo ">>> Clone / update repo ($BRANCH)"
if [ ! -d "$APP_DIR/.git" ]; then
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" fetch origin "$BRANCH"
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" pull --ff-only
fi
cd "$APP_DIR"

echo ">>> Python venv + deps (prefer prebuilt aarch64 wheels)"
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install --prefer-binary -r requirements.txt   # --prefer-binary avoids a Rust build of cryptography
mkdir -p data/logs data/live

echo ">>> Install systemd timer (runs weekdays 22:00 UTC)"
sudo cp deploy/quantbot.service /etc/systemd/system/quantbot.service
sudo cp deploy/quantbot.timer   /etc/systemd/system/quantbot.timer
sudo systemctl daemon-reload
sudo systemctl enable --now quantbot.timer

echo ">>> Smoke-test one run now"
./.venv/bin/python scripts/daily_run.py || true

echo ">>> Done. Useful commands:"
echo "   systemctl list-timers quantbot.timer      # next scheduled run"
echo "   journalctl -u quantbot.service -n 50       # last run logs"
echo "   tail -f ~/quantbot/data/logs/quantbot.log  # app log"
echo "   cat ~/quantbot/data/live/target_*.json     # latest target book"
