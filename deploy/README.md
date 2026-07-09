# Deploying quantbot on Oracle Cloud (Always Free)

Run the system on an Oracle Cloud **Always Free** Ampere A1 (ARM) VM — up to 4 cores /
24 GB, free forever. The workload is light (a daily run on daily bars), so the free
tier is plenty.

## What runs on the VM (today)
A **systemd timer** fires `scripts/daily_run.py` every weekday at 22:00 UTC (after the
US close). It computes the regime + target book and logs it to `data/logs/` and
`data/live/target_YYYYMMDD.json`. **No live orders yet** — the IBKR execution adapter
is future work; there's a marked seam in `daily_run.py` where it plugs in.

## One-time setup (the parts only you can do)

### 1. Oracle account + CLI auth
- Create a free account: https://www.oracle.com/cloud/free/ (needs a card to verify; not charged).
- Install the CLI (done locally already if you ran the project setup): `brew install oci-cli`.
- Authenticate: `oci setup config` — it asks for your **tenancy OCID**, **user OCID**,
  **region**, and generates an API key you paste into **Console → Profile → API keys**.
  Verify with `oci iam region list`.

### 2. Create the VM
**Option A (recommended for the first VM): web Console.** The "Create instance" wizard
auto-creates the network (VCN/subnet), which the CLI does not. Pick shape
`VM.Standard.A1.Flex`, 4 OCPU / 24 GB, image **Ubuntu 22.04 (aarch64)**, add your SSH
public key.

**Option B: CLI.** Once you have a VCN + public subnet, set the OCIDs and run:
```bash
export COMPARTMENT_OCID=ocid1.compartment...
export SUBNET_OCID=ocid1.subnet...
export AD="$(oci iam availability-domain list --query 'data[0].name' --raw-output)"
export SSH_KEY=$HOME/.ssh/id_ed25519.pub    # ssh-keygen -t ed25519 if you don't have one
bash deploy/provision_oci.sh
```
> ⚠️ Always-Free ARM capacity is frequently exhausted in busy regions. If you see
> "Out of host capacity", retry later or choose a different region/availability domain.

### 3. Configure the VM
SSH in and run the setup script (installs deps, venv, and the daily timer):
```bash
ssh ubuntu@<public-ip>
curl -fsSL https://raw.githubusercontent.com/Muckmuckmuckmuck/ArbitrageBot/quantbot/deploy/setup_vm.sh | bash
# (or: git clone --branch quantbot <repo>; cd quantbot; bash deploy/setup_vm.sh)
```

### 4. Verify
```bash
systemctl list-timers quantbot.timer          # next scheduled run
journalctl -u quantbot.service -n 50          # last run's output
cat ~/quantbot/data/live/target_*.json        # today's target book
```

## Open the firewall (if needed)
Oracle VMs have a cloud firewall (security list/NSG) **and** an OS firewall. Outbound
HTTPS (for market data) works by default. You only need inbound rules if you later add
a dashboard/API. For IBKR the VM makes an *outbound* connection to IB Gateway, so no
inbound rule is required.

## Later: live IBKR trading on the VM
When the execution adapter is built, the VM will also run **IB Gateway headless via
IBC** (auto-login + auto-restart), and `daily_run.py` will place paper orders through
`ib_async`. That needs your IBKR credentials on the VM and a keep-alive for the daily
Gateway re-login — documented when we wire it.

## Notes
- ARM (aarch64): all deps (pandas/numpy/pyarrow/ib_async) ship ARM wheels. The setup
  uses `pip install --prefer-binary` so `cryptography` never tries a Rust source build.
- Timezone/DST: the timer uses fixed 22:00 UTC to stay after the US close year-round.
- Cheap no-hassle alternative if Oracle's ARM capacity frustrates you: a Hetzner CX22
  (~€4/mo) — same `setup_vm.sh` works on any Ubuntu 22.04 host.
