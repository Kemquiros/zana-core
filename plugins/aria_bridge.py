from fastapi import FastAPI
import uvicorn
import json
from pathlib import Path

app = FastAPI()

@app.get("/api/mind-map")
def get_mind_map():
    # Placeholder: Lee del modelo de mundo (Dejavu/MapBridge)
    return {"nodes": [{"name": "Cortex", "pos": [0,0,0], "color": "blue"}, {"name": "Malkhut", "pos": [1,1,1], "color": "green"}]}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=54446)
