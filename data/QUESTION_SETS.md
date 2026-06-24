# Question Sets

The package uses the curated CSV files in `questionlist/` as the source of
truth for benchmark and regression cases.

## Retained Datasets

| Profile | Source file | Rows | Role | Gate behavior |
| --- | --- | ---: | --- | --- |
| `benchmark_final_full` | `questionlist/benchmark/benchmark_dataset_test.csv` | 800 | benchmark | Not gate-blocking |
| `regression_golden_full` | `questionlist/regression/regression_golden_set.csv` | 300 | regression | Gate-capable only after active gold metadata is present |
| `custom_seeded_mix` | catalog-selected pools | variable | mixed | Depends on selected pool metadata |

The shared catalog is `config/eval_dataset_catalog.yaml`. Both the UI and
`scripts/eval/compose_eval_dataset.py` read that catalog.

## Required CSV Contract

Preferred columns:

| Concept | Preferred column | Accepted aliases |
| --- | --- | --- |
| Stable case id | `id` | `case_id`, `question_id`, `qid` |
| User question | `question` | `instruction`, `input`, `prompt`, `query`, `user_question` |
| Reference answer | `ground_truth` | `output`, `answer`, `gold_answer`, `expected_answer`, `expected_output`, `reference_answer` |

Optional grouping columns:

| Concept | Preferred column | Accepted aliases |
| --- | --- | --- |
| Domain/category | `qa_category` | `category`, `source_type` |
| Topic/intent | `qa_topic` | `qa_matrix_topic`, `intent` |
| Question type | `question_type` | `qtype`, `type`, `task_type` |
| Forbidden claims | `forbidden_claims` | `must_not_include`, `hallucination_trap` |

The bundled CSV files use Korean source labels. The loader normalizes them into
the common fields above for scoring and UI display.

## Runtime Metadata

The composer injects runtime metadata:

| Field | Meaning |
| --- | --- |
| `dataset_pool_id` | Source pool or profile id |
| `dataset_role` | `benchmark` or `regression` |
| `dataset_version` | Source dataset version |
| `source_hash` | Source CSV hash at compose time |
| `case_status` | Usually `shadow` unless active metadata is supplied |
| `gold_verified` | `true` only for reviewed gold rows |
| `release_gate_eligible` | `true` only for rows allowed to affect release gate |

Release blocking requires:

```text
case_status = active
gold_verified = true
release_gate_eligible = true
deprecated != true
```

The retained regression CSV is curated regression material, but it should not be
treated as a hard deployment gate until that metadata is added.

## User Uploads

The UI can add CSV testsets from the Test Sets tab. Uploaded files are
stored under:

```text
questionlist/user_uploads/benchmark/
questionlist/user_uploads/regression/
```

These runtime uploads are ignored by Git.

## Inventory

The generated score snapshot inventory is:

```text
data/eval_snapshot_20260624_094927/inventories/question_sets.csv
```

It records row counts, byte sizes, and SHA-256 hashes for the retained
benchmark and regression CSV files.

