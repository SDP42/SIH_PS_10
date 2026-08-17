#!/usr/bin/env bash
# exit on error
set -o errexit

echo "=== 1. Upgrading Pip & Installing Dependencies ==="
python -m pip install --upgrade pip
pip install --prefer-binary -r requirements.txt

echo "=== 2. Running Data Initialization & Database Builder ==="
python scripts/init.py

echo "=== 3. Building React Frontend ==="
cd frontend
npm install
npm run build
cd ..

echo "=== Build Completed Successfully! ==="
