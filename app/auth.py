from flask import Blueprint, render_template, request, redirect, session, flash
from flask_bcrypt import Bcrypt
from app.models import get_user_by_username

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = get_user_by_username(request.form['username'])
        if user and bcrypt.check_password_hash(user['password_hash'], request.form['password']):
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['username'] = user['username']
            return redirect('/dashboard')
        flash('Identifiants incorrects', 'danger')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect('/login')