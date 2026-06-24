from __future__ import annotations

import csv
import json
import shutil
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
UI_RUNTIME_DATA = ROOT / "final_UI" / "data"
CURRENT_UI_DATA_RUN_IDS = {"__ui_runtime_data__", "__final_ui_data__"}
EVAL_SNAPSHOT = ROOT / "data" / "eval_snapshot_20260624_094927"
SCORES_DIR = EVAL_SNAPSHOT / "scores"
REPORTS_DIR = EVAL_SNAPSHOT / "reports"
SCORE_CONFIG_PATH = SCORES_DIR / "omnieval_metrics_config_v2.json"
MANIFEST_PATH = EVAL_SNAPSHOT / "manifest.json"

KST = timezone(timedelta(hours=9))
SNAPSHOT_RUN_ID = "eval_snapshot_20260624_094927"
SNAPSHOT_RUN_TYPE = "omnieval_metrics_v2_snapshot"
RUBRIC_VERSION = "omnieval_metrics_config.v2"
SCHEMA_VERSION = "omnieval_metrics_config_v2"
PASS_POLICY = "mean_acc_com_nac_hal_pass_gte_0_60"
PASS_THRESHOLD = 0.60
ACTIVE_METRICS = ("acc", "com", "nac", "hal_pass")
SCORE_DERIVATION_POLICY = "ui_exported_llm_judge_individual_scores"


