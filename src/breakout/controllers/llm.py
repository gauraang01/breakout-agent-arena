from __future__ import annotations

import json
import time
import requests
from typing import Callable, Any
from ..config import LLM

class LLMAgentController:
    def __init__(self, trajectory_predictor):
        self.trajectory_predictor = trajectory_predictor
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
        start_time = time.time()
        
        try:
            log_callback("[LLM] Thinking...")
            draw_callback()

            # The new approach: give the LLM two tools for strategic aiming
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "predict_landing_spot",
                        "description": "Calculate exactly where the ball will land on the paddle line (in mm).",
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
                },
                {
                    "type": "function",
                    "function": {
                        "name": "calculate_paddle_offset",
                        "description": "Calculate the paddle offset (-1.0 to 1.0) needed to bounce the ball to a specific target X coordinate.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "target_x": {"type": "number"},
                            },
                            "required": ["target_x"]
                        }
                    }
                }
            ]
            
            # Find the lowest brick to aim at!
            lowest_brick = None
            for rect in brick_rects:
                if lowest_brick is None or rect.bottom > lowest_brick.bottom:
                    lowest_brick = rect
            
            aim_hint = f"Try aiming for the brick at X={lowest_brick.centerx:.1f}!" if lowest_brick else "Just catch the ball."

            messages = [
                {
                    "role": "system", 
                    "content": "You are a strategic Breakout AI. First, think about your strategy. Then, use predict_landing_spot to find where the ball falls. If you want to aim, use calculate_paddle_offset. Finally, output your thoughts!"
                },
                {
                    "role": "user", 
                    "content": f"Ball: X={ball_x:.1f}, Y={ball_y:.1f}, dX={ball_dx:.1f}, dY={ball_dy:.1f}. {aim_hint}"
                }
            ]
            
            log_callback("LLM: ")
            log_idx = len(self.traces) - 1

            response = requests.post("http://localhost:11434/api/chat", json={
                "model": LLM.model,
                "messages": messages,
                "tools": tools,
                "stream": True
            }, stream=True, timeout=None)
            response.raise_for_status()
            
            tool_calls = []
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    msg = chunk.get("message", {})
                    content = msg.get("content", "")
                    if content:
                        self.traces[log_idx] += content
                        draw_callback()
                    
                    if "tool_calls" in msg:
                        tool_calls.extend(msg["tool_calls"])
            
            latency = time.time() - start_time
            log_callback(f"[Latency] LLM Thinking Time: {latency:.2f}s")
            draw_callback()

            # We execute the python tool regardless of what the LLM chose, 
            # but now we can see its streaming thoughts and strategy!
            prediction = self.trajectory_predictor.predict(
                ball_x=ball_x, ball_y=ball_y, ball_dx=ball_dx, ball_dy=ball_dy,
                strike_y=strike_y, field_rect=field_rect, paddle_min_center_x=paddle_min_center_x,
                paddle_max_center_x=paddle_max_center_x, track_length_mm=track_length_mm,
                brick_rects=brick_rects
            )
            
            # Simple aiming logic: if LLM tried to use calculate_paddle_offset, apply an offset!
            target_mm = prediction.target_mm
            from ..tools.aim_predictor import calculate_paddle_offset
            from ..config import PADDLE
            
            for tool in tool_calls:
                if tool["function"]["name"] == "calculate_paddle_offset":
                    try:
                        args = tool["function"]["arguments"]
                        if isinstance(args, str):
                            args = json.loads(args)
                        aim_x = args.get("target_x", paddle_min_center_x)
                        
                        offset_mm = calculate_paddle_offset(
                            landing_x=target_mm,
                            paddle_y=strike_y,
                            target_brick_x=aim_x,
                            target_brick_y=lowest_brick.centery if lowest_brick else 0.0,
                            paddle_width=PADDLE.width
                        )
                        target_mm += offset_mm
                        log_callback(f"[PYTHON] Applying calculated offset: {offset_mm:.1f}mm")
                    except Exception:
                        pass
            
            total_latency = time.time() - start_time
            log_callback(f"[Latency] Total Pipeline Time: {total_latency:.2f}s")
            log_callback(f"[V-HAL] Driving paddle to {target_mm:.1f}mm")
            draw_callback()
            
            return float(target_mm)
            
        except Exception as e:
            print(f"LLM Error: {e}")
            log_callback(f"[ERROR] LLM failed ({e})")
            draw_callback()
            return 250.0
