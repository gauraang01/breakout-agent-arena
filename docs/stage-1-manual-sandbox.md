# Stage 1: Manual Sandbox

## Objective

Build a playable Breakout game that proves the collision boundaries and V-HAL
motion constraints before adding autonomous or hardware-driven control.

## Controls

- Left arrow: command the V-HAL target to `0 mm`.
- Right arrow: command the V-HAL target to `500 mm`.
- No arrow key: command the V-HAL target to the current physical position so the
  paddle decelerates to a stop.
- Space: launch the ball or restart after game over / stage clear.
- Escape: quit.

## Required UI

- Ball.
- Destructible top bricks.
- Bottom paddle.
- Live data overlay with:
  - Ball position `(X, Y)`.
  - Ball vector velocity `(dX, dY)`.
  - Paddle pixel position.
  - Paddle physical position in millimeters.
  - Paddle target in millimeters.
  - Paddle velocity in millimeters per second.

## Gameplay Notes

- The Stage 1 window is `1280 x 800`.
- The paddle starts at the center of the 500 mm track.
- The ball starts attached above the paddle until launched.
- Losing the ball costs one life and resets the ball and paddle target.
- Clearing all bricks shows a stage-clear state and allows restart.

## Done Criteria

- The game is playable with keyboard input.
- Paddle movement visibly accelerates and decelerates instead of teleporting.
- Bricks are destroyed on impact.
- Ball collisions behave consistently against walls, bricks, and paddle.
- Telemetry updates live while playing.
