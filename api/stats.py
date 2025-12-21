import os
import psutil
import json
import time
import logging
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(__file__), "../ai_engine/healing_audit.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def get_system_stats():
    """Get REAL system-wide infrastructure stats"""
    try:
        # CPU usage with 1-second interval for accuracy
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = memory.used / (1024**3)  # Convert to GB
        memory_total_gb = memory.total / (1024**3)  # Convert to GB
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_used_gb = disk.used / (1024**3)  # Convert to GB
        disk_total_gb = disk.total / (1024**3)  # Convert to GB
        
        # Network I/O - get current stats
        net_io = psutil.net_io_counters()
        network_recv = net_io.bytes_recv
        network_sent = net_io.bytes_sent
        
        # System uptime
        uptime_seconds = time.time() - psutil.boot_time()
        
        # Load average (Linux/Unix)
        try:
            load_avg = os.getloadavg()[0]  # 1-minute load average
        except:
            load_avg = 0.0
        
        stats = {
            "cpu": cpu_percent,
            "memory": memory_percent,
            "memory_used_gb": round(memory_used_gb, 2),
            "memory_total_gb": round(memory_total_gb, 2),
            "disk": disk_percent,
            "disk_used_gb": round(disk_used_gb, 2),
            "disk_total_gb": round(disk_total_gb, 2),
            "network_recv": network_recv,
            "network_sent": network_sent,
            "uptime": uptime_seconds,
            "load_average": load_avg,
            "timestamp": datetime.now().isoformat()
        }
        
        logging.info(f"Real system stats collected: CPU={cpu_percent}%, Memory={memory_percent}%, Disk={disk_percent}%")
        return stats
        
    except Exception as e:
        logging.error(f"Error collecting system stats: {e}")
        # Return fallback stats if something fails
        return {
            "cpu": 0.0,
            "memory": 0.0,
            "disk": 0.0,
            "network_recv": 0,
            "network_sent": 0,
            "uptime": 0,
            "load_average": 0.0
        }

def get_user_system_stats():
    """Get REAL user's local system stats"""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # Network I/O
        net_io = psutil.net_io_counters()
        network_recv = net_io.bytes_recv
        network_sent = net_io.bytes_sent
        
        # Running processes count
        processes = len(psutil.pids())
        
        # System uptime
        uptime_seconds = time.time() - psutil.boot_time()
        
        # Network usage in MB
        network_usage_mb = (network_recv + network_sent) / (1024 * 1024)
        
        # Additional user-specific metrics
        try:
            # CPU frequencies
            cpu_freq = psutil.cpu_freq()
            cpu_current_ghz = cpu_freq.current / 1000 if cpu_freq else 0
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            disk_read_mb = disk_io.read_bytes / (1024 * 1024) if disk_io else 0
            disk_write_mb = disk_io.write_bytes / (1024 * 1024) if disk_io else 0
            
        except:
            cpu_current_ghz = 0
            disk_read_mb = 0
            disk_write_mb = 0

        stats = {
            "cpu": cpu_percent,
            "memory": memory_percent,
            "disk": disk_percent,
            "network_recv": network_recv,
            "network_sent": network_sent,
            "processes": processes,
            "uptime": uptime_seconds,
            "network_usage": round(network_usage_mb, 2),
            "cpu_frequency_ghz": round(cpu_current_ghz, 2),
            "disk_read_mb": round(disk_read_mb, 2),
            "disk_write_mb": round(disk_write_mb, 2),
            "timestamp": datetime.now().isoformat()
        }
        
        logging.info(f"Real user system stats collected: CPU={cpu_percent}%, Processes={processes}")
        return stats
        
    except Exception as e:
        logging.error(f"Error collecting user system stats: {e}")
        # Return fallback stats if something fails
        return {
            "cpu": 0.0,
            "memory": 0.0,
            "disk": 0.0,
            "network_recv": 0,
            "network_sent": 0,
            "processes": 0,
            "uptime": 0,
            "network_usage": 0.0
        }

