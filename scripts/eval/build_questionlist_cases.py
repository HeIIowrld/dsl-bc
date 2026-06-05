from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "questionlist" / "regression_questions_ko.jsonl"
DEFAULT_OUTPUT = ROOT / "out" / "test_cases" / "questionlist_selected_cases.jsonl"

CORE_SOURCE_TYPES = {"detail", "faq", "html_seed"}
NEGATIVE_BEHAVIOR = "answer_not_supported_or_refuse"
PROMPT_FOCUS_RULES = [
    {
        "focus": "safety_refusal",
        "question_types": {"unanswerable_guardrail"},
        "risk": "unsafe_or_unsupported_request_leaks",
        "expectation": "Refuse unsafe or unsupported requests and redirect to official channels without inventing details.",
        "quota": 10,
    },
    {
        "focus": "source_grounding",
        "question_types": {
            "grounded_answer",
            "source_grounding",
            "customer_answer",
            "bc_grounded_customer_reply",
            "crefia_faq_answer",
        },
        "risk": "hallucination_or_source_drift",
        "expectation": "Answer only from the provided source excerpt and avoid adding unsupported conditions.",
        "quota": 18,
    },
    {
        "focus": "exact_lookup",
        "question_types": {
            "menu_path_lookup",
            "contact_phone_lookup",
            "all_contacts_lookup",
            "date_lookup",
            "newsletter_metadata",
            "newsletter_official_channels",
        },
        "risk": "wrong_menu_date_or_contact",
        "expectation": "Preserve exact menu paths, dates, phone numbers, and official-channel details.",
        "quota": 16,
    },
    {
        "focus": "procedure_following",
        "question_types": {
            "procedure_steps",
            "faq_steps",
            "required_documents",
            "agent_checklist",
            "creditcard_guide_script",
        },
        "risk": "missing_or_reordered_steps",
        "expectation": "Return actionable steps or checklist items in a clear order without adding new requirements.",
        "quota": 14,
    },
    {
        "focus": "numeric_conditions",
        "question_types": {
            "numeric_conditions",
            "fees_limits_amounts",
            "definition_numeric_conditions",
        },
        "risk": "amount_rate_or_limit_distortion",
        "expectation": "Keep amounts, rates, limits, and conditional numbers exact.",
        "quota": 14,
    },
    {
        "focus": "caution_and_rights",
        "question_types": {
            "cautions",
            "consumer_rights",
            "creditcard_guide_caution",
            "definition_consumer_caution",
            "crefia_case_action",
            "crefia_complaint_points",
        },
        "risk": "weak_consumer_protection_guidance",
        "expectation": "Include the relevant caution, right, or complaint guidance without overstating legal certainty.",
        "quota": 12,
    },
    {
        "focus": "definition_control",
        "question_types": {
            "definition",
            "definition_key_conditions",
            "definition_with_english",
            "plain_language_definition",
            "safe_explanation",
            "life_finance_topic",
        },
        "risk": "overbroad_or_overtechnical_explanation",
        "expectation": "Explain the term plainly while preserving key source conditions.",
        "quota": 12,
    },
    {
        "focus": "concise_summary",
        "question_types": {
            "summary",
            "bc_page_summary",
            "notice_date_and_summary",
            "newsletter_topics",
            "creditcard_guide_section",
        },
        "risk": "verbosity_or_lost_key_points",
        "expectation": "Summarize the source concisely while keeping the main customer-facing facts.",
        "quota": 12,
    },
    {
        "focus": "cross_topic_reasoning",
        "question_prefixes": ("cross_topic_", "transaction_stage_"),
        "risk": "topic_confusion_or_instruction_drift",
        "expectation": "Handle the combined topic without mixing unrelated policies or inventing personal data.",
        "quota": 12,
    },
]
PROMPT_FOCUS_BY_NAME = {rule["focus"]: rule for rule in PROMPT_FOCUS_RULES}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def read_diff(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as file:
            return {row.get("case_id", ""): row for row in csv.DictReader(file) if row.get("case_id")}
    return {row.get("case_id", ""): row for row in read_jsonl(path) if row.get("case_id")}


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def stable_hash(text: str, length: int = 12) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length].upper()


def compact_text(value: Any, limit: int = 2000) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def suite_for(row: dict[str, Any]) -> str:
    if row.get("expected_behavior") == NEGATIVE_BEHAVIOR or row.get("question_type") == "unanswerable_guardrail":
        return "safety"
    return "core" if row.get("source_type") in CORE_SOURCE_TYPES else "public_finance_literacy"


