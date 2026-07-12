from __future__ import annotations

import csv
from pathlib import Path
from typing import TextIO


class TrainingDataLogger:
    def __init__(self, path: Path, sample_interval_frames: int = 4) -> None:
        self.path = path
        self.sample_interval_frames = sample_interval_frames
        self.rows_written = 0
        self._file: TextIO | None = None
        self._writer: csv.writer | None = None

    def log(
        self,
        frame: int,
        ball_x: float,
        ball_y: float,
        ball_dx: float,
        ball_dy: float,
        left_d: float,
        center_d: float,
        right_d: float,
        target_paddle_mm: float,
    ) -> None:
        if frame % self.sample_interval_frames != 0:
            return

        writer = self._ensure_writer()
        row = [
            f"{ball_x:.3f}",
            f"{ball_y:.3f}",
            f"{ball_dx:.3f}",
            f"{ball_dy:.3f}",
            f"{left_d:.3f}",
            f"{center_d:.3f}",
            f"{right_d:.3f}",
            f"{target_paddle_mm:.3f}"
        ]
        
        writer.writerow(row)
        self.rows_written += 1

    def close(self) -> None:
        if self._file is None:
            return
        self._file.close()
        self._file = None
        self._writer = None

    def _ensure_writer(self) -> csv.writer:
        if self._writer is not None:
            return self._writer

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("w", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        
        headers = ["ball_x", "ball_y", "ball_dx", "ball_dy", "left_d", "center_d", "right_d", "target_paddle_mm"]
        self._writer.writerow(headers)
        return self._writer
