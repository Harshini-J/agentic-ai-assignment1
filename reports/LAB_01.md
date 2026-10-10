# Assignment 1 report · Four ways to triage an issue

Every number here also goes in `reports/LAB_01.json`, which the checker reads
(format: `checks/FORMATS.md`, section 7). Give each number its run count. Mark
any vendor figure you cite with its source type and date.

## Part 0 · The recorded trace
Model calls, tool calls, prompt tokens and the cached share, first and last
prompt size, cumulative over first. One sentence on what the growth means.

| Measure | Value |
|---|---|
| Model calls | 21 |
| Tool calls | 23 |
| Prompt tokens (summed over calls) | 399,123 |
| Cache-read tokens | 388,338 |
| Cached share | 0.973 |
| First prompt | 13,445 |
| Last prompt | 24,188 |
| Cumulative over first | 29.69 |

Growth means the agent's prompt size becomes larger over time because every step of a loop re-sends everything (the whole conversation) before it; over 21 model calls, the run used 29.7 times its first prompt instead of 21, so cost grows faster than the number of steps.

## Part A · Your loop's bounds
Your three bounds and why. Your worst case: *F*, *A*, *N*, and the cumulative
prompt tokens at your turn limit.

### Bounds (agent/bounds.yaml)

| Bound | Value | Why |
|---|---|---|
| `max_steps` | 10 | Provides sufficient model calls for the agent to complete a typical triage and perform extra searches when needed. A typical triage takes about 6-7 calls: read the issue, 2-4 searches, post, and stop. |
| `max_tokens` | 60,000 | Provides a sufficient token budget for a full 10-step run with multiple searches, about double the estimated worst case below (27000), while staying well below the 400,000-token harness ceiling. |
| `wall_clock_s` | 180 | Provides sufficient time for the agent to complete its tasks without being constrained by a very short time limit or a very long one that could lead to unnecessary delays. |

### Worst case (estimated before real run)

**N = 10**, the chosen `max_steps`.

**F**, the prompt_tokens of a run's first call , at about 4 characters per token:

| Part | Characters | Tokens |
|---|---|---|
| Three tool definitions (`SCHEMA`s as JSON) | 759 | ~190 |
| System prompt (`prompts/agent_prompt.md`) | 970 | ~242 |
| First message ("Triage issue 4191.") | 18 | ~5 |
| Tool-use overhead added by the API (`make ping` used 987 prompt tokens with an almost empty prompt and one small tool) | | ~900 |
| **F** | | **~1,350** |

**A**, the increase in `prompt_tokens` from one call to the next. Between two calls the loop appends two things: the model's reply with its tool request, and the tool's result. So A is the size of those two:

| Part | How estimated | Tokens |
|---|---|---|
| A `search_repo` result | Four searches were run on the code (`export`, `report`, `format`, `error`): each returned 10 lines, 762 to 879 characters, average 821 | ~205 |
| The model's tool request and its JSON wrapping | 64 in the smoke test (127 per step − 63 for the result), rounded up for larger requests | ~100 |
| **A** | | **~300** |

**Cumulative prompt tokens at the turn limit:**
N.F + A.N(N−1)/2 = 10 x 1350 + 300 x 10 x 9 / 2 = 13500 + 13500 = **~27000**

The chosen 60,000-token budget is well above the expected cost, so the run should normally hit the 10-step limit first. The token budget is there as a backup if the tool results are unusually large.

### Worst case (measured after Part B)

Measured over the 60 agent evaluation runs (`python -m eval.worst_case`), these replace the estimate in `reports/LAB_01.json`:

| | Estimated | Measured | How measured |
|---|---|---|---|
| **N** | 10 | 10 | `max_steps` |
| **F** | ~1,350 | **966** | mean `prompt_tokens` of the first call, over 60 runs |
| **A** | ~300 | **354** | mean increase in `prompt_tokens` over all 257 consecutive call pairs |
| **Cumulative at the turn limit** | ~27,000 | **25,590** | 10 x 966 + 354 x 10 x 9 / 2 = 9,660 + 15,930 |

