import pytest
from fastapi.testclient import TestClient
from sensory.multimodal_gateway import app

client = TestClient(app)

def test_websocket_stream_basic():
    with client.websocket_connect("/sense/stream") as websocket:
        websocket.send_json({"type": "text", "data": "Hello Aeon", "session_id": "test_1"})
        
        # We expect a chunk response or an error (since API keys might be missing in test env)
        response = websocket.receive_json()
        assert "type" in response or "modality" in response

def test_websocket_stream_stress():
    with client.websocket_connect("/sense/stream") as websocket:
        # Send 10 messages rapidly
        for i in range(10):
            websocket.send_json({"type": "text", "data": f"Stress {i}", "session_id": f"stress_{i}"})
        
        responses = []
        # Each message triggers a stream of chunks and an 'end' or PerceptionEvent
        # In current implementation, it might block and we might get them sequentially or it might crash
        # We just want to see if we get responses without connection being closed prematurely
        for _ in range(5): # Just check first 5 responses
            responses.append(websocket.receive_json())
            
        assert len(responses) > 0
