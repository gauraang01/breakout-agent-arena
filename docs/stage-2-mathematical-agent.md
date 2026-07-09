# Stage 2: Mathematical Agent

## Objective

Run the Breakout engine autonomously with a deterministic geometry controller and
use it as a data generator for later learning-based stages.

## Mode Switch

- `1`: Manual keyboard control.
- `2`: Mathematical Agent control.

The game still uses the same V-HAL in both modes. The agent never teleports the
paddle; it only sends target millimeter coordinates to the V-HAL.

## Algorithm

Each frame, the Mathematical Agent reads:

- Ball position: `ball_x`, `ball_y`
- Ball vector velocity: `ball_dx`, `ball_dy`
- Playfield bounds
- Paddle strike line

It predicts where the ball center will cross the paddle strike line by applying
reflection geometry against the left and right walls. When the ball is moving
upward, the agent first reflects the trajectory off the top boundary and then
projects the downward path.

The predicted pixel X coordinate is converted into a paddle-center millimeter
target across the `0 mm` to `500 mm` physical track.

## Anti-Vertical-Loop Rule

If the ball is traveling relatively perpendicular to the paddle, the agent checks
whether the current trajectory will hit any remaining brick before reaching the
paddle strike line.

When both conditions are true:

- the horizontal component is small compared with the vertical component
- no brick is expected on the path to the paddle

the agent intentionally targets the paddle slightly off-center. This creates a
small rebound angle instead of sending the ball straight back upward into an
unproductive vertical loop.

The CSV label remains the desired paddle-center position, not just the raw ball
impact point. That means later learning stages train against the tactically
correct target chosen by the Mathematical Agent.

## Data Harvesting

While the game is in Mathematical Agent mode and the ball is actively playing, a
sample is written every 4 frames to:

```text
training_data.csv
```

Samples are written only when `ball_dy > 0`, so the dataset focuses on downward
trajectories toward the paddle and avoids noisy upward brick-collision states.

CSV columns:

- `ball_x`
- `ball_y`
- `ball_dx`
- `ball_dy`
- `target_paddle_mm`

`target_paddle_mm` represents the agent's desired paddle-center target. For
normal catches this lines up with the predicted impact X. For
anti-vertical-loop catches it is slightly offset from the impact point.

The file is overwritten on each game run or data-collection run. This keeps a
run's dataset internally consistent and avoids accidentally mixing data from
different physics settings.

## Known Limitations

- Brick collisions can change the ball vector after the agent has predicted a
  path. The prediction is recalculated every frame, so the target corrects
  immediately after the collision.
- The agent is deterministic geometry, not perception. It has direct access to
  game state and is intended to generate supervised labels for later stages.
