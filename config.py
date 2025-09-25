import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # C2 Server settings (no authentication required)
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "downloads")
    
    # Enhanced features settings
    MAX_COMMAND_QUEUE_SIZE: int = int(os.getenv("MAX_COMMAND_QUEUE_SIZE", "100"))
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "50000000"))  # 50MB default
    SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", "3600"))  # 1 hour default
    LOG_RETENTION_DAYS: int = int(os.getenv("LOG_RETENTION_DAYS", "30"))

settings = Settings()
