# OmniEval Metrics Config v2 Score Snapshot

Generated: 2026-06-24T11:14:27+09:00
Source run: eval_snapshot_20260624_094927

UTL is treated as N/A for every completed row and excluded from all denominators.
Scores are derived from the current UI export in `final_UI/data/question_cases.csv`.
Each row uses `llm_judge_individual_scores` when available; otherwise the row-level scored fields are used.

```
acc = mean(judge_acc)
com = mean(judge_com)
nac = mean(judge_nac)
hal_rate = 1 - mean(judge_hal_pass)
hal_pass = mean(judge_hal_pass)
overall_score = mean(acc, com, nac, hal_pass)
pass_fail = Pass if overall_score >= 0.60 else Fail
```

Rows converted: 12000
Average overall_score: 0.487469
Pass rate: 0.3744
UTL applicable rate: 0
