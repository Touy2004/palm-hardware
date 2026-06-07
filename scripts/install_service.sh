#!/usr/bin/env bash

set -e

PROJECT_DIR="$HOME/palm-hardware"
SERVICE_NAME="palm-hardware"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
PYTHON_BIN="${PROJECT_DIR}/venv/bin/python"
APP_ENTRY="${PROJECT_DIR}/app/main.py"
LOG_DIR="${PROJECT_DIR}/logs"

echo "========== Palm Hardware Service Installer =========="
echo "Project dir: ${PROJECT_DIR}"
echo "Service:     ${SERVICE_NAME}"
echo "Python:      ${PYTHON_BIN}"
echo "Entry:       ${APP_ENTRY}"

if [ ! -d "${PROJECT_DIR}" ]; then
  echo "ERROR: Project directory not found: ${PROJECT_DIR}"
  exit 1
fi

if [ ! -f "${PYTHON_BIN}" ]; then
  echo "ERROR: Python venv not found: ${PYTHON_BIN}"
  echo "Create it first:"
  echo "cd ${PROJECT_DIR}"
  echo "python3 -m venv venv"
  echo "source venv/bin/activate"
  echo "pip install -r requirements.txt"
  exit 1
fi

if [ ! -f "${APP_ENTRY}" ]; then
  echo "ERROR: App entry file not found: ${APP_ENTRY}"
  echo "Create app/main.py first."
  exit 1
fi

mkdir -p "${LOG_DIR}"

echo "Creating systemd service file..."

sudo bash -c "cat > ${SERVICE_FILE}" <<EOF
[Unit]
Description=Palm Hardware Recognition Device Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${PROJECT_DIR}
Environment=PYTHONUNBUFFERED=1
ExecStart=${PYTHON_BIN} ${APP_ENTRY}
Restart=always
RestartSec=5
StandardOutput=append:${LOG_DIR}/device.log
StandardError=append:${LOG_DIR}/error.log

[Install]
WantedBy=multi-user.target
EOF

echo "Reloading systemd..."
sudo systemctl daemon-reload

echo "Enabling service..."
sudo systemctl enable "${SERVICE_NAME}"

echo "Starting service..."
sudo systemctl restart "${SERVICE_NAME}"

echo ""
echo "========== Installed Successfully =========="
echo "Check status:"
echo "sudo systemctl status ${SERVICE_NAME}"
echo ""
echo "View logs:"
echo "tail -f ${LOG_DIR}/device.log"
echo "tail -f ${LOG_DIR}/error.log"
echo ""
echo "Stop service:"
echo "sudo systemctl stop ${SERVICE_NAME}"
echo ""
echo "Restart service:"
echo "sudo systemctl restart ${SERVICE_NAME}"