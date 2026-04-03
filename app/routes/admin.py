# app/routes/admin.py
from flask import Blueprint, render_template, request, redirect, flash, Response
from flask_login import current_user  # FIXED [VULN-015]: Utiliser current_user Flask-Login
from app.decorators import role_required
from app.models import get_db
from app import bcrypt
from datetime import date, timedelta
import uuid
import re

admin_bp = Blueprint('admin', __name__)


# ── Helpers ───────────────────────────────────────────────────────────────────
def td_to_str(val):
    """Convertit un timedelta MySQL en string HH:MM."""
    if val is None:
        return ''
    if hasattr(val, 'total_seconds'):
        total = int(val.total_seconds())
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
    return str(val)[:5]


def get_week_bounds(semaine_str=None):
    """Retourne (lundi, dimanche) de la semaine donnée ('YYYY-MM-DD' = lundi)."""
    if semaine_str:
        try:
            lundi = date.fromisoformat(semaine_str)
            lundi = lundi - timedelta(days=lundi.weekday())
        except ValueError:
            lundi = date.today() - timedelta(days=date.today().weekday())
    else:
        lundi = date.today() - timedelta(days=date.today().weekday())
    dimanche = lundi + timedelta(days=6)
    return lundi, dimanche


def build_ical(cours_list):
    """Génère un fichier iCal à partir d'une liste de cours."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//NotePro//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for c in cours_list:
        dc = c.get('date_cours')
        if not dc:
            continue
        hd = c.get('heure_debut', '')
        hf = c.get('heure_fin', '')
        if isinstance(dc, date):
            date_str = dc.strftime('%Y%m%d')
        else:
            date_str = str(dc).replace('-', '')
        start = f"{date_str}T{hd.replace(':', '')}00"
        end = f"{date_str}T{hf.replace(':', '')}00"
        uid = str(uuid.uuid4())
        summary = c.get('matiere', 'Cours')
        desc = f"Classe: {c.get('classe_nom', '')} | Prof: {c.get('prof_nom', '')}"
        location = c.get('salle') or ''
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTART:{start}",
            f"DTEND:{end}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{desc}",
            f"LOCATION:{location}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


# ── INDEX ─────────────────────────────────────────────────────────────────────
@admin_bp.route('/')
@role_required('admin')
def index():
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # KPIs
    cur.execute("SELECT COUNT(*) as count FROM users WHERE role = 'etudiant'")
    total_eleves = cur.fetchone()['count']

    cur.execute("SELECT COUNT(*) as count FROM users WHERE role = 'professeur'")
    total_enseignants = cur.fetchone()['count']

    cur.execute("SELECT COUNT(*) as count FROM classes")
    total_classes = cur.fetchone()['count']

    cur.execute("SELECT COUNT(*) as count FROM absences")
    total_absences = cur.fetchone()['count']

    # Dernières Évaluations
    cur.execute("""
        SELECT ev.*, c.nom as classe_nom, u.username as prof_nom
        FROM evaluations ev
        JOIN classes c ON ev.classe_id = c.id
        LEFT JOIN users u ON ev.professeur_id = u.id
        ORDER BY ev.id DESC LIMIT 6
    """)
    dernieres_evaluations = cur.fetchall()

    # Nouveaux Utilisateurs
    cur.execute("""
        SELECT username, role, created_at
        FROM users
        ORDER BY id DESC LIMIT 6
    """)
    nouveaux_utilisateurs = cur.fetchall()

    # Evenements du calendrier (Tous les cours)
    cur.execute("""
        SELECT e.*, c.nom as classe_nom, u.username as prof_nom
        FROM emplois_du_temps e
        JOIN classes c ON e.classe_id = c.id
        LEFT JOIN users u ON e.professeur_id = u.id
        WHERE e.date_cours IS NOT NULL
    """)
    tous_cours = cur.fetchall()

    calendar_events = []
    for c in tous_cours:
        hd = td_to_str(c.get('heure_debut'))
        hf = td_to_str(c.get('heure_fin'))
        dc = c.get('date_cours').isoformat()

        # Format string for datetime needed by FullCalendar
        start_time = f"{dc}T{hd}:00"
        end_time = f"{dc}T{hf}:00"

        # Alternating colors based on some attribute (e.g. hash of class name)
        calendar_events.append({
            'title': f"{c['matiere']} ({c['classe_nom']})",
            'start': start_time,
            'end': end_time,
            'backgroundColor': '#3b82f6' if 'EPS' not in c['matiere'] else '#10b981',
            'borderColor': 'transparent',
            'textColor': 'white',
            'display': 'block',
            'extendedProps': {
                'matiere': c['matiere'],
                'classe': c['classe_nom'],
                'professeur': c['prof_nom'] or 'Non attribué',
                'salle': c.get('salle') or 'Non spécifiée',
                'horaire': f"{hd} - {hf}"
            }
        })

    # Alertes / Messages récents
    cur.execute("SELECT * FROM messages_admin ORDER BY created_at DESC LIMIT 5")
    recent_messages = cur.fetchall()

    return render_template('admin/index.html',
                           total_eleves=total_eleves,
                           total_enseignants=total_enseignants,
                           total_classes=total_classes,
                           total_absences=total_absences,
                           dernieres_evaluations=dernieres_evaluations,
                           nouveaux_utilisateurs=nouveaux_utilisateurs,
                           recent_messages=recent_messages,
                           calendar_events=calendar_events)


# ── CLASSES ───────────────────────────────────────────────────────────────────
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


# FIXED [VULN-005]: Convertir la route DELETE en POST pour protection CSRF
# Ancienne route GET retirée: @admin_bp.route('/classes/delete/<int:id>')
@admin_bp.route('/classes/delete/<int:id>', methods=['POST'])
@role_required('admin')
def delete_class(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM classes WHERE id = %s", (id,))
    conn.commit()
    flash('Classe supprimée.', 'warning')
    return redirect('/admin/classes')


@admin_bp.route('/classes/<int:id>')
@role_required('admin')
def class_detail(id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM classes WHERE id = %s", (id,))
    classe = cur.fetchone()
    if not classe:
        flash("Classe introuvable.", "danger")
        return redirect('/admin/classes')

    cur.execute("""
        SELECT u.id, u.username, u.telephone
        FROM users u
        JOIN classe_etudiants ce ON u.id = ce.etudiant_id
        WHERE ce.classe_id = %s
        ORDER BY u.username
    """, (id,))
    etudiants = cur.fetchall()

    cur.execute("""
        SELECT id, username FROM users
        WHERE role = 'etudiant'
        AND id NOT IN (SELECT etudiant_id FROM classe_etudiants WHERE classe_id = %s)
        ORDER BY username
    """, (id,))
    etudiants_dispo = cur.fetchall()

    return render_template(
        'admin/classe_detail.html',
        classe=classe,
        etudiants=etudiants,
        etudiants_dispo=etudiants_dispo)


@admin_bp.route('/classes/edit/<int:id>', methods=['POST'])
@role_required('admin')
def edit_class(id):
    nom = request.form.get('nom', '').strip()
    if nom:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("UPDATE classes SET nom = %s WHERE id = %s", (nom, id))
        conn.commit()
        flash('Nom de la classe modifié.', 'success')
    return redirect(f'/admin/classes/{id}')


@admin_bp.route('/classes/add_student/<int:id>', methods=['POST'])
@role_required('admin')
def add_student_to_class(id):
    etudiant_id = request.form.get('etudiant_id')
    if etudiant_id:
        conn = get_db()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO classe_etudiants (etudiant_id, classe_id) VALUES (%s, %s)", (etudiant_id, id))
            conn.commit()
            flash('Étudiant ajouté à la classe.', 'success')
        except Exception:
            flash("L'étudiant est déjà dans cette classe.", "warning")
    return redirect(f'/admin/classes/{id}')


# FIXED [VULN-005]: Convertir en POST pour protection CSRF
@admin_bp.route('/classes/remove_student/<int:classe_id>/<int:etudiant_id>', methods=['POST'])
@role_required('admin')
def remove_student_from_class(classe_id, etudiant_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM classe_etudiants WHERE classe_id = %s AND etudiant_id = %s", (classe_id, etudiant_id))
    conn.commit()
    flash('Étudiant retiré de la classe.', 'warning')
    return redirect(f'/admin/classes/{classe_id}')


# ── USERS ─────────────────────────────────────────────────────────────────────
@admin_bp.route('/users')
@role_required('admin')
def users():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, username, role, totp_enabled FROM users ORDER BY role, username")
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
    if len(password) < 15 or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        flash('Le mot de passe doit contenir au moins 15 caractères et un caractère spécial.', 'danger')
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


# FIXED [VULN-005]: Convertir en POST pour protection CSRF
@admin_bp.route('/users/delete/<int:id>', methods=['POST'])
@role_required('admin')
def delete_user(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = %s", (id,))
    conn.commit()
    flash('Utilisateur supprimé.', 'warning')
    return redirect('/admin/users')


@admin_bp.route('/users/delete_2fa/<int:id>', methods=['POST'])
@role_required('admin')
def delete_user_2fa(id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT role FROM users WHERE id = %s", (id,))
    user = cur.fetchone()

    if user:
        if user['role'] != 'admin':
            cur = conn.cursor()
            cur.execute("UPDATE users SET totp_enabled = FALSE, totp_secret = NULL WHERE id = %s", (id,))
            conn.commit()
            flash("La double authentification de l'utilisateur a été désactivée.", 'info')
        else:
            flash("Impossible de désactiver le 2FA d'un autre administrateur.", 'danger')

    return redirect('/admin/users')


@admin_bp.route('/users/changepwd/<int:id>', methods=['POST'])
@role_required('admin')
def admin_change_pwd(id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT role FROM users WHERE id = %s", (id,))
    target_user = cur.fetchone()

    if not target_user:
        flash("Utilisateur introuvable.", "danger")
        return redirect('/admin/users')

    if target_user['role'] == 'admin':
        flash("Sécurité : Un administrateur ne peut pas changer le mot de passe d'un autre administrateur.", "danger")
        return redirect('/admin/users')

    new_password = request.form['new_password']

    if len(new_password) < 15 or not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
        flash("La politique de sécurité exige 15 caractères et 1 caractère spécial minimum.", "danger")
        return redirect('/admin/users')

    pw_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
    cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (pw_hash, id))
    conn.commit()
    flash("Le mot de passe de l'utilisateur a été mis à jour avec succès.", "success")
    return redirect('/admin/users')

# ── EMPLOIS DU TEMPS ──────────────────────────────────────────────────────────


@admin_bp.route('/emplois')
@role_required('admin')
def emplois():
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    semaine_str = request.args.get('semaine')
    vue = request.args.get('vue', 'hebdo')
    jour_str = request.args.get('jour')
    classe_id = request.args.get('classe_id', type=int)

    lundi, dimanche = get_week_bounds(semaine_str)
    semaine_str = lundi.isoformat()

    prev_semaine = (lundi - timedelta(weeks=1)).isoformat()
    next_semaine = (lundi + timedelta(weeks=1)).isoformat()

    titre_semaine = f"{lundi.strftime('%-d %b')} – {dimanche.strftime('%-d %b %Y')}"

    jours_semaine = [lundi + timedelta(days=i) for i in range(7)]

    if vue == 'jour' and jour_str:
        try:
            jour_selectionne = date.fromisoformat(jour_str)
        except ValueError:
            jour_selectionne = lundi
    else:
        jour_selectionne = lundi

    heures = [f"{h:02d}:00" for h in range(6, 20)]

    cur.execute("SELECT * FROM classes ORDER BY nom")
    classes = cur.fetchall()

    cur.execute("SELECT id, username FROM users WHERE role = 'professeur' ORDER BY username")
    profs = cur.fetchall()

    if vue == 'jour':
        if classe_id:
            cur.execute("""
                SELECT e.*, c.nom AS classe_nom, u.username AS prof_nom
                FROM emplois_du_temps e
                JOIN classes c ON e.classe_id = c.id
                LEFT JOIN users u ON e.professeur_id = u.id
                WHERE e.date_cours = %s AND e.classe_id = %s
                ORDER BY e.heure_debut
            """, (jour_selectionne, classe_id))
        else:
            cur.execute("""
                SELECT e.*, c.nom AS classe_nom, u.username AS prof_nom
                FROM emplois_du_temps e
                JOIN classes c ON e.classe_id = c.id
                LEFT JOIN users u ON e.professeur_id = u.id
                WHERE e.date_cours = %s
                ORDER BY e.heure_debut
            """, (jour_selectionne,))
    else:
        if classe_id:
            cur.execute("""
                SELECT e.*, c.nom AS classe_nom, u.username AS prof_nom
                FROM emplois_du_temps e
                JOIN classes c ON e.classe_id = c.id
                LEFT JOIN users u ON e.professeur_id = u.id
                WHERE e.date_cours BETWEEN %s AND %s AND e.classe_id = %s
                ORDER BY e.date_cours, e.heure_debut
            """, (lundi, dimanche, classe_id))
        else:
            cur.execute("""
                SELECT e.*, c.nom AS classe_nom, u.username AS prof_nom
                FROM emplois_du_temps e
                JOIN classes c ON e.classe_id = c.id
                LEFT JOIN users u ON e.professeur_id = u.id
                WHERE e.date_cours BETWEEN %s AND %s
                ORDER BY e.date_cours, e.heure_debut
            """, (lundi, dimanche))

    cours_list = cur.fetchall()
    for c in cours_list:
        c['heure_debut'] = td_to_str(c.get('heure_debut'))
        c['heure_fin'] = td_to_str(c.get('heure_fin'))
        if isinstance(c.get('date_cours'), date):
            c['date_cours_str'] = c['date_cours'].isoformat()
        else:
            c['date_cours_str'] = ''

    return render_template('admin/emplois.html',
                           cours=cours_list,
                           classes=classes,
                           profs=profs,
                           heures=heures,
                           jours_semaine=jours_semaine,
                           lundi=lundi,
                           dimanche=dimanche,
                           semaine_str=semaine_str,
                           prev_semaine=prev_semaine,
                           next_semaine=next_semaine,
                           titre_semaine=titre_semaine,
                           vue=vue,
                           jour_selectionne=jour_selectionne,
                           selected_classe=classe_id)


@admin_bp.route('/emplois/add', methods=['POST'])
@role_required('admin')
def add_emploi():
    conn = get_db()
    cur = conn.cursor()
    date_cours = request.form.get('date_cours')
    if not date_cours:
        flash('La date du cours est obligatoire.', 'danger')
        return redirect('/admin/emplois')

    dc = date.fromisoformat(date_cours)
    jours_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    jour = jours_fr[dc.weekday()]

    cur.execute("""
        INSERT INTO emplois_du_temps
            (classe_id, date_cours, jour, heure_debut, heure_fin, matiere, salle, professeur_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        request.form['classe_id'],
        date_cours,
        jour,
        request.form['heure_debut'],
        request.form['heure_fin'],
        request.form['matiere'],
        request.form.get('salle', ''),
        request.form.get('professeur_id') or None,
    ))
    conn.commit()
    flash('Créneau ajouté.', 'success')
    semaine = (dc - timedelta(days=dc.weekday())).isoformat()
    return redirect(f'/admin/emplois?semaine={semaine}')


