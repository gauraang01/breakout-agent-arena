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

            # The new approach: give the LLM tools for strategic aiming
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
                    "content": 'You are a strategic Breakout AI. First, use predict_landing_spot to find where the ball falls. If you want to aim, use calculate_paddle_offset. Finally, you MUST output a JSON response in the exact format {"base_target_mm": float, "offset_mm": float} containing the values you got from the tools (use 0.0 for offset if you did not aim). Do not output any reasoning, just the JSON object to save time.'
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
            assistant_content = ""
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    msg = chunk.get("message", {})
                    content = msg.get("content", "")
                    if content:
                        assistant_content += content
                        self.traces[log_idx] += content
                        draw_callback()
                    
                    if "tool_calls" in msg:
                        tool_calls.extend(msg["tool_calls"])
            
            latency = time.time() - start_time
            log_callback(f"[Latency] LLM Thinking Time: {latency:.2f}s")
            draw_callback()

            target_mm = 250.0

            # Execute the tools if requested, and send the result back to the LLM!
            if tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": assistant_content,
                    "tool_calls": tool_calls
                })
                
                from ..tools.aim_predictor import calculate_paddle_offset
                from ..config import PADDLE
                
                base_target = 250.0
                impact_x_px = paddle_min_center_x
                
                # First pass: execute predict_landing_spot
                for tool in tool_calls:
                    if tool["function"]["name"] == "predict_landing_spot":
                        prediction = self.trajectory_predictor.predict(
                            ball_x=ball_x, ball_y=ball_y, ball_dx=ball_dx, ball_dy=ball_dy,
                            strike_y=strike_y, field_rect=field_rect, paddle_min_center_x=paddle_min_center_x,
                            paddle_max_center_x=paddle_max_center_x, track_length_mm=track_length_mm,
                            brick_rects=brick_rects
                        )
                        base_target = prediction.target_mm
                        impact_x_px = prediction.impact_x_px
                        
                        # If the trajectory predictor added a random angled offset, remove it so the LLM can aim purely
                        if prediction.angled_hit:
                            from ..tools.trajectory_predictor import pixel_center_x_to_track_mm
                            base_target = pixel_center_x_to_track_mm(
                                impact_x_px, paddle_min_center_x, paddle_max_center_x, track_length_mm
                            )
                            
                        log_callback(f"[PYTHON] predict_landing_spot: {base_target:.1f}mm")
                        messages.append({
                            "role": "tool",
                            "name": tool["function"]["name"],
                            "content": json.dumps({"target_mm": base_target})
                        })
                        draw_callback()
                
                # Second pass: execute calculate_paddle_offset
                for tool in tool_calls:
                    if tool["function"]["name"] == "calculate_paddle_offset":
                        try:
                            args = tool["function"]["arguments"]
                            if isinstance(args, str):
                                args = json.loads(args)
                            aim_x = args.get("target_x", paddle_min_center_x)
                            
                            offset_px = calculate_paddle_offset(
                                landing_x=impact_x_px,
                                paddle_y=strike_y,
                                target_brick_x=aim_x,
                                target_brick_y=lowest_brick.centery if lowest_brick else 0.0,
                                paddle_width=PADDLE.width
                            )
                            # Convert pixel offset to hardware mm offset
                            px_range = paddle_max_center_x - paddle_min_center_x
                            offset_mm = offset_px * (track_length_mm / px_range) if px_range > 0 else 0.0
                            log_callback(f"[PYTHON] calculate_paddle_offset: {offset_mm:.1f}mm")
                            messages.append({
                                "role": "tool",
                                "name": tool["function"]["name"],
                                "content": json.dumps({
                                    "offset_mm": offset_mm
                                })
                            })
                            draw_callback()
                        except Exception as e:
                            messages.append({
                                "role": "tool",
                                "name": tool["function"]["name"],
                                "content": json.dumps({"error": str(e)})
                            })
                            
                # Final roundtrip back to the LLM to get the JSON synthesis
                self.traces.append("LLM (Synthesizing JSON): ")
                log_idx = len(self.traces) - 1
                log_callback("LLM (Synthesizing JSON): ")
                draw_callback()
                
                response = requests.post("http://localhost:11434/api/chat", json={
                    "model": LLM.model,
                    "messages": messages,
                    "format": "json", # Force it to return guaranteed JSON output
                    "stream": True
                }, stream=True, timeout=None)
                response.raise_for_status()
                
                final_content = ""
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        msg = chunk.get("message", {})
                        content = msg.get("content", "")
                        if content:
                            final_content += content
                            self.traces[log_idx] += content
                            draw_callback()
                
                # Parse the guaranteed JSON
                try:
                    final_data = json.loads(final_content)
                    base_target_mm = float(final_data.get("base_target_mm", 250.0))
                    offset_mm = float(final_data.get("offset_mm", 0.0))
                    
                    target_mm = base_target_mm - offset_mm
                    log_callback(f"[PYTHON] Final Math: {base_target_mm:.1f} - {offset_mm:.1f} = {target_mm:.1f}mm")
                except Exception as e:
                    log_callback(f"[ERROR] JSON parse failed: {e}")
            
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
