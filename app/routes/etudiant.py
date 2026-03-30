from flask import Blueprint, render_template, session
from app.decorators import role_required
from app.models import get_db, get_notes_etudiant

etu_bp = Blueprint('etudiant', __name__)

@etu_bp.route('/notes')
@role_required('etudiant')
def mes_notes():
    notes = get_notes_etudiant(session['user_id'])
    return render_template('etudiant/notes.html', notes=notes)

@etu_bp.route('/emploi')
@role_required('etudiant')
def emploi_du_temps():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT e.jour, e.heure_debut, e.heure_fin, e.matiere, u.username as prof
        FROM emplois_du_temps e
        JOIN classe_etudiants ce ON e.classe_id = ce.classe_id
        LEFT JOIN users u ON e.professeur_id = u.id
        WHERE ce.etudiant_id = %s
        ORDER BY FIELD(e.jour,'Lundi','Mardi','Mercredi','Jeudi','Vendredi'), e.heure_debut
    """, (session['user_id'],))
    emplois = cur.fetchall()
    return render_template('etudiant/emploi.html', emplois=emplois)