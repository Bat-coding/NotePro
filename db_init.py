import mysql.connector
import time
import os


def wait_and_init():
    for _ in range(30):
        try:
            db = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'db'),
                user=os.getenv('DB_USER', 'notepro'),
                password=os.getenv('DB_PASSWORD', 'notepro'),
                database=os.getenv('DB_NAME', 'notepro')
            )
            cursor = db.cursor()
            with open('/app/db/init.sql', 'r') as f:
                for stmt in f.read().split(';'):
                    s = stmt.strip()
                    if s:
                        try:
                            cursor.execute(s)
                        except Exception as e:
                            print(f"SQL ignoré : {e}")
            db.commit()
            cursor.close()
            db.close()
            print("DB initialisée !")
            return
        except Exception as e:
            print(f"Attente MySQL... ({e})")
            time.sleep(2)
    print("Echec connexion MySQL après 30 tentatives.")


if __name__ == '__main__':
    wait_and_init()