F came out lower than estimated because the ~900-token API overhead taken from `make ping` was too high; A came out higher because the model's tool requests and search results were somewhat larger than estimated. The 60,000-token budget is still more than twice the measured worst case.

### Smoke test

`make bounds-smoke` ran the agent against `NeverStops` (a model that never stops) on both dev issues, 4191 and 4192. Both runs ended on `turn_limit` after exactly 10 model calls (10,585 tokens each), so the step limit binds before the 60,000-token budget.

## Part B · Results
The table for all three ways: passes out of 60, per issue out of 10, the spread
(lowest and highest sweep), issues solved in every run, tokens, p50 and p95
latency, cost, tool calls.

60 runs per way: 10 sweeps over the six evaluation issues (4201 to 4206), model claude-sonnet-5.
Costs are priced from `pricing.yaml` (read 2026-06-24) by the metered client. All numbers are computed by `eval/summarize.py` from `runs/` and `tracker/comments.jsonl`.

| Way | Passes (of 60) | 4201 | 4202 | 4203 | 4204 | 4205 | 4206 | Sweep min | Sweep max | All 10 of 10 (Issues solved in every run) |
|---|---|---|---|---|---|---|---|---|---|---|
| Direct call | 45 | 10 | 10 | 10 | 0 | 10 | 5 | 4 | 5 | 4 |
| Workflow | 23 | 10 | 0 | 0 | 2 | 10 | 1 | 2 | 4 | 2 |
| Agent | 40 | 10 | 0 | 10 | 0 | 10 | 10 | 4 | 4 | 4 |

| Way | Prompt tokens | Uncached | Cached | Output tokens | p50 latency | p95 latency | Cost (USD) | Tool calls (mean) | Tool calls (max) |
|---|---|---|---|---|---|---|---|---|---|
| Direct call | 1573.0 | 1573.0 | 0.0 | 90.18 | 0.929 s | 5.036 s | 0.004048 | 2.0 | 2 |
| Workflow | 1309.42 | 1309.42 | 0.0 | 110.25 | 2.147 s | 4.683 s | 0.003721 | 5.55 | 6 |
| Agent | 10284.62 | 10284.62 | 0.0 | 550.13 | 6.534 s | 15.85 s | 0.026071 | 6.25 | 19 |

Token, latency, cost and tool-call figures are means per run, except the latency percentiles and the maximum. No prompt caching was used, so all prompt tokens are uncached.

## Part C · The decision
1. Find the diamond, for each way.

| Question | Direct call | Workflow | Agent |
|---|---|---|---|
| Does a person approve each step that matters? | No | No | No |
| Who picks the next step? | The code decides: read the issue, make one model call, and post the answer | The code decides: read the issue, get search terms, search each term, choose the answer, and post it | The model decides: replies with which tool to use next based on the previous result |
| Who ends the run? | The code ends it after posting the answer (`completed`) | The code ends it after posting the answer (`completed`) | The model ends it when it replies without a tool call (`model_stopped`). The bounds set limits the run if needed |
| Position | A fixed script with one model call | Workflow | An agent, bounded from outside |

Per component: in the direct call, the model only decides the content of the answer (label and file). In the workflow, the code decides the overall steps, but the model chooses the search terms. Since we do not limit the number of terms, the model also indirectly decides how many searches are made. In the agent, the model chooses the tools, their inputs, and when to stop, while the code runs the tools and enforces the three bounds. In all three ways, no person approves the comment before it is posted.

The model ended 51 of the 60 agent runs itself (`model_stopped`); the other 9, all on issue 4204, were ended by code's `turn_limit` bound after the agent kept searching without posting.

2. Your multipliers, and two differences from the vendor's 4×.

| Way | Mean prompt tokens | Mean output tokens | Tokens per run |
|---|---|---|---|
| Agent | 10284.62 | 550.13 | 10834.75 |
| Direct call | 1573.0 | 90.18 | 1663.18 |

Agent tokens per run / direct-call tokens per run = 10834.75 / 1663.18 = **6.51x**, against the lecture's ≈4x

