import sys
import os
import threading

# --- START OF THE FIX ---
# This block of code adds the project's root directory (Tether C2.13) to the Python path.
# This allows imports like 'from c2_server...' to work even when running this script directly.
def add_project_root_to_path():
    # Get the absolute path of the current file (e.g., C:\...\Tether C2.13\c2_server\main.py)
    current_file_path = os.path.abspath(__file__)
    # Get the directory of the current file (e.g., C:\...\Tether C2.13\c2_server)
    c2_server_dir = os.path.dirname(current_file_path)
    # Get the parent directory, which is our project root (e.g., C:\...\Tether C2.13)
    project_root = os.path.dirname(c2_server_dir)
    # Add the project root to the list of paths Python searches for modules
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

add_project_root_to_path()
# --- END OF THE FIX ---


# We only need to import the App now
from c2_server.gui.main_window import App

if __name__ == "__main__":
    print("[*] Launching C2 Control Panel GUI...")
    # No longer need a data_queue or a server_thread
    app = App()
    app.mainloop()
    print("[*] C2 application has been closed.")