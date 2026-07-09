#!/usr/bin/env bash
# Provision an Oracle Cloud "Always Free" Ampere A1 (ARM) VM for quantbot.
#
# ONE-TIME PREREQS (gated on YOUR Oracle account — can't be automated for you):
#   1. Oracle Cloud account (free):  https://www.oracle.com/cloud/free/
#   2. Configure the CLI:            oci setup config
#      (needs your tenancy OCID, user OCID, region; generates an API key you paste
#       into Console -> Profile -> API keys). Verify with:  oci iam region list
#   3. A VCN + public subnet. Easiest: create the FIRST VM in the web Console (its
#      wizard auto-creates networking), then use this script for rebuilds. Or create
#      networking via CLI (oci network vcn create / subnet create / internet-gateway).
#
# Then set the vars below and run:  bash deploy/provision_oci.sh
set -euo pipefail

: "${COMPARTMENT_OCID:?export COMPARTMENT_OCID=ocid1.compartment...}"
: "${SUBNET_OCID:?export SUBNET_OCID=ocid1.subnet...}"
: "${AD:?export AD=<availability domain, e.g. from: oci iam availability-domain list>}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519.pub}"   # generate with: ssh-keygen -t ed25519
SHAPE="VM.Standard.A1.Flex"                        # Ampere ARM (Always Free)
OCPUS="${OCPUS:-4}"; MEM_GB="${MEM_GB:-24}"        # max Always Free = 4 OCPU / 24 GB
NAME="${NAME:-quantbot}"

[ -f "$SSH_KEY" ] || { echo "SSH public key not found: $SSH_KEY (run: ssh-keygen -t ed25519)"; exit 1; }

echo ">>> Latest Ubuntu 22.04 aarch64 image in this compartment..."
IMAGE_OCID=$(oci compute image list \
  --compartment-id "$COMPARTMENT_OCID" \
  --operating-system "Canonical Ubuntu" --operating-system-version "22.04" \
  --shape "$SHAPE" --sort-by TIMECREATED --sort-order DESC \
  --query 'data[0].id' --raw-output)
echo "    image: $IMAGE_OCID"

echo ">>> Launching $SHAPE ($OCPUS OCPU / ${MEM_GB}GB)..."
echo "    NOTE: Always-Free ARM capacity is often exhausted in busy regions."
echo "    If you get 'Out of host capacity', retry later or pick another region/AD."
oci compute instance launch \
  --compartment-id "$COMPARTMENT_OCID" \
  --availability-domain "$AD" \
  --shape "$SHAPE" \
  --shape-config "{\"ocpus\": $OCPUS, \"memoryInGBs\": $MEM_GB}" \
  --image-id "$IMAGE_OCID" \
  --subnet-id "$SUBNET_OCID" \
  --assign-public-ip true \
  --ssh-authorized-keys-file "$SSH_KEY" \
  --display-name "$NAME" \
  --wait-for-state RUNNING

echo ">>> Instance running. Get its public IP with:"
echo "    INSTANCE_OCID=\$(oci compute instance list -c \"$COMPARTMENT_OCID\" --display-name \"$NAME\" --query 'data[0].id' --raw-output)"
echo "    oci compute instance list-vnics --instance-id \"\$INSTANCE_OCID\" --query 'data[0].\"public-ip\"' --raw-output"
echo ">>> Then: ssh ubuntu@<public-ip>  and run  deploy/setup_vm.sh"
