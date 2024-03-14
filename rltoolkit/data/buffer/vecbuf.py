from typing import Any

import numpy as np

from .base import ReplayBuffer
from .her import HERReplayBuffer
from .manager import (HERReplayBufferManager, PrioritizedReplayBufferManager,
                      ReplayBufferManager)
from .prio import PrioritizedReplayBuffer


class VectorReplayBuffer(ReplayBufferManager):
    """VectorReplayBuffer contains n ReplayBuffer with the same size.

    It is used for storing transition from different environments yet keeping the order
    of time.

    :param int total_size: the total size of VectorReplayBuffer.
    :param int buffer_num: the number of ReplayBuffer it uses, which are under the same
        configuration.

    Other input arguments (stack_num/ignore_obs_next/save_only_last_obs/sample_avail)
    are the same as :class:`~rltoolkit.data.ReplayBuffer`.

    .. seealso::

        Please refer to :class:`~rltoolkit.data.ReplayBuffer` for other APIs' usage.
    """

    def __init__(self, total_size: int, buffer_num: int,
                 **kwargs: Any) -> None:
        assert buffer_num > 0
        size = int(np.ceil(total_size / buffer_num))
        buffer_list = [ReplayBuffer(size, **kwargs) for _ in range(buffer_num)]
        super().__init__(buffer_list)


class PrioritizedVectorReplayBuffer(PrioritizedReplayBufferManager):
    """PrioritizedVectorReplayBuffer contains n PrioritizedReplayBuffer with
    same size.

    It is used for storing transition from different environments yet keeping the order
    of time.

    :param int total_size: the total size of PrioritizedVectorReplayBuffer.
    :param int buffer_num: the number of PrioritizedReplayBuffer it uses, which are
        under the same configuration.

    Other input arguments (alpha/beta/stack_num/ignore_obs_next/save_only_last_obs/
    sample_avail) are the same as :class:`~rltoolkit.data.PrioritizedReplayBuffer`.

    .. seealso::

        Please refer to :class:`~rltoolkit.data.ReplayBuffer` for other APIs' usage.
    """

    def __init__(self, total_size: int, buffer_num: int,
                 **kwargs: Any) -> None:
        assert buffer_num > 0
        size = int(np.ceil(total_size / buffer_num))
        buffer_list = [
            PrioritizedReplayBuffer(size, **kwargs) for _ in range(buffer_num)
        ]
        super().__init__(buffer_list)

    def set_beta(self, beta: float) -> None:
        for buffer in self.buffers:
            buffer.set_beta(beta)


class HERVectorReplayBuffer(HERReplayBufferManager):
    """HERVectorReplayBuffer contains n HERReplayBuffer with same size.

    It is used for storing transition from different environments yet keeping the order
    of time.

    :param int total_size: the total size of HERVectorReplayBuffer.
    :param int buffer_num: the number of HERReplayBuffer it uses, which are
        under the same configuration.

    Other input arguments are the same as :class:`~rltoolkit.data.HERReplayBuffer`.

    .. seealso::
        Please refer to :class:`~rltoolkit.data.ReplayBuffer` for other APIs' usage.
    """

    def __init__(self, total_size: int, buffer_num: int,
                 **kwargs: Any) -> None:
        assert buffer_num > 0
        size = int(np.ceil(total_size / buffer_num))
        buffer_list = [
            HERReplayBuffer(size, **kwargs) for _ in range(buffer_num)
        ]
        super().__init__(buffer_list)
