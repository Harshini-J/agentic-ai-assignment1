"""Assignment 1, Parts B to D: build the tables in reports/LAB_01.json from your runs. This file is yours.

Read every trace in runs/ and the comments in the tracker, decide each run's
success with your eval/check_triage.check, and compute the `results` entry for
each way (direct, workflow, agent, hybrid) and the computed fields of `analysis`.
Write them into reports/LAB_01.json and leave every other field (part0,
worst_case, verdict) as you set it. Every field is defined in checks/FORMATS.md,
section 7. The checker recomputes the counts and means the same way, so compute
them here, from the traces, never by hand.

    python -m eval.summarize
"""

import json
import math
from collections import Counter
from pathlib import Path
 
import yaml
 
from eval.check_triage import check
from harness.tracker import Tracker
 
RUNS = Path("runs")
REPORT = Path("reports/LAB_01.json")
ANSWERS = Path("fixtures/answers.yaml")
WAYS = ("direct", "workflow", "agent", "hybrid")

def load_runs(eval_issues):
    """Every finished evaluation run (it has a run_end line), except the never-stops runs."""
    runs = []
    for path in sorted(RUNS.glob("*.jsonl")):
        if path.name.startswith("_"):          # skip runs/_ledger.jsonl
            continue
        records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        if not records or records[0]["type"] != "run_start" or records[-1]["type"] != "run_end":
            continue
        start = records[0]
        if start["backend"] == "never-stops" or start["issue"] not in eval_issues:
            continue
        runs.append(records)
    return runs

def percentile(values, p):
    """Nearest-rank percentile: the value at rank ceil(p/100 * n) in sorted order."""
    ordered = sorted(values)
    rank = max(1, math.ceil(p / 100 * len(ordered)))
    return ordered[rank - 1]
 
def summarize_way(way_runs, tracker, answers):
    """The results entry for one way."""
    per_issue = {str(issue): 0 for issue in sorted(answers)}
    runs_per_issue = Counter()
    sweep_passes = Counter()
    prompt, output, cached, cost, latency, tool_counts = [], [], [], [], [], []
 
    for records in way_runs:
        start = records[0]
        issue = start["issue"]
        passed = check(tracker, start["run_id"], issue, answers[issue])
 
        runs_per_issue[issue] += 1
        sweep_passes[start["sweep"]] += 0           # make sure every sweep appears, even with 0 passes
        if passed:
            per_issue[str(issue)] += 1
            sweep_passes[start["sweep"]] += 1
 
        calls = [r for r in records if r["type"] == "model_call"]
        prompt.append(sum(c["usage"]["prompt_tokens"] for c in calls))
        output.append(sum(c["usage"]["output_tokens"] for c in calls))
        cached.append(sum(c["usage"]["cache_read_input_tokens"] for c in calls))
        cost.append(sum(c["cost_usd"] or 0 for c in calls))          # an unpriced call counts 0
        latency.append(records[-1]["elapsed_s"])
        tool_counts.append(sum(1 for r in records if r["type"] == "tool_call"))
 
    n = len(way_runs)
    all_ten = sum(1 for issue in answers if runs_per_issue[issue] >= 10 and per_issue[str(issue)] == runs_per_issue[issue])
    return {
        "runs": n,
        "passes": sum(per_issue.values()),
        "per_issue": per_issue,
        "sweep_min": min(sweep_passes.values()),
        "sweep_max": max(sweep_passes.values()),
        "all_ten": all_ten,
        "mean_prompt_tokens": round(sum(prompt) / n, 2),
        "mean_output_tokens": round(sum(output) / n, 2),
        "mean_cached_tokens": round(sum(cached) / n, 2),
        "p50_latency_s": percentile(latency, 50),
        "p95_latency_s": percentile(latency, 95),
        "mean_cost_usd": round(sum(cost) / n, 6),
        "mean_tool_calls": round(sum(tool_counts) / n, 2),
        "max_tool_calls": max(tool_counts),
    }
 

def path_entropy(agent_runs):
    """Distinct tool-name sequences over the agent's runs, and the share the top three cover."""
    sequences = Counter(
        tuple(r["name"] for r in records if r["type"] == "tool_call") for records in agent_runs
    )
    total = sum(sequences.values())
    top3 = sum(count for _, count in sequences.most_common(3))
    return {"distinct_sequences": len(sequences), "top3_share": round(top3 / total, 3)}


def summarize_analysis(results, by_way):
    """The computed fields of `analysis`; a field stays unset when its inputs are missing."""
    analysis = {}
    direct, workflow, agent = (results.get(w) for w in ("direct", "workflow", "agent"))

    if direct and agent:
        direct_tokens = direct["mean_prompt_tokens"] + direct["mean_output_tokens"]
        agent_tokens = agent["mean_prompt_tokens"] + agent["mean_output_tokens"]
        analysis["ratio_agent_over_direct_tokens"] = round(agent_tokens / direct_tokens, 2)

    if workflow and agent:
        c = workflow["mean_cost_usd"]
        m = agent["mean_cost_usd"] / c
        issues = workflow["per_issue"]
        f = sum(1 for i in issues if workflow["per_issue"][i] < 5 and agent["per_issue"][i] >= 5) / len(issues)
        analysis["m_agent_over_workflow_cost"] = round(m, 2)
        analysis["f"] = round(f, 4)
        analysis["blended_cost"] = round(c * ((1 - f) + f * m), 6)
        analysis["all_agent_cost"] = round(c * m, 6)
        analysis["workflow_cost"] = round(c, 6)

    if by_way["agent"]:
        analysis["path_entropy"] = path_entropy(by_way["agent"])

    if by_way["hybrid"]:
        reasons = [r["terminal_reason"] for records in by_way["hybrid"] for r in records if r["type"] == "end"]
        analysis["hybrid_handoffs"] = sum(1 for reason in reasons if reason not in ("completed", "crashed"))

    return analysis


def main() -> None:
    answers = yaml.safe_load(ANSWERS.read_text())["eval"]
    tracker = Tracker()
    all_runs = load_runs(set(answers))
 
    by_way = {way: [r for r in all_runs if r[0]["way"] == way] for way in WAYS}
 
    report = json.loads(REPORT.read_text())
    for way in WAYS:
        if by_way[way]:                   
            report["results"][way] = summarize_way(by_way[way], tracker, answers)
 
    report["analysis"].update(summarize_analysis(report["results"], by_way))

    REPORT.write_text(json.dumps(report, indent=2) + "\n")

if __name__ == "__main__":
    main()
