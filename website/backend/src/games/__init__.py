import copy
import random
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from typing import Any, Generic, TypeVar

import gymnasium as gym
import networkx as nx
from gymnasium import register, spaces
from gymnasium.core import ActType, ObsType, RenderFrame
from networkx import DiGraph, Graph

register(
    id="brll/Hanoi-v0",
    entry_point="src.games.hanoi:HanoiEnvironment",
    disable_env_checker=True,
)

# Implementation from https://github.com/bath-reinforcement-learning-lab/brll-core


class AvailableActionsMixin(Generic[ActType], ABC):
    @abstractmethod
    def is_action_valid(self, action: ActType) -> bool:
        """
        Checks if the given action is valid in the current state of the environment.

        Args:
            action (ActType): The action to check for validity.

        Returns:
            bool: True if the action is valid, False otherwise.
        """
        raise NotImplementedError(
            "is_action_valid method must be implemented by the subclass."
        )

    @abstractmethod
    def get_available_actions(self) -> Sequence[ActType]:
        """
        Returns a list of available actions in the current state of the environment.

        Returns:
            Sequence[ActType]: A sequence of available actions.
        """
        raise NotImplementedError(
            "get_available_actions method must be implemented by the subclass."
        )


EncodedObsType = TypeVar("EncodedObsType")


