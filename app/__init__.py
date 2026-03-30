from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
from datetime import timedelta

csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.secret_key = 'changeme_secret'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    csrf.init_app(app)
    Talisman(app, content_security_policy=False)

    from app.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.professeur import prof_bp
    from app.routes.etudiant import etu_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(prof_bp, url_prefix='/professeur')
    app.register_blueprint(etu_bp, url_prefix='/etudiant')

    return app