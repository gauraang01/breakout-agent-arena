from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import pygame

from .agent import MathematicalAgent, Prediction
from .config import BALL, BRICK_COLORS, BRICKS, COLORS, PADDLE, SCREEN, VHAL
from .data_logger import TrainingDataLogger
from .vhal import VirtualPaddleHAL


class PlayState(Enum):
    READY = "ready"
    PLAYING = "playing"
    LOST_BALL = "lost_ball"
    CLEARED = "cleared"
    GAME_OVER = "game_over"


class ControlMode(Enum):
    MANUAL = "manual"
    MATHEMATICAL_AGENT = "mathematical_agent"


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


class BreakoutGame:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Breakout V-HAL - Stage 2 Mathematical Agent")
        self.screen = pygame.display.set_mode((SCREEN.width, SCREEN.height))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 22)
        self.large_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 18)

        self.field_rect = pygame.Rect(32, 32, SCREEN.width - 64, SCREEN.height - 64)
        self.paddle_y = self.field_rect.bottom - PADDLE.y_offset
        self.paddle_min_center_x = self.field_rect.left + PADDLE.width / 2
        self.paddle_max_center_x = self.field_rect.right - PADDLE.width / 2

        self.vhal = VirtualPaddleHAL.centered(
            track_length_mm=VHAL.track_length_mm,
            max_velocity_mm_s=VHAL.max_velocity_mm_s,
            max_acceleration_mm_s2=VHAL.max_acceleration_mm_s2,
        )
        self.ball = self._new_attached_ball()
        self.bricks = self._create_bricks()
        self.agent = MathematicalAgent()
        self.prediction: Prediction | None = None
        self.control_mode = ControlMode.MANUAL
        self.frame = 0
        self.training_logger = TrainingDataLogger(Path("training_data.csv"))
        self.state = PlayState.READY
        self.score = 0
        self.lives = 3
        self.running = True

    def run(self) -> None:
        try:
            while self.running:
                dt_s = min(self.clock.tick(SCREEN.fps) / 1000.0, 1.0 / 30.0)
                self.frame += 1
                self._handle_events()
                self._handle_input()
                self._update(dt_s)
                self._draw()
        finally:
            self.training_logger.close()
            pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self._handle_space()
                elif event.key == pygame.K_1:
                    self.control_mode = ControlMode.MANUAL
                    self.prediction = None
                elif event.key == pygame.K_2:
                    self.control_mode = ControlMode.MATHEMATICAL_AGENT

    def _handle_space(self) -> None:
        if self.state in {PlayState.READY, PlayState.LOST_BALL}:
            self._launch_ball()
            self.state = PlayState.PLAYING
        elif self.state in {PlayState.CLEARED, PlayState.GAME_OVER}:
            self._restart_game()

    def _handle_input(self) -> None:
        if self.control_mode == ControlMode.MATHEMATICAL_AGENT:
            self._handle_agent_input()
            return

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and not keys[pygame.K_RIGHT]:
            self.vhal.set_target_mm(0.0)
        elif keys[pygame.K_RIGHT] and not keys[pygame.K_LEFT]:
            self.vhal.set_target_mm(VHAL.track_length_mm)
        elif self.state == PlayState.PLAYING:
            self.vhal.hold_position()

    def _handle_agent_input(self) -> None:
        self.prediction = self.agent.predict(
            ball_x=self.ball.x,
            ball_y=self.ball.y,
            ball_dx=self.ball.dx,
            ball_dy=self.ball.dy,
            strike_y=self.paddle_y - BALL.radius,
            field_rect=self.field_rect,
            paddle_min_center_x=self.paddle_min_center_x,
            paddle_max_center_x=self.paddle_max_center_x,
            track_length_mm=VHAL.track_length_mm,
            brick_rects=[brick.rect for brick in self.bricks if brick.alive],
        )
        self.vhal.set_target_mm(self.prediction.target_mm)

    def _update(self, dt_s: float) -> None:
        self.vhal.update(dt_s)
        if self.state in {PlayState.READY, PlayState.LOST_BALL}:
            self._attach_ball_to_paddle()
            return

        if self.state != PlayState.PLAYING:
            return

        self.ball.x += self.ball.dx * dt_s
        self.ball.y += self.ball.dy * dt_s
        self._resolve_wall_collisions()
        self._resolve_paddle_collision()
        self._resolve_brick_collision()

        if self.ball.y - BALL.radius > self.field_rect.bottom:
            self._lose_ball()
        elif all(not brick.alive for brick in self.bricks):
            self.state = PlayState.CLEARED

        self._log_training_sample()

    def _resolve_wall_collisions(self) -> None:
        if self.ball.x - BALL.radius <= self.field_rect.left:
            self.ball.x = self.field_rect.left + BALL.radius
            self.ball.dx = abs(self.ball.dx)
        elif self.ball.x + BALL.radius >= self.field_rect.right:
            self.ball.x = self.field_rect.right - BALL.radius
            self.ball.dx = -abs(self.ball.dx)

        if self.ball.y - BALL.radius <= self.field_rect.top:
            self.ball.y = self.field_rect.top + BALL.radius
            self.ball.dy = abs(self.ball.dy)

    def _resolve_paddle_collision(self) -> None:
        paddle_rect = self._paddle_rect()
        if self.ball.dy <= 0 or not self.ball.rect.colliderect(paddle_rect):
            return

        self.ball.y = paddle_rect.top - BALL.radius
        offset = (self.ball.x - paddle_rect.centerx) / (PADDLE.width / 2)
        offset = max(-1.0, min(1.0, offset))
        angle = math.radians(90 - offset * 58)
        speed = max(BALL.speed_px_s, math.hypot(self.ball.dx, self.ball.dy) * 1.01)
        self.ball.dx = math.cos(angle) * speed
        self.ball.dy = -abs(math.sin(angle) * speed)

    def _resolve_brick_collision(self) -> None:
        ball_rect = self.ball.rect
        for brick in self.bricks:
            if not brick.alive or not ball_rect.colliderect(brick.rect):
                continue

            brick.alive = False
            self.score += 100

            overlap_left = ball_rect.right - brick.rect.left
            overlap_right = brick.rect.right - ball_rect.left
            overlap_top = ball_rect.bottom - brick.rect.top
            overlap_bottom = brick.rect.bottom - ball_rect.top
            min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)

            if min_overlap in (overlap_left, overlap_right):
                self.ball.dx *= -1
            else:
                self.ball.dy *= -1
            return

    def _lose_ball(self) -> None:
        self.lives -= 1
        if self.lives <= 0:
            self.state = PlayState.GAME_OVER
        else:
            self.state = PlayState.LOST_BALL
        self.vhal.hold_position()
        self.ball = self._new_attached_ball()

    def _restart_game(self) -> None:
        self.score = 0
        self.lives = 3
        self.bricks = self._create_bricks()
        self.vhal = VirtualPaddleHAL.centered(
            track_length_mm=VHAL.track_length_mm,
            max_velocity_mm_s=VHAL.max_velocity_mm_s,
            max_acceleration_mm_s2=VHAL.max_acceleration_mm_s2,
        )
        self.ball = self._new_attached_ball()
        self.state = PlayState.READY
        self.prediction = None

    def _launch_ball(self) -> None:
        angle = math.radians(random.choice([58, 64, 116, 122]))
        self.ball.dx = math.cos(angle) * BALL.speed_px_s
        self.ball.dy = -abs(math.sin(angle) * BALL.speed_px_s)

    def _new_attached_ball(self) -> BallState:
        paddle_rect = self._paddle_rect()
        return BallState(
            x=float(paddle_rect.centerx),
            y=float(paddle_rect.top - BALL.radius - 2),
            dx=0.0,
            dy=0.0,
        )

    def _attach_ball_to_paddle(self) -> None:
        paddle_rect = self._paddle_rect()
        self.ball.x = float(paddle_rect.centerx)
        self.ball.y = float(paddle_rect.top - BALL.radius - 2)
        self.ball.dx = 0.0
        self.ball.dy = 0.0

    def _paddle_rect(self) -> pygame.Rect:
        center_x = self.vhal.position_to_pixel_center(
            self.paddle_min_center_x,
            self.paddle_max_center_x,
        )
        return pygame.Rect(
            int(center_x - PADDLE.width / 2),
            self.paddle_y,
            PADDLE.width,
            PADDLE.height,
        )

    def _target_x(self) -> float:
        return self.vhal.target_to_pixel_center(
            self.paddle_min_center_x,
            self.paddle_max_center_x,
        )

    def _log_training_sample(self) -> None:
        if (
            self.control_mode != ControlMode.MATHEMATICAL_AGENT
            or self.state != PlayState.PLAYING
            or self.prediction is None
        ):
            return

        self.training_logger.log(
            frame=self.frame,
            mode=self.control_mode.value,
            ball_x=self.ball.x,
            ball_y=self.ball.y,
            ball_dx=self.ball.dx,
            ball_dy=self.ball.dy,
            correct_paddle_x_px=self.prediction.target_x_px,
            correct_paddle_mm=self.prediction.target_mm,
            actual_paddle_mm=self.vhal.position_mm,
        )

    def _create_bricks(self) -> list[Brick]:
        total_width = BRICKS.columns * BRICKS.width + (BRICKS.columns - 1) * BRICKS.gap
        left = self.field_rect.centerx - total_width // 2
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

    def _draw(self) -> None:
        self.screen.fill(COLORS["background"])
        pygame.draw.rect(self.screen, COLORS["field"], self.field_rect, border_radius=4)
        pygame.draw.rect(self.screen, COLORS["field_border"], self.field_rect, width=2, border_radius=4)

        self._draw_bricks()
        self._draw_paddle()
        pygame.draw.circle(
            self.screen,
            COLORS["ball"],
            (int(self.ball.x), int(self.ball.y)),
            BALL.radius,
        )
        self._draw_overlay()
        self._draw_state_message()
        pygame.display.flip()

    def _draw_bricks(self) -> None:
        for brick in self.bricks:
            if not brick.alive:
                continue
            pygame.draw.rect(self.screen, brick.color, brick.rect, border_radius=3)
            highlight = brick.rect.copy()
            highlight.height = 4
            pygame.draw.rect(self.screen, (255, 255, 255, 70), highlight, border_radius=3)

    def _draw_paddle(self) -> None:
        paddle_rect = self._paddle_rect()
        target_x = int(self._target_x())
        pygame.draw.line(
            self.screen,
            COLORS["paddle_target"],
            (target_x, paddle_rect.top - 14),
            (target_x, paddle_rect.bottom + 14),
            2,
        )
        pygame.draw.rect(self.screen, COLORS["paddle"], paddle_rect, border_radius=4)
        pygame.draw.rect(self.screen, (197, 244, 255), paddle_rect, width=2, border_radius=4)

    def _draw_overlay(self) -> None:
        overlay_rect = pygame.Rect(48, SCREEN.height - 190, 430, 142)
        pygame.draw.rect(self.screen, COLORS["overlay"], overlay_rect, border_radius=4)
        pygame.draw.rect(self.screen, COLORS["field_border"], overlay_rect, width=1, border_radius=4)

        paddle_rect = self._paddle_rect()
        predicted_x = self.prediction.impact_x_px if self.prediction else self.ball.x
        target_x = self.prediction.target_x_px if self.prediction else self._target_x()
        angled = "yes" if self.prediction and self.prediction.angled_hit else "no"
        lines = [
            f"Mode: {self.control_mode.value}  (1 manual, 2 agent)",
            f"Ball X,Y: {self.ball.x:7.1f}, {self.ball.y:7.1f}",
            f"Ball dX,dY: {self.ball.dx:7.1f}, {self.ball.dy:7.1f} px/s",
            f"Paddle: {paddle_rect.centerx:6.1f}px | {self.vhal.position_mm:6.1f}mm",
            f"Target: {self.vhal.target_mm:6.1f}mm | V: {self.vhal.velocity_mm_s:7.1f}mm/s",
            f"Impact X: {predicted_x:7.1f}px | Target X: {target_x:7.1f}px",
            f"Forced angled hit: {angled}",
            f"Vmax: {self.vhal.max_velocity_mm_s:.0f}mm/s | Amax: {self.vhal.max_acceleration_mm_s2:.0f}mm/s2",
        ]
        for index, line in enumerate(lines):
            color = COLORS["text"] if index < 3 else COLORS["muted_text"]
            surface = self.small_font.render(line, True, color)
            self.screen.blit(surface, (overlay_rect.left + 14, overlay_rect.top + 10 + index * 18))

        status = (
            f"Score {self.score}   Lives {self.lives}   State {self.state.value}   "
            f"Mode {self.control_mode.value}"
        )
        surface = self.font.render(status, True, COLORS["text"])
        self.screen.blit(surface, (self.field_rect.left, self.field_rect.top - 26))

    def _draw_state_message(self) -> None:
        messages = {
            PlayState.READY: "Press Space to Launch",
            PlayState.LOST_BALL: "Ball Lost - Press Space",
            PlayState.CLEARED: "Stage Clear - Press Space",
            PlayState.GAME_OVER: "Game Over - Press Space",
        }
        message = messages.get(self.state)
        if not message:
            return

        surface = self.large_font.render(message, True, COLORS["text"])
        shadow = self.large_font.render(message, True, (0, 0, 0))
        rect = surface.get_rect(center=(self.field_rect.centerx, self.field_rect.centery + 60))
        self.screen.blit(shadow, rect.move(2, 2))
        self.screen.blit(surface, rect)


def main() -> None:
    BreakoutGame().run()
