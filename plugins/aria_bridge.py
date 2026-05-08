import uvicorn
from fastapi import FastAPI

app = FastAPI()


@app.get("/api/mind-map")
def get_mind_map():
    # Placeholder: Lee del modelo de mundo (Dejavu/MapBridge)
    return {
        "nodes": [
            {"name": "Cortex", "pos": [0, 0, 0], "color": "blue"},
            {"name": "Malkhut", "pos": [1, 1, 1], "color": "green"},
        ]
    }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=54446)


@app.get("/api/arena-state")
def get_arena_state():
    return {"participants": [{"id": 1, "pos": [0, 0, 0]}, {"id": 2, "pos": [2, 0, 2]}]}
