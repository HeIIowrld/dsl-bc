# Scoring Logic

This document defines the active score contract for the retained BC finance QA
evaluation package.

## Active Schema

The active runtime CSV columns use the OmniEval v2 consensus metric set. The
score snapshot is packaged as:

```text
data/eval_snapshot_20260624_094927/scores/omnieval_metrics_config_v2.json
```

The current source of truth is the UI runtime export:

```text
final_UI/data/question_cases.csv
```

Each scored row must carry `llm_judge_individual_scores`. Snapshot generation
does not reconstruct judge scores from older row-level score columns.

| Field | Name | Scale | Source |
| --- | --- | --- | --- |
| `acc` | Accuracy | 0-1 | Mean of judge scores |
| `com` | Completeness | 0-1 | Mean of judge scores |
| `nac` | Numeric accuracy | 0-1 | Mean of judge scores |
| `hal_pass` | Hallucination pass | 0-1 | Mean of judge scores |
| `hal_rate` | Hallucination rate | 0-1 | `1 - hal_pass`; lower is better |

Rows use this score rule. `score_denominator` is the count of applicable
normalized metrics, not always 4:

```text
raw_metric_score = sum(applicable normalized metrics)
score_denominator = len(applicable_metrics)
overall_score = raw_metric_score / score_denominator
pass_fail = Pass when overall_score >= 0.60 and critical_fail is false
```

## Judge Contract

Judge responses must use OmniEval-style raw integer predictions:

```text
omnieval_scores.accuracy              # 0, 1, 2
omnieval_scores.completeness          # -1, 0, 1, 2
omnieval_scores.numerical_accuracy    # -1, 0, 1
omnieval_scores.hallucination         # 0, 1
critical_fail
error_type
reason
confidence
evidence_notes
```

The runner normalizes these raw values before aggregation:

```text
acc = accuracy / 2
com = excluded from applicable_metrics if completeness == -1 else completeness / 2
nac = excluded from applicable_metrics if numerical_accuracy == -1 else numerical_accuracy
hal_pass = 1 - hallucination
overall_score = mean(applicable normalized metrics)
```

The runner rejects schema-invalid JSON before aggregation. Missing score fields
are not converted to zero.

## Arbiter And Pass Policy

Base judges and arbiter judges use the same OmniEval v2 score contract.
Arbitration compares normalized 0-1 scores directly.

The runner marks a judge conflict when any of these are true:

- primary judges disagree on pass/fail
- primary judge `overall_score` gap is at least `0.30`
- primary judges report different non-`normal` error types

Conflict policy behavior:

- `review`: keep the primary aggregate and mark the conflict unresolved.
- `arbiter_override`: call the selected Arbiter only for conflict rows and use
  the Arbiter score as the final LLM judge score.
- `three_judge`: call the selected Arbiter only for conflict rows and aggregate
  base judges plus Arbiter.

The UI uses `arbiter_override` when an Arbiter config is selected. If no Arbiter
is selected, conflicts stay in review mode. Saved-answer rejudging must also
provide an explicit Arbiter config before an Arbiter policy is allowed.

```text
Pass when overall_score >= 0.60 and critical_fail is false
Fail otherwise
```

Arbitrated rows preserve audit fields:

```text
llm_judge_conflict_detected
llm_judge_unresolved_conflict
llm_judge_conflict_reason
llm_judge_conflict_resolution_policy
llm_judge_arbiter_config_id
llm_judge_arbitration_status
llm_judge_base_average_score
llm_judge_arbiter_score
llm_judge_arbiter_override
llm_judge_individual_scores
```

Release-gate status is separate and remains in:

```text
release_gate
gate_eligible_cases
pass_count
review_count
block_count
critical_fail_count
core_pass_rate
reason
```

Benchmark, shadow, draft, and unverified rows are analysis data and should not
be interpreted as deployment-blocking cases by themselves.

## Validation

Static checks that do not call external model APIs:

```powershell
node --check .\final_UI\app.js
python -m py_compile .\final_UI\server.py .\scripts\eval\run_multi_model_eval.py .\scripts\eval\apply_omnieval_metrics_v2.py
```
