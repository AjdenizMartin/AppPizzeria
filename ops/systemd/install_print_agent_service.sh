#!/usr/bin/env bash

set -euo pipefail

SERVICE_NAME="pizzeria-print-agent.service"
APP_DIR="${1:-/opt/pizzeria-app}"
RUN_USER="${2:-$USER}"
PYTHON_BIN="${3:-$APP_DIR/.venv/bin/python}"
ENV_FILE="/etc/pizzeria-print-agent.env"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"

if [[ ! -f "${APP_DIR}/print_agent/agent.py" ]]; then
  echo "Error: no se encontró ${APP_DIR}/print_agent/agent.py"
  echo "Uso: $0 [APP_DIR] [RUN_USER] [PYTHON_BIN]"
  exit 1
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Error: no se encontró ejecutable Python en ${PYTHON_BIN}"
  echo "Uso: $0 [APP_DIR] [RUN_USER] [PYTHON_BIN]"
  exit 1
fi

echo "Instalando ${SERVICE_NAME}..."
sudo tee "${SERVICE_FILE}" >/dev/null <<EOF
[Unit]
Description=Pizzeria Print Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${PYTHON_BIN} ${APP_DIR}/print_agent/agent.py
Restart=always
RestartSec=2
User=${RUN_USER}
Group=${RUN_USER}
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Creando ${ENV_FILE}..."
  sudo tee "${ENV_FILE}" >/dev/null <<EOF
PRINT_AGENT_KEY=change-me
PRINT_AGENT_API_URL=http://127.0.0.1:8000
PRINT_AGENT_ID=kitchen-agent-1
PRINT_AGENT_INTERVAL_SECONDS=2
PRINT_AGENT_OUTPUT_FILE=
EOF
  sudo chmod 600 "${ENV_FILE}"
fi

echo "Recargando systemd y arrancando servicio..."
sudo systemctl daemon-reload
sudo systemctl enable --now "${SERVICE_NAME}"

echo
echo "Servicio activo:"
sudo systemctl status "${SERVICE_NAME}" --no-pager
echo
echo "Siguiente paso:"
echo "1) Edita ${ENV_FILE} y pon tu PRINT_AGENT_KEY real."
echo "2) Reinicia: sudo systemctl restart ${SERVICE_NAME}"
echo "3) Ver logs: sudo journalctl -u ${SERVICE_NAME} -f"
