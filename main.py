import time
from agent import VoiceAgent

def main():
    """Main function to run the voice agent."""
    agent = VoiceAgent()
    agent.start()

    print("Agent is running. Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping agent...")
        agent.stop()
        # The final "Agent stopped." message is printed from within agent.stop()

if __name__ == "__main__":
    main()