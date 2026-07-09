from __future__ import annotations


def build_paddle_mlp():
    import torch.nn as nn

    return nn.Sequential(
        nn.Linear(4, 64),
        nn.ReLU(),
        nn.Linear(64, 64),
        nn.ReLU(),
        nn.Linear(64, 1),
    )
