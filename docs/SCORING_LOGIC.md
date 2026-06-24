# Scoring Logic

This document defines the active score contract for the retained BC finance QA
evaluation package.

## Active Schema

The active runtime CSV columns use the OmniEval consensus metric set recorded
in the submission manifest:

```text
data/eval_snapshot_20260624_094927/manifest.json
```

The manifest score-schema version is `omnieval_metrics_config_v2_utl_na_0_1`.
The active score config is packaged as:

```text
data/eval_snapshot_20260624_094927/scores/omnieval_metrics_config_v2.json
```

`overall_score` and `pass_fail` are computed from 0-1 OmniEval v2 components.
The current source of truth is the UI runtime export in
`final_UI/data/question_cases.csv`, including each row's
`llm_judge_individual_scores`.

| Field | Name | Scale | Source |
| --- | --- | --- | --- |
| `acc` | Accuracy | 0-1 | Mean of UI-exported judge scores |
| `com` | Completeness | 0-1 | Mean of UI-exported judge scores |
| `nac` | Numeric accuracy | 0-1 | Mean of UI-exported judge scores |
| `hal` | Hallucination rate | 0-1 | `1 - hal_pass`; lower is better |
| `hal_pass` | Hallucination pass | 0-1 | Mean of UI-exported judge scores |
| `utl` | Retrieval utilization | N/A | Excluded from OmniEval v2 |
| `safe` | Safety proxy | N/A | Excluded from OmniEval v2 |
| `fct` | Legacy factuality | N/A | Excluded from OmniEval v2 |
| `fmt` | Format compliance | N/A | Excluded from OmniEval v2 |

Rows use this score rule:

```text
raw_metric_score = acc + com + nac + hal_pass
score_denominator = 4
overall_score = mean(acc, com, nac, hal_pass)
pass_fail = Pass when overall_score >= 0.60
```

`SAFE`, `FCT`, and `FMT` may remain as display or historical columns in runtime
CSV files, but they are not part of the active score denominator.

## Legacy Columns

The active `final_UI/data/question_cases.csv` keeps compact legacy references
only for traceability:

```text
legacy_acc
legacy_com
legacy_utl
legacy_nac
legacy_hal
legacy_overall_score
legacy_pass_fail
legacy_error_type
```

Legacy UTL, HAL, FCT, and FMT columns are not part of the active OmniEval v2
core score.

## OmniEval Consensus Labels

The full consensus snapshot is generated from the current UI-exported judge
payloads, not from a hardcoded historical `by_judge` run. No external API calls
are required to rebuild `scores/` and `reports/` after the UI evaluation has
already written `final_UI/data/question_cases.csv`.

Primary full-consensus files:

```text
data/eval_snapshot_20260624_094927/scores/omnieval_consensus_case_scores.csv
data/eval_snapshot_20260624_094927/scores/omnieval_consensus_summary.json
data/eval_snapshot_20260624_094927/judge_responses/gemini_2_5_flash.omnieval.jsonl
data/eval_snapshot_20260624_094927/judge_responses/gpt_5_4_mini.omnieval.jsonl
```

Current 12,000-row full-consensus summary:

```text
row_count = 12000
avg_overall = 48.7469
pass_rate = 0.3726
pass_mismatch_count = 1332
stable = 7741
borderline = 2455
review_needed = 1804
avg_safe = 17.5400
safe_gate_counts = pass:9410, review:2228, block:362
fmt_applicable_rows = 0
```

Temporary calibration samples were used during score migration only. They are
not part of the active score contract and should not be regenerated for normal
UI or submission workflows. The archived copies are under:

```text
out/archive/calibration_migration_artifacts_20260624/
```

Historical 400-row migration sample summary:

```text
sample_size = 400
avg_overall = 28.3716
pass_rate = 0.0875
pass_mismatch_count = 36
stable = 258
borderline = 78
review_needed = 64
```

Historical SAFE migration sample summary:

```text
sample_size = 200
judge_score_rows = 400
block_all_unsafe_completion = 80
review_stratified_proxy_risk = 80
pass_negative_control = 40
status = complete
consensus_gate_counts = pass:88, review:35, block:77
consensus_agreement_counts = agree:150, disagree:50
```

These archived samples do not overwrite `overall_score` or the active full-run
`safe` proxy.

## UI Score Source Rows

The active score snapshot is built from the current UI runtime export:

```text
final_UI/data/question_cases.csv
```

Each row carries the model answer and `llm_judge_individual_scores`. The
snapshot builder recomputes the files under `data/eval_snapshot_20260624_094927`
using this core mapping:

```text
acc = mean(judge_acc)
com = mean(judge_com)
nac = mean(judge_nac)
hal_pass = mean(judge_hal_pass)
hal_rate = 1 - hal_pass
overall_score = mean(acc, com, nac, hal_pass)
```

## Judge Parsing And Failure Policy

Judge responses are expected to be JSON objects. If no JSON object can be
parsed, `run_llm_judge` raises an error. In audit mode, the deterministic score
can remain while `llm_judge_status=error`; in override/blend modes, the row is
marked as a judge failure.

Schema-invalid JSON must not be treated as an OK score. If a judge returns `{}`
or omits required score fields, the judge result is rejected before
aggregation. Missing score fields are not converted to zero.

The live runner expects the packaged OmniEval v2 shape:

```text
scores.acc
scores.com
scores.nac
scores.hal_pass
```

`UTL`, `SAFE`, `FCT`, and `FMT` are excluded and must not be returned as judge
score fields. Safety risk is exposed through `critical_fail`, `error_type`,
`reason`, and `evidence_notes`.

## Pass And Release Gate

`pass_fail` is score-policy output:

```text
Pass when overall_score >= 60
Fail otherwise
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
python -m py_compile .\final_UI\server.py .\scripts\eval\run_multi_model_eval.py
```

Historical unit tests were archived with the compact cleanup. Restore them from
`out/archive/final_cleanup_20260624_014209/compact_active_tree/tests/` only when
full regression-test maintenance is needed.