# FIXED [VULN-005]: Convertir en POST pour protection CSRF
@admin_bp.route('/emplois/delete/<int:id>', methods=['POST'])
@role_required('admin')
def delete_emploi(id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT date_cours FROM emplois_du_temps WHERE id = %s", (id,))
    row = cur.fetchone()
    conn.cursor().execute("DELETE FROM emplois_du_temps WHERE id = %s", (id,))
    conn.commit()
    flash('Créneau supprimé.', 'warning')
    if row and row.get('date_cours'):
        dc = row['date_cours']
        semaine = (dc - timedelta(days=dc.weekday())).isoformat()
        return redirect(f'/admin/emplois?semaine={semaine}')
    return redirect('/admin/emplois')


@admin_bp.route('/emplois/ical')
@role_required('admin')
def emplois_ical():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT e.*, c.nom AS classe_nom, u.username AS prof_nom
        FROM emplois_du_temps e
        JOIN classes c ON e.classe_id = c.id
        LEFT JOIN users u ON e.professeur_id = u.id
        WHERE e.date_cours IS NOT NULL
        ORDER BY e.date_cours, e.heure_debut
    """)
    cours_list = cur.fetchall()
    for c in cours_list:
        c['heure_debut'] = td_to_str(c.get('heure_debut'))
        c['heure_fin'] = td_to_str(c.get('heure_fin'))

    ical = build_ical(cours_list)
    return Response(ical, mimetype='text/calendar',
                    headers={'Content-Disposition': 'attachment; filename=planning_notepro.ics'})


# ── MENU CANTINE ──────────────────────────────────────────────────────────────
@admin_bp.route('/cantine')
@role_required('admin')
def cantine():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    semaine_str = request.args.get('semaine')
    today = date.today()

    if semaine_str:
        try:
            lundi = date.fromisoformat(semaine_str)
            lundi = lundi - timedelta(days=lundi.weekday())
        except ValueError:
            lundi = today - timedelta(days=today.weekday())
    else:
        lundi = today - timedelta(days=today.weekday())

    dimanche = lundi + timedelta(days=6)
    prev_semaine = (lundi - timedelta(weeks=1)).isoformat()
    next_semaine = (lundi + timedelta(weeks=1)).isoformat()
    titre_semaine = f"{lundi.strftime('%-d %b')} – {dimanche.strftime('%-d %b %Y')}"
    jours_semaine = [lundi + timedelta(days=i) for i in range(7)]

    cur.execute("""
        SELECT * FROM menu_cantine
        WHERE date_menu BETWEEN %s AND %s
        ORDER BY date_menu
    """, (lundi, dimanche))
    menus = {row['date_menu']: row for row in cur.fetchall()}

    return render_template('admin/cantine.html',
                           menus=menus,
                           jours_semaine=jours_semaine,
                           lundi=lundi,
                           dimanche=dimanche,
                           semaine_str=lundi.isoformat(),
                           prev_semaine=prev_semaine,
                           next_semaine=next_semaine,
                           titre_semaine=titre_semaine,
                           today=today)


@admin_bp.route('/cantine/save', methods=['POST'])
@role_required('admin')
def save_cantine():
    conn = get_db()
    cur = conn.cursor()
    date_menu = request.form['date_menu']
    plat = request.form.get('plat_principal', '').strip()
    if not plat:
        flash('Le plat principal est obligatoire.', 'danger')
        return redirect('/admin/cantine')

    cur.execute("""
        INSERT INTO menu_cantine (date_menu, entree, plat_principal, accompagnement, dessert, regime_special)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            entree = VALUES(entree),
            plat_principal = VALUES(plat_principal),
            accompagnement = VALUES(accompagnement),
            dessert = VALUES(dessert),
            regime_special = VALUES(regime_special)
    """, (
        date_menu,
        request.form.get('entree', ''),
        plat,
        request.form.get('accompagnement', ''),
        request.form.get('dessert', ''),
        request.form.get('regime_special', ''),
    ))
    conn.commit()
    flash('Menu enregistré.', 'success')
    d = date.fromisoformat(date_menu)
    semaine = (d - timedelta(days=d.weekday())).isoformat()
    return redirect(f'/admin/cantine?semaine={semaine}')


# FIXED [VULN-005]: Convertir en POST pour protection CSRF
@admin_bp.route('/cantine/delete/<int:id>', methods=['POST'])
@role_required('admin')
def delete_cantine(id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT date_menu FROM menu_cantine WHERE id = %s", (id,))
    row = cur.fetchone()
    conn.cursor().execute("DELETE FROM menu_cantine WHERE id = %s", (id,))
    conn.commit()
    flash('Menu supprimé.', 'warning')
    if row:
        d = row['date_menu']
        semaine = (d - timedelta(days=d.weekday())).isoformat()
        return redirect(f'/admin/cantine?semaine={semaine}')
    return redirect('/admin/cantine')


# ── AFFECTATIONS PROFESSEURS ──────────────────────────────────────────────────
@admin_bp.route('/affectations')
@role_required('admin')
def affectations():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM classes ORDER BY nom")
    classes = cur.fetchall()
    cur.execute("SELECT id, username FROM users WHERE role = 'professeur' ORDER BY username")
    profs = cur.fetchall()

    cur.execute("""
        SELECT cp.*, c.nom as classe_nom, p.username as prof_nom
        FROM classe_professeurs cp
        JOIN classes c ON cp.classe_id = c.id
        JOIN users p ON cp.professeur_id = p.id
        ORDER BY c.nom, p.username
    """)
    affectations_list = cur.fetchall()

    return render_template('admin/affectations.html', classes=classes, profs=profs, affectations=affectations_list)


@admin_bp.route('/affectations/add', methods=['POST'])
@role_required('admin')
def add_affectation():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO classe_professeurs (classe_id, professeur_id, matiere)
            VALUES (%s, %s, %s)
        """, (request.form['classe_id'], request.form['professeur_id'], request.form['matiere']))
        conn.commit()
        flash('Affectation ajoutée.', 'success')
    except Exception:
        flash('Erreur ou doublon.', 'danger')
    return redirect('/admin/affectations')


