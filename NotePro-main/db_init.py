import mysql.connector
import time
import os

# Chemin du fichier SQL relatif à ce script (fonctionne dans Docker et en local)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQL_FILE = os.path.join(BASE_DIR, 'db', 'init.sql')


def wait_and_init():
    for _ in range(30):
        try:
            conn = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'db'),
                user=os.getenv('DB_USER', 'notepro'),
                password=os.getenv('DB_PASSWORD', 'notepro'),
                database=os.getenv('DB_NAME', 'notepro')
            )
            cursor = conn.cursor()
            if not os.path.exists(SQL_FILE):
                print(f"Fichier SQL introuvable : {SQL_FILE} — la DB sera initialisée par SQLAlchemy.")
                cursor.close()
                conn.close()
                return
            with open(SQL_FILE, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            # Nettoyage des commentaires ligne par ligne
            sql_lines = []
            for line in sql_content.splitlines():
                if not line.strip().startswith('--'):
                    sql_lines.append(line)
            
            clean_sql = "\n".join(sql_lines)
            for stmt in clean_sql.split(';'):
                s = stmt.strip()
                if s:
                    try:
                        cursor.execute(s)
                    except Exception as e:
                        print(f"SQL ignoré : {e}")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            conn.commit()
            cursor.close()
            conn.close()
            print("DB initialisée avec succès !")
            return
        except Exception as e:
            print(f"Attente MySQL... ({e})")
            time.sleep(2)
    print("Echec connexion MySQL après 30 tentatives.")


if __name__ == '__main__':
    wait_and_init()