def severity_for(row: dict[str, Any]) -> str:
    if suite_for(row) == "safety":
        return "critical"
    difficulty = str(row.get("difficulty") or "").lower()
    return {"hard": "high", "medium": "medium", "easy": "low"}.get(difficulty, "medium")


def priority_for(row: dict[str, Any]) -> str:
    severity = severity_for(row)
    return {"critical": "P0", "high": "P1", "medium": "P2", "low": "P3"}.get(severity, "P2")


def case_from_question(row: dict[str, Any], *, status: str, selection_mode: str) -> dict[str, Any]:
    question_id = str(row.get("question_id") or "")
    question = compact_text(row.get("question"), limit=4000)
    answer_excerpt = compact_text(row.get("expected_answer_excerpt") or row.get("answer_hint"), limit=4000)
    source_doc_id = str(row.get("expected_source_doc_id") or "")
    case_id = question_id or f"RQ_{stable_hash(question)}"
    suite = suite_for(row)
    is_safety = suite == "safety"
    expected_behavior = str(row.get("expected_behavior") or "").strip()
    if not expected_behavior:
        expected_behavior = NEGATIVE_BEHAVIOR if is_safety else "answer_from_source"

    gold_answer = None if is_safety else answer_excerpt
    gold_evidence = []
    if source_doc_id or answer_excerpt:
        gold_evidence.append(
            {
                "source_id": source_doc_id,
                "document_id": source_doc_id,
                "title": row.get("source_title") or row.get("source_subject") or "",
                "url": row.get("source_url") or "",
                "excerpt": answer_excerpt,
            }
        )

    return {
        "case_id": case_id,
        "status": status,
        "suite": suite,
        "priority": priority_for(row),
        "severity": severity_for(row),
        "intent": str(row.get("question_type") or "grounded_answer"),
        "task_type": "safety_refusal" if is_safety else "grounded_qa",
        "expected_behavior": expected_behavior,
        "source_mode": "questionlist_generated",
        "question": question,
        "conversation_turns": [{"role": "user", "content": question}],
        "gold_answer": gold_answer,
        "gold_evidence": gold_evidence,
        "required_conditions": list(row.get("_required_conditions") or row.get("required_conditions") or []),
        "forbidden_claims": list(row.get("_forbidden_claims") or row.get("forbidden_claims") or []),
        "expected_tool_path": [],
        "scoring_rubric": {
            "answer_correctness": 3,
            "completeness": 2,
            "hallucination": -3,
            "safety": 2 if is_safety else 1,
        },
        "metadata": {
            "question_id": question_id,
            "question_type": row.get("question_type"),
            "difficulty": row.get("difficulty"),
            "expected_behavior": expected_behavior,
            "expected_source_doc_id": source_doc_id,
            "source_type": row.get("source_type"),
            "source_title": row.get("source_title"),
            "source_subject": row.get("source_subject"),
            "source_path": row.get("source_path"),
            "source_url": row.get("source_url"),
            "tags": row.get("tags"),
            "selection_mode": selection_mode,
            "prompt_focus": row.get("_prompt_focus") or row.get("prompt_focus"),
            "prompt_risk": row.get("_prompt_risk") or row.get("prompt_risk"),
            "prompt_expectation": row.get("_prompt_expectation") or row.get("prompt_expectation"),
        },
    }


def stratify_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row.get("expected_behavior") or ""),
        str(row.get("source_type") or ""),
        str(row.get("question_type") or ""),
        str(row.get("difficulty") or ""),
    )


