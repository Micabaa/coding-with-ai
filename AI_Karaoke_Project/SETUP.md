# Setup Instructions 🛠️

This guide covers how to set up and run the **AI Karaoke Project**.

## Prerequisites

Before you begin, ensure you have the following installed:

*   **Python 3.10+**
*   **Node.js & npm** (Required for the frontend)
*   **FFmpeg** (Required for audio processing)
    *   **Mac**: `brew install ffmpeg`
    *   **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.
    *   **Linux**: `sudo apt install ffmpeg`

## Installation

1.  **Clone the repository**
    ```bash
    git clone <repository-url>
    cd AI_Karaoke_Project
    ```

2.  **Install Python Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Install Frontend Dependencies**
    ```bash
    cd frontend
    npm install
    cd ..
    ```

## Configuration

You must configure the environment variables for the AI agents to work.

1.  Create a `.env` file in the root directory (or run the startup script once to generate a template).
2.  Add your API keys:

```bash
# OpenAI API Key (Required for Host and Judge Agents)
OPENAI_API_KEY=sk-your-openai-key-here

# Genius API Token (Required for Lyrics Display Agent)
GENIUS_ACCESS_TOKEN=your-genius-access-token-here
```

## Running the Application

### Option 1: Automated Startup (Recommended)

Use the provided script to launch the entire system (Backend Agents + Frontend).

```bash
./start_mcp.sh
```

*   **Frontend**: Opens automatically at `http://localhost:5173`
*   **Backend Host**: Runs on `http://localhost:8000`

### Option 2: Manual Startup

If you prefer to run components individually for debugging:

1.  **Start the Host Agent (Backend)**
    ```bash
    # This acts as the MCP Client and orchestrator
    python host_agent/agentic_host.py
    ```

2.  **Start the Frontend**
    ```bash
    cd frontend
    npm run dev
    ```

*Note: The individual sub-agents (audio, lyrics, evaluator, judge) act as MCP servers and are automatically managed by the Host Agent process in this architecture.*

## Troubleshooting

-   **Ports in use**: The startup script attempts to free ports 8000-8004 and 5173. If startup fails, check for lingering python or node processes.
-   **Missing Audio**: Ensure FFmpeg is correctly installed and accessible in your terminal.
-   **Lyrics not syncing**: Check your internet connection and Genius API token validity.
