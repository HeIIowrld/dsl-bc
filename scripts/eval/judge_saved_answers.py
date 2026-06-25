from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import re
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.run_multi_model_eval import (
    DEFAULT_FINAL_UI_DATA,
    DEFAULT_JUDGE_CACHE_DIR,
    DEFAULT_MATRIX,
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OUT_ROOT,
    DEFAULT_REFUSAL_KEYWORDS,
    DEFAULT_RISK,
    DEFAULT_SEEDED_TARGET_MODELS,
    EvalCancelled,
    HttpChatProvider,
    SCORE_PASS_THRESHOLD,
    aggregate_release_gates,
    aggregate_runs,
    append_jsonl,
    build_regression_diff,
    build_static_similarity_scorer,
    ensure_ollama_models_by_endpoint,
    export_final_ui,
    load_cases_file,
    load_config,
    load_judge_cache,
    load_model_registry,
    normalize_pass_threshold,
    ollama_base_url_for_config,
    ollama_provider_for_config,
    output_fingerprint,
    parse_judge_score_weights,
    qa_slice_score_rows,
    question_case_rows,
    read_jsonl,
    resolve_judge_system_prompt,
    run_type_for_cases,
    safe_filename,
    score_fingerprint,
    score_with_optional_llm_judge,
    wait_for_eval_control,
    write_csv,
    write_html_report,
    write_jsonl,
    write_partitioned_eval_artifacts,
    write_xlsx,
)


SCORING_MODES = {"static", "static_llm", "llm_override", "blend"}
JUDGE_MODES = {"audit", "override", "blend"}
ANSWER_TEMPLATE_COLUMNS = [
    "case_id",
    "config_id",
    "model",
    "display_name",
    "model_answer",
    "status",
    "latency_ms",
    "raw_response",
]


def resolve_project_path(value: str | Path) -> Path:
    path = Path(str(value or "").strip())
    if not path.is_absolute():
        path = ROOT / path
    return path


def load_run_config(run_dir: Path) -> dict[str, Any]:
    for name in ("config.json", "config.yaml"):
        path = run_dir / name
        if path.exists():
            loaded = load_config(path)
            if isinstance(loaded, dict):
                return loaded
    raise SystemExit(f"source run has no config.json/config.yaml: {run_dir}")


def source_run_dir(args: argparse.Namespace) -> Path | None:
    if args.source_run_dir:
        path = resolve_project_path(args.source_run_dir)
        if path.is_dir():
            return path
        raise SystemExit(f"source run dir not found: {path}")
    if args.source_run_id:
        path = Path(args.out_root) / str(args.source_run_id)
        if path.is_dir():
            return path
        raise SystemExit(f"source run id not found: {args.source_run_id}")
    return None


