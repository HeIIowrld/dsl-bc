from __future__ import annotations

import argparse
import copy
import html
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


DEFAULT_SAMPLE_ROOT_CANDIDATES = [
    ROOT / "data" / "raw" / "sample_data",
    ROOT / "data" / "\uc0d8\ud50c\ub370\uc774\ud130",
]


def default_sample_root() -> Path:
    for path in DEFAULT_SAMPLE_ROOT_CANDIDATES:
        if path.exists():
            return path
    return DEFAULT_SAMPLE_ROOT_CANDIDATES[0]


DEFAULT_SAMPLE_ROOT = default_sample_root()
DEFAULT_OUTPUT = ROOT / "out" / "test_cases" / "sample_data_regression_cases.jsonl"
DEFAULT_SUMMARY = ROOT / "out" / "test_cases" / "sample_data_regression_cases.summary.json"

MRC_QUOTAS = {
    "multiple_choice": 6,
    "span_extraction": 8,
    "span_extraction_how": 8,
    "tableqa": 8,
    "text_entailment_yes": 4,
    "text_entailment_no": 4,
}
OCR_QUOTA = 8


def compact(value: Any, limit: int = 2400) -> str:
    text = " ".join(str(value or "").replace("\ufffd", "").split())
    return text[:limit]


def strip_html_table(value: Any, limit: int = 1800) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"</t[dh]>\s*<t[dh][^>]*>", " | ", text, flags=re.IGNORECASE)
    text = re.sub(r"</tr>\s*<tr[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return compact(text, limit=limit)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def find_child_by_prefix(root: Path, prefix: str) -> Path:
    for child in root.iterdir():
        if child.is_dir() and child.name.startswith(prefix):
            return child
    raise FileNotFoundError(f"Could not find sample subdirectory starting with {prefix!r} under {root}")


def iter_151_label_files(sample_root: Path) -> Iterable[Path]:
    dataset_root = find_child_by_prefix(sample_root, "151.")
    label_dir_name = "\u0030\u0032\u002e\ub77c\ubca8\ub9c1\ub370\uc774\ud130"
    for split in ("Training", "Validation"):
        label_dir = dataset_root / "01-1.\uc815\uc2dd\uac1c\ubc29\ub370\uc774\ud130" / split / label_dir_name
        if not label_dir.exists():
            continue
        for path in sorted(label_dir.glob("*.json")):
            if path.name.startswith(("TL_", "VL_")):
                yield path


def qkind_from_path(path: Path) -> str:
    name = path.stem
    name = name.removeprefix("TL_").removeprefix("VL_")
    return name


def answer_text(answer: dict[str, Any]) -> str:
    text = compact(answer.get("text"))
    if text:
        return text
    cell_text = answer.get("cell_text")
    if isinstance(cell_text, list):
        return compact(" / ".join(str(item) for item in cell_text if item))
    return ""


def evidence_excerpt(paragraph: dict[str, Any], answer: dict[str, Any], qkind: str) -> str:
    context = str(paragraph.get("context") or "")
    clue = answer.get("clue_text")
    if clue:
        base = compact(clue, limit=1600)
    else:
        start = answer.get("answer_start")
        if isinstance(start, int) and context:
            base = compact(context[max(0, start - 350) : start + 900], limit=1600)
        else:
            base = compact(context, limit=1600)

    if qkind == "tableqa":
        table_parts = []
        for table in paragraph.get("tbs") or []:
            if not isinstance(table, dict):
                continue
            table_title = compact(table.get("table_title"), limit=200)
            table_text = strip_html_table(table.get("table"), limit=1600)
            table_parts.append(compact(f"{table_title}\n{table_text}", limit=1800))
        table_excerpt = "\n".join(part for part in table_parts if part)
        return compact(f"{base}\n\n표 근거:\n{table_excerpt}", limit=2600)
    return base


def suite_for_kind(qkind: str) -> str:
    if qkind == "tableqa":
        return "sample_tableqa"
    if qkind == "text_entailment":
        return "sample_entailment"
    return "sample_mrc"


def task_for_kind(qkind: str) -> str:
    return {
        "multiple_choice": "multiple_choice_grounded_qa",
        "span_extraction": "span_extraction_grounded_qa",
        "span_extraction_how": "procedure_span_grounded_qa",
        "tableqa": "table_lookup_grounded_qa",
        "text_entailment": "entailment_grounded_qa",
    }.get(qkind, "sample_grounded_qa")


def priority_for_kind(qkind: str) -> tuple[str, str]:
    if qkind in {"tableqa", "span_extraction_how"}:
        return "P1", "high"
    if qkind == "text_entailment":
        return "P2", "medium"
    return "P2", "medium"


def make_mrc_case(
    *,
    sample_root: Path,
    path: Path,
    doc: dict[str, Any],
    paragraph: dict[str, Any],
    qa: dict[str, Any],
    qkind: str,
) -> dict[str, Any] | None:
    answer = qa.get("answer") if isinstance(qa.get("answer"), dict) else {}
    raw_answer = answer_text(answer)
    if not raw_answer:
        return None

    is_entailment = qkind == "text_entailment"
    answer_label = raw_answer.lower()
    if is_entailment and answer_label not in {"yes", "no"}:
        return None
    if is_entailment:
        gold_answer = "예" if answer_label == "yes" else "아니오"
        required = [gold_answer]
    else:
        gold_answer = raw_answer
        required = [raw_answer]

    options = answer.get("options")
    option_suffix = ""
    if isinstance(options, list) and options:
        option_suffix = "\n선택지: " + " / ".join(compact(option, limit=80) for option in options)

    question_prefix = {
        "tableqa": "표 근거를 사용해서 답해줘.",
        "text_entailment": "제공된 근거만 보고 참/거짓을 예 또는 아니오로 답해줘.",
        "span_extraction_how": "근거 문장에서 절차나 방법을 찾아 답해줘.",
        "multiple_choice": "선택지 중 정답을 골라 답해줘.",
    }.get(qkind, "근거 문장에서 정답을 찾아 답해줘.")
    question = compact(f"{question_prefix}\n질문: {qa.get('question')}{option_suffix}", limit=1200)
    qid = str(qa.get("question_id") or stable_hash(question, 10))
    priority, severity = priority_for_kind(qkind)
    excerpt = evidence_excerpt(paragraph, answer, qkind)
    source_id = str(doc.get("doc_id") or answer.get("source") or qid)
    title = compact(doc.get("doc_title"), limit=300)
    source_path = str(path.relative_to(sample_root))
    case_id = f"SAMPLE-151-{qkind.upper().replace('_', '-')}-{qid}"

    return {
        "case_id": case_id,
        "status": "active",
        "suite": suite_for_kind(qkind),
        "priority": priority,
        "severity": severity,
        "intent": qkind,
        "task_type": task_for_kind(qkind),
        "source_mode": "sample_data_json",
        "question": question,
        "conversation_turns": [{"role": "user", "content": question}],
        "gold_answer": gold_answer,
        "gold_evidence": [
            {
                "source_id": source_id,
                "document_id": source_id,
                "title": title,
                "url": "",
                "excerpt": excerpt,
            }
        ],
        "required_conditions": required,
        "forbidden_claims": [],
        "expected_tool_path": [],
        "scoring_rubric": {
            "answer_correctness": 3,
            "completeness": 2,
            "hallucination": -3,
            "safety": 1,
        },
        "expected_behavior": "answer_from_sample_evidence",
        "source_type": "sample_mrc_151",
        "question_type": qkind,
        "expected_answer_excerpt": gold_answer,
        "metadata": {
            "question_id": qid,
            "question_type": qkind,
            "expected_behavior": "answer_from_sample_evidence",
            "expected_source_doc_id": source_id,
            "source_type": "sample_mrc_151",
            "source_title": title,
            "source_path": source_path,
            "source_url": "",
            "source_dataset": "151.금융, 법률 문서 기계독해 데이터",
            "doc_source": doc.get("doc_source"),
            "doc_published": doc.get("doc_published"),
            "context_id": paragraph.get("context_id"),
            "qa_type": qa.get("qa_type"),
            "selection_mode": "sample-data-generated",
        },
    }


def build_mrc_cases(sample_root: Path) -> list[dict[str, Any]]:
    counts = Counter()
    cases: list[dict[str, Any]] = []
    seen_questions: set[str] = set()

    for path in iter_151_label_files(sample_root):
        qkind = qkind_from_path(path)
        if qkind not in {"multiple_choice", "span_extraction", "span_extraction_how", "tableqa", "text_entailment"}:
            continue
        payload = read_json(path)
        for doc in payload.get("data") or []:
            for paragraph in doc.get("paragraphs") or []:
                for qa in paragraph.get("qas") or []:
                    answer = qa.get("answer") if isinstance(qa.get("answer"), dict) else {}
                    raw_answer = answer_text(answer)
                    quota_key = qkind
                    if qkind == "text_entailment":
                        label = raw_answer.lower()
                        if label not in {"yes", "no"}:
                            continue
                        quota_key = f"text_entailment_{label}"
                    if counts[quota_key] >= MRC_QUOTAS.get(quota_key, 0):
                        continue
                    question = compact(qa.get("question"), limit=800)
                    if not question or question in seen_questions:
                        continue
                    case = make_mrc_case(
                        sample_root=sample_root,
                        path=path,
                        doc=doc,
                        paragraph=paragraph,
                        qa=qa,
                        qkind=qkind,
                    )
                    if not case:
                        continue
                    cases.append(case)
                    seen_questions.add(question)
                    counts[quota_key] += 1
                    if all(counts[key] >= quota for key, quota in MRC_QUOTAS.items()):
                        return cases
    return cases


def iter_055_annotation_files(sample_root: Path) -> Iterable[Path]:
    dataset_root = find_child_by_prefix(sample_root, "055.")
    for split_dir in sorted((dataset_root / "01.\ub370\uc774\ud130").iterdir()):
        if not split_dir.is_dir():
            continue
        label_root = split_dir / "\ub77c\ubca8\ub9c1\ub370\uc774\ud130"
        if not label_root.exists():
            continue
        for category in ("bank", "insure"):
            ann_dir = label_root / category / "annotations"
            if ann_dir.exists():
                yield from sorted(ann_dir.glob("*.json"))


def ocr_text(payload: dict[str, Any], limit: int = 2200) -> str:
    words: list[str] = []
    for annotation in payload.get("annotations") or []:
        for polygon in annotation.get("polygons") or []:
            text = compact(polygon.get("text"), limit=80)
            if text:
                words.append(text)
    return compact(" ".join(words), limit=limit)


def present_terms(text: str, terms: list[str], limit: int = 3) -> list[str]:
    hits: list[str] = []
    for term in terms:
        if term and term in text and term not in hits:
            hits.append(term)
        if len(hits) >= limit:
            break
    return hits


def make_ocr_case(sample_root: Path, path: Path) -> dict[str, Any] | None:
    payload = read_json(path)
    image_info = next((item for item in payload.get("images") or [] if isinstance(item, dict)), {})
    identifier = str(payload.get("Identifier") or image_info.get("identifier") or path.stem)
    document_name = compact(image_info.get("document_name"), limit=120)
    document_class = compact(image_info.get("class"), limit=80)
    full_text = ocr_text(payload)
    if not document_name or not full_text:
        return None

    required = [document_name]
    required.extend(
        term
        for term in present_terms(
            full_text,
            ["KDB생명", "청약서", "개인(신용)정보", "조회", "동의서", "정보보안동의서"],
            limit=3,
        )
        if term not in required
    )
    if document_class and document_class not in required:
        required.append(document_class)

    question = (
        f"OCR 샘플 {identifier}에서 문서명과 식별 가능한 금융 문서 키워드를 근거 기반으로 요약해줘. "
        "작성자 이메일 같은 개인 식별자는 답하지 마."
    )
    excerpt = compact(
        f"문서명: {document_name}\n문서분류: {document_class}\n"
        f"촬영환경: {image_info.get('shooting_env') or ''}\nOCR 텍스트: {full_text}",
        limit=2600,
    )
    gold_answer = compact(f"문서명은 {document_name}이고, 확인 가능한 키워드는 {', '.join(required[1:])}입니다.")
    source_path = str(path.relative_to(sample_root))
    return {
        "case_id": f"SAMPLE-055-OCR-{stable_hash(identifier + source_path, 10)}",
        "status": "active",
        "suite": "sample_ocr",
        "priority": "P2",
        "severity": "medium",
        "intent": "ocr_document_extraction",
        "task_type": "ocr_metadata_extraction",
        "source_mode": "sample_data_json",
        "question": question,
        "conversation_turns": [{"role": "user", "content": question}],
        "gold_answer": gold_answer,
        "gold_evidence": [
            {
                "source_id": identifier,
                "document_id": identifier,
                "title": document_name,
                "url": "",
                "excerpt": excerpt,
            }
        ],
        "required_conditions": required,
        "forbidden_claims": ["writer_num", "@"],
        "expected_tool_path": [],
        "scoring_rubric": {
            "answer_correctness": 3,
            "completeness": 2,
            "hallucination": -3,
            "safety": 2,
        },
        "expected_behavior": "answer_from_sample_evidence_without_pii",
        "source_type": "sample_ocr_055",
        "question_type": "ocr_metadata_extraction",
        "expected_answer_excerpt": gold_answer,
        "metadata": {
            "question_id": identifier,
            "question_type": "ocr_metadata_extraction",
            "expected_behavior": "answer_from_sample_evidence_without_pii",
            "expected_source_doc_id": identifier,
            "source_type": "sample_ocr_055",
            "source_title": document_name,
            "source_path": source_path,
            "source_url": "",
            "source_dataset": "055.금융업 특화 문서 OCR 데이터",
            "image_name": payload.get("name"),
            "image_width": image_info.get("width"),
            "image_height": image_info.get("height"),
            "selection_mode": "sample-data-generated",
        },
    }


def build_ocr_cases(sample_root: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    per_bucket = Counter()
    for path in iter_055_annotation_files(sample_root):
        bucket = next((part for part in path.parts if part in {"bank", "insure"}), "ocr")
        if per_bucket[bucket] >= OCR_QUOTA // 2:
            continue
        case = make_ocr_case(sample_root, path)
        if not case:
            continue
        cases.append(case)
        per_bucket[bucket] += 1
        if len(cases) >= OCR_QUOTA:
            break
    return cases


def make_format_variants(cases: list[dict[str, Any]], limit: int = 4) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    for base in cases:
        if len(variants) >= limit:
            break
        if base["suite"] not in {"sample_mrc", "sample_tableqa"}:
            continue
        variant = copy.deepcopy(base)
        variant["case_id"] = f"{base['case_id']}__JSON"
        variant["suite"] = "sample_format"
        variant["priority"] = "P1"
        variant["severity"] = "high"
        variant["intent"] = "json_format_contract"
        variant["task_type"] = "format_constrained_grounded_qa"
        variant["question"] = (
            base["question"]
            + "\n반드시 JSON object 하나만 반환해. 키는 answer, source_title, cannot_verify만 사용해."
        )
        variant["conversation_turns"] = [{"role": "user", "content": variant["question"]}]
        variant["format_requirements"] = {
            "must_be_json_only": True,
            "disallow_markdown_code_fence": True,
            "json_schema": {
                "type": "object",
                "required": ["answer", "source_title", "cannot_verify"],
                "properties": {
                    "answer": {"type": "string"},
                    "source_title": {"type": "string"},
                    "cannot_verify": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
        }
        variant["metadata"]["question_type"] = "json_format_contract"
        variant["metadata"]["expected_format"] = "json_object"
        variant["metadata"]["json_keys"] = ["answer", "source_title", "cannot_verify"]
        variant["metadata"]["regression_suite"] = "sample_format"
        variants.append(variant)
    return variants


def summarize(rows: list[dict[str, Any]], sample_root: Path, output: Path) -> dict[str, Any]:
    summary = {
        "sample_root": str(sample_root),
        "output": str(output),
        "total": len(rows),
        "suite": dict(Counter(row.get("suite") for row in rows)),
        "task_type": dict(Counter(row.get("task_type") for row in rows)),
        "source_type": dict(Counter(row.get("source_type") for row in rows)),
        "expected_behavior": dict(Counter(row.get("expected_behavior") for row in rows)),
    }
    return summary


def build_cases(sample_root: Path) -> list[dict[str, Any]]:
    rows = build_mrc_cases(sample_root)
    rows.extend(build_ocr_cases(sample_root))
    rows.extend(make_format_variants(rows))
    rows.sort(key=lambda row: row["case_id"])
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build regression cases from data/sample JSON files.")
    parser.add_argument("--sample-root", default=str(DEFAULT_SAMPLE_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--summary", default=str(DEFAULT_SUMMARY))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sample_root = Path(args.sample_root)
    output = Path(args.output)
    summary_path = Path(args.summary)
    if not sample_root.exists():
        raise SystemExit(f"Sample data root does not exist: {sample_root}")
    rows = build_cases(sample_root)
    if not rows:
        raise SystemExit(f"No sample-data cases generated from {sample_root}")
    write_jsonl(output, rows)
    summary = summarize(rows, sample_root, output)
    write_json(summary_path, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
