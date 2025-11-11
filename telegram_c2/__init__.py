"""
Telegram C2 package

Modules:
- server: SafeTelegramC2Server and entrypoint
- client: TelegramC2Client and CLI
- manager: TelegramClientManager and CLI
- config: telegram_settings loader
"""

# Re-export common items for convenience
from .config import telegram_settings  # noqa: F401


