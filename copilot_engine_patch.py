with open('copilot_engine.py', 'r') as f:
    content = f.read()

OLD1 = """last_heal_time = {}
metric_history = {metric: [] for metric in METRICS.keys()}
models = {metric: IsolationForest(contamination=0.1) for metric in METRICS.keys()}"""

NEW1 = """last_heal_time = {}
metric_history = {}
models = {}

def get_target_models(target_id):
    if target_id not in models:
        models[target_id] = {m: IsolationForest(contamination=0.1) for m in METRICS.keys()}
        metric_history[target_id] = {m: [] for m in METRICS.keys()}
    return models[target_id], metric_history[target_id]"""

if OLD1 in content:
    content = content.replace(OLD1, NEW1)
    print("PATCH 1 applied")
else:
    print("PATCH 1 FAILED")

OLD2 = """# ----------------- Prometheus fetch -----------------
def fetch_metric(metric_name, query):"""

NEW2 = """def fetch_target_metric(target, metric_name):
    is_local = target.ip_address in ['localhost', '127.0.0.1', '0.0.0.0']
    try:
        if target.type in ('server', 'vm'):
            if is_local:
                query = METRICS.get(metric_name)
                if not query:
                    return None
                return fetch_metric(metric_name, query)
            else:
                import re
                resp = requests.get(f"http://{target.ip_address}:9100/metrics", timeout=3)
                if resp.status_code != 200:
                    return None
                text = resp.text
                if metric_name == "cpu":
                    idle = re.findall(r'node_cpu_seconds_total\\{[^}]*mode="idle"[^}]*\\}\\s+([\\d.]+)', text)
                    total = re.findall(r'node_cpu_seconds_total\\{[^}]*\\}\\s+([\\d.]+)', text)
                    if idle and total:
                        cpu_idle = sum(float(x) for x in idle)
                        cpu_total = sum(float(x) for x in total)
                        return round((1 - cpu_idle/cpu_total) * 100, 1) if cpu_total else None
                elif metric_name == "memory":
                    avail_m = re.search(r'node_memory_MemAvailable_bytes\\s+([\\d.]+)', text)
                    total_m = re.search(r'node_memory_MemTotal_bytes\\s+([\\d.]+)', text)
                    if avail_m and total_m:
                        avail, total = float(avail_m.group(1)), float(total_m.group(1))
                        return round((1 - avail/total) * 100, 1) if total else None
                return None
        elif target.type == 'container':
            import docker
            client = docker.from_env()
            containers = client.containers.list()
            container_name = target.name.lower().replace(' ', '-')
            matched = None
            for c in containers:
                if container_name in c.name.lower():
                    matched = c
                    break
            if not matched:
                return None
            stats = matched.stats(stream=False)
            if metric_name == "cpu":
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
                sys_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
                num_cpus = stats['cpu_stats'].get('online_cpus', 1)
                return round((cpu_delta / sys_delta) * num_cpus * 100, 1) if sys_delta > 0 else 0
            elif metric_name == "memory":
                mem_usage = stats['memory_stats']['usage']
                mem_limit = stats['memory_stats']['limit']
                return round((mem_usage/mem_limit)*100, 1) if mem_limit else None
            return None
        elif target.type == 'network':
            if metric_name == "network":
                import subprocess, re
                result = subprocess.run(['ping', '-c', '2', target.ip_address], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    times = re.findall(r'time[=<](\\d+\\.?\\d*)', result.stdout)
                    if times:
                        return sum(float(t) for t in times) / len(times)
            return None
    except Exception as e:
        print(f"[ERROR] fetch_target_metric failed for {target.name} ({metric_name}): {e}")
        return None
    return None


# ----------------- Prometheus fetch (local machine) -----------------
def fetch_metric(metric_name, query):"""

if OLD2 in content:
    content = content.replace(OLD2, NEW2)
    print("PATCH 2 applied")
else:
    print("PATCH 2 FAILED")

OLD3 = """# ----------------- Anomaly detection -----------------
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
                heal_anomaly(metric_name, value, timestamp)"""

NEW3 = """def detect_anomalies(metric_name, value, auth_token_manager, target_id=None):
    global last_heal_time
    now = datetime.now()
    heal_key = (target_id, metric_name)

    if target_id is not None:
        target_models, target_history = get_target_models(target_id)
        history = target_history[metric_name]
        model = target_models[metric_name]
    else:
        return

    history.append([value])
    if len(history) > THRESHOLD_HISTORY_SIZE:
        history.pop(0)

    if len(history) >= MIN_HISTORY_FOR_MODEL:
        model.fit(history)
        prediction = model.predict([[value]])

        if prediction[0] == -1:
            threshold = SEVERITY_THRESHOLDS.get(metric_name, 90)
            severity_trigger = (value < threshold if metric_name == "network" else value > threshold)

            if not severity_trigger:
                print(f"⚠️ [SKIP] target={target_id} {metric_name.upper()} anomaly NOT severe enough ({value:.2f})")
                return

            last_heal = last_heal_time.get(heal_key)
            if last_heal and (now - last_heal) < timedelta(minutes=COOLDOWN_MINUTES):
                print(f"⏳ Cooldown active target={target_id} {metric_name.upper()}")
                return

            token = auth_token_manager.get_token()
            if token:
                timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
                print(f"🚨 [ANOMALY] target={target_id} {metric_name.upper()} anomaly at {timestamp}: {value:.2f}")
                heal_anomaly(metric_name, value, timestamp, target_id=target_id)"""

if OLD3 in content:
    content = content.replace(OLD3, NEW3)
    print("PATCH 3 applied")
else:
    print("PATCH 3 FAILED")

OLD5 = """    # Main monitoring loop
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
            time.sleep(10)"""

NEW5 = """    while True:
        try:
            from api.app import app, MonitoringTarget
            with app.app_context():
                targets = MonitoringTarget.query.all()

            if not targets:
                print("[WARN] No monitoring targets configured yet")
            else:
                for target in targets:
                    metrics_to_check = ["cpu", "memory"] if target.type in ("server", "vm", "container") else ["network"]
                    for metric_name in metrics_to_check:
                        value = fetch_target_metric(target, metric_name)
                        if value is not None:
                            print(f"[OK] target={target.name} {metric_name} = {value:.2f}")
                            detect_anomalies(metric_name, value, auth_token_manager, target_id=target.id)
                        else:
                            print(f"[WARN] No data for target={target.name} {metric_name}")
            print("-----")
            time.sleep(10)
        except Exception as e:
            print(f"⚠️ Monitor loop error: {e}")
            time.sleep(10)"""

if OLD5 in content:
    content = content.replace(OLD5, NEW5)
    print("PATCH 5 applied")
else:
    print("PATCH 5 FAILED")

with open('copilot_engine.py', 'w') as f:
    f.write(content)

print("DONE - check above for any FAILED lines")
