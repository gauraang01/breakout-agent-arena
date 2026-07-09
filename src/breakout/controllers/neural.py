from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..config import VHAL


@dataclass(frozen=True)
class NeuralPrediction:
    target_mm: float
    available: bool
    reason: str = ""


class NeuralNetworkController:
    def __init__(
        self,
        model_path: Path = Path("models/mlp_model.pt"),
        scaler_path: Path = Path("models/scaler.json"),
    ) -> None:
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.model = None
        self.feature_mean: list[float] | None = None
        self.feature_std: list[float] | None = None
        self.torch = None
        self.load_error = ""
        self._load()

    @property
    def available(self) -> bool:
        return (
            self.model is not None
            and self.feature_mean is not None
            and self.feature_std is not None
            and self.torch is not None
        )

    def predict_target_mm(
        self,
        ball_x: float,
        ball_y: float,
        ball_dx: float,
        ball_dy: float,
    ) -> NeuralPrediction:
        if ball_dy < 0:
            return NeuralPrediction(
                target_mm=VHAL.track_length_mm / 2.0,
                available=self.available,
                reason="ball_up_center_rest",
            )

        if not self.available:
            return NeuralPrediction(
                target_mm=VHAL.track_length_mm / 2.0,
                available=False,
                reason=self.load_error or "model_not_loaded",
            )

        features = [ball_x, ball_y, ball_dx, ball_dy]
        scaled = [
            (value - mean) / std
            for value, mean, std in zip(features, self.feature_mean, self.feature_std)
        ]
        with self.torch.no_grad():
            tensor = self.torch.tensor([scaled], dtype=self.torch.float32)
            target = float(self.model(tensor).item())
        return NeuralPrediction(
            target_mm=max(0.0, min(VHAL.track_length_mm, target)),
            available=True,
        )

    def _load(self) -> None:
        if not self.model_path.exists() or not self.scaler_path.exists():
            self.load_error = "missing mlp_model.pt or scaler.json"
            return

        try:
            import torch
        except ImportError:
            self.load_error = "torch is not installed"
            return

        try:
            from ..training.mlp_model import build_paddle_mlp

            scaler = json.loads(self.scaler_path.read_text(encoding="utf-8"))
            self.feature_mean = [float(value) for value in scaler["mean"]]
            self.feature_std = [max(float(value), 1e-6) for value in scaler["std"]]
            self.model = build_paddle_mlp()
            state = torch.load(self.model_path, map_location="cpu")
            self.model.load_state_dict(state["model_state_dict"])
            self.model.eval()
            self.torch = torch
        except Exception as exc:
            self.model = None
            self.feature_mean = None
            self.feature_std = None
            self.torch = None
            self.load_error = f"model load failed: {exc}"
