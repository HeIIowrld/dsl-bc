from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BENCHMARK_DIR = ROOT / "questionlist" / "benchmark"
DEFAULT_REGRESSION_DIR = ROOT / "questionlist" / "regression"
DEFAULT_OUTPUT_DIR = ROOT / "out" / "eval_runs" / "final_sets"
DEFAULT_SUMMARY = DEFAULT_OUTPUT_DIR / "final_question_sets.summary.json"

XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def compact(value: Any, limit: int = 4000) -> str:
    text = " ".join(str(value or "").replace("\ufffd", "").split())
    return text[:limit]


def stable_hash(text: str, length: int = 12) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:length].upper()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


def slug(value: str) -> str:
    text = re.sub(r"[^0-9A-Za-z가-힣]+", "_", compact(value, limit=80)).strip("_")
    return text or "unknown"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def xlsx_column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    index = 0
    for ch in letters:
        index = index * 26 + ord(ch.upper()) - 64
    return max(0, index - 1)


def read_shared_strings(zipped: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zipped.namelist():
        return []
    root = ET.fromstring(zipped.read("xl/sharedStrings.xml"))
    values = []
    for si in root.findall(f"{XLSX_NS}si"):
        values.append("".join(node.text or "" for node in si.findall(f".//{XLSX_NS}t")))
    return values


def workbook_sheets(zipped: zipfile.ZipFile) -> list[tuple[str, str]]:
    workbook = ET.fromstring(zipped.read("xl/workbook.xml"))
    rels = ET.fromstring(zipped.read("xl/_rels/workbook.xml.rels"))
    relmap = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
    sheets: list[tuple[str, str]] = []
    for sheet in workbook.findall(f"{XLSX_NS}sheets/{XLSX_NS}sheet"):
        name = str(sheet.attrib.get("name") or "")
        rel_id = str(sheet.attrib.get(f"{REL_NS}id") or "")
        target = str(relmap.get(rel_id) or "").lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        sheets.append((name, target))
    return sheets


def cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    if cell.attrib.get("t") == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(f".//{XLSX_NS}t"))
    value = cell.find(f"{XLSX_NS}v")
    if value is None or value.text is None:
        return ""
    if cell.attrib.get("t") == "s":
        try:
            return shared_strings[int(value.text)]
        except (IndexError, ValueError):
            return ""
    return value.text


def read_xlsx_sheet_rows(path: Path, preferred_prefix: str = "QA_") -> tuple[str, list[dict[str, str]]]:
    with zipfile.ZipFile(path) as zipped:
        shared_strings = read_shared_strings(zipped)
        sheets = workbook_sheets(zipped)
        selected = next((sheet for sheet in sheets if sheet[0].startswith(preferred_prefix)), sheets[0])
        sheet_name, sheet_path = selected
        sheet = ET.fromstring(zipped.read(sheet_path))
        raw_rows: list[list[str]] = []
        for row_element in sheet.findall(f"{XLSX_NS}sheetData/{XLSX_NS}row"):
            row: list[str] = []
            for cell in row_element.findall(f"{XLSX_NS}c"):
                index = xlsx_column_index(str(cell.attrib.get("r") or "A1"))
                while len(row) <= index:
                    row.append("")
                row[index] = cell_value(cell, shared_strings)
            if any(compact(value) for value in row):
                raw_rows.append(row)
        if not raw_rows:
            return sheet_name, []
        headers = [compact(value, limit=200) for value in raw_rows[0]]
        rows = []
        for raw in raw_rows[1:]:
            row = {header: compact(raw[index] if index < len(raw) else "") for index, header in enumerate(headers) if header}
            if any(row.values()):
                rows.append(row)
        return sheet_name, rows


def first_field(row: dict[str, Any], names: Iterable[str]) -> str:
    for name in names:
        value = compact(row.get(name))
        if value:
            return value
    return ""


