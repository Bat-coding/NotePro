from functools import wraps
from flask import session, abort

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated
    return decorator