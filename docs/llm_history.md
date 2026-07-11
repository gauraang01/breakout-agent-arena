# The LLM Journey: Trying to use ChatGPT to Play Breakout

This document chronicles our journey of integrating Large Language Models (LLMs)—specifically Qwen and Llama—into the Breakout environment. 
Our goal was to see if we could use the high-level reasoning of an LLM as the primary "brain" for the paddle. Breakout is a fast-paced, chaotic physics game requiring decisions to be made in under 16.6 milliseconds (60 Frames Per Second). This is the story of what we tried, what worked, what didn't, and why.

---

## 1. Attempt #1: The Raw Physics Guesser

**The Goal:** Pass the raw game state to the LLM and ask it to predict the exact X-coordinate where the ball would land on the paddle.

**The Features (Inputs):** We sent the LLM a text prompt containing:
- The ball's current X and Y coordinates.
- The ball's velocity (speed and direction).
- The layout of the remaining bricks.

**The Trigger Condition:** The LLM was queried continuously, meaning the API request fired every single frame.

**The Output:** A single text number representing the target paddle coordinate.

### What Worked?
- The LLM successfully understood the rules of the game and the spatial context of the board.

### What Didn't Work & Why?
- **Synchronous Freezing:** The HTTP request to the LLM took several seconds. Because the request was "synchronous" (meaning the game had to stop and wait for the answer), the 60 FPS Pygame render loop completely froze every time the LLM was thinking. The game was unplayable.
- **Math Failure:** LLMs are text-prediction engines, not calculators. They are fundamentally incapable of calculating complex trigonometric functions or recursive ray-tracing (bounces) in their "heads". The LLM simply guessed the coordinates, and its guesses were wildly inaccurate. 

---

## 2. Attempt #2: Asynchronous Threading (Fire and Forget)

**The Goal:** We needed to unfreeze the game. We wrapped the LLM API call in an asynchronous Python background thread. 

**The Trigger Condition:** Instead of querying every frame, the prompt triggered exactly once per flight: the exact moment the ball reflected off the paddle (when `ball_dy` became negative). This gave the LLM the maximum possible time (the entire upward and downward flight) to respond.

**The Features (Inputs) & Output:** Same as Attempt #1.

### What Worked?
- **Smooth Gameplay:** The game rendered at a buttery smooth 60 FPS again without pausing. The background thread successfully updated the paddle's target coordinate upon completion without interrupting the animations.

### What Didn't Work & Why?
- **Fatal Latency:** The LLM was just too slow. Even with an entire flight path to think, the ball would often hit a brick and bounce all the way back down before the LLM finished generating its text response. By the time the LLM outputted the coordinate, the ball was already past the paddle and the game was lost. We even slowed the ball speed down to a crawl (30 px/s), but real-time control in a chaotic environment was impossible.

---

## 3. Attempt #3: The Tool-Augmented Strategic Manager

**The Goal:** Realizing the LLM was terrible at raw math, we abandoned asking it to predict physics. Instead, we equipped the LLM with custom Python "Tools" (Function Calling). 

**The Features (Tools provided to the LLM):**
1. `predict_landing_spot(ball_x, ball_y, dx, dy)`: A flawless mathematical ray-tracer that traces the ball's path into the future and returns the exact coordinate where it will hit the paddle.
2. `calculate_paddle_offset(target_brick)`: A geometric tool that calculates the precise paddle-angle offset required to bounce the ball directly into a specific brick.

**The Output:** The LLM's new prompt was to act as a **Strategic Manager**. It didn't output coordinates anymore. It outputted a chain of JSON Tool Calls:
1. Call the raytracer to find where the ball is naturally going.
2. Analyze the board to find high-value clusters of bricks.
3. Call the offset tool to calculate how to snipe those bricks.

**The Trigger Condition:** Triggered once when the ball leaves the paddle. If the ball reached the top bricks before the LLM responded, the game paused.

### What Worked?
- **Incredible Accuracy:** The LLM stopped guessing physics and relied on the flawless math tools. The resulting paddle intercepts were physically perfect.
- **Strategic Depth:** The LLM exhibited genuine intelligence, successfully prioritizing weak points in the brick wall.

### What Didn't Work & Why?
- **The "Dynamic Pausing" Compromise:** Because the LLM was still executing heavy tool-chains, it took several seconds to respond. To compensate, we implemented a system that would temporarily pause the ball in mid-air (while the game timer kept running) if the LLM was still thinking. 
- **The Conclusion:** While dynamic pausing guaranteed perfect shots, it felt highly unnatural for an arcade game. This experiment decisively proved that while an LLM is highly intelligent, a heavy transformer model is fundamentally unsuited for real-time, low-latency control loops without significant hardware acceleration. 

This conclusion directly led us to develop the lightning-fast Neural Network controller.
