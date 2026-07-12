import torch
import torch.nn as nn
import torch.nn.functional as F

class BreakoutDensityMLP(nn.Module):
    def __init__(self):
        super().__init__()
        # Input features: [ball_x, ball_y, ball_dx, ball_dy, left_d, center_d, right_d] (7)
        self.fc = nn.Sequential(
            nn.Linear(7, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1) # Output: Strategic Paddle Offset
        )

    def forward(self, x):
        # Normalize the coordinates and velocities so the network doesn't saturate
        x_norm = x.clone()
        x_norm[:, 0] /= 1000.0  # ball_x
        x_norm[:, 1] /= 1000.0  # ball_y
        x_norm[:, 2] /= 400.0   # ball_dx
        x_norm[:, 3] /= 400.0   # ball_dy
        # left_d, center_d, right_d are already 0.0 to 1.0

        return self.fc(x_norm)

def build_paddle_mlp():
    return BreakoutDensityMLP()
