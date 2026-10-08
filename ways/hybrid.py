"""Assignment 1, Part D: the hybrid.

Run the workflow. Before posting, apply the hand-off rule: if no search result
is in a source code file and the label is not `question`, hand the issue to the
agent instead of posting.
"""

from agent.loop import load_bounds, run_loop
from harness.formats import format_triage_comment, parse_triage_comment
from ways.workflow import read_and_search


def found_code(results: str) -> bool:
    """True if any search result line is in a source code file (src/, but not src/i18n/)."""
    for line in results.splitlines():
        if line.startswith("Search: ") or ":" not in line:
            continue
        path = line.split(":")[0]
        if path.startswith("src/") and not path.startswith("src/i18n/"):
            return True
    return False


def run(ctx) -> None:
    # 1. The workflow: read the issue, extract terms, search (steps 0 and 1).
    issue_text, results = read_and_search(ctx)

    # 2. The workflow's choice, with the same prompt, Not posted yet (step 2).
    response = ctx.client.create(
        system=ctx.prompt("workflow_choose.md"),
        messages=[{"role": "user", "content": f"Issue:\n{issue_text}\n\nResults:\n{results}"}],
    )
    ctx.trace.model_call(2, response)
    label, file = parse_triage_comment(response.text)

    # 3. The hand-off rule.
    if label != "question" and not found_code(results):
        # Hand off: the agent runs with its own prompt and bounds and posts the comment.
        # The loop writes the end record with its own terminal reason.
        bounds = load_bounds()
        system = ctx.prompt("agent_prompt.md")
        run_loop(ctx.client, ctx.tools, system, f"Triage issue {ctx.issue_number}.", bounds, ctx.trace)
        return

    # 4. No hand-off: the workflow posts its own answer; the runner writes `completed`.
    body = format_triage_comment(label or "none", file)
    ctx.call_tool(2, "post_comment", {"number": ctx.issue_number, "body": body})