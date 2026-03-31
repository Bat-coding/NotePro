import mysql.connector
import os
from flask_bcrypt import Bcrypt

def fix_admin():
    bcrypt = Bcrypt()
    hashed = bcrypt.generate_password_hash('admin123').decode('utf-8')
    
    try:
        db = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'notepro'),
            password=os.getenv('DB_PASSWORD', 'notepro'),
            database=os.getenv('DB_NAME', 'notepro'),
            port=3306
        )
        cursor = db.cursor()
        # Delete existing admin to be sure
        cursor.execute("DELETE FROM users WHERE username = 'admin_fix'")
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
            ('admin_fix', hashed, 'admin')
        )
        db.commit()
        print("User admin_fix created with password: admin123")
        cursor.close()
        db.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    fix_admin()
