from __future__ import annotations

import pygame

from ..config import BALL, COLORS, SCREEN
from .state import PlayState, ControlMode
from .time_utils import format_optional_time, format_time


class GameRenderer:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font = pygame.font.Font(None, 22)
        self.large_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 18)

    def draw(self, game) -> None:
        self.screen.fill(COLORS["background"])
        
        is_mode_4 = game.control_mode == ControlMode.LLM_AGENT
        field_border_color = COLORS["agentic_purple"] if is_mode_4 else COLORS["field_border"]
        
        pygame.draw.rect(self.screen, COLORS["field"], game.field_rect, border_radius=4)
        pygame.draw.rect(
            self.screen,
            field_border_color,
            game.field_rect,
            width=2,
            border_radius=4,
        )

        self._draw_bricks(game)
        self._draw_paddle(game)
        pygame.draw.circle(
            self.screen,
            COLORS["ball"],
            (int(game.ball.x), int(game.ball.y)),
            BALL.radius,
        )
        self._draw_overlay(game)
        self._draw_sidebar(game)
        self._draw_state_message(game)
        pygame.display.flip()

    def _draw_bricks(self, game) -> None:
        for brick in game.bricks:
            if not brick.alive:
                continue
            pygame.draw.rect(self.screen, brick.color, brick.rect, border_radius=3)
            highlight = brick.rect.copy()
            highlight.height = 4
            pygame.draw.rect(self.screen, (255, 255, 255, 70), highlight, border_radius=3)

    def _draw_paddle(self, game) -> None:
        paddle_rect = game.paddle_rect()
        target_x = int(game.target_x())
        pygame.draw.line(
            self.screen,
            COLORS["paddle_target"],
            (target_x, paddle_rect.top - 14),
            (target_x, paddle_rect.bottom + 14),
            2,
        )
        pygame.draw.rect(self.screen, COLORS["paddle"], paddle_rect, border_radius=4)
        pygame.draw.rect(self.screen, (197, 244, 255), paddle_rect, width=2, border_radius=4)

    def _draw_overlay(self, game) -> None:
        overlay_rect = pygame.Rect(48, SCREEN.height - 236, 520, 188)
        pygame.draw.rect(self.screen, COLORS["overlay"], overlay_rect, border_radius=4)
        pygame.draw.rect(self.screen, COLORS["field_border"], overlay_rect, width=1, border_radius=4)

        paddle_rect = game.paddle_rect()
        predicted_x = game.prediction.impact_x_px if game.prediction else game.ball.x
        target_x = game.prediction.target_x_px if game.prediction else game.target_x()
        angled = "yes" if game.prediction and game.prediction.angled_hit else "no"
        neural_status = "loaded" if game.neural_controller.available else game.neural_controller.load_error
        lines = [
            f"Mode: {game.control_mode.value}  (1 manual, 2 neural, 3 agent)",
            f"Time: {format_time(game.elapsed_time_s)} | Finish: {format_optional_time(game.final_time_s)}",
            f"Ball X,Y: {game.ball.x:7.1f}, {game.ball.y:7.1f}",
            f"Ball dX,dY: {game.ball.dx:7.1f}, {game.ball.dy:7.1f} px/s",
            f"Paddle: {paddle_rect.centerx:6.1f}px | {game.vhal.position_mm:6.1f}mm",
            f"Target: {game.vhal.target_mm:6.1f}mm | V: {game.vhal.velocity_mm_s:7.1f}mm/s",
            f"Impact X: {predicted_x:7.1f}px | Target X: {target_x:7.1f}px",
            f"Forced angled hit: {angled}",
            f"Neural model: {neural_status}",
            f"Vmax: {game.vhal.max_velocity_mm_s:.0f}mm/s | Amax: {game.vhal.max_acceleration_mm_s2:.0f}mm/s2",
        ]
        for index, line in enumerate(lines):
            color = COLORS["text"] if index < 3 else COLORS["muted_text"]
            surface = self.small_font.render(line, True, color)
            self.screen.blit(surface, (overlay_rect.left + 14, overlay_rect.top + 10 + index * 18))

        status = (
            f"Score {game.score}   Lives {game.lives}   Time {format_time(game.elapsed_time_s)}   "
            f"Finish {format_optional_time(game.final_time_s)}   State {game.state.value}   "
            f"Mode {game.control_mode.value}"
        )
        surface = self.font.render(status, True, COLORS["text"])
        self.screen.blit(surface, (game.field_rect.left, game.field_rect.top - 26))

    def _draw_state_message(self, game) -> None:
        messages = {
            PlayState.READY: "Press Space to Launch",
            PlayState.LOST_BALL: "Ball Lost - Press Space",
            PlayState.CLEARED: "Stage Clear - Press Space",
            PlayState.GAME_OVER: "Game Over - Press Space",
        }
        message = messages.get(game.state)
        if not message:
            return

        surface = self.large_font.render(message, True, COLORS["text"])
        shadow = self.large_font.render(message, True, (0, 0, 0))
        rect = surface.get_rect(center=(game.field_rect.centerx, game.field_rect.centery + 60))
        self.screen.blit(shadow, rect.move(2, 2))
        self.screen.blit(surface, rect)

    def _draw_sidebar(self, game) -> None:
        sidebar_rect = game.sidebar_rect
        pygame.draw.rect(self.screen, COLORS["background"], sidebar_rect)
        
        is_mode_4 = game.control_mode == ControlMode.LLM_AGENT
        sidebar_border_color = COLORS["agentic_purple"] if is_mode_4 else COLORS["field_border"]
        
        pygame.draw.line(self.screen, sidebar_border_color, sidebar_rect.topleft, sidebar_rect.bottomleft, 2)
        
        title_color = COLORS["agentic_purple"] if is_mode_4 else COLORS["muted_text"]
        title = self.large_font.render("Diagnostic UI", True, title_color)
        self.screen.blit(title, (sidebar_rect.left + 24, sidebar_rect.top + 32))
        
        y_offset = 96
        if is_mode_4:
            for trace in game.llm_controller.traces:
                surface = self.small_font.render(trace, True, COLORS["agentic_purple"])
                self.screen.blit(surface, (sidebar_rect.left + 24, sidebar_rect.top + y_offset))
                y_offset += 24
