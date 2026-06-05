from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


DEFAULT_INPUTS = [
    "bc_llm_regression_corpus.jsonl",
    "fine_life_finance_talk_all_corpus.jsonl",
    "fine_newsletter_corpus.jsonl",
    "fine_financial_dictionary_corpus.jsonl",
    "fine_prc_step_info_corpus.jsonl",
    "crefia_creditcard_guide_corpus.jsonl",
    "crefia_creditcard_faq_corpus.jsonl",
]

COMMON_FIELDS = [
    "doc_id",
    "source_type",
    "title",
    "path",
    "url",
    "content",
    "char_count",
    "source_file",
    "metadata_json",
]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def normalize_row(row: dict[str, Any], source_file: str) -> dict[str, Any]:
    metadata = {
        key: value
        for key, value in row.items()
        if key not in {"doc_id", "source_type", "title", "path", "url", "content", "char_count"}
        and value not in {"", None}
    }
    content = str(row.get("content") or "")
    char_count = row.get("char_count") or len(content)
    return {
        "doc_id": row.get("doc_id", ""),
        "source_type": row.get("source_type", ""),
        "title": row.get("title", ""),
        "path": row.get("path", ""),
        "url": row.get("url", ""),
        "content": content,
        "char_count": int(char_count),
        "source_file": source_file,
        "metadata_json": json.dumps(metadata, ensure_ascii=False),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=COMMON_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Combine BC/FINE corpus JSONL files for LLM regression tests.")
    parser.add_argument("--out-dir", default="sources/bc_cs_notice/generated", help="Directory containing corpus JSONL files")
    parser.add_argument(
        "--inputs",
        nargs="*",
        default=DEFAULT_INPUTS,
        help="Input corpus JSONL filenames under --out-dir",
    )
    parser.add_argument("--output-name", default="llm_regression_all_sources", help="Output basename")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    combined: list[dict[str, Any]] = []

    for filename in args.inputs:
        path = out_dir / filename
        if not path.exists():
            print(f"[combine-corpus] skip missing {path}")
            continue
        rows = [normalize_row(row, path.name) for row in load_jsonl(path)]
        combined.extend(rows)
        print(f"[combine-corpus] loaded {len(rows)} rows from {path.name}")

    base = out_dir / args.output_name
    write_csv(base.with_suffix(".csv"), combined)
    write_jsonl(base.with_suffix(".jsonl"), combined)

    print(f"[combine-corpus] total={len(combined)}")
    print(f"[combine-corpus] wrote {base.with_suffix('.csv')}")
    print(f"[combine-corpus] wrote {base.with_suffix('.jsonl')}")


if __name__ == "__main__":
    main()


