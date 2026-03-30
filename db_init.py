import mysql.connector, time, os

def wait_and_init():
    for _ in range(30):
        try:
            db = mysql.connector.connect(
                host=os.getenv('DB_HOST', 'db'),
                user=os.getenv('DB_USER', 'root'),
                password=os.getenv('DB_PASSWORD', 'rootpassword'),
                database=os.getenv('DB_NAME', 'notepro')
            )
            cursor = db.cursor()
            with open('/app/db/init.sql', 'r') as f:
                for stmt in f.read().split(';'):
                    s = stmt.strip()
                    if s:
                        try:
                            cursor.execute(s)
                        except:
                            pass
            db.commit()
            print("DB initialisée !")
            return
        except:
            print("Attente MySQL...")
            time.sleep(2)

if __name__ == '__main__':
    wait_and_init()