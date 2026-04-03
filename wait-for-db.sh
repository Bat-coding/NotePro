#!/bin/bash
echo "Waiting for MySQL..."

MAX_RETRIES=30
COUNT=0

while ! python -c "
import mysql.connector, os
mysql.connector.connect(
    host=os.getenv('DB_HOST', 'db'),
    user=os.getenv('DB_USER', 'notepro'),
    password=os.getenv('DB_PASSWORD', ''),
    database=os.getenv('DB_NAME', 'notepro')
)" 2>/dev/null; do
  COUNT=$((COUNT+1))
  if [ $COUNT -ge $MAX_RETRIES ]; then
    echo "MySQL not reachable after $MAX_RETRIES attempts, exiting."
    exit 1
  fi
  echo "Attempt $COUNT/$MAX_RETRIES..."
  sleep 2
done

echo "MySQL ready!"
python /app/db_init.py
exec "$@"