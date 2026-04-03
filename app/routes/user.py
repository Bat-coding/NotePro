from flask import Blueprint, render_template, request, current_app, redirect, flash
from flask_login import current_user, login_required
from app.models import get_db, db, User
from app import bcrypt
import os
import uuid
import imghdr
import pyotp
import qrcode
import qrcode.image.svg
import base64
from io import BytesIO
import re

user_bp = Blueprint('user', __name__)

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
ALLOWED_IMAGE_MIMETYPES = {'jpeg', 'png', 'gif', 'webp', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def validate_image_content(file_stream):
    header = file_stream.read(512)
    file_stream.seek(0)
    fmt = imghdr.what(None, header)
    return fmt in ALLOWED_IMAGE_MIMETYPES

@user_bp.route('/parametres', methods=['GET', 'POST'])
@login_required
def parametres():
    conn = get_db()
    cur = conn.cursor(dictionary=True)
    user_id = current_user.id

    if request.method == 'POST':
        action = request.form.get('action')

        # Action : Activer 2FA
        if action == 'enable_2fa':
            secret = pyotp.random_base32()
            cur.execute("UPDATE users SET totp_secret = %s WHERE id = %s", (secret, user_id))
            conn.commit()
            flash('Veuillez scanner le QR Code et entrer un code de validation pour activer le 2FA.', 'info')
            return redirect('/user/parametres')

        # Action : Confirmer 2FA
        if action == 'confirm_2fa':
            code = request.form.get('totp_code')
            cur.execute("SELECT totp_secret FROM users WHERE id = %s", (user_id,))
            secret = cur.fetchone()['totp_secret']
            totp = pyotp.TOTP(secret)
            if totp.verify(code):
                cur.execute("UPDATE users SET totp_enabled = TRUE WHERE id = %s", (user_id,))
                conn.commit()
                flash('Le 2FA a été activé avec succès.', 'success')
            else:
                flash("Code invalide, l'activation a échoué.", 'danger')
            return redirect('/user/parametres')

        # Action : Désactiver 2FA
        if action == 'disable_2fa':
            cur.execute("UPDATE users SET totp_enabled = FALSE, totp_secret = NULL WHERE id = %s", (user_id,))
            conn.commit()
            flash('Le 2FA a été désactivé.', 'success')
            return redirect('/user/parametres')

        # Action : Mise à jour Classique
        telephone = request.form.get('telephone', '').replace(' ', '').strip()
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        avatar = request.files.get('avatar')

        cur.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
        current_hash = cur.fetchone()['password_hash']

        queries = []
        params = []

        if telephone:
            if not telephone.isdigit() or len(telephone) != 10:
                flash('Le numéro de téléphone doit contenir exactement 10 chiffres.', 'danger')
                return redirect('/user/parametres')
            queries.append("telephone = %s")
            params.append(telephone)
        elif telephone == "":
            queries.append("telephone = NULL")

        if new_password:
            if len(new_password) < 15 or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", new_password):
                flash("Le nouveau mot de passe doit contenir au moins 15 caractères et un caractère spécial.", 'danger')
                return redirect('/user/parametres')
            if not old_password or not bcrypt.check_password_hash(current_hash, old_password):
                flash("L'ancien mot de passe est incorrect.", 'danger')
                return redirect('/user/parametres')
            queries.append("password_hash = %s")
            params.append(bcrypt.generate_password_hash(new_password).decode('utf-8'))

        if avatar and avatar.filename:
            if not allowed_file(avatar.filename):
                flash('Type de fichier non autorisé.', 'danger')
                return redirect('/user/parametres')
            if not validate_image_content(avatar.stream):
                flash('Le contenu du fichier ne correspond pas à une image valide.', 'danger')
                return redirect('/user/parametres')

            extension = avatar.filename.rsplit('.', 1)[1].lower()
            unique_filename = f"avatar_{user_id}_{uuid.uuid4().hex}.{extension}"
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
            os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
            avatar.save(upload_path)
            queries.append("avatar = %s")
            params.append(unique_filename)

        if queries:
            sql = "UPDATE users SET " + ", ".join(queries) + " WHERE id = %s"
            params.append(user_id)
            cur.execute(sql, tuple(params))
            conn.commit()
            flash('Paramètres mis à jour.', 'success')

        return redirect('/user/parametres')

    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()

    qr_b64 = None
    if user.get('totp_secret') and not user.get('totp_enabled'):
        totp = pyotp.TOTP(user['totp_secret'])
        totp_uri = totp.provisioning_uri(name=user['username'], issuer_name='NotePro')
        img = qrcode.make(totp_uri)
        stream = BytesIO()
        img.save(stream, format="PNG")
        qr_b64 = base64.b64encode(stream.getvalue()).decode('utf-8')

    # Pass everything to template
    return render_template('parametres.html', user=user, qr_b64=qr_b64)
