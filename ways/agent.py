"""Way 3, the agent. The model decides, at runtime, what to call and when to stop.

Write this in Part A, task 5: `make bounds-smoke` runs it.

Load your bounds (agent.loop.load_bounds()), then call agent.loop.run_loop with
ctx.client, ctx.tools (all three tools), a system prompt from prompts/, and a
first user message naming the issue. The agent posts its own comment through
post_comment. Your loop writes the trace, including trace.end.
"""

from agent.loop import load_bounds, run_loop


def run(ctx) -> None:
    # 1. Load the bounds from agent/bounds.yaml.
    bounds = load_bounds()

    # 2. Run the loop, which calls the model and tools until it stops or hits a bound.
    system = ctx.prompt("agent_prompt.md")
    user_message = f"Triage issue {ctx.issue_number}."
    run_loop(ctx.client, ctx.tools, system, user_message, bounds, ctx.trace)
