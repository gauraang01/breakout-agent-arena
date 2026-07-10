from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScreenConfig:
    width: int = 1440
    height: int = 900
    fps: int = 60
    arena_width: int = 990
    sidebar_width: int = 450


@dataclass(frozen=True)
class VHALConfig:
    track_length_mm: float = 500.0
    max_velocity_mm_s: float = 320.0
    max_acceleration_mm_s2: float = 1000.0


@dataclass(frozen=True)
class PaddleConfig:
    width: int = 148
    height: int = 20
    y_offset: int = 68


@dataclass(frozen=True)
class BallConfig:
    radius: int = 10
    speed_px_s: float = 300.0


@dataclass(frozen=True)
class BrickConfig:
    rows: int = 6
    columns: int = 8
    width: int = 96
    height: int = 26
    gap: int = 12
    top: int = 92


@dataclass(frozen=True)
class GameplayConfig:
    lives: int = 1


@dataclass(frozen=True)
class LLMConfig:
    model: str = "qwen2.5:1.5b"


SCREEN = ScreenConfig()
VHAL = VHALConfig()
PADDLE = PaddleConfig()
BALL = BallConfig()
BRICKS = BrickConfig()
GAMEPLAY = GameplayConfig()
LLM = LLMConfig()


COLORS = {
    "background": (12, 14, 18),
    "field": (20, 24, 31),
    "field_border": (67, 75, 91),
    "text": (229, 233, 240),
    "muted_text": (151, 161, 178),
    "paddle": (76, 201, 240),
    "paddle_target": (248, 197, 85),
    "ball": (248, 248, 242),
    "overlay": (28, 33, 42),
    "danger": (255, 97, 109),
    "agentic_purple": (155, 89, 182),
}

BRICK_COLORS = [
    (239, 83, 80),
    (255, 167, 38),
    (255, 213, 79),
    (102, 187, 106),
    (38, 198, 218),
    (126, 87, 194),
]
