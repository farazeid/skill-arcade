from abc import ABC, abstractmethod
from typing import Any

import gymnasium as gym
from gymnasium import register, spaces
from gymnasium.core import ActType, ObsType, RenderFrame

register(
    id="brll/Hanoi-v0",
    entry_point="src.games.hanoi:HanoiEnvironment",
    disable_env_checker=True,
)


class BaseEnvironment(gym.Env[ObsType, ActType], ABC):
    """
    Base class for all environments in the BRLL framework, providing a common interface and basic functionality.
    This class inherits from Farama Gymnasium's `Env` class.
    """

    metadata: dict[str, Any] = {"render_modes": []}

    observation_space: spaces.Space[ObsType]
    action_space: spaces.Space[ActType]

    def __init__(self, render_mode: str | None = None) -> None:
        super().__init__()

    @abstractmethod
    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[ObsType, dict[str, Any]]:
        raise NotImplementedError("Reset method must be implemented by the subclass.")

    @abstractmethod
    def step(
        self, action: ActType
    ) -> tuple[ObsType, float, bool, bool, dict[str, Any]]:
        raise NotImplementedError("Step method must be implemented by the subclass.")

    def render(self) -> RenderFrame | list[RenderFrame] | None:
        return None
