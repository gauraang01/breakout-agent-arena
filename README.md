# Breakout V-HAL

A staged Breakout project where the paddle is constrained by a Virtual Hardware
Abstraction Layer that simulates a 0-500 mm physical rail.

## Run Stage 1

```bash
python3 run_stage1.py
```

Or install the package in editable mode:

```bash
python3 -m pip install -e .
python3 -m breakout_vhal
```

Project planning and architecture notes are in [docs/README.md](docs/README.md).
