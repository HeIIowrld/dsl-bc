# Question Sets

## Final QA Schema

The final QA set is normalized to these columns:

| Column | Allowed values / meaning |
| --- | --- |
| `qa_category` | `사내FAQ`, `금융정보`, `카드상품` |
| `question_type` | `단일추론(사실추출)`, `비교대조`, `복합추론`, `수치추론/계산`, `민감` |
| `qa_topic` | `카드/결제`, `대출/여신`, `예적금`, `투자/펀드`, `일반 금융` |
| `instruction` | User-facing question or instruction sent to the model |
| `output` | Reference answer or expected output |

The UI still accepts legacy fields from older exports, but normalizes them as follows:

| Legacy field | Canonical field |
| --- | --- |
| `source_type` | `qa_category` |
| `qa_matrix_topic` | `qa_topic` |
| `difficulty` | `question_type` |

## Aggregation Policy

The QA matrix is a `3 x 5 x 5` grid: category by question type by finance topic.

Current scoring reports should prioritize one-dimensional aggregates because the current cell counts are not sufficient for stable per-cell evaluation. Two-dimensional slices and individual cells may still be rendered, but they should be marked as insufficient confidence until the minimum sample count is met.

Default reliability threshold:

| Slice | Minimum cases |
| --- | ---: |
| 1D aggregate | 30 |
| 2D aggregate | 30 |
| 3D cell | 30 |

## Final UI Defaults

The benchmark UI uses only these final question sets:

| File | Cases | Role |
| --- | ---: | --- |
| `out/test_cases/final_sets/benchmark_final_full_cases.jsonl` | 1,459 | benchmark |
| `out/test_cases/final_sets/regression_golden_full_cases.jsonl` | 220 | regression golden |

The source CSV files live under:

| Folder | Role |
| --- | --- |
| `questionlist/benchmark/` | final benchmark source files |
| `questionlist/regression/` | regression golden source files |

## UI Profiles

| Profile | Composition |
| --- | --- |
| `benchmark_smoke` | 100 sampled benchmark cases |
| `benchmark_full` | all 1,459 benchmark cases |
| `regression_golden_smoke` | 50 sampled regression cases |
| `regression_golden_full` | all 220 regression cases |

The UI catalog intentionally does not expose older generated pools or compatibility aliases.
