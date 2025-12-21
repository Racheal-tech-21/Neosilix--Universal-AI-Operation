import os
import json
import time
import logging
import psutil
import requests
import smtplib
import threading
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
from flask import Blueprint, jsonify
import psycopg2
from api.stats import get_system_stats

stats_bp = Blueprint("stats", __name__)

@stats_bp.route("/api/stats", methods=["GET"])
def stats():
    return jsonify(get_system_stats())

# === Logging setup ===
LOG_FILE = os.path.join(os.path.dirname(__file__), "healing_audit.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

METRICS_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "metrics_history.json")
HISTORY_LIMIT = 20

# === Prometheus config ===
PROMETHEUS_URL = "http://localhost:9090/api/v1/query"

# === Cooldown tracker ===
last_healed = {"cpu": 0, "memory": 0, "disk": 0, "network": 0, "website": 0}
COOLDOWN_PERIOD = 600  # 10 minutes

# === Email alert config ===
EMAIL_FROM = "Rachealsililo11@gmail.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "Rachealsililo11@gmail.com"
SMTP_PASSWORD = "jgks jewk bbbq ukam"

# === CPU HEALER INTEGRATION ===
def diagnose_cpu_stress():
    """Comprehensive CPU stress diagnosis"""
    try:
        # Get detailed CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_percent_per_core = psutil.cpu_percent(interval=1, percpu=True)
        load_avg = os.getloadavg()[0] if hasattr(os, 'getloadavg') else 0
        
        # Identify top CPU-consuming processes
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage
        top_processes = sorted(processes, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:10]
        
        return {
            'cpu_total': cpu_percent,
            'cpu_per_core': cpu_percent_per_core,
            'load_average': load_avg,
            'top_processes': top_processes,
            'core_count': psutil.cpu_count(),
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {'error': str(e)}

def safe_cpu_healing_strategy(cpu_diagnosis):
    """Intelligent CPU healing with multiple safe strategies"""
    
    healing_actions = []
    cpu_percent = cpu_diagnosis.get('cpu_total', 0)
    top_processes = cpu_diagnosis.get('top_processes', [])
    
    # Strategy 1: Identify and manage resource-intensive processes
    problematic_processes = []
    for proc in top_processes:
        if proc['cpu_percent'] and proc['cpu_percent'] > 30:  # High CPU threshold
            problematic_processes.append({
                'pid': proc['pid'],
                'name': proc['name'],
                'cpu_usage': proc['cpu_percent'],
                'action': 'monitor'
            })
    
    # Strategy 2: Adjust process priorities (safer than killing)
    for proc_info in problematic_processes[:3]:  # Limit to top 3
        try:
            process = psutil.Process(proc_info['pid'])
            current_nice = process.nice()
            
            # Only lower priority if it's not already low
            if current_nice < 10:  # 10 is lower priority (nicer)
                new_nice = min(current_nice + 5, 19)  # Increase nice value (lower priority)
                process.nice(new_nice)
                
                healing_actions.append({
                    'action': 'adjust_priority',
                    'pid': proc_info['pid'],
                    'process_name': proc_info['name'],
                    'old_priority': current_nice,
                    'new_priority': new_nice,
                    'impact': 'low'
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    # Strategy 3: Clear disk caches (if high I/O wait)
    if cpu_percent > 85:
        try:
            # Clear page cache, dentries, and inodes
            if os.name != 'nt':  # Linux/Unix only
                os.system('sync && echo 3 > /proc/sys/vm/drop_caches')
                healing_actions.append({
                    'action': 'clear_caches',
                    'impact': 'medium',
                    'details': 'Cleared disk caches to reduce I/O pressure'
                })
        except:
            pass
    
    # Strategy 4: Suggest system-level optimizations
    if cpu_percent > 90:
        healing_actions.append({
            'action': 'recommendation',
            'type': 'system_optimization',
            'suggestions': [
                'Consider adding more CPU cores',
                'Optimize application code',
                'Distribute load across multiple servers',
                'Implement rate limiting'
            ]
        })
    
    return healing_actions

def intelligent_cpu_healer(cpu_threshold=80):
    """Main auto-heal function for CPU stress"""
    
    # Step 1: Comprehensive diagnosis
    diagnosis = diagnose_cpu_stress()
    cpu_percent = diagnosis.get('cpu_total', 0)
    
    healing_report = {
        'timestamp': datetime.now().isoformat(),
        'cpu_percent': cpu_percent,
        'threshold': cpu_threshold,
        'needs_healing': cpu_percent > cpu_threshold,
        'diagnosis': diagnosis,
        'actions_taken': [],
        'warnings': []
    }
    
    # Only proceed if CPU is above threshold
    if not healing_report['needs_healing']:
        healing_report['status'] = 'normal'
        return healing_report
    
    # Step 2: Apply safe healing strategies
    try:
        healing_actions = safe_cpu_healing_strategy(diagnosis)
        healing_report['actions_taken'] = healing_actions
        
        # Step 3: Monitor effectiveness
        time.sleep(2)  # Wait to see impact
        post_heal_cpu = psutil.cpu_percent(interval=1)
        healing_report['post_heal_cpu'] = post_heal_cpu
        healing_report['improvement'] = cpu_percent - post_heal_cpu
        
        if healing_report['improvement'] > 5:  # Significant improvement
            healing_report['status'] = 'success'
        else:
            healing_report['status'] = 'partial_success'
            healing_report['warnings'].append('Limited improvement - consider manual intervention')
            
    except Exception as e:
        healing_report['status'] = 'error'
        healing_report['error'] = str(e)
        healing_report['warnings'].append('Healing process encountered errors')
    
    return healing_report

def start_cpu_auto_heal_monitor(interval=30, cpu_threshold=80):
    """Background monitor for CPU auto-healing"""
    
    def monitor_loop():
        while True:
            try:
                # Check current CPU
                current_cpu = psutil.cpu_percent(interval=1)
                
                if current_cpu > cpu_threshold:
                    print(f"🚨 High CPU detected: {current_cpu}% - Starting auto-heal...")
                    
                    # Trigger healing
                    heal_report = intelligent_cpu_healer(cpu_threshold)
                    
                    # Log results
                    print(f"🔧 Auto-heal completed: {heal_report['status']}")
                    print(f"📊 Improvement: {heal_report.get('improvement', 0):.1f}%")
                    
                    if heal_report['actions_taken']:
                        for action in heal_report['actions_taken']:
                            print(f"   ✅ {action['action']}: {action.get('process_name', 'system')}")
                
                time.sleep(interval)
                
            except Exception as e:
                print(f"❌ CPU monitor error: {e}")
                time.sleep(interval)
    
    # Start monitoring in background thread
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()
    print(f"🔍 CPU Auto-Heal Monitor started (threshold: {cpu_threshold}%, interval: {interval}s)")
    return monitor_thread

def heal_cpu_anomaly_safe(anomaly_data=None):
    """Safe CPU healing integrated with existing system"""
    try:
        heal_report = intelligent_cpu_healer(cpu_threshold=80)
        
        # Log the healing action
        log_heal_event("cpu_safe", heal_report['cpu_percent'], 
                      f"Safe healing: {heal_report['status']}", 
                      None, None)
        
        return {
            'success': heal_report['status'] in ['success', 'partial_success'],
            'action': 'cpu_optimization_safe',
            'details': heal_report,
            'message': f"CPU safe auto-heal completed: {heal_report['status']}"
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'action': 'cpu_optimization_safe'
        }

# === Helpers ===
def get_user_info(user_id):
    try:
        conn = psycopg2.connect(
            dbname="neosilix",
            user="neosilix_rw",
            password="November212004",
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()
        cur.execute('SELECT email, role, is_admin FROM users WHERE id=%s', [user_id])
        result = cur.fetchone()
        cur.close()
        conn.close()
        if result:
            return {"email": result[0], "role": result[1], "is_admin": result[2]}
        return None
    except Exception as e:
        logging.error(f"Failed to fetch info for user {user_id}: {e}")
        return None

def log_heal_event(metric, value, action_taken, user_id=None, website=None):
    message = f"Healed [{metric.upper()}] anomaly. Value: {value}. Action: {action_taken}"
    if user_id:
        message += f" User ID: {user_id}"
    if website:
        message += f" Website: {website}"
    logging.info(message)
    print(message)
    send_email_alert(metric, value, action_taken, user_id, website)

def cooldown_passed(metric_name):
    return (time.time() - last_healed.get(metric_name, 0)) > COOLDOWN_PERIOD

def load_metrics_history():
    if os.path.exists(METRICS_HISTORY_FILE):
        with open(METRICS_HISTORY_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_metrics_history(entry):
    history = load_metrics_history()
    history.append(entry)
    if len(history) > HISTORY_LIMIT:
        history = history[-HISTORY_LIMIT:]
    with open(METRICS_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def fetch_metric(metric_name, query):
    try:
        r = requests.get(PROMETHEUS_URL, params={"query": query})
        r.raise_for_status()
        results = r.json().get("data", {}).get("result", [])
        if not results:
            return 0.0
        return float(results[0]['value'][1])
    except Exception as e:
        print(f"[ERROR] Prometheus fetch failed: {e}")
        history = load_metrics_history()
        past_entries = [m for m in history if m.get("metric_name") == metric_name]
        if past_entries:
            return past_entries[-1]["value"]
        return 0.0

def dynamic_threshold(metric):
    history = load_metrics_history()
    default_thresholds = {"cpu": 80, "memory": 80, "disk": 90, "network": 1e9, "website": 0}
    if not history:
        return default_thresholds[metric]
    values = [m.get("value", 0.0) for m in history if m.get("metric_name") == metric]
    values.sort()
    if not values:
        return default_thresholds[metric]
    index = max(int(len(values) * 0.95) - 1, 0)
    return max(values[index], default_thresholds[metric])

# === Email sending ===
def send_email_alert(metric, value, action_taken, user_id=None, website=None):
    user_info = get_user_info(user_id) if user_id else None
    if user_info:
        EMAIL_TO = user_info["email"]
    else:
        logging.warning(f"No email for user {user_id}, skipping alert")
        return

    subject = f"[ALERT] Healed {metric.upper()} anomaly - {value:.2f}"
    body = f"Automated system healing notification.\n\nMetric: {metric.upper()}\nValue: {value:.2f}\nAction: {action_taken}\n"
    if website:
        body += f"Website: {website}\n"
    if user_id:
        body += f"User ID: {user_id}\n"

    # Full system snapshot for everyone
    snapshot_cpu = fetch_metric('cpu', '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)')
    snapshot_memory = fetch_metric('memory', '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100')
    snapshot_disk = fetch_metric('disk', '(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100')
    net_io = psutil.net_io_counters()
    snapshot_network = (net_io.bytes_recv + net_io.bytes_sent) / 1024 / 1024  # MB

    body += f"\nSystem Snapshot at Heal:\n- CPU Usage: {snapshot_cpu:.2f}%\n- Memory Usage: {snapshot_memory:.2f}%\n- Disk Usage: {snapshot_disk:.2f}%\n- Network I/O: {snapshot_network:.2f} MB\n"

    # Add last 5 metrics
    history = load_metrics_history()
    past_entries = [m for m in history if m.get("metric_name") == metric]
    last_values = [m["value"] for m in past_entries[-5:]]
    last_timestamps = [m["timestamp"] for m in past_entries[-5:]]
    body += "\nLast 5 readings:\n"
    for ts, val in zip(last_timestamps, last_values):
        body += f"- {ts}: {val:.2f}\n"

    body += f"\nTimestamp: {datetime.now(timezone.utc).isoformat()}\nAlert ID: {int(time.time())}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        logging.info(f"Sent email alert for {metric} to {EMAIL_TO}")
    except Exception as e:
        logging.error(f"Failed to send email to {EMAIL_TO}: {e}")

# === Healing logic ===
def heal_anomaly(metric_name, value, timestamp, user_id=None, website=None):
    if not cooldown_passed(metric_name):
        return

    # NEW: Use safe CPU healing instead of killing processes
    if metric_name == "cpu":
        # Try safe healing first
        safe_result = heal_cpu_anomaly_safe()
        if safe_result['success']:
            log_heal_event("cpu_safe", value, "Used priority adjustment instead of killing", user_id, website)
            return
        
        # Fallback to original method only if safe healing fails
        processes = sorted(
            [p for p in psutil.process_iter(['pid', 'cpu_percent']) if p.pid > 100],
            key=lambda p: p.info['cpu_percent'], reverse=True
        )
        for proc in processes[:2]:
            if proc.is_running() and proc.username() == psutil.Process().username():
                try:
                    proc.kill()
                    log_heal_event("cpu", value, f"Killed PID {proc.pid}", user_id, website)
                except Exception as e:
                    log_heal_event("cpu", value, f"Failed PID {proc.pid} - {e}", user_id, website)

    elif metric_name == "memory":
        processes = sorted(
            [p for p in psutil.process_iter(['pid', 'memory_percent']) if p.pid > 100],
            key=lambda p: p.info['memory_percent'], reverse=True
        )
        for proc in processes[:2]:
            try:
                proc.kill()
                log_heal_event("memory", value, f"Killed PID {proc.pid}", user_id, website)
            except Exception as e:
                log_heal_event("memory", value, f"Failed PID {proc.pid} - {e}", user_id, website)

    elif metric_name == "disk":
        try:
            os.system("rm -rf /tmp/*")
            log_heal_event("disk", value, "Cleared /tmp", user_id, website)
        except Exception as e:
            log_heal_event("disk", value, f"Failed /tmp clear - {e}", user_id, website)

    elif metric_name == "network":
        try:
            os.system("sudo systemctl restart NetworkManager")
            log_heal_event("network", value, "Restarted NetworkManager", user_id, website)
        except Exception as e:
            log_heal_event("network", value, f"Failed network restart - {e}", user_id, website)

    elif metric_name == "website":
        try:
            os.system("sudo systemctl restart apache2")
            log_heal_event("website", value, "Restarted web service", user_id, website)
        except Exception as e:
            log_heal_event("website", value, f"Failed website restart - {e}", user_id, website)

    last_healed[metric_name] = time.time()
    save_metrics_history({
        "timestamp": timestamp,
        "metric_name": metric_name,
        "value": value,
        "user_id": user_id,
        "website": website
    })

# === WEBSITE MONITORING ===
def check_websites():
    try:
        conn = psycopg2.connect(
            dbname="neosilix",
            user="neosilix_rw",
            password="November212004",
            host="localhost",
            port="5432"
        )
        cursor = conn.cursor()
        time_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
        cursor.execute("""
            SELECT user_id, website, metric_name, metric_value, created_at
            FROM metrics
            WHERE metric_name IN ('latency_ms','status_code')
              AND created_at >= %s
        """, (time_threshold,))
        rows = cursor.fetchall()
        for row in rows:
            user_id, website, metric_name, value, ts = row
            timestamp = ts.isoformat() if isinstance(ts, datetime) else datetime.now(timezone.utc).isoformat()
            if metric_name == 'status_code' and value != 200:
                heal_anomaly("website", value, timestamp, user_id, website)
            elif metric_name == 'latency_ms' and value > 2000:
                heal_anomaly("website", value, timestamp, user_id, website)
        cursor.close()
        conn.close()
    except Exception as e:
        logging.error(f"Website monitoring failed: {e}")

# === Auto-heal loop ===
def auto_heal_loop(interval=60):
    # NEW: Start CPU auto-heal monitor
    #start_cpu_auto_heal_monitor(interval=30, cpu_threshold=80)
    
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(
            dbname="neosilix",
            user="neosilix_rw",
            password="November212004",
            host="localhost",
            port="5432"
        )
        cursor = conn.cursor()
        while True:
            cursor.execute("SELECT id FROM users")
            users = cursor.fetchall()
            for user in users:
                user_id = user[0]
                cursor.execute("SELECT website FROM websites WHERE user_id=%s", (user_id,))
                websites = cursor.fetchall()
                for w in websites:
                    website_url = w[0]
                    metrics = {
                        "cpu": fetch_metric("cpu", '100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)'),
                        "memory": fetch_metric("memory", '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100'),
                        "disk": fetch_metric("disk", '(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100'),
                        "network": fetch_metric("network", 'rate(node_network_receive_bytes_total[1m]) + rate(node_network_transmit_bytes_total[1m])')
                    }
                    timestamp = datetime.now(timezone.utc).isoformat()
                    for metric, value in metrics.items():
                        if value > dynamic_threshold(metric):
                            heal_anomaly(metric, value, timestamp, user_id, website_url)
            time.sleep(interval)
    except Exception as e:
        logging.error(f"Auto-heal loop failed: {e}")
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass

if __name__ == "__main__":
    print("Auto-heal loop started… checking metrics every 10 seconds")
    auto_heal_loop(interval=10)
