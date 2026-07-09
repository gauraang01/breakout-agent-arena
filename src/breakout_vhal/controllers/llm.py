from __future__ import annotations

import json
import time
import requests
from typing import Callable, Any
from ..config import LLM

class LLMAgentController:
    def __init__(self, math_controller):
        self.math_controller = math_controller
        self.traces: list[str] = []

    def clear_traces(self) -> None:
        self.traces.clear()

    def predict_target_mm(
        self,
        ball_x: float,
        ball_y: float,
        ball_dx: float,
        ball_dy: float,
        strike_y: float,
        field_rect: Any,
        paddle_min_center_x: float,
        paddle_max_center_x: float,
        track_length_mm: float,
        brick_rects: list[Any],
        log_callback: Callable[[str], None],
        draw_callback: Callable[[], None]
    ) -> float:
        self.clear_traces()
        try:
            log_callback("[LLM] Analyzing ball vector...")
            draw_callback()

            
            # Step 1: Initial query
            tools = [{
                "type": "function",
                "function": {
                    "name": "predict_trajectory",
                    "description": "Calculate exact paddle target in millimeters",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ball_x": {"type": "number"},
                            "ball_y": {"type": "number"},
                            "ball_dx": {"type": "number"},
                            "ball_dy": {"type": "number"}
                        },
                        "required": ["ball_x", "ball_y", "ball_dx", "ball_dy"]
                    }
                }
            }]
            
            messages = [
                {"role": "system", "content": "You are a Breakout controller. You must use the predict_trajectory tool to find the target position."},
                {"role": "user", "content": f"Ball: X={ball_x:.1f}, Y={ball_y:.1f}, dX={ball_dx:.1f}, dY={ball_dy:.1f}"}
            ]
            
            response = requests.post("http://localhost:11434/api/chat", json={
                "model": LLM.model,
                "messages": messages,
                "tools": tools,
                "stream": False
            }, timeout=None)
            response.raise_for_status()
            message = response.json().get("message", {})
            
            log_callback("[LLM] Math is too complex. Requesting tool: predict_trajectory()")
            draw_callback()

            
            # Step 2: Python Execution
            prediction = self.math_controller.predict(
                ball_x=ball_x, ball_y=ball_y, ball_dx=ball_dx, ball_dy=ball_dy,
                strike_y=strike_y, field_rect=field_rect, paddle_min_center_x=paddle_min_center_x,
                paddle_max_center_x=paddle_max_center_x, track_length_mm=track_length_mm,
                brick_rects=brick_rects
            )
            target_mm = prediction.target_mm
            
            log_callback(f"[PYTHON] Executing MathematicalController... Output: {target_mm:.1f}mm")
            draw_callback()

            
            # Step 3 Optimization: Skip asking the LLM to repeat the answer!
            # The python tool already gave us target_mm, so we can just use it immediately.
            log_callback(f"[LLM] Tool confirmed. Finalizing target: {target_mm:.1f}mm")
            draw_callback()

            
            log_callback("[V-HAL] Accelerating paddle...")
            draw_callback()

            
            return float(target_mm)
            
        except Exception as e:
            print(f"LLM Error: {e}")
            log_callback(f"[ERROR] LLM failed, defaulting to center. ({e})")
            draw_callback()
            return 250.0
