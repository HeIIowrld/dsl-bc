# Local Evaluation UI

The local evaluation UI is the dashboard for browsing saved benchmark/regression
results and starting new evaluation jobs.

## Run

Run from the repository root:

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

Demo mode without auth:

```powershell
$env:FINAL_UI_AUTH_DISABLED = "1"
python .\final_UI\server.py
```

## Tabs

| Tab | Purpose |
| --- | --- |
| Settings | Target model, judge model, API env, and health check setup |
| Test Sets | Benchmark/regression dataset preview and CSV upload |
| Run | Model selection, judge selection, dry-run, and real evaluation execution |
| Results | KPI, release gate summary, matrix, detail panel, and charts |
| Compare | Model-level and run-level comparisons |
| Pass/Fail Overview | Failure type summary and review queue |
| Per-Case Responses | One question with all model answers and judge reasons |
| Search | Search over questions, answers, reasons, and error types |

## Data Loading

| Data | Load timing |
| --- | --- |
| `eval_runs.csv` | Initial load |
| `run_release_gates.csv` | Initial load |
| `question_cases.csv` | First result-like tab only |
| `api/eval/runs` | Background after first render |
| `api/eval/judge-comparison/options` | Background after first render |
| `api/questionlist/datasets` | Initial metadata load |
| `api/questionlist/dataset-cases` | Test Sets preview |

The large `question_cases.csv` file is loaded lazily. The default Run tab should
not fetch it.

## Run Tab Judge Controls

The Run tab separates primary judges from conflict arbiters.

- Primary judge options come from `registered_judge_models.json` entries with
  `judge_role=judge`.
- Arbiter options come from entries with `judge_role=arbiter` or
  `system_prompt_preset=arbiter_conflict_v1`.
- Arbiter-only configs are hidden from the primary judge picker.
- The Arbiter selector appears only when scoring is not `static`, including the
  multi-judge `llm_blended` mode, and two or more primary judges are selected.
- Selecting no Arbiter leaves judge conflicts unresolved for manual review.
- Selecting an Arbiter applies `conflict_policy=arbiter_override`; the Arbiter
  is invoked only for rows where primary judges disagree.

Run cache toggles are independent:

- Answer cache controls target model answer reuse.
- Judge cache controls primary judge response reuse.
- Arbiter cache controls selected-Arbiter response reuse for conflict rows.

## Runtime Data

Default files:

```text
final_UI/data/eval_runs.csv
final_UI/data/question_cases.csv
final_UI/data/qa_slice_scores.csv
final_UI/data/run_release_gates.csv
final_UI/data/registered_target_models.json
final_UI/data/registered_judge_models.json
final_UI/data/judge_api_presets.json
```

## Score Display

Saved results are displayed from the full 12,000-row OmniEval consensus
summaries under `data/eval_snapshot_20260624_094927/scores/`:

- core metric bars: `ACC`, `COM`, `NAC`, `HAL_pass`
- every displayed score is a normalized 0-1 value
- `overall_score` is the ranking and pass/fail score
- `hal_rate` may be stored as a reported diagnostic, but `HAL_pass` is the
  score component used in `overall_score`

Do not keep these in the active tree:

```text
final_UI/data/server_api_secrets.json
final_UI/data/access_log*.jsonl
final_UI/data/server_*.log
```

They are ignored by Git and were moved to `out/archive/final_cleanup_20260624_014209/`.

## API Cost Safety

No external model API is called for:

- opening saved results
- browsing compare/search/detail tabs
- viewing HTML or CSV reports
- recomposing saved judge scores
- previewing test sets

External API cost may occur for:

- generating new target model answers
- running new LLM judge scoring
- running new Arbiter scoring
- provider health checks that call real endpoints

## Run Output Contract

New run directories should preserve raw model outputs and judge scores
separately:

```text
out/eval_runs/{RUN_ID}/
  model_outputs.jsonl
  judge_scores.jsonl
  judge_scores.csv
  question_cases.csv
  eval_runs.csv
  run_release_gates.csv
  regression_report.html
  by_judge/{judge_config_id}/judge_scores.jsonl
```

This supports answer reuse, selected-case rescoring, and later Arbiter review.
The compact handoff keeps old large projections in
`out/archive/final_cleanup_20260624_014209/compact_active_tree/`; current UI
browsing uses `final_UI/data/` by default.

## Validation

```powershell
node --check .\final_UI\app.js
python -m py_compile .\final_UI\server.py
```

Browser checks:

- initial page load does not request `question_cases.csv`
- result-like tabs request `question_cases.csv` once
- direct hashes work: `#overview`, `#compare`, `#caseSets`, `#search`
- no API-costing endpoints are called unless a run is explicitly started

