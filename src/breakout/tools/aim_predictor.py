from __future__ import annotations

import math

def calculate_paddle_offset(
    landing_x: float,
    paddle_y: float,
    target_brick_x: float,
    target_brick_y: float,
    paddle_width: float
) -> float:
    """
    Calculates the exact physical offset (in pixels) on the paddle needed
    to rebound the ball perfectly into a target brick coordinate.
    """
    dx = target_brick_x - landing_x
    dy = paddle_y - target_brick_y
    
    if dy <= 0:
        return 0.0
        
    # Calculate the exact angle we need the ball to fly at to hit the target
    angle_deg = math.degrees(math.atan2(dy, dx))
    
    # The game's physics engine resolves bounces as: angle = 90 - (offset * 58)
    # We solve backwards for the normalized offset (-1.0 to 1.0)
    offset_normalized = (90.0 - angle_deg) / 58.0
    
    # Clamp to the physical limits of the paddle
    offset_normalized = max(-1.0, min(1.0, offset_normalized))
    
    # Convert the normalized ratio back into physical pixels/millimeters
    offset_mm = offset_normalized * (paddle_width / 2.0)
    
    return offset_mm
