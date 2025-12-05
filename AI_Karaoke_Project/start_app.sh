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
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies."
    exit 1
fi
echo "✅ Dependencies installed."

# 3. Check .env for Judge Agent
ENV_FILE="judge_agent/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  No .env file found for Judge Agent."
    echo "   Creating a template at $ENV_FILE..."
    echo "OPENAI_API_KEY=" > "$ENV_FILE"
    echo "   Please add your OPENAI_API_KEY to $ENV_FILE for real feedback."
else
    echo "✅ .env file found."
fi

# 4. Start Host Agent
echo "🚀 Starting Host Agent..."
echo "   Access the application at http://localhost:8090"
python3 host_agent/host_coordinator.py
