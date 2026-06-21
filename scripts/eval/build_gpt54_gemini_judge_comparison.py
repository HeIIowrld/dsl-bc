from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
METRIC_KEYS = ("acc", "com", "utl", "nac", "hal")


def resolve_path(value: str | Path) -> Path:
    path = Path(str(value or "").strip())
    return path if path.is_absolute() else ROOT / path


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "pass"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_json_field(value: Any, fallback: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback
    return value if value is not None else fallback


def score_from_individual(score: dict[str, Any]) -> dict[str, Any]:
    overall = score.get("overall_score")
    if overall in (None, ""):
        denominator = safe_float(score.get("score_denominator"), 80.0) or 80.0
        overall = round(sum(safe_float(score.get(key)) for key in METRIC_KEYS) / denominator * 100, 2)
    return {
        "role": "judge",
        "config_id": score.get("config_id", ""),
        "provider": score.get("provider", ""),
        "model": score.get("model", ""),
        "prompt_version": score.get("prompt_version", ""),
        "prompt_hash": score.get("prompt_hash", ""),
        "system_prompt_preset": score.get("system_prompt_preset", ""),
        **{key: safe_float(score.get(key)) for key in METRIC_KEYS},
        "utl_applicable": score.get("utl_applicable", ""),
        "score_denominator": score.get("score_denominator", ""),
        "raw_metric_score": score.get("raw_metric_score", ""),
        "overall_score": safe_float(overall),
        "pass": safe_bool(score.get("pass")),
        "critical_fail": safe_bool(score.get("critical_fail")),
        "error_type": score.get("error_type", ""),
        "reason": score.get("reason", ""),
    }


def score_from_gemini_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": "judge",
        "config_id": row.get("llm_judge_config_id", "gemini_2_5_flash_judge"),
        "provider": row.get("llm_judge_provider", "gemini"),
        "model": row.get("llm_judge_model", ""),
        "prompt_version": row.get("llm_judge_prompt_version", ""),
        "prompt_hash": row.get("llm_judge_prompt_hash", ""),
        "system_prompt_preset": row.get("llm_judge_prompt_preset", ""),
        **{key: safe_float(row.get(f"llm_judge_{key}")) for key in METRIC_KEYS},
        "utl_applicable": row.get("utl_applicable", ""),
        "score_denominator": row.get("llm_judge_score_denominator", row.get("score_denominator", "")),
        "raw_metric_score": row.get("llm_judge_raw_metric_score", ""),
        "overall_score": safe_float(row.get("llm_judge_overall_score", row.get("overall_score"))),
        "pass": safe_bool(row.get("llm_judge_pass", row.get("pass"))),
        "critical_fail": safe_bool(row.get("llm_judge_critical_fail", row.get("critical_fail"))),
        "error_type": row.get("llm_judge_error_type", row.get("error_type", "")),
        "reason": row.get("llm_judge_reason", ""),
    }


def load_gpt54_scores(question_cases_csv: Path, judge_config_id: str) -> dict[tuple[str, str], dict[str, Any]]:
    scores: dict[tuple[str, str], dict[str, Any]] = {}
    with question_cases_csv.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            config_id = str(row.get("version") or row.get("config_id") or "").strip()
            case_id = str(row.get("question_id") or row.get("case_id") or "").strip()
            if not config_id or not case_id:
                continue
            individual = parse_json_field(row.get("llm_judge_individual_scores"), [])
            if not isinstance(individual, list):
                continue
            for item in individual:
                if isinstance(item, dict) and str(item.get("config_id") or "") == judge_config_id:
                    scores[(config_id, case_id)] = score_from_individual(item)
                    break
    return scores


def load_gemini_scores(run_dir: Path) -> dict[tuple[str, str], dict[str, Any]]:
    scores: dict[tuple[str, str], dict[str, Any]] = {}
    for row in read_jsonl(run_dir / "judge_scores.jsonl"):
        if str(row.get("llm_judge_status") or "").lower() != "ok":
            continue
        config_id = str(row.get("config_id") or "").strip()
        case_id = str(row.get("case_id") or "").strip()
        if config_id and case_id:
            scores[(config_id, case_id)] = score_from_gemini_row(row)
    return scores


def conflict_reason(gpt54: dict[str, Any], gemini: dict[str, Any], threshold: float) -> tuple[bool, str]:
    gpt_score = safe_float(gpt54.get("overall_score"))
    gemini_score = safe_float(gemini.get("overall_score"))
    gap = abs(gemini_score - gpt_score)
    reasons: list[str] = []
    if gap >= threshold:
        reasons.append(f"judge score gap {gap:.2f}")
    if bool(gpt54.get("pass")) != bool(gemini.get("pass")):
        reasons.append("judge pass/fail disagreement")
    if str(gpt54.get("error_type") or "") != str(gemini.get("error_type") or ""):
        reasons.append(
            "judge error-type disagreement: "
            + ", ".join(sorted({str(gpt54.get("error_type") or ""), str(gemini.get("error_type") or "")}))
        )
    return bool(reasons), "; ".join(reasons)


