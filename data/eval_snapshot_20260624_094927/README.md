# Eval Snapshot Data

This folder contains the current score and report snapshot generated from the
Final UI runtime export.

## Active Source

The active source of truth is:

```text
final_UI/data/question_cases.csv
final_UI/data/eval_runs.csv
final_UI/data/qa_slice_scores.csv
final_UI/data/run_release_gates.csv
```

`question_cases.csv` carries the model answer and each row's
`llm_judge_individual_scores`. The snapshot builder recomputes `scores/` and
`reports/` from those UI-exported rows.

## Scores

The active OmniEval v2 score uses 0-1 metrics:

```text
overall_score = mean(acc, com, nac, hal_pass)
pass_fail = Pass when overall_score >= 0.60
```

Only `acc`, `com`, `nac`, and `hal_pass` are part of the active denominator.

| File | Purpose |
| --- | --- |
| `scores/target_model_scores.csv` | Ranked target-model score table. |
| `scores/omnieval_metrics_config_v2.json` | Active metric scale and pass-policy config. |
| `scores/omnieval_consensus_case_scores.csv` | Compact case-level score table. |
| `scores/omnieval_consensus_summary.json` | Score snapshot summary. |
| `scores/judge_scores_overall.csv` | Judge score summary across all scored rows. |
| `scores/judge_scores_by_target_model.csv` | Judge score summary split by target model. |
| `scores/release_gates.csv` | Current release-gate summary derived from the UI export. |

## Reports

| File | Purpose |
| --- | --- |
| `reports/omnieval_metrics_v2_score_snapshot.md` | Human-readable score snapshot report. |
| `reports/new_omnieval_rubric_score_summary.json` | Machine-readable score summary. |
| `reports/new_omnieval_rubric_scoring_method.md` | Rubric notes for the active score schema. |

## Runtime Snapshots

`models/` and `inventories/` keep lightweight runtime references and file
inventories. Historical raw judge-response files are archived outside this
active snapshot tree.
