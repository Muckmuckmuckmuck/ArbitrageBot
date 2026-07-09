# Headless IB Gateway on the VM (for live paper trading)

The bot connects to a running **IB Gateway** (IBKR's lightweight API app). On a
headless VM you run it under a virtual display with **IBC** for automatic login and
the daily restart IBKR forces. This needs *your* IBKR account + credentials, so it's a
manual step — here's the whole recipe.

> Until this is set up, the daily run still works: with `QUANTBOT_EXECUTE=false` (or no
> Gateway reachable) it computes and logs the target book / orders as a dry-run.

## 1. Prerequisites
- An IBKR account with a **paper trading** login (username usually starts with a
  letter; paper account id looks like `DU1234567`).
- Ubuntu 22.04 (Python 3.10+ — required by `ib_async`).

## 2. Install IB Gateway + IBC
```bash
sudo apt-get install -y openjdk-17-jre xvfb
# IB Gateway (stable, offline installer):
curl -fsSLO https://download2.interactivebrokers.com/installers/ibgateway/stable-standalone/ibgateway-stable-standalone-linux-x64.sh
sh ibgateway-stable-standalone-linux-x64.sh -q     # installs to ~/Jts / ~/ibgateway
# IBC (auto-login controller):
IBC_VER=3.20.0
curl -fsSLO https://github.com/IbcAlpha/IBC/releases/download/${IBC_VER}/IBCLinux-${IBC_VER}.zip
mkdir -p ~/ibc && unzip -o IBCLinux-${IBC_VER}.zip -d ~/ibc && chmod +x ~/ibc/*.sh ~/ibc/scripts/*.sh
```

## 3. Configure IBC
Edit `~/ibc/config.ini`:
```
IbLoginId=YOUR_IBKR_USERNAME
IbPassword=YOUR_IBKR_PASSWORD
TradingMode=paper
IbDir=/home/ubuntu/ibgateway/<version>
AcceptIncomingConnectionAction=accept
ReadOnlyApi=no
OverrideTwsApiPort=4002
# IBKR force-restarts daily; let IBC handle it:
ClosedownAt=
AutoRestartTime=11:50 PM
```
> Keep `config.ini` private (`chmod 600`). 2FA: paper logins generally don't require it;
> live logins do (IB Key on your phone) and aren't suitable for unattended headless use.

## 4. Run headless under a virtual display
`deploy/ibc.service` (a systemd unit) starts Xvfb + IBC and keeps the Gateway up:
```bash
sudo cp deploy/ibc.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now ibc
sleep 30 && ss -ltnp | grep 4002        # API port should be listening
```

## 5. Point the bot at it and go live (paper)
In `~/quantbot/.env`:
```
QUANTBOT_MODE=PAPER
QUANTBOT_EXECUTE=true
IBKR_PORT=4002
```
Test a single run, then let the daily timer drive it:
```bash
cd ~/quantbot && ./.venv/bin/python scripts/daily_run.py     # should show broker=ibkr and place paper orders
```

## Notes / gotchas
- **`ib_async` requires Python 3.10+** — Ubuntu 22.04 has it; the 3.9 Mac used for dev does not.
- The Gateway must be **restarted daily** (IBKR requirement) — `AutoRestartTime` handles it;
  schedule the bot's 22:00 UTC run to avoid the restart window.
- Firewall: the API bind is localhost only (`127.0.0.1:4002`); no inbound cloud rule needed.
- Start read-only (`ReadOnlyApi=yes`, `QUANTBOT_EXECUTE=false`) to confirm connectivity and
  the target book before enabling order placement.
