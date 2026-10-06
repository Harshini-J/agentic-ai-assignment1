import json

from pathlib import Path

TRACE_FILE = Path("fixtures/week01_recorded_run.jsonl")
REPORT = Path("reports/LAB_01.json")

def read_lines(path):
    """Yield each JSON object in a JSONL file"""
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)

def calculate_prompt_tokens(usage):
    """Calculate the full prompt tokens for one model call."""
    return (
        usage.get("input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
    )

def calculate_metrics(trace_file):
    """Calculate metrics from a recorded run trace."""
    calls = {}
    tool_ids = set()

    # Read the trace and collect each model call's usage once, keyed by message.id,
    # because one model call can span several assistant lines with the same usage.
    # Also collect the id of every tool_use block, so each tool call is counted once.
    for record in read_lines(trace_file):
        if record.get("type") != "assistant":
            continue
        message = record["message"]

        if message["id"] not in calls:
            calls[message["id"]] = message["usage"]

        for content in message.get("content", []):
            if content.get("type") == "tool_use":
                tool_ids.add(content["id"])

    model_usages = list(calls.values())

    prompt_sizes = []

    # Calculate prompt tokens for each model call and store them in a list.
    for usage in model_usages:
        prompt_sizes.append(calculate_prompt_tokens(usage))

    # Calculate total prompt tokens and cache read tokens.
    total_prompt_tokens = sum(prompt_sizes)

    cache_read_tokens = 0

    for usage in model_usages:
        cache_read_tokens += usage.get("cache_read_input_tokens", 0)

    return {
        "model_calls": len(model_usages),
        "tool_calls": len(tool_ids),
        "prompt_tokens": total_prompt_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cache_read_share": round(cache_read_tokens / total_prompt_tokens, 4),
        "first_prompt": prompt_sizes[0],
        "last_prompt": prompt_sizes[-1],
        "cumulative_over_first": round(total_prompt_tokens / prompt_sizes[0], 2)
    }

def main(): 
    """Calculate metrics from a recorded run trace and update the report."""
    metrics = calculate_metrics(TRACE_FILE)
    report = json.loads(REPORT.read_text())
    report["part0"] = metrics

    REPORT.write_text( json.dumps(report, indent=2) + "\n" )

    print(metrics) 
    
if __name__ == "__main__":
    main()
