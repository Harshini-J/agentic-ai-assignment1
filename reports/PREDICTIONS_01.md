# Predictions

| Way | Passes expected (of 60) | Hardest issue | Why |
|---|---|---|---|
| Direct call | 34 | 4204 | The issue is likely related to date handling in src/util/, but the repository summary does not give the exact file name. So, the model may guess the wrong file. |
| Workflow | 41 | 4204 | The issue uses everyday words like “Monday” and “Tuesday,” which may not match the date logic. The workflow chooses all its search terms in one round before it sees the results, so it cannot try different terms when the first ones miss. |
| Agent | 45 | 4202 | The issue could be either a question or a feature request, so choosing the correct label may be difficult. Searching more does not help much with choosing the label, so the agent's advantage is limited here. |

## Per-issue expectations (passes out of 10)

| Issue | Direct | Workflow | Agent |
|---|---|---|---|
| 4201 Password reset email links to localhost | 3 | 6 | 7 |
| 4202 Export reports as TSV? | 5 | 5 | 5 |
| 4203 Every upload fails with "Malformed row" on row 1 | 5 | 9 | 9 |
| 4204 Monday summary email arrives on Tuesday | 3 | 4 | 7 |
| 4205 Do you keep our uploaded files after an import? | 9 | 8 | 8 |
| 4206 src/export/csv.ts merges rows with different currencies | 9 | 9 | 9 |
| **Total** | **34** | **41** | **45** |

## Reasoning from the dev runs (issues 4191 and 4192)

| Way | 4191 | 4192 |
|---|---|---|
| Direct call | 5 / 5 | 2 / 5 |
| Workflow | 3 / 3 | 2 / 3 |
| Agent | 1 / 1 | 1 / 1 |

- **Direct call:** It can only see the repository summary and cannot search the code. It passed 4191 in all 5 runs because `README.md` is mentioned in the summary. It passed 4192 in 2 of 5 runs because the file is inside `src/components/`, so the model had to guess the file name and gave different answers in different runs.

- **Workflow:** It can see search results, but it chooses all the search terms before seeing the results. On 4192, the first run used variable names that returned "No matches" and failed. After changing the prompt, one run still got no matches but guessed the right file, while another searched for "disabled" and found the correct file. So, the workflow works better when the issue words also appear in the code.

- **Agent:** It can use the search results to decide what to search next. On 4192, the first searches did not find anything, so it tried different words until "disabled" and "busy" found the right file. It was more accurate, but it cost about 5 to 10 times more than the workflow.
