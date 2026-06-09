import time
import urllib.request
from datetime import datetime

# Set your live URL here
URL = "https://crisis-logistics-optimizer.onrender.com"

# Ping interval (10 minutes = 600 seconds)
INTERVAL_SECONDS = 600

print(f"Starting keep-alive ping service for: {URL}")
print(f"Pinging every {INTERVAL_SECONDS // 60} minutes. Press Ctrl+C to stop.\n")

while True:
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Send a simple HEAD request to minimize bandwidth usage
        req = urllib.request.Request(URL, method="HEAD")
        with urllib.request.urlopen(req) as response:
            status = response.status
            print(f"[{current_time}] Ping sent. Server response status: {status}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Ping failed: {e}")
    
    time.sleep(INTERVAL_SECONDS)