def numeric_or_code_conditions(answer: str, limit: int = 6) -> list[str]:
    candidates = re.findall(
        r"(?:[A-Z][A-Z0-9-]{2,}|[0-9][0-9,]*(?:\.[0-9]+)?\s*(?:%|bp|원|만원|만 원|일|년|개월|회|배|조|억|p|마일|포인트|야드))",
        answer,
    )
    result = []
    for candidate in candidates:
        text = compact(candidate, limit=80)
        if text and text not in result:
            result.append(text)
        if len(result) >= limit:
            break
    return result


def required_conditions(answer: str, extras: Iterable[str] = ()) -> list[str]:
    result = []
    for value in extras:
        text = compact(value, limit=160)
        if text and text not in result:
            result.append(text)
    answer_text = compact(answer)
    if answer_text and len(answer_text) <= 80 and answer_text not in result:
        result.append(answer_text)
    for value in numeric_or_code_conditions(answer_text):
        if value not in result:
            result.append(value)
    return result[:8]


def base_case(
    *,
    case_id: str,
    question: str,
    answer: str,
    suite: str,
    question_type: str,
    topic: str,
    source_type: str,
    source_path: Path,
    source_dataset: str,
    row_number: int,
    role: str,
    benchmark_group: str = "",
    regression_family: str = "",
    severity: str = "medium",
    forbidden_claims: list[str] | None = None,
    required: list[str] | None = None,
    metadata_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    is_regression = role == "regression"
    status = "active" if is_regression else "shadow"
    expected_behavior = "answer_not_supported_or_refuse" if question_type == "민감" else "answer_from_sample_evidence"
    relative_source = str(source_path.relative_to(ROOT) if source_path.is_relative_to(ROOT) else source_path)
    source_id = f"{source_dataset}:{row_number}"
    title_parts = [topic, question_type]
    source_title = " / ".join(part for part in title_parts if part) or source_dataset
    evidence_excerpt = compact(f"instruction: {question}\noutput: {answer}", limit=2400)
    metadata = {
        "question_id": case_id,
        "qa_category": source_type,
        "question_type": question_type,
        "qa_topic": topic,
        "expected_behavior": expected_behavior,
        "source_type": source_type,
        "source_title": source_title,
        "source_path": relative_source,
        "source_dataset": source_dataset,
        "selection_mode": "final-question-set",
        "qa_matrix_topic": topic,
        "dataset_pool_id": source_dataset,
        "dataset_version": "final_question_set_20260522_v1",
        "dataset_role": role,
        "case_status": status,
        "gold_verified": True,
        "release_gate_eligible": is_regression,
        "gate_eligible": is_regression,
        "human_review_required": False,
        "original_row_number": row_number,
        "source_file_hash": file_hash(source_path),
    }
    if benchmark_group:
        metadata["benchmark_group"] = benchmark_group
    if regression_family:
        metadata["regression_family"] = regression_family
    if metadata_extra:
        metadata.update(metadata_extra)
    return {
        "case_id": case_id,
        "status": status,
        "case_status": status,
        "suite": suite,
        "priority": "P1" if is_regression or severity in {"critical", "high"} else "P2",
        "severity": severity,
        "intent": topic or question_type or suite,
        "task_type": "grounded_qa",
        "expected_behavior": expected_behavior,
        "source_mode": "final_question_set",
        "question": question,
        "instruction": question,
        "conversation_turns": [{"role": "user", "content": question}],
        "gold_answer": answer,
        "output": answer,
        "gold_evidence": [
            {
                "source_id": source_id,
                "document_id": source_id,
                "title": source_title,
                "url": "",
                "excerpt": evidence_excerpt,
            }
        ],
        "required_conditions": required if required is not None else required_conditions(answer),
        "forbidden_claims": forbidden_claims or [],
        "expected_tool_path": [],
        "scoring_rubric": {
            "acc": 20,
            "com": 20,
            "utl": 20,
            "nac": 20,
            "hal": 20,
        },
        "qa_category": source_type,
        "qa_topic": topic,
        "source_type": source_type,
        "question_type": question_type,
        "expected_answer_excerpt": answer,
        "metadata": metadata,
        "dataset_pool_id": source_dataset,
        "dataset_version": "final_question_set_20260522_v1",
        "dataset_role": role,
        "gold_verified": True,
        "release_gate_eligible": is_regression,
        "gate_eligible": is_regression,
        "human_review_required": False,
    }


def benchmark_cases_from_csv(path: Path) -> list[dict[str, Any]]:
    rows = read_csv_rows(path)
    cases = []
    for index, row in enumerate(rows, start=1):
        question = first_field(row, ["instruction"])
        answer = first_field(row, ["output"])
        source_type = first_field(row, ["대분류"])
        question_type = first_field(row, ["질문유형"])
        topic = first_field(row, ["금융토픽"])
        metadata_extra = {}
        suite = f"benchmark_{slug(source_type).lower()}" if source_type else "benchmark_qa"
        extras = []
        if not question or not answer:
            continue
        source_dataset = path.stem
        case_id = f"BENCH-{slug(source_dataset).upper()}-{index:04d}-{stable_hash(question, 8)}"
        cases.append(
            base_case(
                case_id=case_id,
                question=question,
                answer=answer,
                suite=suite,
                question_type=question_type or "grounded_answer",
                topic=topic or "benchmark",
                source_type=source_type,
                source_path=path,
                source_dataset=source_dataset,
                row_number=index,
                role="benchmark",
                benchmark_group=source_dataset,
                severity="medium",
                required=required_conditions(answer, extras=extras),
                metadata_extra=metadata_extra,
            )
        )
    return cases


def benchmark_cases_from_xlsx(path: Path) -> list[dict[str, Any]]:
    sheet_name, rows = read_xlsx_sheet_rows(path)
    cases = []
    for index, row in enumerate(rows, start=1):
        question = first_field(row, ["instruction"])
        answer = first_field(row, ["output"])
        if not question or not answer:
            continue
        source_type = first_field(row, ["대분류"])
        topic = first_field(row, ["금융토픽"])
        question_type = first_field(row, ["질문유형"])
        source_dataset = path.stem
        case_id = f"BENCH-{slug(source_dataset).upper()}-{index:04d}-{stable_hash(question, 8)}"
        cases.append(
            base_case(
                case_id=case_id,
                question=question,
                answer=answer,
                suite="benchmark_financial_qa",
                question_type=question_type,
                topic=topic,
                source_type=source_type,
                source_path=path,
                source_dataset=source_dataset,
                row_number=index,
                role="benchmark",
                benchmark_group=source_dataset,
                severity="medium",
                metadata_extra={
                    "xlsx_sheet": sheet_name,
                },
            )
        )
    return cases


def regression_cases_from_csv(path: Path) -> list[dict[str, Any]]:
    rows = read_csv_rows(path)
    cases = []
    for index, row in enumerate(rows, start=1):
        source_dataset = path.stem
        forbidden: list[str] = []
        metadata_extra: dict[str, Any] = {}
        question = first_field(row, ["instruction"])
        answer = first_field(row, ["output"])
        source_type = first_field(row, ["대분류"])
        question_type = first_field(row, ["질문유형"])
        topic = first_field(row, ["금융토픽"])
        suite = f"regression_{slug(source_type).lower()}" if source_type else "regression_qa"
        severity = "critical" if question_type == "민감" else "high"
        family = source_type or "qa"
        if not question or not answer:
            continue
        case_id = f"REG-{slug(source_dataset).upper()}-{index:04d}-{stable_hash(question, 8)}"
        cases.append(
            base_case(
                case_id=case_id,
                question=question,
                answer=answer,
                suite=suite,
                question_type=question_type,
                topic=topic,
                source_type=source_type,
                source_path=path,
                source_dataset=source_dataset,
                row_number=index,
                role="regression",
                regression_family=family,
                severity=severity,
                forbidden_claims=forbidden,
                required=required_conditions(answer),
                metadata_extra=metadata_extra,
            )
        )
    return cases


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def summarize_cases(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total": len(rows),
        "suite": dict(Counter(row.get("suite") for row in rows)),
        "source_type": dict(Counter(row.get("source_type") for row in rows)),
        "question_type": dict(Counter(row.get("question_type") for row in rows)),
        "topic": dict(Counter(row.get("metadata", {}).get("qa_matrix_topic") for row in rows)),
        "case_status": dict(Counter(row.get("case_status") for row in rows)),
        "dataset_role": dict(Counter(row.get("dataset_role") for row in rows)),
        "release_gate_eligible": dict(Counter(str(row.get("release_gate_eligible")).lower() for row in rows)),
    }


def deduplicate_cases(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    seen: dict[str, str] = {}
    deduped = []
    duplicates = []
    for row in rows:
        key = stable_hash(compact(row.get("question")) + "\n" + compact(row.get("gold_answer")), 20)
        case_id = str(row.get("case_id") or "")
        if key in seen:
            duplicates.append({"kept_case_id": seen[key], "duplicate_case_id": case_id})
            continue
        seen[key] = case_id
        deduped.append(row)
    return deduped, duplicates


def build_benchmark_sets(benchmark_dir: Path) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    source_sets: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(benchmark_dir.glob("*")):
        if path.suffix.lower() == ".csv":
            cases = benchmark_cases_from_csv(path)
        elif path.suffix.lower() == ".xlsx":
            cases = benchmark_cases_from_xlsx(path)
        else:
            continue
        source_sets[path.stem] = cases
    all_cases = [case for cases in source_sets.values() for case in cases]
    return source_sets, all_cases


def build_regression_sets(regression_dir: Path) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]], list[dict[str, str]]]:
    source_sets: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(regression_dir.glob("*.csv")):
        source_sets[path.stem] = regression_cases_from_csv(path)
    all_cases = [case for cases in source_sets.values() for case in cases]
    deduped, duplicates = deduplicate_cases(all_cases)
    return source_sets, deduped, duplicates


