#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  KEY=$(python3 -c "from django.core.management.utils import get_random_secret_key as k; print(k())" 2>/dev/null || echo "change-me")
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${KEY}|" .env
  echo "→ .env créé depuis .env.example"
fi

echo "[1/3] Installation des dépendances..."
pip install -r requirements.txt -q
echo "[2/3] Base de données..."
python3 manage.py migrate
python3 manage.py seed_db
echo "[3/3] Serveur sur http://localhost:8000"
python3 manage.py runserver
