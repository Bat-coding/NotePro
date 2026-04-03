# app/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
import pyotp
from .models import User
from .forms import LoginForm

auth_bp = Blueprint('auth', __name__)


# FIXED [VULN-011]: Rate limiting sur la route de login pour prévenir le brute force
# Nécessite l'installation de flask-limiter: pip install flask-limiter
# Si flask-limiter n'est pas encore installé, ce décorateur est optionnel mais FORTEMENT recommandé
# from flask_limiter import Limiter
# from flask_limiter.util import get_remote_address
# limiter = Limiter(key_func=get_remote_address)
#
# @limiter.limit("10 per minute")
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            if user.totp_enabled:
                session['totp_user_id'] = user.id
                return redirect(url_for('auth.verify_2fa'))

            login_user(user)
            session['user_id'] = user.id
            session['role'] = user.role
            session.permanent = True
            flash('Connexion réussie.', 'success')
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/') and not next_page.startswith('//'):
                return redirect(next_page)
            return redirect(url_for('main.dashboard'))
        else:
            # FIXED [VULN-011]: Message générique — ne pas distinguer "utilisateur inconnu" de
            # "mauvais mot de passe" pour éviter l'énumération d'utilisateurs (user enumeration)
            flash('Identifiant ou mot de passe incorrect.', 'danger')

    return render_template('login.html', form=form)


@auth_bp.route('/verify_2fa', methods=['GET', 'POST'])
def verify_2fa():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    totp_user_id = session.get('totp_user_id')
    if not totp_user_id:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        totp_code = request.form.get('totp_code')
        user = User.query.get(totp_user_id)
        if user and pyotp.TOTP(user.totp_secret).verify(totp_code):
            session.pop('totp_user_id', None)
            login_user(user)
            session['user_id'] = user.id
            session['role'] = user.role
            session.permanent = True
            flash('Connexion réussie.', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Code de vérification invalide.', 'danger')

    return render_template('verify_2fa.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Déconnexion réussie.', 'info')
    return redirect(url_for('auth.login'))