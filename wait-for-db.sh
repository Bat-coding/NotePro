#!/bin/bash
echo "Waiting for MySQL..."
while ! python -c "import mysql.connector; mysql.connector.connect(host='db', user='root', password='rootpassword', database='notepro')" 2>/dev/null; do
  sleep 2
done
echo "MySQL ready!"
python /app/db_init.py
exec "$@"