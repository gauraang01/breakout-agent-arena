# Breakout V-HAL

A staged Breakout project where the paddle is constrained by a Virtual Hardware
Abstraction Layer that simulates a 0-500 mm physical rail.

## Run

```bash
python3 run_stage1.py
```

Controls:

- `1`: manual mode
- `2`: mathematical agent mode
- `3`: neural network mode
- Space: launch/restart
- Escape: quit

Stage 3 workflow:

```bash
python3 scripts/collect_training_data.py --rows 20000
python3 scripts/train_mlp_model.py
python3 run_stage1.py
```

When the mathematical agent is active, downward-ball samples are written every 4
frames to `training_data.csv`.

Or install the package in editable mode:

```bash
python3 -m pip install -e .
python3 -m breakout_vhal
```

Project planning and architecture notes are in [docs/README.md](docs/README.md).
