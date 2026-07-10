import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from breakout.app.game import BreakoutGame
from breakout.app.state import PlayState
from breakout.gameplay.entities import create_bricks
import pygame

def evaluate_pattern(pattern: str, steps: int = 3000):
    game = BreakoutGame()
    
    # Initialize the specific map pattern
    game.pattern_idx = game.patterns.index(pattern)
    game.bricks = create_bricks(game.field_rect, pattern)
    game.harvest_training_data = False
    game._launch_ball()
    game.state = PlayState.PLAYING

    errors = []

    for _ in range(steps):
        game.frame += 1
        
        # 1. Ask the deterministic Math tool for the perfect answer
        game.force_predict_trajectory()
        true_target = game.prediction.target_mm
        
        # 2. Ask the Neural Network for its statistical guess
        neural_pred = game.neural_controller.predict_target_mm(
            ball_x=game.ball.x,
            ball_y=game.ball.y,
            ball_dx=game.ball.dx,
            ball_dy=game.ball.dy,
            brick_states=[b.alive for b in game.bricks],
        )
        nn_target = neural_pred.target_mm
        
        # Record the error
        errors.append(abs(true_target - nn_target))
        
        # Step physics forward
        game._update(1/60.0)

        # Handle board resets to keep simulating
        if game.state in {PlayState.LOST_BALL, PlayState.READY}:
            game._launch_ball()
            game.state = PlayState.PLAYING
        elif game.state in {PlayState.CLEARED, PlayState.GAME_OVER}:
            game._restart_game()
            game.bricks = create_bricks(game.field_rect, pattern)
            game._launch_ball()
            game.state = PlayState.PLAYING

    # Avoid pygame uninitialized errors from repeated quits
    if pygame.get_init():
        pygame.quit()
        
    if not errors:
        return 0.0
    return sum(errors) / len(errors)

def main():
    patterns = ["solid", "checkerboard", "diamond", "circle", "hollow"]
    print("Evaluating Neural Network against all maps (Lower MAE is better)...")
    print("-" * 60)
    for pat in patterns:
        mae = evaluate_pattern(pat, steps=4000)
        print(f"Map: {pat.ljust(15)} | Mean Absolute Error: {mae:>6.2f} mm")
    print("-" * 60)

if __name__ == "__main__":
    main()