# FIXED [VULN-005]: Convertir en POST pour protection CSRF
@admin_bp.route('/affectations/delete/<int:id>', methods=['POST'])
@role_required('admin')
def delete_affectation(id):
    conn = get_db()
    conn.cursor().execute("DELETE FROM classe_professeurs WHERE id = %s", (id,))
    conn.commit()
    flash('Affectation supprimée.', 'warning')
    return redirect('/admin/affectations')


# ── ABSENCES PROFESSEURS ──────────────────────────────────────────────────────
@admin_bp.route('/prof_absences')
@role_required('admin')
def prof_absences():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, username FROM users WHERE role = 'professeur' ORDER BY username")
    profs = cur.fetchall()

    cur.execute("""
        SELECT a.*, p.username as prof_nom
        FROM professeur_absences a
        JOIN users p ON a.professeur_id = p.id
        ORDER BY a.date_absence DESC
    """)
    absences_list = cur.fetchall()

    return render_template('admin/prof_absences.html', profs=profs, absences=absences_list, today=date.today())


@admin_bp.route('/prof_absences/add', methods=['POST'])
@role_required('admin')
def add_prof_absence():
    conn = get_db()
    try:
        conn.cursor().execute("""
            INSERT INTO professeur_absences (professeur_id, date_absence)
            VALUES (%s, %s)
        """, (request.form['professeur_id'], request.form['date_absence']))
        conn.commit()
        flash('Absence enregistrée.', 'success')
    except Exception:
        flash('Erreur ou doublon.', 'danger')
    return redirect('/admin/prof_absences')


