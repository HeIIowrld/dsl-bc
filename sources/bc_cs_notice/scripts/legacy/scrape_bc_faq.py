from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup, NavigableString


FAQ_LIST_URL = "https://www.bccard.com/app/card/FaqListActn.do"
FAQ_API_URL = "https://www.bccard.com/app/card/CommonErmsByPassNew.do"
DOMAIN_ID = "DOMAIN_BCCARD"


@dataclass
class FaqItem:
    kb_id: str
    node_id: str
    title: str
    answer: str
    node_name: str
    node_path: str
    created_date: str
    updated_date: str
    hit_count: int | None
    source_url: str
    scrape_status: str
    error: str = ""


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def format_yyyymmddhhmmss(value: str | None) -> str:
    if not value:
        return ""
    digits = re.sub(r"\D", "", value)
    if len(digits) < 8:
        return value
    date = f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    if len(digits) >= 12:
        date += f" {digits[8:10]}:{digits[10:12]}"
    if len(digits) >= 14:
        date += f":{digits[12:14]}"
    return date


def html_to_text(markup: str) -> str:
    markup = html.unescape(markup or "")
    soup = BeautifulSoup(markup, "lxml")

    for img in soup.find_all("img"):
        alt = normalize_space(img.get("alt") or "")
        if alt:
            img.insert_before(NavigableString(f"\n{alt}\n"))
        img.decompose()

    for node in soup.select("script, style, noscript, iframe, object, embed"):
        node.decompose()

    lines: list[str] = []
    previous = ""
    for line in soup.get_text("\n", strip=True).splitlines():
        line = normalize_space(line.replace("\xa0", " "))
        if line and line != previous:
            lines.append(line)
        previous = line
    return "\n".join(lines)


class BcFaqClient:
    def __init__(self, timeout: int) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
                ),
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": FAQ_LIST_URL,
            }
        )

    def post_command(self, command: dict[str, Any]) -> dict[str, Any]:
        response = self.session.post(
            FAQ_API_URL,
            data={
                "dataType": "json",
                "cmd": json.dumps(command, ensure_ascii=False, separators=(",", ":")),
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        error_code = payload.get("errorCode", payload.get("error_code", 0))
        if error_code not in (0, "0", None):
            raise RuntimeError(payload.get("errorMessage") or payload)
        return payload

    def fetch_list_page(self, page_no: int) -> tuple[list[dict[str, Any]], int]:
        payload = self.post_command(
            {
                "command": "FaqTopList",
                "domainId": DOMAIN_ID,
                "pageNo": str(page_no),
            }
        )
        data = payload.get("data", {})
        return data.get("faqList", []), int(data.get("faqCount") or 0)

    def fetch_detail(self, kb_id: str, node_id: str) -> dict[str, Any]:
        payload = self.post_command(
            {
                "command": "FaqDetailView",
                "domainId": DOMAIN_ID,
                "nodeId": node_id,
                "kbId": kb_id,
            }
        )
        return payload.get("data", {}).get("kbInfo", {})


def scrape_faqs(delay: float, timeout: int, limit: int | None = None) -> list[FaqItem]:
    client = BcFaqClient(timeout=timeout)

    first_page, total_count = client.fetch_list_page(1)
    pages = max(1, math.ceil(total_count / 10))
    raw_items = first_page[:]
    print(f"FAQ count from API: {total_count}")

    for page_no in range(2, pages + 1):
        if limit and len(raw_items) >= limit:
            break
        page_items, _ = client.fetch_list_page(page_no)
        raw_items.extend(page_items)
        print(f"[list {page_no:03d}/{pages:03d}] cumulative={len(raw_items)}")
        if delay:
            time.sleep(delay)

    if limit:
        raw_items = raw_items[:limit]

    rows: list[FaqItem] = []
    seen: set[tuple[str, str]] = set()
    for index, item in enumerate(raw_items, start=1):
        kb_id = item.get("kbId") or ""
        node_id = item.get("nodeId") or ""
        key = (kb_id, node_id)
        if key in seen:
            continue
        seen.add(key)

        try:
            detail = client.fetch_detail(kb_id, node_id)
            answer = html_to_text(detail.get("contents") or "")
            source = detail or item
            row = FaqItem(
                kb_id=kb_id,
                node_id=node_id,
                title=normalize_space(source.get("title") or item.get("title") or ""),
                answer=answer,
                node_name=normalize_space(source.get("nodeName") or item.get("nodeName") or ""),
                node_path=normalize_space(source.get("nodePath") or item.get("nodePath") or ""),
                created_date=format_yyyymmddhhmmss(
                    source.get("createdDate") or item.get("createdDate")
                ),
                updated_date=format_yyyymmddhhmmss(
                    source.get("updatedDate") or item.get("updatedDate")
                ),
                hit_count=source.get("hitCount") or item.get("hitCount"),
                source_url=FAQ_LIST_URL,
                scrape_status="ok" if answer else "empty",
            )
        except Exception as exc:
            row = FaqItem(
                kb_id=kb_id,
                node_id=node_id,
                title=normalize_space(item.get("title") or ""),
                answer="",
                node_name=normalize_space(item.get("nodeName") or ""),
                node_path=normalize_space(item.get("nodePath") or ""),
                created_date=format_yyyymmddhhmmss(item.get("createdDate")),
                updated_date=format_yyyymmddhhmmss(item.get("updatedDate")),
                hit_count=item.get("hitCount"),
                source_url=FAQ_LIST_URL,
                scrape_status="error",
                error=f"{type(exc).__name__}: {exc}",
            )

        rows.append(row)
        print(f"[detail {index:03d}/{len(raw_items):03d}] {row.scrape_status:5s} {kb_id} {row.title}")
        if delay:
            time.sleep(delay)

    return rows


def write_jsonl(rows: list[FaqItem], path: Path) -> None:
    with path.open("w", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")


def write_csv(rows: list[FaqItem], path: Path) -> None:
    fieldnames = list(asdict(rows[0]).keys()) if rows else list(FaqItem.__annotations__)
    with path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape BC Card FAQ question/answer items.")
    parser.add_argument("--out-dir", default="sources/bc_cs_notice/generated")
    parser.add_argument("--delay", type=float, default=0.05)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--limit", type=int, default=None, help="Optional small test limit.")
    return parser.parse_args()


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = scrape_faqs(delay=args.delay, timeout=args.timeout, limit=args.limit)
    csv_path = out_dir / "bc_faq_items.csv"
    jsonl_path = out_dir / "bc_faq_items.jsonl"
    write_csv(rows, csv_path)
    write_jsonl(rows, jsonl_path)

    summary: dict[str, int] = {}
    for row in rows:
        summary[row.scrape_status] = summary.get(row.scrape_status, 0) + 1
    print("\nSummary")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"CSV:   {csv_path}")
    print(f"JSONL: {jsonl_path}")


if __name__ == "__main__":
    main()


