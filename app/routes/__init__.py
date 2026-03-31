from flask import Blueprint, redirect, url_for
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin.index'))
    elif current_user.role == 'professeur':
        return redirect(url_for('professeur.index'))
    elif current_user.role == 'etudiant':
        return redirect(url_for('etudiant.index'))
    return redirect(url_for('auth.login'))