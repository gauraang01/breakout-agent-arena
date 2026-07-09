from __future__ import annotations

import math
import random
from pathlib import Path

import pygame

from ..controllers.manual import ManualController
from ..controllers.mathematical import MathematicalController, MathematicalPrediction
from ..controllers.neural import NeuralNetworkController, NeuralPrediction
from ..controllers.llm import LLMAgentController
from ..config import BALL, GAMEPLAY, PADDLE, SCREEN, VHAL
from ..gameplay.collisions import (
    resolve_brick_collision,
    resolve_paddle_collision,
    resolve_wall_collisions,
)
from ..gameplay.entities import BallState, Brick, create_bricks
from ..hardware.vhal import VirtualPaddleHAL
from ..training.data_logger import TrainingDataLogger
from .renderer import GameRenderer
from .state import ControlMode, PlayState


class BreakoutGame:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Breakout V-HAL - Stage 3 Neural Controller")
        self.screen = pygame.display.set_mode((SCREEN.width, SCREEN.height))
        self.clock = pygame.time.Clock()
        self.renderer = GameRenderer(self.screen)

        self.field_rect = pygame.Rect(32, 32, SCREEN.arena_width - 64, SCREEN.height - 64)
        self.sidebar_rect = pygame.Rect(SCREEN.arena_width, 0, SCREEN.sidebar_width, SCREEN.height)
        self.paddle_y = self.field_rect.bottom - PADDLE.y_offset
        self.paddle_min_center_x = self.field_rect.left + PADDLE.width / 2
        self.paddle_max_center_x = self.field_rect.right - PADDLE.width / 2

        self.vhal = self._new_vhal()
        self.ball = self._new_attached_ball()
        self.bricks: list[Brick] = create_bricks(self.field_rect)

        self.manual_controller = ManualController()
        self.mathematical_controller = MathematicalController()
        self.neural_controller = NeuralNetworkController()
        self.llm_controller = LLMAgentController(self.mathematical_controller)
        self.llm_acted_this_fall = False
        
        self.prediction: MathematicalPrediction | None = None
        self.neural_prediction: NeuralPrediction | None = None
        self.training_logger = TrainingDataLogger(Path("training_data.csv"))

        self.control_mode = ControlMode.MANUAL
        self.state = PlayState.READY
        self.frame = 0
        self.score = 0
        self.lives = GAMEPLAY.lives
        self.elapsed_time_s = 0.0
        self.final_time_s: float | None = None
        self.running = True

    def run(self) -> None:
        try:
            while self.running:
                dt_s = min(self.clock.tick(SCREEN.fps) / 1000.0, 1.0 / 30.0)
                self.frame += 1
                self._handle_events()
                self._handle_input()
                self._update(dt_s)
                self.renderer.draw(self)
        finally:
            self.training_logger.close()
            pygame.quit()

    def paddle_rect(self) -> pygame.Rect:
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

    def target_x(self) -> float:
        return self.vhal.target_to_pixel_center(
            self.paddle_min_center_x,
            self.paddle_max_center_x,
        )

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event.key)

    def _handle_keydown(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self.running = False
        elif key == pygame.K_SPACE:
            self._handle_space()
        elif key == pygame.K_1:
            self.control_mode = ControlMode.MANUAL
            self.prediction = None
            self.neural_prediction = None
        elif key == pygame.K_2:
            self.control_mode = ControlMode.MATHEMATICAL_CONTROLLER
            self.neural_prediction = None
        elif key == pygame.K_3:
            self.control_mode = ControlMode.NEURAL_NETWORK
            self.prediction = None
        elif key == pygame.K_4:
            self.control_mode = ControlMode.LLM_AGENT
            self.prediction = None
            self.neural_prediction = None
            self.llm_controller.clear_traces()

    def _handle_space(self) -> None:
        if self.state in {PlayState.READY, PlayState.LOST_BALL}:
            self._launch_ball()
            self.state = PlayState.PLAYING
        elif self.state in {PlayState.CLEARED, PlayState.GAME_OVER}:
            self._restart_game()

    def _handle_input(self) -> None:
        if self.control_mode == ControlMode.MATHEMATICAL_CONTROLLER:
            self._handle_mathematical_controller_input()
            return
        if self.control_mode == ControlMode.NEURAL_NETWORK:
            self._handle_neural_controller_input()
            return
        if self.control_mode == ControlMode.LLM_AGENT:
            self._handle_llm_agent_input()
            return
        self._handle_manual_controller_input()

    def _handle_manual_controller_input(self) -> None:
        self.manual_controller.update_target(self.vhal, self.state)

    def _handle_mathematical_controller_input(self) -> None:
        self.neural_prediction = None
        self.prediction = self.mathematical_controller.predict(
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

    def _handle_neural_controller_input(self) -> None:
        self.prediction = None
        self.neural_prediction = self.neural_controller.predict_target_mm(
            ball_x=self.ball.x,
            ball_y=self.ball.y,
            ball_dx=self.ball.dx,
            ball_dy=self.ball.dy,
        )
        self.vhal.set_target_mm(self.neural_prediction.target_mm)

    def _handle_llm_agent_input(self) -> None:
        if self.ball.dy < 0:
            self.llm_acted_this_fall = False
            return
            
        if self.ball.dy > 0 and self.ball.y > 400 and not self.llm_acted_this_fall:
            self.llm_acted_this_fall = True
            
            def log_trace(msg: str):
                self.llm_controller.traces.append(msg)
                
            def draw_update():
                self.renderer.draw(self)
                pygame.event.pump()
                
            target_mm = self.llm_controller.predict_target_mm(
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
                log_callback=log_trace,
                draw_callback=draw_update
            )
            self.vhal.set_target_mm(target_mm)

    def _update(self, dt_s: float) -> None:
        self.vhal.update(dt_s)
        if self.state in {PlayState.READY, PlayState.LOST_BALL}:
            self._attach_ball_to_paddle()
            return

        if self.state != PlayState.PLAYING:
            return

        self.elapsed_time_s += dt_s
        self.ball.x += self.ball.dx * dt_s
        self.ball.y += self.ball.dy * dt_s

        resolve_wall_collisions(self.ball, self.field_rect)
        resolve_paddle_collision(self.ball, self.paddle_rect())
        self.score += resolve_brick_collision(self.ball, self.bricks)

        if self.ball.y - BALL.radius > self.field_rect.bottom:
            self._lose_ball()
        elif all(not brick.alive for brick in self.bricks):
            self.state = PlayState.CLEARED
            self._finish_run()

        self._log_training_sample()

    def _lose_ball(self) -> None:
        self.lives -= 1
        if self.lives <= 0:
            self.state = PlayState.GAME_OVER
            self._finish_run()
        else:
            self.state = PlayState.LOST_BALL
        self.vhal.hold_position()
        self.ball = self._new_attached_ball()

    def _restart_game(self) -> None:
        self.score = 0
        self.lives = GAMEPLAY.lives
        self.elapsed_time_s = 0.0
        self.final_time_s = None
        self.bricks = create_bricks(self.field_rect)
        self.vhal = self._new_vhal()
        self.ball = self._new_attached_ball()
        self.state = PlayState.READY
        self.prediction = None
        self.neural_prediction = None

    def _finish_run(self) -> None:
        if self.final_time_s is None:
            self.final_time_s = self.elapsed_time_s

    def _launch_ball(self) -> None:
        angle = math.radians(random.choice([58, 64, 116, 122]))
        self.ball.dx = math.cos(angle) * BALL.speed_px_s
        self.ball.dy = -abs(math.sin(angle) * BALL.speed_px_s)

    def _new_vhal(self) -> VirtualPaddleHAL:
        return VirtualPaddleHAL.centered(
            track_length_mm=VHAL.track_length_mm,
            max_velocity_mm_s=VHAL.max_velocity_mm_s,
            max_acceleration_mm_s2=VHAL.max_acceleration_mm_s2,
        )

    def _new_attached_ball(self) -> BallState:
        paddle_rect = self.paddle_rect()
        return BallState(
            x=float(paddle_rect.centerx),
            y=float(paddle_rect.top - BALL.radius - 2),
            dx=0.0,
            dy=0.0,
        )

    def _attach_ball_to_paddle(self) -> None:
        paddle_rect = self.paddle_rect()
        self.ball.x = float(paddle_rect.centerx)
        self.ball.y = float(paddle_rect.top - BALL.radius - 2)
        self.ball.dx = 0.0
        self.ball.dy = 0.0

    def _log_training_sample(self) -> None:
        if (
            self.control_mode != ControlMode.MATHEMATICAL_CONTROLLER
            or self.state != PlayState.PLAYING
            or self.prediction is None
        ):
            return

        self.training_logger.log(
            frame=self.frame,
            ball_x=self.ball.x,
            ball_y=self.ball.y,
            ball_dx=self.ball.dx,
            ball_dy=self.ball.dy,
            target_paddle_mm=self.prediction.target_mm,
        )


def main() -> None:
    BreakoutGame().run()
