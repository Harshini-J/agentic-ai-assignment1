# ARCHITECTURE.md · RepoMind on the seven layers

Assignment 1, Part C item 7 (Week 1, slide 43). For each layer: what does this job,
and where is it enforced. Cite code as a file path and line number joined by a
colon, inside backticks; the checker opens every reference. A layer held only by a
sentence in a prompt (any file under `prompts/`) is **EMPTY**, and so is a layer
nothing does yet. Status is one of: present, partial (say what is missing), or
**EMPTY**. Keep this file current: later assignments fill it in.

What each layer is for (Week 1, slides 40 to 42):

- **Model**: reasoning, choosing tools, generating text.
- **Harness**: runs the loop, builds each prompt, trims old history.
- **Tools**: where the system acts on the world.
- **Memory & State**: what survives a step, a session, a restart.
- **Control & Policy**: what the system may do, and when it must ask.
- **Observability**: a step-by-step record of what it did.
- **Evaluation**: measuring quality, before and after release.

| Layer | What does this job | Where it is enforced | Status |
|---|---|---|---|
| Model |  `claude-sonnet-5` reasons, picks tools and writes the label and file. | model set at `settings.yaml:24`; called at `agent/loop.py:79` | present |
| Harness | `run_loop` runs the loop and builds each prompt by appending every turn | loop at `agent/loop.py:56`; prompt built at `agent/loop.py:81` and `agent/loop.py:104` | partial: old history is never trimmed, so the prompt grows every step |
| Tools | `read_issue`, `search_repo`, `post_comment`, run by the loop | called at `agent/loop.py:98`; defined at `tools/read_issue.py:14`, `tools/search_repo.py:33`, `tools/post_comment.py:18`| present |
| Memory & State | the `messages` list holds the conversation within one run | `agent/loop.py:81`, `agent/loop.py:104` | partial: survives a step, but nothing survives to the next run or a restart |
| Control & Policy | three bounds checked in code before every model call, plus the harness's per-run token ceiling | `agent/loop.py:66`, `agent/loop.py:69`, `agent/loop.py:73`; ceiling set at `settings.yaml:42` and enforced by `harness/client.py:107` | partial: limits steps, tokens and time, but nothing approves or checks the public comment before it is posted; "post exactly one comment" exists only in the prompt |
| Observability | every model call, tool call and the run's ending are written to `runs/*.jsonl` | `agent/loop.py:80`, `agent/loop.py:99`, `agent/loop.py:106`; writer at `harness/trace.py:20` | present |
| Evaluation | the grounded check reads the tracker, not the agent's claims; `summarize.py` builds the results from the traces | `eval/check_triage.py:21`, `eval/summarize.py:50` | partial: measures quality before release on 6 known issues; nothing measures it after release |

**Empty layers:** 0 of 7. Slide 46 expects four to be missing from a first build:
memory and state, control and policy, observability, and evaluation. How does
yours compare?

None of the four layers is completely empty. The assignment includes the three bounds, traces in `runs/`, and the grounded checker. Still, all four layers are fairly basic:

- **Memory and state:** Nothing carries over between runs or restarts.
- **Control and policy:** The bounds limit steps, tokens, and time, but no one checks the comment before it is posted.
- **Evaluation:** Quality is tested only before release, on 6 known issues.
- **Observability:** Model calls, tool calls, and run endings are recorded.

Overall, the layers exist, but they are still basic. Observability is mostly complete, while memory, control, and evaluation could be improved.