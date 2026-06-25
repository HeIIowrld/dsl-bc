# BC Finance LLM Evaluation Handoff

This repository is the compact handoff package for the BC finance QA LLM
evaluation dashboard. It contains the UI, curated benchmark/regression question
sets, evaluation scripts, schemas, score snapshot summaries, and small demo CSV
files used to verify CSV ingestion.

Markdown handoff documents are kept ASCII-only so they render reliably in
Windows PowerShell, GitHub, copied folders, and remote shells. Runtime CSV
content, model answers, judge reasons, UI labels, and uploaded test data can
still contain Korean text.

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

## Repository Layout

| Path | Purpose |
| --- | --- |
| `final_UI/` | Local dashboard, API server, static assets, fonts, and UI README |
| `final_UI/data/` | Local runtime data directory; Git tracks only `.gitkeep` and `judge_api_presets.json` |
| `questionlist/benchmark/` | Tracked benchmark question CSVs |
| `questionlist/regression/` | Tracked regression question CSVs |
| `questionlist/user_uploads/` | Runtime CSV uploads from the UI; ignored by Git |
| `config/` | Dataset catalog, scoring matrix, risk taxonomy, and seeded model config |
| `scripts/eval/` | Evaluation runners, dataset composition, judge cache handling, scoring, and catalog helpers |
| `schemas/` | JSON schemas for cases, chunks, docs, tool-agent scenarios, and eval outputs |
| `data/QUESTION_SETS.md` | Question-set contract and CSV column mapping |
| `data/eval_snapshot_20260624_094927/` | Tracked score snapshot summaries, reports, inventories, and model lists |
| `docs/` | Pipeline, scoring, and implementation notes |
| `bc_card_demo_questions_10_typed.csv` | Small typed BC-card demo CSV for ingestion checks |
| `question_dataset_demo_10_custom.csv` | Small mixed-domain demo CSV for custom dataset checks |
| `out/` | Local run outputs, caches, logs, audits, and archives; ignored by Git |

## Question Dataset Flow

The shared static catalog is:

```text
config/eval_dataset_catalog.yaml
```

The runtime catalog builder is:

```text
scripts/eval/eval_dataset_catalog.py
```

It starts from the static catalog, discovers CSV files under
`questionlist/benchmark/`, `questionlist/regression/`, and
`questionlist/user_uploads/`, then adds runtime profiles for:

| Runtime profile | Meaning |
| --- | --- |
| `benchmark_default_full` | Current default benchmark dataset |
| `regression_default_full` | Current default regression dataset |
| `benchmark_registered_all` | All registered benchmark datasets |
| `regression_registered_all` | All registered regression datasets |
| `custom_seeded_mix` | Manually selected pool mix |

The default dataset selections are stored locally in:

```text
final_UI/data/question_dataset_settings.json
```

That file is runtime state and is ignored by Git. If it is missing or invalid,
the catalog helper falls back to the bundled benchmark and regression datasets.

`compose_eval_dataset.py` uses the runtime catalog by default:

```powershell
python .\scripts\eval\compose_eval_dataset.py --profile benchmark_default_full --output out\benchmark_cases.jsonl
```

Use `--static-catalog` when you need only the checked-in catalog file and no
runtime-discovered CSV datasets.

## Current Saved Data

The tracked score snapshot is under:

```text
data/eval_snapshot_20260624_094927/
```

Important files:

| File | Contents |
| --- | --- |
| `scores/target_model_scores.csv` | Target model scores ranked by overall score |
| `scores/judge_scores_overall.csv` | Gemini, GPT, and OmniEval consensus judge summary |
| `scores/judge_scores_by_target_model.csv` | Judge summary split by target model |
| `models/target_models.scored.json` | Target model list derived from saved scores |
| `models/judge_models.scored.json` | Judge model list derived from saved scores |
| `inventories/judge_score_sources.csv` | Raw judge source inventory with hashes |
| `scores/omnieval_metrics_config_v2.json` | Active metric scale, denominator, and pass-policy config |
| `scores/omnieval_consensus_case_scores.csv` | 12,000-row OmniEval consensus case scores |
| `scores/omnieval_consensus_summary.json` | Full consensus summary and agreement statistics |
| `inventories/runtime_data.csv` | UI runtime data inventory at snapshot time |
| `inventories/question_sets.csv` | Benchmark and regression question-set inventory |
| `manifest.json` | Source run and summary file map |

The active OmniEval v2 score contract uses `ACC`, `COM`, `NAC`, and `HAL_pass`
on a 0-1 scale. `overall_score` is the mean of those four components.

## Runtime Data Contract

The UI reads and writes runtime files in `final_UI/data/`. These files are local
state and are ignored by Git unless explicitly listed in `.gitignore` as tracked
exceptions.

Expected runtime files include:

```text
final_UI/data/eval_runs.csv
final_UI/data/question_cases.csv
final_UI/data/qa_slice_scores.csv
final_UI/data/run_release_gates.csv
final_UI/data/registered_target_models.json
final_UI/data/registered_judge_models.json
final_UI/data/question_dataset_settings.json
final_UI/data/judge_api_presets.json
```

Do not commit local secrets, logs, caches, or generated run output:

```text
.env
final_UI/data/access_log*.jsonl
final_UI/data/server_*.log
final_UI/data/server_api_secrets.json
out/
questionlist/user_uploads/
```

## API Cost Safety

Opening saved results in the UI does not call external model APIs. API cost can
occur only when a user explicitly starts answer generation, judge scoring,
Arbiter scoring, or provider health checks.

Judge cache loading is disabled when there are no judge configs or when scoring
is skipped, so saved-answer browsing and no-scoring runs stay local.

## Validation

Static checks that do not call external model APIs:

```powershell
node --check .\final_UI\app.js
python -m py_compile .\final_UI\server.py .\scripts\eval\compose_eval_dataset.py .\scripts\eval\eval_dataset_catalog.py .\scripts\eval\judge_saved_answers.py .\scripts\eval\run_multi_model_eval.py
```

Browser checks:

```text
initial page load does not request question_cases.csv
result-like tabs request question_cases.csv once
direct hashes work: #overview, #compare, #caseSets, #search
no API-costing endpoints are called unless a run is explicitly started
```

## Documentation Map

| Document | Purpose |
| --- | --- |
| `docs/BC_LLM_REGRESSION_IMPLEMENTATION.md` | Pipeline and runbook |
| `docs/SCORING_LOGIC.md` | OmniEval v2 score contract and UI snapshot derivation policy |
| `data/QUESTION_SETS.md` | Benchmark/regression CSV contract and upload behavior |
| `data/eval_snapshot_20260624_094927/README.md` | Score snapshot file guide |
| `final_UI/README.md` | UI server, tabs, loading model, and run output contract |

