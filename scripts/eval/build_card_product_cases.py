from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.build_questionlist_cases import stable_hash


DEFAULT_OUTPUT = ROOT / "out" / "eval_runs" / "profiles" / "card_product_dummy_cases.jsonl"
DEFAULT_SUMMARY = ROOT / "out" / "eval_runs" / "profiles" / "card_product_dummy_cases.summary.json"

QUESTION_TYPE_DEFAULTS = {
    "annual_fee": ("product_fee", "card_product_fee_qa"),
    "benefit_lookup": ("product_benefit", "card_product_benefit_qa"),
    "condition_lookup": ("product_condition", "card_product_condition_qa"),
    "exclusion_lookup": ("product_exclusion", "card_product_exclusion_qa"),
    "summary": ("product_summary", "card_product_summary_qa"),
}


def compact(value: Any, limit: int = 1800) -> str:
    text = " ".join(str(value or "").replace("\ufffd", "").split())
    return text[:limit]


def split_list(value: Any) -> list[str]:
    if value is None:
        return []
    parts = re.split(r"[|;\n]", str(value))
    return [compact(part, limit=240) for part in parts if compact(part, limit=240)]


def field(row: dict[str, Any], key: str, default: str = "") -> str:
    return compact(row.get(key), limit=400) or default


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def evidence_excerpt(row: dict[str, Any]) -> str:
    explicit = field(row, "evidence_excerpt")
    if explicit:
        return explicit
    parts = [
        f"카드명: {field(row, 'card_name')}",
        f"연회비: {field(row, 'annual_fee')}",
        f"혜택분류: {field(row, 'benefit_category')}",
        f"혜택내용: {field(row, 'benefit_summary')}",
        f"적용조건: {field(row, 'conditions')}",
        f"제외기준: {field(row, 'exclusions')}",
        f"비고: {field(row, 'notes')}",
    ]
    return compact("\n".join(part for part in parts if not part.endswith(": ")), limit=1800)


def derived_question(row: dict[str, Any], question_type: str) -> str:
    card_name = field(row, "card_name", "해당 카드")
    benefit_category = field(row, "benefit_category", "주요")
    if question_type == "annual_fee":
        return f"{card_name}의 연회비는 얼마인가요?"
    if question_type == "benefit_lookup":
        return f"{card_name}의 {benefit_category} 혜택은 무엇인가요?"
    if question_type == "condition_lookup":
        return f"{card_name}의 혜택 적용 조건은 무엇인가요?"
    if question_type == "exclusion_lookup":
        return f"{card_name}의 혜택 제외 기준은 무엇인가요?"
    if question_type == "summary":
        return f"{card_name}의 주요 혜택과 조건을 근거 기반으로 요약해주세요."
    return f"{card_name}에 대해 근거 기반으로 답변해주세요."


def derived_answer(row: dict[str, Any], question_type: str) -> str:
    card_name = field(row, "card_name", "해당 카드")
    annual_fee = field(row, "annual_fee")
    benefit_category = field(row, "benefit_category", "주요")
    benefit_summary = field(row, "benefit_summary")
    conditions = field(row, "conditions")
    exclusions = field(row, "exclusions")
    if question_type == "annual_fee":
        return f"{card_name}의 연회비는 {annual_fee}입니다."
    if question_type == "benefit_lookup":
        return f"{card_name}의 {benefit_category} 혜택은 {benefit_summary}입니다."
    if question_type == "condition_lookup":
        return f"{card_name}의 혜택 적용 조건은 {conditions}입니다."
    if question_type == "exclusion_lookup":
        return f"{card_name}의 혜택 제외 기준은 {exclusions}입니다."
    if question_type == "summary":
        return f"{card_name}은 {benefit_summary} 혜택을 제공하며 주요 조건은 {conditions}입니다."
    return compact(f"{card_name}: {benefit_summary} {conditions}")


def derived_required(row: dict[str, Any], question_type: str, gold_answer: str) -> list[str]:
    explicit = split_list(row.get("required_conditions"))
    if explicit:
        return explicit

    required = [field(row, "card_name")]
    if question_type == "annual_fee":
        required.append(field(row, "annual_fee"))
    elif question_type == "benefit_lookup":
        required.extend([field(row, "benefit_category"), field(row, "benefit_summary")])
    elif question_type == "condition_lookup":
        required.append(field(row, "conditions"))
    elif question_type == "exclusion_lookup":
        required.append(field(row, "exclusions"))
    else:
        required.extend([field(row, "benefit_summary"), field(row, "conditions")])

    return [item for item in required if item] or [gold_answer]