Two differences:
1. **The baseline.** The lecture compares agents with chat interactions, where the person interacts with a model and conversation grows over several turns (it resends the whole conversation). We compare the agent with a single direct call, where there is exactly one model call per run (about 1573 prompt tokens and 90 output tokens). A single call is a smaller baseline than a whole chat, so the ratio comes out larger.

2. **The workload.** The lecture's number comes from Anthropic team's different real-world tasks in 2025. The results here, are from one specific small task: triaging 6 issues in a small repository, with 10 runs for each issue. An agent's token usage depends on how many steps the task takes and how large the tool results are. In our task, most of the tokens come from search results that are sent again in later steps, and there was no caching. So, a different task could give a different ratio.

m = mean agent cost / mean workflow cost = $0.026071 / $0.003721 = **7.0065**

3. *f*, the blended cost, and the comparison with all-agent and all-workflow;
   then the slide's version, with *c*, *m* and *f* against the direct call.

f is the share of evaluation issues where the workflow passed fewer than 5 of 10 runs and the agent passed 5 or more.

| Issue | Workflow passes | Agent passes | Agent earns it? |
|---|---|---|---|
| 4201 | 10 | 10 | No |
| 4202 | 0 | 0 | No, both fail |
| 4203 | 0 | 10 | Yes |
| 4204 | 2 | 0 | No, both fail |
| 4205 | 10 | 10 | No |
| 4206 | 1 | 10 | Yes |

f = 2/6 = **0.3333**

With c = $0.003721 (workflow mean cost per run) and m = 7.0065:

| Option | Formula | Cost per run | Passes |
|---|---|---|---|
| Workflow alone | c | $0.003721 | 23/60 |
| Blended | c × [(1 − f) + f × m] | $0.011171 | 23 + 19 = 42/60 (expected) | 
| All agent | c × m | $0.026071 | 40/60 |

The blend sends the 2 issues where the agent does better to the agent, and the other 4 issues to the workflow. It costs about 3.0x as much as using the workflow alone. Running everything through the agent costs 2.3x more than the blend, or about 7.0x the workflow.

**Against the direct call**
| Issue | Direct passes | Agent passes | Agent earns it? |
|---|---|---|---|
| 4201 | 10 | 10 | No |
| 4202 | 10 | 0 | No, direct succeeds |
| 4203 | 10 | 10 | No |
| 4204 | 0 | 0 | No, both fail |
| 4205 | 10 | 10 | No |
| 4206 | 5 | 10 | No, direct succeeds (5 is not fewer than 5) |

f = 0

With c = $0.004048 (direct call mean cost per run), m = 0.026071 / 0.004048 = 6.4405 and f = 0:

| Option | Formula | Cost per run | Passes |
|---|---|---|---|
| Direct call alone | c | $0.004048 | 45/60 |
| Blended | c × [(1 − f) + f × m] = 0.004048 × [(1 − 0) + 0 × 6.4405] | $0.004048 | 45/60 (same as direct call) |
| All agent | c × m | $0.026071 | 40/60 |

With f = 0, the blended cost equals the direct call alone, since no issue is sent to the agent.

**Which baseline Gate 4 should use:** the direct call. The assignment uses the workflow because it is the design which we would ship if the agent does not win, but on this evaluation set the direct call performed better. It passed 45/60 issues compared with 23/60 for the workflow, while the costs were close ($0.004048 vs. $0.003721). It also performed better than the workflow-based blend, which would have about 42/60 passes at $0.011171. So, the direct call is the baseline without the agent. Against this baseline, `f = 0` because the agent did not fix any issue that the direct call got wrong.

**Conclusion for gate 4:** against the direct call, the agent is not worth its multiplier on this evaluation set. It costs 6.4x more per run, f = 0, and it passes fewer issues (40/60 against 45/60).

**Cost of each extra correct triage** (extra cost per run / extra passes per run):

