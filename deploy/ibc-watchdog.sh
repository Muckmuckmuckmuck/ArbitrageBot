#!/usr/bin/env bash
# Self-heal IB Gateway: if the API port isn't listening, restart IBC.
#
# WHY THIS EXISTS: IBKR force-restarts the Gateway nightly (IBC AutoRestartTime).
# If that re-login hangs, the Gateway dies but the systemd unit still looks "active"
# (the xvfb-run/ibcstart.sh wrapper survives) — so the bot silently falls back to
# dry-run and stops trading with nothing reporting a failure. This caught exactly
# that: a 2-day silent outage.
#
# Install (see deploy/ibc-watchdog.timer):
#   sudo cp deploy/ibc-watchdog.sh /usr/local/bin/ && sudo chmod +x /usr/local/bin/ibc-watchdog.sh
#   sudo cp deploy/ibc-watchdog.{service,timer} /etc/systemd/system/
#   sudo systemctl daemon-reload && sudo systemctl enable --now ibc-watchdog.timer
LOG=/home/ubuntu/ibc/watchdog.log
up() { ss -ltn 2>/dev/null | grep -q ':4002'; }
if up; then exit 0; fi
sleep 60                      # check twice so a normal restart window doesn't bounce it
if up; then exit 0; fi
echo "$(date -u '+%F %T') API 4002 down -> restarting ibc" >> "$LOG"
systemctl restart ibc
