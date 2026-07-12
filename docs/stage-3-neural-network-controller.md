# Stage 3: Neural Network Controller

## Objective

Train a neural model that acts as a **Strategic Aiming Agent**. Instead of forcing the neural network to learn the highly discontinuous laws of physics (which fails due to chaos and the butterfly effect), we let the deterministic math tool handle the base physics prediction. The Neural Network acts purely as a spatial strategy layer: it looks at the board, identifies the best remaining bricks, and predicts the exact paddle offset (-50 mm to +50 mm) needed to snipe them.

## Architecture

The model is a **Spatial Density MLP**.
Instead of passing the exact coordinates of all 48 bricks (which leads to overfitting and chaos when bricks break mid-flight), the board is reduced to three macro-features: `left_d`, `center_d`, and `right_d`. 
This allows the neural network to develop a generalized spatial intuition. The Multi-Layer Perceptron (MLP) digests these 3 density zones alongside the ball's trajectory and outputs a single Regression value representing the strategic paddle offset.

## Data Acquisition

Run:

```bash
python3 scripts/collect_training_data.py --rows 30000
```

The collector runs headless and fast. It generates a dataset of "Perfect Strategic Aiming". Instead of forcing the data collector to target the lowest individual brick (which contradicts macro-density features), it mathematically calculates the geometric center of the **highest density zone** and logs the geometric paddle offset required to bounce the ball directly into that zone.

CSV schema:

```text
ball_x,ball_y,ball_dx,ball_dy,left_d,center_d,right_d,target_paddle_mm
```

`target_paddle_mm` contains the strategic offset from the deterministic landing spot.

## Training

Run:

```bash
python3 scripts/train_mlp_model.py
```

The training script:

- Reads `training_data.csv`.
- Maps features to a 7-element vector.
- Trains a PyTorch MLP using Mean Squared Error (MSE) loss.
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
