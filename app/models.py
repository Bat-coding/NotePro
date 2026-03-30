import mysql.connector, os

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "db"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "notepro")
    )

def get_user_by_username(username):
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    return cur.fetchone()

def get_notes_etudiant(etudiant_id):
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT e.titre, n.valeur FROM notes n
        JOIN evaluations e ON n.evaluation_id = e.id
        WHERE n.etudiant_id = %s
    """, (etudiant_id,))
    return cur.fetchall()

def get_classes():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM classes")
    return cur.fetchall()