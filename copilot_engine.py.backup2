# Neosilix U-AIOps — Created by Racheal Sililo
# Original source: https://github.com/Racheal-tech-21/neosilix-uaiops
# License: CC BY-NC 4.0 — Not for commercial use without permission

import os
import time
import requests
from flask import request, jsonify, Blueprint
import jwt
from datetime import datetime, timedelta, timezone
from sklearn.ensemble import IsolationForest
from dotenv import load_dotenv
from copilot_shared import copilot_logs
from ai_engine.self_healer import heal_anomaly

load_dotenv()

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL")
MONITOR_AUTH_URL = os.getenv("MONITOR_AUTH_URL")
MONITOR_USERNAME = os.getenv("MONITOR_AUTH_USERNAME")
MONITOR_PASSWORD = os.getenv("MONITOR_AUTH_PASSWORD")
SECRET_KEY = os.getenv("SECRET_KEY")

METRICS = {
    "cpu": '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)',
    "memory": '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100',
    "disk": 'rate(node_disk_io_time_seconds_total[1m]) * 100',
    "network": 'sum(rate(node_network_receive_bytes_total[1m]) + rate(node_network_transmit_bytes_total[1m])) / 1024'
}

THRESHOLD_HISTORY_SIZE = 20
MIN_HISTORY_FOR_MODEL = 10
COOLDOWN_MINUTES = 10
SEVERITY_THRESHOLDS = {
    "cpu": 95,
    "memory": 90,
    "disk": 85,
    "network": 100
}

last_heal_time = {}
metric_history = {metric: [] for metric in METRICS.keys()}
models = {metric: IsolationForest(contamination=0.1) for metric in METRICS.keys()}


# ----------------- AuthTokenManager for monitor -----------------
class AuthTokenManager:
    def __init__(self, auth_url, username, password, secret_key):
        self.monitor_auth_url = auth_url
        self.monitor_auth_username = username
        self.monitor_auth_password = password
        self.secret_key = secret_key
        self.token = None
        self.expiry = None

    def fetch_token(self):
        try:
            response = requests.post(
                self.monitor_auth_url,
                json={"username": self.monitor_auth_username, "password": self.monitor_auth_password},
                timeout=5
            )
            if response.status_code == 200:
                self.token = response.json().get("token")
                if not self.token:
                    raise Exception("No token received from auth service.")
                decoded_token = jwt.decode(self.token, self.secret_key, algorithms=["HS256"])
                self.expiry = datetime.fromtimestamp(decoded_token.get("exp"), tz=timezone.utc)
            elif response.status_code == 404:
                raise Exception("Auth URL not found (404). Check MONITOR_AUTH_URL in .env")
            else:
                raise Exception(f"Auth failed: {response.status_code} - {response.text}")
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch monitor token: {str(e)}")

    def get_token(self):
        if self.token is None or datetime.now(timezone.utc) > (self.expiry - timedelta(seconds=60)):
            print("⏳ Token expired or missing, fetching new one...")
            self.fetch_token()
        return self.token


# ----------------- Prometheus fetch -----------------
def fetch_metric(metric_name, query):
    try:
        response = requests.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query}, timeout=5)
        response.raise_for_status()
        results = response.json().get("data", {}).get("result", [])
        if not results:
            print(f"[WARN] No data for {metric_name}")
            return None
        return float(results[0]["value"][1])
    except Exception as e:
        print(f"[ERROR] {metric_name}: {e}")
        return None