def build_comparison(args: argparse.Namespace) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    gpt54_scores = load_gpt54_scores(resolve_path(args.question_cases_csv), args.gpt54_config_id)
    gemini_scores = load_gemini_scores(resolve_path(args.gemini_run_dir))
    matched_keys = sorted(set(gpt54_scores) & set(gemini_scores))
    comparison_rows: list[dict[str, Any]] = []
    arbiter_keys: list[dict[str, Any]] = []
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for config_id, case_id in matched_keys:
        gpt54 = gpt54_scores[(config_id, case_id)]
        gemini = gemini_scores[(config_id, case_id)]
        gpt_score = safe_float(gpt54.get("overall_score"))
        gemini_score = safe_float(gemini.get("overall_score"))
        delta = round(gemini_score - gpt_score, 2)
        gap = abs(delta)
        pass_mismatch = bool(gpt54.get("pass")) != bool(gemini.get("pass"))
        is_conflict, reason = conflict_reason(gpt54, gemini, args.score_gap_threshold)
        row = {
            "config_id": config_id,
            "case_id": case_id,
            "gpt54_score": gpt_score,
            "gemini_score": gemini_score,
            "delta_gemini_minus_gpt54": delta,
            "abs_score_gap": round(gap, 2),
            "gpt54_pass": bool(gpt54.get("pass")),
            "gemini_pass": bool(gemini.get("pass")),
            "pass_mismatch": pass_mismatch,
            "gpt54_error_type": gpt54.get("error_type", ""),
            "gemini_error_type": gemini.get("error_type", ""),
            "conflict_for_arbiter": is_conflict,
            "conflict_reason": reason,
            "gpt54_reason": gpt54.get("reason", ""),
            "gemini_reason": gemini.get("reason", ""),
        }
        comparison_rows.append(row)
        by_model[config_id].append(row)
        if is_conflict or args.arbitrate_all:
            base_judges = [
                {**gpt54, "role": "judge", "label": "GPT 5.4 mini Judge"},
                {**gemini, "role": "judge", "label": "Gemini 2.5 Flash V1 Judge"},
            ]
            arbiter_keys.append(
                {
                    "config_id": config_id,
                    "case_id": case_id,
                    "reason": reason or "requested full judge comparison",
                    "arbiter_context": {
                        "comparison_target": "openai_gpt54_mini_judge_vs_gemini_2_5_flash_judge",
                        "conflict_reason": reason or "requested full judge comparison",
                        "score_gap": round(gap, 2),
                        "score_min": round(min(gpt_score, gemini_score), 2),
                        "score_max": round(max(gpt_score, gemini_score), 2),
                        "pass_mismatch": pass_mismatch,
                        "base_judges": base_judges,
                    },
                }
            )

    model_summary = []
    for config_id, rows in sorted(by_model.items()):
        model_summary.append(
            {
                "config_id": config_id,
                "rows": len(rows),
                "gpt54_avg": round(mean(safe_float(row["gpt54_score"]) for row in rows), 2),
                "gemini_avg": round(mean(safe_float(row["gemini_score"]) for row in rows), 2),
                "avg_delta_gemini_minus_gpt54": round(
                    mean(safe_float(row["delta_gemini_minus_gpt54"]) for row in rows),
                    2,
                ),
                "pass_mismatch_rows": sum(1 for row in rows if row["pass_mismatch"]),
                "error_type_mismatch_rows": sum(
                    1 for row in rows if row["gpt54_error_type"] != row["gemini_error_type"]
                ),
                "arbiter_conflict_rows": sum(1 for row in rows if row["conflict_for_arbiter"]),
            }
        )

    summary = {
        "gpt54_source_rows": len(gpt54_scores),
        "gemini_source_rows": len(gemini_scores),
        "matched_rows": len(comparison_rows),
        "missing_gpt54_rows": len(set(gemini_scores) - set(gpt54_scores)),
        "missing_gemini_rows": len(set(gpt54_scores) - set(gemini_scores)),
        "score_gap_threshold": args.score_gap_threshold,
        "arbiter_key_rows": len(arbiter_keys),
        "pass_mismatch_rows": sum(1 for row in comparison_rows if row["pass_mismatch"]),
        "error_type_mismatch_rows": sum(
            1 for row in comparison_rows if row["gpt54_error_type"] != row["gemini_error_type"]
        ),
        "gap_threshold_rows": sum(1 for row in comparison_rows if safe_float(row["abs_score_gap"]) >= args.score_gap_threshold),
        "gpt54_avg": round(mean(safe_float(row["gpt54_score"]) for row in comparison_rows), 2) if comparison_rows else 0,
        "gemini_avg": round(mean(safe_float(row["gemini_score"]) for row in comparison_rows), 2) if comparison_rows else 0,
        "avg_delta_gemini_minus_gpt54": round(
            mean(safe_float(row["delta_gemini_minus_gpt54"]) for row in comparison_rows),
            2,
        )
        if comparison_rows
        else 0,
        "gpt54_pass_rows": sum(1 for row in comparison_rows if row["gpt54_pass"]),
        "gemini_pass_rows": sum(1 for row in comparison_rows if row["gemini_pass"]),
        "gpt54_error_types": dict(Counter(str(row["gpt54_error_type"] or "normal") for row in comparison_rows)),
        "gemini_error_types": dict(Counter(str(row["gemini_error_type"] or "normal") for row in comparison_rows)),
        "by_model": model_summary,
    }
    return comparison_rows, arbiter_keys, summary


