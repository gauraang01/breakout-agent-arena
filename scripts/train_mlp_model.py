from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the Stage 3 MLP paddle controller.")
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "training_data.csv",
        help="Training CSV path.",
    )
    parser.add_argument(
        "--model-output",
        type=Path,
        default=ROOT / "models"/ "mlp_model.pt",
        help="Output PyTorch model checkpoint path.",
    )
    parser.add_argument(
        "--scaler-output",
        type=Path,
        default=ROOT / "models"/ "scaler.json",
        help="Output JSON feature scaler path.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=250,
        help="Training epochs.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=256,
        help="Mini-batch size.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset

        from breakout_vhal.training.mlp_model import build_paddle_mlp
    except ImportError as exc:
        raise SystemExit(
            "Missing ML dependency. Install with: python3 -m pip install -r requirements.txt"
        ) from exc

    rows = _read_rows(args.input)
    if len(rows) < 1000:
        raise SystemExit(f"Need at least 1000 rows; found {len(rows)} in {args.input}")

    torch.manual_seed(42)
    data = torch.tensor(rows, dtype=torch.float32)
    x = data[:, :4]
    y = data[:, 4:5]

    permutation = torch.randperm(len(data))
    split = int(len(data) * 0.8)
    train_idx = permutation[:split]
    test_idx = permutation[split:]

    x_train = x[train_idx]
    y_train = y[train_idx]
    x_test = x[test_idx]
    y_test = y[test_idx]

    mean = x_train.mean(dim=0)
    std = x_train.std(dim=0).clamp_min(1e-6)
    x_train_scaled = (x_train - mean) / std
    x_test_scaled = (x_test - mean) / std

    train_loader = DataLoader(
        TensorDataset(x_train_scaled, y_train),
        batch_size=args.batch_size,
        shuffle=True,
    )

    model = build_paddle_mlp()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    loss_fn = nn.MSELoss()

    for epoch in range(1, args.epochs + 1):
        model.train()
        total_loss = 0.0
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            prediction = model(batch_x)
            loss = loss_fn(prediction, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item()) * len(batch_x)

        if epoch == 1 or epoch % 25 == 0 or epoch == args.epochs:
            print(f"epoch={epoch} train_mse={total_loss / len(x_train):.4f}")

    model.eval()
    with torch.no_grad():
        predictions = model(x_test_scaled)
        mae = torch.mean(torch.abs(predictions - y_test)).item()
        residual = torch.sum((y_test - predictions) ** 2)
        total = torch.sum((y_test - torch.mean(y_test)) ** 2).clamp_min(1e-6)
        r2 = (1.0 - residual / total).item()

    torch.save({"model_state_dict": model.state_dict()}, args.model_output)
    args.scaler_output.write_text(
        json.dumps(
            {
                "mean": [float(value) for value in mean.tolist()],
                "std": [float(value) for value in std.tolist()],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"rows={len(rows)}")
    print(f"mae_mm={mae:.3f}")
    print(f"r2={r2:.4f}")
    print(f"saved_model={args.model_output}")
    print(f"saved_scaler={args.scaler_output}")


def _read_rows(path: Path) -> list[list[float]]:
    if not path.exists():
        raise SystemExit(f"Training data not found: {path}")

    rows: list[list[float]] = []
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        required = ["ball_x", "ball_y", "ball_dx", "ball_dy", "target_paddle_mm"]
        if reader.fieldnames != required:
            raise SystemExit(f"Expected columns {required}; found {reader.fieldnames}")

        for row in reader:
            rows.append(
                [
                    float(row["ball_x"]),
                    float(row["ball_y"]),
                    float(row["ball_dx"]),
                    float(row["ball_dy"]),
                    float(row["target_paddle_mm"]),
                ]
            )
    return rows


if __name__ == "__main__":
    main()
