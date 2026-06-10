#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "=== Pizzeria App: All-in-one installer ==="
echo "Root: $ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required."
  exit 1
fi

if ! python3 - <<'PY'
import sys

raise SystemExit(0 if sys.version_info >= (3, 11) else 1)
PY
then
  echo "ERROR: python3 >= 3.11 is required. Current version: $(python3 --version 2>&1)"
  echo "Install Python 3.13 with pyenv, then run: pyenv local 3.13"
  exit 1
fi

if ! command -v node >/dev/null 2>&1; then
  echo "ERROR: node is required."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "ERROR: npm is required."
  exit 1
fi

if ! command -v alembic >/dev/null 2>&1; then
  echo "WARN: alembic command not found globally. Will try with venv later."
fi

ENV_FILE="${ROOT_DIR}/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  cp "${ROOT_DIR}/.env.example" "$ENV_FILE"
  echo "Created .env from .env.example"
fi

read -r -p "Backend URL for print agent [http://127.0.0.1:8000]: " PRINT_AGENT_API_URL
PRINT_AGENT_API_URL="${PRINT_AGENT_API_URL:-http://127.0.0.1:8000}"

read -r -p "Print agent ID [kitchen-agent-1]: " PRINT_AGENT_ID
PRINT_AGENT_ID="${PRINT_AGENT_ID:-kitchen-agent-1}"

read -r -p "Print polling interval seconds [2]: " PRINT_AGENT_INTERVAL_SECONDS
PRINT_AGENT_INTERVAL_SECONDS="${PRINT_AGENT_INTERVAL_SECONDS:-2}"

CURRENT_PRINT_KEY="$(grep -E '^PRINT_AGENT_KEY=' "$ENV_FILE" | head -n1 | cut -d'=' -f2- || true)"
if [[ -z "${CURRENT_PRINT_KEY}" || "${CURRENT_PRINT_KEY}" == "shared_secret_for_printer_agent" || "${CURRENT_PRINT_KEY}" == "change-me" ]]; then
  GENERATED_KEY="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(32))
PY
)"
  if grep -qE '^PRINT_AGENT_KEY=' "$ENV_FILE"; then
    sed -i.bak "s|^PRINT_AGENT_KEY=.*|PRINT_AGENT_KEY=${GENERATED_KEY}|" "$ENV_FILE"
  else
    echo "PRINT_AGENT_KEY=${GENERATED_KEY}" >> "$ENV_FILE"
  fi
  echo "Generated secure PRINT_AGENT_KEY in .env"
fi

echo "Creating/updating Python virtualenv..."
if [[ ! -d "${ROOT_DIR}/.venv" ]]; then
  python3 -m venv "${ROOT_DIR}/.venv"
fi
source "${ROOT_DIR}/.venv/bin/activate"
python -m pip install --upgrade pip
pip install -e ".[dev]"

echo "Installing frontend deps and building React..."
pushd "${ROOT_DIR}/frontend-react" >/dev/null
npm ci
npm run build
popd >/dev/null

echo "Running database migrations..."
alembic upgrade head

echo "Preparing systemd print agent env..."
SYSTEMD_ENV_FILE="/etc/pizzeria-print-agent.env"
PRINT_AGENT_KEY="$(grep -E '^PRINT_AGENT_KEY=' "$ENV_FILE" | head -n1 | cut -d'=' -f2-)"

cat > /tmp/pizzeria-print-agent.env <<EOF
PRINT_AGENT_KEY=${PRINT_AGENT_KEY}
PRINT_AGENT_API_URL=${PRINT_AGENT_API_URL}
PRINT_AGENT_ID=${PRINT_AGENT_ID}
PRINT_AGENT_INTERVAL_SECONDS=${PRINT_AGENT_INTERVAL_SECONDS}
PRINT_AGENT_OUTPUT_FILE=
EOF

echo
echo "Next step requires sudo to install/refresh systemd service:"
echo "  - writes ${SYSTEMD_ENV_FILE}"
echo "  - installs/updates pizzeria-print-agent.service"
echo
read -r -p "Install/refresh print agent systemd service now? [Y/n]: " INSTALL_SERVICE
INSTALL_SERVICE="${INSTALL_SERVICE:-Y}"

if [[ "$INSTALL_SERVICE" =~ ^[Yy]$ ]]; then
  sudo cp /tmp/pizzeria-print-agent.env "${SYSTEMD_ENV_FILE}"
  sudo chmod 600 "${SYSTEMD_ENV_FILE}"
  sudo ./ops/systemd/install_print_agent_service.sh "${ROOT_DIR}" "$(whoami)"
  echo "Print agent service installed."
else
  echo "Skipped service installation."
fi

echo
echo "=== Installation completed ==="
echo "Run backend:"
echo "  source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "Open app:"
echo "  http://127.0.0.1:8000"
echo
echo "Check print agent:"
echo "  systemctl status pizzeria-print-agent"
echo "  journalctl -u pizzeria-print-agent -f"