| Comparison | Extra cost per run | Extra passes per run | Cost per extra correct triage |
|---|---|---|---|
| Agent vs workflow | 0.026071 − 0.003721 = $0.02235 | (40 − 23) / 60 = 0.2833 | 0.022350 / 0.2833 = $0.0789 |
| Agent vs direct call | 0.026071 − 0.004048 = $0.022023 | (40 − 45) / 60 = −0.0833 | none: the agent passes fewer |

Against the workflow, the agent costs about $0.08 for each extra correct triage. Against the direct call, there is no extra benefit to buy because the agent costs 6.4x more per run and  passes fewer issues.

**Issues for Part D:** the agent passed more often than the workflow on 4203 (10 vs 0) and 4206 (10 vs 1). 

4. Path entropy.

Across the agent's 60 evaluation runs there are **9 distinct tool-call sequences**, and the three most common cover (22 + 15 + 9) / 60 = **0.767** of runs.

| Runs | Sequence |
|---|---|
| 22 | read_issue, search_repo ×2, post_comment |
| 15 | read_issue, search_repo ×3, post_comment |
| 9 | read_issue, post_comment |
| 4 | read_issue, search_repo ×17 (no comment) |
| 3 | read_issue, search_repo ×4, post_comment |
| 3 | read_issue, search_repo ×18 (no comment) |
| 2 | read_issue, search_repo ×16 (no comment) |
| 1 | read_issue, search_repo ×1, post_comment |
| 1 | read_issue, search_repo ×8, post_comment |

The 9 sequences fall into three groups:

- **Read, search 1 to 8 times, post (42 runs):** Normal triage pattern, which is similar to the workflow. The main difference was how many searches the agent decided to make.

- **Read, post with no search (9 runs):** All of these were on 4205, which the agent passed 10/10. So, skipping the search worked well for this issue.

- **Read, search 16 to 18 times, never post (9 runs):** All of these were on 4204. The runs reached the `turn_limit` after 10 model calls, so no comment was posted and all of them failed. These were also the most expensive runs, with up to 19 tool calls, but they did not produce a result.

**Which part is not worth the cost:** Letting the model control every next step. In 77% of the runs, the agent followed the normal pattern of reading, searching a few times, and posting, which the workflow already does with fixed code. The search terms and number of searches are also already chosen by the model in the workflow. This helped on some runs, such as skipping the search on 4205, but it also caused the repeated searches on 4204, which used the most resources and still failed. The sequences only show the tool names, so runs with the same sequence could still use different search terms. That is where the agent is  adapting to the issue.

5. The four gates, one line of evidence each, and your verdict: agent,
   workflow or hybrid. If hybrid, where the line sits.


| Gate | Answer | Evidence |
|---|---|---|
| 1. Does the task vary case to case? | Mostly no | Path entropy: 77% of agent runs followed one of the three most common sequences, all of the same shape: read the issue, search up to 3 times, post. The task varies more on issues such as 4203 and 4206, where the right search terms have to be found by trying different searches; there the workflow fails (0 and 1 of 10) while the agent passes 10 of 10. |
| 2. Can you limit the damage of a mistake? | Yes |The only write tool is `post_comment`; `read_issue` and `search_repo` only read, so the worst case is a wrong public label or file, not lost or changed data. The loop also has three bounds that stop runaway runs. For example, all 9 runs on 4204 that kept searching were stopped by `turn_limit` after 10 model calls. |
| 3. Will you catch it in time? | Partly | No person checks the comment before it is posted, but the triage comment is advice for a maintainer to review before making changes. So a wrong label or file can be noticed and corrected before any code changes are made. |
| 4. Is it worth the multiplier? |  Not as an all-agent design | Against the direct call, *f* = 0: the agent costs 6.4x more per run and passes fewer issues (40/60 vs. 45/60). Against the workflow, the agent is worth using only on 4203 and 4206, where it gets more correct triages, at about $0.08 per extra correct triage. |

Not all four gates pass for every issue, so an agent is not justified for the whole step. Gates 1 and 4 fail for most issues but pass for a few.

**RepoMind, gate by gate:**

