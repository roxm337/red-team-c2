# Enhanced C2 Server Makefile

.PHONY: help install start test demo clean

# Default target
help:
	@echo "Enhanced C2 Server - Available Commands:"
	@echo "========================================"
	@echo "  make install    - Install dependencies"
	@echo "  make start      - Start the C2 server"
	@echo "  make test       - Run tests"
	@echo "  make demo       - Run demo"
	@echo "  make clean      - Clean up files"
	@echo "  make help       - Show this help"

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	pip3 install -r requirements.txt
	@echo "✅ Dependencies installed!"

# Start the server
start:
	@echo "🚀 Starting Enhanced C2 Server..."
	python3 start_server.py

# Run tests
test:
	@echo "🧪 Running tests..."
	python3 test_c2.py

# Run demo
demo:
	@echo "🎭 Running demo..."
	python3 demo.py

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	rm -rf uploads/*
	rm -rf downloads/*
	rm -rf __pycache__
	rm -rf *.pyc
	rm -rf .pytest_cache
	@echo "✅ Cleanup complete!"

# Development setup
dev-setup: install
	@echo "🔧 Setting up development environment..."
	mkdir -p uploads downloads static templates
	@echo "✅ Development environment ready!"

# Quick start (install + start)
quick-start: install start
