import asyncio
import websockets
import json

async def mock_koruos_aeon():
    uri = "ws://localhost:4444/ws/mcp"
    print("⏳ [KoruOS] Connecting to ZANA MCP Socket...")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ [KoruOS] Connected. Waiting for proactive events (Push)...")

            while True:
                # The Aeon listens for server events without polling
                response = await websocket.recv()
                event = json.loads(response)

                print(f"\n⚡ [KoruOS] Interrupt received from ZANA!")
                print(f"  └─> Intent:   {event.get('intent')}")
                print(f"  └─> Emotion:  {event.get('emotion')}")
                print(f"  └─> Message:  \"{event.get('message')}\"")

    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(mock_koruos_aeon())
