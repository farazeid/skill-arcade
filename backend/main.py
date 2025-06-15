# main.py
# To run this:
# 1. Make sure this file (main.py) and the index.html file are in the SAME directory.
# 2. Install dependencies: pip install "gymnasium[atari, accept-rom-license]" opencv-python "fastapi[all]"
# 3. Run the server: uvicorn main:app --reload
# 4. Open your browser and go to http://127.0.0.1:8000

import asyncio
import base64
import json
from pathlib import Path
from typing import Any, Dict

import ale_py  # <-- IMPORT THIS TO REGISTER ATARI ENVS
import cv2
import gymnasium as gym
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

# Initialize FastAPI app
app = FastAPI()


# --- Game Logic ---
class BreakoutGame:
    """Encapsulates the state and logic for a single Gymnasium Breakout instance."""

    def __init__(self):
        # Create the Gymnasium environment
        self.env = gym.make("BreakoutNoFrameskip-v4", render_mode="rgb_array")
        self.score: int = 0
        self.lives: int = 5  # Breakout starts with 5 lives
        self.game_over: bool = False
        self.last_observation, self.info = self.env.reset()
        print("Gymnasium environment created.")

    def step(self, action: int) -> None:
        """Takes a step in the environment."""
        # We don't step the environment if the game is already over.
        if self.game_over:
            return

        # Execute the action in the environment
        observation, reward, terminated, truncated, info = self.env.step(action)

        self.last_observation = observation
        self.score += reward

        # CORRECTED LOGIC:
        # The definitive game over condition is running out of lives.
        # The `terminated` flag from the env only signals the end of a single life (episode).
        # We rely on the 'lives' from the info dict to determine the true game state.
        if "lives" in info:
            self.lives = info["lives"]
            if self.lives == 0:
                self.game_over = True

    def get_state(self) -> Dict[str, Any]:
        """
        Returns the current state of the game, including the rendered frame.
        The frame is encoded as a Base64 string for JSON serialization.
        """
        # Encode the frame as a JPEG image
        _, buffer = cv2.imencode(".jpg", self.last_observation)
        # Convert the buffer to a Base64 string
        jpg_as_text = base64.b64encode(buffer).decode("utf-8")

        return {
            "frame": jpg_as_text,
            "score": self.score,
            "lives": self.lives,
            "gameOver": self.game_over,
        }


async def game_loop(websocket: WebSocket, game: BreakoutGame):
    """The main loop that drives a single game instance and sends updates."""
    TICK_RATE = 1 / 60  # Aim for 60 FPS

    # For FPS calculation
    loop = asyncio.get_event_loop()
    last_fps_time = loop.time()
    frame_count = 0
    server_fps = 0.0

    active_actions = set()

    while True:
        try:
            # --- Handle all incoming client messages ---
            # Drain the websocket queue to process all messages since last tick
            while True:
                try:
                    message_str = await asyncio.wait_for(
                        websocket.receive_text(), timeout=0.001
                    )
                    message = json.loads(message_str)
                    action = message.get("action")
                    if not action:
                        continue

                    if message["type"] == "action":
                        active_actions.add(action)
                    elif message["type"] == "release_action":
                        active_actions.discard(action)

                except asyncio.TimeoutError:
                    # No more messages in the queue
                    break
                except WebSocketDisconnect:
                    raise  # Re-raise to be caught by the outer loop
                except Exception:
                    # Ignore other message-related errors
                    pass

            # --- Determine action for this tick ---
            # Action priority: FIRE > RIGHT > LEFT.
            # Only one action can be sent to the environment at a time.
            action_for_this_tick = 0  # Default to NOOP
            if "FIRE" in active_actions:
                action_for_this_tick = 1
            elif "RIGHT" in active_actions:
                action_for_this_tick = 2
            elif "LEFT" in active_actions:
                action_for_this_tick = 3

            # Update the game state with the action for this tick
            game.step(action_for_this_tick)

            # --- FPS Calculation ---
            frame_count += 1
            current_time = loop.time()
            if current_time - last_fps_time >= 1.0:
                server_fps = frame_count / (current_time - last_fps_time)
                frame_count = 0
                last_fps_time = current_time

            # Send the new state to the client
            state = game.get_state()
            state["serverFps"] = round(server_fps, 1)
            await websocket.send_text(json.dumps(state))

        except WebSocketDisconnect:
            print("Client disconnected. Ending game loop.")
            break
        except Exception as e:
            print(f"An error occurred in the game loop: {e}")
            break

        # Control the game's speed
        await asyncio.sleep(TICK_RATE)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle a new WebSocket connection, creating a unique game for it."""
    await websocket.accept()
    print("New client connected, creating Breakout game.")

    game = BreakoutGame()
    game_loop_task = None
    try:
        # Send the initial state to get the game started on the client
        initial_state = game.get_state()
        await websocket.send_text(json.dumps(initial_state))

        # Start the game loop for this client
        game_loop_task = asyncio.create_task(game_loop(websocket, game))
        await game_loop_task

    except WebSocketDisconnect:
        print("Client forcefully disconnected.")
    finally:
        if game_loop_task:
            game_loop_task.cancel()
        game.env.close()  # Important: close the environment to free resources
        print("Game loop task cancelled and environment closed.")


# --- Serve Frontend --
# This mounts the current directory and tells FastAPI to serve index.html
# for the root URL. This is more robust than reading the file manually.
# NOTE: This must come AFTER the /ws endpoint.
script_dir = Path(__file__).parent.resolve()
app.mount("/", StaticFiles(directory=script_dir, html=True), name="static")
