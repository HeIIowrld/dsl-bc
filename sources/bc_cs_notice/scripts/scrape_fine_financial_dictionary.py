from __future__ import annotations

import argparse
import csv
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


DEFAULT_LIST_URL = "https://fine.fss.or.kr/fine/fnctip/fncDicary/list.do?menuNo=900021"


@dataclass
class DictionaryEntry:
    source_type: str
    sequence: str
    term_ko: str
    term_en: str
    definition: str
    page_index: int
    list_url: str
    content: str
    text_length: int
    scrape_status: str
    error: str = ""


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_multiline(value: str) -> str:
    lines: list[str] = []
    previous = ""
    for line in (value or "").replace("\xa0", " ").splitlines():
        line = normalize_space(line)
        if line and line != previous:
            lines.append(line)
        previous = line
    return "\n".join(lines)


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
            ),
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }
    )
    return session


def with_page_index(url: str, page_index: int) -> str:
    parsed = urlparse(url)
    query = {key: values[-1] for key, values in parse_qs(parsed.query, keep_blank_values=True).items()}
    query["pageIndex"] = str(page_index)
    return urlunparse(parsed._replace(query=urlencode(query)))


def max_page_from_list(soup: BeautifulSoup) -> int:
    count_text = soup.select_one(".count-total")
    if count_text:
        text = normalize_space(count_text.get_text(" ", strip=True))
        match = re.search(r"\[\s*\d+\s*/\s*(\d+)\s*페이지\s*\]", text)
        if match:
            return int(match.group(1))
    pages = []
    for anchor in soup.select(".pagination a[href]"):
        match = re.search(r"fnSearch\((\d+)\)", anchor.get("href") or "")
        if match:
            pages.append(int(match.group(1)))
    return max(pages, default=1)


def split_term(raw_title: str) -> tuple[str, str, str]:
    title = normalize_space(raw_title)
    match = re.match(r"(?P<seq>\d+)\.\s*(?P<body>.*)", title)
    sequence = match.group("seq") if match else ""
    body = match.group("body") if match else title

    english = ""
    english_match = re.search(r"\[([^\]]+)\]\s*$", body)
    if english_match:
        english = normalize_space(english_match.group(1))
        body = body[: english_match.start()].strip()
    return sequence, normalize_space(body), english


def parse_entries_from_page(
    session: requests.Session,
    list_url: str,
    page_index: int,
    timeout: int,
) -> tuple[list[DictionaryEntry], int]:
    url = with_page_index(list_url, page_index)
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    max_page = max_page_from_list(soup)

    entries: list[DictionaryEntry] = []
    for dl in soup.select("#content .bd-list.result-list dl"):
        dt = dl.find("dt")
        dd = dl.find("dd")
        if not dt or not dd:
            continue
        sequence, term_ko, term_en = split_term(dt.get_text("\n", strip=True))
        definition = normalize_multiline(dd.get_text("\n", strip=True))
        if not term_ko and not definition:
            continue

        content_parts = [f"용어: {term_ko}"]
        if term_en:
            content_parts.append(f"영문: {term_en}")
        if sequence:
            content_parts.append(f"번호: {sequence}")
        content_parts.append(f"정의:\n{definition}")
        content = "\n".join(content_parts)

        entries.append(
            DictionaryEntry(
                source_type="fine_financial_dictionary",
                sequence=sequence,
                term_ko=term_ko,
                term_en=term_en,
                definition=definition,
                page_index=page_index,
                list_url=response.url,
                content=content,
                text_length=len(content),
                scrape_status="ok",
            )
        )
    return entries, max_page


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_corpus_rows(entries: list[DictionaryEntry]) -> list[dict[str, object]]:
    rows = []
    for entry in entries:
        if entry.scrape_status != "ok" or not entry.content.strip():
            continue
        doc_id = f"fine_financial_dictionary_{entry.sequence or entry.page_index}_{entry.term_ko}"
        rows.append(
            {
                "doc_id": doc_id,
                "source_type": entry.source_type,
                "title": entry.term_ko,
                "url": entry.list_url,
                "sequence": entry.sequence,
                "term_ko": entry.term_ko,
                "term_en": entry.term_en,
                "content": entry.content,
                "char_count": len(entry.content),
            }
        )
    return rows


def scrape_dictionary(
    list_url: str,
    timeout: int,
    delay: float,
    limit_pages: int | None,
) -> list[DictionaryEntry]:
    session = make_session()
    first_entries, max_page = parse_entries_from_page(session, list_url, 1, timeout)
    entries = first_entries
    total_pages = min(max_page, limit_pages) if limit_pages else max_page
    print(f"[fine-dict] page 1/{total_pages}: {len(first_entries)} entries")

    for page_index in range(2, total_pages + 1):
        if delay:
            time.sleep(delay)
        try:
            page_entries, _ = parse_entries_from_page(session, list_url, page_index, timeout)
            entries.extend(page_entries)
            print(f"[fine-dict] page {page_index}/{total_pages}: {len(page_entries)} entries")
        except Exception as exc:
            print(f"[fine-dict] page {page_index}/{total_pages}: error {type(exc).__name__}: {exc}")
            entries.append(
                DictionaryEntry(
                    source_type="fine_financial_dictionary",
                    sequence="",
                    term_ko="",
                    term_en="",
                    definition="",
                    page_index=page_index,
                    list_url=with_page_index(list_url, page_index),
                    content="",
                    text_length=0,
                    scrape_status="error",
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
    return entries


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape FINE financial dictionary entries.")
    parser.add_argument("--url", default=DEFAULT_LIST_URL, help="FINE financial dictionary list URL")
    parser.add_argument("--out-dir", default="sources/bc_cs_notice/generated", help="Output directory")
    parser.add_argument("--timeout", type=int, default=25, help="HTTP timeout in seconds")
    parser.add_argument("--delay", type=float, default=0.03, help="Delay between page requests")
    parser.add_argument("--limit-pages", type=int, default=None, help="Limit page count for testing")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    entries = scrape_dictionary(args.url, args.timeout, args.delay, args.limit_pages)
    rows = [asdict(entry) for entry in entries]
    corpus_rows = build_corpus_rows(entries)

    base = out_dir / "fine_financial_dictionary"
    write_csv(base.with_suffix(".csv"), rows, list(DictionaryEntry.__dataclass_fields__.keys()))
    write_jsonl(base.with_suffix(".jsonl"), rows)
    write_csv(
        out_dir / "fine_financial_dictionary_corpus.csv",
        corpus_rows,
        ["doc_id", "source_type", "title", "url", "sequence", "term_ko", "term_en", "content", "char_count"],
    )
    write_jsonl(out_dir / "fine_financial_dictionary_corpus.jsonl", corpus_rows)

    ok_count = sum(1 for entry in entries if entry.scrape_status == "ok")
    print(f"[fine-dict] total={len(entries)} ok={ok_count} corpus={len(corpus_rows)}")
    print(f"[fine-dict] wrote {base.with_suffix('.csv')}")
    print(f"[fine-dict] wrote {base.with_suffix('.jsonl')}")
    print(f"[fine-dict] wrote {out_dir / 'fine_financial_dictionary_corpus.csv'}")
    print(f"[fine-dict] wrote {out_dir / 'fine_financial_dictionary_corpus.jsonl'}")


if __name__ == "__main__":
    main()


