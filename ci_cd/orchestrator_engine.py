import os
import subprocess
import datetime
import json

# ----------------------
# CONFIG
# ----------------------
TEST_MODE = True  # True = local-only, False = multi-cloud deploy
REPO_PATH = "/home/rachealsililo/neosilix-uaiops"  # Your local repo path
DEPLOY_VERSION = "v1.0.0"  # Docker image / version tag

LOG_FILE = "deployment_logs.json"

# ----------------------
# Logging
# ----------------------
def load_logs():
    try:
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_logs(logs):
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=4)

def log_action(logs, action, status, details=""):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logs.append({
        "timestamp": timestamp,
        "metric": "CI/CD",
        "action": action,
        "status": status,
        "details": details
    })
    save_logs(logs)

# ----------------------
# Shell runner
# ----------------------
def run_shell(cmd):
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip(), "SUCCESS"
    except subprocess.CalledProcessError as e:
        return e.stderr.strip(), "FAILED"

# ----------------------
# Docker deployment
# ----------------------
def deploy_docker(repo_path, logs):
    os.chdir(repo_path)

    log_action(logs, "Pulling latest code", "STARTED")
    out, status = run_shell("git pull origin main")
    log_action(logs, "Pulled latest code", status, out)

    log_action(logs, "Building Docker image", "STARTED")
    out, status = run_shell(f"docker build -t neosilix-app:{DEPLOY_VERSION} .")
    log_action(logs, "Docker build", status, out)

    log_action(logs, "Restarting container", "STARTED")
    out, status = run_shell("docker compose down && docker compose up -d")
    log_action(logs, "Docker restart", status, out)

    return status

# ----------------------
# Rollback
# ----------------------
def rollback(repo_path, logs):
    log_action(logs, "Rolling back", "STARTED")
    out, status = run_shell("docker compose down && docker compose up -d")
    log_action(logs, "Rollback completed", status, out)
    print("Rollback completed.")

# ----------------------
# Canary deploy
# ----------------------
def canary_deploy(repo_path, logs):
    print("Starting canary deployment...")
    status = deploy_docker(repo_path, logs)
    if status != "SUCCESS":
        print("Canary failed, rolling back...")
        rollback(repo_path, logs)
        return False
    print("Canary successful.")
    return True

# ----------------------
# Multi-cloud dummy placeholders
# ----------------------
class CloudProviderAWS:
    def __init__(self):
        self.cluster_name = "dummy-cluster"
        self.service_name = "dummy-service"

    def deploy(self, version, canary=False):
        print(f"AWS ECS deploy {version}, canary={canary}")
        return True

    def rollback(self, version):
        print(f"AWS ECS rollback {version}")
        return True

class CloudProviderGCP:
    def __init__(self):
        self.project_id = "dummy-project-id"
        self.location = "us-central1"
        self.service_name = "neosilix-service"

    def deploy(self, version, canary=False):
        print(f"GCP Cloud Run deploy {version}, canary={canary}")
        return True

    def rollback(self, version):
        print(f"GCP Cloud Run rollback {version}")
        return True

class CloudProviderAzure:
    def __init__(self):
        self.subscription_id = "dummy-subscription-id"
        self.resource_group = "dummy-rg"
        self.container_group = "dummy-cg"

    def deploy(self, version, canary=False):
        print(f"Azure Container Instances deploy {version}, canary={canary}")
        return True

    def rollback(self, version):
        print(f"Azure rollback {version}")
        return True

class MultiCloudOrchestrator:
    def __init__(self):
        self.providers = {
            "aws": CloudProviderAWS(),
            "gcp": CloudProviderGCP(),
            "azure": CloudProviderAzure()
        }

    def deploy(self, version, canary=False):
        for name, provider in self.providers.items():
            success = provider.deploy(version, canary=canary)
            print(f"{name} deployment {'success' if success else 'failed'}")
            if not success and not canary:
                provider.rollback(version)

# ----------------------
# MAIN
# ----------------------
if __name__ == "__main__":
    logs = load_logs()

    # Step 1: Canary (local Docker)
    if canary_deploy(REPO_PATH, logs):
        # Step 2: Full local Docker deployment
        deploy_docker(REPO_PATH, logs)

    # Step 3: Multi-cloud deploy (only if TEST_MODE=False)
    if not TEST_MODE:
        mc = MultiCloudOrchestrator()
        mc.deploy(DEPLOY_VERSION, canary=True)
        mc.deploy(DEPLOY_VERSION)
    else:
        print("TEST_MODE ON: Skipping multi-cloud deploy.")
