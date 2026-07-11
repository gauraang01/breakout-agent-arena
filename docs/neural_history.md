# Comprehensive History of Neural Network Approaches

After the LLM approach proved too slow for real-time control, we pivoted to training custom Neural Networks using PyTorch. The goal was to build a model with the intelligence of an LLM but with a sub-millisecond inference time that could run natively inside the 60 FPS Pygame loop.

## 1. Initial Multi-Layer Perceptron (Physics Engine) - `Commit 67c08e4`

Our first neural approach was a lightweight **Dense Feed-Forward Multi-Layer Perceptron (MLP)**. The theoretical goal was to train the neural network to act as an end-to-end physics engine. It received basic game state features and was trained via **Supervised Learning (Regression)** using Mean Squared Error (MSE) loss to predict the final X-coordinate landing spot of the ball.

### Pros & Cons
- **Pros:** Inference took less than a millisecond, completely solving the fatal latency issues we experienced with the LLM approach. The paddle tracked targets at 60 FPS.
- **Cons (The Butterfly Effect):** The model failed catastrophically. Neural networks fundamentally learn continuous functions (i.e., a small change in input yields a small change in output). Breakout physics, however, are highly chaotic and discontinuous. A 1-pixel shift in the ball's starting position can cause it to hit the corner of a brick instead of a flat edge, altering the final landing spot on the paddle by hundreds of pixels. 
- **The Result:** The continuous nature of the MLP couldn't learn this chaos. To minimize Mean Squared Error (MSE) during training, the network simply averaged all possible chaotic outcomes, causing the paddle to hover uselessly in the center of the screen, resulting in massive tracking errors (100+ mm).

---

## 2. Upgrading to 52 Inputs - `Commit aa58a7f`

We theorized that the model failed because it didn't have enough environmental context to map the bounces. We expanded the input layer of the **Supervised Feed-Forward MLP** from basic coordinates to 52 full features: `Ball X`, `Ball Y`, `Ball dX`, `Ball dY`, and 48 individual boolean states representing every brick on the board. We also standardized the map rendering so the model always received a uniform 52-length array regardless of how many bricks were destroyed.

### Pros & Cons
- **Pros:** The model now had full visibility of the entire game board, theoretically giving it the data required to calculate ricochets.
- **Cons (Architectural Failure):** Performance was still "absolutely bad." The core issue wasn't the lack of data, but the architectural inability of a dense MLP regression model to map chaotic trigonometric physics. The model continued to average the discontinuous outcomes.

*(Note: We also attempted spatial classification—dividing the screen into 50 probability bins to solve the regression averaging issue. However, this led to the **Expected Value Trap**, where a bimodal distribution (e.g., 50% chance of landing far left, 50% far right) would still average out to the dead center. When we forced it to pick the highest probability bin (Argmax), the paddle chattered violently between bins.)*

### Why not Reinforcement Learning (RL) or Recurrent Neural Networks (RNN/LSTM)?
We explicitly avoided **Reinforcement Learning (RL)** (like PPO or DQN) and **Unsupervised Learning** because RL is notoriously sample-inefficient. An RL agent requires millions of trial-and-error episodes to randomly stumble upon the basic physics of a bouncing ball before it even begins to learn strategy. By leveraging our mathematical raytracer to generate perfect ground-truth labels, we could use highly efficient **Supervised Learning** to train the model to superhuman levels in just a few minutes. 
We also considered **Recurrent Neural Networks (RNN/LSTM)** to track the ball's trajectory over time, but time-series models still suffer from the exact same continuous-chaos physics constraints as dense MLPs. Small errors in the physics prediction just endlessly compound and accumulate over the sequence.
---

## 3. The 2D Spatial CNN Aiming Agent - `Commit a336918`

Realizing that dense neural networks struggle with rigid mathematical physics, we completely overhauled the architecture. We abandoned the idea of making the Neural Network learn raw physics and instead modeled it after our successful LLM strategy: **Separate the Math from the Strategy.**

1. **The Math:** We brought back the deterministic mathematical raytracer from the LLM era to handle the chaotic base physics perfectly.
2. **The Vision:** We reconstructed the 52 raw features into a 2-channel 2D spatial image grid. Channel 0 contained the spatial arrangement of the bricks, and Channel 1 tracked the spatial location of the ball.
3. **The Strategy:** We swapped the dense MLP for a **Supervised Convolutional Neural Network (CNN)**. The CNN was trained via supervised regression *not* to predict where the ball would land, but to predict a **Strategic Offset** (-50 mm to +50 mm) that could be layered on top of the math raytracer's prediction to snipe specific bricks.

### Pros & Cons
- **Pros (Flawless Execution):** By delegating the chaotic physics to the raytracer, the CNN was free to leverage its natural spatial intuition to "see" gaps in the bricks and apply precise, intelligent offsets to the paddle. It achieves zero-latency superhuman gameplay.
- **Cons:** It is no longer a pure end-to-end neural solution, as it relies heavily on the hard-coded raytracer as a crutch.

---

## 4. Hardware Stabilization (The Trajectory Lock)

While the CNN Strategy worked beautifully in software, it revealed a severe hardware incompatibility. Because the CNN evaluates the board 60 times a second, as the ball descends pixel-by-pixel, the spatial dot moves across the CNN's input grid. This caused the CNN's output offset to fluctuate by 1-2 mm continuously (e.g., oscillating between an offset of 24.5 mm and 26.2 mm). 

In a software simulation, this just looks like a vibrating target line. But if deployed to a physical Arduino, this continuous micro-jitter would cause physical stepper motors to violently vibrate ("chatter"), overheating the drivers and stripping the gears.

**The Fix:** 
We implemented a **Trajectory Lock** in the neural controller. 
Because the mathematical base raytracer is perfectly accurate, its output does not change while the ball is falling in open air—it only changes when the ball physically bounces off a wall or a brick. We programmed the neural controller to use the math raytracer as a "Flight Path Check." If the mathematical landing spot hasn't changed since the last frame, the controller knows the ball is on the exact same flight path. It completely shuts off the CNN and **hard-freezes** the target line exactly where it was.

It only wakes the Neural Network back up to calculate a new strategic offset the instant the ball bounces off something. This completely eliminates motor jitter, guaranteeing that the Arduino executes a single, perfectly smooth, decisive sweep to catch the ball.
