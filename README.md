# Neosilix — Universal AI Operations Platform

> AI-powered infrastructure monitoring and auto-remediation platform built for real-world DevOps and SRE environments.

**Created by Racheal Sililo** | BSc Computer Science, Mulungushi University

-----

## What is Neosilix?

Neosilix is an intelligent AIOps (AI for IT Operations) platform that monitors live infrastructure in real time, detects anomalies using machine learning, and automatically heals systems before failures escalate — without human intervention.

It combines a Python/Flask backend, a React + TypeScript frontend, Prometheus + Grafana observability stack, and a custom AI Copilot engine trained on live metric data.

-----

## Key Features

### 🧠 AI Copilot Engine

- Uses **Scikit-learn IsolationForest** to learn what “normal” system behaviour looks like
- Detects deviations across CPU, memory, disk I/O, and network metrics in real time
- Runs a warm-up/learning phase before making predictions — no false positives out of the box

### ⚡ Auto-Remediation (Self-Healer)

- When a real anomaly is confirmed, the system automatically triggers a heal action
- Severity thresholds prevent unnecessary interventions (CPU > 95%, memory > 90%, etc.)
- Cooldown logic (10-minute window) prevents heal storms on the same metric

### 🔐 JWT-Authenticated Monitor

- The monitoring engine authenticates via JWT before it is permitted to trigger any actions
- Token auto-refresh with expiry checking
- Exponential backoff on startup failures — production-grade reliability

### 📊 Real-Time Observability Stack

- **Prometheus** scrapes live metrics every 5 seconds using PromQL queries
- **Grafana** dashboards visualise CPU, memory, disk, and network trends
- **Zabbix** for additional infrastructure-level monitoring
- **Node Exporter** for Linux host metrics

### 🖥️ Cyberpunk Operations Dashboard

- React + TypeScript frontend with a real-time terminal-style ops dashboard
- Live service status cards (ONLINE / DEGRADED / OFFLINE)
- Recent alerts feed with auto-remediation logs
- AI Copilot chat interface

### 🐳 Docker-First Deployment

- Full Docker Compose setup for one-command deployment
- Separate monitoring stack (docker-compose.monitoring.yml)
- Shell management scripts for start/stop/status/logs/restart

-----

## Tech Stack

|Layer         |Technology                                |
|--------------|------------------------------------------|
|Backend       |Python, Flask, JWT                        |
|AI / ML       |Scikit-learn (IsolationForest)            |
|Frontend      |React, TypeScript, Vite                   |
|Monitoring    |Prometheus, Grafana, Zabbix, Node Exporter|
|Infrastructure|Docker, Docker Compose, Shell scripts     |
|Protocol      |PromQL, SNMP, Blackbox Exporter           |

-----

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Neosilix Platform                    │
├──────────────┬──────────────────┬───────────────────────┤
│  React UI    │   Flask API      │   AI Copilot Engine   │
│  Dashboard   │   + JWT Auth     │   (IsolationForest)   │
├──────────────┴──────────────────┴───────────────────────┤
│              Prometheus Metrics Layer                    │
│         (CPU / Memory / Disk / Network / SNMP)          │
├─────────────────────────────────────────────────────────┤
│         Grafana + Zabbix Visualisation Layer            │
├─────────────────────────────────────────────────────────┤
│              Docker Compose Infrastructure              │
└─────────────────────────────────────────────────────────┘
```

-----

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.10+
- Node.js 18+

### Quick Start

```bash
# Clone the repository
git clone https://github.com/Racheal-tech-21/Neosilix--Universal-AI-Operation.git
cd Neosilix--Universal-AI-Operation

# Start all services
./manage-neosilix.sh start

# Or using Docker Compose directly
docker-compose up -d
docker-compose -f docker-compose.monitoring.yml up -d
```

### Access URLs

|Service           |URL                    |Credentials                  |
|------------------|-----------------------|-----------------------------|
|Neosilix Dashboard|<http://localhost:5173>|—                            |
|Grafana           |<http://localhost:3002>|admin / neosilix_grafana_2025|
|Prometheus        |<http://localhost:9090>|—                            |
|Zabbix            |<http://localhost:3001>|Admin / zabbix               |
|Node Exporter     |<http://localhost:9100>|—                            |

### Management Commands


## Monitored Metrics

|Metric            |Severity Threshold|
|------------------|------------------|
|CPU Usage         |> 95%             |
|Memory Usage      |> 90%             |
|Disk I/O          |> 85%             |
|Network Throughput|> 100 KB/s        |

-----

## Project Structure

```
neosilix/
├── ai_engine/          # ML anomaly detection & self-healer
├── api/                # Flask REST API
├── ci_cd/              # CI/CD pipeline configs
├── config/             # Environment configurations
├── core/               # Core platform logic
├── dashboard/          # Dashboard components
├── models/             # ML model definitions
├── monitoring/         # Prometheus configs
├── neosilix-frontend/  # React + TypeScript UI
├── neosilix-landing/   # Landing page
├── node_exporter/      # Node exporter setup
├── prometheus/         # Prometheus config
├── copilot_engine.py   # AI Copilot monitor loop
├── copilot_shared.py   # Shared copilot state
├── docker-compose.yml  # Main stack
├── docker-compose.monitoring.yml  # Monitoring stack
└── manage-neosilix.sh  # Platform management script
```

-----

## License

This project is licensed under **CC BY-NC 4.0** — free for personal and academic use.
Commercial use requires explicit permission from the author.

© 2025 Racheal Sililo. All rights reserved.

-----

## Author

**Racheal Sililo**
Founder, Neosilix Universal AI Ops
BSc Computer Science — Mulungushi University, Zambia
GitHub: <https://github.com/Racheal-tech-21>
