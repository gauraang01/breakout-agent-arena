# Stage 3: Neural Network Controller

## Objective

Train a neural model that acts as a **Strategic Aiming Agent**. Instead of forcing the neural network to learn the highly discontinuous laws of physics (which fails due to chaos and the butterfly effect), we let the deterministic math tool handle the base physics prediction. The Neural Network acts purely as a spatial strategy layer: it looks at the board, identifies the best remaining bricks, and predicts the exact paddle offset (-50 mm to +50 mm) needed to snipe them.

## Architecture

The model is a **2D Spatial CNN**.
During inference and training, the raw coordinates (`ball_x`, `ball_y`, `bricks`) are plotted onto a 2-channel 2D Grid:
- **Channel 0**: A 2D spatial representation of the alive bricks.
- **Channel 1**: A spatial dot representing the ball's current location.

This allows the convolutional layers to physically "see" the board state and the ball's approach, naturally extracting geometric features. The CNN then outputs a single Regression value representing the strategic paddle offset.

## Data Acquisition

Run:

```bash
python3 scripts/collect_training_data.py --rows 30000
```

The collector runs headless and fast. It generates a dataset of "Perfect Strategic Aiming". Instead of forcing the data collector to just catch the ball, it mathematically identifies the lowest cluster of alive bricks, calculates the exact geometric paddle offset required to bounce the ball directly into that cluster, and logs that offset as the Ground Truth label.

CSV schema:

```text
ball_x,ball_y,ball_dx,ball_dy,b0...b47,target_paddle_mm
```

`target_paddle_mm` contains the strategic offset from the deterministic landing spot.

## Training

Run:

```bash
python3 scripts/train_mlp_model.py
```

The training script:

- Reads `training_data.csv`.
- Maps coordinates to the 2D Spatial Grid on the fly.
- Trains a PyTorch CNN using Mean Squared Error (MSE) loss.
- Saves `mlp_model.pt`

The model achieves extremely low MAE (e.g. ~2.1 mm) when predicting the ideal strategic offset.

## Runtime Control

Controls:

- `1`: Manual mode.
- `2`: Neural Network Controller mode.
- `3`: LLM Agent mode (Requires Ollama)

On game startup, the neural controller attempts to load `mlp_model.pt`.

Runtime behavior:

1. The controller uses the deterministic `TrajectoryPredictor` to compute `base_target`.
2. The neural network predicts the `strategic_offset` based on the visual board state.
3. The paddle is moved to `base_target + strategic_offset`.

This seamlessly combines flawless physics with intelligent neural strategy.
