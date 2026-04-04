from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
import os


db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
csrf = CSRFProtect()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'


def create_app():
    app = Flask(__name__)

    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        raise RuntimeError(
            "ERREUR DE CONFIGURATION : La variable d'environnement SECRET_KEY est obligatoire. "
            "Générez une clé forte avec: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    app.config['SECRET_KEY'] = secret_key

    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL',
        'mysql+mysqlconnector://notepro:notepro@db/notepro'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') != 'development'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    # Timeout de session à 8 heures
    from datetime import timedelta
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

    # Upload configuration
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'avatars')
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2 Mo max pour l'upload

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # force_https=False en développement (passer True en production avec TLS)
    is_production = os.environ.get('FLASK_ENV', 'production') == 'production'
    csp = {
        'default-src': ["'self'"],
        'script-src': [
            "'self'",
            "https://cdn.jsdelivr.net",
        ],
        'style-src': [
            "'self'",
            "https://cdn.jsdelivr.net",
            "https://fonts.googleapis.com",
            # Nécessaire pour Bootstrap inline styles (à terme, remplacer par hash SRI)
            "'unsafe-inline'",
        ],
        'font-src': [
            "'self'",
            "https://fonts.gstatic.com",
            "https://cdn.jsdelivr.net",
        ],
        'img-src': ["'self'", "data:"],
        'connect-src': ["'self'"],
        'frame-ancestors': ["'none'"],
    }
    Talisman(
        app,
        force_https=is_production,
        strict_transport_security=is_production,
        strict_transport_security_max_age=31536000,
        content_security_policy=csp,
        content_security_policy_nonce_in=['script-src'],
        x_content_type_options=True,
        x_xss_protection=True,
        referrer_policy='strict-origin-when-cross-origin',
    )

    from .routes import main_bp
    from .auth import auth_bp
    from .routes.admin import admin_bp
    from .routes.professeur import prof_bp
    from .routes.etudiant import etu_bp
    from .routes.user import user_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(prof_bp, url_prefix='/professeur')
    app.register_blueprint(etu_bp, url_prefix='/etudiant')
    app.register_blueprint(user_bp, url_prefix='/user')

    @app.route('/health')
    def health_check():
        from flask import jsonify
        return jsonify({'status': 'ok'}), 200

    return app
