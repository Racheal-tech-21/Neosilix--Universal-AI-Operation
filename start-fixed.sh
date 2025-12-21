#!/bin/bash
echo "🚀 Starting Neosilix with PostgreSQL 16 - OPTIMIZED VERSION"
echo "==========================================================="

# Run system health check first
echo "🔍 Performing system health check..."
python3 -c "
import psutil
import time

def check_system_health():
    memory = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=1)
    
    print(f'🖥️  System Health Check:')
    print(f'   RAM: {memory.percent}% used ({memory.available / (1024**3):.1f}GB available)')
    print(f'   CPU: {cpu}% used')
    
    if memory.percent > 85:
        print('🚨 WARNING: High memory usage - ML features will be limited')
    else:
        print('✅ System ready for ML operations')

check_system_health()
"

echo "🎯 Starting NeoSilix with 8GB-optimized configuration..."

# Check for port conflicts and resolve them
echo "🔍 Checking for port conflicts..."
if sudo netstat -tulpn | grep -q ":10051 "; then
    echo "⚠️ Port 10051 is in use. Stopping conflicting service..."
    sudo pkill -f ":10051" || true
    sleep 2
fi

# Stop any running services
docker-compose -f docker-compose.monitoring.yml down 2>/dev/null

# Create fresh docker-compose with PostgreSQL 16 optimizations
echo "📁 Creating optimized docker-compose.monitoring.yml..."
cat > docker-compose.monitoring.yml << 'DOCKERCOMPOSE'
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus:/etc/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.enable-lifecycle'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin123
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped

  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    restart: unless-stopped

  zabbix-postgres:
    image: postgres:16
    container_name: zabbix-postgres
    environment:
      - POSTGRES_USER=zabbix
      - POSTGRES_PASSWORD=zabbix_2025
      - POSTGRES_DB=zabbix
      - POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256
      - PGDATA=/var/lib/postgresql/data/pgdata
    volumes:
      - zabbix_postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U zabbix -d zabbix"]
      interval: 15s
      timeout: 10s
      retries: 10
      start_period: 60s

  zabbix-server:
    image: zabbix/zabbix-server-pgsql:alpine-6.4-latest
    container_name: zabbix-server
    ports:
      - "10051:10051"
    environment:
      - DB_SERVER_HOST=zabbix-postgres
      - POSTGRES_USER=zabbix
      - POSTGRES_PASSWORD=zabbix_2025
      - POSTGRES_DB=zabbix
    restart: unless-stopped
    depends_on:
      zabbix-postgres:
        condition: service_healthy

  zabbix-web:
    image: zabbix/zabbix-web-nginx-pgsql:alpine-6.4-latest
    container_name: zabbix-web
    ports:
      - "3001:8080"
    environment:
      - DB_SERVER_HOST=zabbix-postgres
      - POSTGRES_USER=zabbix
      - POSTGRES_PASSWORD=zabbix_2025
      - POSTGRES_DB=zabbix
      - ZBX_SERVER_HOST=zabbix-server
      - PHP_TZ=UTC
    restart: unless-stopped
    depends_on:
      - zabbix-postgres
      - zabbix-server

  zabbix-agent:
    image: zabbix/zabbix-agent2:alpine-6.4-latest
    container_name: zabbix-agent
    ports:
      - "10052:10050"
    environment:
      - ZBX_HOSTNAME=zabbix-server
      - ZBX_SERVER_HOST=zabbix-server
    restart: unless-stopped
    depends_on:
      - zabbix-server

volumes:
  grafana_data:
  zabbix_postgres_data:
DOCKERCOMPOSE

# Create monitoring directory and Prometheus config
mkdir -p monitoring/prometheus
cat > monitoring/prometheus/prometheus.yml << 'PROMETHEUS'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'zabbix-server'
    static_configs:
      - targets: ['zabbix-server:10051']

  - job_name: 'neosilix-api'
    static_configs:
      - targets: ['host.docker.internal:5000']
    metrics_path: /metrics
    scrape_interval: 30s
PROMETHEUS

# Function to pull image with retry
pull_with_retry() {
    local image=$1
    local max_attempts=3
    local attempt=1
    
    echo "📥 Pulling $image..."
    
    while [ $attempt -le $max_attempts ]; do
        if timeout 300 docker pull $image; then
            echo "✅ Successfully pulled $image"
            return 0
        else
            echo "❌ Attempt $attempt failed for $image"
            if [ $attempt -eq $max_attempts ]; then
                echo "💡 Trying alternative approach for $image..."
                return 1
            fi
            echo "🔄 Retrying in 20 seconds..."
            sleep 20
            attempt=$((attempt + 1))
        fi
    done
    return 1
}

# Start with PostgreSQL first (most critical)
echo "🗄️ Starting PostgreSQL 16 (this may take a few minutes)..."
docker-compose -f docker-compose.monitoring.yml up -d zabbix-postgres

# Start other basic services while PostgreSQL initializes
echo "📦 Starting basic monitoring services..."
docker-compose -f docker-compose.monitoring.yml up -d prometheus grafana node-exporter

