import torch
import torch.nn as nn
import torch.nn.functional as F

class BreakoutSpatialCNN(nn.Module):
    def __init__(self):
        super().__init__()
        # 2 Channels: Channel 0 is Bricks, Channel 1 is the Ball
        self.conv = nn.Sequential(
            nn.Conv2d(2, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2), # 30x25 -> 15x12
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2), # 15x12 -> 7x6
            nn.Flatten()
        )
        self.fc = nn.Sequential(
            nn.Linear(32 * 7 * 6 + 2, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1) # Output: Strategic Paddle Offset (-50 to +50)
        )

    def forward(self, x_raw):
        # x_raw is (Batch, 52) - Unscaled raw features!
        batch_size = x_raw.size(0)
        grids = torch.zeros((batch_size, 2, 30, 25), device=x_raw.device)
        
        ball_x = x_raw[:, 0]
        ball_y = x_raw[:, 1]
        velocities = x_raw[:, 2:4] / 400.0  # Normalize dx, dy
        
        # Channel 0: Bricks (scaled up to look like the real 2D game board)
        bricks = x_raw[:, 4:].view(-1, 1, 6, 8)
        bricks_upscaled = F.interpolate(bricks, size=(12, 24), mode='nearest')
        grids[:, 0:1, 3:15, 0:24] = bricks_upscaled
        
        # Channel 1: Ball position plotted on the 2D grid
        cols = (ball_x / 500.0 * 24).clamp(0, 24).long()
        rows = (ball_y / 600.0 * 29).clamp(0, 29).long()
        
        batch_indices = torch.arange(batch_size, device=x_raw.device)
        grids[batch_indices, 1, rows, cols] = 1.0
        
        c = self.conv(grids)
        return self.fc(torch.cat([c, velocities], dim=1))

def build_paddle_mlp():
    return BreakoutSpatialCNN()
