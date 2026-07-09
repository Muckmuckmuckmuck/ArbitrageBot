#!/usr/bin/env bash
# Retry-grab an Always-Free ARM VM (VM.Standard.A1.Flex, 4 OCPU / 24 GB) whenever
# Oracle has capacity. Meant to run periodically (launchd/cron). No-ops — and stops
# itself — once the ARM instance exists. Reads OCIDs from ~/.oci/quantbot_resources.env.
export SUPPRESS_LABEL_WARNING=True
export PATH="/usr/local/bin:/usr/bin:/bin:$PATH"
source "$HOME/.oci/quantbot_resources.env"
LOG="$HOME/.oci/armgrab.log"
KEY="$HOME/.ssh/oracle_vm.pub"
PLIST="$HOME/Library/LaunchAgents/com.quantbot.armgrab.plist"
ts() { date "+%Y-%m-%d %H:%M:%S"; }

EXIST=$(oci compute instance list -c "$TENANCY" --display-name quantbot-arm \
  --lifecycle-state RUNNING --query 'data[0].id' --raw-output 2>/dev/null)
if [ -n "$EXIST" ] && [ "$EXIST" != "null" ]; then
  echo "$(ts) ARM already running ($EXIST) — stopping retries" >> "$LOG"
  launchctl unload "$PLIST" 2>/dev/null
  exit 0
fi

for AD in "DOei:US-ASHBURN-AD-1" "DOei:US-ASHBURN-AD-2" "DOei:US-ASHBURN-AD-3"; do
  OUT=$(oci compute instance launch -c "$TENANCY" --availability-domain "$AD" \
    --shape "VM.Standard.A1.Flex" --shape-config '{"ocpus":4,"memoryInGBs":24}' \
    --image-id "$IMAGE_ARM" --subnet-id "$SUBNET" --assign-public-ip true \
    --ssh-authorized-keys-file "$KEY" --display-name quantbot-arm \
    --wait-for-state RUNNING --no-retry --query 'data.id' --raw-output 2>&1) && {
      INST=$(echo "$OUT" | grep -oE 'ocid1\.instance[^ "]+' | tail -1)
      IP=$(oci compute instance list-vnics --instance-id "$INST" --query 'data[0]."public-ip"' --raw-output 2>/dev/null)
      echo "$(ts) GOT ARM $INST @ $IP" >> "$LOG"
      { echo "ARM_INSTANCE=$INST"; echo "ARM_PUBLIC_IP=$IP"; } >> "$HOME/.oci/quantbot_resources.env"
      launchctl unload "$PLIST" 2>/dev/null
      exit 0
    }
done
echo "$(ts) still out of ARM capacity" >> "$LOG"
exit 1