def text_at(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        text = str(value or "").strip()
        if text:
            return text
    return ""


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def imported_config(config_id: str, row: dict[str, Any]) -> dict[str, Any]:
    model = text_at(row, "model", "model_name") or config_id
    return {
        "config_id": config_id,
        "display_name": text_at(row, "display_name", "model_display_name") or model,
        "provider": text_at(row, "provider") or "external_csv",
        "model": model,
        "prompt_version": text_at(row, "prompt_version") or "external_answers_csv",
        "rag_config": text_at(row, "rag_config") or "external",
        "safety_policy": text_at(row, "safety_policy") or "external_answers",
        "eval_target": True,
        "options": {},
    }


def load_outputs_from_csv(
    path: Path,
    *,
    run_id: str,
    cases: list[dict[str, Any]],
    registry_by_id: dict[str, dict[str, Any]],
    default_config_id: str,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if not path.exists():
        raise SystemExit(f"answers csv not found: {path}")
    imported_configs: dict[str, dict[str, Any]] = {}
    case_by_id = {str(case.get("case_id") or ""): case for case in cases}
    outputs: list[dict[str, Any]] = []
    missing_cases: list[str] = []
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames:
            raise SystemExit("answers csv has no header row")
        for index, row in enumerate(reader, 1):
            case_id = text_at(row, "case_id", "question_id", "id")
            if not case_id and index <= len(cases):
                case_id = str(cases[index - 1].get("case_id") or "")
            config_id = text_at(row, "config_id", "model_id", "version") or default_config_id
            answer = text_at(row, "model_answer", "answer", "response", "output")
            status = text_at(row, "status") or "ok"
            if not case_id or case_id not in case_by_id:
                missing_cases.append(case_id or f"row_{index}")
                continue
            if config_id not in registry_by_id and config_id not in imported_configs:
                imported_configs[config_id] = imported_config(config_id, row)
            output = {
                "run_id": run_id,
                "config_id": config_id,
                "case_id": case_id,
                "status": status,
                "model_answer": answer,
                "model": text_at(row, "model", "model_name") or config_id,
                "display_name": text_at(row, "display_name", "model_display_name"),
                "latency_ms": safe_float(text_at(row, "latency_ms"), 0.0),
                "raw_response": text_at(row, "raw_response"),
                "source": "answers_csv_import",
            }
            outputs.append(output)
    if missing_cases:
        preview = ", ".join(missing_cases[:8])
        suffix = "" if len(missing_cases) <= 8 else f" ... +{len(missing_cases) - 8}"
        raise SystemExit(f"answers csv contains case_id values not found in cases-file: {preview}{suffix}")
    if not outputs:
        raise SystemExit("answers csv did not produce any model outputs")
    return outputs, imported_configs


def configs_for_outputs(
    *,
    outputs: list[dict[str, Any]],
    registry_by_id: dict[str, dict[str, Any]],
    source_configs: list[dict[str, Any]] | None = None,
    imported_configs: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    imported_configs = imported_configs or {}
    source_by_id = {
        str(config.get("config_id") or ""): dict(config)
        for config in (source_configs or [])
        if isinstance(config, dict) and config.get("config_id")
    }
    result: list[dict[str, Any]] = []
    for config_id in sorted({str(output.get("config_id") or "") for output in outputs if output.get("config_id")}):
        config = source_by_id.get(config_id) or registry_by_id.get(config_id) or imported_configs.get(config_id)
        if not config:
            config = {
                "config_id": config_id,
                "display_name": config_id,
                "provider": "external_saved_answers",
                "model": config_id,
                "prompt_version": "saved_answers",
                "eval_target": True,
                "options": {},
            }
        result.append(dict(config))
    if not result:
        raise SystemExit("no config metadata could be derived from model outputs")
    return result


def load_source_payload(args: argparse.Namespace, registry_by_id: dict[str, dict[str, Any]]):
    run_dir = source_run_dir(args)
    if run_dir:
        try:
            source_config = load_run_config(run_dir)
        except SystemExit:
            if not args.cases_file:
                raise
            source_config = {}
        outputs = read_jsonl(run_dir / "model_outputs.jsonl")
        if not outputs:
            raise SystemExit(f"source run has no model_outputs.jsonl rows: {run_dir}")
        case_source = str(args.cases_file or source_config.get("case_source") or "")
        if not case_source:
            raise SystemExit("source run config has no case_source; pass --cases-file for in-progress answer runs")
        cases_path = resolve_project_path(case_source)
        cases, resolved_case_source = load_cases_file(cases_path, suites=None, limit=None)
        configs = configs_for_outputs(
            outputs=outputs,
            registry_by_id=registry_by_id,
            source_configs=[config for config in source_config.get("configs", []) if isinstance(config, dict)],
        )
        return {
            "source_run_id": run_dir.name,
            "source_config": source_config,
            "cases": cases,
            "case_source": resolved_case_source,
            "outputs": outputs,
            "configs": configs,
            "imported_answers_csv": "",
        }

    if not args.answers_csv:
        raise SystemExit("provide --source-run-id/--source-run-dir or --answers-csv")
    if not args.cases_file:
        raise SystemExit("--cases-file is required when --answers-csv is used")
    cases_path = resolve_project_path(args.cases_file)
    cases, resolved_case_source = load_cases_file(cases_path, suites=None, limit=None)
    outputs, imported_configs = load_outputs_from_csv(
        resolve_project_path(args.answers_csv),
        run_id=args.run_id,
        cases=cases,
        registry_by_id=registry_by_id,
        default_config_id=args.external_config_id,
    )
    configs = configs_for_outputs(
        outputs=outputs,
        registry_by_id=registry_by_id,
        imported_configs=imported_configs,
    )
    return {
        "source_run_id": "",
        "source_config": {},
        "cases": cases,
        "case_source": resolved_case_source,
        "outputs": outputs,
        "configs": configs,
        "imported_answers_csv": str(resolve_project_path(args.answers_csv)),
    }


def selected_judge_configs(registry_by_id: dict[str, dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    ids: list[str] = []
    for value in args.judge_config or []:
        ids.extend(part.strip() for part in str(value).split(",") if part.strip())
    ids = list(dict.fromkeys(ids))
    if args.scoring_mode == "static":
        return []
    if not ids:
        raise SystemExit(f"scoring_mode={args.scoring_mode} requires --judge-config")
    missing = [config_id for config_id in ids if config_id not in registry_by_id]
    if missing:
        raise SystemExit(f"unknown judge config_id: {', '.join(missing)}")
    return [dict(registry_by_id[config_id]) for config_id in ids]


def split_cli_ids(values: list[str] | None) -> list[str]:
    ids: list[str] = []
    for value in values or []:
        ids.extend(part.strip() for part in str(value).split(",") if part.strip())
    return list(dict.fromkeys(ids))


def answer_is_complete(output: dict[str, Any]) -> bool:
    return output.get("status") == "ok" and bool(str(output.get("model_answer") or "").strip())


def load_key_filter(path_value: str) -> tuple[set[tuple[str, str]], dict[tuple[str, str], dict[str, Any]]]:
    if not str(path_value or "").strip():
        return set(), {}
    path = resolve_project_path(path_value)
    if not path.exists():
        raise SystemExit(f"key file not found: {path}")
    keys: set[tuple[str, str]] = set()
    contexts: dict[tuple[str, str], dict[str, Any]] = {}
    if path.suffix.lower() == ".jsonl":
        for row in read_jsonl(path):
            config_id = str(row.get("config_id") or "").strip()
            case_id = str(row.get("case_id") or row.get("question_id") or "").strip()
            if config_id and case_id:
                key = (config_id, case_id)
                keys.add(key)
                context = row.get("arbiter_context")
                if isinstance(context, dict):
                    contexts[key] = context
    else:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                config_id = str(row.get("config_id") or "").strip()
                case_id = str(row.get("case_id") or row.get("question_id") or "").strip()
                if config_id and case_id:
                    keys.add((config_id, case_id))
    if not keys:
        raise SystemExit(f"key file has no usable config_id/case_id rows: {path}")
    return keys, contexts


def filter_source_payload(payload: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    requested = split_cli_ids(args.config)
    key_filter, judge_context_by_key = load_key_filter(args.key_file)
    cases = list(payload["cases"])
    case_ids = {str(case.get("case_id") or "") for case in cases}
    configs = list(payload["configs"])
    config_ids = [str(config.get("config_id") or "") for config in configs]
    selected_ids = requested or config_ids
    unknown = [config_id for config_id in selected_ids if config_id not in set(config_ids)]
    if unknown:
        raise SystemExit(f"selected config_id has no saved outputs in source run: {', '.join(unknown)}")

    keep_ids: list[str] = []
    dropped: list[str] = []
    for config_id in selected_ids:
        config_outputs = [row for row in payload["outputs"] if str(row.get("config_id") or "") == config_id]
        complete_case_ids = {
            str(row.get("case_id") or "")
            for row in config_outputs
            if answer_is_complete(row)
        }
        if args.complete_only and complete_case_ids != case_ids:
            dropped.append(f"{config_id} ({len(complete_case_ids)}/{len(case_ids)})")
            continue
        keep_ids.append(config_id)

    if not keep_ids:
        detail = "; dropped " + ", ".join(dropped[:8]) if dropped else ""
        raise SystemExit(f"no configs left to judge after filtering{detail}")
    if dropped:
        print("COMPLETE_ONLY_DROPPED " + ", ".join(dropped), flush=True)

    keep_set = set(keep_ids)
    filtered = dict(payload)
    filtered["configs"] = [config for config in configs if str(config.get("config_id") or "") in keep_set]
    filtered["outputs"] = [
        output
        for output in payload["outputs"]
        if str(output.get("config_id") or "") in keep_set
        and (not args.complete_only or answer_is_complete(output))
        and (not key_filter or (str(output.get("config_id") or ""), str(output.get("case_id") or "")) in key_filter)
    ]
    filtered["judge_context_by_key"] = judge_context_by_key
    return filtered


def resolved_judge_mode(args: argparse.Namespace) -> str:
    if args.judge_mode:
        return args.judge_mode
    return {
        "static": "audit",
        "static_llm": "audit",
        "llm_override": "override",
        "blend": "blend",
    }[args.scoring_mode]


def attach_output_fingerprints(
    *,
    outputs: list[dict[str, Any]],
    configs: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    run_id: str,
) -> list[dict[str, Any]]:
    config_by_id = {str(config.get("config_id") or ""): config for config in configs}
    case_by_id = {str(case.get("case_id") or ""): case for case in cases}
    normalized: list[dict[str, Any]] = []
    missing: list[str] = []
    for output in outputs:
        config_id = str(output.get("config_id") or "")
        case_id = str(output.get("case_id") or "")
        config = config_by_id.get(config_id)
        case = case_by_id.get(case_id)
        if not config or not case:
            missing.append(f"{config_id}/{case_id}")
            continue
        row = dict(output)
        row["run_id"] = run_id
        row["output_fingerprint"] = output_fingerprint(config, case)
        normalized.append(row)
    if missing:
        preview = ", ".join(missing[:8])
        suffix = "" if len(missing) <= 8 else f" ... +{len(missing) - 8}"
        raise SystemExit(f"model outputs do not match case/config metadata: {preview}{suffix}")
    return normalized


def write_run_outputs(
    *,
    run_dir: Path,
    run_id: str,
    cases: list[dict[str, Any]],
    configs: list[dict[str, Any]],
    outputs: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    matrix: dict[str, Any],
    release_gate_config: dict[str, Any],
    baseline_config: str,
    eval_started_at: str,
    run_metadata: dict[str, Any],
    export_ui: bool,
    final_ui_data: Path,
) -> None:
    regression_diff = build_regression_diff(cases=cases, scores=scores, baseline_config=baseline_config)
    summary = aggregate_runs(
        run_id=run_id,
        configs=configs,
        scores=scores,
        outputs=outputs,
        eval_started_at=eval_started_at,
    )
    run_release_gates = aggregate_release_gates(
        run_id=run_id,
        cases=cases,
        configs=configs,
        scores=scores,
        release_gate_config=release_gate_config,
    )
    question_rows = question_case_rows(
        cases=cases,
        configs=configs,
        outputs=outputs,
        scores=scores,
        regression_diff=regression_diff,
    )
    slice_rows = qa_slice_score_rows(question_rows)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(run_dir / "model_outputs.jsonl", outputs)
    write_jsonl(run_dir / "judge_scores.jsonl", scores)
    write_jsonl(run_dir / "regression_diff.jsonl", regression_diff)
    write_jsonl(run_dir / "run_release_gates.jsonl", run_release_gates)
    write_jsonl(run_dir / "qa_slice_scores.jsonl", slice_rows)
    write_csv(run_dir / "model_outputs.csv", outputs)
    write_csv(run_dir / "judge_scores.csv", scores)
    write_csv(run_dir / "regression_diff.csv", regression_diff)
    write_csv(run_dir / "run_release_gates.csv", run_release_gates)
    write_csv(run_dir / "eval_runs.csv", summary)
    write_csv(run_dir / "question_cases.csv", question_rows)
    write_csv(run_dir / "qa_slice_scores.csv", slice_rows)
    by_model_dir = run_dir / "by_model"
    by_model_dir.mkdir(parents=True, exist_ok=True)
    score_by_key = {(row.get("case_id"), row.get("config_id")): row for row in scores}
    for config in configs:
        config_id = str(config.get("config_id") or "")
        rows = []
        for output in outputs:
            if output.get("config_id") != config_id:
                continue
            score = score_by_key.get((output.get("case_id"), config_id), {})
            rows.append({**output, **{f"score_{key}": value for key, value in score.items() if key not in output}})
        write_jsonl(by_model_dir / f"{safe_filename(config_id)}.jsonl", rows)
    write_partitioned_eval_artifacts(run_dir, outputs, scores)
    write_html_report(run_dir / "regression_report.html", summary, regression_diff, run_release_gates, run_metadata)
    write_xlsx(
        run_dir / "regression_report.xlsx",
        {
            "run_metadata": [run_metadata],
            "summary": summary,
            "run_release_gates": run_release_gates,
            "model_outputs": outputs,
            "judge_scores": scores,
            "regression_diff": regression_diff,
            "qa_slice_scores": slice_rows,
        },
    )
    if export_ui:
        export_final_ui(
            final_ui_data=final_ui_data,
            run_id=run_id,
            summary=summary,
            question_rows=question_rows,
            slice_rows=slice_rows,
            run_release_gates=run_release_gates,
            configs=configs,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Judge saved model answers without calling target models.")
    parser.add_argument("--source-run-id", default="")
    parser.add_argument("--source-run-dir", default="")
    parser.add_argument("--answers-csv", default="")
    parser.add_argument("--cases-file", default="")
    parser.add_argument("--external-config-id", default="external_model_v1")
    parser.add_argument("--config", action="append", default=[], help="Target config_id to judge. Repeat or comma-separate. Defaults to all configs in the source answers.")
    parser.add_argument("--key-file", default="", help="Optional CSV/JSONL with config_id and case_id columns to judge only selected rows.")
    parser.add_argument("--complete-only", action="store_true", help="Drop configs that do not have one ok, non-empty answer for every case.")
    parser.add_argument("--registry", default=str(DEFAULT_SEEDED_TARGET_MODELS))
    parser.add_argument("--matrix", default=str(DEFAULT_MATRIX))
    parser.add_argument("--risk-taxonomy", default=str(DEFAULT_RISK))
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--base-url", default=DEFAULT_OLLAMA_BASE_URL)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--control-file", default="")
    parser.add_argument("--export-final-ui", action="store_true")
    parser.add_argument("--final-ui-data", default=str(DEFAULT_FINAL_UI_DATA))
    parser.add_argument("--scoring-mode", choices=sorted(SCORING_MODES), default="static_llm")
    parser.add_argument("--judge-config", action="append", default=[])
    parser.add_argument("--judge-mode", choices=sorted(JUDGE_MODES), default="")
    parser.add_argument("--judge-blend-weight", type=float, default=0.5)
    parser.add_argument(
        "--judge-score-weights",
        default="",
        help="JSON object or comma list mapping judge config_id to score weight. Values are normalized before aggregation.",
    )
    parser.add_argument(
        "--judge-aggregation-method",
        choices=["auto", "weighted_mean", "mean", "trimmed_mean", "max", "min"],
        default="auto",
        help="How to combine multiple judges when a single runner receives more than one judge config.",
    )
    parser.add_argument("--pass-threshold", type=float, default=None)
    parser.add_argument("--static-embedding-model", default="")
    parser.add_argument("--static-embedding-base-url", default="")
    parser.add_argument("--static-embedding-keep-alive", default="0")
    parser.add_argument("--workers", type=int, default=1, help="Number of saved-answer judge rows to score concurrently.")
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True, help="Reuse completed judge_scores rows in the same run directory.")
    parser.add_argument("--judge-cache", action=argparse.BooleanOptionalAction, default=True, help="Reuse globally cached base judge responses when inputs match.")
    parser.add_argument("--arbiter-cache", action=argparse.BooleanOptionalAction, default=True, help="Reuse globally cached arbiter judge responses when inputs match.")
    parser.add_argument("--judge-cache-dir", default=str(DEFAULT_JUDGE_CACHE_DIR))
    parser.add_argument("--retry-transient", type=int, default=2, help="Retry transient judge API failures per row.")
    parser.add_argument("--retry-sleep-seconds", type=float, default=2.0, help="Base sleep between transient judge retries.")
    parser.add_argument("--rate-limit-max-retries", type=int, default=0, help="Max 429 retries per row. 0 means keep waiting/retrying.")
    parser.add_argument("--rate-limit-sleep-seconds", type=float, default=90.0, help="Minimum sleep when a judge API returns HTTP 429.")
    return parser.parse_args()


def score_row_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row.get("config_id") or ""), str(row.get("case_id") or "")


def unique_join(values: list[str]) -> str:
    return ", ".join(dict.fromkeys(value for value in values if value))


def expected_judge_resume_metadata(judge_configs: list[dict[str, Any]]) -> dict[str, str]:
    config_ids: list[str] = []
    prompt_versions: list[str] = []
    prompt_hashes: list[str] = []
    prompt_presets: list[str] = []
    for judge_config in judge_configs:
        _prompt, version, preset, prompt_hash = resolve_judge_system_prompt(judge_config)
        config_ids.append(str(judge_config.get("config_id") or ""))
        prompt_versions.append(str(version or ""))
        prompt_hashes.append(str(prompt_hash or ""))
        prompt_presets.append(str(preset or ""))
    return {
        "llm_judge_config_id": unique_join(config_ids),
        "llm_judge_prompt_version": unique_join(prompt_versions),
        "llm_judge_prompt_hash": unique_join(prompt_hashes),
        "llm_judge_prompt_preset": unique_join(prompt_presets),
    }


def judge_resume_metadata_matches(row: dict[str, Any], expected: dict[str, str]) -> bool:
    for key, value in expected.items():
        if value and str(row.get(key) or "") != value:
            return False
    return True


def is_resumable_score(
    row: dict[str, Any],
    *,
    judge_required: bool,
    expected_judge_metadata: dict[str, str] | None = None,
) -> bool:
    if not row.get("config_id") or not row.get("case_id"):
        return False
    if not judge_required:
        return True
    if str(row.get("llm_judge_status") or "").lower() not in {"ok", "refused_by_provider_policy"}:
        return False
    return judge_resume_metadata_matches(row, expected_judge_metadata or {})


def is_transient_judge_error(score: dict[str, Any]) -> bool:
    if str(score.get("llm_judge_status") or "").lower() != "error":
        return False
    reason = str(score.get("llm_judge_reason") or score.get("reason") or "").lower()
    transient_markers = (
        "http error 429",
        "http error 500",
        "http error 502",
        "http error 503",
        "http error 504",
        "http error 520",
        "timeout",
        "timed out",
        "temporarily unavailable",
        "remote end closed",
        "connection reset",
        "did not return a json object",
    )
    return any(marker in reason for marker in transient_markers)


def is_rate_limit_judge_error(score: dict[str, Any]) -> bool:
    if str(score.get("llm_judge_status") or "").lower() != "error":
        return False
    reason = str(score.get("llm_judge_reason") or score.get("reason") or "").lower()
    permanent_quota_markers = (
        "exceeded your current quota",
        "insufficient_quota",
        "check your plan and billing",
        "billing details",
    )
    if any(marker in reason for marker in permanent_quota_markers):
        return False
    return "http error 429" in reason or "too many requests" in reason or "rate limit" in reason


def retry_after_seconds_from_score(score: dict[str, Any]) -> float:
    reason = str(score.get("llm_judge_reason") or score.get("reason") or "")
    match = re.search(r"retry_after=([0-9]+(?:\.[0-9]+)?)", reason, re.IGNORECASE)
    if match:
        return safe_float(match.group(1), 0.0)
    match = re.search(r"try again in ([0-9]+(?:\.[0-9]+)?)s", reason, re.IGNORECASE)
    if match:
        return safe_float(match.group(1), 0.0)
    match = re.search(r"try again in ([0-9]+(?:\.[0-9]+)?)m", reason, re.IGNORECASE)
    if match:
        return safe_float(match.group(1), 0.0) * 60.0
    return 0.0


def main() -> None:
    args = parse_args()
    registry = load_model_registry(Path(args.registry))
    registry_by_id = {str(config.get("config_id") or ""): dict(config) for config in registry.get("configs", [])}
    payload = load_source_payload(args, registry_by_id)
    payload = filter_source_payload(payload, args)
    source_config = payload["source_config"]
    source_run_id = str(payload["source_run_id"] or "")
    default_run_id = (
        f"{source_run_id}_JUDGE_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if source_run_id
        else f"IMPORTED_ANSWERS_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    run_id = args.run_id or default_run_id
    run_dir = Path(args.out_root) / run_id
    cases = payload["cases"]
    configs = payload["configs"]
    outputs = attach_output_fingerprints(
        outputs=payload["outputs"],
        configs=configs,
        cases=cases,
        run_id=run_id,
    )
    judge_configs = selected_judge_configs(registry_by_id, args)
    judge_mode = resolved_judge_mode(args)
    judge_score_weights = parse_judge_score_weights(args.judge_score_weights)
    matrix_from_file = load_config(Path(args.matrix))
    eval_run = source_config.get("matrix") if isinstance(source_config.get("matrix"), dict) else {}
    if not eval_run:
        eval_run = matrix_from_file.get("eval_run") if isinstance(matrix_from_file.get("eval_run"), dict) else {}
    release_gate_config = eval_run.get("release_gates") if isinstance(eval_run.get("release_gates"), dict) else {}
    pass_threshold = normalize_pass_threshold(
        args.pass_threshold if args.pass_threshold is not None else eval_run.get("pass_threshold"),
        SCORE_PASS_THRESHOLD,
    )
    baseline_config = (
        str(source_config.get("baseline_config") or "")
        or str(eval_run.get("baseline_config") or "")
        or str(configs[0].get("config_id") or "")
    )
    if baseline_config not in {str(config.get("config_id") or "") for config in configs}:
        baseline_config = str(configs[0].get("config_id") or "")

    provider_cache: dict[str, Any] = {}
    api_provider = HttpChatProvider(timeout=args.timeout)
    installed_models_by_base_url = ensure_ollama_models_by_endpoint(
        configs=judge_configs,
        provider_cache=provider_cache,
        allow_missing=args.allow_missing,
        default_base_url=args.base_url,
        timeout=args.timeout,
    )
    static_args = SimpleNamespace(
        static_embedding_model=args.static_embedding_model or None,
        static_embedding_base_url=args.static_embedding_base_url or None,
        static_embedding_keep_alive=args.static_embedding_keep_alive,
        base_url=args.base_url,
        allow_missing=args.allow_missing,
    )
    similarity_scorer = build_static_similarity_scorer(
        args=static_args,
        eval_run=eval_run,
        provider_cache=provider_cache,
    )
    static_similarity_summary = (
        similarity_scorer.summary()
        if hasattr(similarity_scorer, "summary")
        else {"provider": "deterministic"}
    )
    risk = load_config(Path(args.risk_taxonomy))
    refusal_keywords = list(dict.fromkeys(list(risk.get("refusal_keywords", [])) + DEFAULT_REFUSAL_KEYWORDS))
    case_by_id = {str(case.get("case_id") or ""): case for case in cases}
    config_by_id = {str(config.get("config_id") or ""): config for config in configs}
    control_file = Path(args.control_file) if args.control_file else None
    judge_cache_dir = Path(args.judge_cache_dir)
    judge_cache_active = bool(judge_configs and (args.judge_cache or args.arbiter_cache))
    judge_cache_by_key = load_judge_cache(
        judge_cache_dir,
        include_judge=bool(args.judge_cache),
        include_arbiter=bool(args.arbiter_cache),
        target_configs=configs,
        judge_configs=judge_configs,
        default_base_url=args.base_url,
    ) if judge_cache_active else {}
    judge_cache_lock = threading.Lock()

    eval_started_at = datetime.now().isoformat(timespec="seconds")
    run_type = "imported_answers" if payload.get("imported_answers_csv") else "judge_saved_answers"
    run_metadata = {
        "run_id": run_id,
        "source_run_id": source_run_id,
        "run_type": run_type,
        "eval_started_at": eval_started_at,
        "case_source": payload["case_source"],
        "scoring_mode": args.scoring_mode,
        "judge_mode": judge_mode,
        "judge_blend_weight": args.judge_blend_weight,
        "judge_score_weights": judge_score_weights,
        "judge_aggregation_method": args.judge_aggregation_method,
        "judge_configs": [config.get("config_id") for config in judge_configs],
        "judge_cache": {
            "judge_enabled": bool(args.judge_cache and judge_configs),
            "arbiter_enabled": bool(args.arbiter_cache and judge_configs),
            "dir": str(judge_cache_dir),
            "entries_loaded": len(judge_cache_by_key),
        },
        "pass_threshold": pass_threshold,
        "baseline_config": baseline_config,
        "configs": [config.get("config_id") for config in configs],
        "case_count": len(cases),
        "imported_answers_csv": payload.get("imported_answers_csv", ""),
    }
    run_config = {
        **run_metadata,
        "case_source": payload["case_source"],
        "configs": configs,
        "matrix": eval_run,
        "resolved_scoring": {
            "scoring_mode": args.scoring_mode,
            "judge_mode": judge_mode,
            "judge_blend_weight": args.judge_blend_weight,
            "judge_score_weights": judge_score_weights,
            "judge_aggregation_method": args.judge_aggregation_method,
            "judge_configs": [config.get("config_id") for config in judge_configs],
            "pass_threshold": pass_threshold,
            "static_similarity": static_similarity_summary,
        },
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    config_text = json.dumps(run_config, ensure_ascii=False, indent=2) + "\n"
    (run_dir / "config.json").write_text(config_text, encoding="utf-8")
    (run_dir / "config.yaml").write_text(config_text, encoding="utf-8")
    (run_dir / "run_metadata.json").write_text(
        json.dumps(run_metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_jsonl(run_dir / "model_outputs.jsonl", outputs)
    write_csv(run_dir / "model_outputs.csv", outputs)
    score_path = run_dir / "judge_scores.jsonl"
    judge_required = bool(judge_configs and args.scoring_mode in {"static_llm", "llm_override", "blend"})
    expected_judge_metadata = expected_judge_resume_metadata(judge_configs) if judge_required else {}
    completed_scores_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    if args.resume and score_path.exists():
        for existing_score in read_jsonl(score_path):
            if is_resumable_score(
                existing_score,
                judge_required=judge_required,
                expected_judge_metadata=expected_judge_metadata,
            ):
                completed_scores_by_key[score_row_key(existing_score)] = existing_score

    print(f"run_id={run_id}", flush=True)
    if source_run_id:
        print(f"source_run_id={source_run_id}", flush=True)
    if payload.get("imported_answers_csv"):
        print(f"answers_csv={payload['imported_answers_csv']}", flush=True)
    print(f"cases={len(cases)}", flush=True)
    print("configs=" + ",".join(str(config.get("config_id") or "") for config in configs), flush=True)
    print(f"scoring_mode={args.scoring_mode}", flush=True)
    print(
        "llm_judge="
        + (
            ",".join(str(config.get("config_id") or "") for config in judge_configs)
            if judge_configs
            else "disabled"
        ),
        flush=True,
    )
    print(
        "judge_cache="
        + (
            f"judge={'enabled' if args.judge_cache else 'disabled'} "
            f"arbiter={'enabled' if args.arbiter_cache else 'disabled'} "
            f"dir={judge_cache_dir} entries={len(judge_cache_by_key)}"
            if judge_configs
            else "disabled"
        ),
        flush=True,
    )
    print(f"workers={max(1, args.workers)} resume={args.resume}", flush=True)

    tasks: list[dict[str, Any]] = []
    ordered_keys: list[tuple[str, str]] = []
    for model_index, config in enumerate(configs, 1):
        config_id = str(config.get("config_id") or "")
        config_outputs = [output for output in outputs if output.get("config_id") == config_id]
        for index, output in enumerate(config_outputs, 1):
            case_id = str(output.get("case_id") or "")
            key = (config_id, case_id)
            ordered_keys.append(key)
            if key in completed_scores_by_key:
                continue
            tasks.append(
                {
                    "model_index": model_index,
                    "model_count": len(configs),
                    "config": config,
                    "config_id": config_id,
                    "index": index,
                    "total": len(config_outputs),
                    "output": output,
                }
            )

    scores: list[dict[str, Any]] = [
        completed_scores_by_key[key]
        for key in ordered_keys
        if key in completed_scores_by_key
    ]
    score_append_lock = threading.Lock()
    write_jsonl(score_path, scores)
    if completed_scores_by_key:
        print(f"RESUME_DONE completed={len(completed_scores_by_key)} pending={len(tasks)}", flush=True)
    else:
        print(f"RESUME_DONE completed=0 pending={len(tasks)}", flush=True)

    def judge_contexts_for_worker(local_provider_cache: dict[str, Any]) -> list[dict[str, Any]]:
        contexts = []
        for judge_config in judge_configs:
            judge_provider = (
                ollama_provider_for_config(
                    judge_config,
                    local_provider_cache,
                    default_base_url=args.base_url,
                    timeout=args.timeout,
                )
                if judge_config.get("provider") == "ollama"
                else None
            )
            if judge_config.get("provider") == "ollama":
                installed_models = installed_models_by_base_url.get(
                    ollama_base_url_for_config(judge_config, default_base_url=args.base_url),
                    set(),
                )
            else:
                installed_models = set()
            contexts.append(
                {
                    "judge_config": judge_config,
                    "provider": judge_provider,
                    "installed_models": installed_models,
                }
            )
        return contexts

    def score_task(task: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        config = task["config"]
        output = task["output"]
        config_id = str(task["config_id"])
        case_id = str(output.get("case_id") or "")
        case = case_by_id[case_id]
        arbiter_context = payload.get("judge_context_by_key", {}).get((config_id, case_id))
        local_provider_cache: dict[str, Any] = {}
        local_api_provider = HttpChatProvider(timeout=args.timeout)
        last_score: dict[str, Any] | None = None
        max_attempts = max(1, int(args.retry_transient) + 1)
        attempt = 0
        rate_limit_attempts = 0
        while True:
            attempt += 1
            try:
                wait_for_eval_control(control_file, run_id=run_id, config_id=config_id, case_id=case_id)
            except EvalCancelled:
                raise SystemExit(130)
            score = score_with_optional_llm_judge(
                case=case,
                output=output,
                config=config,
                pass_threshold=pass_threshold,
                refusal_keywords=refusal_keywords,
                judge_contexts=judge_contexts_for_worker(local_provider_cache),
                judge_mode=judge_mode,
                judge_blend_weight=args.judge_blend_weight,
                judge_score_weights=judge_score_weights,
                judge_aggregation_method=args.judge_aggregation_method,
                scoring_mode=args.scoring_mode,
                api_provider=local_api_provider,
                keep_alive=None,
                similarity_scorer=similarity_scorer,
                arbiter_context=arbiter_context,
                log_context={
                    "target_config_id": config_id,
                    "case_index": task["index"],
                    "case_total": task["total"],
                    "case_id": case_id,
                },
                judge_cache_enabled=bool(args.judge_cache),
                arbiter_cache_enabled=bool(args.arbiter_cache),
                judge_cache_dir=judge_cache_dir,
                judge_cache_by_key=judge_cache_by_key,
                judge_cache_lock=judge_cache_lock,
                default_base_url=args.base_url,
            )
            score["output_fingerprint"] = output.get("output_fingerprint", "")
            score["score_fingerprint"] = score_fingerprint(
                output_hash=str(output.get("output_fingerprint") or ""),
                case=case,
                scoring_mode=args.scoring_mode,
                judge_mode=judge_mode,
                judge_blend_weight=args.judge_blend_weight,
                judge_configs=judge_configs,
                pass_threshold=pass_threshold,
                refusal_keywords=refusal_keywords,
                static_similarity=static_similarity_summary,
                judge_score_weights=judge_score_weights,
                judge_aggregation_method=args.judge_aggregation_method,
                arbiter_context=arbiter_context,
            )
            last_score = score
            if is_rate_limit_judge_error(score):
                rate_limit_attempts += 1
                if args.rate_limit_max_retries > 0 and rate_limit_attempts > args.rate_limit_max_retries:
                    break
                retry_after = retry_after_seconds_from_score(score)
                sleep_seconds = max(
                    safe_float(args.rate_limit_sleep_seconds, 90.0),
                    retry_after,
                )
                # Back off a little more on repeated 429s, but keep the run alive instead of writing
                # a permanent error row for a temporary API throttle.
                sleep_seconds *= min(rate_limit_attempts, 4)
                print(
                    f"RATE_LIMIT_BACKOFF [{config_id}] {task['index']}/{task['total']} {case_id} "
                    f"attempt={rate_limit_attempts} sleep={sleep_seconds:.1f}s "
                    f"reason={str(score.get('llm_judge_reason') or '')[:240]}",
                    flush=True,
                )
                time.sleep(sleep_seconds)
                continue
            if not is_transient_judge_error(score) or attempt >= max_attempts:
                break
            time.sleep(max(0.0, args.retry_sleep_seconds) * attempt)
        return task, last_score or {}

    if max(1, args.workers) <= 1:
        current_model_id = ""
        for task in tasks:
            if task["config_id"] != current_model_id:
                current_model_id = task["config_id"]
                print(
                    f"MODEL_START {task['model_index']}/{task['model_count']} "
                    f"{current_model_id} cases={task['total']}",
                    flush=True,
                )
            if judge_configs and task["output"].get("status") == "ok":
                print(f"JUDGE_START [{task['config_id']}] {task['index']}/{task['total']} {task['output'].get('case_id')}", flush=True)
            _, score = score_task(task)
            scores.append(score)
            with score_append_lock:
                append_jsonl(score_path, score)
            if judge_configs and task["output"].get("status") == "ok":
                print(
                    f"JUDGE_DONE [{task['config_id']}] {task['index']}/{task['total']} "
                    f"{task['output'].get('case_id')} status={score.get('llm_judge_status', 'static')}",
                    flush=True,
                )
            else:
                print(f"SCORE_DONE [{task['config_id']}] {task['index']}/{task['total']} {task['output'].get('case_id')}", flush=True)
    else:
        workers = max(1, args.workers)
        print(f"PARALLEL_START workers={workers} pending={len(tasks)}", flush=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_task = {executor.submit(score_task, task): task for task in tasks}
            futures = list(future_to_task)
            for future in concurrent.futures.as_completed(futures):
                try:
                    task, score = future.result()
                except BaseException as exc:
                    task = future_to_task.get(future, {})
                    print(
                        "WORKER_ERROR "
                        f"[{task.get('config_id', '-')}] {task.get('index', '-')}/{task.get('total', '-')} "
                        f"{task.get('output', {}).get('case_id', '-')} {type(exc).__name__}: {exc}",
                        flush=True,
                    )
                    print(traceback.format_exc(), file=sys.stderr, flush=True)
                    continue
                scores.append(score)
                with score_append_lock:
                    append_jsonl(score_path, score)
                if judge_configs and task["output"].get("status") == "ok":
                    print(
                        f"JUDGE_DONE [{task['config_id']}] {task['index']}/{task['total']} "
                        f"{task['output'].get('case_id')} status={score.get('llm_judge_status', 'static')}",
                        flush=True,
                    )
                else:
                    print(f"SCORE_DONE [{task['config_id']}] {task['index']}/{task['total']} {task['output'].get('case_id')}", flush=True)

    config_order = {str(config.get("config_id") or ""): index for index, config in enumerate(configs)}
    case_order = {str(case.get("case_id") or ""): index for index, case in enumerate(cases)}
    scores.sort(key=lambda row: (config_order.get(str(row.get("config_id") or ""), 10**9), case_order.get(str(row.get("case_id") or ""), 10**9)))

    write_run_outputs(
        run_dir=run_dir,
        run_id=run_id,
        cases=cases,
        configs=configs,
        outputs=outputs,
        scores=scores,
        matrix=eval_run,
        release_gate_config=release_gate_config,
        baseline_config=baseline_config,
        eval_started_at=eval_started_at,
        run_metadata=run_metadata,
        export_ui=args.export_final_ui,
        final_ui_data=Path(args.final_ui_data),
    )
    print(f"Wrote saved-answer judge run to {run_dir}", flush=True)


if __name__ == "__main__":
    main()