def write_markdown_report(path: Path, summary: dict[str, Any], arbiter_summary: dict[str, Any] | None = None) -> None:
    lines = [
        "# GPT 5.4 mini vs Gemini 2.5 Flash V1 Judge Comparison",
        "",
        "## Scope",
        "",
        "- Base judge A: openai_gpt54_mini_judge from final_UI/data/question_cases.csv individual scores.",
        "- Base judge B: gemini_2_5_flash_judge from the fresh V1 saved-answer rejudge run.",
        "- Arbiter input rows are selected by pass/fail disagreement, error-type disagreement, or score gap threshold.",
        "",
        "## Summary",
        "",
        f"- Matched rows: {summary.get('matched_rows', 0):,}",
        f"- Gemini source rows: {summary.get('gemini_source_rows', 0):,}",
        f"- GPT 5.4 mini source rows: {summary.get('gpt54_source_rows', 0):,}",
        f"- Arbiter key rows: {summary.get('arbiter_key_rows', 0):,}",
        f"- Pass/fail mismatches: {summary.get('pass_mismatch_rows', 0):,}",
        f"- Error-type mismatches: {summary.get('error_type_mismatch_rows', 0):,}",
        f"- Rows over score-gap threshold ({summary.get('score_gap_threshold')}): {summary.get('gap_threshold_rows', 0):,}",
        f"- GPT 5.4 mini average score: {summary.get('gpt54_avg')}",
        f"- Gemini average score: {summary.get('gemini_avg')}",
        f"- Average delta, Gemini - GPT 5.4 mini: {summary.get('avg_delta_gemini_minus_gpt54')}",
        f"- GPT 5.4 mini pass rows: {summary.get('gpt54_pass_rows', 0):,}",
        f"- Gemini pass rows: {summary.get('gemini_pass_rows', 0):,}",
        "",
    ]
    if arbiter_summary:
        lines.extend(
            [
                "## Arbiter",
                "",
                f"- Arbiter rows: {arbiter_summary.get('rows', 0):,}",
                f"- Status counts: {json.dumps(arbiter_summary.get('status_counts', {}), ensure_ascii=False, sort_keys=True)}",
                f"- Arbiter average score: {arbiter_summary.get('arbiter_avg_score', 0)}",
                f"- Arbiter pass rows: {arbiter_summary.get('arbiter_pass_rows', 0):,}",
                "",
            ]
        )
    lines.extend(
        [
            "## By Model",
            "",
            "| Model config | Rows | GPT54 avg | Gemini avg | Delta | Pass mismatch | Error-type mismatch | Arbiter keys |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary.get("by_model", []):
        lines.append(
            "| {config_id} | {rows:,} | {gpt54_avg} | {gemini_avg} | {avg_delta_gemini_minus_gpt54} | "
            "{pass_mismatch_rows:,} | {error_type_mismatch_rows:,} | {arbiter_conflict_rows:,} |".format(**row)
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def arbiter_summary(run_dir: Path) -> dict[str, Any]:
    rows = read_jsonl(run_dir / "judge_scores.jsonl")
    ok_rows = [row for row in rows if str(row.get("llm_judge_status") or "").lower() == "ok"]
    return {
        "rows": len(rows),
        "status_counts": dict(Counter(str(row.get("llm_judge_status") or "") for row in rows)),
        "arbiter_avg_score": round(mean(safe_float(row.get("llm_judge_overall_score")) for row in ok_rows), 2)
        if ok_rows
        else 0,
        "arbiter_pass_rows": sum(1 for row in ok_rows if safe_bool(row.get("llm_judge_pass"))),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build GPT 5.4 mini vs Gemini 2.5 Flash V1 judge comparison files.")
    parser.add_argument("--question-cases-csv", default="final_UI/data/question_cases.csv")
    parser.add_argument("--gemini-run-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--gpt54-config-id", default="openai_gpt54_mini_judge")
    parser.add_argument("--score-gap-threshold", type=float, default=30.0)
    parser.add_argument("--arbitrate-all", action="store_true")
    parser.add_argument("--arbiter-run-dir", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = resolve_path(args.out_dir)
    comparison_rows, arbiter_keys, summary = build_comparison(args)
    write_jsonl(out_dir / "gpt54_gemini_comparison.jsonl", comparison_rows)
    write_csv(out_dir / "gpt54_gemini_comparison.csv", comparison_rows)
    write_jsonl(out_dir / "gpt54_gemini_arbiter_keys.jsonl", arbiter_keys)
    (out_dir / "gpt54_gemini_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    arbiter = arbiter_summary(resolve_path(args.arbiter_run_dir)) if args.arbiter_run_dir else None
    write_markdown_report(out_dir / "gpt54_gemini_report.md", summary, arbiter)
    print(json.dumps({"out_dir": str(out_dir), **summary}, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
