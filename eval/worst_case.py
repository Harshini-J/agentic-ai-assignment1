"""Assignment 1, Part C: measure worst_case (F, A, N) from the agent's evaluation runs.

F is the mean prompt_tokens of the first call; A is the mean increase in
prompt_tokens over every pair of consecutive calls; N is max_steps. Writes only
the worst_case field of reports/LAB_01.json.

    python -m eval.worst_case
"""

import json

import yaml

from eval.summarize import ANSWERS, REPORT, load_runs

BOUNDS = "agent/bounds.yaml"


def main() -> None:
    answers = yaml.safe_load(ANSWERS.read_text())["eval"]
    runs = [r for r in load_runs(set(answers)) if r[0]["way"] == "agent"]

    firsts, increases = [], []
    for records in runs:
        prompts = [c["usage"]["prompt_tokens"] for c in records if c["type"] == "model_call"]
        firsts.append(prompts[0])
        increases += [b - a for a, b in zip(prompts, prompts[1:])]

    n = int(yaml.safe_load(open(BOUNDS))["max_steps"])
    f = round(sum(firsts) / len(firsts))
    a = round(sum(increases) / len(increases))

    report = json.loads(REPORT.read_text())
    report["worst_case"] = {"F": f, "A": a, "N": n, "cumulative_prompt_tokens": n * f + a * n * (n - 1) // 2}
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{len(runs)} agent runs: {report['worst_case']}")


if __name__ == "__main__":
    main()
