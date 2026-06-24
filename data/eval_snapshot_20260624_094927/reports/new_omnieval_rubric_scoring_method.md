# OmniEval Metrics Config v2 Scoring Method

Generated: 2026-06-24T11:14:27+09:00

## Active Source

The score snapshot is generated from the current UI runtime export:

```text
final_UI/data/question_cases.csv
```

Each row carries the model answer and `llm_judge_individual_scores`.

## Core Score

- Active metrics: ACC, COM, NAC, HAL_pass.
- Each metric is stored on a 0-1 scale in the generated CSV/JSON files.
- UTL, SAFE, FCT, and FMT are excluded from the active denominator.
- HAL is reported as `hal_rate`; `hal_pass` is used in `overall_score`.

```text
overall_score = mean(acc, com, nac, hal_pass)
pass_fail = Pass if overall_score >= 0.60 else Fail
```

## Gate Policy

| Gate | Values | Rule |
| --- | --- | --- |
| quality_gate | pass / fail | pass when overall_score >= 0.60 |
| safe_gate | not_applicable | SAFE is excluded from OmniEval v2 |
| judge_agreement_gate | pass / monitor / review | stable -> pass, borderline -> monitor, review_needed -> review |
| final_gate | pass / fail / review | judge review first, then quality fail/pass |

## Outputs

- `scores/new_omnieval_rubric_definition.csv`
- `scores/omnieval_metrics_config_v2.json`
- `scores/omnieval_consensus_case_scores.csv`
- `scores/new_omnieval_rubric_case_scores.csv`
- `scores/new_omnieval_rubric_gate_scores.csv`
- `scores/new_omnieval_rubric_model_scores.csv`
- `scores/new_omnieval_rubric_model_gate_summary.csv`
- `reports/new_omnieval_rubric_score_summary.json`
- `reports/omnieval_metrics_v2_score_snapshot.md`
