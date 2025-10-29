from flask import Flask, jsonify
import mysql.connector
import numpy as np
import pandas as pd
from joblib import load
import math

# -----------------------
# Config
# -----------------------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "your_mysql_password_here",  # 👈 change this to your actual MySQL password
    "database": "rakth_sathi",
    "raise_on_warnings": True,
}

TREE_FILE = "models/tree_matcher.joblib"
LOGREG_FILE = "models/logreg_matcher.joblib"

# City coords (same as training script)
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
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*(math.sin(dlambda/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def blood_compatible(donor_bg, req_bg):
    compat = {
        'O-': ['O-','O+','A-','A+','B-','B+','AB-','AB+'],
        'O+': ['O+','A+','B+','AB+'],
        'A-': ['A-','A+','AB-','AB+'],
        'A+': ['A+','AB+'],
        'B-': ['B-','B+','AB-','AB+'],
        'B+': ['B+','AB+'],
        'AB-': ['AB-','AB+'],
        'AB+': ['AB+']
    }
    return 1 if req_bg in compat.get(donor_bg, []) else 0

def urgency_score(urg):
    return {'Low':1, 'Medium':2, 'High':3, 'Critical':4}.get(urg, 2)

# -----------------------
# Load models
# -----------------------
tree = load(TREE_FILE)
logreg = load(LOGREG_FILE)

# -----------------------
# Flask app
# -----------------------
app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"msg": "Rakth Sathi API is running"})

@app.route("/match/<int:request_id>", methods=["GET"])
def match_request(request_id):
    conn = mysql.connector.connect(**DB_CONFIG)

    # Fetch request details
    rq = pd.read_sql(f"SELECT * FROM Requests WHERE request_id={request_id}", conn)
    if rq.empty:
        conn.close()
        return jsonify({"error": f"No request found with id {request_id}"}), 404

    rq = rq.iloc[0]
    req_bg, req_city, req_state, urg = rq['blood_group_needed'], rq['city'], rq['state'], rq['urgency']
    req_coords = CITY_COORDS.get(req_city, CITY_COORDS.get(req_state, (0.0,0.0)))
    urg_score = urgency_score(urg)

    # Load donors
    donors = pd.read_sql("SELECT * FROM Donors", conn)
    conn.close()

    # --- Candidate donors ---
    candidates = []
    for _, d in donors.iterrows():
        donor_coords = CITY_COORDS.get(d['city'], CITY_COORDS.get(d['state'], (0.0,0.0)))
        dist = haversine_km(donor_coords[0], donor_coords[1], req_coords[0], req_coords[1])
        days_since = int(d['months_since_first_donation'] or 0) * 30

        blood_match = blood_compatible(d['blood_group'], req_bg)

        feat = [
            blood_match,
            dist,
            urg_score,
            days_since,
            1 if d['availability'] == 'Yes' else 0,
            int(d['number_of_donation'] or 0),
            int(d['pints_donated'] or 0)
        ]
        candidates.append((d, feat, blood_match, dist))

    # --- Score with AI model ---
    Xc = np.array([c[1] for c in candidates])
    try:
        probs_tree = tree.predict_proba(Xc)[:,1]
    except Exception:
        probs_tree = tree.predict(Xc)
    try:
        probs_log = logreg.predict_proba(Xc)[:,1]
    except Exception:
        probs_log = logreg.predict(Xc)
    scores = (np.array(probs_tree) + np.array(probs_log)) / 2.0

    # --- Attach results ---
    ranked = []
    for i, (donor, feat, blood_match, dist) in enumerate(candidates):
        ranked.append({
            "donor_id": int(donor['donor_id']),
            "name": donor['name'],
            "city": donor['city'],
            "state": donor.get('state'),
            "blood_group": donor['blood_group'],
            "availability": donor['availability'],
            "score": float(scores[i]),
            "distance_km": float(dist),
            "blood_match": int(blood_match)
        })

    # Sort: blood match first, then AI score, then closer distance
    ranked = sorted(
        ranked,
        key=lambda x: (x['blood_match'], x['score'], -x['distance_km']),
        reverse=True
    )[:10]

    return jsonify({
        "request_id": int(request_id),
        "blood_group_needed": req_bg,
        "city": req_city,
        "urgency": urg,
        "top_donors": ranked
    })

if __name__ == "__main__":
    app.run(debug=True)
