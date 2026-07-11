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

    def predict_target_mm(self, ball_x: float, ball_y: float, ball_dx: float, ball_dy: float, brick_states: list[bool], base_target: float = 250.0) -> NeuralPrediction:
        if not self.available or self.model is None:
            return NeuralPrediction(target_mm=base_target, available=False, reason=self.load_error)
            
        try:
            # Trajectory Lock: Arduino motors hate micro-jitters.
            # Since base_target is mathematically perfect, it stays exactly identical for an entire flight path.
            # Floating point noise can cause base_target to drift by 0.5-2.0 mm per frame.
            # We use a 5.0 mm tolerance to ensure we only break the lock if a true physical bounce happens.
            if hasattr(self, 'last_base_target') and abs(self.last_base_target - base_target) < 5.0:
                return NeuralPrediction(target_mm=self.locked_target, available=True)

            features = [ball_x, ball_y, ball_dx, ball_dy] + [1.0 if alive else 0.0 for alive in brick_states]
            with self.torch.no_grad():
                tensor = self.torch.tensor([features], dtype=self.torch.float32)
                strategic_offset = self.model(tensor).item()
                
            final_target = max(0.0, min(VHAL.track_length_mm, base_target + strategic_offset))
            
            self.last_base_target = base_target
            self.locked_target = final_target
            
            return NeuralPrediction(
                target_mm=max(0.0, min(VHAL.track_length_mm, final_target)),
                available=True,
            )
        except Exception as exc:
            return NeuralPrediction(
                target_mm=VHAL.track_length_mm / 2.0,
                available=False,
                reason=str(exc)
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
