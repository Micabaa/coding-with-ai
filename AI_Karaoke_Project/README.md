# 🎤 AI Agentic Karaoke Platform 🤖🎵

> **"Unleash your inner star with the power of AI Agents!"**

The **AI Karaoke Project** is a cutting-edge karaoke platform powered by a **Multi-Agent System** using the **Model Context Protocol (MCP)**. It features real-time lyrics synchronization, AI-based singing evaluation, dynamic judge personalities, and a competitive 1v1 Battle Mode.

---

## ✨ Features

### 🕺 Casual Mode
- **Search & Sing**: Instantly fetch instrumental tracks and synchronized lyrics for any song.
- **AI Sync**: Adjust audio/video offset in real-time for perfect timing.
- **Performance Evaluation**: Get detailed feedback on your **Pitch**, **Rhythm**, and **Lyrics** accuracy.
- **AI Judges**: Choose your judge! From a **Strict Professional** to a **Kind Grandma**, or generate your own custom AI persona.

### 🥊 1v1 Battle Mode
- **Head-to-Head**: Challenge a friend in a turn-based singing battle.
- **Hidden Scores**: Scores are kept secret until the dramatic reveal.
- **Winner Reveal**: Cinematic winner announcement with side-by-side stat comparison.

### 💬 AI Host Chatbot
- **Interactive Host**: Chat with the AI Host to request songs or just hang out.
- **"Sing Now" Integration**: The host finds songs for you and provides a direct button to start performing instantly.
- **Context Aware**: The host remembers your conversation history.

### 📊 Leaderboards
- Track high scores for both Casual and Competition modes.
- Compete for the top spot!

---

## 🏗️ Architecture: The Agentic Mesh

This project demonstrates a robust **Agentic Architecture** where specialized AI agents collaborate to deliver the experience. It uses the **Model Context Protocol (MCP)** to standardize communication.

| Agent | Responsibility |
|-------|----------------|
| **Host Agent** (`host_agent`) | The orchestrator. Exposes the API, manages user state, and routes tasks to other agents. |
| **Audio Agent** (`audio_playback_agent`) | Searches and streams instrumental tracks (using `yt-dlp`). |
| **Lyrics Agent** (`lyrics_display_agent`) | Fetches and synchronizes lyrics (using Genius API). |
| **Evaluator Agent** (`singing_evaluator_agent`) | Analyzes audio input to compute pitch and rhythm scores. |
| **Judge Agent** (`judge_agent`) | Generates qualitative feedback and personas based on performance data. |

---

## 🚀 Getting Started

### Prerequisites

*   **Python 3.10+**
*   **Node.js & npm** (Required for the frontend)
*   **FFmpeg** (Required for audio processing)
    *   **Mac**: `brew install ffmpeg`
    *   **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.
    *   **Linux**: `sudo apt install ffmpeg`
*   **OpenAI API Key** (for Judge/Host intelligence)
*   **Genius API Token** (for Lyrics)

### Quick Start

1.  **Clone the Repository**
    ```bash
    git clone <repository-url>
    cd AI_Karaoke_Project
    ```

2.  **Configure Environment**
    Create a `.env` file in the root directory:
    ```bash
    # OpenAI API Key (Required for Host and Judge Agents)
    OPENAI_API_KEY=sk-your-openai-key-here
    
    # Genius API Token (Required for Lyrics Display Agent)
    GENIUS_ACCESS_TOKEN=your-genius-access-token-here
    ```

3.  **Run the Initialization Script**
    This script sets up virtual environments, installs dependencies, and launches the system.
    ```bash
    ./start_mcp.sh
    ```

4.  **Sing!**
    *   **Frontend**: [http://localhost:5173](http://localhost:5173) (User Interface)
    *   **API Host**: [http://localhost:8000](http://localhost:8000) (Backend API)

---

## 🎮 How to Play

1. **Pick a Mode**: Choose between **Casual** (Solo) or **Battle** (1v1).
2. **Select a Song**: Use the search bar or ask the Chatbot.
3. **Sing Your Heart Out**: The system records your audio (ensure microphone permission is granted).
4. **Get Judged**:
   - In **Casual**, see your score and feedback immediately.
   - In **Battle**, wait for your opponent to finish, then watch the reveal!
5. **View the Legend**: Use the color-coded legend in the evaluation report to understand your lyrics accuracy:
   - 🟢 **Green**: Correct
   - 🟠 **Orange**: Mispronounced
   - 🔴 **Red**: Missed
   - 🔵 **Cyan**: Extra words

---

## 🛠️ Tech Stack
- **Frontend**: React, Vite, Lucide React (Icons), CSS Modules
- **Backend**: Python, FastAPI, MCP (Model Context Protocol)
- **AI/LLM**: OpenAI GPT-4o
- **Audio**: FFmpeg, yt-dlp

---

*Built with ❤️ by the AI Karaoke Team*
