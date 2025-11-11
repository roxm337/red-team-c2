#!/usr/bin/env python3


import asyncio
import os
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, TypedDict, Any, Union
import json

from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    Application
)

# --- Configuration ---

# Prefer package-local config; fallback to env
try:
    from .config import telegram_settings
except Exception:
    class _DummySettings:
        TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
        TELEGRAM_ADMIN_CHAT_ID = int(os.getenv("TELEGRAM_ADMIN_CHAT_ID", "0")) if os.getenv("TELEGRAM_ADMIN_CHAT_ID", "0").isdigit() else None
        UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
        DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")
        AGENT_TIMEOUT_SECONDS = int(os.getenv("AGENT_TIMEOUT_SECONDS", "120"))
        COMMAND_HISTORY_DAYS = int(os.getenv("COMMAND_HISTORY_DAYS", "7"))
    telegram_settings = _DummySettings()

# --- Constants ---

# Whitelisted safe commands that agents are allowed to run (diagnostics only)
SAFE_COMMANDS = {
    "PING": "Respond with PONG and timestamp",
    "GET_SYSINFO": "Return sanitized system information",
    "GET_PROCESSES": "Return a limited list of processes (pid + name)",
}

# --- Logging ---

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("SafeTelemetryServer")

# --- Data Models (TypedDict for clarity) ---

class AgentInfo(TypedDict):
    agent_id: str
    hostname: str
    username: str
    os_info: str
    ip_address: str
    python_version: str
    architecture: str
    capabilities: Dict[str, bool]
    last_seen: str
    status: str
    registered_at: str

class CommandEntry(TypedDict):
    command_id: str
    command: str
    command_type: str
    timestamp: str
    status: str
    completed_at: Optional[str]

class CommandResultEntry(TypedDict):
    command_id: str
    agent_id: str
    result: str
    success: bool
    timestamp: str

# --- In-Memory Stores ---

agents: Dict[str, AgentInfo] = {}
commands: Dict[str, List[CommandEntry]] = {}
command_results: Dict[str, List[CommandResultEntry]] = {}

# --- Singleton Server Class ---

