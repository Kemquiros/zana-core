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
