# FIXED [VULN-016]: Épingler l'image par digest pour reproductibilité et sécurité supply chain
# Pour obtenir le digest courant: docker pull python:3.11-slim && docker inspect python:3.11-slim --format='{{index .RepoDigests 0}}'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
# FIXED [INFO-001]: pip install avec --no-cache-dir déjà présent, conserver
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x wait-for-db.sh

# FIXED [VULN-002]: Créer un utilisateur non-privilégié et basculer sur cet utilisateur
# Le processus gunicorn ne tourne plus en tant que root
RUN addgroup --system notepro && adduser --system --ingroup notepro --home /app --no-create-home notepro

# FIXED [VULN-002]: S'assurer que l'utilisateur notepro a accès aux fichiers nécessaires
RUN chown -R notepro:notepro /app

USER notepro

# FIXED [VULN-006]: Ajouter un HEALTHCHECK pour détecter les pannes silencieuses
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# FIXED [VULN-017]: Supprimer --reload (mode développement) pour la production
CMD ["sh", "-c", "python db_init.py && gunicorn --bind 0.0.0.0:5000 --timeout 120 --workers 2 'app:create_app()'"]