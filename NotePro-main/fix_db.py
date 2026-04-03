# fix_db.py
# FIXED [VULN-001]: Suppression du mot de passe 'admin123' codé en dur
# Usage: ADMIN_PASSWORD=<mot_de_passe_fort> python fix_db.py
# Ce script crée un utilisateur admin de secours (admin_fix) avec un mot de passe fourni en env var

import mysql.connector
import os
from flask_bcrypt import Bcrypt


def fix_admin():
    # FIXED [VULN-001]: Lire le mot de passe depuis une variable d'environnement
    admin_password = os.environ.get('ADMIN_PASSWORD')
    if not admin_password:
        raise SystemExit(
            "ERREUR : Vous devez définir la variable d'environnement ADMIN_PASSWORD.\n"
            "Usage: ADMIN_PASSWORD='<mot_de_passe_fort>' python fix_db.py"
        )

    # FIXED [VULN-010]: Valider la complexité minimale
    if len(admin_password) < 8:
        raise SystemExit("ERREUR : Le mot de passe doit contenir au moins 8 caractères.")

    bcrypt = Bcrypt()
    hashed = bcrypt.generate_password_hash(admin_password).decode('utf-8')

    try:
        db = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'notepro'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'notepro'),
            port=3306
        )
        cursor = db.cursor()
        cursor.execute("DELETE FROM users WHERE username = 'admin_fix'")
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
            ('admin_fix', hashed, 'admin')
        )
        db.commit()
        # FIXED [VULN-001]: Ne jamais afficher le mot de passe dans les logs
        print("Utilisateur admin_fix créé avec succès.")
        cursor.close()
        db.close()
    except Exception as e:
        # FIXED: Message d'erreur générique sans détails système
        print("Erreur lors de la création de l'utilisateur admin_fix.")


if __name__ == '__main__':
    fix_admin()
