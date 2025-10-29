# app.py
import math
import os
from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
import numpy as np
import pandas as pd
from joblib import load
import bcrypt
import jwt
import datetime
from flask import send_file

# Optional: import chatbot helper (create chatbot_helper.py as discussed)
try:
    from chatbot_helper import get_bot_reply
    CHATBOT_AVAILABLE = True
except Exception:
    CHATBOT_AVAILABLE = False

# -----------------------
# Config - database credentials (can be overridden via environment variables)
# -----------------------
DB_CONFIG = {
    "host": os.environ.get('DB_HOST', 'localhost'),
    "user": os.environ.get('DB_USER', 'root'),
    "password": os.environ.get('DB_PASSWORD', 'db_password'),
    "database": os.environ.get('DB_NAME', 'rakth_sathi'),
    "raise_on_warnings": True,
    # If you use MySQL 8+ with caching_sha2_password, you may need auth_plugin. Keep default unless needed.
    "auth_plugin": os.environ.get('DB_AUTH_PLUGIN', 'mysql_native_password')
}

# JWT secret (override with env var in production)
SECRET_KEY = os.environ.get('SECRET_KEY', 'change_this_secret')

TREE_FILE = os.path.join("models", "tree_matcher.joblib")
LOGREG_FILE = os.path.join("models", "logreg_matcher.joblib")

# -----------------------
# City coordinates (for distance calculation)
# keep adding cities/states you need
# -----------------------
CITY_COORDS = {
    # Andhra Pradesh
    "Visakhapatnam": (17.6868, 83.2185),
    "Vijayawada": (16.5062, 80.6480),
    "Guntur": (16.3067, 80.4365),
    "Nellore": (14.4426, 79.9865),
    "Kurnool": (15.8281, 78.0373),
    "Tirupati": (13.6288, 79.4192),
    "Rajahmundry": (16.9891, 81.7898),
    "Kadapa": (14.4674, 78.8242),
    "Anantapur": (14.6816, 77.6000),
    "Ongole": (15.5057, 80.0499),
    # Telangana
    "Hyderabad": (17.3850, 78.4867),
    "Warangal": (17.9689, 79.5941),
    "Nizamabad": (18.6727, 78.0941),
    "Khammam": (17.2473, 80.1514),
    "Karimnagar": (18.4386, 79.1281),
    "Mahbubnagar": (16.7428, 77.9874),
    "Adilabad": (19.6640, 78.5316),
    "Nalgonda": (17.0540, 79.2670),
    "Suryapet": (17.1450, 79.6126),
    "Ramagundam": (18.8060, 79.4526),
}