| Gate | Issues the workflow's search can find | Issues where the workflow's search finds nothing |
|---|---|---|
| **The issues** | The issue's own words appear in the code (4201, 4205: workflow 10/10) | The issue's relevant words do not appear in the code (4203, 4206: workflow 0/10 and 1/10, agent 10/10 on both) |
| **1. Does the task vary case to case?** | No: read, choose search terms, search, and post | Yes: the right search terms have to be found by trying different searches |
| **2. Can you limit the damage of a mistake?** | Not asked: gate 1 sent it to a workflow | Yes: the tools are read-only except for one comment, and the loop has three bounds to stop runaway runs |
| **3. Will you catch it in time?** | Not asked | Partly: no one checks before posting, but a maintainer reads the comment before acting on it |
| **4. Is it worth the multiplier?** | Not asked | Yes against the workflow: 2 of 6 issues benefit from the agent. With *m* = 7.01, the blended cost is $0.011171 per run, about 3.0x the workflow cost, compared with $0.026071 for using the agent on all issues. It fixes 2 issues that the workflow usually fails. |

Two issues fit neither column: 4202 and 4204, where the agent also failed (0/10). On 4202, the direct call passed 10/10 while both search-based ways failed. On 4204, all three ways performed poorly, and the agent was the most expensive failure, with 9 of 10 runs reaching `turn_limit` without posting.

**Verdict: hybrid.** The line sits at the search. The workflow handles reading, searching, choosing, and posting. If its searches find nothing, the agent takes over the search, with the three bounds still enforced. 
Against the direct call the agent never earned its cost (f = 0), so this verdict depends on Part D: if the hybrid does not beat the direct call (45/60 at $0.004048), the verdict changes to workflow.

6. Your predictions: each one in `reports/PREDICTIONS_01.md` that missed, what
   you believed, and which trace shows why it was wrong.

**Totals and hardest issue:**

| Way | Predicted passes | Actual passes | Hardest predicted | Actual hardest |
|---|---|---|---|---|
| Direct call | 34 | 45 | 4204 | 4204 (0/10): correct |
| Workflow | 41 | 23 | 4204 | 4202 and 4203 (0/10): missed |
| Agent | 45 | 40 | 4202 | 4202 and 4204 (0/10): half right |

All three totals missed: the direct call was underestimated by 11, the workflow overestimated by 18 and the agent by 5.

A per-issue prediction counts as missed when it was off by 4 or more passes out of 10. Smaller differences can happen from normal run-to-run variation.

| Miss | What was believed | Trace | Why it was wrong |
|---|---|---|---|
| Workflow 4203: 9 → 0 | Searching the error message would find the file. | `workflow-4203-s01-00ce33` | The search only found `src/i18n/en.json`, where the error message is stored. Since the workflow could not search again, it guessed the file. |
| Workflow 4206: 9 → 1 | The title names the file, so it would be easy. | `workflow-4206-s01-e56221` | The searches mostly found docs and changelog lines, and it chose `src/util/dedupe.ts` instead of the file named in the title. |
| Agent 4204: 7 → 0 | The agent would keep trying until a search worked. | `agent-4204-s01-ecd1e6` | It found relevant code early, but kept searching for names that did not exist. It made 17 searches and hit `turn_limit` without posting. |
| Agent 4202: 5 → 0 | The label was the hard part. | `agent-4202-s01-56882e` | Two searches found a changelog line about `src/export/`, which led it to choose the wrong file. |
| Workflow 4202: 5 → 0 | The label was the hard part. | `workflow-4202-s01-e50bd5` | `TSV` found nothing, while `CSV` found the same changelog line. It then posted `src/export/`, which is a folder and could not pass. |
| Direct 4201: 3 → 10 | Without search, it would guess the file wrong. | `direct-4201-s01-98aa21` | The repository summary was enough for it to name the right file in every run. |
| Direct 4202: 5 → 10 | Same as 4201. | `direct-4202-s01-4b452d` | Without search, it was not misled by the changelog and named the right file in every run. |
| Direct 4203: 5 → 10 | Same as 4201. | `direct-4203-s01-58f266` | The summary pointed it to the right part of the code, and it named the right file in every run. |
| Direct 4206: 9 → 5 | The title names the file, so it would be right. | `direct-4206-s01-4cf7b5` and the other 9 runs | The label was always `bug`, but the file split 5–5 between `src/export/csv.ts` and `src/ingest/dedupe.ts`, so it passed only half. |
| Workflow 4201: 6 → 10 | Weak search terms might miss the file. | `workflow-4201-s01-817963` | The issue's words (`localhost:3000`, `reset-password`) appear in the code, so the search found the file directly. |

