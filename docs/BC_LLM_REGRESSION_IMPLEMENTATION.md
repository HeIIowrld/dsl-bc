# Pipeline Runbook

This is the active runbook for the retained BC finance QA evaluation package.
It describes the current files and commands only. Historical implementation
notes and old PRDs are archived under `out/archive/final_cleanup_20260624_014209/`.

## Runtime Inputs

| Input | Path |
| --- | --- |
| Benchmark questions | `questionlist/benchmark/benchmark_dataset_test.csv` |
| Regression questions | `questionlist/regression/regression_golden_set.csv` |
| Dataset catalog | `config/eval_dataset_catalog.yaml` |
| Scoring and gate config | `config/eval_matrix.yaml` |
| Seeded model config | `config/seeded_target_models.yaml` |
| Current UI runtime data | `final_UI/data/` |

## Compose Cases

Benchmark:

```powershell
python .\scripts\eval\compose_eval_dataset.py `
  --profile benchmark_final_full `
  --seed 42 `
  --output .\out\test_cases\composed\benchmark_final_full_seed42.jsonl `
  --summary .\out\test_cases\composed\benchmark_final_full_seed42.summary.json
```

Regression:

```powershell
python .\scripts\eval\compose_eval_dataset.py `
  --profile regression_golden_full `
  --seed 42 `
  --output .\out\test_cases\composed\regression_golden_full_seed42.jsonl `
  --summary .\out\test_cases\composed\regression_golden_full_seed42.summary.json
```

The UI can also resolve these profiles through the Run tab.

## Run Evaluation

Static smoke:

```powershell
python .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\out\test_cases\composed\benchmark_final_full_seed42.jsonl `
  --config bc_gemma_9b_bcgpt_q4 `
  --limit 5 `
  --scoring-mode static
```

LLM judge run:

```powershell
python .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\out\test_cases\composed\benchmark_final_full_seed42.jsonl `
  --config bc_gemma_9b_bcgpt_q4 `
  --scoring-mode static_llm `
  --judge-config openai_gpt54_mini_judge
```

Multi-judge run with explicit Arbiter:

```powershell
python .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\out\test_cases\composed\benchmark_final_full_seed42.jsonl `
  --config bc_gemma_9b_bcgpt_q4 `
  --scoring-mode llm_override `
  --judge-config openai_gpt54_mini_judge `
  --judge-config gemini_2_5_flash_judge `
  --conflict-policy arbiter_override `
  --arbiter-config gemini_2_5_pro_arbiter
```

Arbiter configs must be explicit. The runner does not choose a default Arbiter.
The UI follows the same rule: no selected Arbiter means conflict rows remain in
review mode.

Provider credentials must be supplied through environment variables or the UI
secret store. Do not store real keys in repository files.

## Saved Run Contract

New saved runs should use:

```text
out/eval_runs/{RUN_ID}/
  artifact_manifest.json
  config.json or config.yaml
  model_outputs.jsonl
  judge_scores.jsonl
  judge_scores.csv
  question_cases.csv
  eval_runs.csv
  run_release_gates.csv
  regression_diff.csv
  by_judge/{judge_config_id}/judge_scores.jsonl
  by_judge/{judge_config_id}/judge_scores.csv
  by_target_model/{target_config_id}/model_outputs.jsonl
```

The active score/report snapshot is generated from the current UI runtime data
in `final_UI/data/question_cases.csv`, including the model answers and each
row's `llm_judge_individual_scores`. Large aggregate projections and per-target
answer partitions were moved to
`out/archive/final_cleanup_20260624_014209/compact_active_tree/`.

## UI Runtime Data

The dashboard reads these files by default:

```text
final_UI/data/eval_runs.csv
final_UI/data/question_cases.csv
final_UI/data/qa_slice_scores.csv
final_UI/data/run_release_gates.csv
final_UI/data/registered_target_models.json
final_UI/data/registered_judge_models.json
final_UI/data/judge_api_presets.json
```

Runtime-only files such as logs and `server_api_secrets.json` should stay out of
the active tree and are ignored by Git.

## Score Reuse

Raw model answers and judge scores are intentionally separated by the pipeline.
For this compact handoff, active raw evidence focuses on judge source rows while
large answer partitions are archived. This allows:

- recomputing aggregate scores without regenerating answers
- comparing judge sources such as GPT vs Gemini or GPT vs Clova
- running Arbiter review only on selected conflict candidates
- preserving per-judge evidence for later audit

The default judge cache directory is:

```text
out/eval_runs/_judge_cache/
```

Primary judge cache entries are keyed by answer model and judge model. Arbiter
cache entries add the base judge set and selected Arbiter model to the cache
namespace. This prevents one Arbiter model from reusing another Arbiter's
decision while still allowing repeated runs with the same judge set to avoid
extra API calls.

Generated score snapshot summaries are in `data/eval_snapshot_20260624_094927/`; retained raw judge
evidence stays in `out/eval_runs/`.

## Release Gate Status

The current bundled benchmark is for model comparison. The regression source is
curated, but rows are not blocking release-gate rows unless metadata marks them
as active and gold-verified.

Blocking release gates require:

```text
case_status = active
gold_verified = true
release_gate_eligible = true
deprecated != true
```

Rows without that metadata remain useful for analysis, comparison, and manual
review, but should not be treated as a hard deployment gate.

## Validation

```powershell
node --check .\final_UI\app.js
python -m py_compile .\final_UI\server.py
```

Run the UI:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_final_ui.ps1 -Port 8512 -StopExisting
```

