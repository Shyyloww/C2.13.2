import sys
import os

def add_project_root_to_path():
    current_file_path = os.path.abspath(__file__)
    c2_server_dir = os.path.dirname(current_file_path)
    project_root = os.path.dirname(c2_server_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

add_project_root_to_path()

# We only need to import the App now
from c2_server.gui.main_window import App

if __name__ == "__main__":
    print("[*] Launching C2 Control Panel GUI...")
    # No longer need a data_queue or a server_thread
    app = App()
    app.mainloop()
    print("[*] C2 application has been closed.")