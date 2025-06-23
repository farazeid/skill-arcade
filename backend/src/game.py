import base64
from typing import Any, Dict

import ale_py
import cv2
import gymnasium as gym


class Game:
    def __init__(self, display_name: str, env: dict) -> None:
        self.display_name = display_name

        self.env = gym.make(**env["make"])

        action_meanings = self.env.unwrapped.get_action_meanings()
        self.action_ids = {name: i for i, name in enumerate(action_meanings)}

        self.obs, self.info = self.env.reset()

        self.game_over = False

    def step(self, action: int) -> None:
        if self.game_over:
            return

        self.obs, _, _, _, info = self.env.step(action)

        if "lives" in info:
            self.lives = info["lives"]
            if self.lives == 0:
                self.game_over = True

    def get_state(self) -> Dict[str, Any]:
        _, buffer = cv2.imencode(".jpg", self.obs)
        obs_encoded = base64.b64encode(buffer).decode("utf-8")

        return {
            "frame": obs_encoded,
            "gameOver": self.game_over,
        }

    def get_init_state(self) -> Dict[str, Any]:
        state = self.get_state()
        state["actions"] = list(self.action_ids.keys())
        state["gameName"] = self.display_name
        return state
