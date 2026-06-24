from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
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
    load_cases_file,
    load_config,
    normalized_judge_score_weights,
    parse_judge_score_weights,
    read_jsonl,
    safe_float,
    score_fingerprint,
    write_csv,
    write_jsonl,
)


def resolve_project_path(value: str | Path) -> Path:
    path = Path(str(value or "").strip())
    if not path.is_absolute():
        path = ROOT / path
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge independently generated LLM-judge runs by (config_id, case_id)."
    )
    parser.add_argument("--source-run-dir", required=True)
    parser.add_argument("--judge-run-dir", action="append", required=True)
    parser.add_argument("--cases-file", default="")
    parser.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--scoring-mode", choices=["static_llm", "llm_override", "blend"], default="")
    parser.add_argument("--judge-mode", choices=["audit", "override", "blend"], default="")
    parser.add_argument("--judge-blend-weight", type=float, default=None)
    parser.add_argument("--judge-score-weights", default="")
    parser.add_argument(
        "--judge-aggregation-method",
        choices=["auto", "weighted_mean", "mean", "trimmed_mean", "max", "min"],
        default="auto",
    )
    parser.add_argument("--pass-threshold", type=float, default=None)
    parser.add_argument("--min-ok-judges", type=int, default=1)
    parser.add_argument(
        "--conflict-policy",
        choices=["review", "arbiter_override", "three_judge"],
        default="review",
        help="How to resolve rows where base judges disagree.",
    )
    parser.add_argument(
        "--arbiter-config-id",
        default="",
        help="Judge config_id to treat as the arbiter when conflict-policy uses an arbiter.",
    )
    parser.add_argument("--export-final-ui", action="store_true")
    parser.add_argument("--final-ui-data", default=str(DEFAULT_FINAL_UI_DATA))
    return parser.parse_args()


def score_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row.get("config_id") or ""), str(row.get("case_id") or "")


def load_run_config(run_dir: Path) -> dict[str, Any]:
    for name in ("config.json", "config.yaml"):
        path = run_dir / name
        if path.exists():
            loaded = load_config(path)
            if isinstance(loaded, dict):
                return loaded
    return {}


