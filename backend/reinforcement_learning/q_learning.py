"""Small, inspectable tabular Q learner; inference needs no Ray service."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from backend.storage.atomic import write_json

from .battery_environment import (
    ACTION_FRACTIONS,
    IDLE_ACTION,
    BatteryDispatchEnvironment,
    greedy_action,
)
from .training_dataset import Episode

State = tuple[int, int, int]


@dataclass
class QLearningPolicy:
    values: dict[State, list[float]]
    visits: dict[State, list[int]]
    minimum_visits: int = 3

    def action(self, state: State, episode: Episode, index: int) -> tuple[int, bool]:
        counts = self.visits.get(state)
        if counts is None:
            return greedy_action(episode.slots[index]), True
        eligible = [i for i, count in enumerate(counts) if count >= self.minimum_visits]
        if not eligible:
            return greedy_action(episode.slots[index]), True
        return max(eligible, key=lambda i: (self.values[state][i], -abs(i - IDLE_ACTION))), False

    def fraction(self, env: BatteryDispatchEnvironment) -> tuple[float, bool]:
        action, fallback = self.action(env.state(), env.episode, env.index)
        return ACTION_FRACTIONS[action], fallback

    def save(self, path: Path, provenance: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "algorithm": "tabular_q_learning",
            "minimum_visits": self.minimum_visits,
            "action_fractions": ACTION_FRACTIONS,
            "provenance": provenance,
            "states": [
                {
                    "state": list(state),
                    "values": self.values[state],
                    "visits": self.visits[state],
                }
                for state in sorted(self.values)
            ],
        }
        write_json(path, payload)

    @classmethod
    def load(cls, path: Path) -> "QLearningPolicy":
        payload = json.loads(path.read_text())
        if (
            payload["algorithm"] != "tabular_q_learning"
            or tuple(payload["action_fractions"]) != ACTION_FRACTIONS
        ):
            raise ValueError("Unsupported policy artifact")
        return cls(
            {tuple(row["state"]): row["values"] for row in payload["states"]},
            {tuple(row["state"]): row["visits"] for row in payload["states"]},
            payload["minimum_visits"],
        )


def train(
    episodes: tuple[Episode, ...], config: dict, iterations: int = 12000, seed: int = 42
) -> QLearningPolicy:
    if not episodes or iterations <= 0:
        raise ValueError("Training needs episodes and positive iterations")
    rng = random.Random(seed)
    policy = QLearningPolicy({}, {})
    discount = 0.985
    for iteration in range(iterations):
        episode = rng.choice(episodes)
        env = BatteryDispatchEnvironment(episode, config)
        state = env.reset()
        exploration = max(0.05, 0.8 * (1 - iteration / iterations))
        for index in range(len(episode.slots)):
            if rng.random() < exploration:
                action = rng.randrange(len(ACTION_FRACTIONS))
            else:
                action, _ = policy.action(state, episode, index)
            _, reward, done = env.step(action)
            values = policy.values.setdefault(state, [0.0] * len(ACTION_FRACTIONS))
            visits = policy.visits.setdefault(state, [0] * len(ACTION_FRACTIONS))
            visits[action] += 1
            next_value = 0.0
            if not done:
                next_state = env.state()
                next_visits = policy.visits.get(next_state)
                if next_visits:
                    next_value = max(
                        policy.values[next_state][i] for i, count in enumerate(next_visits) if count
                    )
            rate = 0.18 / (1 + visits[action] / 75) ** 0.5
            values[action] += rate * (reward + discount * next_value - values[action])
            if done:
                break
            state = next_state
    return policy
