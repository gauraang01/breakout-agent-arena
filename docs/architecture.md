# Architecture

## Goals

The game should be useful as both a playable Breakout sandbox and a hardware
simulation harness. Every stage must keep the V-HAL as the only path for paddle
movement so later autonomous controllers, serial bridges, or real hardware
drivers can replace manual input without changing game physics.

## Module Layout

```text
src/breakout_vhal/
  __main__.py      # module entrypoint
  config.py        # dimensions, colors, gameplay constants, V-HAL constants
  game.py          # Pygame loop, rendering, input, collisions, game state
  vhal.py          # virtual hardware motion model
```

## Runtime Flow

1. Pygame initializes the window and game entities.
2. The keyboard handler updates a target position in the V-HAL:
   - Left arrow means target = 0 mm.
   - Right arrow means target = 500 mm.
   - No horizontal input means target = current paddle position, causing a
     controlled stop.
3. Each frame advances the V-HAL with `dt`.
4. The game reads the V-HAL paddle position and maps it to the screen.
5. Ball, brick, wall, paddle, scoring, and life collisions are resolved.
6. The overlay renders telemetry from both the game and V-HAL.

## Separation Rules

- Input code may set V-HAL targets but must not directly edit paddle pixels.
- Game collision code may read paddle position but must not bypass V-HAL
  acceleration or velocity limits.
- Future controllers should call the same target-position API used by keyboard
  input.
- Hardware-specific details should stay outside the core Breakout game loop
  until a later hardware stage.

## Extension Points

- Replace manual keyboard target generation with an AI/controller module.
- Add serial or GPIO output by adapting V-HAL state to real motor commands.
- Tune the V-HAL constants after measuring a physical NEMA 17 setup.
- Add logging or replay by recording V-HAL state and ball state each frame.
