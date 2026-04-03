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
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
