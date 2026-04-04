FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x wait-for-db.sh

RUN addgroup --system notepro && adduser --system --ingroup notepro --no-create-home notepro

RUN chown -R notepro:notepro /app

USER notepro

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["sh", "-c", "python db_init.py && gunicorn --bind 0.0.0.0:8080 --timeout 120 --workers 2 'app:create_app()'"]