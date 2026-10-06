"""Assignment 1, Part A: the smallest tool-using loop you can write. This file is yours.

The contract (checks/FORMATS.md, section 3). The checker calls run_loop
directly, with a scripted model that never stops, a stub tool registry and its
own bounds, so keep this exact signature:

    run_loop(client, tools, system, user_message, bounds, trace) -> str

    client        harness.client.ModelClient: client.create(system=, messages=, tools=)
                  returns a ModelResponse; client.total_tokens is this run's running total
    tools         a registry: tools.schemas (definitions), tools.call(name, input) -> ToolResult
    system        the system prompt, a string
    user_message  the first user turn, a string
    bounds        a Bounds (below): max_steps, max_tokens, wall_clock_s
    trace         harness.trace.TraceWriter
    returns       the model's last text, possibly empty

Your loop must:
  1. Enforce all three bounds itself, in code, before each model call.
  2. Call trace.model_call(step, response) after every model call and
     trace.tool_call(step, call, result) after every tool call. Steps count from 1.
  3. Call trace.end(reason) exactly once, with the harness's reason for stopping:
     model_stopped, turn_limit, token_budget, wall_clock, tool_error or refusal.
     The model never reports its own ending.
  4. Append each assistant turn unchanged (response.assistant_message()) and send
     all of a step's tool results back in one user turn (harness.client.tool_result).

"turn_limit" means the loop made exactly max_steps model calls. "token_budget"
means client.total_tokens had reached bounds.max_tokens when the loop checked,
before its next call.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time

import yaml

from harness.client import tool_result


@dataclass(frozen=True)
class Bounds:
    max_steps: int        # model calls per run
    max_tokens: int       # prompt plus output tokens per run, from client.total_tokens
    wall_clock_s: float   # seconds per run


def load_bounds(path: Path | str = Path(__file__).parent / "bounds.yaml") -> Bounds:
    data = yaml.safe_load(Path(path).read_text())
    return Bounds(int(data["max_steps"]), int(data["max_tokens"]), float(data["wall_clock_s"]))


def run_loop(client, tools, system: str, user_message: str, bounds: Bounds, trace) -> str:

    messages = [{"role": "user", "content": user_message}]

    start = time.monotonic()
    step = 0
    last_text = ""

    while True:
        # 1. Enforce the three bounds in code, before the next model call.
        if step >= bounds.max_steps:
            reason, detail = "turn_limit", f"made {step} model calls"
            break
        if client.total_tokens >= bounds.max_tokens:
            reason, detail = "token_budget", f"{client.total_tokens} >= {bounds.max_tokens} tokens"
            break
        elapsed = time.monotonic() - start
        if elapsed >= bounds.wall_clock_s:
            reason, detail = "wall_clock", f"{elapsed:.1f}s >= {bounds.wall_clock_s}s"
            break

        # 2. One model call, traced, and its turn appended unchanged.
        step += 1
        response = client.create(system=system, messages=messages, tools=tools.schemas)
        trace.model_call(step, response)
        messages.append(response.assistant_message())
        last_text = response.text

         # 3. Did the model end its turn?
        if response.stop_reason == "refusal":
            reason, detail = "refusal", "the model declined"
            break
        if not response.tool_calls:
            reason, detail = "model_stopped", f"stop_reason {response.stop_reason}"
            break
 
        # 4. Run every tool the model asked for, then send all results back in one user turn.
        #    A tool that reports is_error goes back to the model, which may recover;
        #    a tool that raises ends the run.
        results = []
        try:
            for call in response.tool_calls:
                result = tools.call(call.name, call.input)
                trace.tool_call(step, call, result)
                results.append(tool_result(call, result.content, result.is_error))
        except Exception as exc:
            reason, detail = "tool_error", f"{call.name} raised {type(exc).__name__}: {exc}"
            break
        messages.append({"role": "user", "content": results})
 
    trace.end(reason, detail)
    return last_text