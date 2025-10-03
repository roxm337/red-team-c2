import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # C2 Server settings (no authentication required)
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    DOWNLOAD_DIR: str = os.getenv("DOWNLOAD_DIR", "downloads")
    
    # Public IP Configuration for External Access
    PUBLIC_IP: str = os.getenv("PUBLIC_IP", "")
    PUBLIC_DOMAIN: str = os.getenv("PUBLIC_DOMAIN", "")
    USE_HTTPS: bool = os.getenv("USE_HTTPS", "false").lower() == "true"
    
    # Get the public URL for client connections
    @property
    def get_public_url(self) -> str:
        if self.PUBLIC_DOMAIN:
            protocol = "https" if self.USE_HTTPS else "http"
            return f"{protocol}://{self.PUBLIC_DOMAIN}"
        elif self.PUBLIC_IP:
            protocol = "https" if self.USE_HTTPS else "http"
            return f"{protocol}://{self.PUBLIC_IP}:{self.SERVER_PORT}"
        else:
            return f"http://{self.SERVER_HOST}:{self.SERVER_PORT}"
    
    # Enhanced features settings
    MAX_COMMAND_QUEUE_SIZE: int = int(os.getenv("MAX_COMMAND_QUEUE_SIZE", "100"))
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "50000000"))  # 50MB default
    SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", "3600"))  # 1 hour default
    LOG_RETENTION_DAYS: int = int(os.getenv("LOG_RETENTION_DAYS", "30"))

settings = Settings()
