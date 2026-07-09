from __future__ import annotations

from dataclasses import dataclass

import pygame

from ..config import BALL, BRICK_COLORS, BRICKS


@dataclass
class Brick:
    rect: pygame.Rect
    color: tuple[int, int, int]
    alive: bool = True


@dataclass
class BallState:
    x: float
    y: float
    dx: float
    dy: float

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(
            int(self.x - BALL.radius),
            int(self.y - BALL.radius),
            BALL.radius * 2,
            BALL.radius * 2,
        )


def create_bricks(field_rect: pygame.Rect) -> list[Brick]:
    total_width = BRICKS.columns * BRICKS.width + (BRICKS.columns - 1) * BRICKS.gap
    left = field_rect.centerx - total_width // 2
    bricks: list[Brick] = []
    for row in range(BRICKS.rows):
        for column in range(BRICKS.columns):
            rect = pygame.Rect(
                left + column * (BRICKS.width + BRICKS.gap),
                BRICKS.top + row * (BRICKS.height + BRICKS.gap),
                BRICKS.width,
                BRICKS.height,
            )
            bricks.append(Brick(rect=rect, color=BRICK_COLORS[row % len(BRICK_COLORS)]))
    return bricks
