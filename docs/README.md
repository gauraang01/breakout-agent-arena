# Breakout V-HAL Project

This project builds a Breakout-style game in stages around a Virtual Hardware
Abstraction Layer (V-HAL). The game is intentionally constrained by physical
motion rules so the simulated paddle behaves like a real paddle driven along a
linear track by a NEMA 17 stepper motor.

## Current Stage

Stage 2: Mathematical Agent

- Human control through left and right arrow keys.
- Autonomous control by pressing `2`.
- A fully playable Breakout field with ball, bricks, paddle, scoring, lives, and
  restart flow.
- The paddle is not moved directly by keyboard input. Keyboard input updates a
  V-HAL target position, and the V-HAL moves the paddle using velocity and
  acceleration limits.
- The Mathematical Agent predicts the paddle target with reflection geometry and
  writes training samples to `training_data.csv`.
- A live overlay exposes ball coordinates, ball velocity vector, paddle target,
  paddle position in pixels, paddle physical position in millimeters, paddle
  velocity, and V-HAL limits.

## Documentation Map

- [Architecture](architecture.md): module layout, runtime flow, and extension
  points.
- [V-HAL Specification](vhal.md): physical model, coordinate mapping, and
  constraints.
- [Stage 1 Manual Sandbox](stage-1-manual-sandbox.md): gameplay scope and manual
  control behavior.
- [Stage 2 Mathematical Agent](stage-2-mathematical-agent.md): autonomous
  geometry controller and data harvesting schema.

## Run

```bash
python3 run_stage1.py
```

Or install the package in editable mode:

```bash
python3 -m pip install -e .
python3 -m breakout_vhal
```
