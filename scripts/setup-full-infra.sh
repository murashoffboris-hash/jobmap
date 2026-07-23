#!/usr/bin/env bash
#
# setup-full-infra.sh — полная настройка инфраструктуры JobMap на VPS
# Запуск: bash setup-full-infra.sh
#
# Внимание: запускать от root на свежем VPS (Ubuntu 24.04)
#
set -euo pipefail

echo "╔════════════════════════════════════════════════════════╗"
echo "║   JobMap — Full Infrastructure Setup                  ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# ── Утилиты ──
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
ok()  { echo -e "  ${GREEN}✓${NC} $1"; }
warn(){ echo -e "  ${YELLOW}⚠${NC} $1"; }
fail(){ echo -e "  ${RED}✗${NC} $1"; }

# ═══════════════════════════════════════════
# 1. Let's Encrypt
# ═══════════════════════════════════════════
echo ""
echo "=== 1/7: Let's Encrypt (SSL) ==="

if [ -d "/etc/letsencrypt/live/phone.service247.by" ]; then
    ok "SSL certificate already exists"
    certbot certificates 2>/dev/null | head -5
else
    echo "  Installing certbot..."
    apt-get update -qq && apt-get install -y -qq certbot python3-certbot-nginx
    ok "certbot installed"

    echo "  Obtaining certificates..."
    certbot --nginx \
        -d phone.service247.by \
        -d api.example.by \
        --non-interactive \
        --agree-tos \
        -m admin@service247.by \
        2>&1
    ok "Certificates obtained"

    # Auto-renew test
    certbot renew --dry-run 2>&1
    ok "Auto-renewal configured (systemd timer: certbot.timer)"
fi

# ═══════════════════════════════════════════
# 2. Healthchecks (docker-compose up -d)
# ═══════════════════════════════════════════
echo ""
echo "=== 2/7: Deploy docker-compose ==="

cd /opt/jobmap
docker compose up -d 2>&1
sleep 5

echo "  Container status:"
docker ps --format 'table {{.Names}}\t{{.Status}}'
ok "Docker compose deployed"

# ═══════════════════════════════════════════
# 3. Docker log rotation
# ═══════════════════════════════════════════
echo ""
echo "=== 3/7: Docker log rotation ==="

mkdir -p /etc/docker
if [ -f /etc/docker/daemon.json ]; then
    warn "daemon.json exists — checking for log config"
    if grep -q '"max-size"' /etc/docker/daemon.json 2>/dev/null; then
        ok "Log rotation already configured"
    else
        warn "Manual merge needed — see scripts/setup-monitoring.sh"
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
    ok "daemon.json created — restart: systemctl restart docker"
fi

# ═══════════════════════════════════════════
# 4. UFW Firewall
# ═══════════════════════════════════════════
echo ""
echo "=== 4/7: Firewall (UFW) ==="

if command -v ufw &>/dev/null; then
    if ufw status | grep -q "Status: active"; then
        ok "UFW already active"
    else
        ufw allow OpenSSH
        ufw allow 80/tcp
        ufw allow 443/tcp
        ufw --force enable
        ok "UFW enabled (OpenSSH, 80/tcp, 443/tcp)"
    fi
else
    apt-get install -y -qq ufw
    ufw allow OpenSSH
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable
    ok "UFW installed and enabled"
fi

# Verify internal ports are not public
for port in 5432 6379 9000 9001 3001; do
    if ss -tlnp "sport = :$port" 2>/dev/null | grep -q "0.0.0.0:$port"; then
        fail "Port $port is publicly exposed!"
    else
        ok "Port $port is bound to 127.0.0.1 only"
    fi
done

# ═══════════════════════════════════════════
# 5. SSH Hardening
# ═══════════════════════════════════════════
echo ""
echo "=== 5/7: SSH hardening ==="

SSHD_CONFIG="/etc/ssh/sshd_config"
RESTART_SSH=false

if grep -q "^PasswordAuthentication no" "$SSHD_CONFIG" 2>/dev/null; then
    ok "PasswordAuthentication already disabled"
else
    sed -i 's/^#PasswordAuthentication yes/PasswordAuthentication no/' "$SSHD_CONFIG"
    sed -i 's/^PasswordAuthentication yes/PasswordAuthentication no/' "$SSHD_CONFIG"
    if ! grep -q "^PasswordAuthentication" "$SSHD_CONFIG"; then
        echo "PasswordAuthentication no" >> "$SSHD_CONFIG"
    fi
    RESTART_SSH=true
    ok "PasswordAuthentication disabled"
fi

# Also disable root login with password
if grep -q "^PermitRootLogin prohibit-password" "$SSHD_CONFIG" 2>/dev/null; then
    ok "Root login restricted to key auth"
else
    sed -i 's/^#PermitRootLogin.*/PermitRootLogin prohibit-password/' "$SSHD_CONFIG"
    sed -i 's/^PermitRootLogin yes/PermitRootLogin prohibit-password/' "$SSHD_CONFIG"
    if ! grep -q "^PermitRootLogin" "$SSHD_CONFIG"; then
        echo "PermitRootLogin prohibit-password" >> "$SSHD_CONFIG"
    fi
    RESTART_SSH=true
    ok "Root login restricted to key auth"
fi

if [ "$RESTART_SSH" = true ]; then
    systemctl restart sshd
    ok "SSH restarted with new config"
fi

# ═══════════════════════════════════════════
# 6. Fail2Ban
# ═══════════════════════════════════════════
echo ""
echo "=== 6/7: Fail2Ban ==="

if command -v fail2ban-client &>/dev/null && systemctl is-active --quiet fail2ban; then
    ok "Fail2Ban is running"
else
    apt-get install -y -qq fail2ban
    systemctl enable fail2ban
    systemctl start fail2ban
    ok "Fail2Ban installed and started"
fi

# ═══════════════════════════════════════════
# 7. Backup cron
# ═══════════════════════════════════════════
echo ""
echo "=== 7/7: Backup cron ==="

if crontab -l 2>/dev/null | grep -q "backup.sh"; then
    ok "Backup cron already installed"
else
    (
        crontab -l 2>/dev/null || true
        echo "# JobMap — daily DB backup at 3:00 AM"
        echo "0 3 * * * /opt/jobmap/scripts/backup.sh >> /var/log/jobmap-backup.log 2>&1"
    ) | crontab -
    ok "Backup cron installed: daily 3:00 AM"
fi

# ═══════════════════════════════════════════
echo ""
echo "╔════════════════════════════════════════════════════════╗"
echo "║   Setup Complete!                                     ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "Smoke tests:"
echo "  curl -sI http://phone.service247.by/health      # → 301"
echo "  curl -sI https://phone.service247.by/health     # → 200"
echo "  docker ps | grep '(healthy)'                    # all healthy"
echo "  certbot certificates                            # valid SSL"
echo "  ls -la /opt/jobmap/backups/                     # backups exist"
echo ""
echo "Uptime Kuma:"
echo "  ssh -L 3001:127.0.0.1:3001 root@104.237.11.110"
echo "  → http://localhost:3001"
echo ""
echo "Post-setup (manual):"
echo "  [ ] Restart Docker (if daemon.json was created): systemctl restart docker"
echo "  [ ] Set up Uptime Kuma monitors + Telegram alerts"
echo "  [ ] Verify fail2ban: fail2ban-client status sshd"
echo "  [ ] Update DNS if needed: nslookup phone.service247.by 8.8.8.8"
echo ""
