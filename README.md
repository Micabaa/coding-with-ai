# AI Karaoke Project 🎤

An interactive, agentic AI karaoke experience where multiple AI agents collaborate to provide backing tracks, synced lyrics, real-time singing evaluation, and personality-driven judging.

## Overview

This project demonstrates an **Agentic AI Architecture** using the **Model Context Protocol (MCP)**. Instead of a monolithic application, distinct agents run as independent servers and communicate via a central Host Agent.

### The Agents 🤖

1.  **Host Agent (Orchestrator)**
    *   **Role**: The central brain. It runs a FastAPI web server and manages connections to all other agents using MCP.
    *   **Tech**: Python, FastAPI, MCP Client, OpenAI GPT-4o.
    *   **Entry Point**: `host_agent/agentic_host.py`

2.  **Audio Playback Agent**
    *   **Role**: Manages the library of songs and handles audio playback commands.
    *   **Tech**: MCP Server, PyDub, SoundFile.

3.  **Lyrics Display Agent**
    *   **Role**: Fetches lyrics from the Genius API and provides line-by-line synchronization.
    *   **Tech**: MCP Server, LyricsGenius.

4.  **Singing Evaluator Agent**
    *   **Role**: The "ears" of the system. It analyzes user audio input, comparing pitch and timing against the original track.
    *   **Tech**: MCP Server, Librosa, FastDTW.

5.  **Judge Agent**
    *   **Role**: The "critic". It takes evaluation data and generates feedback based on a specific persona (e.g., "Strict Simon" or "Kind Grandma").
    *   **Tech**: MCP Server, OpenAI API.

## Project Structure

```
AI_Karaoke_Project/
├── host_agent/           # Central orchestrator (MCP Client + Web Server)
├── audio_playback_agent/ # Music library and playback controls
├── lyrics_display_agent/ # Lyrics fetching and sync
├── singing_evaluator_agent/ # Audio analysis logic
├── judge_agent/          # Personality-driven feedback
├── frontend/             # React/Vite web interface
├── start_mcp.sh          # Main startup script
└── requirements.txt      # Python dependencies
```

## Setup & Usage 🛠️

For detailed installation, configuration, and running instructions, please refer to the [Setup Guide](SETUP.md).

Quick Start:
```bash
./start_mcp.sh
```

## How It Works

1.  **User Request**: You type "I want to sing Bohemian Rhapsody" in the web UI.
2.  **Host Planning**: The Host Agent receives the text. It uses an LLM to decide which tool to call.
3.  **Execution**:
    *   Host calls `Audio Agent` -> `play_song("Bohemian Rhapsody")`.
    *   Host calls `Lyrics Agent` -> `search_lyrics("Bohemian Rhapsody")`.
4.  **Performance**: You sing along! The frontend records your audio.
5.  **Evaluation**: The recording is sent to the Host, which forwards it to the `Singing Evaluator`.
6.  **Judgment**: The technical scores (pitch/timing) are passed to the `Judge Agent`, which writes a review like: *"Pitchy on the high notes, darling, but I loved the enthusiasm!"*

## License

MIT License