# api/routes.py
from flask import Blueprint, jsonify
import random
from api.roles import require_role

routes_bp = Blueprint('routes_bp', __name__)

@routes_bp.route('/predict', methods=['POST'])
@require_role(['admin', 'user'])
def predict():
    return jsonify({"result": "Real prediction goes here"})

@routes_bp.route('/dashboard', methods=['GET'])
@require_role(['admin', 'auditor'])
def dashboard():
    return jsonify({"data": "Live dashboard data"})

@routes_bp.route('/admin/metrics', methods=['GET'])
@require_role(['admin'])
def metrics():
    return jsonify({"metrics": "Sensitive performance data"})
@routes_bp.route("/api/cluster/health", methods=["GET"])
def cluster_health():
    nodes = [
        {"name": "Node-1", "status": random.choice(["Healthy", "Degraded", "Unreachable"])},
        {"name": "Node-2", "status": random.choice(["Healthy", "Degraded", "Unreachable"])},
        {"name": "Node-3", "status": random.choice(["Healthy", "Degraded", "Unreachable"])},
    ]
    return jsonify(nodes)
