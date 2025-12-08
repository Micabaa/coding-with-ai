import asyncio
import logging
from host_agent.agentic_host import KaraokeHost

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_flow():
    print("🧪 Starting MCP Flow Verification...")
    host = KaraokeHost()
    try:
        await host.start()
        print("✅ Host started and connected to agents.")
        
        # Test 1: Simple greeting (should not call tools)
        print("\n--- Test 1: Greeting ---")
        response = await host.process_user_input("Hello, who are you?")
        print(f"Host: {response}")
        
        # Test 2: Song request (should call lyrics and audio tools)
        # Note: We won't actually play audio in this test environment, but we check if tools are called.
        # The logs will show tool calls.
        print("\n--- Test 2: Song Request ---")
        response = await host.process_user_input("I want to sing Bohemian Rhapsody")
        print(f"Host: {response}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        await host.cleanup()
        print("\n✅ Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(test_flow())