def balanced_select(rows: list[dict[str, Any]], sample_size: int, seed: int) -> list[dict[str, Any]]:
    if sample_size <= 0 or sample_size >= len(rows):
        return list(rows)

    rng = random.Random(seed)
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()

    def add(row: dict[str, Any]) -> None:
        question_id = str(row.get("question_id") or stable_hash(str(row.get("question"))))
        if question_id not in selected_ids and len(selected) < sample_size:
            selected_ids.add(question_id)
            selected.append(row)

    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[stratify_key(row)].append(row)
    for group_rows in groups.values():
        rng.shuffle(group_rows)

    def interleaved_group_keys(keys: list[tuple[str, str, str, str]]) -> list[tuple[str, str, str, str]]:
        by_source: dict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
        for key in sorted(keys, key=lambda item: (item[2], item[3], item[1], item[0])):
            by_source[key[1]].append(key)

        ordered: list[tuple[str, str, str, str]] = []
        sources = sorted(by_source)
        while any(by_source.values()):
            for source in sources:
                if by_source[source]:
                    ordered.append(by_source[source].pop(0))
        return ordered

    non_negative_keys = [key for key in groups if key[0] != NEGATIVE_BEHAVIOR]
    ordered_keys = interleaved_group_keys(non_negative_keys)

    negative_rows = [row for row in rows if row.get("expected_behavior") == NEGATIVE_BEHAVIOR]
    rng.shuffle(negative_rows)
    negative_quota = 0
    if negative_rows:
        negative_quota = len(negative_rows) if sample_size >= 300 else max(1, sample_size // 30)
        negative_quota = min(len(negative_rows), negative_quota, sample_size)
    positive_target = sample_size - negative_quota

    for key in ordered_keys:
        if len(selected) >= positive_target:
            break
        add(groups[key][0])

    group_items = [(key, groups[key][1:]) for key in ordered_keys]
    while len(selected) < positive_target:
        added = False
        for _, group_rows in group_items:
            while group_rows:
                row = group_rows.pop(0)
                before = len(selected)
                add(row)
                added = added or len(selected) > before
                break
            if len(selected) >= positive_target:
                break
        if not added:
            break

    guardrails = negative_rows[:negative_quota]
    if not guardrails:
        return selected

    total = min(sample_size, len(selected) + len(guardrails))
    positions: list[int] = []
    for index in range(len(guardrails)):
        position = 0 if len(guardrails) == 1 else round(index * (total - 1) / (len(guardrails) - 1))
        while position in positions and position < total - 1:
            position += 1
        positions.append(position)
    position_set = set(positions)

    interleaved: list[dict[str, Any]] = []
    positive_index = 0
    guardrail_index = 0
    for position in range(total):
        if position in position_set and guardrail_index < len(guardrails):
            interleaved.append(guardrails[guardrail_index])
            guardrail_index += 1
        elif positive_index < len(selected):
            interleaved.append(selected[positive_index])
            positive_index += 1
        elif guardrail_index < len(guardrails):
            interleaved.append(guardrails[guardrail_index])
            guardrail_index += 1
    return interleaved


def diff_score(diff_row: dict[str, Any]) -> float:
    regression_type = str(diff_row.get("regression_type") or "")
    release_gate = str(diff_row.get("release_gate") or "")
    error_type = str(diff_row.get("error_type") or "")
    try:
        score_delta = float(diff_row.get("score_delta") or 0)
    except ValueError:
        score_delta = 0.0
    score = abs(score_delta)
    if score_delta < 0:
        score += abs(score_delta)
    if release_gate == "block":
        score += 1000
    elif release_gate == "review":
        score += 500
    if regression_type == "new_failure":
        score += 800
    elif regression_type == "score_drop":
        score += 400
    elif regression_type == "persistent_failure":
        score += 150
    if error_type and error_type != "normal":
        score += 100
    return score


def select_from_diff(rows: list[dict[str, Any]], diff_path: Path, sample_size: int, seed: int) -> list[dict[str, Any]]:
    diff_by_case = read_diff(diff_path)
    matched = [row for row in rows if str(row.get("question_id") or "") in diff_by_case]
    if not matched:
        raise SystemExit(
            "No regression_diff rows matched questionlist question_id values. "
            "Run a questionlist eval with at least two configs first, then pass that run's regression_diff.jsonl."
        )
    matched.sort(key=lambda row: diff_score(diff_by_case[str(row.get("question_id"))]), reverse=True)
    return matched[:sample_size] if sample_size > 0 else matched


def prompt_focus_for(row: dict[str, Any]) -> dict[str, Any] | None:
    question_type = str(row.get("question_type") or "")
    for rule in PROMPT_FOCUS_RULES:
        if question_type in rule.get("question_types", set()):
            return rule
        if any(question_type.startswith(prefix) for prefix in rule.get("question_prefixes", ())):
            return rule
    return None


def annotated_prompt_row(row: dict[str, Any], rule: dict[str, Any]) -> dict[str, Any]:
    annotated = dict(row)
    annotated["_prompt_focus"] = rule["focus"]
    annotated["_prompt_risk"] = rule["risk"]
    annotated["_prompt_expectation"] = rule["expectation"]
    return annotated


def prompt_change_select(rows: list[dict[str, Any]], sample_size: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    groups: dict[str, list[dict[str, Any]]] = {rule["focus"]: [] for rule in PROMPT_FOCUS_RULES}
    for row in rows:
        rule = prompt_focus_for(row)
        if rule:
            groups[rule["focus"]].append(annotated_prompt_row(row, rule))
    for group_rows in groups.values():
        rng.shuffle(group_rows)

    max_size = sum(len(group_rows) for group_rows in groups.values())
    target_size = max_size if sample_size <= 0 else min(sample_size, max_size)
    if target_size <= 0:
        return []

    base_total = sum(min(int(rule["quota"]), len(groups[rule["focus"]])) for rule in PROMPT_FOCUS_RULES)
    if target_size >= base_total:
        quotas = {rule["focus"]: min(int(rule["quota"]), len(groups[rule["focus"]])) for rule in PROMPT_FOCUS_RULES}
    else:
        quotas = {rule["focus"]: 0 for rule in PROMPT_FOCUS_RULES}
        remaining = target_size
        focus_cycle = [rule["focus"] for rule in PROMPT_FOCUS_RULES if groups[rule["focus"]]]
        while remaining > 0 and focus_cycle:
            progressed = False
            for focus in focus_cycle:
                if quotas[focus] < len(groups[focus]):
                    quotas[focus] += 1
                    remaining -= 1
                    progressed = True
                    if remaining <= 0:
                        break
            if not progressed:
                break

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()

    def add(row: dict[str, Any]) -> None:
        question_id = str(row.get("question_id") or stable_hash(str(row.get("question"))))
        if question_id not in selected_ids and len(selected) < target_size:
            selected_ids.add(question_id)
            selected.append(row)

    for rule in PROMPT_FOCUS_RULES:
        focus = rule["focus"]
        for row in groups[focus][: quotas.get(focus, 0)]:
            add(row)

    while len(selected) < target_size:
        progressed = False
        for rule in PROMPT_FOCUS_RULES:
            focus = rule["focus"]
            for row in groups[focus]:
                before = len(selected)
                add(row)
                if len(selected) > before:
                    progressed = True
                    break
            if len(selected) >= target_size:
                break
        if not progressed:
            break

    selected_by_focus: dict[str, list[dict[str, Any]]] = {rule["focus"]: [] for rule in PROMPT_FOCUS_RULES}
    for row in selected:
        selected_by_focus[str(row.get("_prompt_focus") or "")].append(row)

    interleaved: list[dict[str, Any]] = []
    while any(selected_by_focus.values()):
        for rule in PROMPT_FOCUS_RULES:
            focus = rule["focus"]
            if selected_by_focus[focus]:
                interleaved.append(selected_by_focus[focus].pop(0))
    return interleaved


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def count(field: str) -> dict[str, int]:
        result: dict[str, int] = {}
        for row in rows:
            key = str(row.get(field) or row.get(f"_{field}") or "")
            result[key] = result.get(key, 0) + 1
        return dict(sorted(result.items()))

    return {
        "total": len(rows),
        "source_type": count("source_type"),
        "question_type": count("question_type"),
        "difficulty": count("difficulty"),
        "expected_behavior": count("expected_behavior"),
        "prompt_focus": count("prompt_focus"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build regression cases from generated questionlist files.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--mode", choices=["balanced", "all", "from-diff", "prompt-change"], default="balanced")
    parser.add_argument("--sample-size", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--diff", default=None, help="Previous regression_diff.jsonl/csv used by --mode from-diff.")
    parser.add_argument("--status", choices=["active", "candidate", "shadow"], default="active")
    parser.add_argument("--summary", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)
    raw_rows = read_jsonl(input_path)

    if args.mode == "all":
        selected = raw_rows
    elif args.mode == "from-diff":
        if not args.diff:
            raise SystemExit("--diff is required when --mode from-diff")
        selected = select_from_diff(raw_rows, Path(args.diff), args.sample_size, args.seed)
    elif args.mode == "prompt-change":
        selected = prompt_change_select(raw_rows, args.sample_size, args.seed)
    else:
        selected = balanced_select(raw_rows, args.sample_size, args.seed)

    cases = [case_from_question(row, status=args.status, selection_mode=args.mode) for row in selected]
    write_jsonl(output_path, cases)

    summary = {
        "input": str(input_path),
        "output": str(output_path),
        "mode": args.mode,
        "sample_size": args.sample_size,
        "seed": args.seed,
        "selected": summarize(selected),
    }
    summary_path = Path(args.summary) if args.summary else output_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"input={input_path}")
    print(f"output={output_path}")
    print(f"cases={len(cases)}")
    print(f"summary={summary_path}")


if __name__ == "__main__":
    main()
