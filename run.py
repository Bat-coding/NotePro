# run.py
from app import create_app
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# FIXED [VULN-003]: Ne jamais afficher DATABASE_URL (contient les credentials) dans les logs
# Ancienne ligne retirée: print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")

app = create_app()

if __name__ == '__main__':
    # FIXED [VULN-003]: debug=False contrôlé par variable d'environnement
    # Ne jamais activer debug=True en production — le débogueur Werkzeug permet l'exécution de code arbitraire
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='127.0.0.1', port=5000, debug=debug_mode)
