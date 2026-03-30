from flask import Blueprint, render_template, request, redirect, flash, session
from app.decorators import role_required
from app.models import get_db

prof_bp = Blueprint('professeur', __name__)

@prof_bp.route('/')
@role_required('professeur')
def index():
    return render_template('professeur/index.html')

# ── ÉVALUATIONS ───────────────────────────────────────
@prof_bp.route('/evaluations')
@role_required('professeur')
def evaluations():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT e.id, e.titre, c.nom as classe
        FROM evaluations e
        JOIN classes c ON e.classe_id = c.id
        WHERE e.professeur_id = %s
    """, (session['user_id'],))
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
    cur.execute("INSERT INTO evaluations (titre, classe_id, professeur_id) VALUES (%s, %s, %s)",
                (titre, classe_id, session['user_id']))
    db.commit()
    flash('Évaluation créée', 'success')
    return redirect('/professeur/evaluations')

# ── EMPLOI DU TEMPS ───────────────────────────────────
@prof_bp.route('/emploi')
@role_required('professeur')
def emploi_du_temps():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT e.jour, e.heure_debut, e.heure_fin, e.matiere, c.nom as classe
        FROM emplois_du_temps e
        JOIN classes c ON e.classe_id = c.id
        WHERE e.professeur_id = %s
        ORDER BY FIELD(e.jour,'Lundi','Mardi','Mercredi','Jeudi','Vendredi'), e.heure_debut
    """, (session['user_id'],))
    emplois = cur.fetchall()
    return render_template('professeur/emploi.html', emplois=emplois)


# ── NOTES ─────────────────────────────────────────────
@prof_bp.route('/notes')
@role_required('professeur')
def notes():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT e.id, e.titre FROM evaluations e
        WHERE e.professeur_id = %s
    """, (session['user_id'],))
    evals = cur.fetchall()
    return render_template('professeur/notes.html', evaluations=evals)

@prof_bp.route('/notes/<int:eval_id>', methods=['GET', 'POST'])
@role_required('professeur')
def saisir_notes(eval_id):
    db = get_db()
    cur = db.cursor(dictionary=True)
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