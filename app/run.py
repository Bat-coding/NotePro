from flask import redirect, session, render_template
from app import create_app
import subprocess, sys, os

# Init DB au démarrage
os.system("python /app/init_db.py")

app = create_app()

@app.route('/')
def index():
    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('dashboard.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)