# FIXED [VULN-005]: Convertir en POST pour protection CSRF
@admin_bp.route('/prof_absences/delete/<int:id>', methods=['POST'])
@role_required('admin')
def delete_prof_absence(id):
    conn = get_db()
    conn.cursor().execute("DELETE FROM professeur_absences WHERE id = %s", (id,))
    conn.commit()
    flash('Absence supprimée.', 'warning')
    return redirect('/admin/prof_absences')


# ── MESSAGES D'ADMINISTRATION ─────────────────────────────────────────────────
@admin_bp.route('/messages')
@role_required('admin')
def messages():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM messages_admin ORDER BY created_at DESC")
    msgs = cur.fetchall()
    return render_template('admin/messages.html', messages=msgs)


@admin_bp.route('/messages/add', methods=['POST'])
@role_required('admin')
def add_message():
    conn = get_db()
    contenu = request.form.get('contenu', '').strip()
    if contenu:
        conn.cursor().execute("INSERT INTO messages_admin (contenu) VALUES (%s)", (contenu,))
        conn.commit()
        flash('Message publié.', 'success')
    return redirect('/admin/messages')


# FIXED [VULN-005]: Convertir en POST pour protection CSRF
@admin_bp.route('/messages/toggle/<int:id>', methods=['POST'])
@role_required('admin')
def toggle_message(id):
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT actif FROM messages_admin WHERE id = %s", (id,))
    row = cur.fetchone()
    if row:
        new_val = 0 if row['actif'] else 1
        conn.cursor().execute("UPDATE messages_admin SET actif = %s WHERE id = %s", (new_val, id))
        conn.commit()
    return redirect('/admin/messages')


