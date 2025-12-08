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
    echo "🧹 Cleaning up ports 8000-8004 and 5173-5174..."
    # Combine backend and frontend ports logic
    PORTS=(8000 8001 8002 8003 8004 5173 5174)
    for PORT in "${PORTS[@]}"; do
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
    for PORT in "${PORTS[@]}"; do
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

# 3. Start Frontend
echo "🚀 Starting Frontend..."
cd frontend
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Trap to kill frontend on exit
trap "kill $FRONTEND_PID 2>/dev/null; echo 'Frontend stopped.'" EXIT

# 3. Run Agentic Host
# This is an interactive CLI, so we run it in foreground.
python3 host_agent/agentic_host.py