class SafeTelegramC2Server:
    def __init__(self, bot_token: str, admin_chat_id: Optional[int] = None):
        if not bot_token:
            raise ValueError("Bot token required")

        self.bot_token = bot_token
        self.admin_chat_id = admin_chat_id
        self.agent_timeout_seconds = getattr(telegram_settings, "AGENT_TIMEOUT_SECONDS", 120)
        self.command_history_days = getattr(telegram_settings, "COMMAND_HISTORY_DAYS", 7)

        self.application: Application = (
            ApplicationBuilder()
            .token(bot_token)
            .post_init(self._post_init)
            .build()
        )

        os.makedirs(telegram_settings.UPLOAD_DIR, exist_ok=True)
        os.makedirs(telegram_settings.DOWNLOAD_DIR, exist_ok=True)

        self._register_handlers()
        self._set_bot_commands()

        self._bg_started = False

    def _register_handlers(self):
        self.application.add_handler(CommandHandler("start", self._handle_start))
        self.application.add_handler(CommandHandler("help", self._handle_help))
        self.application.add_handler(CommandHandler("agents", self._handle_list_agents))
        self.application.add_handler(CommandHandler("info", self._handle_agent_info))
        self.application.add_handler(CommandHandler("cmd", self._handle_queue_command))
        self.application.add_handler(CommandHandler("files", self._handle_list_files))
        self.application.add_handler(CommandHandler("register_agent", self._handle_register_agent))
        self.application.add_handler(CommandHandler("heartbeat", self._handle_heartbeat))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))

    def _set_bot_commands(self):
        pass

    # --- Public API for Agents/Clients ---

    async def register_agent(self, agent_data: Dict[str, Any]) -> bool:
        agent_id = agent_data.get("agent_id")
        if not agent_id or not isinstance(agent_id, str):
            logger.warning(f"Invalid agent registration attempt: {agent_data}")
            return False

        now_str = datetime.utcnow().isoformat()
        new_agent_info: AgentInfo = {
            "agent_id": agent_id,
            "hostname": agent_data.get("hostname", "Unknown"),
            "username": agent_data.get("username", "Unknown"),
            "os_info": agent_data.get("os_info", "Unknown"),
            "ip_address": agent_data.get("ip_address", "Unknown"),
            "python_version": agent_data.get("python_version", "Unknown"),
            "architecture": agent_data.get("architecture", "Unknown"),
            "capabilities": agent_data.get("capabilities", {}),
            "last_seen": now_str,
            "status": "online",
            "registered_at": now_str,
        }

        agents[agent_id] = new_agent_info
        commands.setdefault(agent_id, [])
        command_results.setdefault(agent_id, [])

        logger.info(f"Agent registered: {agent_id} ({new_agent_info['hostname']})")
        await self._notify_admin(f"✅ Agent registered: <code>{agent_id}</code>\nHost: {new_agent_info['hostname']}")
        return True

    async def heartbeat(self, agent_id: str) -> bool:
        if agent_id in agents:
            agents[agent_id]["last_seen"] = datetime.utcnow().isoformat()
            agents[agent_id]["status"] = "online"
            return True
        return False

    def get_commands_for_agent(self, agent_id: str) -> List[CommandEntry]:
        return [cmd for cmd in commands.get(agent_id, []) if cmd.get("status") == "pending"]

    async def send_command_result(self, agent_id: str, command_id: str, result: Any, success: bool):
        result_str = str(result)[:4000]
        entry: CommandResultEntry = {
            "command_id": command_id,
            "agent_id": agent_id,
            "result": result_str,
            "success": bool(success),
            "timestamp": datetime.utcnow().isoformat(),
        }
        command_results.setdefault(agent_id, []).append(entry)
        self.mark_command_completed(agent_id, command_id)

        logger.info(f"Result stored for {agent_id} cmd {command_id}, success={success}")
        await self._notify_admin(f"{'✅' if success else '❌'} Result for <code>{agent_id}</code> cmd <code>{command_id}</code>\nResult: <pre>{result_str[:500]}</pre>")

    def mark_command_completed(self, agent_id: str, command_id: str):
        if agent_id in commands:
            for cmd in commands[agent_id]:
                if cmd.get("command_id") == command_id:
                    cmd["status"] = "completed"
                    cmd["completed_at"] = datetime.utcnow().isoformat()
                    break

    # --- Internal Telegram Command Handlers ---

    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("✅ Safe Telemetry Server running. Use /help for commands.")

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "Safe Telemetry Server - Admin Commands:\n\n"
            "/agents - List connected agents\n"
            "/info &lt;agent_id&gt; - Show detailed info about an agent\n"
            "/cmd &lt;agent_id&gt; &lt;WHITELISTED_COMMAND&gt; [args...] - Queue a safe command to an agent\n"
            "/files - List files in server upload/download directories\n\n"
            "Allowed Commands:\n" + "\n".join([f"- {k}: {v}" for k, v in SAFE_COMMANDS.items()])
        )
        await update.message.reply_text(help_text, parse_mode="HTML")

    async def _handle_list_agents(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not agents:
            await update.message.reply_text("No agents registered.")
            return

        lines = []
        now = datetime.utcnow()
        for agent_id, agent_info in agents.items():
            last_seen_str = agent_info.get("last_seen", "Never")
            try:
                last_seen_dt = datetime.fromisoformat(last_seen_str)
                diff = now - last_seen_dt
                if diff > timedelta(seconds=self.agent_timeout_seconds):
                    status = "offline"
                else:
                    status = agent_info.get("status", "unknown")
            except ValueError:
                status = "unknown"

            lines.append(
                f"ID: <code>{agent_id}</code>\n"
                f"  Host: {agent_info['hostname']}\n"
                f"  OS: {agent_info['os_info']}\n"
                f"  Status: {status}\n"
                f"  Last Seen: {last_seen_str}\n"
            )
        response = "Connected Agents:\n\n" + "\n".join(lines[:50])
        await update.message.reply_text(response, parse_mode="HTML")

    async def _handle_agent_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 1:
            await update.message.reply_text("Usage: /info <agent_id>")
            return

        agent_id = context.args[0]
        agent_info = agents.get(agent_id)
        if not agent_info:
            await update.message.reply_text(f"Agent <code>{agent_id}</code> not found.", parse_mode="HTML")
            return

        info_lines = [
            f"<b>Agent Information: {agent_id}</b>\n",
            f"• Hostname: {agent_info['hostname']}",
            f"• Username: {agent_info['username']}",
            f"• OS: {agent_info['os_info']}",
            f"• IP: {agent_info['ip_address']}",
            f"• Python: {agent_info['python_version']}",
            f"• Arch: {agent_info['architecture']}",
            f"• Registered: {agent_info['registered_at']}",
            f"• Last Seen: {agent_info['last_seen']}",
            f"• Status: {agent_info['status']}",
        ]
        caps = [k for k, v in agent_info['capabilities'].items() if v]
        if caps:
            info_lines.append(f"• Capabilities: {', '.join(caps)}")
        else:
            info_lines.append(f"• Capabilities: None")

        response = "\n".join(info_lines)
        await update.message.reply_text(response, parse_mode="HTML")

    async def _handle_register_agent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            message_text = update.message.text
            if '\n' in message_text:
                json_part = message_text.split('\n', 1)[1]
                agent_data = json.loads(json_part)
            else:
                await update.message.reply_text("Invalid registration format. Expected JSON data.")
                return

            success = await self.register_agent(agent_data)
            if success:
                agent_id = agent_data.get('agent_id', 'unknown')
                await update.message.reply_text(f"✅ Agent {agent_id} registered successfully!")
            else:
                await update.message.reply_text("❌ Failed to register agent. Invalid data.")
        except json.JSONDecodeError:
            await update.message.reply_text("❌ Invalid JSON format in registration data.")
        except Exception as e:
            logger.error(f"Error handling agent registration: {e}")
            await update.message.reply_text("❌ Error processing registration.")

    async def _handle_heartbeat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 1:
            await update.message.reply_text("Usage: /heartbeat <agent_id>")
            return
        agent_id = context.args[0]
        success = await self.heartbeat(agent_id)
        if success:
            await update.message.reply_text(f"✅ Heartbeat received from {agent_id}")
        else:
            await update.message.reply_text(f"❌ Agent {agent_id} not found")

    async def _handle_queue_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /cmd <agent_id> <COMMAND> [args...]")
            return

        agent_id = context.args[0]
        if agent_id not in agents:
            await update.message.reply_text(f"Agent <code>{agent_id}</code> not found.", parse_mode="HTML")
            return

        command_name = context.args[1].upper()
        if command_name not in SAFE_COMMANDS:
            allowed_list = ", ".join(SAFE_COMMANDS.keys())
            await update.message.reply_text(f"Command '{command_name}' is not allowed. Allowed: {allowed_list}")
            return

        params = context.args[2:]
        command_full = command_name + (" " + " ".join(params) if params else "")

        command_id = str(uuid.uuid4())
        cmd_entry: CommandEntry = {
            "command_id": command_id,
            "command": command_full,
            "command_type": "safe",
            "timestamp": datetime.utcnow().isoformat(),
            "status": "pending",
            "completed_at": None,
        }
        commands.setdefault(agent_id, []).append(cmd_entry)

        logger.info(f"Queued safe command {command_id} -> {agent_id}: {command_full}")
        await update.message.reply_text(f"✅ Queued command '{command_name}' for agent <code>{agent_id}</code> (ID: <code>{command_id}</code>)", parse_mode="HTML")

    async def _handle_list_files(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        upload_files = []
        download_files = []
        try:
            upload_files = [f for f in os.listdir(telegram_settings.UPLOAD_DIR) if os.path.isfile(os.path.join(telegram_settings.UPLOAD_DIR, f))]
        except Exception as e:
            logger.error(f"Error listing upload dir: {e}")
        try:
            download_files = [f for f in os.listdir(telegram_settings.DOWNLOAD_DIR) if os.path.isfile(os.path.join(telegram_settings.DOWNLOAD_DIR, f))]
        except Exception as e:
            logger.error(f"Error listing download dir: {e}")
        if not upload_files and not download_files:
            await update.message.reply_text("No files found in server directories.")
            return
        text_parts = []
        if upload_files:
            text_parts.append(f"<b>Upload Directory ({telegram_settings.UPLOAD_DIR}):</b>\n" + "\n".join([f"• <code>{f}</code>" for f in upload_files[:20]]))
        if download_files:
            text_parts.append(f"\n<b>Download Directory ({telegram_settings.DOWNLOAD_DIR}):</b>\n" + "\n".join([f"• <code>{f}</code>" for f in download_files[:20]]))
        response = "\n".join(text_parts)
        await update.message.reply_text(response, parse_mode="HTML")

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Message received by the server. Use /help for available commands.")

    # --- Background Tasks ---

    async def _post_init(self, app: Application):
        if not self._bg_started:
            self._bg_started = True
            try:
                await app.bot.set_my_commands([
                    BotCommand("start", "Start the bot"),
                    BotCommand("help", "Show help message"),
                    BotCommand("agents", "List connected agents"),
                    BotCommand("info", "Get info about a specific agent"),
                    BotCommand("cmd", "Queue a safe command to an agent"),
                    BotCommand("files", "List server-side files"),
                ])
                logger.info("Bot commands set successfully.")
            except Exception as e:
                logger.error(f"Failed to set bot commands: {e}")
            app.create_task(self._maintenance_loop())

    async def _maintenance_loop(self):
        while True:
            try:
                now = datetime.utcnow()
                cutoff = now - timedelta(seconds=self.agent_timeout_seconds)
                for agent_id, agent_info in agents.items():
                    last_seen_str = agent_info.get("last_seen")
                    if last_seen_str:
                        try:
                            last_seen_dt = datetime.fromisoformat(last_seen_str)
                            if last_seen_dt < cutoff:
                                agent_info["status"] = "offline"
                        except ValueError:
                            agent_info["status"] = "offline"
                expiry = now - timedelta(days=self.command_history_days)
                for agent_id in list(command_results.keys()):
                    command_results[agent_id] = [
                        r for r in command_results[agent_id]
                        if datetime.fromisoformat(r["timestamp"]) > expiry
                    ]
            except Exception as e:
                logger.error(f"Error in maintenance loop: {e}")
            await asyncio.sleep(30)

    # --- Utility Methods ---

    async def _notify_admin(self, message: str):
        if self.admin_chat_id:
            try:
                await self.application.bot.send_message(
                    chat_id=self.admin_chat_id,
                    text=message,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to notify admin: {e}")

    def start(self):
        logger.info("🚀 Starting Safe Telemetry Server...")
        logger.info(f"Admin Chat ID: {self.admin_chat_id}")
        self.application.run_polling()

    async def shutdown(self):
        await self.application.shutdown()

# --- Singleton Access ---

_telegram_c2_server: Optional[SafeTelegramC2Server] = None

def get_telegram_server() -> Optional[SafeTelegramC2Server]:
    global _telegram_c2_server
    return _telegram_c2_server

# --- Main Entry Point ---

def main():
    global _telegram_c2_server
    bot_token = getattr(telegram_settings, "TELEGRAM_BOT_TOKEN", "") or os.getenv("TELEGRAM_BOT_TOKEN", "")
    admin_chat_id_env = getattr(telegram_settings, "TELEGRAM_ADMIN_CHAT_ID", None) or os.getenv("TELEGRAM_ADMIN_CHAT_ID")

    if not bot_token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not set; exiting.")
        return

    admin_chat_id = None
    if admin_chat_id_env:
        try:
            admin_chat_id = int(admin_chat_id_env)
        except (ValueError, TypeError):
            logger.error("❌ TELEGRAM_ADMIN_CHAT_ID is not a valid integer; proceeding without admin notifications.")

    _telegram_c2_server = SafeTelegramC2Server(bot_token=bot_token, admin_chat_id=admin_chat_id)
    _telegram_c2_server.start()

if __name__ == "__main__":
    main()


