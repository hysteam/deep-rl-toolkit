from typing import Any, Tuple, Union

import cloudpickle
import gymnasium as gym
import numpy as np
from rltoolkit.envs.pettingzooo_env import PettingZooEnv

ENV_TYPE = Union[gym.Env, 'gym.Env', PettingZooEnv]

gym_new_venv_step_type = Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray,
                               np.ndarray]


class CloudpickleWrapper(object):
    """A cloudpickle wrapper used in SubprocVectorEnv."""

    def __init__(self, data: Any) -> None:
        self.data = data

    def __getstate__(self) -> str:
        return cloudpickle.dumps(self.data)

    def __setstate__(self, data: str) -> None:
        self.data = cloudpickle.loads(data)
