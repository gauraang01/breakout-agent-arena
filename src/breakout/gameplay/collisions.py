from __future__ import annotations

import math

import pygame

from ..config import BALL, PADDLE
from .entities import BallState, Brick


def resolve_wall_collisions(ball: BallState, field_rect: pygame.Rect) -> None:
    if ball.x - BALL.radius <= field_rect.left:
        ball.x = field_rect.left + BALL.radius
        ball.dx = abs(ball.dx)
    elif ball.x + BALL.radius >= field_rect.right:
        ball.x = field_rect.right - BALL.radius
        ball.dx = -abs(ball.dx)

    if ball.y - BALL.radius <= field_rect.top:
        ball.y = field_rect.top + BALL.radius
        ball.dy = abs(ball.dy)


def resolve_paddle_collision(ball: BallState, paddle_rect: pygame.Rect) -> None:
    if ball.dy <= 0 or not ball.rect.colliderect(paddle_rect):
        return

    ball.y = paddle_rect.top - BALL.radius
    offset = (ball.x - paddle_rect.centerx) / (PADDLE.width / 2)
    offset = max(-1.0, min(1.0, offset))
    angle = math.radians(90 - offset * 58)
    speed = max(BALL.speed_px_s, math.hypot(ball.dx, ball.dy) * 1.01)
    ball.dx = math.cos(angle) * speed
    ball.dy = -abs(math.sin(angle) * speed)


def resolve_brick_collision(ball: BallState, bricks: list[Brick]) -> int:
    ball_rect = ball.rect
    for brick in bricks:
        if not brick.alive or not ball_rect.colliderect(brick.rect):
            continue

        brick.alive = False

        overlap_left = ball_rect.right - brick.rect.left
        overlap_right = brick.rect.right - ball_rect.left
        overlap_top = ball_rect.bottom - brick.rect.top
        overlap_bottom = brick.rect.bottom - ball_rect.top
        min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)

        if min_overlap in (overlap_left, overlap_right):
            ball.dx *= -1
        else:
            ball.dy *= -1
        return 100

    return 0
