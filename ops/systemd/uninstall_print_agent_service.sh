#!/usr/bin/env bash

set -euo pipefail

SERVICE_NAME="pizzeria-print-agent.service"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}"

echo "Deteniendo ${SERVICE_NAME}..."
sudo systemctl disable --now "${SERVICE_NAME}" 2>/dev/null || true

echo "Eliminando unidad systemd..."
if [[ -f "${SERVICE_FILE}" ]]; then
  sudo rm -f "${SERVICE_FILE}"
fi

sudo systemctl daemon-reload

echo
echo "Servicio eliminado. Si quieres borrar variables también:"
echo "sudo rm -f /etc/pizzeria-print-agent.env"
