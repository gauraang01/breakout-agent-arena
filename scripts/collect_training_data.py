from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from breakout.app.game import BreakoutGame
from breakout.app.state import ControlMode, PlayState
from breakout.training.data_logger import TrainingDataLogger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Stage 3 neural training data.")
    parser.add_argument("--rows", type=int, default=20000, help="Rows to collect.")
    parser.add_argument(
        "--interval",
        type=int,
        default=4,
        help="Log every N frames while ball_dy > 0.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "training_data.csv",
        help="CSV output path.",
    )
    parser.add_argument(
        "--dt",
        type=float,
        default=1 / 60,
        help="Simulation timestep in seconds.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    game = BreakoutGame()
    game.training_logger.close()
    game.training_logger = TrainingDataLogger(args.output, sample_interval_frames=args.interval)
    game.harvest_training_data = True
    game._launch_ball()
    game.state = PlayState.PLAYING

    try:
        while game.training_logger.rows_written < args.rows:
            game.frame += 1
            game.force_predict_trajectory()
            game._update(args.dt)

            if game.state in {PlayState.LOST_BALL, PlayState.READY}:
                import random
                for brick in game.bricks:
                    brick.alive = random.random() > 0.5
                game._launch_ball()
                game.state = PlayState.PLAYING
            elif game.state in {PlayState.CLEARED, PlayState.GAME_OVER}:
                game._restart_game()
                import random
                for brick in game.bricks:
                    brick.alive = random.random() > 0.5
                game.harvest_training_data = True
                game._launch_ball()
                game.state = PlayState.PLAYING

            if game.frame % 1000 == 0:
                print(f"rows={game.training_logger.rows_written} frame={game.frame}")
    finally:
        game.training_logger.close()
        import pygame

        pygame.quit()

    print(f"wrote {game.training_logger.rows_written} rows to {args.output}")


if __name__ == "__main__":
    main()