# FIXED [VULN-005]: Convertir en POST pour protection CSRF
@admin_bp.route('/messages/delete/<int:id>', methods=['POST'])
@role_required('admin')
def delete_message(id):
    conn = get_db()
    conn.cursor().execute("DELETE FROM messages_admin WHERE id = %s", (id,))
    conn.commit()
    return redirect('/admin/messages')


# ── ABSENCES ETUDIANTS (VUE ADMIN) ─────────────────────────────────────────────
@admin_bp.route('/etudiant_absences')
@role_required('admin')
def etudiant_absences():
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    # Récupérer toutes les absences élèves pour la vue globale admin
    cur.execute("""
        SELECT a.*, e.username as etudiant_nom, p.username as prof_nom, c.nom as classe_nom
        FROM absences a
        JOIN users e ON a.etudiant_id = e.id
        LEFT JOIN users p ON a.professeur_id = p.id
        LEFT JOIN classes c ON a.classe_id = c.id
        ORDER BY a.date_absence DESC, a.created_at DESC
    """)
    absences_list = cur.fetchall()

    return render_template('admin/etudiant_absences.html', absences=absences_list)


@admin_bp.route('/etudiant_absences/justifier/<int:id>', methods=['POST'])
@role_required('admin')
def justifier_absence(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE absences SET justifiee = TRUE WHERE id = %s", (id,))
    conn.commit()
    flash('Absence marquée comme justifiée.', 'success')
    return redirect('/admin/etudiant_absences')


@admin_bp.route('/etudiant_absences/delete/<int:id>', methods=['POST'])
@role_required('admin')
def delete_etudiant_absence(id):
    conn = get_db()
    conn.cursor().execute("DELETE FROM absences WHERE id = %s", (id,))
    conn.commit()
    flash('Absence supprimée.', 'warning')
    return redirect('/admin/etudiant_absences')
