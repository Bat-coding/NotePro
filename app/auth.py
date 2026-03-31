# app/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from .models import User
from .forms import LoginForm

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            # Stocker aussi dans session pour les routes qui utilisent session['user_id']
            session['user_id'] = user.id
            session['role'] = user.role
            flash('Connexion réussie.', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Identifiant ou mot de passe incorrect.', 'danger')

    return render_template('login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Déconnexion réussie.', 'info')
    return redirect(url_for('auth.login'))