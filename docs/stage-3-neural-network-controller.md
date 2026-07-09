# Stage 3: Neural Network Controller

## Objective

Replace hardcoded reflection geometry at runtime with a lightweight neural model
that learns the mapping from observed ball state to the correct paddle target.
The Neural Network Controller still controls the rail only through the V-HAL.

## Data Acquisition

The Stage 2 Mathematical Controller is used as the label generator.

Run:

```bash
python3 scripts/collect_training_data.py --rows 20000
```

The collector runs headless and fast. It uses the same game physics and V-HAL
target contract, but does not render frames.

Data rules:

- Only log when `ball_dy > 0`, meaning the ball is falling toward the paddle.
- Log every 4 frames by default to avoid excessive redundant samples.
- Generate at least 10,000 rows; 20,000 to 50,000 is preferred.
- The output file is overwritten each run.

CSV schema:

```text
ball_x,ball_y,ball_dx,ball_dy,target_paddle_mm
```

`target_paddle_mm` is the Stage 2 controller's desired paddle-center target, including
the anti-vertical-loop offset when that rule applies.

## Training

Run:

```bash
python3 scripts/train_mlp_model.py
```

The training script:

- Reads `training_data.csv`.
- Uses inputs `[ball_x, ball_y, ball_dx, ball_dy]`.
- Computes feature mean and standard deviation from the training split.
- Standardizes features before training.
- Trains a PyTorch MLP with two 64-neuron hidden layers.
- Saves:
  - `mlp_model.pt`
  - `scaler.json`

These are generated artifacts and should not be committed. They are ignored by
`.gitignore` and can be recreated from `training_data.csv` at any time.

The model is deliberately small so PyTorch inference stays lightweight inside
the 60 FPS Pygame loop.

PyTorch expects NumPy to be installed in this environment. If NumPy is missing,
training and gameplay may still work, but PyTorch emits a startup warning.

## Runtime Control

Controls:

- `1`: Manual mode.
- `2`: Mathematical Controller mode.
- `3`: Neural Network Controller mode.

On game startup, the neural controller attempts to load `mlp_model.pt` and
`scaler.json` from the project root.

Runtime behavior:

- If `ball_dy < 0`, the neural controller rests by sending the paddle to `250 mm`.
- If `ball_dy > 0`, it scales the current ball state and predicts
  `target_paddle_mm`.
- The predicted coordinate is clamped to `0-500 mm`.
- The target is sent to the V-HAL, which still enforces max speed, acceleration,
  braking, and rail bounds.

## Jitter Notes

Neural predictions may shift slightly from frame to frame as the ball descends.
This is intentional for the stress test: it exposes whether V-HAL acceleration
and braking are stable enough for low-latency AI control.

If the paddle chatters too much:

- Lower `max_acceleration_mm_s2`.
- Add a deadband around small target changes.
- Smooth neural outputs with a short moving average.

Those mitigations should be added only if the live model actually jitters.