def priority_for_question_type(question_type: str) -> tuple[str, str]:
    if question_type in {"annual_fee", "condition_lookup", "exclusion_lookup"}:
        return "P1", "high"
    return "P2", "medium"


def make_case(row: dict[str, Any], row_number: int, csv_path: Path) -> dict[str, Any]:
    question_type = field(row, "question_type", "summary")
    topic, task_type = QUESTION_TYPE_DEFAULTS.get(question_type, ("product_general", "card_product_grounded_qa"))
    topic = field(row, "topic", topic)
    card_name = field(row, "card_name", f"dummy_card_{row_number}")
    question = field(row, "question") or derived_question(row, question_type)
    gold_answer = field(row, "gold_answer") or derived_answer(row, question_type)
    required_conditions = derived_required(row, question_type, gold_answer)
    product_id = field(row, "product_id", stable_hash(card_name, 8))
    case_id = field(row, "case_id") or f"CARD-PRODUCT-{stable_hash(product_id + question_type + question, 12)}"
    priority, severity = priority_for_question_type(question_type)
    priority = field(row, "priority", priority)
    severity = field(row, "severity", severity)
    source_url = field(row, "source_url")
    title = field(row, "evidence_title", card_name)

    return {
        "case_id": case_id,
        "status": field(row, "status", "active"),
        "suite": field(row, "suite", "card_product_info"),
        "priority": priority,
        "severity": severity,
        "intent": topic,
        "task_type": task_type,
        "source_mode": "card_product_csv",
        "question": question,
        "conversation_turns": [{"role": "user", "content": question}],
        "gold_answer": gold_answer,
        "gold_evidence": [
            {
                "source_id": f"card_product:{product_id}",
                "document_id": product_id,
                "title": title,
                "url": source_url,
                "excerpt": evidence_excerpt(row),
            }
        ],
        "required_conditions": required_conditions,
        "forbidden_claims": split_list(row.get("forbidden_claims")),
        "expected_tool_path": [],
        "scoring_rubric": {
            "answer_correctness": 3,
            "completeness": 2,
            "hallucination": -3,
            "safety": 1,
        },
        "expected_behavior": "answer_from_sample_evidence",
        "source_type": "card_product_csv",
        "question_type": question_type,
        "expected_answer_excerpt": gold_answer,
        "metadata": {
            "question_id": case_id,
            "question_type": question_type,
            "expected_behavior": "answer_from_sample_evidence",
            "expected_source_doc_id": product_id,
            "source_type": "card_product_csv",
            "source_title": title,
            "source_path": str(csv_path),
            "source_url": source_url,
            "source_dataset": field(row, "source_dataset", "card_product_dummy_csv"),
            "selection_mode": field(row, "selection_mode", "card-product-csv-generated"),
            "qa_matrix_topic": topic,
            "card_name": card_name,
            "benefit_category": field(row, "benefit_category"),
            "annual_fee": field(row, "annual_fee"),
        },
    }


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def build_cases(csv_path: Path) -> list[dict[str, Any]]:
    rows = [make_case(row, idx, csv_path) for idx, row in enumerate(read_csv_rows(csv_path), start=1)]
    rows.sort(key=lambda row: row["case_id"])
    return rows


def summarize(rows: list[dict[str, Any]], csv_path: Path, output: Path) -> dict[str, Any]:
    return {
        "input": str(csv_path),
        "output": str(output),
        "total": len(rows),
        "suite": dict(Counter(row.get("suite") for row in rows)),
        "topic": dict(Counter(row.get("metadata", {}).get("qa_matrix_topic") for row in rows)),
        "question_type": dict(Counter(row.get("question_type") for row in rows)),
        "source_type": dict(Counter(row.get("source_type") for row in rows)),
        "expected_behavior": dict(Counter(row.get("expected_behavior") for row in rows)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build card/product CSV regression cases.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    csv_path = Path(args.input)
    output = Path(args.output)
    summary_path = Path(args.summary)
    if not csv_path.exists():
        raise SystemExit(f"Card/product CSV does not exist: {csv_path}")
    rows = build_cases(csv_path)
    if not rows:
        raise SystemExit(f"No card/product cases generated from {csv_path}")
    write_jsonl(output, rows)
    summary = summarize(rows, csv_path, output)
    write_json(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
