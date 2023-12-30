import random

import numpy as np


def uniform_float_sample(start: float, end: float, sample_size: int, round_off=2) -> list[float]:  # noqa: E501
    sampled_values = set()

    start = float(start)
    end = float(end)

    while len(sampled_values) < sample_size:
        value = np.round(random.uniform(start, end), round_off)
        if value not in sampled_values:
            sampled_values.add(value)

    return list(sampled_values)
