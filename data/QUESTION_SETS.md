# Question Sets

## Current Runtime Sources

The runtime package uses the curated CSV files under `questionlist/` directly. Generated `out/test_cases/final_sets/*.jsonl` files are no longer the source of truth for the Final UI.

| Dataset ID / profile | Source file | Cases | Role | Release gate |
| --- | --- | ---: | --- | --- |
| `benchmark_final_full` | `questionlist/benchmark/benchmark_dataset_test.csv` | 800 | benchmark | Not gate-eligible |
| `regression_golden_full` | `questionlist/regression/regression_golden_set.csv` | 300 | regression | Pool is gate-capable, but current rows are not active-gold |
| `custom_seeded_mix` | User-selected quotas from catalog pools | variable | mixed | Depends on selected pools and case metadata |

`config/eval_dataset_catalog.yaml` is the catalog used by both the UI and `scripts/eval/compose_eval_dataset.py`.

Users with write access can also add CSV testsets from the Final UI testset tab. These files are stored under `questionlist/user_uploads/{benchmark|regression}/`, are auto-discovered as `user__benchmark__...` or `user__regression__...`, and are ignored by Git.

## Source CSV Schema

The checked-in CSV files use compact Korean source columns:

| Source column | Meaning | Normalized field |
| --- | --- | --- |
| `no` | Row number | fallback case ordinal |
| `id` | Stable case id | `case_id`, `question_id` |
| `대분류` | QA category/domain | `qa_category`, `source_type` |
| `금융토픽` | Finance topic | `qa_topic`, `qa_matrix_topic` |
| `문제유형` | Question type | `question_type` |
| `question` | User-facing prompt | `question`, `instruction` |
| `ground_truth` | Reference answer | `output`, `gold_answer`, `required_conditions` |
| `split_type` | Regression split only | source metadata for regression rows |

Uploaded CSV files should use at least `question` and `ground_truth`; `id` is recommended for stable case IDs.

## Current Distribution

Benchmark distribution:

| Dimension | Values |
| --- | --- |
| `대분류` | `금융정보` 500, `BCfaq` 150, `카드상품` 150 |
| `금융토픽` | `카드및결제` 250, `BCfaq` 150, `투자및펀드` 100, `일반금융` 100, `대출및여신` 100, `예적금` 100 |
| `문제유형` | `단일추론`, `비교대조`, `복합추론`, `수치추론및계산`, `민감` 각 160 |

Regression distribution:

| Dimension | Values |
| --- | --- |
| `대분류` | `general` 200, `hard_negative` 50, `edge_case` 50 |
| `금융토픽` | `투자및펀드` 57, `일반금융` 55, `대출및여신` 53, `카드및결제` 53, `예적금` 52, `재무회계` 30 |
| `문제유형` | `수치추론및계산` 100, `단일추론` 50, `비교대조` 50, `복합추론` 50, `민감` 50 |
| `split_type` | `general` 200, `hard_negative` 50, `edge_case` 50 |

## Lifecycle Notes

Composer lifecycle fields are injected at runtime:

| Field | Current behavior |
| --- | --- |
| `dataset_pool_id` | `benchmark_final_full` or `regression_golden_full` |
| `dataset_role` | `benchmark` or `regression` |
| `dataset_version` | `benchmark_dataset_test` or `regression_golden_set` |
| `source_hash` | Hash of the source CSV at compose time |
| `case_status` | Current CSV rows compose as `shadow` unless active-gold metadata is added |
| `gold_verified` | `false` for current CSV rows because no explicit `gold_verified` column exists |
| `release_gate_eligible` | `false` for current CSV rows until rows are marked active and gold-verified |

This means `regression_golden_full` is the curated regression source, but it is not yet an active release gate set by metadata. To make it gate-blocking, add explicit active-gold metadata such as `case_status=active` and `gold_verified=true` to reviewed rows or catalog defaults.

## Aggregation Policy

The QA matrix is category by question type by finance topic. Reports may render 1D, 2D, and 3D slices, but low-count cells should be treated as directional rather than conclusive.

Default reliability threshold:

| Slice | Minimum cases |
| --- | ---: |
| 1D aggregate | 30 |
| 2D aggregate | 30 |
| 3D cell | 30 |

## Related Runtime Files

| File | Purpose |
| --- | --- |
| `config/eval_dataset_catalog.yaml` | Dataset pool/profile catalog |
| `scripts/eval/compose_eval_dataset.py` | Resolves catalog profiles into JSONL cases |
| `scripts/eval/run_multi_model_eval.py` | Runs model evaluation and exports UI data |
| `final_UI/server.py` | Serves dataset summaries and starts evaluation jobs |
| `questionlist/user_uploads/` | Runtime-only CSV uploads from the UI, excluded from Git |
