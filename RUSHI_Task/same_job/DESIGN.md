# Design and test plan: the same-job (finish-together) rule

**Owner:** Rushi Jhala (D5 extension). The rule, comparisons, success criteria and
predictions below were fixed before any run (see "History" at the end). Every run records
the SHA-256 of `policy.py`, `run.py` and the simulator code it ran with.

## Question

Does a simple placement rule, "put each task next to tasks of its own job", make Rohan's two
LR-MMT policies use less energy on the team's data?

- `lr_mmt_same_job`: Rohan's LR-MMT + the rule
- `lr_mmt_memory_same_job`: Rohan's memory-aware LR-MMT + the rule

## Why the rule should help

A server can only sleep when its **last** task leaves. Tasks of the same job (task group)
are created together, and in the team's trace they finish a median of 2 s apart, against
47 s for different jobs released in the same 5 minutes. (This was checked on the team's
4,000-group sample before the test was designed; `analyze.py` recomputes it into
`reports/premise_check.json`.) A server holding one job therefore tends to empty in one go,
while a server holding many jobs stays on until the slowest one ends.

## Is it new? (a literature search, not a systematic review)

- **Already known:** the goal of emptying servers by grouping work that ends together.
  - MinUsageTime dynamic bin packing, which assumes finish times are known in advance.
  - Microsoft's Resource Central (2017) and lifetime-aware placement (2023), and Google's
    LAVA/NILAS (2025), which use machine-learned lifetime predictions.
- **Appears new:** using job membership itself as a prediction-free signal that tasks will
  finish together, for energy-saving placement inside LR-MMT. No search found this. Claims
  should say "to our knowledge".

## The rule (`policy.py`)

Put a new task on a server that

1. is running work right now,
2. already has tasks of this job (by the policy's own records), and
3. stays under the controller's overload line after this task (Rohan's own `_pressure`
   test: memory 90%, CPU forecast × 1.2).

If several servers qualify, Rohan's original score picks among them. If none qualifies,
Rohan's policy decides exactly as before.

Why each condition is there:
- **1** stops the rule from waking a sleeping server or refilling an empty one. The policy
  is not told when a task finishes, so between controller ticks its records can name a
  server whose job-mates have already left.
- **3** stops the rule from overcrowding a server, which would make the controller move
  the job's tasks apart again (the opposite of the goal).

The controller (LR forecast, MMT, 30% underload rule, cooldowns) is inherited unchanged
and uses the same order for migration destinations. The policy sees only what the engine
gives every policy: each request's job id, host snapshots, and every 5 minutes the list of
running tasks. It never sees durations. No new numbers are introduced: the overload line
already exists in Rohan's controller. With the rule off, the code is Rohan's policy
exactly (unit test, `RUSHI_Task/tests/test_same_job.py`).

## Data and runs

The team's 9 cases only (250 / 1,000 / 4,000 groups × 3 SPECpower curves), with the same
tasks, 64 hosts and settings as `BASELINE_Comparison`. There are 36 runs:
- the two original policies, re-run with a read-only observer that counts how many
  different jobs share each busy server at every controller tick. Each re-run must
  reproduce the team's committed result (`RAW_Alibaba/reports/summaries.json`) in every
  field, or the run stops;
- the two new policies, with the same observer.

First Fit and Best Fit use the team's committed results.

## Comparisons and success criteria

| ID | Comparison | Question |
|---|---|---|
| S1 | `lr_mmt_same_job` vs `lr_mmt` | Does the rule improve LR-MMT? (main) |
| S2 | `lr_mmt_memory_same_job` vs `lr_mmt_memory` | Does the rule improve memory-aware LR-MMT? (main) |
| S3 | `lr_mmt_same_job` vs `first_fit` | Does LR-MMT + rule beat the simplest rule? |
| S4 | `lr_mmt_memory_same_job` vs `first_fit` | Does memory-aware + rule beat the simplest rule? |
| S5 | `lr_mmt_memory_same_job` vs `lr_mmt` | The team's question: does the proposal (with the rule) beat LR-MMT? |
| S6 | `lr_mmt_memory_same_job` vs `lr_mmt_same_job` | With the rule on both, does caring about memory help? |

**Works better** means:
1. less energy in more than half of the 9 cases;
2. lower total energy;
3. every win stays within the team's limits (`POLICY_Improvement/config.json`): mean and
   P95 wait +max(1 s, 5%), and pressure +0.01.

## Predictions (written before the first run)

- **Mechanism (strong):** with the rule, busy servers hold fewer different jobs, for both
  policies.
- **S1:** small, within about ±1.5% in total. Expected to save energy, mostly on the
  largest workload.
- **S2:** a larger saving than S1 on the largest workload. The original memory-aware score
  spreads a job's tasks over emptier servers (D5), so there is more to gather.
- **S5:** on the largest workload, memory-aware + rule probably still uses more energy than
  LR-MMT. The rule does not change where the **first** task of each job goes, and that is
  where the memory-aware spreading starts.
- **Side effects:** small. The rule never wakes a server, and condition 3 keeps it under the
  overload line, so waits and pressure should stay within the limits.

## Limits

The same 9 cases were used in D5, so this is not a test on unseen data, and the predictions
above are informed by D5's diagnostics. The guards: nothing is tuned, each policy runs once
per case, and this plan was fixed before any run. All results are reported, whichever way
they go.

## History

This plan, the rule and the predictions were first committed before any run, on Rushi's
local working branch (commit `742d058`, 26 November 2026). That branch also held
exploratory work that is not part of this pull request, so its history is not included
here. For this pull request the code was moved into this self-contained folder (only file
paths and docstrings changed; the rule's logic is identical) and all 36 runs were repeated.
