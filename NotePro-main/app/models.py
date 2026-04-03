# app/models.py
from flask_login import UserMixin
from flask import g
import mysql.connector
import os
from . import db, bcrypt, login_manager


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.Enum('admin', 'professeur', 'etudiant'),  # rôles unifiés en français
        default='etudiant',
        nullable=False
    )
    totp_secret = db.Column(db.String(32), nullable=True)
    totp_enabled = db.Column(db.Boolean, default=False, nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def get_db():
    """Retourne une connexion MySQL brute (utilisée dans les routes admin/prof/etudiant)."""
    if 'db_conn' not in g:
        g.db_conn = mysql.connector.connect(
            host=os.environ.get('DB_HOST', 'db'),
            user=os.environ.get('DB_USER', 'notepro'),
            password=os.environ.get('DB_PASSWORD', 'notepro'),
            database=os.environ.get('DB_NAME', 'notepro')
        )
    return g.db_conn


def get_notes_etudiant(etudiant_id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT e.titre, n.valeur
        FROM notes n
        JOIN evaluations e ON n.evaluation_id = e.id
        WHERE n.etudiant_id = %s
    """, (etudiant_id,))
    return cur.fetchall()