# -----------------------
# Utils
# -----------------------
def haversine_km(lat1, lon1, lat2, lon2):
    """Return distance in km between two lat/lon points (haversine)."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def blood_compatible(donor_bg, req_bg):
    compat = {
        'O-': ['O-', 'O+', 'A-', 'A+', 'B-', 'B+', 'AB-', 'AB+'],
        'O+': ['O+', 'A+', 'B+', 'AB+'],
        'A-': ['A-', 'A+', 'AB-', 'AB+'],
        'A+': ['A+', 'AB+'],
        'B-': ['B-', 'B+', 'AB-', 'AB+'],
        'B+': ['B+', 'AB+'],
        'AB-': ['AB-', 'AB+'],
        'AB+': ['AB+']
    }
    return 1 if req_bg in compat.get(donor_bg, []) else 0

def urgency_score(urg):
    return {'Low': 1, 'Medium': 2, 'High': 3, 'Critical': 4}.get(urg, 2)

def safe_connect():
    """Create and return a new DB connection. Caller must close()."""
    return mysql.connector.connect(**DB_CONFIG)

# -----------------------
# Load models (if present)
# -----------------------
tree, logreg = None, None
try:
    if os.path.exists(TREE_FILE):
        tree = load(TREE_FILE)
    if os.path.exists(LOGREG_FILE):
        logreg = load(LOGREG_FILE)
except Exception as e:
    print(f"⚠️ Error loading models: {e}")
    tree, logreg = None, None

# -----------------------
# Flask app
# -----------------------
app = Flask(__name__)
CORS(app)  # allow cross origin for mobile app testing

@app.route("/")
def home():
    return jsonify({"msg": "Rakth Sathi API is running", "chatbot_available": CHATBOT_AVAILABLE})

# -----------------------
# Chatbot endpointpython 
# -----------------------
@app.route("/chatbot", methods=["POST"])
def chatbot_route():
    if not CHATBOT_AVAILABLE:
        return jsonify({"error": "Chatbot helper is not available on server."}), 500

    data = request.get_json(force=True, silent=True)
    if not data or "message" not in data:
        return jsonify({"error": "Please provide a JSON body with 'message' field."}), 400

    user_msg = data["message"]
    try:
        reply = get_bot_reply(user_msg)
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": f"Chatbot error: {str(e)}"}), 500


# -----------------------
# API endpoints used by the frontend
# -----------------------
@app.route("/api/donor/register", methods=["POST"])
def api_register_donor():
    data = request.get_json(force=True, silent=True) or {}
    # Basic validation
    name = data.get('name') or data.get('full_name') or ''
    email = data.get('email') or ''
    phone = data.get('phone') or ''
    blood_group = data.get('blood_group') or data.get('donor_blood_group') or ''
    city = data.get('city') or ''
    state = data.get('state') or ''
    last_donation_date = data.get('last_donation_date')
    pints_donated = int(data.get('pints_donated') or 0)
    is_active = int(data.get('is_active') or 0)
    availability = data.get('availability') or ''

    try:
        conn = safe_connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO donors (name, email, phone, blood_group, city, state, last_donation_date, pints_donated, availability, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (name, email, phone, blood_group, city, state, last_donation_date, pints_donated, availability, is_active)
        )
        conn.commit()
        donor_id = cursor.lastrowid if hasattr(cursor, 'lastrowid') else None
        cursor.close()
        conn.close()
        return jsonify({"donor_id": donor_id})
    except Exception as e:
        return jsonify({"error": f"Could not register donor: {str(e)}"}), 500


@app.route('/api/auth/register', methods=['POST'])
def api_auth_register():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    name = data.get('name') or ''

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    try:
        # Hash password
        pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        conn = safe_connect()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, password_hash, name) VALUES (%s, %s, %s)",
            (email, pw_hash, name)
        )
        conn.commit()
        user_id = cursor.lastrowid if hasattr(cursor, 'lastrowid') else None
        cursor.close()
        conn.close()
        return jsonify({'user_id': user_id})

    except Exception as e:
        # Duplicate email handling (MySQL IntegrityError will surface here)
        return jsonify({'error': f'Could not create user: {str(e)}'}), 500


@app.route('/api/auth/login', methods=['POST'])
def api_auth_login():
    data = request.get_json(force=True, silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    if not email or not password:
        return jsonify({'error': 'Email and password required.'}), 400

    try:
        conn = safe_connect()
        df = pd.read_sql('SELECT user_id, password_hash, name FROM users WHERE email = %s', conn, params=(email,))
        conn.close()
        if df.empty:
            return jsonify({'error': 'Invalid credentials.'}), 401
        row = df.iloc[0]
        stored_hash = row['password_hash']
        if not bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            return jsonify({'error': 'Invalid credentials.'}), 401

        payload = {
            'user_id': int(row['user_id']),
            'name': row.get('name', ''),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=6)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        return jsonify({'token': token, 'user_id': int(row['user_id']), 'name': row.get('name', '')})

    except Exception as e:
        return jsonify({'error': f'Login error: {str(e)}'}), 500


@app.route('/ui')
def serve_ui():
    # Serve the frontend HTML directly for easy testing
    ui_path = os.path.join(os.path.dirname(__file__), '..', 'front.html', 'fornt.html')
    ui_path = os.path.abspath(ui_path)
    if os.path.exists(ui_path):
        return send_file(ui_path)
    return 'UI not found', 404


@app.route("/api/request/create", methods=["POST"])
def api_create_request():
    data = request.get_json(force=True, silent=True) or {}
    patient_name = data.get('patient_name') or ''
    email = data.get('email') or ''
    phone = data.get('phone') or ''
    blood_group = data.get('blood_group') or data.get('blood_group_needed') or ''
    city = data.get('city') or ''
    urgency = data.get('urgency') or ''
    radius_km = float(data.get('radius_km') or data.get('radius') or 20)

    try:
        conn = safe_connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO requests (patient_name, email, phone, blood_group_needed, city, urgency, radius_km)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (patient_name, email, phone, blood_group, city, urgency, radius_km)
        )
        conn.commit()
        request_id = cursor.lastrowid if hasattr(cursor, 'lastrowid') else None
        cursor.close()
        conn.close()

        # After creating request, run matching logic using existing match_request function
        # match_request expects an int path param; call it directly to compute matches
        # But to keep response consistent, return the new request id and a minimal message
        return jsonify({"request_id": request_id, "message": "Request created. Run match endpoint to fetch matches."})
    except Exception as e:
        return jsonify({"error": f"Could not create request: {str(e)}"}), 500

# -----------------------
# Match endpoint
# -----------------------
@app.route("/match/<int:request_id>", methods=["GET"])
def match_request(request_id):
    """
    Returns top donors for a given request.
    Query params:
      - radius (km): optional, default 50
    """
    radius = float(request.args.get("radius", 50.0))

    # Connect to DB
    conn = None
    try:
        conn = safe_connect()
    except Exception as e:
        return jsonify({"error": f"DB connection failed: {str(e)}"}), 500

    try:
        # Parameterized fetch for the request
        rq = pd.read_sql("SELECT * FROM requests WHERE request_id = %s", conn, params=(request_id,))
        if rq.empty:
            return jsonify({"error": f"No request found with id {request_id}"}), 404

        rq = rq.iloc[0]
        req_bg = rq['blood_group_needed']
        req_city = rq.get('city', None)
        req_state = rq.get('state', None)
        urg = rq.get('urgency', None)
        req_coords = CITY_COORDS.get(req_city) or CITY_COORDS.get(req_state) or (0.0, 0.0)
        urg_score = urgency_score(urg)

        donors = pd.read_sql("SELECT * FROM donors", conn)
        if donors.empty:
            return jsonify({"error": "No donors found"}), 404

        candidates = []
        for _, d in donors.iterrows():
            donor_city = d.get('city', None)
            donor_state = d.get('state', None)
            donor_coords = CITY_COORDS.get(donor_city) or CITY_COORDS.get(donor_state) or (0.0, 0.0)

            dist = haversine_km(donor_coords[0], donor_coords[1], req_coords[0], req_coords[1])

            # months_since_first_donation may be missing or string; try to coerce
            months_since = d.get('months_since_first_donation', 0)
            try:
                months_since = float(months_since)
            except Exception:
                months_since = 0.0
            days_since = int(months_since * 30)

            blood_match = blood_compatible(d.get('blood_group', ''), req_bg)

            feat = [
                blood_match,
                dist,
                urg_score,
                days_since,
                1 if str(d.get('availability', '')).strip().lower() in ("yes", "y", "true") else 0,
                int(d.get('number_of_donation', 0) or 0),
                int(d.get('pints_donated', 0) or 0)
            ]
            candidates.append((d, feat, blood_match, dist))

        # Scoring via models (if available), otherwise simple heuristic
        Xc = np.array([c[1] for c in candidates])
        if tree is not None and logreg is not None:
            try:
                probs_tree = tree.predict_proba(Xc)[:, 1]
            except Exception:
                probs_tree = tree.predict(Xc)
            try:
                probs_log = logreg.predict_proba(Xc)[:, 1]
            except Exception:
                probs_log = logreg.predict(Xc)
            scores = (np.array(probs_tree) + np.array(probs_log)) / 2.0
        else:
            # Simple heuristic if models missing: prefer blood_match, availability, closeness, donation history
            scores = []
            for i, (donor, feat, blood_match, dist) in enumerate(candidates):
                score = (blood_match * 2.0) + (feat[4] * 1.0) + max(0, (100 - dist) / 100) + (feat[5] * 0.1)
                scores.append(score)
            scores = np.array(scores, dtype=float)

        # Build ranked list
        ranked = []
        for i, (donor, feat, blood_match, dist) in enumerate(candidates):
            ranked.append({
                "donor_id": int(donor.get('donor_id', 0)),
                "name": donor.get('name', ''),
                "city": donor.get('city', ''),
                "state": donor.get('state', ''),
                "blood_group": donor.get('blood_group', ''),
                "availability": donor.get('availability', ''),
                "score": float(scores[i]),
                "distance_km": float(dist),
                "blood_match": int(blood_match)
            })

        # Filter by radius
        nearby = [d for d in ranked if d["distance_km"] <= radius]
        candidate_pool = nearby if nearby else ranked

        # Sort by blood_match first, then score
        final_list = sorted(
            candidate_pool,
            key=lambda x: (x['blood_match'], x['score']),
            reverse=True
        )[:10]

        # Save matches to DB (avoid duplicates)
        try:
            cursor = conn.cursor()
            for donor in final_list:
                # Check if match already exists
                cursor.execute(
                    "SELECT COUNT(1) FROM matches WHERE request_id = %s AND donor_id = %s",
                    (request_id, donor["donor_id"])
                )
                exists = cursor.fetchone()[0] > 0
                if not exists:
                    cursor.execute(
                        "INSERT INTO matches (request_id, donor_id, match_score) VALUES (%s, %s, %s)",
                        (request_id, donor["donor_id"], donor["score"])
                    )
            conn.commit()
            cursor.close()
        except Exception as e:
            # do not fail the whole request if saving matches fails; log and continue
            print(f"⚠️ Could not save matches to DB: {e}")

        return jsonify({
            "request_id": int(request_id),
            "blood_group_needed": req_bg,
            "city": req_city,
            "urgency": urg,
            "radius_used_km": radius,
            "top_donors": final_list
        })

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

# -----------------------
# Fetch matches for a request
# -----------------------
@app.route("/matches/request/<int:request_id>", methods=["GET"])
def get_matches_for_request(request_id):
    try:
        conn = safe_connect()
    except Exception as e:
        return jsonify({"error": f"DB connection failed: {str(e)}"}), 500

    try:
        df = pd.read_sql("SELECT * FROM matches WHERE request_id = %s", conn, params=(request_id,))
        if df.empty:
            return jsonify({"error": f"No matches found for request {request_id}"}), 404
        return df.to_json(orient="records")
    except Exception as e:
        return jsonify({"error": f"Error reading matches: {str(e)}"}), 500
    finally:
        conn.close()

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    # debug=True for local dev; set to False in production
    app.run(host="0.0.0.0", port=5000, debug=True)
