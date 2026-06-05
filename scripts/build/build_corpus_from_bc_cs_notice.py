from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "sources" / "bc_cs_notice" / "out" / "llm_regression_all_sources.jsonl"
DEFAULT_OUT_DIR = ROOT / "out" / "corpus"
DEFAULT_EVIDENCE_DIR = ROOT / "out" / "evidence"


def stable_hash(value: str, length: int = 16) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def safe_slug(value: str, fallback: str = "unknown") -> str:
    text = re.sub(r"[^0-9A-Za-z가-힣_]+", "_", value or "").strip("_")
    return text or fallback


def source_group_for(source_type: str, source_file: str) -> str:
    text = f"{source_type} {source_file}".lower()
    if "bc" in text or "bccard" in text:
        return "bc_public"
    if "crefia" in text:
        return "card_industry_public"
    if "fine" in text:
        return "fss_public_finance"
    return "public_corpus"


def authority_for(source_group: str) -> str:
    if source_group == "bc_public":
        return "bc_official_public"
    if source_group in {"card_industry_public", "fss_public_finance"}:
        return "public_reference"
    return "public_corpus"


def infer_format(row: dict[str, Any]) -> str:
    url = str(row.get("url") or row.get("path") or "").lower()
    if url.endswith(".pdf"):
        return "pdf"
    if url.endswith((".xlsx", ".xls")):
        return "spreadsheet"
    if url.endswith(".csv"):
        return "csv"
    return "html_or_jsonl"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line_no, line in enumerate(file, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def split_chunks(text: str, max_chars: int) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []

    paragraphs = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs or [text]:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            for start in range(0, len(paragraph), max_chars):
                chunks.append(paragraph[start : start + max_chars].strip())
            continue
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current.strip())
            current = paragraph
    if current:
        chunks.append(current.strip())
    return chunks


