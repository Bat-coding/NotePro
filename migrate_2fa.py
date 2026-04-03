import mysql.connector
import os

try:
    db = mysql.connector.connect(
        host=os.getenv('DB_HOST', 'db'),
        user=os.getenv('DB_USER', 'notepro'),
        password=os.getenv('DB_PASSWORD', 'notepro'),
        database=os.getenv('DB_NAME', 'notepro')
    )
    cursor = db.cursor()
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN totp_secret VARCHAR(32) NULL;")
        cursor.execute("ALTER TABLE users ADD COLUMN totp_enabled BOOLEAN DEFAULT FALSE;")
        db.commit()
        print("Columns added successfully")
    except Exception as ie:
        db.rollback()
        print("Inner Exception:", ie)
    cursor.close()
    db.close()
except Exception as e:
    print("Exception:", e)
