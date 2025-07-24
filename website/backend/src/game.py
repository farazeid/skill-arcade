import asyncio
import base64
import json
import logging
import uuid
from datetime import datetime
from typing import Any

import ale_py  # noqa: F401
import cv2
import gymnasium as gym
from fastapi import WebSocket, WebSocketDisconnect

import src.games  # Import to ensure Gymnasium environments are registered
from src.db import Transition
from src.uploader import Uploader

TICK_RATE = 1 / 60  # Aim for 60 FPS


class Game:
    def __init__(
        self,
        seed: int,
        display_name: str,
        env: dict,
        render: bool = False,
        realtime: bool = True,
    ) -> None:
        self.seed = seed
        self.display_name = display_name

        self.env = gym.make(**env["make"])

        self.obs, self.info = self.env.reset(seed=seed)
        self.reward = 0.0
        self.terminated = False
        self.truncated = False
        self.info = {}

        self.render = render
        self.realtime = realtime

        self.n_steps = 0
        self.game_over = False
        self.won = False

    def step(self, action: int) -> None:
        if self.game_over:
            return
        if "INVALID_ACTION" in self.info:
            self.info.pop("INVALID_ACTION")

        try:
            (
                self.obs,
                self.reward,
                self.terminated,
                self.truncated,
                self.info,
            ) = self.env.step(action)
        except KeyError:  # Invalid action `self.transition_matrix[(state, action)][0]`
            self.info["INVALID_ACTION"] = str(action)

        if self.terminated or self.truncated:
            self.game_over = True

        self.won = self.is_game_won()

        self.n_steps += 1

    def is_game_won(self) -> bool:
        if self.display_name == "Towers of Hanoi":
            return self.env.unwrapped.is_state_terminal()
        return False

    def get_state(self) -> dict[str, Any]:
        frame = self.env.render() if self.render else self.obs
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) if frame.shape[-1] == 3 else frame  # fmt: skip
        _, buffer = cv2.imencode(".jpg", frame)
        frame_encoded = base64.b64encode(buffer).decode("utf-8")

        return {
            "frame": frame_encoded,
            "gameOver": self.game_over,
        }

    def get_init_state(self) -> dict[str, Any]:
        state = self.get_state()
        state["gameName"] = self.display_name
        return state


async def game_loop(
    websocket: WebSocket,
    game: Game,
    uploader: Uploader,
    episode_id: uuid.UUID,
) -> None:
    """The main loop that drives a single game instance and sends updates."""

    # For FPS calculation
    loop = asyncio.get_event_loop()
    last_fps_time = loop.time()
    frame_count = 0
    server_fps = 0.0

    action = 0
    time_obs_shown = datetime.now()
    time_action_input = datetime.now()
    while not game.game_over:
        if not game.realtime:
            action = None

        try:
            # --- Handle all incoming client messages ---
            while True:
                try:
                    message_str = await asyncio.wait_for(
                        websocket.receive_text(),
                        timeout=0.001,
                    )
                    message = json.loads(message_str)

                    if message.get("type") == "action" and "action" in message:
                        action = message.get("action")
                        time_obs_shown = message.get("timeObsShown")
                        time_action_input = message.get("timeActionInput")

                        time_obs_shown = time_obs_shown / 1000
                        time_action_input = time_action_input / 1000

                        time_obs_shown = datetime.fromtimestamp(time_obs_shown)
                        time_action_input = datetime.fromtimestamp(time_action_input)

                except TimeoutError:
                    break

                except WebSocketDisconnect:
                    raise

            # If Hanoi, don't tick server until valid action received
            if not game.realtime and action is None:
                await asyncio.sleep(TICK_RATE)
                continue

            obs = game.obs
            game.step(action)
            next_obs = game.obs

            # Create Transition DB entry
            transition = Transition(
                episode_id=episode_id,
                step=game.n_steps,
                action=action,
                reward=game.reward,
                terminated=game.terminated,
                truncated=game.truncated,
                info=game.info,
                time_obs_shown=time_obs_shown,
                time_action_input=time_action_input,
            )

            uploader.put(
                transition,
                obs,
                next_obs if not game.terminated else None,
            )

            # --- FPS Calculation ---
            frame_count += 1
            current_time = loop.time()
            if current_time - last_fps_time >= 1.0:
                server_fps = frame_count / (current_time - last_fps_time)
                frame_count = 0
                last_fps_time = current_time

            # Send the new state to the client
            state = game.get_state()
            state["gameWon"] = game.won
            state["serverFps"] = round(server_fps, 1)
            await websocket.send_text(json.dumps(state))

        except WebSocketDisconnect:
            logging.info("WS: Client disconnected; ending game loop.")
            break

        except Exception as e:
            logging.error(f"WS: Game loop error: {e}", exc_info=True)
            break

        await asyncio.sleep(TICK_RATE)

    # Final state update to make sure client knows game is over
    logging.info("WS: Game over; sending final state.")
    state = game.get_state()
    state["gameWon"] = game.won
    state["serverFps"] = server_fps
    await websocket.send_text(json.dumps(state))
