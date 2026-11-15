"""Soft Actor-Critic policy for continuous battery power.

The actor chooses a fraction of inverter power in [-1, 1]. Negative fractions
charge from observed PV surplus; positive fractions discharge into observed EV
load. Training resamples recorded episodes. Evaluation uses the deterministic actor.
"""

from __future__ import annotations

import json
from datetime import datetime
from math import cos, pi, sin
from pathlib import Path

import numpy as np

from .battery_environment import BatteryDispatchEnvironment
from .training_dataset import Episode

OBSERVATION_SIZE = 6


def observation(env: BatteryDispatchEnvironment) -> np.ndarray:
    slot = env.episode.slots[env.index]
    clock = datetime.fromisoformat(slot.source_time)
    hour = clock.hour + clock.minute / 60
    return np.array(
        [
            env.energy / env.capacity,
            (slot.observed_ev_kw - slot.solar_kw) / env.max_power,
            sin(2 * pi * hour / 24),
            cos(2 * pi * hour / 24),
            (env.energy - env.reserve) / env.capacity,
            1 - env.index / len(env.episode.slots),
        ],
        dtype=np.float32,
    )


def _environment(episodes: tuple[Episode, ...], config: dict, seed: int):
    import gymnasium as gym

    class HistoricalDispatch(gym.Env):
        def __init__(self):
            super().__init__()
            self.episodes = episodes
            self.config = config
            self._rng = np.random.default_rng(seed)
            self.action_space = gym.spaces.Box(-1, 1, shape=(1,), dtype=np.float32)
            self.observation_space = gym.spaces.Box(
                -5, 5, shape=(OBSERVATION_SIZE,), dtype=np.float32
            )
            self.sim: BatteryDispatchEnvironment | None = None

        def reset(self, *, seed=None, options=None):
            super().reset(seed=seed)
            if seed is not None:
                self._rng = np.random.default_rng(seed)
            episode = self.episodes[int(self._rng.integers(len(self.episodes)))]
            self.sim = BatteryDispatchEnvironment(episode, self.config)
            self.sim.reset()
            return observation(self.sim), {}

        def step(self, action):
            assert self.sim is not None
            _outcome, reward, done = self.sim.apply(float(np.asarray(action).reshape(-1)[0]))
            observed = (
                np.zeros(OBSERVATION_SIZE, dtype=np.float32) if done else observation(self.sim)
            )
            return observed, float(reward), bool(done), False, {}

    return HistoricalDispatch()


class SacPolicy:
    algorithm = "soft_actor_critic"

    def __init__(self, model):
        self.model = model

    def fraction(self, env: BatteryDispatchEnvironment) -> tuple[float, bool]:
        action, _state = self.model.predict(observation(env), deterministic=True)
        return float(np.clip(np.asarray(action).reshape(-1)[0], -1, 1)), False

    @classmethod
    def train(
        cls,
        episodes: tuple[Episode, ...],
        config: dict,
        timesteps: int,
        seed: int,
        net_arch: tuple[int, int] = (256, 256),
    ) -> "SacPolicy":
        from stable_baselines3 import SAC

        model = SAC(
            "MlpPolicy",
            _environment(episodes, config, seed),
            learning_rate=3e-4,
            buffer_size=max(timesteps, 10_000),
            learning_starts=min(1_000, max(32, timesteps // 10)),
            batch_size=min(256, max(32, timesteps // 8)),
            tau=0.005,
            gamma=0.99,
            train_freq=1,
            gradient_steps=1,
            ent_coef="auto",
            policy_kwargs={"net_arch": list(net_arch)},
            seed=seed,
            device=_device(),
            verbose=0,
        )
        model.learn(total_timesteps=timesteps, progress_bar=False)
        return cls(model)

    def save(self, path: Path, provenance: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.model.save(str(path.with_suffix("")))
        path.with_suffix(".json").write_text(
            json.dumps(
                {
                    "algorithm": self.algorithm,
                    "device": str(self.model.device),
                    "observation": [
                        "state_of_charge",
                        "net_load_over_inverter",
                        "hour_sin",
                        "hour_cos",
                        "energy_above_reserve",
                        "episode_remaining",
                    ],
                    "action": "battery_power_fraction",
                    "provenance": provenance,
                },
                indent=2,
            )
        )

    @classmethod
    def load(cls, path: Path) -> "SacPolicy":
        from stable_baselines3 import SAC

        return cls(SAC.load(str(path.with_suffix("")), device=_device()))


def _device() -> str:
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"