Overall, the predictions assumed that searching would usually help. The actual runs showed that this was not always true. Searching worked well on 4201, but it led both search-based ways to the wrong file on 4202, and the workflow on 4203 and 4206. The direct call passed 4201, 4202, and 4203 without searching.

7. The seven-layer audit: how many layers are empty (`ARCHITECTURE.md`).

**0 of 7 layers are empty**, but only three are fully present. The full audit and `file:line` references are in `ARCHITECTURE.md`.

| Layer | Status |
|---|---|
| Model | Present |
| Harness | Partial: the prompt grows at every step because old history is not trimmed. |
| Tools | Present |
| Memory & State | Partial: nothing carries over between runs. |
| Control & Policy | Partial: bounds are enforced, but the comment is not checked before posting. |
| Observability | Present |
| Evaluation | Partial: testing uses only six known issues. |

It is expected for the four layers to be missing in a first build. In this project, all four have at least some implementation: bounds, traces, and a grounded checker. Observability is the only one that is fully present among these four.

Control and policy is the weakest. The rules to post exactly one comment and use a valid label are only in the prompt, not enforced by code, so the agent could still break them.

## Part D · The hybrid
Your hand-off rule, and the Part B traces that led you to it (written before you
measure). Its row beside the three ways (the same columns as Part B's table), how many of
its runs handed the issue to the agent, and its measured cost per run beside your
blended cost from Part C, item 3. Does it change your Part C verdict? Which of
the four would you ship, and why?

### Hand-off rule (written before measuring)

**Rule:** The workflow runs as before: it reads the issue, extracts search terms, searches, and chooses a label and file. Before posting, it checks the search results. **If none of the results is from a source code file** (all matches are in `docs/`, `CHANGELOG.md`, `README.md`, or `src/i18n/`, or there are no matches), **and the label is not `question`**, it hands the issue to the agent. Otherwise, the workflow posts its answer.

**How the rule was chosen.** In Part B, the workflow had 37 wrong and 23 correct answers. The three suggested rules were tested on all 60 runs, but they were not very useful, so the traces were read and rule D came from them.

| Rule | Wrong answers handed off (expected) | Right answers handed off (expected) |
|---|---:|---:|
| A: every search returned `No matches` | 0/37 | 0/23 |
| B: chosen file is not in search results | 34/37 | 3/23 |
| C: no file named and label is not `question` | 0/37 | 0/23 |
| **D: no source code file in search results and label is not `question`** | **32/37** | **0/23** |

- **A and C** never fired because the workflow always found something and always named a file.
- **B** caught the most wrong answers but also handed off 3 correct ones (two on 4204, one on 4206).
- **D** caught almost as many wrong answers as B (32 vs 34) and did not hand off any correct ones.

### Rule D by issue (expected, from Part B traces)

| Issue | Workflow result (Part B) | Wrong handed off (expected) | Right handed off (expected) |
|---|---|---:|---:|
| 4201 | 10 right | 0 | 0 |
| 4202 | 10 wrong | 10 | 0 |
| 4203 | 10 wrong | 10 | 0 |
| 4204 | 8 wrong, 2 right | 8 | 0 |
| 4205 | 10 right | 0 | 0 |
| 4206 | 9 wrong, 1 right | 4 | 0 |

### What the traces showed

- **4203:** The search only found `src/i18n/en.json`, so the workflow guessed the code file.
- **4201:** The search found a source file matching the issue's own words, and the workflow got the answer right.
- **4204:** The two runs that found a source file were right; the other eight were wrong.
- **4205:** The workflow correctly answered `question` with `file: none`, so the rule keeps this case from being handed off.

### Expected weaknesses

Rule D would hand off 18 runs on issues 4202 (10) and 4204 (8). These hand-offs add cost but no correct answers, since the agent also scored 0/10 on both issues. The rule also misses 5 of the 9 wrong answers on 4206 because those searches found source code, just not the right file. As a result, the workflow keeps its wrong answer instead of handing off to the agent.

Some trace excerpts cut off search results, so the actual hybrid may fire less often.

**This result is optimistic:** the rule was chosen using these same six evaluation issues, so it may not work as well on new issues.

### Results (measured after the rule was written)

| | Direct | Workflow | Agent | Hybrid |
|---|---:|---:|---:|---:|
| Passes (of 60) | 45 | 23 | 40 | **35** |
| Cost per run | $0.004048 | $0.003721 | $0.026071 | **$0.009768** |
| Runs handed to the agent | – | – | – | **13** |

Hybrid row in full: 35/60 passes, sweeps 3–5, 3 issues at 10/10, 3571.58 prompt tokens and 262.45 output tokens per run, p50 2.331 s, p95 15.966 s, $0.009768 per run, 6.6 tool calls per run on average (max 13).

The hybrid passed 12 more than the workflow and 5 fewer than the agent, at 2.6 times the workflow's cost and 0.37 times the agent's. Each extra correct triage over the workflow cost about $0.03, against about $0.08 for the agent alone.

**Hand-offs:** 13 of 60 runs. Counted from the `end` records: 13 runs ended with an agent-loop reason (such as `model_stopped`), and the other 47 ended with `completed`, written by the runner.

**Did they land where the agent earns its cost?** Yes. The agent did better on 4203 (workflow 0/10, agent 10/10) and 4206 (workflow 1/10, agent 10/10). All 13 hand-offs were on these two issues, and none were on the other four.

| Issue | Agent earns its cost (Part C)? | Hand-offs (expected) | Hand-offs (actual) | Hybrid passes |
|---|---|---:|---:|---:|
| 4201 | No | 0 | 0 | 10 |
| 4202 | No | 10 | 0 | 0 |
| 4203 | **Yes** | 10 | **10** | 10 |
| 4204 | No | 8 | 0 | 2 |
| 4205 | No | 0 | 0 | 10 |
| 4206 | **Yes** | 4 | **3** | 3 |
| **Total** | | **32** | **13** | **35** |

On 4203, all 10 runs were handed off and passed, matching the agent's results. On 4206, only 3 runs were handed off, so the hybrid missed most of the agent's benefit. Issues 4202 and 4204 were never handed off, so their results stayed the same as the workflow's: 0 and 2 passes. The 18 wasted hand-offs predicted for 4202 and 4204 did not happen: in the live runs, their full search results included a source file that the trace excerpts had cut off.

**Measured cost against the Part C blend:** $0.009768 measured, against $0.011171 blended. The gap has two causes:

1. **Fewer runs went to the agent, so the hybrid was cheaper.** The blend assumed 33% of runs would use the agent, but the hybrid handed off only 13 of 60 runs (21.7%). With 21.7% in the same blend formula, the estimate would be 0.003721 × [(1 − 0.217) + 0.217 × 7.01] ≈ $0.0086.

2. **Each run that went to the agent cost extra, which made it more expensive.** The blend counts a handed-off run as one agent run. In the hybrid, a handed-off run pays for both: first the workflow's steps (extract, search, choose), then the full agent run. So the real cost came out above $0.0086, at $0.0098.

**Does it change the Part C verdict?** By the condition written in Part C, it should: Part C said the verdict changes to workflow if the hybrid does not beat the direct call (45/60 at $0.004048), and it did not (35/60 at $0.009768, 2.4 times the cost). The verdict here stays hybrid anyway, which departs from that condition. The reason is that the condition compared the hybrid with the wrong alternative. The verdict chooses among agent, workflow and hybrid, and switching to workflow would make things worse: the workflow passed 23/60 against the hybrid's 35/60. Among those three, the hybrid is still the best trade-off: 12 more passes than the workflow and only 5 fewer than the agent, at 37% of the agent's cost.

**Which of the four to ship.** For this repository, the direct call is the one to ship, provided `repo_summary.md` is kept up to date. It had the most passes (45/60), low cost ($0.004048), and the lowest p50 latency (0.93 s). However, it can guess the wrong file when the summary falls short, as seen on 4206. If the summary cannot be maintained or the repository grows, the hybrid is the better choice because it searches first and hands off when it finds no source code. Unlike the direct call, the hybrid can search the live code when the repository summary is incomplete. These results are limited because all approaches were tested on the same six issues, and the hybrid rule was chosen using those issues.

## Assistance
Which AI tool, what it wrote, what you checked.

**AI tools:** Anthropic Claude Code; GitHub Copilot (inline autocomplete in VS Code)

**Date:** 5 - 9 October 2026

**Understanding the existing codebase:** Claude Code helped me understand the starter code before I wrote my own: what each tool in `tools/` does and where its definition (`SCHEMA`) is, what the harness provides (`harness/client.py`, `harness/trace.py`, `harness/runner.py`, `harness/formats.py`, `harness/tracker.py`), what `ctx` provides (`ctx.prompt`, `ctx.call_tool`, `ctx.issue_number`, `ctx.repo_summary`), and where each format is defined in `checks/FORMATS.md`.

I used it to explain parts of the assignment I didn't understand. 

- **Part 0:** how each metric is calculated from the recorded trace, and why a repeated message ID is counted once.
- **Part A:** how the loop in `agent/loop.py` works, how to estimate F, A and the worst-case cumulative prompt tokens, and how and why bounds are chosen.
- **Part B:** what the grounded check is, and what each field in `eval/summarize.py` means (sweeps, all-ten, percentiles, cached tokens).
- **Part C:** path entropy and which part of the agent is not earning its cost; the four gates; and what "which trace shows why it was wrong" means.
- **Part D:** what a hand-off is, how to choose a hand-off rule from the workflow traces, and how to count hand-offs from the `end` records.

**What it wrote:**

- Claude Code: drafts of all the prompts in `prompts/`, `eval/summarize.py` and `eval/worst_case.py`, which I edited and ran
- Claude Code: one-off commands for reading and understanding traces and testing hand-off rules
- Claude Code: parts of `loop.py`, where it helped me understand the sequence of how it flows and helped with some parts of drafts.
- Claude Code: `part0.py`, reading and parsing the JSONL correctly and writing the results to `LAB_01.json` (the metrics and calculations were done by me, with GitHub Copilot autocomplete)
- Claude Code: `hybrid.py`, a draft of the `found_code` function
- Claude Code: `ARCHITECTURE.md`, searched the repo and identified where the model call and tools are invoked
- GitHub Copilot: inline autocomplete suggestions while I was coding


**What I checked:**

- **Prompts in `prompts/`:** Tested each approach on the dev issues and reviewed the traces. Updated the direct-call prompt after it posted an incomplete answer and the workflow prompt after it used search terms that returned "No matches."
- **`eval/summarize.py` and `eval/worst_case.py`:** Checked the fields against `checks/FORMATS.md` (Sections 4 and 7), compared the summary with the Part B results and Part C calculations, and verified the worst-case formula: 10 × 966 + 354 × 45 = 25,590.
- **`agent/loop.py`:** Ran `make check-01` to test the bounds and `make bounds-smoke` to confirm both runs stopped at `turn_limit` after 10 model calls.
- **`eval/part0.py`:** Compared its output with the recorded run and ran `make check-01`.
- **Hand-off rule and `ways/hybrid.py`:** Rechecked the rule counts on all 60 workflow traces, tested `found_code` with the `question` exception, and confirmed it. Also ran a dev test and checked hand-offs and passes per issue after evaluation.
- **60-run results:** Verified pass/fail using `eval/check_triage.py`, which checks the actual tracker comments. Ran `make check-01` to recompute counts and means, and spot-checked individual traces.
- **`ARCHITECTURE.md`:** Verified each `file:line` reference using `grep -n`.
- I checked every autocomplete suggestion manually.