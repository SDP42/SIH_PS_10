#!/usr/bin/env bash
# exit on error
set -o errexit

echo "=== 1. Installing Python Dependencies ==="
pip install -r requirements.txt

echo "=== 2. Running Data Initialization & Database Builder ==="
python scripts/init.py

echo "=== 3. Building React Frontend ==="
cd frontend
npm install
npm run build
cd ..

echo "=== Build Completed Successfully! ==="
