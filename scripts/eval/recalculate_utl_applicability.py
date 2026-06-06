from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.judge_saved_answers import write_run_outputs
from scripts.eval.run_multi_model_eval import (
    DEFAULT_FINAL_UI_DATA,
    DEFAULT_OUT_ROOT,
    SCORE_METRIC_KEYS,
    aggregate_llm_judge_scores,
    apply_llm_judge,
    bool_from_metadata,
    load_cases_file,
    load_config,
    metric_keys_for_score,
    metric_value,
    raw_metric_score,
    read_jsonl,
    score_denominator,
    score_total_from_metrics,
    utl_applicable_for_score,
    write_csv,
    write_jsonl,
)


def resolve_path(value: str | Path) -> Path:
    path = Path(str(value or "").strip())
    if not path.is_absolute():
        path = ROOT / path
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Recalculate UTL applicability and scaled scores for existing eval runs.")
    parser.add_argument("--run-dir", action="append", default=[], help="Run directory to repair. Repeatable.")
    parser.add_argument("--all", action="store_true", help="Repair every eval run under out/eval_runs that has judge_scores.jsonl and config.json.")
    parser.add_argument("--source-config", default=str(ROOT / "config" / "seeded_target_models.yaml"))
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--backup", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--export-final-ui", action="store_true")
    parser.add_argument("--final-ui-data", default=str(DEFAULT_FINAL_UI_DATA))
    return parser.parse_args()


def load_run_config(run_dir: Path) -> dict[str, Any]:
    for name in ("config.json", "config.yaml"):
        path = run_dir / name
        if path.exists():
            loaded = load_config(path)
            if isinstance(loaded, dict):
                return loaded
    return {}


