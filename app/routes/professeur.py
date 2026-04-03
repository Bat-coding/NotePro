# app/routes/professeur.py
from flask import Blueprint, render_template, request, redirect, flash, session, Response
from flask_login import current_user  # FIXED [VULN-015]: Utiliser current_user Flask-Login
from app.decorators import role_required
from app.models import get_db
from datetime import date, timedelta, datetime
import uuid

prof_bp = Blueprint('professeur', __name__)


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
            f"DESCRIPTION:Classe: {c.get('classe_nom', '')}",
            f"LOCATION:{c.get('salle') or ''}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


# ── INDEX ─────────────────────────────────────────────────────────────────────
@prof_bp.route('/')
@role_required('professeur')
def index():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    prof_id = current_user.id
    
    # KPI 1: Nombre de classes
    cur.execute("SELECT COUNT(DISTINCT classe_id) as count FROM classe_professeurs WHERE professeur_id = %s", (prof_id,))
    total_classes = cur.fetchone()['count']
    
    # KPI 2: Nombre d'élèves total
    cur.execute("""
        SELECT COUNT(DISTINCT ce.etudiant_id) as count 
        FROM classe_etudiants ce 
        JOIN classe_professeurs cp ON ce.classe_id = cp.classe_id 
        WHERE cp.professeur_id = %s
    """, (prof_id,))
    total_eleves = cur.fetchone()['count']
    
    # KPI 3: Heures de cours cette semaine
    today = date.today()
    lundi = today - timedelta(days=today.weekday())
    dimanche = lundi + timedelta(days=6)
    cur.execute("""
        SELECT SUM(TIMESTAMPDIFF(MINUTE, heure_debut, heure_fin))/60 as total_hours 
        FROM emplois_du_temps 
        WHERE professeur_id = %s AND date_cours BETWEEN %s AND %s
    """, (prof_id, lundi, dimanche))
    res_hours = cur.fetchone()['total_hours']
    total_heures = float(res_hours) if res_hours else 0.0
    
    # KPI 4: Absences signalées (total historique)
    cur.execute("SELECT COUNT(*) as count FROM absences WHERE professeur_id = %s", (prof_id,))
    total_absences_signalees = cur.fetchone()['count']
    
    # Cours du jour
    cur.execute("""
        SELECT e.*, c.nom as classe_nom 
        FROM emplois_du_temps e
        JOIN classes c ON e.classe_id = c.id
        WHERE e.professeur_id = %s AND e.date_cours = %s
        ORDER BY e.heure_debut
    """, (prof_id, today))
    cours_du_jour = cur.fetchall()
    for c in cours_du_jour:
        c['heure_debut'] = td_to_str(c.get('heure_debut'))
        c['heure_fin'] = td_to_str(c.get('heure_fin'))
        
    # Dernières évaluations créées
    cur.execute("""
        SELECT ev.*, c.nom as classe_nom 
        FROM evaluations ev
        JOIN classes c ON ev.classe_id = c.id
        WHERE ev.professeur_id = %s
        ORDER BY ev.id DESC LIMIT 5
    """, (prof_id,))
    recent_evals = cur.fetchall()
    
    # Alertes / Messages récents
    cur.execute("SELECT * FROM messages_admin ORDER BY created_at DESC LIMIT 5")
    recent_messages = cur.fetchall()
    
    # Événements pour le calendrier (tous les cours du prof)
    cur.execute("""
        SELECT e.*, c.nom as classe_nom 
        FROM emplois_du_temps e
        JOIN classes c ON e.classe_id = c.id
        WHERE e.professeur_id = %s AND e.date_cours IS NOT NULL
    """, (prof_id,))
    tous_cours = cur.fetchall()
    
    calendar_events = []
    for c in tous_cours:
        hd = td_to_str(c.get('heure_debut'))
        hf = td_to_str(c.get('heure_fin'))
        d_str = c['date_cours'].strftime('%Y-%m-%d')
        calendar_events.append({
            'title': f"{c['matiere']} ({c['classe_nom']})",
            'start': f"{d_str}T{hd}:00",
            'end': f"{d_str}T{hf}:00",
            'backgroundColor': '#2563eb' if c.get('salle') else '#64748b',
            'extendedProps': {
                'salle': c.get('salle') or 'N/C',
                'classe': c['classe_nom'],
                'matiere': c['matiere'],
                'horaire': f"{hd} - {hf}"
            }
        })
    
    return render_template('professeur/index.html',
                           total_classes=total_classes,
                           total_eleves=total_eleves,
                           total_heures=total_heures,
                           total_absences=total_absences_signalees,
                           cours_du_jour=cours_du_jour,
                           recent_evals=recent_evals,
                           recent_messages=recent_messages,
                           calendar_events=calendar_events,
                           date=date)


