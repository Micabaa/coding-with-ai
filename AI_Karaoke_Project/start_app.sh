#!/bin/bash

# AI Karaoke Project Startup Script

echo "🎤 Starting AI Karaoke Project Setup..."

# 1. Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi
echo "✅ Python 3 found."

# 2. Install Dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt --break-system-packages
if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies."
    exit 1
fi
echo "✅ Dependencies installed."

# 3. Check .env
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  No .env file found."
    echo "   Creating a template at $ENV_FILE..."
    echo "OPENAI_API_KEY=" > "$ENV_FILE"
    echo "GENIUS_ACCESS_TOKEN=" >> "$ENV_FILE"
    echo "   Please add your keys to $ENV_FILE."
else
    echo "✅ .env file found."
fi

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

# 4. Start Agents
echo "🚀 Starting Audio Playback Agent (Port 8001)..."
python3 audio_playback_agent/playback_server.py > audio_agent.log 2>&1 &
AUDIO_PID=$!

echo "🚀 Starting Lyrics Display Agent (Port 8002)..."
python3 lyrics_display_agent/lyrics_server.py > lyrics_agent.log 2>&1 &
LYRICS_PID=$!

echo "🚀 Starting Singing Evaluator Agent (Port 8003)..."
python3 singing_evaluator_agent/evaluator_server.py > evaluator_agent.log 2>&1 &
EVAL_PID=$!

echo "🚀 Starting Judge Agent (Port 8004)..."
python3 judge_agent/judge_server.py > judge_agent.log 2>&1 &
JUDGE_PID=$!

echo "🚀 Starting Host Agent (Port 8000)..."
echo "   Access the application at http://localhost:8000"

# Trap to kill background processes on exit
trap "kill $AUDIO_PID $LYRICS_PID $EVAL_PID $JUDGE_PID" EXIT

python3 host_agent/host_coordinator.py

