# Stage 4: Tool-Augmented LLM Agent

## Objective

Enhance the Breakout sandbox with a Tool-Augmented LLM Agent via Ollama. The game enters an agentic mode where an LLM is queried to make paddling decisions. It demonstrates tool use by requesting the trajectory from a python math engine instead of attempting to do the math internally.

## Controls

- `1`: Manual Mode
- `2`: Mathematical Controller
- `3`: Neural Network Controller
- `4`: LLM Agent Controller

## The "Bullet Time" Mechanic

When Mode 4 is active and the ball starts falling (dY > 0) past Y > 400, the game enters a "Bullet Time" freeze. The main game loop blocks to execute a synchronous sequence while pumping the UI:

1. **Initial Query**: A request is sent to `localhost:11434` with the ball's current vector and the tool schema for `predict_trajectory`.
2. **Tool Request**: The LLM acknowledges that the math is complex and outputs a tool call to `predict_trajectory`.
3. **Python Execution**: The Python engine evaluates `MathematicalController.predict()` and returns the exact target_mm back to the LLM.
4. **Final Target**: The LLM synthesizes this into a final JSON response `{"reasoning": "...", "target_mm": float}`.
5. **Resume**: The game unpauses, the V-HAL receives the `target_mm`, and the paddle accelerates towards the impact zone.

## Diagnostic UI

To visualize this process, the layout has been changed to a `1200x800` window featuring:
- `800x800` game arena
- `400x800` diagnostic sidebar

When Mode 4 is toggled, the borders switch to **Agentic Purple**. As the LLM loop executes, it prints a real-time trace in the sidebar:

```
[LLM] Analyzing ball vector...
[LLM] Math is too complex. Requesting tool: predict_trajectory()
[PYTHON] Executing MathematicalController... Output: 245.5mm
[LLM] Tool confirmed. Finalizing target: 245.5mm
[V-HAL] Accelerating paddle...
```

## Resilience

If the LLM hallucinates an incorrect format or the connection times out, the `LLMAgentController` gracefully defaults the target to the center (250.0 mm) without crashing the python runtime.
