#!/bin/bash
# FIXED [VULN-001]: Suppression des credentials root codés en dur (rootpassword)
# Le script utilise maintenant les variables d'environnement injectées par Docker

echo "Waiting for MySQL..."

# FIXED [VULN-001]: Utiliser les variables d'environnement au lieu de credentials en clair
# DB_USER et DB_PASSWORD sont injectés via le fichier .env de docker-compose
while ! python -c "
import mysql.connector, os
mysql.connector.connect(
    host=os.getenv('DB_HOST', 'db'),
    user=os.getenv('DB_USER', 'notepro'),
    password=os.getenv('DB_PASSWORD', ''),
    database=os.getenv('DB_NAME', 'notepro')
)" 2>/dev/null; do
  sleep 2
done

echo "MySQL ready!"
python /app/db_init.py
exec "$@"