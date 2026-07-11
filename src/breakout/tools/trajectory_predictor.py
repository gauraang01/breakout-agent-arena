from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import pygame

from ..config import BALL, PADDLE


@dataclass(frozen=True)
class TrajectoryPrediction:
    impact_x_px: float
    target_x_px: float
    target_mm: float
    angled_hit: bool = False


class TrajectoryPredictor:
    """Deterministic reflection-geometry paddle controller."""

    def predict(
        self,
        ball_x: float,
        ball_y: float,
        ball_dx: float,
        ball_dy: float,
        strike_y: float,
        field_rect: pygame.Rect,
        paddle_min_center_x: float,
        paddle_max_center_x: float,
        track_length_mm: float,
        brick_rects: Sequence[pygame.Rect] = (),
    ) -> TrajectoryPrediction:
        impact_x = predict_reflected_x(
            ball_x=ball_x,
            ball_y=ball_y,
            ball_dx=ball_dx,
            ball_dy=ball_dy,
            strike_y=strike_y,
            field_rect=field_rect,
            brick_rects=brick_rects,
        )
        target_x = impact_x
        angled_hit = should_force_angled_hit(
            ball_x=ball_x,
            ball_y=ball_y,
            ball_dx=ball_dx,
            ball_dy=ball_dy,
            strike_y=strike_y,
            field_rect=field_rect,
            brick_rects=brick_rects,
        )
        if angled_hit:
            target_x = angled_paddle_center_x(
                impact_x=impact_x,
                field_center_x=field_rect.centerx,
                paddle_min_center_x=paddle_min_center_x,
                paddle_max_center_x=paddle_max_center_x,
            )

        target_mm = pixel_center_x_to_track_mm(
            target_x,
            paddle_min_center_x,
            paddle_max_center_x,
            track_length_mm,
        )
        return TrajectoryPrediction(
            impact_x_px=impact_x,
            target_x_px=target_x,
            target_mm=target_mm,
            angled_hit=angled_hit,
        )


def predict_reflected_x(
    ball_x: float,
    ball_y: float,
    ball_dx: float,
    ball_dy: float,
    strike_y: float,
    field_rect: pygame.Rect,
    brick_rects: Sequence[pygame.Rect],
) -> float:
    x = ball_x
    y = ball_y
    dx = ball_dx
    dy = ball_dy
    sim_bricks = list(brick_rects)
    
    speed = math.hypot(dx, dy)
    if speed < 1.0:
        return x
        
    step_s = BALL.radius / speed
    max_steps = 5000
    
    for _ in range(max_steps):
        if dy > 0 and y >= strike_y:
            return x

        x += dx * step_s
        y += dy * step_s

        if x - BALL.radius <= field_rect.left:
            x = field_rect.left + BALL.radius
            dx = abs(dx)
        elif x + BALL.radius >= field_rect.right:
            x = field_rect.right - BALL.radius
            dx = -abs(dx)

        if y - BALL.radius <= field_rect.top:
            y = field_rect.top + BALL.radius
            dy = abs(dy)

        ball_rect = pygame.Rect(
            int(x - BALL.radius),
            int(y - BALL.radius),
            int(BALL.radius * 2),
            int(BALL.radius * 2),
        )
        
        hit_idx = -1
        for i, b_rect in enumerate(sim_bricks):
            if ball_rect.colliderect(b_rect):
                hit_idx = i
                break
                
        if hit_idx != -1:
            hit_rect = sim_bricks.pop(hit_idx)
            dx_diff = x - hit_rect.centerx
            dy_diff = y - hit_rect.centery
            
            norm_x = abs(dx_diff) / (hit_rect.width / 2)
            norm_y = abs(dy_diff) / (hit_rect.height / 2)
            
            if norm_x > norm_y:
                dx *= -1
            else:
                dy *= -1

    return x


def pixel_center_x_to_track_mm(
    pixel_x: float,
    min_center_x: float,
    max_center_x: float,
    track_length_mm: float,
) -> float:
    if math.isclose(max_center_x, min_center_x):
        return 0.0
    normalized = (pixel_x - min_center_x) / (max_center_x - min_center_x)
    return _clamp(normalized, 0.0, 1.0) * track_length_mm


def should_force_angled_hit(
    ball_x: float,
    ball_y: float,
    ball_dx: float,
    ball_dy: float,
    strike_y: float,
    field_rect: pygame.Rect,
    brick_rects: Sequence[pygame.Rect],
) -> bool:
    if math.isclose(ball_dy, 0.0, abs_tol=0.0001):
        return False

    vertical_ratio = abs(ball_dx) / max(abs(ball_dy), 1.0)
    if vertical_ratio > 0.22:
        return False

    return not path_hits_brick_before_strike(
        ball_x=ball_x,
        ball_y=ball_y,
        ball_dx=ball_dx,
        ball_dy=ball_dy,
        strike_y=strike_y,
        field_rect=field_rect,
        brick_rects=brick_rects,
    )


def angled_paddle_center_x(
    impact_x: float,
    field_center_x: float,
    paddle_min_center_x: float,
    paddle_max_center_x: float,
) -> float:
    half_paddle = PADDLE.width / 2.0
    desired_collision_offset = 0.32
    if impact_x < field_center_x:
        target_x = impact_x - desired_collision_offset * half_paddle
    else:
        target_x = impact_x + desired_collision_offset * half_paddle
    return _clamp(target_x, paddle_min_center_x, paddle_max_center_x)


def path_hits_brick_before_strike(
    ball_x: float,
    ball_y: float,
    ball_dx: float,
    ball_dy: float,
    strike_y: float,
    field_rect: pygame.Rect,
    brick_rects: Sequence[pygame.Rect],
) -> bool:
    if not brick_rects or math.isclose(ball_dy, 0.0, abs_tol=0.0001):
        return False

    x = ball_x
    y = ball_y
    dx = ball_dx
    dy = ball_dy
    step_s = BALL.radius / max(math.hypot(dx, dy), 1.0)
    max_steps = 1200
    inflated_bricks = [rect.inflate(BALL.radius * 2, BALL.radius * 2) for rect in brick_rects]

    for _ in range(max_steps):
        if dy > 0 and y >= strike_y:
            return False

        x += dx * step_s
        y += dy * step_s

        if x - BALL.radius <= field_rect.left:
            x = field_rect.left + BALL.radius
            dx = abs(dx)
        elif x + BALL.radius >= field_rect.right:
            x = field_rect.right - BALL.radius
            dx = -abs(dx)

        if y - BALL.radius <= field_rect.top:
            y = field_rect.top + BALL.radius
            dy = abs(dy)

        if any(rect.collidepoint(x, y) for rect in inflated_bricks):
            return True

    return False


def _fold_reflected_x(x: float, min_x: float, max_x: float) -> float:
    width = max_x - min_x
    if width <= 0:
        return min_x

    period = width * 2.0
    folded = (x - min_x) % period
    if folded > width:
        folded = period - folded
    return min_x + folded


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
