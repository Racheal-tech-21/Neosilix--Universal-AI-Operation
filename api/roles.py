# api/roles.py
from functools import wraps
from flask import request, jsonify
import jwt

SECRET_KEY = 'neosilix_secret_2025'

def require_role(allowed_roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth = request.headers.get('Authorization', None)
            if not auth or not auth.startswith('Bearer '):
                return jsonify({"message": "Token missing"}), 401
            token = auth.split(' ')[1]

            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                if payload["role"] not in allowed_roles:
                    return jsonify({"message": "Access forbidden: insufficient rights"}), 403
            except jwt.ExpiredSignatureError:
                return jsonify({"message": "Token expired"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"message": "Invalid token"}), 401

            return f(*args, **kwargs)
        return wrapper
    return decorator
