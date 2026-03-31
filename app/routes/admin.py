# app/routes/admin.py
from flask import Blueprint, render_template, request, redirect, flash
from app.decorators import role_required
from app.models import get_db
from app import bcrypt

admin_bp = Blueprint('admin', __name__)


# ── INDEX ────────────────────────────────────────────────────────────────────
@admin_bp.route('/')
@role_required('admin')
def index():
    return render_template('admin/index.html')


# ── CLASSES ──────────────────────────────────────────────────────────────────
@admin_bp.route('/classes')
@role_required('admin')
def classes():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM classes ORDER BY nom")
    return render_template('admin/classes.html', classes=cur.fetchall())


@admin_bp.route('/classes/add', methods=['POST'])
@role_required('admin')
def add_class():
    nom = request.form.get('nom', '').strip()
    if not nom:
        flash('Le nom de la classe est requis.', 'danger')
        return redirect('/admin/classes')
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO classes (nom) VALUES (%s)", (nom,))
    conn.commit()
    flash('Classe ajoutée.', 'success')
    return redirect('/admin/classes')


@admin_bp.route('/classes/delete/<int:id>')
@role_required('admin')
def delete_class(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM classes WHERE id = %s", (id,))
    conn.commit()
    flash('Classe supprimée.', 'warning')
    return redirect('/admin/classes')


# ── USERS ────────────────────────────────────────────────────────────────────
@admin_bp.route('/users')
@role_required('admin')
def users():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, username, role FROM users ORDER BY role, username")
    return render_template('admin/users.html', users=cur.fetchall())


@admin_bp.route('/users/add', methods=['POST'])
@role_required('admin')
def add_user():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    role = request.form.get('role', 'etudiant')

    if not username or not password:
        flash('Tous les champs sont requis.', 'danger')
        return redirect('/admin/users')

    if role not in ('admin', 'professeur', 'etudiant'):
        flash('Rôle invalide.', 'danger')
        return redirect('/admin/users')

    hashed = bcrypt.generate_password_hash(password).decode('utf-8')
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
        (username, hashed, role)
    )
    conn.commit()
    flash('Utilisateur créé.', 'success')
    return redirect('/admin/users')


@admin_bp.route('/users/delete/<int:id>')
@role_required('admin')
def delete_user(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = %s", (id,))
    conn.commit()
    flash('Utilisateur supprimé.', 'warning')
    return redirect('/admin/users')


# ── EMPLOIS DU TEMPS ─────────────────────────────────────────────────────────
@admin_bp.route('/emplois')
@role_required('admin')
def emplois():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT e.*, c.nom AS classe_nom, u.username AS prof_nom
        FROM emplois_du_temps e
        JOIN classes c ON e.classe_id = c.id
        LEFT JOIN users u ON e.professeur_id = u.id
        ORDER BY e.jour, e.heure_debut
    """)
    liste_emplois = cur.fetchall()
    cur.execute("SELECT * FROM classes ORDER BY nom")
    classes = cur.fetchall()
    cur.execute("SELECT id, username FROM users WHERE role = 'professeur' ORDER BY username")
    profs = cur.fetchall()
    return render_template('admin/emplois.html',
                           emplois=liste_emplois,
                           classes=classes,
                           profs=profs)


@admin_bp.route('/emplois/add', methods=['POST'])
@role_required('admin')
def add_emploi():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO emplois_du_temps
            (classe_id, jour, heure_debut, heure_fin, matiere, professeur_id)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        request.form['classe_id'],
        request.form['jour'],
        request.form['heure_debut'],
        request.form['heure_fin'],
        request.form['matiere'],
        request.form['professeur_id']
    ))
    conn.commit()
    flash('Créneau ajouté.', 'success')
    return redirect('/admin/emplois')


@admin_bp.route('/emplois/delete/<int:id>')
@role_required('admin')
def delete_emploi(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM emplois_du_temps WHERE id = %s", (id,))
    conn.commit()
    flash('Créneau supprimé.', 'warning')
    return redirect('/admin/emplois')