#!/usr/bin/env bash
#
# setup-monitoring.sh — установка Uptime Kuma + Docker log rotation + настройки
# Запуск: bash scripts/setup-monitoring.sh
#
set -euo pipefail

echo "=== JobMap — Setup Monitoring ==="
echo ""

# ═══════════════════════════════════════════
# 1. Docker log rotation
# ═══════════════════════════════════════════
echo "--- 1/5: Docker log rotation ---"
mkdir -p /etc/docker
if [ -f /etc/docker/daemon.json ]; then
    echo "  /etc/docker/daemon.json already exists — checking config..."
    if grep -q '"max-size".*"10m"' /etc/docker/daemon.json 2>/dev/null; then
        echo "  ✓ Log rotation already configured"
    else
        echo "  ⚠ Existing daemon.json doesn't have log settings — please merge manually:"
        cat << 'EOF'
Expected /etc/docker/daemon.json:
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
    fi
else
    cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
    echo "  ✓ /etc/docker/daemon.json created"
    echo "  ⚠ Restart Docker to apply: systemctl restart docker"
fi

# ═══════════════════════════════════════════
# 2. Uptime Kuma
# ═══════════════════════════════════════════
echo ""
echo "--- 2/5: Uptime Kuma (self-hosted monitoring) ---"

KUMA_CONTAINER=$(docker ps --filter name=uptime-kuma --format '{{.Names}}' 2>/dev/null || true)

if [ -n "$KUMA_CONTAINER" ]; then
    echo "  ✓ Uptime Kuma already running"
else
    echo "  Starting Uptime Kuma on 127.0.0.1:3001..."
    docker run -d \
        --restart=unless-stopped \
        -p 127.0.0.1:3001:3001 \
        -v uptime-kuma:/app/data \
        --name uptime-kuma \
        louislam/uptime-kuma:latest
    echo "  ✓ Uptime Kuma started"
    echo ""
    echo "  Access: http://localhost:3001 (via SSH tunnel or VPN)"
    echo "  Tunnel: ssh -L 3001:127.0.0.1:3001 root@104.237.11.110"
fi

# ═══════════════════════════════════════════
# 3. Firewall (ufw)
# ═══════════════════════════════════════════
echo ""
echo "--- 3/5: Firewall (ufw) ---"

if command -v ufw &>/dev/null; then
    ufw_info=$(ufw status 2>&1 || true)
    if echo "$ufw_info" | grep -q "Status: active"; then
        echo "  ✓ UFW already active"
    else
        echo "  Configuring UFW..."
        ufw allow OpenSSH
        ufw allow 80/tcp   # HTTP → redirect
        ufw allow 443/tcp  # HTTPS
        ufw --force enable
        echo "  ✓ UFW enabled"
        echo "  ✓ Allowed: OpenSSH, 80/tcp, 443/tcp"
    fi
else
    echo "  ⚠ UFW not installed. Install: apt install -y ufw"
    echo "  Then: ufw allow OpenSSH && ufw allow 80/tcp && ufw allow 443/tcp && ufw enable"
fi

# Verify: internal ports should not be publicly exposed
echo ""
echo "  Checking exposed ports..."
docker ps --format '{{.Names}}: {{.Ports}}' | while read -r line; do
    if echo "$line" | grep -q '0.0.0.0'; then
        echo "  ⚠ $line — publicly exposed!"
    else
        echo "  ✓ $line"
    fi
done

# ═══════════════════════════════════════════
# 4. SSH hardening
# ═══════════════════════════════════════════
echo ""
echo "--- 4/5: SSH hardening ---"

if grep -q "^PasswordAuthentication no" /etc/ssh/sshd_config 2>/dev/null; then
    echo "  ✓ PasswordAuthentication already disabled"
else
    echo "  Disabling PasswordAuthentication..."
    sed -i 's/^#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
    sed -i 's/^PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
    # Add if not present
    if ! grep -q "^PasswordAuthentication" /etc/ssh/sshd_config; then
        echo "PasswordAuthentication no" >> /etc/ssh/sshd_config
    fi
    echo "  ✓ PasswordAuthentication disabled (restart SSH: systemctl restart sshd)"
fi

# ═══════════════════════════════════════════
# 5. Fail2Ban
# ═══════════════════════════════════════════
echo ""
echo "--- 5/5: Fail2Ban ---"

if command -v fail2ban-client &>/dev/null; then
    f2b_status=$(fail2ban-client status 2>&1 || true)
    if echo "$f2b_status" | grep -q "Status"; then
        echo "  ✓ Fail2Ban is running"
    else
        echo "  ⚠ Fail2Ban installed but not started — run: systemctl enable fail2ban && systemctl start fail2ban"
    fi
else
    echo "  Installing Fail2Ban..."
    apt-get update -qq && apt-get install -y -qq fail2ban
    systemctl enable fail2ban
    systemctl start fail2ban
    echo "  ✓ Fail2Ban installed and started"
fi

# ═══════════════════════════════════════════
echo ""
echo "=== Setup complete ==="
echo ""
echo "Post-install checklist:"
echo "  [ ] systemctl restart docker    (if daemon.json was created)"
echo "  [ ] systemctl restart sshd      (if PasswordAuthentication was changed)"
echo "  [ ] Set up Uptime Kuma monitors for:"
echo "      - https://phone.service247.by/health  (every 30s, HTTP 200)"
echo "      - https://phone.service247.by          (POST, frontend)"
echo "  [ ] Configure Telegram/Discord alert webhook in Uptime Kuma"
echo ""
