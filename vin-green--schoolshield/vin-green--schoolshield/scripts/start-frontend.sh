#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../frontend"

if [ ! -d node_modules ]; then
  echo "Installing Node dependencies..."
  npm install
fi

echo "Starting SchoolShield frontend on http://localhost:5173"
npm run dev
