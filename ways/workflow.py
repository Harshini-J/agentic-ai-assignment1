"""Way 2, the workflow. Your code decides every step, in advance, in this order:

    read_issue  ->  one call to extract search terms  ->  search_repo
                ->  one call to choose the label and the file  ->  post_comment

A fixed sequence, no loop: the model never chooses a tool. Trace every model
call (ctx.trace.model_call); call every tool through ctx.call_tool(step, name,
input), which traces it. Keep your prompts in prompts/.

Part D reuses this way: its first half (read, extract, search) and its second
half (choose, post) are easier to reuse as two functions.
"""

from harness.formats import format_triage_comment, parse_triage_comment

def read_and_search(ctx):
    """First half: read the issue, get search terms, search for each term."""
    # 1. Read the issue.
    issue = ctx.call_tool(0, "read_issue", {"number": ctx.issue_number})

    # 2. One model call to extract search terms from the issue.
    response = ctx.client.create(
        system=ctx.prompt("workflow_extract.md"),
        messages=[{"role": "user", "content": issue.content}],
    )
    ctx.trace.model_call(1, response)

    # 3. Call search_repo with the extracted terms.
    search_terms = [line.strip() for line in response.text.splitlines() if line.strip()]
    search_result = ""
    for term in search_terms:
        result = ctx.call_tool(1, "search_repo", {"query": term})
        search_result += f"Search: {term}\n{result.content}\n\n"

    return issue.content, search_result

def choose_and_post(ctx, issue_text, results):
    """Second half: choose the label and file, then post the comment."""

    # 4. One model call to choose the label and file.
    response = ctx.client.create(
        system=ctx.prompt("workflow_choose.md"),
        messages=[{"role": "user", "content": f"Issue:\n{issue_text}\n\nResults:\n{results}"}],
    )
    ctx.trace.model_call(2, response)

    # 5. Turn the model's answer into a comment and post it.
    label, file = parse_triage_comment(response.text)
    body = format_triage_comment(label or "none", file)
    ctx.call_tool(2, "post_comment", {"number": ctx.issue_number, "body": body})

def run(ctx) -> None:
    issue_text, results = read_and_search(ctx)
    choose_and_post(ctx, issue_text, results)
