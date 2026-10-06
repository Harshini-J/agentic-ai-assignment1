# Assignment 1 report · Four ways to triage an issue

Every number here also goes in `reports/LAB_01.json`, which the checker reads
(format: `checks/FORMATS.md`, section 7). Give each number its run count. Mark
any vendor figure you cite with its source type and date.

## Part 0 · The recorded trace
Model calls, tool calls, prompt tokens and the cached share, first and last
prompt size, cumulative over first. One sentence on what the growth means.

Growth means the agent's prompt size becomes larger over time because every step of a loop re-sends everything (the whole conversation) before it; over 21 model calls, the run used 29.7 times its first prompt instead of 21, so cost grows faster than the number of steps.

## Part A · Your loop's bounds
Your three bounds and why. Your worst case: *F*, *A*, *N*, and the cumulative
prompt tokens at your turn limit.

## Part A · Your loop's bounds

### Bounds (agent/bounds.yaml)

| Bound | Value | Why |
|---|---|---|
| `max_steps` | 10 | Provides sufficient model calls for the agent to complete a typical triage and perform extra searches when needed. A typical triage takes about 6-7 calls: read the issue, 2-4 searches, post, and stop. |
| `max_tokens` | 60,000 | Provides a sufficient token budget for a full 10-step run with multiple searches, about double the estimated worst case below (31,500), while staying well below the 400,000-token harness ceiling. |
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
| A `search_repo` result | I ran four searches on the code (`export`, `report`, `format`, `error`): each returned 10 lines, 762 to 879 characters, average 821 | ~205 |
| The model's tool request and its JSON wrapping | 64 in the smoke test (127 per step − 63 for the result), rounded up for larger requests | ~100 |
| **A** | | **~300** |

**Cumulative prompt tokens at the turn limit:**
N.F + A.N(N−1)/2 = 10 x 1350 + 300 x 10 x 9 / 2 = 13500 + 13500 = **~27000**

The chosen 60,000-token budget is well above the expected cost, so the run should normally hit the 10-step limit first. The token budget is there as a backup if the tool results are unusually large.

## Part B · Results
The table for all three ways: passes out of 60, per issue out of 10, the spread
(lowest and highest sweep), issues solved in every run, tokens, p50 and p95
latency, cost, tool calls.

## Part C · The decision
1. Find the diamond, for each way.
2. Your multipliers, and two differences from the vendor's 4×.
3. *f*, the blended cost, and the comparison with all-agent and all-workflow;
   then the slide's version, with *c*, *m* and *f* against the direct call.
4. Path entropy.
5. The four gates, one line of evidence each, and your verdict: agent,
   workflow or hybrid. If hybrid, where the line sits.
6. Your predictions: each one in `reports/PREDICTIONS_01.md` that missed, what
   you believed, and which trace shows why it was wrong.
7. The seven-layer audit: how many layers are empty (`ARCHITECTURE.md`).

## Part D · The hybrid
Your hand-off rule, and the Part B traces that led you to it (written before you
measure). Its row beside the three ways (the same columns as Part B's table), how many of
its runs handed the issue to the agent, and its measured cost per run beside your
blended cost from Part C, item 3. Does it change your Part C verdict? Which of
the four would you ship, and why?

## Assistance
Which AI tool, what it wrote, what you checked.