echo "⏳ Waiting for PostgreSQL 16 to be ready (this can take 2-3 minutes)..."
max_attempts=40  # Increased for PostgreSQL 16
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker ps | grep -q zabbix-postgres && docker exec zabbix-postgres pg_isready -U zabbix -d zabbix > /dev/null 2>&1; then
        echo "✅ PostgreSQL 16 is ready and accepting connections!"
        break
    fi
    echo "Waiting for PostgreSQL 16... ($((attempt+1))/$max_attempts) - This is normal for PostgreSQL 16"
    sleep 10
    attempt=$((attempt+1))
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ PostgreSQL 16 failed to start within expected time"
    echo "💡 Checking container logs..."
    docker logs zabbix-postgres
    echo "⚠️ Continuing with other services - Zabbix may not work properly"
fi

# Try to pull Zabbix images if not already available
echo "🔧 Attempting to download Zabbix images..."
if ! docker images | grep -q "zabbix/zabbix-server-pgsql"; then
    pull_with_retry "zabbix/zabbix-server-pgsql:alpine-6.4-latest" || echo "⚠️ Zabbix server image not available"
fi

if ! docker images | grep -q "zabbix/zabbix-web-nginx-pgsql"; then
    pull_with_retry "zabbix/zabbix-web-nginx-pgsql:alpine-6.4-latest" || echo "⚠️ Zabbix web image not available"
fi

if ! docker images | grep -q "zabbix/zabbix-agent2"; then
    pull_with_retry "zabbix/zabbix-agent2:alpine-6.4-latest" || echo "⚠️ Zabbix agent image not available"
fi

# Start Zabbix services if PostgreSQL is ready and images are available
if docker ps | grep -q zabbix-postgres && docker exec zabbix-postgres pg_isready -U zabbix -d zabbix > /dev/null 2>&1; then
    if docker images | grep -q "zabbix/zabbix-server-pgsql" && docker images | grep -q "zabbix/zabbix-web-nginx-pgsql"; then
        echo "🚀 Starting Zabbix services..."
        docker-compose -f docker-compose.monitoring.yml up -d zabbix-server zabbix-web zabbix-agent
        
        echo "⏳ Waiting for Zabbix to initialize..."
        sleep 60
        
        # Check Zabbix
        echo "🔍 Checking Zabbix..."
        if curl -s http://localhost:3001 > /dev/null; then
            echo "✅ Zabbix is running on port 3001"
        else
            echo "⚠️ Zabbix is not responding on port 3001"
            echo "💡 Checking Zabbix logs..."
            docker logs zabbix-web 2>/dev/null || echo "Zabbix web container not found"
        fi
    else
        echo "⚠️ Zabbix images not available - skipping Zabbix setup"
    fi
else
    echo "⚠️ PostgreSQL not ready or Zabbix images missing - skipping Zabbix setup"
fi

# Check service status
echo "🔍 Final Service Status:"
docker-compose -f docker-compose.monitoring.yml ps

echo ""
echo "📊 Service Overview:"
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Grafana:     http://localhost:3000"
else
    echo "❌ Grafana:     Not responding"
fi

if curl -s http://localhost:9090 > /dev/null; then
    echo "✅ Prometheus:  http://localhost:9090"
else
    echo "❌ Prometheus:  Not responding"
fi

if curl -s http://localhost:3001 > /dev/null; then
    echo "✅ Zabbix:      http://localhost:3001"
else
    echo "❌ Zabbix:      Not available"
fi

# Start Flask app
cd api

# Update app configuration
echo "🔧 Configuring Flask app for Zabbix on 3001..."
python3 -c "
import re
with open('app.py', 'r') as f:
    content = f.read()

# Update Zabbix URL
content = re.sub(r'ZABBIX_URL = \"http://[^\"]+\"', 'ZABBIX_URL = \"http://localhost:3001\"', content)

# Update Zabbix config to use correct API endpoint
content = re.sub(r\"f\\\"\\{ZABBIX_URL\\}/[^\\\"]*\\\"\", \"f\\\"{ZABBIX_URL}/api_jsonrpc.php\\\"\", content)

with open('app.py', 'w') as f:
    f.write(content)
print('✅ Zabbix configuration updated')
"

# Set environment variables
export ZABBIX_URL=http://localhost:3001
export GRAFANA_URL=http://localhost:3000
export PROMETHEUS_URL=http://localhost:9090
export MONITORING_MODE=real

echo ""
echo "🎉 NEOSILIX AI OPS STARTING"
echo "============================"
echo "🌐 Access URLs:"
echo "   Grafana:     http://localhost:3000"
echo "   Prometheus:  http://localhost:9090"
echo "   Zabbix:      http://localhost:3001"
echo "   Neosilix API: http://localhost:5000"
echo ""
echo "🔑 Credentials:"
echo "   Grafana:     admin / admin123"
echo "   Zabbix:      Admin / zabbix"
echo ""
echo "💡 Note: PostgreSQL 16 takes longer to initialize. If Zabbix fails,"
echo "      basic monitoring with Prometheus+Grafana will still work."

python3 app.py
