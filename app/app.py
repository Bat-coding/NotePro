from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>NotePro : Plateforme Académique Sécurisée</h1><p>Environnement prêt !</p>"

if __name__ == '__main__':
    # Rappel : Ne jamais mettre debug=True en production !
    app.run(host='0.0.0.0', port=5000)