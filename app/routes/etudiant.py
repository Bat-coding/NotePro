# app/routes/etudiant.py
from flask import Blueprint, render_template, session, request, Response, current_app, redirect, flash
from flask_login import current_user  # FIXED [VULN-015]: Importer current_user Flask-Login
from app.decorators import role_required
from app.models import get_db, get_notes_etudiant
from datetime import date, timedelta
from app import bcrypt
import uuid
import os
import imghdr  # FIXED [VULN-008]: Pour validation du type MIME réel (magic bytes)
from werkzeug.utils import secure_filename

etu_bp = Blueprint('etudiant', __name__)

# FIXED [VULN-008]: Extensions d'images autorisées pour l'upload d'avatar
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
ALLOWED_IMAGE_MIMETYPES = {'jpeg', 'png', 'gif', 'webp', 'bmp'}


def allowed_file(filename):
    """Vérifie que l'extension du fichier est dans la liste blanche."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def validate_image_content(file_stream):
    """Vérifie le type MIME réel du fichier via ses magic bytes."""
    header = file_stream.read(512)
    file_stream.seek(0)  # Remettre le curseur au début
    fmt = imghdr.what(None, header)
    return fmt in ALLOWED_IMAGE_MIMETYPES


@etu_bp.context_processor
def inject_active_messages():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM messages_admin WHERE actif = 1 ORDER BY created_at DESC")
    msgs = cur.fetchall()
    return dict(messages_actifs=msgs)


def td_to_str(val):
    if val is None:
        return ''
    if hasattr(val, 'total_seconds'):
        total = int(val.total_seconds())
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
    return str(val)[:5]


def get_week_bounds(semaine_str=None):
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
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0",
        "PRODID:-//NotePro//FR", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
    ]
    for c in cours_list:
        dc = c.get('date_cours')
        if not dc:
            continue
        hd = c.get('heure_debut', '')
        hf = c.get('heure_fin', '')
        date_str = dc.strftime('%Y%m%d') if isinstance(dc, date) else str(dc).replace('-', '')
        start = f"{date_str}T{hd.replace(':', '')}00"
        end = f"{date_str}T{hf.replace(':', '')}00"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uuid.uuid4()}",
            f"DTSTART:{start}",
            f"DTEND:{end}",
            f"SUMMARY:{c.get('matiere', 'Cours')}",
            f"DESCRIPTION:Prof: {c.get('prof_nom', '')}",
            f"LOCATION:{c.get('salle') or ''}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


# ── INDEX ─────────────────────────────────────────────────────────────────────
@etu_bp.route('/')
@role_required('etudiant')
def index():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    etudiant_id = current_user.id

    # Récupérer la classe de l'étudiant
    cur.execute("SELECT classe_id FROM classe_etudiants WHERE etudiant_id = %s", (etudiant_id,))
    row_classe = cur.fetchone()
    classe_id = row_classe['classe_id'] if row_classe else None

    classe_nom = "Non assigné"
    if classe_id:
        cur.execute("SELECT nom FROM classes WHERE id = %s", (classe_id,))
        row_n = cur.fetchone()
        if row_n: classe_nom = row_n['nom']

    # KPI 1: Moyenne Générale
    notes = get_notes_etudiant(etudiant_id)
    valeurs_notes = [n['valeur'] for n in notes if n['valeur'] is not None]
    moyenne = sum(valeurs_notes) / len(valeurs_notes) if valeurs_notes else 0.0

    # KPI 2: Total Absences
    cur.execute("SELECT COUNT(*) as count FROM absences WHERE etudiant_id = %s AND type_absence = 'absence'", (etudiant_id,))
    total_absences = cur.fetchone()['count']

    # KPI 3: Travail à faire (Agenda futur)
    cur.execute("""
        SELECT COUNT(*) as count FROM agenda
        WHERE classe_id = %s AND date_event >= CURDATE()
    """, (classe_id,))
    total_agenda = cur.fetchone()['count']

    # Cours du jour
    today = date.today()
    cours_du_jour = []
    if classe_id:
        cur.execute("""
            SELECT e.*, u.username as prof_nom
            FROM emplois_du_temps e
            LEFT JOIN users u ON e.professeur_id = u.id
            WHERE e.classe_id = %s AND e.date_cours = %s
            ORDER BY e.heure_debut
        """, (classe_id, today))
        cours_du_jour = cur.fetchall()
        for c in cours_du_jour:
            c['heure_debut'] = td_to_str(c.get('heure_debut'))
            c['heure_fin'] = td_to_str(c.get('heure_fin'))

    # Dernières notes
    recent_notes = notes[:5]

    # Prochains travaux (Agenda)
    agenda_events = []
    if classe_id:
        cur.execute("""
            SELECT a.*, u.username as prof_nom
            FROM agenda a
            LEFT JOIN users u ON a.professeur_id = u.id
            WHERE a.classe_id = %s AND a.date_event >= CURDATE()
            ORDER BY a.date_event ASC LIMIT 5
        """, (classe_id,))
        agenda_events = cur.fetchall()

    # Alertes / Messages récents
    cur.execute("SELECT * FROM messages_admin ORDER BY created_at DESC LIMIT 5")
    recent_messages = cur.fetchall()

    # Événements pour le calendrier (tous les cours de la classe)
    calendar_events = []
    if classe_id:
        cur.execute("""
            SELECT e.*, u.username as prof_nom
            FROM emplois_du_temps e
            LEFT JOIN users u ON e.professeur_id = u.id
            WHERE e.classe_id = %s AND e.date_cours IS NOT NULL
        """, (classe_id,))
        tous_cours = cur.fetchall()

        for c in tous_cours:
            hd = td_to_str(c.get('heure_debut'))
            hf = td_to_str(c.get('heure_fin'))
            d_str = c['date_cours'].strftime('%Y-%m-%d')
            calendar_events.append({
                'title': f"{c['matiere']}",
                'start': f"{d_str}T{hd}:00",
                'end': f"{d_str}T{hf}:00",
                'backgroundColor': '#2563eb',
                'extendedProps': {
                    'salle': c.get('salle') or 'N/C',
                    'professeur': c.get('prof_nom') or 'N/C',
                    'matiere': c['matiere'],
                    'horaire': f"{hd} - {hf}"
                }
            })

    return render_template('etudiant/index.html',
                           classe_nom=classe_nom,
                           moyenne=moyenne,
                           total_absences=total_absences,
                           total_agenda=total_agenda,
                           cours_du_jour=cours_du_jour,
                           recent_notes=recent_notes,
                           agenda_events=agenda_events,
                           recent_messages=recent_messages,
                           calendar_events=calendar_events,
                           date=date)


# ── NOTES ─────────────────────────────────────────────────────────────────────
@etu_bp.route('/notes')
@role_required('etudiant')
def mes_notes():
    # FIXED [VULN-015]: Utiliser current_user.id (Flask-Login) au lieu de session['user_id']
    notes = get_notes_etudiant(current_user.id)
    return render_template('etudiant/notes.html', notes=notes)


# ── EMPLOI DU TEMPS (classe de l'étudiant uniquement) ────────────────────────
@etu_bp.route('/emploi')
@role_required('etudiant')
def emploi_du_temps():
    conn = get_db()
    cur = conn.cursor(dictionary=True)

    semaine_str = request.args.get('semaine')
    vue = request.args.get('vue', 'hebdo')
    jour_str = request.args.get('jour')
    # FIXED [VULN-015]: Utiliser current_user.id au lieu de session['user_id']
    etudiant_id = current_user.id

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

    # Cours filtrés par la/les classe(s) de l'étudiant avec vérification d'absence du professeur
    if vue == 'jour':
        cur.execute("""
            SELECT e.*, c.nom AS classe_nom, u.username AS prof_nom, pa.id AS prof_absent
            FROM emplois_du_temps e
            JOIN classes c ON e.classe_id = c.id
            LEFT JOIN users u ON e.professeur_id = u.id
            JOIN classe_etudiants ce ON e.classe_id = ce.classe_id
            LEFT JOIN professeur_absences pa ON pa.professeur_id = e.professeur_id AND pa.date_absence = e.date_cours
            WHERE ce.etudiant_id = %s AND e.date_cours = %s
            ORDER BY e.heure_debut
        """, (etudiant_id, jour_selectionne))
    else:
        cur.execute("""
            SELECT e.*, c.nom AS classe_nom, u.username AS prof_nom, pa.id AS prof_absent
            FROM emplois_du_temps e
            JOIN classes c ON e.classe_id = c.id
            LEFT JOIN users u ON e.professeur_id = u.id
            JOIN classe_etudiants ce ON e.classe_id = ce.classe_id
            LEFT JOIN professeur_absences pa ON pa.professeur_id = e.professeur_id AND pa.date_absence = e.date_cours
            WHERE ce.etudiant_id = %s AND e.date_cours BETWEEN %s AND %s
            ORDER BY e.date_cours, e.heure_debut
        """, (etudiant_id, lundi, dimanche))

    cours_list = cur.fetchall()
    for c in cours_list:
        c['heure_debut'] = td_to_str(c.get('heure_debut'))
        c['heure_fin'] = td_to_str(c.get('heure_fin'))
        c['date_cours_str'] = c['date_cours'].isoformat() if isinstance(c.get('date_cours'), date) else ''

    return render_template('etudiant/emploi.html',
                           cours=cours_list,
                           heures=heures,
                           jours_semaine=jours_semaine,
                           lundi=lundi,
                           dimanche=dimanche,
                           semaine_str=semaine_str,
                           prev_semaine=prev_semaine,
                           next_semaine=next_semaine,
                           titre_semaine=titre_semaine,
                           vue=vue,
                           jour_selectionne=jour_selectionne)


@etu_bp.route('/emploi/ical')
@role_required('etudiant')
def emploi_ical():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    # FIXED [VULN-015]: Utiliser current_user.id au lieu de session['user_id']
    cur.execute("""
        SELECT e.*, c.nom AS classe_nom, u.username AS prof_nom
        FROM emplois_du_temps e
        JOIN classes c ON e.classe_id = c.id
        LEFT JOIN users u ON e.professeur_id = u.id
        JOIN classe_etudiants ce ON e.classe_id = ce.classe_id
        WHERE ce.etudiant_id = %s AND e.date_cours IS NOT NULL
        ORDER BY e.date_cours, e.heure_debut
    """, (current_user.id,))
    cours_list = cur.fetchall()
    for c in cours_list:
        c['heure_debut'] = td_to_str(c.get('heure_debut'))
        c['heure_fin'] = td_to_str(c.get('heure_fin'))

    ical = build_ical(cours_list)
    return Response(ical, mimetype='text/calendar',
                    headers={'Content-Disposition': 'attachment; filename=mon_planning.ics'})


# ── AGENDA (vue étudiant) ─────────────────────────────────────────────────────
@etu_bp.route('/agenda')
@role_required('etudiant')
def agenda():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    # FIXED [VULN-015]: Utiliser current_user.id au lieu de session['user_id']
    etudiant_id = current_user.id

    mois_str = request.args.get('mois')
    today = date.today()
    if mois_str:
        try:
            first_of_month = date.fromisoformat(mois_str + '-01')
        except ValueError:
            first_of_month = today.replace(day=1)
    else:
        first_of_month = today.replace(day=1)

    if first_of_month.month == 12:
        last_of_month = first_of_month.replace(year=first_of_month.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last_of_month = first_of_month.replace(month=first_of_month.month + 1, day=1) - timedelta(days=1)

    prev_mois = (first_of_month - timedelta(days=1)).strftime('%Y-%m')
    next_mois = (last_of_month + timedelta(days=1)).strftime('%Y-%m')

    cur.execute("""
        SELECT a.*, c.nom as classe_nom, u.username as prof_nom
        FROM agenda a
        JOIN classes c ON a.classe_id = c.id
        LEFT JOIN users u ON a.professeur_id = u.id
        JOIN classe_etudiants ce ON a.classe_id = ce.classe_id
        WHERE ce.etudiant_id = %s AND a.date_event BETWEEN %s AND %s
        ORDER BY a.date_event
    """, (etudiant_id, first_of_month, last_of_month))
    evenements = cur.fetchall()

    return render_template('etudiant/agenda.html',
                           evenements=evenements,
                           first_of_month=first_of_month,
                           last_of_month=last_of_month,
                           prev_mois=prev_mois,
                           next_mois=next_mois,
                           today=today)


# ── ABSENCES (vue étudiant) ───────────────────────────────────────────────────
@etu_bp.route('/absences')
@role_required('etudiant')
def mes_absences():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    # FIXED [VULN-015]: Utiliser current_user.id au lieu de session['user_id']
    etudiant_id = current_user.id

    cur.execute("""
        SELECT ab.*, u.username as prof_nom
        FROM absences ab
        LEFT JOIN users u ON ab.professeur_id = u.id
        WHERE ab.etudiant_id = %s
        ORDER BY ab.date_absence DESC
    """, (etudiant_id,))
    absences = cur.fetchall()

    total = len(absences)
    nb_abs = sum(1 for a in absences if a['type_absence'] == 'absence')
    nb_ret = sum(1 for a in absences if a['type_absence'] == 'retard')
    nb_just = sum(1 for a in absences if a['justifiee'])

    return render_template('etudiant/absences.html',
                           absences=absences,
                           total=total,
                           nb_abs=nb_abs,
                           nb_ret=nb_ret,
                           nb_just=nb_just)


# ── MENU CANTINE (vue étudiant) ───────────────────────────────────────────────
@etu_bp.route('/cantine')
@role_required('etudiant')
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

    return render_template('etudiant/cantine.html',
                           menus=menus,
                           jours_semaine=jours_semaine,
                           lundi=lundi,
                           dimanche=dimanche,
                           semaine_str=lundi.isoformat(),
                           prev_semaine=prev_semaine,
                           next_semaine=next_semaine,
                           titre_semaine=titre_semaine,
                           today=today)

