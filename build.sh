#!/usr/bin/env bash
# exit on error
set -o errexit

echo "=== 1. Upgrading Pip & Installing Dependencies ==="
python -m pip install --upgrade pip
pip install --prefer-binary -r requirements.txt

echo "=== 2. Running Data Initialization & Database Builder ==="
python scripts/init.py

echo "=== 2b. Generating Synthetic Population Demo Dataset ==="
echo "(clearly labeled SYNTHETIC everywhere it's shown — see README)"
python scripts/migrate_multilingual_fts.py
python scripts/generate_synthetic_population.py --count 2200 --seed 42

echo "=== 3. Building React Frontend ==="
cd frontend
npm install
npm run build
cd ..

echo "=== Build Completed Successfully! ==="
