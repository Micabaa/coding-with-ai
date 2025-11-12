# Contents of /AI_Karaoke_Project/host_agent/host_coordinator.py

class HostCoordinator:
    def __init__(self):
        self.agents = {
            "audio_playback": None,
            "lyrics_display": None,
            "singing_evaluator": None,
            "judge": None
        }

    def register_agent(self, agent_name, agent_instance):
        if agent_name in self.agents:
            self.agents[agent_name] = agent_instance
            print(f"{agent_name} registered successfully.")
        else:
            print(f"Agent {agent_name} is not recognized.")

    def coordinate(self):
        # Logic to coordinate between agents
        print("Coordinating between agents...")
        # Example of interaction
        if self.agents["audio_playback"] and self.agents["lyrics_display"]:
            self.agents["audio_playback"].play()
            lyrics = self.agents["lyrics_display"].get_lyrics()
            print(f"Displaying lyrics: {lyrics}")

if __name__ == "__main__":
    coordinator = HostCoordinator()
    # Here you would typically register agents and start the coordination process
    # Example: coordinator.register_agent("audio_playback", AudioPlaybackAgent())
    # coordinator.coordinate()