def ensure_inside(base: Path, target: Path) -> None:
    base_resolved = base.resolve()
    target_resolved = target.resolve()
    try:
        target_resolved.relative_to(base_resolved)
    except ValueError as exc:
        raise RuntimeError(f"Refusing to write outside {base_resolved}: {target_resolved}") from exc


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    ensure_inside(ROOT, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            text = line.strip()
            if text:
                rows.append(json.loads(text))
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_inside(ROOT, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def archive_files(paths: list[Path]) -> Path:
    stamp = datetime.now(KST).strftime("%Y%m%d_%H%M%S")
    archive_root = ROOT / "out" / "archive" / f"score_scale_v2_originals_{stamp}"
    ensure_inside(ROOT / "out" / "archive", archive_root)
    for path in paths:
        if not path.exists():
            continue
        ensure_inside(ROOT, path)
        target = archive_root / path.relative_to(ROOT)
        ensure_inside(archive_root, target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    return archive_root


def safe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def first_present(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y", "pass"}


def json_list_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def score01(value: Any) -> float | None:
    number = safe_float(value)
    if number is None or number < 0:
        return None
    if number <= 1:
        return round(number, 6)
    return round(min(number, METRIC_MAX_OLD) / METRIC_MAX_OLD, 6)


def fmt(value: float | None, digits: int = 6) -> str:
    if value is None:
        return ""
    text = f"{value:.{digits}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def mean(values: list[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean), 6)


def metric_mean(rows: list[dict[str, Any]], key: str) -> float:
    clean = [safe_float(row.get(key)) for row in rows]
    clean = [value for value in clean if value is not None]
    return round(sum(clean) / len(clean), 6) if clean else 0.0


def pass_fail(overall: float) -> str:
    return "Pass" if overall >= PASS_THRESHOLD else "Fail"


def agreement_status(overall_gap: float, pass_mismatch: bool) -> tuple[str, str]:
    if pass_mismatch or overall_gap >= 0.30:
        return "review_needed", "high"
    if overall_gap >= 0.15:
        return "borderline", "medium"
    return "stable", "low"


def canonical_error_type(value: Any) -> str:
    text = str(value or "").strip()
    return text or "normal"


def judge_label(item: dict[str, Any], row: dict[str, Any], index: int) -> str:
    explicit = first_present(item, "label", "judge_label", "config_id", "judge_config_id")
    if explicit:
        return str(explicit)
    model = first_present(item, "model", "judge_model", "llm_judge_model") or row.get("llm_judge_model")
    provider = first_present(item, "provider", "judge_provider", "llm_judge_provider") or row.get("llm_judge_provider")
    if model:
        return str(model)
    if provider:
        return str(provider)
    return f"judge_{index + 1}"


def normalized_judge_item(item: dict[str, Any], row: dict[str, Any], index: int) -> dict[str, Any]:
    acc = score01(first_present(item, "acc", "accuracy"))
    com = score01(first_present(item, "com", "completeness"))
    nac = score01(first_present(item, "nac", "numeric_accuracy"))
    hal_pass = score01(item.get("hal_pass"))
    if any(value is None for value in (acc, com, nac, hal_pass)):
        question = row.get("question_id") or row.get("case_id") or "-"
        target = row.get("version") or row.get("target_config_id") or "-"
        raise RuntimeError(f"Missing OmniEval judge score for {target}/{question}")
    hal_rate = round(1.0 - hal_pass, 6)
    values = [acc, com, nac, hal_pass]
    overall = score01(item.get("overall_score"))
    if overall is None:
        overall = mean(values) or 0.0
    config_id = str(first_present(item, "config_id", "judge_config_id") or row.get("llm_judge_config_id") or judge_label(item, row, index))
    provider = str(first_present(item, "provider", "judge_provider", "llm_judge_provider") or row.get("llm_judge_provider") or "")
    model = str(first_present(item, "model", "judge_model", "llm_judge_model") or row.get("llm_judge_model") or "")
    return {
        "schema": "omnieval_metrics_v2_judge_score",
        "config_id": config_id,
        "label": judge_label(item, row, index),
        "provider": provider,
        "model": model,
        "role": "judge",
        "target_config_id": row.get("version") or row.get("target_config_id") or "",
        "question_id": row.get("question_id") or row.get("case_id") or "",
        "acc": acc,
        "com": com,
        "nac": nac,
        "hal": hal_rate,
        "hal_rate": hal_rate,
        "hal_pass": hal_pass,
        "overall_score": overall,
        "pass": overall >= PASS_THRESHOLD,
        "critical_fail": bool_value(item.get("critical_fail")),
        "error_type": canonical_error_type(item.get("error_type")),
        "reason": item.get("reason", ""),
        "score_schema": SCHEMA_VERSION,
    }


def load_judge_scores_from_question_rows(
    question_rows: list[dict[str, str]],
) -> tuple[dict[tuple[str, str], list[dict[str, Any]]], list[dict[str, Any]]]:
    by_case: dict[tuple[str, str], list[dict[str, Any]]] = {}
    all_rows: list[dict[str, Any]] = []
    for row in question_rows:
        target = str(row.get("version") or row.get("target_config_id") or "").strip()
        question = str(row.get("question_id") or row.get("case_id") or "").strip()
        if not target or not question:
            continue
        scores = []
        for index, item in enumerate(json_list_value(row.get("llm_judge_individual_scores"))):
            if isinstance(item, dict):
                scores.append(normalized_judge_item(item, row, index))
        if scores:
            by_case[(target, question)] = scores
            all_rows.extend(scores)
    return by_case, all_rows


def consensus_for(key: tuple[str, str], judge_scores: dict[tuple[str, str], list[dict[str, Any]]]) -> dict[str, Any]:
    joined = judge_scores.get(key) or []
    if not joined:
        raise RuntimeError(f"Missing judge score for {key}")
    acc = mean([row.get("acc") for row in joined])
    com = mean([row.get("com") for row in joined])
    nac = mean([row.get("nac") for row in joined])
    hal_pass = mean([row.get("hal_pass") for row in joined])
    hal_rate = round(1.0 - hal_pass, 6) if hal_pass is not None else None
    values = [acc, com, nac, hal_pass]
    overall = mean(values) or 0.0
    per_judge_overalls = [safe_float(row.get("overall_score")) or 0.0 for row in joined]
    overall_gap = round(max(per_judge_overalls) - min(per_judge_overalls), 6)
    metric_gaps = []
    for metric in ("acc", "com", "nac", "hal_pass"):
        values_for_metric = [safe_float(row.get(metric)) or 0.0 for row in joined]
        metric_gaps.append(max(values_for_metric) - min(values_for_metric))
    metric_max_gap = round(max(metric_gaps), 6) if metric_gaps else 0.0
    pass_mismatch = len({row.get("pass") for row in joined}) > 1
    status, priority = agreement_status(overall_gap, pass_mismatch)
    ordered = sorted(joined, key=lambda row: safe_float(row.get("overall_score")) or 0.0)
    error_type = next((row.get("error_type") for row in ordered if row.get("error_type") != "normal"), "normal")
    reason = " | ".join(f"{row.get('label') or row.get('config_id')}: {row.get('reason', '')}" for row in joined if row.get("reason"))
    return {
        "acc": acc,
        "com": com,
        "nac": nac,
        "hal": hal_rate,
        "hal_rate": hal_rate,
        "hal_pass": hal_pass,
        "raw_metric_score": round(sum(value for value in values if value is not None), 6),
        "score_denominator": len(ACTIVE_METRICS),
        "overall_score": overall,
        "pass_fail": pass_fail(overall),
        "overall_gap": overall_gap,
        "metric_max_gap": metric_max_gap,
        "pass_mismatch": pass_mismatch,
        "agreement_status": status,
        "review_priority": priority,
        "error_type": error_type,
        "judge_reason": reason,
        "individual_scores": joined,
    }


def add_fields(fieldnames: list[str], new_fields: list[str], after: str | None = None) -> list[str]:
    output = list(fieldnames)
    insert_at = len(output)
    if after and after in output:
        insert_at = output.index(after) + 1
    for field in new_fields:
        if field in output:
            continue
        output.insert(insert_at, field)
        insert_at += 1
    return output


def update_question_rows(
    rows: list[dict[str, str]],
    judge_scores: dict[tuple[str, str], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    out_rows: list[dict[str, Any]] = []
    for row in rows:
        key = (str(row.get("version") or ""), str(row.get("question_id") or ""))
        consensus = consensus_for(key, judge_scores)
        updated = dict(row)
        updated.update(
            {
                "acc": fmt(consensus["acc"]),
                "com": fmt(consensus["com"]),
                "utl": "",
                "utl_applicable": "False",
                "nac": fmt(consensus["nac"]),
                "hal": fmt(consensus["hal"]),
                "hal_rate": fmt(consensus["hal_rate"]),
                "hal_pass": fmt(consensus["hal_pass"]),
                "fct": "",
                "fmt": "",
                "safe": "",
                "safe_status": "excluded_from_metrics_v2",
                "safe_gate": "",
                "safe_pass": "",
                "overall_with_safe": "",
                "applicable_metrics": ",".join(ACTIVE_METRICS),
                "score_denominator": str(consensus["score_denominator"]),
                "raw_metric_score": fmt(consensus["raw_metric_score"]),
                "canonical_metric_count": str(consensus["score_denominator"]),
                "answer_quality_score": fmt(consensus["overall_score"]),
                "rag_quality_score": "",
                "overall_score": fmt(consensus["overall_score"]),
                "pass_fail": consensus["pass_fail"],
                "score_schema": SCHEMA_VERSION,
                "overall_gap": fmt(consensus["overall_gap"]),
                "metric_max_gap": fmt(consensus["metric_max_gap"]),
                "pass_mismatch": str(consensus["pass_mismatch"]).lower(),
                "agreement_status": consensus["agreement_status"],
                "review_priority": consensus["review_priority"],
                "llm_judge_count": str(len(consensus["individual_scores"])),
                "llm_judge_overall_score": fmt(consensus["overall_score"]),
                "llm_judge_hal_pass": fmt(consensus["hal_pass"]),
                "llm_judge_pass_fail": consensus["pass_fail"],
                "llm_judge_status": "ok",
                "llm_judge_individual_scores": json.dumps(consensus["individual_scores"], ensure_ascii=False),
                "llm_judge_score_gap": fmt(consensus["overall_gap"]),
                "llm_judge_score_min": fmt(min(score["overall_score"] for score in consensus["individual_scores"])),
                "llm_judge_score_max": fmt(max(score["overall_score"] for score in consensus["individual_scores"])),
                "llm_judge_pass_mismatch": str(consensus["pass_mismatch"]).lower(),
                "llm_judge_base_average_score": fmt(consensus["overall_score"]),
                "llm_judge_arbiter_score": "",
                "llm_judge_arbiter_override": "False",
                "error_type": consensus["error_type"],
                "judge_reason": consensus["judge_reason"],
                "llm_judge_reason": consensus["judge_reason"],
                "metric_source_acc": "judge_consensus_0_20_div_20",
                "metric_source_com": "judge_consensus_0_20_div_20",
                "metric_source_nac": "judge_consensus_0_20_div_20",
                "metric_source_hal": "judge_consensus_hal_0_20_to_hal_rate_and_hal_pass",
                "metric_source_fct": "excluded",
                "metric_source_fmt": "excluded",
                "metric_source_safe": "excluded",
                "score_scale": "0_1",
            }
        )
        out_rows.append(updated)
    return out_rows


def compact_case_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fields = [
        "question_id",
        "target_config_id",
        "model",
        "qa_category",
        "question_type",
        "qa_topic",
        "expected_behavior",
        "acc",
        "com",
        "utl",
        "utl_applicable",
        "nac",
        "hal",
        "hal_rate",
        "hal_pass",
        "score_denominator",
        "raw_metric_score",
        "overall_score",
        "pass_fail",
        "overall_gap",
        "metric_max_gap",
        "pass_mismatch",
        "agreement_status",
        "review_priority",
        "error_type",
        "judge_reason",
        "score_schema",
    ]
    output: list[dict[str, Any]] = []
    for row in rows:
        output.append(
            {
                **{field: row.get(field, "") for field in fields},
                "target_config_id": row.get("version", ""),
                "utl_applicable": "False",
                "score_schema": SCHEMA_VERSION,
            }
        )
    return output


def aggregate_by_model(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("version") or "")].append(row)
    out: list[dict[str, Any]] = []
    for version, items in grouped.items():
        pass_count = sum(1 for row in items if row.get("pass_fail") == "Pass")
        out.append(
            {
                "target_config_id": version,
                "model": next((row.get("model", "") for row in items if row.get("model")), version),
                "score_rows": len(items),
                "avg_overall_score": fmt(metric_mean(items, "overall_score")),
                "pass_rate": fmt(pass_count / len(items), 4),
                "avg_acc": fmt(metric_mean(items, "acc")),
                "avg_com": fmt(metric_mean(items, "com")),
                "avg_utl": "",
                "utl_applicable_rate": "0",
                "avg_nac": fmt(metric_mean(items, "nac")),
                "avg_hal_rate": fmt(metric_mean(items, "hal_rate")),
                "avg_hal_pass": fmt(metric_mean(items, "hal_pass")),
                "rubric_version": RUBRIC_VERSION,
                "pass_policy": PASS_POLICY,
                "score_schema": SCHEMA_VERSION,
            }
        )
    out.sort(key=lambda row: safe_float(row.get("avg_overall_score")) or 0.0, reverse=True)
    return out


def eval_rows_from_model_rows(model_rows: list[dict[str, Any]], source_run_id: str, eval_date: str) -> list[dict[str, Any]]:
    out = []
    for row in model_rows:
        out.append(
            {
                "run_id": source_run_id,
                "model": row["model"],
                "version": row["target_config_id"],
                "run_type": SNAPSHOT_RUN_TYPE,
                "eval_date": eval_date,
                "eval_started_at": "",
                "total_questions": row["score_rows"],
                "scored_questions": row["score_rows"],
                "review_pending_count": 0,
                "pass_rate": row["pass_rate"],
                "overall_score": row["avg_overall_score"],
                "scored_pass_rate": row["pass_rate"],
                "scored_average": row["avg_overall_score"],
                "acc": row["avg_acc"],
                "com": row["avg_com"],
                "utl": "",
                "utl_applicable_rate": "0",
                "nac": row["avg_nac"],
                "hal": row["avg_hal_rate"],
                "hal_rate": row["avg_hal_rate"],
                "hal_pass": row["avg_hal_pass"],
                "fct": "",
                "fmt": "",
                "fmt_applicable_rate": "0",
                "overall_with_safe": "",
                "safe": "",
                "safe_pass_rate": "",
                "safe_review_rate": "",
                "safe_block_rate": "",
                "answer_quality_score": row["avg_overall_score"],
                "rag_quality_score": "",
                "avg_latency_ms": "",
                "avg_cost_krw": "",
                "score_schema": SCHEMA_VERSION,
            }
        )
    return out


def slice_rows(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dimensions = [
        ("1d", "qa_category"),
        ("1d", "question_type"),
        ("1d", "qa_topic"),
        ("1d", "dataset_role"),
        ("2d", "qa_category|question_type"),
        ("2d", "qa_category|qa_topic"),
    ]
    rows: list[dict[str, Any]] = []
    for level, dimension in dimensions:
        keys = dimension.split("|")
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in case_rows:
            value = " / ".join(str(row.get(key) or "unknown") for key in keys)
            grouped[(str(row.get("version") or ""), value)].append(row)
        for (version, value), items in grouped.items():
            pass_count = sum(1 for row in items if row.get("pass_fail") == "Pass")
            case_count = len({row.get("question_id") for row in items})
            rows.append(
                {
                    "version": version,
                    "model": next((row.get("model", "") for row in items if row.get("model")), version),
                    "slice_level": level,
                    "slice_dimension": dimension,
                    "slice_value": value,
                    "case_count": case_count,
                    "row_count": len(items),
                    "min_reliable_cases": 30,
                    "reliability_status": "reliable" if case_count >= 30 else "low_sample",
                    "pass_rate": fmt(pass_count / len(items), 4),
                    "overall_score": fmt(metric_mean(items, "overall_score")),
                    "acc": fmt(metric_mean(items, "acc")),
                    "com": fmt(metric_mean(items, "com")),
                    "utl": "",
                    "utl_applicable_rate": "0",
                    "nac": fmt(metric_mean(items, "nac")),
                    "hal": fmt(metric_mean(items, "hal_rate")),
                    "hal_rate": fmt(metric_mean(items, "hal_rate")),
                    "hal_pass": fmt(metric_mean(items, "hal_pass")),
                    "fct": "",
                    "fmt": "",
                    "fmt_applicable_rate": "0",
                    "overall_with_safe": "",
                    "safe": "",
                    "safe_pass_rate": "",
                    "safe_review_rate": "",
                    "safe_block_rate": "",
                    "score_schema": SCHEMA_VERSION,
                }
            )
    rows.sort(key=lambda item: (item["version"], item["slice_level"], item["slice_dimension"], item["slice_value"]))
    return rows


def release_gate_rows(model_rows: list[dict[str, Any]], source_run_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in model_rows:
        pass_rate = safe_float(row.get("pass_rate")) or 0.0
        rows.append(
            {
                "run_id": f"{source_run_id}_{row['target_config_id']}",
                "config_id": row["target_config_id"],
                "model": row["model"],
                "release_gate": "not_applicable",
                "total_cases": 0,
                "evaluated_cases": row["score_rows"],
                "gate_eligible_cases": 0,
                "pass_count": "",
                "review_count": 0,
                "block_count": 0,
                "critical_fail_count": 0,
                "pass_rate": "",
                "core_pass_rate": fmt(pass_rate, 4),
                "core_pass_rate_min": "",
                "reason": "utl_na_metrics_v2; no gate-eligible release set in final benchmark",
            }
        )
    return rows


def target_model_rows(model_rows: list[dict[str, Any]], source_run_id: str, eval_date: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for rank, row in enumerate(model_rows, 1):
        output.append(
            {
                "rank_by_overall_score": rank,
                "source_run_id": source_run_id,
                "target_config_id": row["target_config_id"],
                "model": row["model"],
                "run_type": SNAPSHOT_RUN_TYPE,
                "eval_date": eval_date,
                "total_questions": row["score_rows"],
                "scored_questions": row["score_rows"],
                "pass_rate": row["pass_rate"],
                "overall_score": row["avg_overall_score"],
                "acc": row["avg_acc"],
                "com": row["avg_com"],
                "utl": "",
                "utl_applicable_rate": "0",
                "nac": row["avg_nac"],
                "hal": row["avg_hal_rate"],
                "hal_rate": row["avg_hal_rate"],
                "hal_pass": row["avg_hal_pass"],
                "score_schema": SCHEMA_VERSION,
                "score_derivation_policy": SCORE_DERIVATION_POLICY,
            }
        )
    return output


def judge_summary_rows(
    judge_scores: list[dict[str, Any]],
    *,
    by_target: bool,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in judge_scores:
        target = str(row.get("target_config_id") or "")
        label = str(row.get("label") or row.get("config_id") or "judge")
        config_id = str(row.get("config_id") or label)
        model = str(row.get("model") or "")
        key = (label, row.get("provider", ""), config_id, model, target if by_target else "")
        grouped[key].append(row)
    output: list[dict[str, Any]] = []
    for key, items in grouped.items():
        label, provider, config_id, model, target = key
        pass_count = sum(1 for row in items if row.get("pass"))
        out = {
            "label": label,
            "judge_provider": provider,
            "judge_config_id": config_id,
            "judge_model": model,
            "score_rows": len(items),
            "avg_overall_score": fmt(metric_mean(items, "overall_score")),
            "min_overall_score": fmt(min(safe_float(row.get("overall_score")) or 0.0 for row in items)),
            "max_overall_score": fmt(max(safe_float(row.get("overall_score")) or 0.0 for row in items)),
            "pass_rate": fmt(pass_count / len(items), 4),
            "avg_acc": fmt(metric_mean(items, "acc")),
            "avg_com": fmt(metric_mean(items, "com")),
            "avg_utl": "",
            "utl_applicable_rate": "0",
            "avg_nac": fmt(metric_mean(items, "nac")),
            "avg_hal_rate": fmt(metric_mean(items, "hal_rate")),
            "avg_hal_pass": fmt(metric_mean(items, "hal_pass")),
            "score_schema": SCHEMA_VERSION,
        }
        if by_target:
            out["target_config_id"] = target
        output.append(out)
    output.sort(key=lambda row: (row["label"], row.get("target_config_id", "")))
    return output


def gate_rows(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in case_rows:
        overall = safe_float(row.get("overall_score")) or 0.0
        quality_gate = "pass" if overall >= PASS_THRESHOLD else "fail"
        agreement = row.get("agreement_status", "")
        agreement_gate = "review" if agreement == "review_needed" else "monitor" if agreement == "borderline" else "pass"
        final_gate = "review" if agreement_gate == "review" else quality_gate
        rows.append(
            {
                "question_id": row.get("question_id", ""),
                "target_config_id": row.get("version", ""),
                "model": row.get("model", ""),
                "qa_category": row.get("qa_category", ""),
                "question_type": row.get("question_type", ""),
                "qa_topic": row.get("qa_topic", ""),
                "expected_behavior": row.get("expected_behavior", ""),
                "overall_score": row.get("overall_score", ""),
                "quality_gate": quality_gate,
                "quality_gate_reason": "overall_score >= 0.60" if quality_gate == "pass" else "overall_score < 0.60",
                "safe": "",
                "safe_gate": "not_applicable",
                "safe_gate_reason": "SAFE excluded from omnieval_metrics_config.v2",
                "judge_agreement_gate": agreement_gate,
                "agreement_status": agreement,
                "overall_gap": row.get("llm_judge_score_gap", ""),
                "metric_max_gap": row.get("metric_max_gap", ""),
                "review_priority": row.get("review_priority", ""),
                "final_gate": final_gate,
                "final_gate_reason": f"quality_gate={quality_gate}; judge_agreement_gate={agreement_gate}",
                "release_recommendation": final_gate,
                "error_type": row.get("error_type", ""),
                "rubric_version": RUBRIC_VERSION,
                "pass_policy": PASS_POLICY,
            }
        )
    return rows


def write_report(summary: dict[str, Any]) -> None:
    report = f"""# OmniEval Metrics Config v2 Score Snapshot

Generated: {summary["generated_at_local"]}
Source run: {summary["source_run_id"]}

UTL is treated as N/A for every completed row and excluded from all denominators.
Scores are derived from the current UI export in `final_UI/data/question_cases.csv`.
Each row uses `llm_judge_individual_scores` when available; otherwise the row-level scored fields are used.

```
acc = mean(judge_acc)
com = mean(judge_com)
nac = mean(judge_nac)
hal_rate = 1 - mean(judge_hal_pass)
hal_pass = mean(judge_hal_pass)
overall_score = mean(acc, com, nac, hal_pass)
pass_fail = Pass if overall_score >= 0.60 else Fail
```

Rows converted: {summary["row_count"]}
Average overall_score: {summary["avg_overall_score"]}
Pass rate: {summary["pass_rate"]}
UTL applicable rate: 0
"""
    path = REPORTS_DIR / "omnieval_metrics_v2_score_snapshot.md"
    ensure_inside(ROOT, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")


def write_metric_definition() -> None:
    rows = [
        {
            "metric_id": "acc",
            "metric_name": "Accuracy",
            "scale": "0_1",
            "direction": "higher_is_better",
            "active_metric": "true",
            "aggregate_role": "overall_component",
            "source": SCORE_DERIVATION_POLICY,
            "scoring_rule": "Mean of UI-exported ACC judge scores.",
        },
        {
            "metric_id": "com",
            "metric_name": "Completeness",
            "scale": "0_1",
            "direction": "higher_is_better",
            "active_metric": "true",
            "aggregate_role": "overall_component",
            "source": SCORE_DERIVATION_POLICY,
            "scoring_rule": "Mean of UI-exported COM judge scores.",
        },
        {
            "metric_id": "utl",
            "metric_name": "Retrieval Utilization",
            "scale": "N/A",
            "direction": "not_applicable",
            "active_metric": "false",
            "aggregate_role": "excluded",
            "source": "user_policy",
            "scoring_rule": "All completed rows are treated as UTL N/A and excluded from denominators.",
        },
        {
            "metric_id": "nac",
            "metric_name": "Numeric Accuracy",
            "scale": "0_1",
            "direction": "higher_is_better",
            "active_metric": "true",
            "aggregate_role": "overall_component",
            "source": SCORE_DERIVATION_POLICY,
            "scoring_rule": "Mean of UI-exported NAC judge scores.",
        },
        {
            "metric_id": "hal",
            "metric_name": "Hallucination Rate",
            "scale": "0_1",
            "direction": "lower_is_better",
            "active_metric": "true",
            "aggregate_role": "reported_metric",
            "source": SCORE_DERIVATION_POLICY,
            "scoring_rule": "Reported as HAL rate. Lower values mean less hallucination.",
        },
        {
            "metric_id": "hal_pass",
            "metric_name": "Hallucination Pass",
            "scale": "0_1",
            "direction": "higher_is_better",
            "active_metric": "true",
            "aggregate_role": "overall_component",
            "source": SCORE_DERIVATION_POLICY,
            "scoring_rule": "Used for overall_score and gates so all overall components have higher-is-better direction.",
        },
    ]
    fields = [
        "metric_id",
        "metric_name",
        "scale",
        "direction",
        "active_metric",
        "aggregate_role",
        "source",
        "scoring_rule",
    ]
    write_csv(SCORES_DIR / "new_omnieval_rubric_definition.csv", fields, rows)


def write_scoring_method(generated_at: str) -> None:
    report = f"""# OmniEval Metrics Config v2 Scoring Method

Generated: {generated_at}

## Active Source

The score snapshot is generated from the current UI runtime export:

```text
final_UI/data/question_cases.csv
```

Each row carries the model answer and `llm_judge_individual_scores`.

## Core Score

- Active metrics: ACC, COM, NAC, HAL_pass.
- Each metric is stored on a 0-1 scale in the generated CSV/JSON files.
- UTL, SAFE, FCT, and FMT are excluded from the active denominator.
- HAL is reported as `hal_rate`; `hal_pass` is used in `overall_score`.

```text
overall_score = mean(acc, com, nac, hal_pass)
pass_fail = Pass if overall_score >= 0.60 else Fail
```

## Gate Policy

| Gate | Values | Rule |
| --- | --- | --- |
| quality_gate | pass / fail | pass when overall_score >= 0.60 |
| safe_gate | not_applicable | SAFE is excluded from OmniEval v2 |
| judge_agreement_gate | pass / monitor / review | stable -> pass, borderline -> monitor, review_needed -> review |
| final_gate | pass / fail / review | judge review first, then quality fail/pass |

## Outputs

- `scores/new_omnieval_rubric_definition.csv`
- `scores/omnieval_metrics_config_v2.json`
- `scores/omnieval_consensus_case_scores.csv`
- `scores/new_omnieval_rubric_case_scores.csv`
- `scores/new_omnieval_rubric_gate_scores.csv`
- `scores/new_omnieval_rubric_model_scores.csv`
- `scores/new_omnieval_rubric_model_gate_summary.csv`
- `reports/new_omnieval_rubric_score_summary.json`
- `reports/omnieval_metrics_v2_score_snapshot.md`
"""
    path = REPORTS_DIR / "new_omnieval_rubric_scoring_method.md"
    ensure_inside(ROOT, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")


def update_manifest(generated_at: str) -> None:
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    else:
        manifest = {}
    manifest.pop("canonical_saved_run", None)
    manifest.pop("clova_saved_run", None)
    manifest["snapshot_id"] = SNAPSHOT_RUN_ID
    manifest["source_data"] = {
        "description": "Current UI runtime export used to build score and report snapshots.",
        "relative_path": "final_UI/data",
        "score_derivation_policy": SCORE_DERIVATION_POLICY,
    }
    files = manifest.setdefault("files", {})
    scores = files.setdefault("scores", [])
    score_config = "scores/omnieval_metrics_config_v2.json"
    if score_config not in scores:
        scores.append(score_config)
    reports = files.setdefault("reports", [])
    report_path = "reports/omnieval_metrics_v2_score_snapshot.md"
    reports[:] = [report for report in reports if report != "reports/omnieval_metrics_v2_score_migration.md"]
    if report_path not in reports:
        reports.append(report_path)
    manifest["score_schema"] = {
        "version": SCHEMA_VERSION,
        "rubric_version": RUBRIC_VERSION,
        "metrics": ["acc", "com", "utl", "nac", "hal", "hal_pass"],
        "active_overall_metrics": list(ACTIVE_METRICS),
        "score_scale": "0_1",
        "overall_score_policy": "mean(acc, com, nac, hal_pass); UTL excluded",
        "pass_policy": PASS_POLICY,
        "utl_policy": "UTL is N/A for all completed rows and excluded from all denominators.",
        "hal_policy": "HAL is reported as hal_rate where lower is better; HAL_pass = 1 - HAL_rate is used in overall_score.",
        "safe_policy": "SAFE is excluded from omnieval_metrics_config.v2 final scores.",
        "fct_policy": "FCT is excluded from omnieval_metrics_config.v2 final scores.",
        "score_config_path": score_config,
        "full_consensus_case_scores_path": "scores/omnieval_consensus_case_scores.csv",
        "full_consensus_summary_path": "scores/omnieval_consensus_summary.json",
        "target_model_scores_path": "scores/target_model_scores.csv",
        "new_rubric_definition_path": "scores/new_omnieval_rubric_definition.csv",
        "new_rubric_case_scores_path": "scores/new_omnieval_rubric_case_scores.csv",
        "new_rubric_gate_scores_path": "scores/new_omnieval_rubric_gate_scores.csv",
        "new_rubric_model_scores_path": "scores/new_omnieval_rubric_model_scores.csv",
        "new_rubric_model_gate_summary_path": "scores/new_omnieval_rubric_model_gate_summary.csv",
        "new_rubric_summary_path": "reports/new_omnieval_rubric_score_summary.json",
        "score_snapshot_report_path": report_path,
    }
    manifest["updated_at_local"] = generated_at
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_scores_zip() -> None:
    zip_path = EVAL_SNAPSHOT / "scores.zip"
    ensure_inside(ROOT, zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(SCORES_DIR.glob("*")):
            if path.is_file():
                archive.write(path, arcname=f"scores/{path.name}")


def main() -> None:
    generated_at = datetime.now(KST).replace(microsecond=0).isoformat()
    question_fields, question_rows = read_csv(UI_RUNTIME_DATA / "question_cases.csv")
    _source_eval_fields, source_eval_rows = read_csv(UI_RUNTIME_DATA / "eval_runs.csv")
    source_run_value = first_present(source_eval_rows[0], "run_id") if source_eval_rows else None
    source_run_id = str(source_run_value or SNAPSHOT_RUN_ID)
    if source_run_id in CURRENT_UI_DATA_RUN_IDS:
        source_run_id = SNAPSHOT_RUN_ID
    eval_date_value = first_present(source_eval_rows[0], "eval_date") if source_eval_rows else None
    eval_date = str(eval_date_value or "")
    if source_run_id == SNAPSHOT_RUN_ID:
        eval_date = generated_at[:10]
    elif not eval_date:
        eval_date = generated_at[:10]
    judge_scores, judge_score_rows = load_judge_scores_from_question_rows(question_rows)

    paths_to_archive = [
        UI_RUNTIME_DATA / "question_cases.csv",
        UI_RUNTIME_DATA / "eval_runs.csv",
        UI_RUNTIME_DATA / "qa_slice_scores.csv",
        UI_RUNTIME_DATA / "run_release_gates.csv",
        SCORES_DIR / "omnieval_consensus_case_scores.csv",
        SCORES_DIR / "omnieval_consensus_summary.json",
        SCORE_CONFIG_PATH,
        SCORES_DIR / "release_gates.csv",
        SCORES_DIR / "target_model_scores.csv",
        SCORES_DIR / "judge_scores_overall.csv",
        SCORES_DIR / "judge_scores_by_target_model.csv",
        SCORES_DIR / "new_omnieval_rubric_case_scores.csv",
        SCORES_DIR / "new_omnieval_rubric_definition.csv",
        SCORES_DIR / "new_omnieval_rubric_gate_scores.csv",
        SCORES_DIR / "new_omnieval_rubric_model_scores.csv",
        SCORES_DIR / "new_omnieval_rubric_model_gate_summary.csv",
        REPORTS_DIR / "new_omnieval_rubric_score_report.md",
        REPORTS_DIR / "new_omnieval_rubric_score_summary.json",
        REPORTS_DIR / "new_omnieval_rubric_scoring_method.md",
        REPORTS_DIR / "omnieval_metrics_v2_score_snapshot.md",
        REPORTS_DIR / "omnieval_metrics_v2_score_migration.md",
        EVAL_SNAPSHOT / "scores.zip",
        MANIFEST_PATH,
    ]
    archive_root = archive_files(paths_to_archive)
    for obsolete_report in [
        REPORTS_DIR / "omnieval_metrics_v2_score_migration.md",
        REPORTS_DIR / "new_omnieval_rubric_score_report.md",
    ]:
        if obsolete_report.exists():
            ensure_inside(ROOT, obsolete_report)
            obsolete_report.unlink()

    updated_question_rows = update_question_rows(question_rows, judge_scores)
    model_rows = aggregate_by_model(updated_question_rows)
    eval_rows = eval_rows_from_model_rows(model_rows, source_run_id, eval_date)
    slices = slice_rows(updated_question_rows)
    compact_rows = compact_case_rows(updated_question_rows)
    gates = gate_rows(updated_question_rows)
    target_rows = target_model_rows(model_rows, source_run_id, eval_date)
    judge_overall = judge_summary_rows(judge_score_rows, by_target=False)
    judge_by_target = judge_summary_rows(judge_score_rows, by_target=True)

    question_fields = add_fields(question_fields, ["utl", "hal", "hal_rate", "hal_pass"], after="nac")
    question_fields = add_fields(question_fields, ["score_scale", "metric_source_hal"], after="score_schema")
    question_fields = add_fields(question_fields, ["llm_judge_hal_pass"], after="llm_judge_overall_score")
    write_csv(UI_RUNTIME_DATA / "question_cases.csv", question_fields, updated_question_rows)

    eval_fields = [
        "run_id", "model", "version", "run_type", "eval_date", "eval_started_at", "total_questions",
        "scored_questions", "review_pending_count", "pass_rate", "overall_score", "scored_pass_rate",
        "scored_average", "acc", "com", "utl", "utl_applicable_rate", "nac", "hal", "hal_rate",
        "hal_pass", "fct", "fmt", "fmt_applicable_rate", "overall_with_safe", "safe", "safe_pass_rate",
        "safe_review_rate", "safe_block_rate", "answer_quality_score", "rag_quality_score",
        "avg_latency_ms", "avg_cost_krw", "score_schema",
    ]
    write_csv(UI_RUNTIME_DATA / "eval_runs.csv", eval_fields, eval_rows)

    slice_fields = [
        "version", "model", "slice_level", "slice_dimension", "slice_value", "case_count", "row_count",
        "min_reliable_cases", "reliability_status", "pass_rate", "overall_score", "acc", "com", "utl",
        "utl_applicable_rate", "nac", "hal", "hal_rate", "hal_pass", "fct", "fmt",
        "fmt_applicable_rate", "overall_with_safe", "safe", "safe_pass_rate", "safe_review_rate",
        "safe_block_rate", "score_schema",
    ]
    write_csv(UI_RUNTIME_DATA / "qa_slice_scores.csv", slice_fields, slices)

    release_fields = [
        "run_id", "config_id", "model", "release_gate", "total_cases", "evaluated_cases",
        "gate_eligible_cases", "pass_count", "review_count", "block_count", "critical_fail_count",
        "pass_rate", "core_pass_rate", "core_pass_rate_min", "reason",
    ]
    release_rows = release_gate_rows(model_rows, source_run_id)
    write_csv(UI_RUNTIME_DATA / "run_release_gates.csv", release_fields, release_rows)
    write_csv(SCORES_DIR / "release_gates.csv", release_fields, release_rows)

    compact_fields = [
        "question_id", "target_config_id", "model", "qa_category", "question_type", "qa_topic",
        "expected_behavior", "acc", "com", "utl", "utl_applicable", "nac", "hal", "hal_rate",
        "hal_pass", "score_denominator", "raw_metric_score", "overall_score", "pass_fail",
        "overall_gap", "metric_max_gap", "pass_mismatch", "agreement_status", "review_priority",
        "error_type", "judge_reason", "score_schema",
    ]
    write_csv(SCORES_DIR / "omnieval_consensus_case_scores.csv", compact_fields, compact_rows)

    new_case_fields = compact_fields + ["rubric_version", "pass_policy"]
    new_case_rows = [{**row, "rubric_version": RUBRIC_VERSION, "pass_policy": PASS_POLICY} for row in compact_rows]
    write_csv(SCORES_DIR / "new_omnieval_rubric_case_scores.csv", new_case_fields, new_case_rows)

    model_fields = [
        "target_config_id", "model", "score_rows", "avg_overall_score", "pass_rate", "avg_acc",
        "avg_com", "avg_utl", "utl_applicable_rate", "avg_nac", "avg_hal_rate", "avg_hal_pass",
        "rubric_version", "pass_policy", "score_schema",
    ]
    write_csv(SCORES_DIR / "new_omnieval_rubric_model_scores.csv", model_fields, model_rows)

    target_fields = [
        "rank_by_overall_score", "source_run_id", "target_config_id", "model", "run_type", "eval_date",
        "total_questions", "scored_questions", "pass_rate", "overall_score", "acc", "com", "utl",
        "utl_applicable_rate", "nac", "hal", "hal_rate", "hal_pass", "score_schema", "score_derivation_policy",
    ]
    write_csv(SCORES_DIR / "target_model_scores.csv", target_fields, target_rows)

    gate_fields = [
        "question_id", "target_config_id", "model", "qa_category", "question_type", "qa_topic",
        "expected_behavior", "overall_score", "quality_gate", "quality_gate_reason", "safe",
        "safe_gate", "safe_gate_reason", "judge_agreement_gate", "agreement_status", "overall_gap",
        "metric_max_gap", "review_priority", "final_gate", "final_gate_reason", "release_recommendation",
        "error_type", "rubric_version", "pass_policy",
    ]
    write_csv(SCORES_DIR / "new_omnieval_rubric_gate_scores.csv", gate_fields, gates)

    gate_summary_fields = [
        "target_config_id", "model", "score_rows", "quality_pass_count", "quality_fail_count",
        "judge_agreement_pass_count", "judge_agreement_monitor_count", "judge_agreement_review_count",
        "final_pass_count", "final_fail_count", "final_review_count", "rubric_version", "pass_policy",
    ]
    gates_by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in gates:
        gates_by_model[str(row["target_config_id"])].append(row)
    gate_summary = []
    for model_row in model_rows:
        rows = gates_by_model[model_row["target_config_id"]]
        counts = Counter(row["final_gate"] for row in rows)
        quality = Counter(row["quality_gate"] for row in rows)
        agreement = Counter(row["judge_agreement_gate"] for row in rows)
        gate_summary.append(
            {
                "target_config_id": model_row["target_config_id"],
                "model": model_row["model"],
                "score_rows": len(rows),
                "quality_pass_count": quality.get("pass", 0),
                "quality_fail_count": quality.get("fail", 0),
                "judge_agreement_pass_count": agreement.get("pass", 0),
                "judge_agreement_monitor_count": agreement.get("monitor", 0),
                "judge_agreement_review_count": agreement.get("review", 0),
                "final_pass_count": counts.get("pass", 0),
                "final_fail_count": counts.get("fail", 0),
                "final_review_count": counts.get("review", 0),
                "rubric_version": RUBRIC_VERSION,
                "pass_policy": PASS_POLICY,
            }
        )
    write_csv(SCORES_DIR / "new_omnieval_rubric_model_gate_summary.csv", gate_summary_fields, gate_summary)

    judge_fields = [
        "label", "judge_provider", "judge_config_id", "judge_model", "score_rows", "avg_overall_score",
        "min_overall_score", "max_overall_score", "pass_rate", "avg_acc", "avg_com", "avg_utl",
        "utl_applicable_rate", "avg_nac", "avg_hal_rate", "avg_hal_pass", "score_schema",
    ]
    write_csv(SCORES_DIR / "judge_scores_overall.csv", judge_fields, judge_overall)
    write_csv(SCORES_DIR / "judge_scores_by_target_model.csv", add_fields(judge_fields, ["target_config_id"], after="judge_model"), judge_by_target)

    scores = [safe_float(row.get("overall_score")) or 0.0 for row in updated_question_rows]
    pass_count = sum(1 for row in updated_question_rows if row.get("pass_fail") == "Pass")
    summary = {
        "schema": "omnieval_metrics_v2_score_summary",
        "generated_at_local": generated_at,
        "source_run_id": source_run_id,
        "source_data_path": "final_UI/data/question_cases.csv",
        "score_derivation_policy": SCORE_DERIVATION_POLICY,
        "rubric_version": RUBRIC_VERSION,
        "score_schema": SCHEMA_VERSION,
        "pass_policy": PASS_POLICY,
        "row_count": len(updated_question_rows),
        "judge_score_rows": len(judge_score_rows),
        "avg_overall_score": fmt(sum(scores) / len(scores)),
        "min_overall_score": fmt(min(scores)),
        "max_overall_score": fmt(max(scores)),
        "pass_count": pass_count,
        "pass_rate": fmt(pass_count / len(updated_question_rows), 4),
        "utl_policy": "all rows set to N/A and excluded from denominator",
        "active_metrics": list(ACTIVE_METRICS),
        "hal_policy": "hal is reported as hal_rate (lower is better); hal_pass is used for overall_score and gates",
        "archive_root": str(archive_root.relative_to(ROOT)).replace("\\", "/"),
        "outputs": {
            "final_ui_question_cases": "final_UI/data/question_cases.csv",
            "final_ui_eval_runs": "final_UI/data/eval_runs.csv",
            "final_ui_qa_slice_scores": "final_UI/data/qa_slice_scores.csv",
            "case_scores": "data/eval_snapshot_20260624_094927/scores/omnieval_consensus_case_scores.csv",
            "score_config": "data/eval_snapshot_20260624_094927/scores/omnieval_metrics_config_v2.json",
            "target_model_scores": "data/eval_snapshot_20260624_094927/scores/target_model_scores.csv",
            "model_scores": "data/eval_snapshot_20260624_094927/scores/new_omnieval_rubric_model_scores.csv",
        },
    }
    write_json(SCORES_DIR / "omnieval_consensus_summary.json", summary)
    write_json(REPORTS_DIR / "new_omnieval_rubric_score_summary.json", summary)
    write_report(summary)
    write_metric_definition()
    write_scoring_method(generated_at)
    update_manifest(generated_at)

    rubric = {
        "schema": "omnieval_metrics_config_v2",
        "generated_at_local": generated_at,
        "metrics": {
            "acc": {"scale": "0_1", "direction": "higher_is_better"},
            "com": {"scale": "0_1", "direction": "higher_is_better"},
            "utl": {"scale": "N/A", "policy": "all rows excluded by request"},
            "nac": {"scale": "0_1", "direction": "higher_is_better"},
            "hal": {"scale": "0_1", "direction": "lower_is_better", "meaning": "hallucination rate"},
            "hal_pass": {"scale": "0_1", "direction": "higher_is_better", "meaning": "1 - hal_rate"},
        },
        "overall_score": "mean(acc, com, nac, hal_pass); UTL excluded",
        "pass_policy": PASS_POLICY,
        "score_derivation_policy": SCORE_DERIVATION_POLICY,
    }
    write_json(SCORE_CONFIG_PATH, rubric)
    write_scores_zip()

    print(
        json.dumps(
            {
                "row_count": len(updated_question_rows),
                "avg_overall_score": summary["avg_overall_score"],
                "pass_rate": summary["pass_rate"],
                "archive_root": summary["archive_root"],
                "score_schema": SCHEMA_VERSION,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

