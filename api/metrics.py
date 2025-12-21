import requests
import psutil
import time
from datetime import datetime
import subprocess
import socket

class RealMonitoringAPI:
    def __init__(self):
        self.prometheus_url = "http://localhost:9090"
        
    def get_system_metrics(self):
        """Get REAL system metrics from multiple sources"""
        try:
            # Local server metrics
            local_metrics = self._get_local_metrics()
            
            # Prometheus metrics from other servers
            prometheus_metrics = self._get_prometheus_metrics()
            
            # Website status
            website_metrics = self._get_website_status()
            
            # Network device status
            network_metrics = self._get_network_status()
            
            return {
                **local_metrics,
                **prometheus_metrics,
                **website_metrics,
                **network_metrics,
                "monitoring_mode": "real",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error getting real metrics: {e}")
            return self._get_fallback_metrics()
    
    def _get_local_metrics(self):
        """Get metrics from local server"""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Network
            net_io = psutil.net_io_counters()
            network_in = net_io.bytes_recv
            network_out = net_io.bytes_sent
            
            # Processes
            processes = len(psutil.pids())
            
            return {
                "cpu_usage": round(cpu_percent, 1),
                "memory_usage": round(memory_percent, 1),
                "disk_usage": round(disk_percent, 1),
                "network_in": network_in,
                "network_out": network_out,
                "processes": processes,
                "server_name": socket.gethostname(),
                "uptime": int(time.time() - psutil.boot_time())
            }
        except Exception as e:
            print(f"Error getting local metrics: {e}")
            return {}
    
    def _get_prometheus_metrics(self):
        """Get metrics from Prometheus for other servers"""
        try:
            # Example: Query for multiple servers
            queries = {
                'total_hosts': 'count(up)',
                'online_hosts': 'count(up == 1)',
                'cpu_avg': 'avg(rate(node_cpu_seconds_total[5m])) * 100',
            }
            
            metrics = {}
            for key, query in queries.items():
                response = requests.get(
                    f"{self.prometheus_url}/api/v1/query",
                    params={'query': query},
                    timeout=5
                )
                if response.status_code == 200:
                    result = response.json().get('data', {}).get('result', [])
                    if result:
                        metrics[key] = float(result[0].get('value', [0, 0])[1])
            
            return metrics
        except Exception as e:
            print(f"Error getting Prometheus metrics: {e}")
            return {}
    
    def _get_website_status(self):
        """Monitor website status"""
        websites = [
            {"name": "Student Portal", "url": "https://student.mulungushi.ac.zm"},
            {"name": "LMS", "url": "https://lms.mulungushi.ac.zm"},
            {"name": "University Website", "url": "https://mulungushi.ac.zm"},
            {"name": "Email", "url": "https://mail.mulungushi.ac.zm"},
        ]
        
        website_status = {}
        for site in websites:
            try:
                start_time = time.time()
                response = requests.get(site["url"], timeout=10)
                response_time = round((time.time() - start_time) * 1000, 2)
                
                website_status[f"{site['name'].lower().replace(' ', '_')}_status"] = "healthy" if response.status_code == 200 else "down"
                website_status[f"{site['name'].lower().replace(' ', '_')}_response_time"] = response_time
                website_status[f"{site['name'].lower().replace(' ', '_')}_status_code"] = response.status_code
                
            except Exception as e:
                website_status[f"{site['name'].lower().replace(' ', '_')}_status"] = "down"
                website_status[f"{site['name'].lower().replace(' ', '_')}_response_time"] = 0
                website_status[f"{site['name'].lower().replace(' ', '_')}_status_code"] = 0
        
        return website_status
    
    def _get_network_status(self):
        """Check network device status"""
        network_devices = [
            {"name": "main_router", "ip": "192.168.1.1"},
            {"name": "core_switch", "ip": "192.168.1.2"},
            {"name": "firewall", "ip": "192.168.1.254"},
        ]
        
        network_status = {
            "total_network_devices": len(network_devices),
            "online_network_devices": 0
        }
        
        for device in network_devices:
            try:
                # Ping the device
                result = subprocess.run(
                    ['ping', '-c', '1', '-W', '1', device["ip"]],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                is_online = result.returncode == 0
                network_status[f"{device['name']}_status"] = "online" if is_online else "offline"
                
                if is_online:
                    network_status["online_network_devices"] += 1
                    
            except Exception:
                network_status[f"{device['name']}_status"] = "offline"
        
        return network_status
    
    def _get_fallback_metrics(self):
        """Fallback if monitoring fails"""
        return {
            "cpu_usage": 0,
            "memory_usage": 0,
            "disk_usage": 0,
            "network_in": 0,
            "network_out": 0,
            "total_hosts": 0,
            "online_hosts": 0,
            "active_alerts": 0,
            "monitoring_mode": "real",
            "error": "Monitoring services unavailable"
        }
