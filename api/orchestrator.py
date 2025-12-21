from flask import Blueprint, request, jsonify
from ci_cd.orchestrator_engine import deploy_latest_commit
from api.auth import is_authorized

orchestrator_api = Blueprint("orchestrator_api", __name__)

@orchestrator_api.route("/api/orchestrate/deploy", methods=["POST"])
def deploy():
    token = request.headers.get("Authorization")
    if not is_authorized(token):
        return jsonify({"error": "Unauthorized"}), 401

    repo_path = request.json.get("repo_path", ".")
    result = deploy_latest_commit(repo_path)
    return jsonify(result)
