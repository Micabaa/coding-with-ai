# Al Karaoke Project

## Overview
The Al Karaoke Project is an Agentic AI application designed to provide an interactive karaoke experience. It consists of multiple agents, each serving a distinct role in the karaoke process, including audio playback, lyrics display, singing evaluation, and performance judging.

## Project Structure
The project is organized into several modules, each representing a different agent:

- **audio_playback_agent**: Handles audio playback functionality.
  - `playback_server.py`: Main server logic for playing audio tracks.
  - `tools/`: Contains utility functions for audio playback.

- **lyrics_display_agent**: Manages the display of song lyrics.
  - `lyrics_server.py`: Main server logic for displaying lyrics.
  - `api_connectors/`: Connects to external APIs to fetch lyrics.
    - `lyrics_api_tool.py`: Functionality for lyrics API integration.

- **singing_evaluator_agent**: Evaluates singing performances.
  - `evaluator_server.py`: Main server logic for evaluating performances.
  - `audio_tools/`: Tools for analyzing audio input.
    - `audio_analysis_tool.py`: Functions for pitch detection and timing analysis.

- **judge_agent**: Evaluates performances based on predefined criteria.
  - `judge_server.py`: Main server logic for judging performances.
  - `personality_prompts/`: Contains personality prompts for judging.
    - `strict_judge.txt`: Prompts for a strict judging personality.
    - `supportive_grandma.txt`: Prompts for a supportive judging personality.

- **host_agent**: Acts as the client coordinator, managing interactions between agents.
  - `host_coordinator.py`: Logic for coordinating between agents.

## Installation
To set up the project, clone the repository and install the required dependencies:

```bash
git clone <repository-url>
cd Al_Karaoke_Project
pip install -r requirements.txt
```

## Usage
To run the project, start each agent's server in separate terminal instances:

1. Start the audio playback agent:
   ```bash
   python audio_playback_agent/playback_server.py
   ```

2. Start the lyrics display agent:
   ```bash
   python lyrics_display_agent/lyrics_server.py
   ```

3. Start the singing evaluator agent:
   ```bash
   python singing_evaluator_agent/evaluator_server.py
   ```

4. Start the judge agent:
   ```bash
   python judge_agent/judge_server.py
   ```

5. Finally, start the host agent:
   ```bash
   python host_agent/host_coordinator.py
   ```

## Verification
To verify the interaction between the Singing Evaluator and the Judge Agent, run the verification script:

```bash
python test_clients/verify_agents.py
```

This script generates a synthetic audio tone, sends it to the Singing Evaluator, and forwards the result to the Judge Agent.

### Configuration
To enable real AI feedback from the Judge Agent, create a `.env` file in the `judge_agent` directory with your OpenAI API key:

```bash
OPENAI_API_KEY=sk-your-api-key-here
```

If the key is missing, the Judge Agent will run in **Mock Mode** and return placeholder feedback.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.