class EncodedObservationMixin(Generic[ObsType, EncodedObsType], ABC):
    @abstractmethod
    def encode_observation(self, observation: ObsType) -> EncodedObsType:
        """
        Encodes the observation into a format suitable for processing by the agent.

        Args:
            observation (ObsType): The observation to encode.

        Returns:
            EncodedObsType: The encoded observation.
        """
        raise NotImplementedError(
            "encode_observation method must be implemented by the subclass."
        )

    @abstractmethod
    def decode_observation(self, encoded_observation: EncodedObsType) -> ObsType:
        """
        Decodes the encoded observation back into its original format.

        Args:
            encoded_observation (EncodedObsType): The encoded observation to decode.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.

        Returns:
            ObsType: The decoded observation.
        """
        raise NotImplementedError(
            "decode_observation method must be implemented by the subclass."
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


class TabularEnvironment(
    BaseEnvironment[ObsType, ActType], AvailableActionsMixin[ActType], ABC
):
    """
    Base class for tabular environments in the BRLL framework, providing a common interface and basic functionality.
    This class inherits from the `BaseEnvironment` class.
    """

    def __init__(self, deterministic: bool, render_mode: str | None = None) -> None:
        super().__init__(render_mode)

        self.current_state: ObsType
        self.deterministic = deterministic
        self.transition_matrix: dict[
            tuple[ObsType, ActType], Sequence[tuple[tuple[ObsType, float], float]]
        ] = self._compute_transition_matrix()

    @abstractmethod
    def reset(
        self,
        *,
        state: ObsType | None = None,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[ObsType, dict[str, Any]]:
        """
        Resets the environment to an initial state.

        Args:
            state (Optional[ObsType], optional): A specific state to reset the environment to. If None, a random initial state is chosen. Defaults to None.
            seed (Optional[int], optional): A seed for random number generation to ensure reproducibility. Defaults to None.
            options (Optional[Dict[str, Any]], optional): Additional information to specify how to reset the environment (optional, depending on the specific environment). Defaults to None.

        Returns:
            Tuple[ObsType, Dict[str, Any]]: A tuple containing the initial observation of the environment and any additional information as a dictionary.
        """
        raise NotImplementedError("Reset method must be implemented by the subclass.")

    def step(
        self, action: ActType, state: ObsType | None = None
    ) -> tuple[ObsType, float, bool, bool, dict]:
        if state is None:
            state = self.current_state

        if self.deterministic:
            (next_state, reward), _ = self.transition_matrix[(state, action)][0]
        else:
            outcomes, probabilities = zip(
                *self.transition_matrix[(state, action)], strict=False
            )
            (next_state, reward) = random.choices(outcomes, probabilities, k=1)[0]

        terminal = self.is_state_terminal(next_state)
        truncated = False

        self.current_state = next_state

        if self.render_mode == "human":
            self.render()

        return next_state, reward, terminal, truncated, self._get_info()

    @abstractmethod
    def is_state_terminal(self, state: ObsType | None = None) -> bool:
        """
        Checks if the given state is terminal.

        Args:
            state (Optional[ObsType]): The state to check. If None, the current state of the environment is used.

        Returns:
            bool: True if the state is terminal, False otherwise.
        """
        raise NotImplementedError(
            "is_state_terminal method must be implemented by the subclass."
        )

    @abstractmethod
    def get_initial_states(self) -> Sequence[ObsType]:
        """
        Returns an sequence of initial states for the environment.

        Returns:
            Sequence[ObsType]: An iterable of initial states.
        """
        raise NotImplementedError(
            "get_initial_states method must be implemented by the subclass."
        )

    @abstractmethod
    def get_available_actions(self, state: ObsType | None = None) -> Sequence[ActType]:
        """
        Returns an iterable of available actions in the current state of the environment.

        Args:
            state (Optional[ObsType], optional): The state to get available actions for. If None, the current state of the environment is used. Defaults to None.

        Returns:
            Sequence[ActType] | Sequence[Sequence[ActType]]: A sequence of available actions. If the
            action space has multiple dimensions, it returns a sequence of sequences, where each inner
            sequence corresponds to the available actions for that dimension.
        """
        raise NotImplementedError(
            "get_available_actions method must be implemented by the subclass."
        )

    @abstractmethod
    def get_successors(
        self, state: ObsType | None = None, action: ActType | None = None
    ) -> Iterable[tuple[tuple[ObsType, float], float]]:
        """
        Returns the possible successor next-states and rewards of a given state and action, along with their probabilities of occuring.

        The returned iterable contains tuples of the form:
            ((next_state, reward), probability)

        If no state is provided, successors are returned for the environment's current state.
        If no action is provided, successors are returned for all available actions in the current state. In this case, the probabilities are assumed to be equal for each action.

        Args:
            state (Optional[ObsType], optional): The state to get successors for. If None, the current state of the environment is used. Defaults to None.
            action (Optional[ActType], optional): The action to get successors for. If None, successors for all available actions in the current state are returned. Defaults to None.

        Returns:
            Iterable[Tuple[Tuple[ObsType,float],float]]: An iterable of tuples, where each tuple contains the next state and reward, along with the probability of that transition occurring.
        """
        raise NotImplementedError(
            "get_successors method must be implemented by the subclass."
        )

    def _compute_transition_matrix(
        self,
    ) -> dict[tuple[ObsType, ActType], Sequence[tuple[tuple[ObsType, float], float]]]:
        transition_matrix = {}

        all_states = self.generate_interaction_graph(directed=False).nodes()

        for state in all_states:
            for action in self.get_available_actions(state=state):
                transition_matrix[(state, action)] = self.get_successors(
                    state=state, action=action
                )

        return transition_matrix

    def _get_info(self) -> dict:
        """Generates any additional information to be passed during env.step() or env.reset()

        Returns:
            dict: Defaults to an empty dictionary. Override in implemented environments.
        """
        return {}

    def _generate_all_states(self) -> list[ObsType]:
        # Generates a list of all reachable states, starting the search from the environment's initial states.
        states = []
        current_successor_states = self.get_initial_states()

        # Brute force construction of the state-transition graph. Starts with initial states,
        # then tries to add possible successor states until no new successor states can be added.
        while len(current_successor_states) != 0:
            next_successor_states = []
            for successor_state in current_successor_states:
                if successor_state not in states:
                    states.append(successor_state)

                    if not self.is_state_terminal(successor_state):
                        new_successors = self.get_successors(successor_state)
                        for (new_successor_state, _), _ in new_successors:
                            next_successor_states.append(new_successor_state)

            current_successor_states = copy.deepcopy(next_successor_states)
        return states

    def generate_interaction_graph(
        self, directed: bool | None = True, weighted: bool | None = False
    ) -> Graph | DiGraph:
        """
        Returns a NetworkX DiGraph representing the state-transition graph for this environment.

        Arguments:
            directed (bool, optional): Whether the state-transition graph should be directed. Defaults to True.
            weighted (bool, optional): Whether the state-transition graph should be weighted. Defaults to False.

        Raises:
            ValueError: If weighted is True and directed is False. Weighted graphs must be directed.

        Returns:
            nx.DiGraph: A NetworkX DiGraph representing the state-transition graph for this environment. Nodes are states, edges are possible transitions, edge weights are one.
        """

        if weighted and not directed:
            raise ValueError("Weighted graphs must be directed.")

        # Build state-transition graph.
        stg = nx.DiGraph() if directed else nx.Graph()

        for state in self._generate_all_states():
            # Add node for state.
            stg.add_node(state)

            # Add edge between node and its successors.
            successors = self.get_successors(state)
            for (successor_state, _), transition_prob in successors:
                stg.add_node(successor_state)
                if not weighted:
                    stg.add_edge(state, successor_state)
                else:
                    if stg.has_edge(state, successor_state):
                        stg[state][successor_state]["weight"] += transition_prob
                    else:
                        stg.add_edge(state, successor_state, weight=transition_prob)

        return stg
