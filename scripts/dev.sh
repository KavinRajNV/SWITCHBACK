#!/usr/bin/env bash
# Switchback — start backend + frontend for local development.
# Usage:  ./scripts/dev.sh        (from anywhere)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== Switchback dev bootstrap =="

command -v uv >/dev/null 2>&1 || {
  echo "uv is not installed: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
}

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example — fill in keys, or leave MONGODB_URI blank to use the local snapshot (docker compose up -d)."
fi

if [ ! -d backend/.venv ]; then
  echo "Creating backend/.venv (Python 3.11)..."
  uv venv backend/.venv --python 3.11
fi
echo "Installing backend dependencies..."
uv pip install --python backend/.venv -r backend/requirements.txt >/dev/null

if [ ! -d frontend/node_modules ]; then
  echo "Installing frontend dependencies..."
  npm --prefix frontend install
fi
[ -f frontend/.env ] || cp frontend/.env.example frontend/.env

PYBIN="backend/.venv/bin/python"
[ -x "$PYBIN" ] || PYBIN="backend/.venv/Scripts/python.exe"   # Git Bash on Windows

echo "Starting backend on http://127.0.0.1:8011 ..."
"$PYBIN" -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8011 --reload &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null || true' EXIT

echo "Starting frontend on http://127.0.0.1:5173 ..."
npm --prefix frontend run dev