def build_artifacts(
    rows: list[dict[str, Any]],
    *,
    input_name: str,
    collected_at: str,
    max_chunk_chars: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    documents: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    hard_negative_rows: list[dict[str, Any]] = []
    source_stats: dict[str, dict[str, Any]] = {}
    source_hash_parts: dict[str, list[str]] = defaultdict(list)

    for index, row in enumerate(rows):
        content = str(row.get("content") or "")
        title = str(row.get("title") or "").strip() or "(untitled)"
        source_type = str(row.get("source_type") or "unknown")
        source_file = str(row.get("source_file") or input_name)
        source_slug = safe_slug(Path(source_file).stem or source_type)
        source_id = f"SRC_{source_slug.upper()}"
        source_group = source_group_for(source_type, source_file)
        source_hash = "sha256:" + hashlib.sha256(
            json.dumps(
                {
                    "title": title,
                    "url": row.get("url"),
                    "path": row.get("path"),
                    "content": content,
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        original_doc_id = str(row.get("doc_id") or f"row_{index:06d}")
        document_id = f"DOC_{stable_hash(source_id + ':' + original_doc_id + ':' + source_hash, 20)}"

        metadata = {
            key: value
            for key, value in row.items()
            if key
            not in {
                "content",
            }
        }
        metadata["original_doc_id"] = original_doc_id
        metadata["input_name"] = input_name

        document = {
            "document_id": document_id,
            "source_id": source_id,
            "source_group": source_group,
            "source_type": source_type,
            "authority_level": authority_for(source_group),
            "title": title,
            "version": None,
            "effective_date": None,
            "collected_at": collected_at,
            "source_url_or_path": str(row.get("url") or row.get("path") or ""),
            "source_hash": source_hash,
            "content_format": infer_format(row),
            "pii_level": "none",
            "license_scope": "internal_eval_only",
            "char_count": len(content),
            "metadata": metadata,
        }
        documents.append(document)
        source_hash_parts[source_id].append(source_hash)
        source_stats.setdefault(
            source_id,
            {
                "source_id": source_id,
                "source_group": source_group,
                "source_type": source_type,
                "authority_level": document["authority_level"],
                "collected_at": collected_at,
                "document_count": 0,
                "chunk_count": 0,
                "source_files": set(),
                "source_hash": "",
            },
        )
        source_stats[source_id]["document_count"] += 1
        source_stats[source_id]["source_files"].add(source_file)

        for chunk_index, chunk_text in enumerate(split_chunks(content, max_chunk_chars), 1):
            normalized_text = normalize_ws(chunk_text)
            chunk_id = f"{document_id}__chunk_{chunk_index:04d}"
            chunk = {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "source_id": source_id,
                "section_path": [title],
                "content_type": source_type,
                "text": chunk_text,
                "normalized_text": normalized_text,
                "page": None,
                "clause_no": None,
                "valid_from": None,
                "valid_to": None,
                "embedding_text": normalize_ws(f"{title}\n{chunk_text}"),
                "table_refs": [],
                "metadata": {
                    "source_group": source_group,
                    "source_url_or_path": document["source_url_or_path"],
                    "original_doc_id": original_doc_id,
                },
            }
            chunks.append(chunk)
            source_stats[source_id]["chunk_count"] += 1
            evidence_rows.append(
                {
                    "evidence_id": f"EVID_{stable_hash(chunk_id, 20)}",
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "source_id": source_id,
                    "evidence_type": "text_chunk",
                    "title": title,
                    "source_url_or_path": document["source_url_or_path"],
                    "text": chunk_text,
                }
            )
            if source_group != "bc_public":
                hard_negative_rows.append(
                    {
                        "hard_negative_id": f"HN_{stable_hash(chunk_id, 20)}",
                        "chunk_id": chunk_id,
                        "document_id": document_id,
                        "source_id": source_id,
                        "reason": "non_bc_public_reference",
                        "title": title,
                        "text": chunk_text[:1000],
                    }
                )

    source_versions: list[dict[str, Any]] = []
    for source_id, stats in sorted(source_stats.items()):
        stats = dict(stats)
        stats["source_files"] = sorted(stats["source_files"])
        stats["source_hash"] = "sha256:" + hashlib.sha256(
            "\n".join(sorted(source_hash_parts[source_id])).encode("utf-8")
        ).hexdigest()
        source_versions.append(stats)

    return documents, chunks, source_versions, evidence_rows, hard_negative_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build canonical corpus artifacts from bc_cs_notice outputs.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Input JSONL from bc_cs_notice")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Canonical corpus output directory")
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR), help="Evidence output directory")
    parser.add_argument("--max-chunk-chars", type=int, default=1800)
    parser.add_argument("--collected-at", default=date.today().isoformat())
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    out_dir = Path(args.out_dir)
    evidence_dir = Path(args.evidence_dir)
    if not input_path.exists():
        raise SystemExit(f"Input corpus does not exist: {input_path}")

    rows = read_jsonl(input_path)
    documents, chunks, source_versions, evidence_rows, hard_negative_rows = build_artifacts(
        rows,
        input_name=input_path.name,
        collected_at=args.collected_at,
        max_chunk_chars=args.max_chunk_chars,
    )

    counts = {
        "documents": write_jsonl(out_dir / "documents.jsonl", documents),
        "chunks": write_jsonl(out_dir / "chunks.jsonl", chunks),
        "source_versions": write_jsonl(out_dir / "source_versions.jsonl", source_versions),
        "tables": write_jsonl(out_dir / "tables.jsonl", []),
        "facts": write_jsonl(out_dir / "facts.jsonl", []),
        "api_snapshots": write_jsonl(out_dir / "api_snapshots.jsonl", []),
        "evidence_store": write_jsonl(evidence_dir / "evidence_store.jsonl", evidence_rows),
        "hard_negative_pool": write_jsonl(evidence_dir / "hard_negative_pool.jsonl", hard_negative_rows),
    }
    print(json.dumps(counts, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
