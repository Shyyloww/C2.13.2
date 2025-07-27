from flask import Flask, request, jsonify
from queue import Queue

# This queue will be used to pass data from the Flask thread to the GUI thread
data_queue = Queue()

app = Flask(__name__)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    # Put the entire data packet into the queue for the GUI to process
    data_queue.put({
        "type": "new_session",
        "session_id": data.get("session_id"),
        "hostname": data.get("hostname"),
        "data": data.get("data")
    })
    return jsonify({"status": "ok"}), 200

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json
    data_queue.put({
        "type": "heartbeat",
        "session_id": data.get("session_id")
    })
    return jsonify({"status": "ok"}), 200

def run_server():
    # Runs on a non-standard port to avoid conflicts
    app.run(host='0.0.0.0', port=5001)