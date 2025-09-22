#!/usr/bin/env python3
"""
Startup script for the Enhanced C2 Server
"""

import uvicorn
import os
import sys
from pathlib import Path

def main():
    """Start the C2 server with proper configuration"""
    
    # Ensure we're in the right directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Create necessary directories
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    
    print("🚀 Starting Enhanced C2 Server...")
    print("📊 Dashboard: http://localhost:8000")
    print("🔧 API Docs: http://localhost:8000/docs")
    print("📡 WebSocket: ws://localhost:8000/ws")
    print("\n⚡ Server is running! Press Ctrl+C to stop.")
    print("=" * 50)
    
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print("❌ Server error: {}".format(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