# ── EMPLOI DU TEMPS (toutes classes) ─────────────────────────────────────────
@prof_bp.route('/emploi')
@role_required('professeur')
def emploi_du_temps():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    # FIXED [VULN-015]: Utiliser current_user.id au lieu de session['user_id']
    prof_id = current_user.id

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

    if vue == 'jour':
        if classe_id:
            cur.execute("""
                SELECT e.*, c.nom AS classe_nom, u.username AS prof_nom, pa.id AS prof_absent
                FROM emplois_du_temps e
                JOIN classes c ON e.classe_id = c.id
                LEFT JOIN users u ON e.professeur_id = u.id
                LEFT JOIN professeur_absences pa ON pa.professeur_id = e.professeur_id AND pa.date_absence = e.date_cours
                WHERE e.date_cours = %s AND e.classe_id = %s AND e.professeur_id = %s
                ORDER BY e.heure_debut
            """, (jour_selectionne, classe_id, prof_id))
        else:
            cur.execute("""
                SELECT e.*, c.nom AS classe_nom, u.username AS prof_nom, pa.id AS prof_absent
                FROM emplois_du_temps e
                JOIN classes c ON e.classe_id = c.id
                LEFT JOIN users u ON e.professeur_id = u.id
                LEFT JOIN professeur_absences pa ON pa.professeur_id = e.professeur_id AND pa.date_absence = e.date_cours
                WHERE e.date_cours = %s AND e.professeur_id = %s
                ORDER BY e.heure_debut
            """, (jour_selectionne, prof_id))
    else:
        if classe_id:
            cur.execute("""
                SELECT e.*, c.nom AS classe_nom, u.username AS prof_nom, pa.id AS prof_absent
                FROM emplois_du_temps e
                JOIN classes c ON e.classe_id = c.id
                LEFT JOIN users u ON e.professeur_id = u.id
                LEFT JOIN professeur_absences pa ON pa.professeur_id = e.professeur_id AND pa.date_absence = e.date_cours
                WHERE e.date_cours BETWEEN %s AND %s AND e.classe_id = %s AND e.professeur_id = %s
                ORDER BY e.date_cours, e.heure_debut
            """, (lundi, dimanche, classe_id, prof_id))
        else:
            cur.execute("""
                SELECT e.*, c.nom AS classe_nom, u.username AS prof_nom, pa.id AS prof_absent
                FROM emplois_du_temps e
                JOIN classes c ON e.classe_id = c.id
                LEFT JOIN users u ON e.professeur_id = u.id
                LEFT JOIN professeur_absences pa ON pa.professeur_id = e.professeur_id AND pa.date_absence = e.date_cours
                WHERE e.date_cours BETWEEN %s AND %s AND e.professeur_id = %s
                ORDER BY e.date_cours, e.heure_debut
            """, (lundi, dimanche, prof_id))

    cours_list = cur.fetchall()
    for c in cours_list:
        c['heure_debut'] = td_to_str(c.get('heure_debut'))
        c['heure_fin'] = td_to_str(c.get('heure_fin'))
        c['date_cours_str'] = c['date_cours'].isoformat() if isinstance(c.get('date_cours'), date) else ''

    return render_template('professeur/emploi.html',
                           cours=cours_list,
                           classes=classes,
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


@prof_bp.route('/emploi/ical')
@role_required('professeur')
def emploi_ical():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    # FIXED [VULN-015]: Utiliser current_user.id pour filtrer les cours du professeur connecté
    cur.execute("""
        SELECT e.*, c.nom AS classe_nom, u.username AS prof_nom
        FROM emplois_du_temps e
        JOIN classes c ON e.classe_id = c.id
        LEFT JOIN users u ON e.professeur_id = u.id
        WHERE e.professeur_id = %s AND e.date_cours IS NOT NULL
        ORDER BY e.date_cours, e.heure_debut
    """, (current_user.id,))
    cours_list = cur.fetchall()
    for c in cours_list:
        c['heure_debut'] = td_to_str(c.get('heure_debut'))
        c['heure_fin'] = td_to_str(c.get('heure_fin'))

    ical = build_ical(cours_list)
    return Response(ical, mimetype='text/calendar',
                    headers={'Content-Disposition': 'attachment; filename=planning_prof.ics'})


# ── ÉVALUATIONS ───────────────────────────────────────────────────────────────
@prof_bp.route('/evaluations')
@role_required('professeur')
def evaluations():
    db = get_db()
    cur = db.cursor(dictionary=True)
    # FIXED [VULN-015]: Utiliser current_user.id
    cur.execute("""
        SELECT e.id, e.titre, c.nom as classe
        FROM evaluations e
        JOIN classes c ON e.classe_id = c.id
        WHERE e.professeur_id = %s
    """, (current_user.id,))
    evals = cur.fetchall()
    cur.execute("SELECT * FROM classes")
    classes = cur.fetchall()
    return render_template('professeur/evaluations.html', evaluations=evals, classes=classes)


@prof_bp.route('/evaluations/add', methods=['POST'])
@role_required('professeur')
def add_evaluation():
    titre = request.form['titre']
    classe_id = request.form['classe_id']
    db = get_db()
    cur = db.cursor()
    # FIXED [VULN-015]: Utiliser current_user.id
    cur.execute("INSERT INTO evaluations (titre, classe_id, professeur_id) VALUES (%s, %s, %s)",
                (titre, classe_id, current_user.id))
    db.commit()
    flash('Évaluation créée', 'success')
    return redirect('/professeur/evaluations')


# ── NOTES ─────────────────────────────────────────────────────────────────────
@prof_bp.route('/notes')
@role_required('professeur')
def notes():
    db = get_db()
    cur = db.cursor(dictionary=True)
    # FIXED [VULN-015]: Utiliser current_user.id
    cur.execute("SELECT e.id, e.titre FROM evaluations e WHERE e.professeur_id = %s", (current_user.id,))
    evals = cur.fetchall()
    return render_template('professeur/notes.html', evaluations=evals)


@prof_bp.route('/notes/<int:eval_id>', methods=['GET', 'POST'])
@role_required('professeur')
def saisir_notes(eval_id):
    db = get_db()
    cur = db.cursor(dictionary=True)

    # FIXED: Vérifier que l'évaluation appartient bien au professeur connecté (IDOR protection)
    # FIXED [VULN-015]: Utiliser current_user.id
    cur.execute("SELECT id FROM evaluations WHERE id = %s AND professeur_id = %s", (eval_id, current_user.id))
    if not cur.fetchone():
        flash("Évaluation introuvable ou accès non autorisé.", "danger")
        return redirect('/professeur/notes')

    if request.method == 'POST':
        for key, val in request.form.items():
            if key.startswith('note_'):
                etudiant_id = int(key.split('_')[1])
                cur.execute("""
                    INSERT INTO notes (etudiant_id, evaluation_id, valeur)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE valeur = %s
                """, (etudiant_id, eval_id, val, val))
        db.commit()
        flash('Notes enregistrées', 'success')
        return redirect('/professeur/notes')

    cur.execute("""
        SELECT u.id, u.username FROM users u
        JOIN classe_etudiants ce ON u.id = ce.etudiant_id
        JOIN evaluations e ON ce.classe_id = e.classe_id
        WHERE e.id = %s
    """, (eval_id,))
    etudiants = cur.fetchall()
    cur.execute("SELECT titre FROM evaluations WHERE id = %s", (eval_id,))
    eval_info = cur.fetchone()
    return render_template('professeur/saisir_notes.html', etudiants=etudiants, eval_id=eval_id, eval_info=eval_info)


# ── AGENDA ────────────────────────────────────────────────────────────────────
@prof_bp.route('/agenda')
@role_required('professeur')
def agenda():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM classes ORDER BY nom")
    classes = cur.fetchall()
    classe_id = request.args.get('classe_id', type=int)
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

    if classe_id:
        cur.execute("""
            SELECT a.*, c.nom as classe_nom, u.username as prof_nom
            FROM agenda a
            JOIN classes c ON a.classe_id = c.id
            LEFT JOIN users u ON a.professeur_id = u.id
            WHERE a.date_event BETWEEN %s AND %s AND a.classe_id = %s
            ORDER BY a.date_event
        """, (first_of_month, last_of_month, classe_id))
    else:
        # FIXED [VULN-015]: Utiliser current_user.id
        cur.execute("""
            SELECT a.*, c.nom as classe_nom, u.username as prof_nom
            FROM agenda a
            JOIN classes c ON a.classe_id = c.id
            LEFT JOIN users u ON a.professeur_id = u.id
            WHERE a.date_event BETWEEN %s AND %s AND a.professeur_id = %s
            ORDER BY a.date_event
        """, (first_of_month, last_of_month, current_user.id))

    evenements = cur.fetchall()

    return render_template('professeur/agenda.html',
                           evenements=evenements,
                           classes=classes,
                           first_of_month=first_of_month,
                           last_of_month=last_of_month,
                           prev_mois=prev_mois,
                           next_mois=next_mois,
                           selected_classe=classe_id,
                           today=today)


@prof_bp.route('/agenda/add', methods=['POST'])
@role_required('professeur')
def add_agenda():
    db = get_db()
    cur = db.cursor()
    # FIXED [VULN-015]: Utiliser current_user.id
    cur.execute("""
        INSERT INTO agenda (classe_id, professeur_id, titre, description, date_event, type_event)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        request.form['classe_id'],
        current_user.id,
        request.form['titre'],
        request.form.get('description', ''),
        request.form['date_event'],
        request.form.get('type_event', 'autre'),
    ))
    db.commit()
    flash('Événement ajouté à l\'agenda.', 'success')
    date_ev = date.fromisoformat(request.form['date_event'])
    return redirect(f'/professeur/agenda?mois={date_ev.strftime("%Y-%m")}')


# FIXED [VULN-005]: Convertir en POST pour protection CSRF
@prof_bp.route('/agenda/delete/<int:id>', methods=['POST'])
@role_required('professeur')
def delete_agenda(id):
    db = get_db()
    cur = db.cursor(dictionary=True)
    # FIXED [VULN-015]: Utiliser current_user.id (vérification ownership maintenue)
    cur.execute("SELECT date_event FROM agenda WHERE id = %s AND professeur_id = %s", (id, current_user.id))
    row = cur.fetchone()
    if row:
        db.cursor().execute("DELETE FROM agenda WHERE id = %s", (id,))
        db.commit()
        flash('Événement supprimé.', 'warning')
        mois = row['date_event'].strftime('%Y-%m')
        return redirect(f'/professeur/agenda?mois={mois}')
    flash('Événement introuvable.', 'danger')
    return redirect('/professeur/agenda')


# ── ABSENCES & RETARDS ────────────────────────────────────────────────────────
@prof_bp.route('/absences')
@role_required('professeur')
def absences():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM classes ORDER BY nom")
    classes = cur.fetchall()

    classe_id = request.args.get('classe_id', type=int)
    date_str = request.args.get('date', date.today().isoformat())

    etudiants = []
    absences_list = []
    if classe_id:
        cur.execute("""
            SELECT u.id, u.username FROM users u
            JOIN classe_etudiants ce ON u.id = ce.etudiant_id
            WHERE ce.classe_id = %s ORDER BY u.username
        """, (classe_id,))
        etudiants = cur.fetchall()

        cur.execute("""
            SELECT ab.*, u.username as etudiant_nom
            FROM absences ab
            JOIN users u ON ab.etudiant_id = u.id
            WHERE ab.classe_id = %s
            ORDER BY ab.date_absence DESC, u.username
        """, (classe_id,))
        absences_list = cur.fetchall()

    return render_template('professeur/absences.html',
                           classes=classes,
                           etudiants=etudiants,
                           absences=absences_list,
                           selected_classe=classe_id,
                           selected_date=date_str)


@prof_bp.route('/absences/add', methods=['POST'])
@role_required('professeur')
def add_absence():
    db = get_db()
    cur = db.cursor()
    etudiant_id = request.form['etudiant_id']
    classe_id = request.form['classe_id']
    # FIXED [VULN-015]: Utiliser current_user.id
    cur.execute("""
        INSERT INTO absences (etudiant_id, professeur_id, classe_id, date_absence, type_absence, motif, justifiee)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        etudiant_id,
        current_user.id,
        classe_id,
        request.form['date_absence'],
        request.form.get('type_absence', 'absence'),
        request.form.get('motif', ''),
        1 if request.form.get('justifiee') else 0,
    ))
    db.commit()
    flash('Absence/retard enregistré.', 'success')
    return redirect(f'/professeur/absences?classe_id={classe_id}')


