import customtkinter as ctk

class SessionViewWindow(ctk.CTkToplevel):
    def __init__(self, master, session_data):
        super().__init__(master)
        self.title(f"Session Data - {session_data.get('hostname', 'N/A')}")
        self.geometry("800x600")

        self.textbox = ctk.CTkTextbox(self, corner_radius=0, wrap="word")
        self.textbox.pack(expand=True, fill="both")
        
        self.textbox.insert("0.0", session_data.get("data", "No data received."))
        self.textbox.configure(state="disabled") # Make it read-only