"""Way 1, the direct call. Nobody decides the next step: there is one step.

Read the issue (ctx.call_tool(0, "read_issue", {"number": ctx.issue_number})),
make ONE model call that gets the issue plus ctx.repo_summary and no tools, turn
its answer into a comment with harness.formats.format_triage_comment, and post it
with ctx.call_tool(1, "post_comment", ...). Your code posts the comment, not the
model.

Trace every model call (ctx.trace.model_call(step, response)). ctx.call_tool
calls a tool and traces it in one go; its step is the model call it belongs to,
0 before the first.
Keep your prompt in prompts/ and load it with ctx.prompt("direct.md").
"""

from harness.formats import format_triage_comment, parse_triage_comment

def run(ctx) -> None:
     # 1. Reads the issue 
    issue = ctx.call_tool(0, "read_issue", {"number": ctx.issue_number})
 
    # 2. ONE model call: the issue plus the fixed repository summary, no tools.
    user_message = (
        f"Issue:\n{issue.content}\n\n"
        f"Repository summary:\n{ctx.repo_summary}"
    )
    response = ctx.client.create(
        system=ctx.prompt("direct.md"),
        messages=[{"role": "user", "content": user_message}],
    )
    ctx.trace.model_call(1, response)

    # 3. Turn the model's answer into a comment and post it.

    # If the model corrects itself, use its last answer.
    text = response.text
    last = text.lower().rfind("label:")
    label, file = parse_triage_comment(text[last:] if last >= 0 else text)
    
    body = format_triage_comment(label or "none", file)
    ctx.call_tool(1, "post_comment", {"number": ctx.issue_number, "body": body})
