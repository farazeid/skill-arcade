import asyncio
import json
from pathlib import Path

import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src import Game, game_loop

# Enable CORS so the frontend (served from Firebase or elsewhere) can call the API
# In production you may want to restrict the allowed origins instead of "*".
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Replace with specific origins for stricter security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/games")
def list_games() -> list[dict[str, str]]:
    """List all available games."""
    game_configs_path = Path("game_configs")
    game_info = []
    for f in game_configs_path.glob("*.yaml"):
        with open(f) as f_in:
            game_config = yaml.safe_load(f_in)
            game_info.append(
                {"id": f.stem, "display_name": game_config["display_name"]}
            )
    return game_info


@app.websocket("/ws/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str) -> None:
    """Handle a new WebSocket connection, creating a unique game for it."""
    await websocket.accept()
    print(f"New client connected for game {game_id}, creating game.")

    game_config_path = Path("game_configs") / f"{game_id}.yaml"
    if not game_config_path.is_file():
        print(f"Game config not found: {game_config_path}")
        await websocket.close(code=1003)  # 1003: "unsupported data
        return

    with open(game_config_path) as f:
        game_config = yaml.safe_load(f)

    game = Game(**game_config)
    game_loop_task = None
    try:
        # Send the initial state and action map to get the game started
        initial_state = game.get_init_state()
        await websocket.send_text(json.dumps(initial_state))

        # Start the game loop for this client
        game_loop_task = asyncio.create_task(game_loop(websocket, game))
        await game_loop_task

    except WebSocketDisconnect:
        print("Client forcefully disconnected.")
    finally:
        if game_loop_task:
            game_loop_task.cancel()
        game.env.close()
        print("Game loop task cancelled and environment closed.")