# FIXED [VULN-005]: Convertir en POST pour protection CSRF
@prof_bp.route('/absences/toggle/<int:id>', methods=['POST'])
@role_required('professeur')
def toggle_justification(id):
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT justifiee, classe_id FROM absences WHERE id = %s", (id,))
    row = cur.fetchone()
    if row:
        new_val = 0 if row['justifiee'] else 1
        db.cursor().execute("UPDATE absences SET justifiee = %s WHERE id = %s", (new_val, id))
        db.commit()
        flash('Justification mise à jour.', 'success')
        return redirect(f'/professeur/absences?classe_id={row["classe_id"]}')
    flash('Introuvable.', 'danger')
    return redirect('/professeur/absences')


# FIXED [VULN-005]: Convertir en POST pour protection CSRF
@prof_bp.route('/absences/delete/<int:id>', methods=['POST'])
@role_required('professeur')
def delete_absence(id):
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT classe_id FROM absences WHERE id = %s", (id,))
    row = cur.fetchone()
    db.cursor().execute("DELETE FROM absences WHERE id = %s", (id,))
    db.commit()
    flash('Enregistrement supprimé.', 'warning')
    if row:
        return redirect(f'/professeur/absences?classe_id={row["classe_id"]}')
    return redirect('/professeur/absences')