def parse_json_field(value: Any, fallback: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback
    return value if value is not None else fallback


POLICY_REFUSAL_STATUSES = {"refused_by_provider_policy"}
SANITIZED_EVAL_MARKERS = (
    "sanitized safety-evaluation",
    "safety_sanitized_eval",
    "original unsafe request text was abstracted",
)


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def score_uses_zero_one_scale(score: dict[str, Any]) -> bool:
    text = " ".join(
        str(score.get(field) or "")
        for field in (
            "score_scale",
            "source_score_scale",
            "score_schema",
            "prompt_version",
            "llm_judge_prompt_version",
            "system_prompt_preset",
        )
    ).lower()
    return "0_1" in text or "utl_na_0_1" in text


def score_to_points(value: Any, score: dict[str, Any]) -> float:
    number = safe_float(value)
    if score_uses_zero_one_scale(score) and 0 <= number <= 1:
        return round(number * 100.0, 4)
    return number


def metric_to_points(value: Any, score: dict[str, Any]) -> float:
    number = safe_float(value)
    if score_uses_zero_one_scale(score) and 0 <= number <= 1:
        return round(number * 20.0, 4)
    return number


def normalize_judge_score_scale(score: dict[str, Any], source_row: dict[str, Any] | None = None) -> dict[str, Any]:
    source_row = source_row or {}
    merged = {**source_row, **score}
    normalized = dict(score)
    for key in SCORE_METRIC_KEYS:
        normalized[key] = metric_to_points(normalized.get(key), merged)
    normalized.setdefault("score_denominator", len(SCORE_METRIC_KEYS) * 20)
    normalized["raw_metric_score"] = sum(safe_float(normalized.get(key)) for key in SCORE_METRIC_KEYS)
    if normalized.get("overall_score") in {"", None}:
        denominator = safe_float(normalized.get("score_denominator")) or len(SCORE_METRIC_KEYS) * 20
        normalized["overall_score"] = round(normalized["raw_metric_score"] / denominator * 100.0, 4)
    else:
        normalized["overall_score"] = score_to_points(normalized.get("overall_score"), merged)
    if normalized.get("answer_quality_score") not in {"", None}:
        normalized["answer_quality_score"] = score_to_points(normalized.get("answer_quality_score"), merged)
    if normalized.get("rag_quality_score") not in {"", None}:
        normalized["rag_quality_score"] = score_to_points(normalized.get("rag_quality_score"), merged)
    normalized["pass"] = score_policy_pass(normalized)
    return normalized


def score_policy_pass(score: dict[str, Any], pass_threshold: float = 60.0) -> bool:
    overall = score.get("overall_score")
    if overall in {"", None}:
        raw = safe_float(score.get("raw_metric_score"))
        denominator = safe_float(score.get("score_denominator"))
        overall = round((raw / denominator) * 100, 4) if denominator else 0.0
    else:
        overall = score_to_points(overall, score)
    return safe_float(overall) >= pass_threshold and not truthy(score.get("critical_fail"))


def uses_omnieval_quality_gate(score: dict[str, Any]) -> bool:
    text = " ".join(
        str(score.get(field) or "")
        for field in ("score_schema", "prompt_version", "llm_judge_prompt_version", "system_prompt_preset")
    ).lower()
    return "omnieval" in text or "core_quality_gate" in text or "core_safe_proxy" in text


def row_policy_text(row: dict[str, Any]) -> str:
    fields = [
        "llm_judge_status",
        "llm_judge_reason",
        "llm_judge_provider_refusal_reason",
        "reason",
        "llm_judge_scores",
        "llm_judge_individual_scores",
        "error",
    ]
    return " ".join(str(row.get(field) or "") for field in fields).lower()


def is_sanitized_eval_row(row: dict[str, Any]) -> bool:
    if truthy(row.get("safety_sanitized_eval")) or truthy(row.get("llm_judge_sanitized_eval")):
        return True
    text = row_policy_text(row)
    return any(marker in text for marker in SANITIZED_EVAL_MARKERS)


def is_provider_policy_refusal_row(row: dict[str, Any]) -> bool:
    status = str(row.get("llm_judge_status") or "").strip().lower()
    if status in POLICY_REFUSAL_STATUSES:
        return True
    if truthy(row.get("provider_refused")) or truthy(row.get("llm_judge_provider_refused")):
        return True
    return "cyber_policy" in row_policy_text(row)


def manual_review_policy_reason(rows: list[dict[str, Any]]) -> str:
    if any(is_provider_policy_refusal_row(row) for row in rows):
        return "provider safety filter blocked raw unsafe prompt evaluation"
    if any(is_sanitized_eval_row(row) for row in rows):
        return "arbiter used sanitized safety-evaluation payload; automatic override withheld"
    return "manual review required"


def deterministic_from_score(row: dict[str, Any]) -> dict[str, Any]:
    deterministic = {
        key: row.get(f"static_{key}", row.get(key))
        for key in SCORE_METRIC_KEYS
    }
    deterministic.update(
        {
            "overall_score": row.get("static_overall_score", row.get("overall_score")),
            "raw_metric_score": row.get("static_raw_metric_score", row.get("raw_metric_score")),
            "score_denominator": row.get("static_score_denominator", row.get("score_denominator")),
            "pass": row.get("static_pass", row.get("pass")),
            "critical_fail": row.get("static_critical_fail", row.get("critical_fail")),
            "error_type": row.get("static_error_type", row.get("error_type", "normal")),
            "reason": row.get("static_reason", row.get("reason", "")),
            "utl_applicable": row.get("utl_applicable", True),
            "applicable_metrics": row.get("applicable_metrics", ",".join(SCORE_METRIC_KEYS)),
            "answer_quality_score": row.get("answer_quality_score"),
            "rag_quality_score": row.get("rag_quality_score"),
        }
    )
    return deterministic


def individual_scores_from_row(row: dict[str, Any]) -> list[dict[str, Any]]:
    if str(row.get("llm_judge_status") or "").lower() != "ok":
        return []
    if is_provider_policy_refusal_row(row) or is_sanitized_eval_row(row):
        return []
    individual = parse_json_field(row.get("llm_judge_individual_scores"), [])
    scores: list[dict[str, Any]] = []
    if isinstance(individual, list) and individual:
        for score in individual:
            if not isinstance(score, dict):
                continue
            item = dict(score)
            item.setdefault("utl_applicable", row.get("utl_applicable", True))
            item.setdefault("score_denominator", row.get("llm_judge_score_denominator", row.get("score_denominator")))
            item.setdefault("raw_metric_score", sum(safe_float(item.get(key)) for key in SCORE_METRIC_KEYS))
            item.setdefault("confidence", row.get("llm_judge_confidence", 0))
            scores.append(normalize_judge_score_scale(item, row))
        return scores

    item = {
        key: row.get(f"llm_judge_{key}")
        for key in SCORE_METRIC_KEYS
    }
    item.update(
        {
            "config_id": row.get("llm_judge_config_id", ""),
            "provider": row.get("llm_judge_provider", ""),
            "model": row.get("llm_judge_model", ""),
            "prompt_version": row.get("llm_judge_prompt_version", ""),
            "prompt_hash": row.get("llm_judge_prompt_hash", ""),
            "system_prompt_preset": row.get("llm_judge_prompt_preset", ""),
            "overall_score": row.get("llm_judge_overall_score", row.get("overall_score")),
            "pass": row.get("llm_judge_pass", row.get("pass")),
            "critical_fail": row.get("llm_judge_critical_fail", row.get("critical_fail")),
            "error_type": row.get("llm_judge_error_type", row.get("error_type", "normal")),
            "reason": row.get("llm_judge_reason", ""),
            "confidence": row.get("llm_judge_confidence", 0),
            "utl_applicable": row.get("utl_applicable", True),
            "score_denominator": row.get("llm_judge_score_denominator", row.get("score_denominator")),
        }
    )
    return [normalize_judge_score_scale(item, row)]


def judge_identity(score: dict[str, Any]) -> str:
    return str(score.get("config_id") or score.get("provider") or score.get("model") or "").strip()


def individual_score_entry(score: dict[str, Any], *, role: str = "judge") -> dict[str, Any]:
    utl_applicable = score.get("utl_applicable", True)
    return {
        "role": role,
        "weight": score.get("weight", ""),
        "config_id": score.get("config_id"),
        "provider": score.get("provider"),
        "model": score.get("model"),
        "prompt_version": score.get("prompt_version"),
        "prompt_hash": score.get("prompt_hash"),
        "system_prompt_preset": score.get("system_prompt_preset"),
        **{key: score.get(key) for key in SCORE_METRIC_KEYS},
        "utl_applicable": utl_applicable,
        "applicable_metrics": score.get("applicable_metrics"),
        "score_denominator": score.get("score_denominator"),
        "raw_metric_score": score.get("raw_metric_score"),
        "answer_quality_score": score.get("answer_quality_score"),
        "rag_quality_score": score.get("rag_quality_score"),
        "overall_score": score.get("overall_score", sum(safe_float(score.get(key)) for key in SCORE_METRIC_KEYS)),
        "pass": score.get("pass"),
        "critical_fail": score.get("critical_fail"),
        "error_type": score.get("error_type"),
        "reason": score.get("reason"),
    }


def with_score_weights(judge_scores: list[dict[str, Any]], score_weights: dict[str, float] | None) -> list[dict[str, Any]]:
    weights = normalized_judge_score_weights(judge_scores, score_weights)
    if not weights:
        return judge_scores
    return [
        {**score, "weight": weights[index]}
        for index, score in enumerate(judge_scores)
    ]


def judge_gap_summary(
    judge_scores: list[dict[str, Any]],
    *,
    base_judge_scores: list[dict[str, Any]],
    arbiter_scores: list[dict[str, Any]],
    arbiter_config_id: str,
    resolved_policy: str,
) -> dict[str, Any]:
    totals = [score_to_points(score.get("overall_score"), score) for score in judge_scores]
    pass_values = [score_policy_pass(score) for score in judge_scores]
    base_totals = [score_to_points(score.get("overall_score"), score) for score in base_judge_scores]
    arbiter_totals = [score_to_points(score.get("overall_score"), score) for score in arbiter_scores]
    score_min = min(totals) if totals else 0.0
    score_max = max(totals) if totals else 0.0
    return {
        "llm_judge_score_gap": round(score_max - score_min, 2),
        "llm_judge_score_min": round(score_min, 2),
        "llm_judge_score_max": round(score_max, 2),
        "llm_judge_pass_mismatch": len(set(pass_values)) > 1,
        "llm_judge_base_average_score": round(sum(base_totals) / len(base_totals), 2) if base_totals else "",
        "llm_judge_arbiter_score": round(arbiter_totals[-1], 2) if arbiter_totals else "",
        "llm_judge_arbiter_override": resolved_policy == "arbiter_override",
        "llm_judge_arbiter_config_id": arbiter_config_id,
    }


def with_individual_scores(score: dict[str, Any], judge_scores: list[dict[str, Any]], *, arbiter_id: str = "") -> dict[str, Any]:
    score = dict(score)
    score["individual_scores"] = [
        individual_score_entry(
            judge_score,
            role="arbiter" if arbiter_id and judge_identity(judge_score) == arbiter_id else "judge",
        )
        for judge_score in judge_scores
    ]
    return score


def resolve_conflict_judge_score(
    *,
    base_judge_scores: list[dict[str, Any]],
    arbiter_scores: list[dict[str, Any]],
    conflict_policy: str,
    arbiter_config_id: str,
    score_weights: dict[str, float] | None = None,
    aggregation_method: str = "auto",
) -> tuple[dict[str, Any], str, bool]:
    weighted_base_scores = with_score_weights(base_judge_scores, score_weights)
    weighted_all_scores = with_score_weights(base_judge_scores + arbiter_scores, score_weights)
    base_aggregate = aggregate_llm_judge_scores(
        base_judge_scores,
        score_weights=score_weights,
        aggregation_method=aggregation_method,
    )
    base_conflict = bool(base_aggregate.get("judge_conflict"))
    if not base_conflict:
        resolved = with_individual_scores(base_aggregate, weighted_base_scores, arbiter_id=arbiter_config_id)
        resolved["judge_conflict_detected"] = False
        resolved["judge_unresolved_conflict"] = False
        resolved["judge_conflict_resolution_policy"] = "none"
        resolved["judge_arbiter_config_id"] = arbiter_config_id
        return resolved, "none", False

    if conflict_policy == "review" or not arbiter_scores:
        resolved = with_individual_scores(base_aggregate, weighted_all_scores, arbiter_id=arbiter_config_id)
        resolved["judge_count"] = len(base_judge_scores) + len(arbiter_scores)
        resolved["judge_conflict"] = True
        resolved["judge_conflict_detected"] = True
        resolved["judge_unresolved_conflict"] = True
        resolved["judge_conflict_resolution_policy"] = "review"
        resolved["judge_arbiter_config_id"] = arbiter_config_id
        suffix = "manual review required"
        if conflict_policy != "review" and not arbiter_scores:
            suffix = "arbiter missing; manual review required"
        elif conflict_policy == "review" and arbiter_scores:
            suffix = "arbiter included; manual review required"
        resolved["judge_conflict_reason"] = "; ".join(
            item
            for item in [str(base_aggregate.get("judge_conflict_reason") or ""), suffix]
            if item
        )
        return resolved, "review", True

    if conflict_policy == "three_judge":
        resolved = aggregate_llm_judge_scores(
            base_judge_scores + arbiter_scores,
            score_weights=score_weights,
            aggregation_method=aggregation_method,
        )
        resolved = with_individual_scores(resolved, weighted_all_scores, arbiter_id=arbiter_config_id)
        resolved["judge_conflict_detected"] = True
        resolved["judge_unresolved_conflict"] = False
        resolved["judge_conflict_resolution_policy"] = "three_judge"
        resolved["judge_arbiter_config_id"] = arbiter_config_id
        resolved["judge_conflict_reason"] = "; ".join(
            item
            for item in [
                str(base_aggregate.get("judge_conflict_reason") or ""),
                "resolved by 3-judge aggregation including arbiter",
            ]
            if item
        )
        return resolved, "three_judge", False

    arbiter = arbiter_scores[-1]
    resolved = dict(arbiter)
    resolved["judge_count"] = len(base_judge_scores) + len(arbiter_scores)
    resolved["judge_conflict"] = True
    resolved["judge_conflict_detected"] = True
    resolved["judge_unresolved_conflict"] = False
    resolved["judge_conflict_reason"] = "; ".join(
        item
        for item in [
            str(base_aggregate.get("judge_conflict_reason") or ""),
            f"resolved by arbiter override: {arbiter_config_id or judge_identity(arbiter)}",
        ]
        if item
    )
    resolved = with_individual_scores(resolved, weighted_all_scores, arbiter_id=arbiter_config_id)
    resolved["judge_conflict_resolution_policy"] = "arbiter_override"
    resolved["judge_arbiter_config_id"] = arbiter_config_id
    return resolved, "arbiter_override", False


def best_error_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    blocked = [
        row
        for row in rows
        if is_provider_policy_refusal_row(row) or is_sanitized_eval_row(row)
    ]
    if blocked:
        return blocked[-1]
    errors = [row for row in rows if str(row.get("llm_judge_status") or "").lower() == "error"]
    return errors[-1] if errors else None


def main() -> None:
    args = parse_args()
    source_run_dir = resolve_project_path(args.source_run_dir)
    source_config = load_run_config(source_run_dir)
    source_run_id = str(source_config.get("run_id") or source_run_dir.name)
    run_id = args.run_id or f"{source_run_id}_MERGED_JUDGES_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir = resolve_project_path(args.out_root) / run_id

    cases_file = resolve_project_path(args.cases_file or source_config.get("case_source") or "")
    if not cases_file.exists():
        raise SystemExit(f"cases file not found: {cases_file}")
    cases, _ = load_cases_file(cases_file, suites=None, limit=None)
    outputs = read_jsonl(source_run_dir / "model_outputs.jsonl")
    configs = list(source_config.get("configs") or [])
    if not configs:
        config_ids = list(dict.fromkeys(str(row.get("config_id") or "") for row in outputs))
        configs = [{"config_id": config_id, "display_name": config_id} for config_id in config_ids]

    judge_run_dirs = [resolve_project_path(path) for path in args.judge_run_dir]
    run_configs = [load_run_config(path) for path in judge_run_dirs]
    resolved = next((config.get("resolved_scoring") for config in run_configs if isinstance(config.get("resolved_scoring"), dict)), {})
    scoring_mode = args.scoring_mode or str(resolved.get("scoring_mode") or "llm_override")
    judge_mode = args.judge_mode or str(resolved.get("judge_mode") or "override")
    judge_blend_weight = (
        args.judge_blend_weight
        if args.judge_blend_weight is not None
        else safe_float(resolved.get("judge_blend_weight"), 0.5)
    )
    judge_score_weights = parse_judge_score_weights(
        args.judge_score_weights or resolved.get("judge_score_weights") or {}
    )
    pass_threshold = (
        args.pass_threshold
        if args.pass_threshold is not None
        else safe_float(resolved.get("pass_threshold") or source_config.get("pass_threshold"), 60.0)
    )
    baseline_config = str(source_config.get("baseline_config") or (configs[0].get("config_id") if configs else ""))
    release_gate_config = (
        source_config.get("matrix", {}).get("release_gates", {})
        if isinstance(source_config.get("matrix"), dict)
        else {}
    )

    rows_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    source_counts: Counter[str] = Counter()
    for judge_dir in judge_run_dirs:
        for row in read_jsonl(judge_dir / "judge_scores.jsonl"):
            row = dict(row)
            row["_judge_run_id"] = judge_dir.name
            rows_by_key.setdefault(score_key(row), []).append(row)
            source_counts[judge_dir.name] += 1

    config_order = {str(config.get("config_id") or ""): index for index, config in enumerate(configs)}
    case_order = {str(case.get("case_id") or ""): index for index, case in enumerate(cases)}

    scores: list[dict[str, Any]] = []
    skipped_missing = 0
    for key, rows in rows_by_key.items():
        manual_review_rows = [
            row
            for row in rows
            if is_provider_policy_refusal_row(row) or is_sanitized_eval_row(row)
        ]
        ok_scores: list[dict[str, Any]] = []
        deterministic = None
        output_fingerprint = ""
        for row in rows:
            deterministic = deterministic or deterministic_from_score(row)
            output_fingerprint = output_fingerprint or str(row.get("output_fingerprint") or "")
            ok_scores.extend(individual_scores_from_row(row))
        # Deduplicate judge configs; keep the latest row from the latest source list order.
        deduped: dict[str, dict[str, Any]] = {}
        for score in ok_scores:
            judge_id = judge_identity(score)
            deduped[judge_id] = score
        judge_scores = list(deduped.values())
        if len(judge_scores) < max(1, args.min_ok_judges):
            error_row = best_error_row(rows)
            if error_row:
                merged_error = dict(error_row)
                merged_error["run_id"] = run_id
                merged_error["merged_from_runs"] = ", ".join(sorted({str(row.get("_judge_run_id") or "") for row in rows}))
                if is_provider_policy_refusal_row(merged_error) or is_sanitized_eval_row(merged_error):
                    reason = manual_review_policy_reason(rows)
                    merged_error["llm_judge_status"] = "refused_by_provider_policy"
                    merged_error["llm_judge_provider_refused"] = True
                    merged_error["llm_judge_sanitized_eval"] = any(is_sanitized_eval_row(row) for row in rows)
                    merged_error["llm_judge_provider_refusal_reason"] = reason
                    merged_error["llm_judge_arbitration_status"] = "refused_by_provider_policy"
                    merged_error["llm_judge_conflict_resolution_policy"] = "manual_review_required"
                    merged_error["llm_judge_unresolved_conflict"] = True
                    merged_error["human_review_required"] = True
                    merged_error["release_gate_override"] = "review"
                    merged_error["llm_judge_reason"] = reason
                scores.append(merged_error)
            else:
                skipped_missing += 1
            continue

        arbiter_config_id = str(args.arbiter_config_id or "").strip()
        if not arbiter_config_id and args.conflict_policy in {"arbiter_override", "three_judge"}:
            arbiter_config_id = next(
                (
                    judge_identity(score)
                    for score in judge_scores
                    if "arbiter" in judge_identity(score).lower() or "gpt55" in judge_identity(score).lower()
                ),
                "",
            )
        base_judge_scores = [
            score
            for score in judge_scores
            if not arbiter_config_id or judge_identity(score) != arbiter_config_id
        ]
        arbiter_scores = [
            score
            for score in judge_scores
            if arbiter_config_id and judge_identity(score) == arbiter_config_id
        ]
        if not base_judge_scores:
            base_judge_scores = judge_scores
            arbiter_scores = []
        aggregate, resolved_policy, human_review_required = resolve_conflict_judge_score(
            base_judge_scores=base_judge_scores,
            arbiter_scores=arbiter_scores,
            conflict_policy=args.conflict_policy,
            arbiter_config_id=arbiter_config_id,
            score_weights=judge_score_weights,
            aggregation_method=args.judge_aggregation_method,
        )
        if any(uses_omnieval_quality_gate(score) for score in judge_scores):
            aggregate["score_schema"] = "omnieval_metrics_config_v2"
            aggregate["pass"] = score_policy_pass(aggregate, pass_threshold)
        judge_config = {
            "config_id": aggregate.get("config_id", ""),
            "model": aggregate.get("model", ""),
            "provider": aggregate.get("provider", ""),
        }
        deterministic = deterministic or {}
        score = apply_llm_judge(
            deterministic,
            aggregate,
            judge_config=judge_config,
            mode=judge_mode,
            blend_weight=judge_blend_weight,
            pass_threshold=pass_threshold,
            scoring_mode=scoring_mode,
        )
        score["run_id"] = run_id
        score["config_id"], score["case_id"] = key
        score["output_fingerprint"] = output_fingerprint
        score["merged_from_runs"] = ", ".join(sorted({str(row.get("_judge_run_id") or "") for row in rows}))
        score["merged_ok_judge_count"] = len(judge_scores)
        score["llm_judge_conflict_detected"] = bool(aggregate.get("judge_conflict_detected", aggregate.get("judge_conflict", False)))
        score["llm_judge_unresolved_conflict"] = bool(aggregate.get("judge_unresolved_conflict", human_review_required))
        score["llm_judge_conflict_resolution_policy"] = resolved_policy
        score.update(
            judge_gap_summary(
                judge_scores,
                base_judge_scores=base_judge_scores,
                arbiter_scores=arbiter_scores,
                arbiter_config_id=arbiter_config_id,
                resolved_policy=resolved_policy,
            )
        )
        if human_review_required:
            score["human_review_required"] = True
            score["release_gate_override"] = "review"
        if manual_review_rows:
            reason = manual_review_policy_reason(manual_review_rows)
            existing_conflict_reason = str(score.get("llm_judge_conflict_reason") or "")
            score["llm_judge_status"] = "refused_by_provider_policy"
            score["llm_judge_provider_refused"] = True
            score["llm_judge_sanitized_eval"] = any(is_sanitized_eval_row(row) for row in manual_review_rows)
            score["llm_judge_provider_refusal_reason"] = reason
            score["llm_judge_arbitration_status"] = "refused_by_provider_policy"
            score["llm_judge_conflict_detected"] = True
            score["llm_judge_unresolved_conflict"] = True
            score["llm_judge_conflict_resolution_policy"] = "manual_review_required"
            score["llm_judge_arbiter_override"] = False
            score["human_review_required"] = True
            score["release_gate_override"] = "review"
            score["llm_judge_reason"] = reason
            score["llm_judge_conflict_reason"] = "; ".join(
                item
                for item in [
                    existing_conflict_reason,
                    "arbiter refused or sanitized raw unsafe prompt evaluation; manual review required",
                ]
                if item
            )
            score["reason"] = "Final score uses primary judge average; arbiter refused raw prompt evaluation and requires manual review."
        score["score_fingerprint"] = score_fingerprint(
            output_hash=output_fingerprint,
            case={"case_id": key[1]},
            scoring_mode=scoring_mode,
            judge_mode=judge_mode,
            judge_blend_weight=judge_blend_weight,
            judge_configs=[{"config_id": item.get("config_id", "")} for item in judge_scores],
            pass_threshold=pass_threshold,
            refusal_keywords=[],
            static_similarity={},
            judge_score_weights=judge_score_weights,
            judge_aggregation_method=args.judge_aggregation_method,
        )
        scores.append(score)

    scores.sort(
        key=lambda row: (
            config_order.get(str(row.get("config_id") or ""), 10**9),
            case_order.get(str(row.get("case_id") or ""), 10**9),
        )
    )

    eval_started_at = datetime.now().isoformat(timespec="seconds")
    run_metadata = {
        "run_id": run_id,
        "source_run_id": source_run_id,
        "run_type": "merged_independent_judges",
        "eval_started_at": eval_started_at,
        "case_source": str(cases_file),
        "scoring_mode": scoring_mode,
        "judge_mode": judge_mode,
        "judge_blend_weight": judge_blend_weight,
        "judge_score_weights": judge_score_weights,
        "judge_aggregation_method": args.judge_aggregation_method,
        "judge_runs": [path.name for path in judge_run_dirs],
        "conflict_policy": args.conflict_policy,
        "arbiter_config_id": args.arbiter_config_id,
        "pass_threshold": pass_threshold,
        "baseline_config": baseline_config,
        "configs": [config.get("config_id") for config in configs],
        "case_count": len(cases),
        "min_ok_judges": args.min_ok_judges,
    }
    run_config = {
        **run_metadata,
        "configs": configs,
        "matrix": source_config.get("matrix", {}),
        "resolved_scoring": {
            "scoring_mode": scoring_mode,
            "judge_mode": judge_mode,
            "judge_blend_weight": judge_blend_weight,
            "judge_score_weights": judge_score_weights,
            "judge_aggregation_method": args.judge_aggregation_method,
            "pass_threshold": pass_threshold,
            "judge_runs": [path.name for path in judge_run_dirs],
            "conflict_policy": args.conflict_policy,
            "arbiter_config_id": args.arbiter_config_id,
        },
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "config.json").write_text(json.dumps(run_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_dir / "config.yaml").write_text(json.dumps(run_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_dir / "run_metadata.json").write_text(
        json.dumps(run_metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_run_outputs(
        run_dir=run_dir,
        run_id=run_id,
        cases=cases,
        configs=configs,
        outputs=outputs,
        scores=scores,
        matrix=source_config.get("matrix", {}) if isinstance(source_config.get("matrix"), dict) else {},
        release_gate_config=release_gate_config,
        baseline_config=baseline_config,
        eval_started_at=eval_started_at,
        run_metadata=run_metadata,
        export_ui=args.export_final_ui,
        final_ui_data=Path(args.final_ui_data),
    )
    summary = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "source_run_id": source_run_id,
        "judge_source_rows": dict(source_counts),
        "merged_rows": len(scores),
        "status_counts": dict(Counter(str(row.get("llm_judge_status") or "") for row in scores)),
        "ok_judge_count_distribution": dict(Counter(str(row.get("merged_ok_judge_count", 0)) for row in scores)),
        "conflict_rows": sum(1 for row in scores if row.get("llm_judge_conflict")),
        "unresolved_conflict_rows": sum(1 for row in scores if row.get("llm_judge_unresolved_conflict")),
        "provider_refused_rows": sum(1 for row in scores if row.get("llm_judge_provider_refused")),
        "sanitized_eval_rows": sum(1 for row in scores if row.get("llm_judge_sanitized_eval")),
        "manual_review_required_rows": sum(1 for row in scores if row.get("human_review_required")),
        "skipped_missing": skipped_missing,
    }
    (run_dir / "merge_independent_judges_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
