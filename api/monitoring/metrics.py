'EOF'
from flask import Blueprint, jsonify
import requests
import os
from typing import Dict, Any

monitoring_bp = Blueprint('monitoring', __name__)

# Configuration
ZABBIX_URL = "http://localhost:3001"
GRAFANA_URL = "http://localhost:3002"
PROMETHEUS_URL = "http://localhost:9090"

class MonitoringAPI:
    def __init__(self):
        self.zabbix_auth = self._authenticate_zabbix()
    
    def _authenticate_zabbix(self):
        """Authenticate with Zabbix API"""
        try:
            response = requests.post(
                f"{ZABBIX_URL}/api_jsonrpc.php",
                json={
                    "jsonrpc": "2.0",
                    "method": "user.login",
                    "params": {
                        "user": "Admin",
                        "password": "zabbix"
                    },
                    "id": 1
                },
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 200:
                return response.json().get('result')
        except Exception as e:
            print(f"Zabbix auth error: {e}")
        return None
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get combined system metrics from all monitoring sources"""
        try:
            # Get basic system metrics from Node Exporter via Prometheus
            prometheus_metrics = self._get_prometheus_metrics()
            
            # Get Zabbix host and alert counts
            zabbix_metrics = self._get_zabbix_metrics()
            
            # Combine metrics
            return {
                "cpu_usage": prometheus_metrics.get('cpu_usage', 0),
                "memory_usage": prometheus_metrics.get('memory_usage', 0),
                "disk_usage": prometheus_metrics.get('disk_usage', 0),
                "network_in": prometheus_metrics.get('network_in', 0),
                "network_out": prometheus_metrics.get('network_out', 0),
                "active_alerts": zabbix_metrics.get('active_alerts', 0),
                "total_hosts": zabbix_metrics.get('total_hosts', 0),
                "online_hosts": zabbix_metrics.get('online_hosts', 0)
            }
        except Exception as e:
            print(f"Error getting system metrics: {e}")
            return {}
    
    def _get_prometheus_metrics(self) -> Dict[str, Any]:
        """Get metrics from Prometheus"""
        try:
            # Example Prometheus queries - adjust based on your metrics
            queries = {
                'cpu_usage': '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
                'memory_usage': '(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100',
                'disk_usage': '(node_filesystem_size_bytes{fstype!="tmpfs"} - node_filesystem_free_bytes{fstype!="tmpfs"}) / node_filesystem_size_bytes{fstype!="tmpfs"} * 100',
                'network_in': 'rate(node_network_receive_bytes_total[5m])',
                'network_out': 'rate(node_network_transmit_bytes_total[5m])'
            }
            
            metrics = {}
            for key, query in queries.items():
                response = requests.get(
                    f"{PROMETHEUS_URL}/api/v1/query",
                    params={'query': query}
                )
                if response.status_code == 200:
                    result = response.json().get('data', {}).get('result', [])
                    if result:
                        metrics[key] = float(result[0].get('value', [0, 0])[1])
            
            return metrics
        except Exception as e:
            print(f"Prometheus error: {e}")
            return {}
    
    def _get_zabbix_metrics(self) -> Dict[str, Any]:
        """Get metrics from Zabbix"""
        if not self.zabbix_auth:
            return {}
        
        try:
            # Get host count
            hosts_response = requests.post(
                f"{ZABBIX_URL}/api_jsonrpc.php",
                json={
                    "jsonrpc": "2.0",
                    "method": "host.get",
                    "params": {
                        "output": ["hostid", "status"],
                        "selectInterfaces": ["ip", "port"]
                    },
                    "auth": self.zabbix_auth,
                    "id": 2
                }
            )
            
            # Get active alerts
            alerts_response = requests.post(
                f"{ZABBIX_URL}/api_jsonrpc.php",
                json={
                    "jsonrpc": "2.0",
                    "method": "trigger.get",
                    "params": {
                        "output": ["triggerid", "description", "priority"],
                        "filter": {"value": 1},
                        "sortfield": "lastchange",
                        "sortorder": "DESC"
                    },
                    "auth": self.zabbix_auth,
                    "id": 3
                }
            )
            
            hosts_data = hosts_response.json().get('result', []) if hosts_response.status_code == 200 else []
            alerts_data = alerts_response.json().get('result', []) if alerts_response.status_code == 200 else []
            
            total_hosts = len(hosts_data)
            online_hosts = len([h for h in hosts_data if h.get('status') == '0'])
            active_alerts = len(alerts_data)
            
            return {
                "total_hosts": total_hosts,
                "online_hosts": online_hosts,
                "active_alerts": active_alerts
            }
        except Exception as e:
            print(f"Zabbix error: {e}")
            return {}

# Create API instance
monitoring_api = MonitoringAPI()

@monitoring_bp.route('/api/monitoring/metrics', methods=['GET'])
def get_metrics():
    """Get combined system metrics"""
    metrics = monitoring_api.get_system_metrics()
    return jsonify(metrics)

@monitoring_bp.route('/api/monitoring/alerts', methods=['GET'])
def get_alerts():
    """Get recent alerts"""
    # Mock data for now - replace with actual Zabbix/Prometheus alerts
    alerts = [
        {
            "id": 1,
            "severity": "Critical",
            "message": "High CPU usage on server-01",
            "timestamp": "2024-01-15T10:30:00Z",
            "host": "server-01"
        },
        {
            "id": 2,
            "severity": "High",
            "message": "Memory usage above threshold",
            "timestamp": "2024-01-15T10:25:00Z",
            "host": "server-02"
        },
        {
            "id": 3,
            "severity": "Medium",
            "message": "Disk space running low",
            "timestamp": "2024-01-15T10:20:00Z",
            "host": "server-03"
        }
    ]
    return jsonify(alerts)

@monitoring_bp.route('/api/monitoring/health', methods=['GET'])
def health_check():
    """Health check for monitoring services"""
    services = {
        "zabbix": False,
        "grafana": False,
        "prometheus": False,
        "node_exporter": False
    }
    
    # Check each service
    try:
        services["zabbix"] = requests.get(f"{ZABBIX_URL}").status_code == 200
    except: pass
    
    try:
        services["grafana"] = requests.get(f"{GRAFANA_URL}").status_code == 200
    except: pass
    
    try:
        services["prometheus"] = requests.get(f"{PROMETHEUS_URL}").status_code == 200
    except: pass
    
    try:
        services["node_exporter"] = requests.get("http://localhost:9100").status_code == 200
    except: pass
    
    return jsonify({
        "status": "healthy" if all(services.values()) else "degraded",
        "services": services,
        "timestamp": "2024-01-15T10:30:00Z"
    })
EOF
