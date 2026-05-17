#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../backend"

if ! command -v uvicorn &>/dev/null; then
  echo "Installing Python dependencies..."
  pip install -r requirements.txt
fi

echo "Starting SchoolShield backend on http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
uvicorn main:app --reload --port 8000
