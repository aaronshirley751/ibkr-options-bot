#!/usr/bin/env bash
set -euo pipefail
# Installs a user-level systemd service that runs the run_bot.sh script
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME=ibkr-bot.service
SERVICE_PATH="$HOME/.config/systemd/user/$SERVICE_NAME"

cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=IBKR Options Bot

[Service]
Type=simple
WorkingDirectory=$ROOT_DIR
ExecStart=$ROOT_DIR/scripts/run_bot.sh
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now $SERVICE_NAME
echo "Installed and started $SERVICE_NAME"
