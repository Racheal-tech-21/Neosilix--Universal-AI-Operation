# ai_engine/run_detection.py
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from core.system_metrics_collector import collect_metrics

class AnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(contamination=0.05, random_state=42)
        self.trained = False

    def train(self, data: list):
        df = pd.DataFrame(data)
        self.model.fit(df)
        self.trained = True

    def predict(self, metric_sample: dict):
        if not self.trained:
            return {"error": "Model not trained yet"}

        df = pd.DataFrame([metric_sample])
        result = self.model.predict(df)[0]
        return {"anomaly": result == -1}

def generate_sample_metrics(n=50):
    samples = []
    for _ in range(n):
        metrics = collect_metrics()
        samples.append(metrics)
        time.sleep(0.1)  # simulate time interval
    return samples

import json
import time
import os

if __name__ == "__main__":
    detector = AnomalyDetector()

    print("[INFO] Starting detection loop...")
    history = []

    while True:
        try:
            metric = collect_metrics()
            history.append(metric)

            # Save rolling history (for training later)
            with open("metrics_history.json", "w") as f:
                json.dump(history[-500:], f, indent=2)  # keep last 500 records only

            print(f"[INFO] Collected metric at {time.time()}")

            time.sleep(5)  # collect every 5 seconds

        except Exception as e:
            print(f"[ERROR] Detection loop error: {e}")
            time.sleep(5)