def config_map(*configs_lists: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for configs in configs_lists:
        for config in configs or []:
            config_id = str(config.get("config_id") or "").strip()
            if config_id and config_id not in mapped:
                mapped[config_id] = dict(config)
    return mapped


def case_map(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for case in cases:
        for key in ("case_id", "question_id", "id"):
            case_id = str(case.get(key) or "").strip()
            if case_id and case_id not in mapped:
                mapped[case_id] = case
    return mapped


def load_cases_from_question_cases_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    cases: list[dict[str, Any]] = []
    seen: set[str] = set()
    with path.open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            case_id = str(row.get("question_id") or row.get("case_id") or "").strip()
            if not case_id or case_id in seen:
                continue
            seen.add(case_id)
            metadata = {
                "qa_category": row.get("qa_category", ""),
                "question_type": row.get("question_type", ""),
                "qa_topic": row.get("qa_topic", ""),
                "selection_mode": row.get("selection_mode", ""),
                "regression_suite": row.get("regression_suite", ""),
                "metamorphic_relation": row.get("metamorphic_relation", ""),
                "dataset_pool_id": row.get("dataset_pool_id", ""),
                "dataset_role": row.get("dataset_role", ""),
                "dataset_version": row.get("dataset_version", ""),
                "qa_matrix_topic": row.get("qa_matrix_topic", ""),
                "benchmark_group": row.get("benchmark_group", ""),
                "source_hash": row.get("source_hash", ""),
                "source_title": row.get("source_title", ""),
                "source_url": row.get("source_url", ""),
                "expected_behavior": row.get("expected_behavior", ""),
            }
            case = {
                "case_id": case_id,
                "question_id": case_id,
                "qa_category": row.get("qa_category", ""),
                "question_type": row.get("question_type", ""),
                "qa_topic": row.get("qa_topic", ""),
                "question": row.get("instruction", ""),
                "instruction": row.get("instruction", ""),
                "gold_answer": row.get("output", ""),
                "output": row.get("output", ""),
                "expected_behavior": row.get("expected_behavior", ""),
                "dataset_pool_id": row.get("dataset_pool_id", ""),
                "dataset_role": row.get("dataset_role", ""),
                "gate_eligible": bool_from_metadata(row.get("gate_eligible"), False),
                "release_gate_eligible": bool_from_metadata(row.get("release_gate_eligible"), False),
                "case_status": row.get("case_status", ""),
                "gold_verified": bool_from_metadata(row.get("gold_verified"), False),
                "human_review_required": bool_from_metadata(row.get("human_review_required"), False),
                "case_source": row.get("case_source", ""),
                "dataset_version": row.get("dataset_version", ""),
                "priority": row.get("priority", ""),
                "task_type": row.get("task_type", ""),
                "metadata": metadata,
                "gold_evidence": [],
            }
            cases.append(case)
    return cases


def choose_cases_for_scores(run_dir: Path, cases: list[dict[str, Any]], scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    score_case_ids = {
        str(score.get("case_id") or "").strip()
        for score in scores
        if str(score.get("case_id") or "").strip()
    }
    if not score_case_ids:
        return cases
    loaded_map = case_map(cases)
    loaded_missing = sum(1 for case_id in score_case_ids if case_id not in loaded_map)
    csv_cases = load_cases_from_question_cases_csv(run_dir / "question_cases.csv")
    csv_map = case_map(csv_cases)
    csv_missing = sum(1 for case_id in score_case_ids if case_id not in csv_map)
    if csv_cases and csv_missing < loaded_missing:
        return csv_cases
    return cases


def config_with_current_utl_settings(
    run_config: dict[str, Any],
    source_config: dict[str, Any] | None,
) -> dict[str, Any]:
    fixed = dict(run_config)
    for key in ("utl_applicable", "rag_config", "tags", "model_tags"):
        if source_config is not None and key in source_config:
            fixed[key] = source_config[key]
    return fixed


def resolved_config_list(
    run_configs: list[dict[str, Any]],
    config_by_id: dict[str, dict[str, Any]],
    outputs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    seen: set[str] = set()
    for config in run_configs:
        config_id = str(config.get("config_id") or "").strip()
        if not config_id:
            continue
        resolved.append(config_by_id.get(config_id, config))
        seen.add(config_id)
    for config_id in dict.fromkeys(str(row.get("config_id") or "").strip() for row in outputs):
        if config_id and config_id not in seen and config_id in config_by_id:
            resolved.append(config_by_id[config_id])
            seen.add(config_id)
    return resolved


def bool_or_none(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    return bool_from_metadata(value, False)


def set_metric_totals(row: dict[str, Any], utl_applicable: bool) -> None:
    if not utl_applicable:
        row["utl"] = 0
    row["utl_applicable"] = utl_applicable
    row["applicable_metrics"] = ",".join(metric_keys_for_score(utl_applicable))
    row["score_denominator"] = score_denominator(utl_applicable)
    row["raw_metric_score"] = raw_metric_score(row, utl_applicable)
    row["overall_score"] = score_total_from_metrics(row, utl_applicable)
    row["answer_quality_score"] = score_total_from_metrics(row, False)
    row["rag_quality_score"] = score_total_from_metrics(row, True)


def normalize_individual_scores(value: Any, utl_applicable: bool, pass_threshold: float) -> list[dict[str, Any]]:
    if not value:
        return []
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
    else:
        parsed = value
    if not isinstance(parsed, list):
        return []
    fixed: list[dict[str, Any]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        score = dict(item)
        if not utl_applicable:
            score["utl"] = 0
        score["utl_applicable"] = utl_applicable
        score["applicable_metrics"] = ",".join(metric_keys_for_score(utl_applicable))
        score["score_denominator"] = score_denominator(utl_applicable)
        score["raw_metric_score"] = raw_metric_score(score, utl_applicable)
        score["overall_score"] = score_total_from_metrics(score, utl_applicable)
        score["answer_quality_score"] = score_total_from_metrics(score, False)
        score["rag_quality_score"] = score_total_from_metrics(score, True)
        score["pass"] = score["overall_score"] >= pass_threshold and not bool_from_metadata(score.get("critical_fail"), False)
        fixed.append(score)
    return fixed


def recalc_static_fields(row: dict[str, Any], utl_applicable: bool, pass_threshold: float) -> dict[str, Any]:
    static = {
        key: row.get(f"static_{key}", row.get(key))
        for key in SCORE_METRIC_KEYS
    }
    if not utl_applicable:
        static["utl"] = 0
    static["utl_applicable"] = utl_applicable
    static_overall = score_total_from_metrics(static, utl_applicable)
    row.update({f"static_{key}": static.get(key) for key in SCORE_METRIC_KEYS})
    row["static_overall_score"] = static_overall
    row["static_raw_metric_score"] = raw_metric_score(static, utl_applicable)
    row["static_score_denominator"] = score_denominator(utl_applicable)
    row["static_pass"] = static_overall >= pass_threshold and not bool_from_metadata(row.get("static_critical_fail"), False)
    return static


def recalc_llm_fields(row: dict[str, Any], utl_applicable: bool, pass_threshold: float) -> dict[str, Any] | None:
    if str(row.get("llm_judge_status") or "").lower() != "ok":
        return None
    individual = normalize_individual_scores(row.get("llm_judge_individual_scores"), utl_applicable, pass_threshold)
    if individual:
        aggregate = dict(aggregate_llm_judge_scores(individual))
        aggregate["individual_scores"] = individual
    else:
        aggregate = {
            key: row.get(f"llm_judge_{key}", row.get(key))
            for key in SCORE_METRIC_KEYS
        }
        if not utl_applicable:
            aggregate["utl"] = 0
        aggregate.update(
            {
                "config_id": row.get("llm_judge_config_id", ""),
                "provider": row.get("llm_judge_provider", ""),
                "model": row.get("llm_judge_model", ""),
                "pass": bool_or_none(row.get("llm_judge_pass")),
                "critical_fail": bool_from_metadata(row.get("llm_judge_critical_fail"), False),
                "error_type": row.get("llm_judge_error_type", "normal"),
                "reason": row.get("llm_judge_reason", ""),
                "confidence": row.get("llm_judge_confidence", 0),
                "utl_applicable": utl_applicable,
            }
        )
        aggregate["score_denominator"] = score_denominator(utl_applicable)
        aggregate["raw_metric_score"] = raw_metric_score(aggregate, utl_applicable)
        aggregate["overall_score"] = score_total_from_metrics(aggregate, utl_applicable)
        aggregate["answer_quality_score"] = score_total_from_metrics(aggregate, False)
        aggregate["rag_quality_score"] = score_total_from_metrics(aggregate, True)
    aggregate["utl_applicable"] = utl_applicable
    aggregate["applicable_metrics"] = ",".join(metric_keys_for_score(utl_applicable))
    aggregate["score_denominator"] = score_denominator(utl_applicable)
    aggregate["raw_metric_score"] = raw_metric_score(aggregate, utl_applicable)
    aggregate["overall_score"] = score_total_from_metrics(aggregate, utl_applicable)
    aggregate["answer_quality_score"] = score_total_from_metrics(aggregate, False)
    aggregate["rag_quality_score"] = score_total_from_metrics(aggregate, True)
    if not utl_applicable:
        aggregate["utl"] = 0
    aggregate["pass"] = bool(aggregate.get("pass")) and aggregate["overall_score"] >= pass_threshold
    row["llm_judge_individual_scores"] = json.dumps(individual or aggregate.get("individual_scores", []), ensure_ascii=False, sort_keys=True)
    row["llm_judge_overall_score"] = aggregate["overall_score"]
    row["llm_judge_raw_metric_score"] = aggregate["raw_metric_score"]
    row["llm_judge_score_denominator"] = aggregate["score_denominator"]
    row["llm_judge_answer_quality_score"] = aggregate["answer_quality_score"]
    row["llm_judge_rag_quality_score"] = aggregate["rag_quality_score"]
    for key in SCORE_METRIC_KEYS:
        row[f"llm_judge_{key}"] = aggregate.get(key)
    row["llm_judge_pass"] = aggregate.get("pass")
    return aggregate


def apply_recalculated_score(
    row: dict[str, Any],
    *,
    config: dict[str, Any],
    case: dict[str, Any],
    output: dict[str, Any] | None,
    pass_threshold: float,
) -> tuple[dict[str, Any], bool]:
    fixed = dict(row)
    expected_utl = utl_applicable_for_score(case, config, output)
    old_utl = bool_from_metadata(row.get("utl_applicable"), True)
    old_overall = row.get("overall_score")
    old_individual_scores = row.get("llm_judge_individual_scores")
    static = recalc_static_fields(fixed, expected_utl, pass_threshold)
    judge = recalc_llm_fields(fixed, expected_utl, pass_threshold)
    mode = str(fixed.get("llm_judge_mode") or "").strip()
    scoring_mode = str(fixed.get("scoring_mode") or "").strip()
    if judge is not None and (mode or scoring_mode in {"static_llm", "llm_override", "blend"}):
        resolved_mode = mode or {"static_llm": "audit", "llm_override": "override", "blend": "blend"}.get(scoring_mode, "override")
        blend_weight = float(fixed.get("judge_blend_weight") or fixed.get("llm_judge_blend_weight") or 0.5)
        preserved = {
            key: fixed.get(key)
            for key in (
                "run_id",
                "case_id",
                "config_id",
                "output_fingerprint",
                "score_fingerprint",
                "merged_from_runs",
                "merged_ok_judge_count",
                "llm_judge_conflict_detected",
                "llm_judge_unresolved_conflict",
                "llm_judge_conflict_resolution_policy",
                "llm_judge_arbiter_config_id",
                "human_review_required",
                "release_gate_override",
            )
            if key in fixed
        }
        fixed = apply_llm_judge(
            static,
            judge,
            judge_config={
                "config_id": judge.get("config_id", fixed.get("llm_judge_config_id", "")),
                "provider": judge.get("provider", fixed.get("llm_judge_provider", "")),
                "model": judge.get("model", fixed.get("llm_judge_model", "")),
            },
            mode=resolved_mode,
            blend_weight=blend_weight,
            pass_threshold=pass_threshold,
            scoring_mode=scoring_mode or None,
        )
        fixed.update(preserved)
    else:
        set_metric_totals(fixed, expected_utl)
        fixed["pass"] = fixed["overall_score"] >= pass_threshold and not bool_from_metadata(fixed.get("critical_fail"), False)
    changed = (
        old_utl != expected_utl
        or str(old_overall) != str(fixed.get("overall_score"))
        or str(row.get("score_denominator")) != str(fixed.get("score_denominator"))
        or str(old_individual_scores or "") != str(fixed.get("llm_judge_individual_scores") or "")
    )
    return fixed, changed


def backup_run(run_dir: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = run_dir.with_name(f"{run_dir.name}__pre_utl_recalc_{stamp}")
    shutil.copytree(run_dir, backup_dir)
    return backup_dir


def repair_run(run_dir: Path, source_configs: dict[str, dict[str, Any]], *, backup: bool, export_ui: bool, final_ui_data: Path) -> dict[str, Any]:
    config = load_run_config(run_dir)
    if not config:
        return {"run": run_dir.name, "skipped": "missing config"}
    scores_path = run_dir / "judge_scores.jsonl"
    outputs_path = run_dir / "model_outputs.jsonl"
    if not scores_path.exists() or not outputs_path.exists():
        return {"run": run_dir.name, "skipped": "missing outputs or scores"}
    cases_file = resolve_path(config.get("case_source") or "")
    if not cases_file.exists():
        return {"run": run_dir.name, "skipped": f"missing case_source: {cases_file}"}
    cases, _ = load_cases_file(cases_file, suites=None, limit=None)
    outputs = read_jsonl(outputs_path)
    scores = read_jsonl(scores_path)
    cases = choose_cases_for_scores(run_dir, cases, scores)
    configs = list(config.get("configs") or [])
    run_config_by_id = config_map(configs)
    config_by_id = {
        config_id: config_with_current_utl_settings(run_config, source_configs.get(config_id))
        for config_id, run_config in run_config_by_id.items()
    }
    for config_id, source_config in source_configs.items():
        config_by_id.setdefault(config_id, dict(source_config))
    configs_for_output = resolved_config_list(configs, config_by_id, outputs)
    output_by_key = {(str(row.get("config_id") or ""), str(row.get("case_id") or "")): row for row in outputs}
    case_by_id = case_map(cases)
    pass_threshold = float(config.get("pass_threshold") or config.get("resolved_scoring", {}).get("pass_threshold") or 60.0)

    repaired: list[dict[str, Any]] = []
    changed = 0
    fixed_false = 0
    missing = 0
    for score in scores:
        config_id = str(score.get("config_id") or "")
        case_id = str(score.get("case_id") or "")
        cfg = config_by_id.get(config_id)
        case = case_by_id.get(case_id)
        output = output_by_key.get((config_id, case_id))
        if not cfg:
            missing += 1
            repaired.append(score)
            continue
        if not case:
            missing += 1
            case = {"case_id": case_id}
        fixed, did_change = apply_recalculated_score(
            score,
            config=cfg,
            case=case,
            output=output,
            pass_threshold=pass_threshold,
        )
        if not bool_from_metadata(fixed.get("utl_applicable"), True):
            fixed_false += 1
        changed += int(did_change)
        repaired.append(fixed)

    if backup:
        backup_dir = backup_run(run_dir)
    else:
        backup_dir = None
    run_id = str(config.get("run_id") or run_dir.name)
    eval_started_at = str(config.get("eval_started_at") or config.get("run_metadata", {}).get("eval_started_at") or "")
    if not eval_started_at:
        eval_started_at = datetime.now().isoformat(timespec="seconds")
    baseline_config = str(config.get("baseline_config") or (configs[0].get("config_id") if configs else ""))
    release_gate_config = config.get("matrix", {}).get("release_gates", {}) if isinstance(config.get("matrix"), dict) else {}
    config["configs"] = configs_for_output
    run_metadata = dict(config)
    run_metadata.update(
        {
            "run_id": run_id,
            "utl_recalculated_at": datetime.now().isoformat(timespec="seconds"),
            "utl_recalculated_rows": changed,
        }
    )
    write_run_outputs(
        run_dir=run_dir,
        run_id=run_id,
        cases=cases,
        configs=configs_for_output,
        outputs=outputs,
        scores=repaired,
        matrix=config.get("matrix", {}) if isinstance(config.get("matrix"), dict) else {},
        release_gate_config=release_gate_config,
        baseline_config=baseline_config,
        eval_started_at=eval_started_at,
        run_metadata=run_metadata,
        export_ui=export_ui,
        final_ui_data=final_ui_data,
    )
    config["utl_recalculated_at"] = run_metadata["utl_recalculated_at"]
    config["utl_recalculated_rows"] = changed
    (run_dir / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_dir / "config.yaml").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "run": run_dir.name,
        "rows": len(scores),
        "changed": changed,
        "utl_applicable_false": fixed_false,
        "missing_context": missing,
        "backup": str(backup_dir) if backup_dir else "",
    }


def candidate_runs(args: argparse.Namespace) -> list[Path]:
    if args.run_dir:
        return [resolve_path(path) for path in args.run_dir]
    if args.all:
        out_root = resolve_path(args.out_root)
        return [
            path
            for path in sorted(out_root.iterdir())
            if path.is_dir() and (path / "judge_scores.jsonl").exists() and (path / "config.json").exists()
        ]
    raise SystemExit("Pass --run-dir or --all")


def main() -> None:
    args = parse_args()
    source_config_path = resolve_path(args.source_config)
    source_configs: dict[str, dict[str, Any]] = {}
    if source_config_path.exists():
        source_config = load_config(source_config_path)
        if isinstance(source_config, dict):
            source_configs = config_map(source_config.get("configs") or [])
    summaries = [
        repair_run(
            run_dir,
            source_configs,
            backup=args.backup,
            export_ui=args.export_final_ui,
            final_ui_data=resolve_path(args.final_ui_data),
        )
        for run_dir in candidate_runs(args)
    ]
    print(json.dumps(summaries, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
