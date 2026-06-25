# BC Finance LLM Evaluation Handoff

This repository contains the local handoff package for the BC finance QA
LLM evaluation dashboard. It keeps only the files needed to run the pipeline,
inspect saved benchmark and regression results, and verify the retained score
data.

The markdown handoff documents are intentionally ASCII-only so they render
reliably in Windows PowerShell, GitHub, copied folders, and remote shells. The
runtime CSV files, model answers, judge reasons, and UI labels can still contain
Korean text.

## Quick Start

Run from the repository root in PowerShell.

```powershell
python -m pip install -r .\requirements.txt
powershell -ExecutionPolicy Bypass -File .\scripts\run_final_ui.ps1 -Port 8512 -StopExisting
```

Open:

```text
http://localhost:8512
```

Default User IDs:

```text
admin / admin
user / user
```

Set `FINAL_UI_AUTH_USERS` only when you want to override these accounts.

Local demo mode without auth:

```powershell
$env:FINAL_UI_AUTH_DISABLED = "1"
python .\final_UI\server.py
```

## What Remains

| Path | Purpose |
| --- | --- |
| `final_UI/` | Local dashboard and API server |
| `final_UI/data/` | Current runtime CSV/JSON data used by the UI |
| `questionlist/benchmark/` | Benchmark question CSV |
| `questionlist/regression/` | Regression question CSV |
| `config/` | Dataset, scoring, and seeded model configuration |
| `scripts/eval/` | Core evaluation, saved-answer judging, and judge-merge scripts |
| `schemas/` | JSON schemas for cases, chunks, docs, and outputs |
| `data/eval_snapshot_20260624_094927/` | Generated score snapshot summaries and data inventories |
| `out/eval_runs/` | Retained raw judge score source files |
| `out/archive/` | Old runs, audit artifacts, logs, secrets, and retired docs |

## Current Saved Data

The generated score snapshot summaries are under:

```text
data/eval_snapshot_20260624_094927/
```

Important files:

| File | Contents |
| --- | --- |
| `scores/target_model_scores.csv` | Latest target model scores, ranked by overall score |
| `scores/judge_scores_overall.csv` | Gemini, GPT, and OmniEval consensus judge summary |
| `scores/judge_scores_by_target_model.csv` | Gemini, GPT, and OmniEval consensus summary split by target model |
| `models/target_models.scored.json` | Target model list derived from saved scores |
| `models/judge_models.scored.json` | Judge model list derived from saved scores |
| `inventories/judge_score_sources.csv` | Raw judge source file inventory with hashes |
| `scores/omnieval_metrics_config_v2.json` | Active score metric scale, denominator, and pass-policy config |
| `scores/omnieval_consensus_case_scores.csv` | 12,000-row OmniEval consensus case scores |
| `scores/omnieval_consensus_summary.json` | Full 12,000-row consensus summary and agreement statistics |
| `inventories/runtime_data.csv` | Current UI data inventory |
| `inventories/question_sets.csv` | Benchmark and regression question-set inventory |
| `manifest.json` | Source run and summary file map |

Active score summaries are generated from the current UI runtime export. The
UI evaluation run writes model answers and per-row `llm_judge_individual_scores`
to `final_UI/data/question_cases.csv`; the score snapshot builder then rewrites
the `scores/` and `reports/` files from that runtime data. The active OmniEval
v2 score contract uses `ACC`, `COM`, `NAC`, and `HAL_pass` on a 0-1 scale, and
`overall_score` is their mean.

Historical raw score sources are retained only as archived reference material.

Large derived run projections and per-target answer partitions were archived
under `out/archive/final_cleanup_20260624_014209/compact_active_tree/`.
Temporary calibration artifacts used only during score migration were archived
under `out/archive/calibration_migration_artifacts_20260624/`.

## Runtime Data Contract

Default UI data files:

```text
final_UI/data/eval_runs.csv
final_UI/data/question_cases.csv
final_UI/data/qa_slice_scores.csv
final_UI/data/run_release_gates.csv
final_UI/data/registered_target_models.json
final_UI/data/registered_judge_models.json
final_UI/data/judge_api_presets.json
```

Do not keep these in the active submission tree:

```text
final_UI/data/access_log*.jsonl
final_UI/data/server_*.log
final_UI/data/server_api_secrets.json
out/final_ui_cache/
out/rollback_snapshots/
out/ui_*_audit*/
out/desktop_ui_audit*/
```

Those files were moved to `out/archive/final_cleanup_20260624_014209/`.

## Validation

Static checks that do not call external model APIs:

```powershell
node --check .\final_UI\app.js
python -m py_compile .\final_UI\server.py
python -m py_compile .\scripts\eval\run_multi_model_eval.py
```

Opening saved results in the UI does not call external model APIs. API cost can
occur only when a user explicitly starts answer generation, judge scoring,
Arbiter scoring, or provider health checks.

## Documentation Map

| Document | Purpose |
| --- | --- |
| `docs/BC_LLM_REGRESSION_IMPLEMENTATION.md` | Pipeline and runbook |
| `docs/SCORING_LOGIC.md` | OmniEval v2 score contract and UI snapshot derivation policy |
| `data/QUESTION_SETS.md` | Benchmark and regression question-set contract |
| `data/eval_snapshot_20260624_094927/README.md` | Score snapshot file guide |
| `final_UI/README.md` | UI server and loading model |
| `docs/runbooks/CLOVA_STUDIO.md` | Clova Studio setup notes |

Archived but restorable material includes old docs, generated case builders,
historical tests, UI samples, and derived run projections.

