import os
from flask_cors import cross_origin
import bcrypt
import jwt
import psycopg2
import psycopg2.extras
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# JWT config
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkey")
JWT_ALGORITHM = "HS256"

# PostgreSQL connection
conn = psycopg2.connect(
    dbname="neosilix",
    user="neosilix_rw",
    password="november212004",
    host="localhost",
    port=5432,
)
conn.autocommit = True

def get_cursor():
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ----------------- Tables -----------------
with get_cursor() as cur:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password BYTEA NOT NULL,
            role TEXT DEFAULT 'user',
            plan TEXT DEFAULT 'trial',
            trial_ends TIMESTAMP,
            is_admin BOOLEAN DEFAULT FALSE,
            other_field TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS websites (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            url TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS metrics (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            website TEXT,
            metric_name TEXT,
            metric_value DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

# ----------------- Auth Helpers -----------------
def encode_jwt(user_id, is_admin=False):
    payload = {
        "id": user_id,
        "is_admin": is_admin,
        "exp": datetime.utcnow() + timedelta(hours=12)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)  # Use JWT_SECRET here too

def decode_jwt(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return "Token expired"
    except jwt.InvalidTokenError:
        return "Invalid token"

def auth_required(f):
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "No token"}), 401
        token = auth_header.split(" ")[1]
        decoded = decode_jwt(token)
        if not decoded:
            return jsonify({"error": "Invalid or expired token"}), 401
        request.user_id = decoded["id"]
        request.is_admin = decoded.get("is_admin", False)
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

def admin_required(f):
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "No token"}), 401
        token = auth_header.split(" ")[1]
        decoded = decode_jwt(token)
        if not decoded or not decoded.get("is_admin", False):
            return jsonify({"error": "Admin privileges required"}), 403
        request.user_id = decoded["id"]
        request.is_admin = True
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# ----------------- Routes -----------------
@auth_bp.route("/signup", methods=["POST"])
def signup():
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        role = data.get("role", "user")  # default to 'user'

        if not email or not password:
            return jsonify({"error": "Missing email or password"}), 400

        # Prevent creating another admin
        if role == "admin":
            return jsonify({"error": "Cannot create admin account"}), 403

        with get_cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            if cur.fetchone():
                return jsonify({"error": "Email already registered"}), 400

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())  # store bytes
        trial_end = datetime.utcnow() + timedelta(days=7)
        plan = "trial"

        with get_cursor() as cur:
            cur.execute("""
                INSERT INTO users (email, password, role, plan, trial_ends)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, email, role, plan, trial_ends
            """, (email, hashed, role, plan, trial_end))
            user = cur.fetchone()

        token = encode_jwt(user["id"], is_admin=False)
        return jsonify({"token": token, "user": user})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/login", methods=["POST"])
@cross_origin(supports_credentials=True)
def login():
    try:
        data = request.get_json(silent=True) or {}
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"error": "Missing email or password"}), 400

        with get_cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email=%s", (email,))
            user = cur.fetchone()

        if not user:
            return jsonify({"error": "User not found"}), 400

        stored_hash = bytes(user["password"])
        if not bcrypt.checkpw(password.encode(), stored_hash):
            return jsonify({"error": "Wrong password"}), 400

        role = (user.get("role") or "user").lower()
        is_admin = bool(user.get("is_admin") or role == "admin")

        # IMPORTANT: Don't check trial for admin users
        trial_ends = user.get("trial_ends")
        if not is_admin and trial_ends and datetime.utcnow() > trial_ends:
            return jsonify({"error": "Trial expired, please upgrade"}), 403

        # Use encode_jwt so payload has {"id", "is_admin"}
        token = encode_jwt(user["id"], is_admin=is_admin)

        return jsonify({
            "token": token,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "role": role,
                "plan": user.get("plan") or "trial",
                "trial_ends": user.get("trial_ends"),
                "is_admin": is_admin,
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Alias for backward compatibility
decode_auth_token = decode_jwt
