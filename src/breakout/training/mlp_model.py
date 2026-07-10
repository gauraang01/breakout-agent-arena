from __future__ import annotations
import torch.nn as nn

def build_paddle_mlp():
    return nn.Sequential(
        nn.Linear(52, 256),
        nn.ReLU(),
        nn.Linear(256, 256),
        nn.ReLU(),
        nn.Linear(256, 256),
        nn.ReLU(),
        nn.Linear(256, 1),
    )
