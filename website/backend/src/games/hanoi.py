import copy
import itertools
from collections.abc import Iterable
from typing import Any

import distinctipy
import numpy as np
import pygame
from gymnasium import spaces

from src.games import TabularEnvironment

# Implementation from https://github.com/bath-reinforcement-learning-lab/brll-core


class HanoiEnvironment(TabularEnvironment):
    metadata = {
        "render_modes": ["human", "rgb_array"],
        "render_fps": 4,
    }

    def __init__(
        self,
        num_disks: int = 4,
        num_poles: int = 3,
        action_penalty: float = -0.001,
        goal_reward: float = 1.0,
        start_state: tuple[int, ...] | None = None,
        goal_state: tuple[int, ...] | None = None,
        render_mode: str | None = None,
    ) -> None:
        """
        Instantiates a new HanoiEnvironment object with a specified number of disks and poles.

        Args:
            num_disks (int, optional): Number of poles in the environment. Defaults to 4.
            num_poles (int, optional): Number of disks in the environment. Defaults to 3.
            action_penalty (float, optional): Penalty for each action taken. Defaults to -0.001.
            goal_reward (float, optional): Reward for reaching the goal state. Defaults to 1.0.
            start_state (ObsType, optional): The initial state to use. Defaults to None, in which case the state where all disks are on the leftmost pole is used.
            goal_state (ObsType, optional): The goal state to use. Defaults to None, in which case the state where all disks are on the rightmost pole is used.
        """
        assert num_disks > 0 and num_poles > 0
        self.num_disks = num_disks
        self.num_poles = num_poles

        # Initialise state and action mappings.
        self.move_list = list(itertools.permutations(list(range(self.num_poles)), 2))
        self.state_list = list(
            itertools.product(list(range(self.num_poles)), repeat=self.num_disks)
        )

        self.observation_space = spaces.MultiDiscrete(
            [
                self.num_poles,
            ]
            * self.num_disks
        )
        self.action_space = spaces.Discrete(len(self.move_list))

        # Set start state.
        self.start_state: tuple[int, ...]
        if start_state is not None:
            assert len(start_state) == self.num_disks
            self.start_state = start_state
        else:
            self.start_state = self.num_disks * (0,)

        # Set goal state.
        if goal_state is not None:
            assert len(goal_state) == self.num_disks
            self.goal_state = goal_state
        else:
            self.goal_state = self.num_disks * (self.num_poles - 1,)

        assert self.start_state != self.goal_state

        # Define reward function.
        self.action_penalty = action_penalty
        self.goal_reward = goal_reward

        self.renderer = None
        self.render_mode = render_mode

        # Initialise environment state variables.
        self.terminal = True
        self.current_state: tuple[int, ...]

        super().__init__(deterministic=True)

    def get_action_meanings(self) -> list[str]:
        return [
            f"Move from Pole {source} to Pole {dest}" for source, dest in self.move_list
        ]

    def reset(
        self,
        *,
        state: tuple[int, ...] | None = None,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[tuple[int, ...], dict[str, Any]]:
        """
        Resets the environment to an initial state, with all disks stacked
        on the leftmost pole (i.e. pole with index zero).

        Args:
            state (Optional[Tuple[int, ...]], optional): The initial state to use. Defaults to None, in which case an state is chosen according to the environment's initial state distribution.
            seed (Optional[int], optional): A seed for random number generation to ensure reproducibility. Defaults to None.
            options (Optional[Dict[str, Any]], optional): Additional information to specify how to reset the environment (optional, depending on the specific environment). Defaults to None.

        Returns:
            Tuple[Tuple[int, ...], Dict[str, Any]]: A tuple containing the initial observation of the environment and any additional information as a dictionary.
        """
        self.current_state: tuple[int, ...]
        if state is None:
            self.current_state = copy.deepcopy(self.start_state)
        else:
            self.current_state = copy.deepcopy(state)

        self.terminal = False

        if self.render_mode == "human":
            self.render()

        return copy.deepcopy(self.current_state), self._get_info()

    def is_state_terminal(self, state: tuple[int, ...] | None = None) -> bool:
        if state is None:
            state = self.current_state

        # A state is only terminal if it is the goal state.
        return state == self.goal_state

    def get_successors(
        self, state: tuple[int, ...] | None = None, action: int | None = None
    ) -> Iterable[tuple[tuple[tuple[int, ...], float], float]]:
        if state is None:
            state = self.current_state

        actions: list[int]
        actions = (
            self.get_available_actions(state=state) if action is None else [action]
        )

        # Creates a list of all states which can be reached by
        # taking the legal actions available in the given state.
        successor_states = []
        for action in actions:
            successor_state = list(state)
            source_pole, dest_pole = self.move_list[action]
            disk_to_move = min(self._disks_on_pole(source_pole, state=state))
            successor_state[disk_to_move] = dest_pole
            successor_state = tuple(successor_state)

            reward = (
                self.goal_reward
                if successor_state == self.goal_state
                else self.action_penalty
            )

            successor_states.append(((successor_state, reward), 1.0 / len(actions)))

        return successor_states

    def get_available_actions(self, state: tuple[int, ...] | None = None) -> list[int]:
        if state is None:
            state = self.current_state

        if self.is_state_terminal(state):
            return []
        else:
            legal_actions = [
                i
                for i, action in enumerate(self.move_list)
                if self._is_move_legal(action, state=state)
            ]
            return legal_actions

    def is_action_valid(self, action: int) -> bool:
        return self._is_move_legal(self.move_list[action])

    def _get_action_mask(self) -> np.ndarray:
        # Get legal actions in given state.
        legal_actions = self.get_available_actions(state=self.current_state)

        # Get list of all actions.
        all_actions = list(range(len(self.move_list)))

        # True is action is in legal actions, false otherwise.
        legal_action_mask = map(lambda action: action in legal_actions, all_actions)

        return np.array(list(legal_action_mask), dtype=np.int8)

    def _get_info(self) -> dict:
        return {}
        return {"action_mask": self._get_action_mask()}

    def get_initial_states(self) -> list[tuple[int, ...]]:
        return [self.start_state]

    def _is_move_legal(
        self, move: tuple[int, int], state: tuple[int, ...] | None = None
    ) -> bool:
        if state is None:
            state = self.current_state

        source_pole, dest_pole = move
        source_disks = self._disks_on_pole(source_pole, state=state)
        dest_disks = self._disks_on_pole(dest_pole, state=state)

        if source_disks == []:
            # Cannot move a disk from an empty pole!
            return False
        else:
            if dest_disks == []:
                # Can always move a disk to an empty pole!
                return True
            else:
                # Otherwise, only allow the move if the smallest disk on the
                # source pole is smaller than the smallest disk on destination pole.
                return min(source_disks) < min(dest_disks)

    def _disks_on_pole(
        self, pole: int, state: tuple[int, ...] | None = None
    ) -> list[int]:
        if state is None:
            state = self.current_state
        return [disk for disk in range(self.num_disks) if state[disk] == pole]

    def render(self) -> np.ndarray | None:
        if self.render_mode is None:
            return

        if self.renderer is None:
            self.renderer = HanoiRenderer(
                self.num_poles, self.num_disks, render_mode=self.render_mode
            )

        return self.renderer.update(self.current_state)

    def close(self) -> None:
        """
        Cleanly stops the environment, closing any associated renderer.
        """
        # Close renderer, if one exists.
        if self.renderer is not None:
            self.renderer.close()
            self.renderer = None


WIDTH = 800
HEIGHT = 600

BACKGROUND_COLOUR = (0, 0, 0)
POLE_COLOUR = (128, 128, 128)

POLE_WIDTH = 8
POLE_PADDING = 16
POLE_HEIGHT = HEIGHT // 2
POLE_Y = HEIGHT // 4


class HanoiRenderer:
    def __init__(self, num_poles: int, num_disks: int, render_mode: str) -> None:
        self.num_poles = num_poles
        self.num_disks = num_disks

        self._calculate_dimensions()

        self.pole_spacing = WIDTH // (num_poles + 1)

        self.disk_colours = [
            distinctipy.get_rgb256(colour)
            for colour in distinctipy.get_colors(self.num_disks)
        ]

        self.render_mode = render_mode

        # Initialise pygame and display window.
        pygame.init()
        if self.render_mode == "human":
            self.display_window = pygame.display.set_mode((WIDTH, HEIGHT))
        elif self.render_mode == "rgb_array":
            self.display_window = pygame.Surface((WIDTH, HEIGHT))

    def update(self, state: tuple[int, ...]) -> np.ndarray | None:
        self.display_window.fill(BACKGROUND_COLOUR)

        # Draw poles.
        for pole_index in range(self.num_poles):
            pole_x = self.pole_spacing * (pole_index + 1)
            self._draw_pole(pole_x)

        # Draw disks.
        for pole_index in range(self.num_poles):
            disks_on_pole = [i for i, pos in enumerate(state) if pos == pole_index]
            pole_x = self.pole_spacing * (pole_index + 1)
            self._draw_disks(pole_x, disks_on_pole)

        if self.render_mode == "human":
            pygame.display.update()
        elif self.render_mode == "rgb_array":
            return np.transpose(
                np.array(pygame.surfarray.pixels3d(self.display_window)), axes=(1, 0, 2)
            )

    def close(self) -> None:
        pygame.quit()

    def _calculate_dimensions(self) -> None:
        total_spacing = WIDTH * 0.8
        self.pole_spacing = total_spacing // (self.num_poles + 1)
        self.pole_start_x = (WIDTH - total_spacing) / 2

        self.disk_height = HEIGHT // 2 // (self.num_disks + 1)

        max_disk_width = self.pole_spacing - POLE_PADDING
        self.disk_widths = [
            int(max_disk_width * (disk_index + 1) / self.num_disks)
            for disk_index in range(self.num_disks)
        ]

    def _draw_pole(self, pole_x: int | float) -> None:
        pygame.draw.rect(
            self.display_window,
            POLE_COLOUR,
            (pole_x - POLE_WIDTH // 2, POLE_Y, POLE_WIDTH, POLE_HEIGHT),
        )

    def _draw_disks(self, pole_x: int | float, disks_on_pole: list[int]) -> None:
        for i, disk in enumerate(sorted(disks_on_pole, reverse=False)):
            disk_width = self.disk_widths[disk]
            disk_x = pole_x - disk_width // 2
            disk_y = POLE_Y + POLE_HEIGHT - (len(disks_on_pole) - i) * self.disk_height

            disk_colour = self.disk_colours[disk % len(self.disk_colours)]
            pygame.draw.rect(
                self.display_window,
                disk_colour,
                (disk_x, disk_y, disk_width, self.disk_height),
            )
