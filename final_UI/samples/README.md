# Final UI Sample Files

This directory contains sanitized sample files for GitHub sharing. Runtime files under `final_UI/data/` are ignored by Git because they can contain local model settings, logs, evaluation outputs, and server-saved API keys.

| Sample file | Runtime destination | Purpose |
| --- | --- | --- |
| `registered_target_models.sample.json` | `final_UI/data/registered_target_models.json` | User-registered answer-generation target models |
| `registered_judge_models.sample.json` | `final_UI/data/registered_judge_models.json` | User-registered Judge or Arbiter models |
| `server_api_secrets.sample.json` | `final_UI/data/server_api_secrets.json` | Empty server-side API key store shape |
| `question_dataset_sample.csv` | UI testset upload | Recommended CSV columns for user-uploaded testsets |
| `question_dataset_aliases.sample.csv` | UI testset upload | Alternative accepted column names |
| `eval_runs.sample.csv` | `final_UI/data/eval_runs.csv` | Dashboard run-level KPI sample |
| `question_cases.sample.csv` | `final_UI/data/question_cases.csv` | Dashboard case-level result sample |
| `qa_slice_scores.sample.csv` | `final_UI/data/qa_slice_scores.csv` | Dashboard slice score sample |
| `run_release_gates.sample.csv` | `final_UI/data/run_release_gates.csv` | Dashboard release gate sample |
| `regression_diff.sample.csv` | `final_UI/data/regression_diff.csv` | Regression comparison sample |
| `active_run.sample.json` | `final_UI/data/active_run.json` | Example active-run status payload |

## Notes

- Do not commit real `server_api_secrets.json`, access logs, run outputs, or copied production CSVs.
- If a model should call a remote Ollama server, set `OLLAMA_BASE_URL` in `.env` or the process environment instead of hard-coding a private host into shared samples.
- Server-saved API keys are stored locally in `final_UI/data/server_api_secrets.json`; this sample intentionally contains no secret values.
