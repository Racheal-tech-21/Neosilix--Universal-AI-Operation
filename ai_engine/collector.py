import psutil
import time
import json
import os
from threading import Thread

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LATEST_METRICS_PATH = os.path.join(BASE_DIR, 'ai_engine', 'metrics.json')
METRICS_HISTORY_PATH = os.path.join(BASE_DIR, 'ai_engine', 'metrics_history.json')

class MetricsCollector(Thread):
    def __init__(self, interval=5):
        super().__init__()
        self.interval = interval
        self.running = True

    def collect_metrics(self):
        net_io = psutil.net_io_counters()
        return {
            'cpu': psutil.cpu_percent(interval=None),
            'memory': psutil.virtual_memory().percent,
            'disk': psutil.disk_usage('/').percent,
            'network_recv': net_io.bytes_recv,
            'network_sent': net_io.bytes_sent,
            'timestamp': time.time()
        }

    def run(self):
        history = []
        while self.running:
            metrics = self.collect_metrics()

            # Save latest snapshot
            with open(LATEST_METRICS_PATH, 'w') as f:
                json.dump({'metrics': metrics}, f)

            # Append to history
            history.append(metrics)
            with open(METRICS_HISTORY_PATH, 'w') as f:
                json.dump(history, f)

            time.sleep(self.interval)

    def stop(self):
        self.running = False

# For manual run, if needed
if __name__ == '__main__':
    collector = MetricsCollector(interval=5)
    collector.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        collector.stop()
        collector.join()
