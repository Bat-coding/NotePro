FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x wait-for-db.sh

CMD ["sh", "-c", "./wait-for-db.sh && gunicorn --bind 0.0.0.0:5000 'app:create_app()'"]