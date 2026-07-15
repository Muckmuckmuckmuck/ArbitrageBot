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

## Hard-won gotchas (every one of these actually bit us — don't relearn them)

1. **Use `ibcstart.sh`, NOT `gatewaystart.sh`.** `gatewaystart.sh` launches the Gateway
   inside an `xterm` and then returns — under `xvfb-run` that tears the display down
   instantly and the unit crash-loops (`xterm: command not found`, "Deactivated
   successfully" in ~1s). The working ExecStart is:
   `xvfb-run -a /home/ubuntu/ibc/scripts/ibcstart.sh 1045 --gateway --mode=paper --tws-path=/home/ubuntu/Jts --ibc-path=/home/ubuntu/ibc --ibc-ini=/home/ubuntu/ibc/config.ini`
2. **`AllowBlindTrading=yes` is REQUIRED** on a paper account with no market-data
   subscription. Without it the Gateway blocks every order — and it surfaces
   *misleadingly* as `Error 321 ... read-only mode` plus an undismissed "API client needs
   write access" dialog. Also set `BypassOrderPrecautions=yes`. `ReadOnlyApi=no` alone is
   NOT enough.
3. **Install the watchdog** (`deploy/ibc-watchdog.*`). IBKR force-restarts the Gateway
   nightly; when that re-login hangs the Gateway is dead but systemd still reports the unit
   `active` (the wrapper survives), so the bot silently dry-runs forever. This caused a real
   2-day silent outage. The watchdog restarts IBC within 10 min of the API port dropping.
4. **Match IBC's expected install path:** installing to `~/ibgateway` requires
   `ln -sfn ~/ibgateway ~/Jts/ibgateway/1045` so IBC can find the jars.
5. **Cap the heap on a small box:** `-Xmx512m` in `~/ibgateway/ibgateway.vmoptions`
   (plus 2 GB swap) for the 1 GB VM.
6. **`ib_async` requires Python 3.10+** — Ubuntu 22.04 has it; the 3.9 Mac used for dev does not.
7. Firewall: the API bind is localhost only (`127.0.0.1:4002`); no inbound cloud rule needed.
8. Keep `QUANTBOT_EXECUTE=false` until a dry run reports `broker=ibkr`, then flip it on.
