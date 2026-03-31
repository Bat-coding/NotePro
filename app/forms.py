# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length

class LoginForm(FlaskForm):
    username = StringField('Identifiant', validators=[
        DataRequired(message='Champ obligatoire'),
        Length(min=3, max=80)
    ])
    password = PasswordField('Mot de passe', validators=[
        DataRequired(message='Champ obligatoire')
    ])
    submit = SubmitField('Se connecter')