# ----------------- Anomaly detection -----------------
def detect_anomalies(metric_name, value, auth_token_manager):
    global last_heal_time
    now = datetime.now()
    history = metric_history[metric_name]
    history.append([value])
    if len(history) > THRESHOLD_HISTORY_SIZE:
        history.pop(0)

    if len(history) >= MIN_HISTORY_FOR_MODEL:
        model = models[metric_name]
        model.fit(history)
        prediction = model.predict([[value]])

        if prediction[0] == -1:
            threshold = SEVERITY_THRESHOLDS[metric_name]
            severity_trigger = (value < threshold if metric_name == "network" else value > threshold)

            if not severity_trigger:
                print(f"⚠️ [SKIP] {metric_name.upper()} anomaly NOT severe enough ({value:.2f})")
                return

            last_heal = last_heal_time.get(metric_name)
            if last_heal and (now - last_heal) < timedelta(minutes=COOLDOWN_MINUTES):
                print(f"⏳ Cooldown active for {metric_name.upper()} — Last heal: {last_heal.strftime('%H:%M:%S')}")
                return

            token = auth_token_manager.get_token()
            if token:
                timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
                print(f"🚨 [ANOMALY] {metric_name.upper()} anomaly at {timestamp}: {value:.2f}")
                heal_anomaly(metric_name, value, timestamp)
                copilot_logs.append({
                    "id": len(copilot_logs)+1,
                    "timestamp": timestamp,
                    "metric": metric_name.upper(),
                    "value": value,
                    "action": f"Healed anomaly on {metric_name.upper()}",
                    "status": "Healed"
                })
                last_heal_time[metric_name] = now
            else:
                print("⛔ Unauthorized: Healing aborted due to invalid token.")
        else:
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[OK] {metric_name.capitalize()} = {value:.2f}")
            copilot_logs.append({
                "id": len(copilot_logs)+1,
                "timestamp": timestamp,
                "metric": metric_name.upper(),
                "value": value,
                "action": f"No anomaly detected for {metric_name.upper()}",
                "status": "OK"
            })
    else:
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[LEARNING] {metric_name.capitalize()} = {value:.2f} (warming up)")
        copilot_logs.append({
            "id": len(copilot_logs)+1,
            "timestamp": timestamp,
            "metric": metric_name.upper(),
            "value": value,
            "action": f"Warming up model for {metric_name.upper()}",
            "status": "Learning"
        })


# ----------------- Flask blueprint for monitor token -----------------
monitor_bp = Blueprint('monitor', __name__, url_prefix="/api")

@monitor_bp.route("/token", methods=["POST"])
def get_monitor_token():
    data = request.get_json()
    if data.get("username") != MONITOR_USERNAME or data.get("password") != MONITOR_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    token = jwt.encode(
        {"role": "monitor", "exp": datetime.utcnow() + timedelta(hours=24)},
        SECRET_KEY,
        algorithm="HS256"
    )
    return jsonify({"token": token})
    
# ----------------- Monitor loop -----------------
def monitor_loop():
    """Enhanced monitor loop with proper startup delay and retry logic"""
    print("⏳ Waiting for Flask server to be ready...")
    
    # Wait longer for Flask to be fully ready
    time.sleep(10)
    
    max_retries = 5
    retry_delay = 10  # seconds
    
    auth_token_manager = AuthTokenManager(
        auth_url=MONITOR_AUTH_URL,
        username=MONITOR_USERNAME,
        password=MONITOR_PASSWORD,
        secret_key=SECRET_KEY
    )

    for attempt in range(max_retries):
        try:
            print(f"🔄 Monitor connection attempt {attempt + 1}/{max_retries}...")
            
            # Get authentication token
            auth_token_manager.fetch_token()
            token = auth_token_manager.get_token()
            
            if token:
                print("✅ Monitor authentication successful!")
                break
            else:
                print(f"❌ Monitor auth failed on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    print(f"⏳ Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff
                else:
                    print("❌ All authentication attempts failed. Monitor will not start.")
                    return
        except Exception as e:
            print(f"❌ Monitor auth error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"⏳ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 1.5
            else:
                print("❌ All authentication attempts failed. Monitor will not start.")
                return

    print(" Starting Copilot AI Engine monitor now.")

    # Main monitoring loop
    while True:
        try:
            for metric_name, query in METRICS.items():
                value = fetch_metric(metric_name, query)
                if value is not None:
                    detect_anomalies(metric_name, value, auth_token_manager)
            print("-----")
            time.sleep(5)
        except Exception as e:
            print(f"⚠️ Monitor loop error: {e}")
            time.sleep(10)  # Wait longer on errors
