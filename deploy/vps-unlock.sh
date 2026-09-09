#!/bin/bash
# Run in Hostinger VPS → Browser terminal, then reply "done"
set -euo pipefail
mkdir -p /root/.ssh
chmod 700 /root/.ssh
touch /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys

# Fresh key (old sora_vps_key is broken for signing)
KEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHMIw1OBuIl87Pk5tKh1BBqSRG12Oha95aMzC2GDuPsf joyclub-deploy'
grep -qxF "$KEY" /root/.ssh/authorized_keys || echo "$KEY" >> /root/.ssh/authorized_keys

# Remove any broken/duplicate sora-deploy lines that accept-then-fail
sed -i '/sora-deploy$/d' /root/.ssh/authorized_keys || true
grep -qxF "$KEY" /root/.ssh/authorized_keys || echo "$KEY" >> /root/.ssh/authorized_keys

sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config || true
sed -i 's/^#\?PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config || true
systemctl reload sshd 2>/dev/null || systemctl reload ssh 2>/dev/null || true
echo UNLOCK_OK
