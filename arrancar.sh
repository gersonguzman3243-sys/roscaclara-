#!/usr/bin/env bash
# Arranca RoscaClara en un solo puerto (construye la interfaz si hace falta).
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
# shellcheck disable=SC1091
source .venv/bin/activate

if [[ ! -d web/node_modules ]]; then
  (cd web && npm install)
fi
if [[ ! -d web/dist ]]; then
  (cd web && npm run build)
fi

exec uvicorn rosca.api:app --host 0.0.0.0 --port 8641
