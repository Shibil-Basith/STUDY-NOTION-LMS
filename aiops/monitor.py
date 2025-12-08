import time
import requests
import numpy as np
from sklearn.ensemble import IsolationForest
from datetime import datetime

# Configuration
TARGET_URL = "http://backend-service:80"  # Internal K8s DNS
POLL_INTERVAL = 5  # Seconds
HISTORY_SIZE = 50  # Data points to keep for training

print(f"🤖 AIOps Agent Started. Monitoring {TARGET_URL}...")

# Store response times
latency_history = []

def get_latency():
    try:
        start = time.time()
        requests.get(TARGET_URL, timeout=2)
        return (time.time() - start) * 1000  # Convert to ms
    except:
        return 2000.0  # Penalty for timeout

while True:
    current_latency = get_latency()
    latency_history.append([current_latency])

    # Keep history manageable
    if len(latency_history) > HISTORY_SIZE:
        latency_history.pop(0)

    # Train model continuously on recent data
    if len(latency_history) >= 20:
        # GreenOps: Using a lightweight model (IsolationForest) saves compute
        clf = IsolationForest(contamination=0.1, random_state=42)
        clf.fit(latency_history)
        
        # Predict if current latency is an anomaly (-1 is anomaly, 1 is normal)
        prediction = clf.predict([[current_latency]])
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        if prediction[0] == -1:
            print(f"⚠️ [{timestamp}] ANOMALY DETECTED! High Latency: {current_latency:.2f}ms")
        else:
            print(f"✅ [{timestamp}] System Stable. Latency: {current_latency:.2f}ms")
    
    time.sleep(POLL_INTERVAL)