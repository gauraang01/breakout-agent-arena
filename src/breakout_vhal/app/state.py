from __future__ import annotations

from enum import Enum


class PlayState(Enum):
    READY = "ready"
    PLAYING = "playing"
    LOST_BALL = "lost_ball"
    CLEARED = "cleared"
    GAME_OVER = "game_over"


class ControlMode(Enum):
    MANUAL = "manual"
    MATHEMATICAL_CONTROLLER = "mathematical_controller"
    NEURAL_NETWORK = "neural_network_controller"
