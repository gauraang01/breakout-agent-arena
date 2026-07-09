# Breakout

A staged Breakout project where the paddle is constrained by a Virtual Hardware
Abstraction Layer that simulates a 0-500 mm physical rail.

## Run

```bash
python3 start.py
```

Controls:

- `1`: Manual mode
- `2`: Neural Network mode
- `3`: LLM Agent mode (Requires Ollama)
- Space: launch/restart
- Escape: quit

Stage 3 workflow:

```bash
python3 scripts/collect_training_data.py --rows 20000
python3 scripts/train_mlp_model.py
python3 start.py
```

When the mathematical controller is active, downward-ball samples are written every 4
frames to `training_data.csv`.

Or install the package in editable mode:

```bash
python3 -m pip install -e .
python3 -m breakout
```

Project planning and architecture notes are in [docs/README.md](docs/README.md).
