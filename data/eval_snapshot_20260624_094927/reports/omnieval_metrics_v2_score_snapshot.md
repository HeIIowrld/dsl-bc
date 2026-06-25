# OmniEval Metrics Config v2 Score Snapshot

Generated: 2026-06-24T19:17:11+09:00
Source run: WEB_EVAL_20260624_190250_base_deepseek_r1_distill_llama_8b_q4

Scores are derived from the current UI export in `final_UI/data/question_cases.csv`.
Each row uses `llm_judge_individual_scores`.

```
acc = mean(judge_acc)
com = mean(applicable judge_com; completeness=-1 excluded)
nac = mean(applicable judge_nac; numerical_accuracy=-1 excluded)
hal_rate = 1 - mean(judge_hal_pass)
hal_pass = mean(judge_hal_pass)
overall_score = valid_mean(applicable acc, com, nac, hal_pass)
pass_fail = Pass if overall_score >= 0.60 and critical_fail is false else Fail
```

Rows converted: 20
Average overall_score: 0.247917
Pass rate: 0.15
