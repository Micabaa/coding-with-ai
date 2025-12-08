#!/bin/bash

# AI Karaoke MCP Startup Script

echo "🎤 Starting AI Karaoke Agentic Host (MCP)..."

# 1. Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# 2. Install Dependencies (Fast check)
# We assume they are installed or user can run pip install -r requirements.txt manually if needed, 
# but let's just do a quick install to be safe.
pip3 install -r requirements.txt --break-system-packages > /dev/null 2>&1

# Function to kill processes on specific ports
cleanup_ports() {
    echo "🧹 Cleaning up ports 8000-8004..."
    for PORT in {8000..8004}; do
        # Find all PIDs using the port
        PIDS=$(lsof -ti:$PORT)
        if [ ! -z "$PIDS" ]; then
            echo "   Killing processes on port $PORT: $PIDS"
            # Use xargs to handle multiple PIDs correctly
            echo "$PIDS" | xargs kill -9 2>/dev/null
        fi
    done
    
    echo "   Waiting for ports to be released..."
    sleep 2
    
    # Verify ports are free
    for PORT in {8000..8004}; do
        if lsof -i:$PORT >/dev/null; then
            echo "❌ Port $PORT is still in use. Retrying cleanup..."
            PIDS=$(lsof -ti:$PORT)
            if [ ! -z "$PIDS" ]; then
                echo "$PIDS" | xargs kill -9 2>/dev/null
            fi
            sleep 1
        fi
    done
}

# Clean ports before starting
cleanup_ports

# 3. Run Agentic Host
# This is an interactive CLI, so we run it in foreground.
python3 host_agent/agentic_host.py