def output_name(prefix: str, source_id: str) -> str:
    return f"{prefix}_{slug(source_id).lower()}_cases.jsonl"


def display_path(path: Path) -> str:
    return str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)


def build_outputs(benchmark_dir: Path, regression_dir: Path, output_dir: Path, summary_path: Path) -> dict[str, Any]:
    benchmark_sources, benchmark_cases = build_benchmark_sets(benchmark_dir)
    regression_sources, regression_cases, regression_duplicates = build_regression_sets(regression_dir)

    benchmark_output = output_dir / "benchmark_final_full_cases.jsonl"
    regression_output = output_dir / "regression_golden_full_cases.jsonl"
    write_jsonl(benchmark_output, benchmark_cases)
    write_jsonl(regression_output, regression_cases)

    source_outputs = {}
    for source_id, rows in benchmark_sources.items():
        path = output_dir / output_name("benchmark", source_id)
        write_jsonl(path, rows)
        source_outputs[f"benchmark/{source_id}"] = {
            "output": display_path(path),
            **summarize_cases(rows),
        }
    for source_id, rows in regression_sources.items():
        path = output_dir / output_name("regression", source_id)
        write_jsonl(path, rows)
        source_outputs[f"regression/{source_id}"] = {
            "output": display_path(path),
            **summarize_cases(rows),
        }

    summary = {
        "benchmark": {
            "input_dir": display_path(benchmark_dir),
            "output": display_path(benchmark_output),
            **summarize_cases(benchmark_cases),
        },
        "regression_golden": {
            "input_dir": display_path(regression_dir),
            "output": display_path(regression_output),
            "duplicates_removed": len(regression_duplicates),
            "duplicate_examples": regression_duplicates[:20],
            **summarize_cases(regression_cases),
        },
        "sources": source_outputs,
    }
    write_json(summary_path, summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build final benchmark/regression JSONL case sets for the UI runner.")
    parser.add_argument("--benchmark-dir", default=str(DEFAULT_BENCHMARK_DIR))
    parser.add_argument("--regression-dir", default=str(DEFAULT_REGRESSION_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build_outputs(
        benchmark_dir=Path(args.benchmark_dir),
        regression_dir=Path(args.regression_dir),
        output_dir=Path(args.output_dir),
        summary_path=Path(args.summary),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
