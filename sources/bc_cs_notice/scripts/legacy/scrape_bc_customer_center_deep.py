from __future__ import annotations

import argparse
import csv
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

from scrape_bc_customer_pages import (
    BASE_URL,
    DEFAULT_START_URL,
    MenuItem,
    dedupe_by_url,
    extract_main_text,
    find_javascript_redirect,
    is_login_redirect,
    iter_menu_items,
    normalize_space,
    scrape_page,
)
from scrape_bc_faq import FaqItem, scrape_faqs


DETAIL_URL_PATTERNS = (
    "BcnewsViewActn.do",
    "ServiceChangeViewActn.do",
    "FinanceCautionView.do",
    "CstmrBestCaseViewActn.do",
    "FinanceExampleView.do",
    "FinanceConflictView.do",
)


@dataclass
class DeepPage:
    source_type: str
    label: str
    url: str
    final_url: str
    parent_menu_path: str
    http_status: int | None
    scrape_status: str
    title: str
    breadcrumbs: str
    text: str
    text_length: int
    kb_id: str = ""
    node_id: str = ""
    error: str = ""


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


def with_page_no(url: str, page_no: int) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["pageNo"] = str(page_no)
    return urlunparse(parsed._replace(query=urlencode(query)))


def max_page_from_html(html: str) -> int:
    pages = [int(value) for value in re.findall(r"goPageMove\(['\"]?(\d+)['\"]?\)", html)]
    pages = [page for page in pages if page > 0]
    return max(pages, default=1)


def is_internal_detail_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc != urlparse(BASE_URL).netloc:
        return False
    if not parsed.path.startswith("/app/card/"):
        return False
    return any(pattern in parsed.path for pattern in DETAIL_URL_PATTERNS)


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)))
    return urlunparse(parsed._replace(query=query, fragment=""))


def extract_detail_links(html: str, page_url: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    contents = soup.select_one("#contents") or soup.body or soup
    links: list[tuple[str, str]] = []
    seen: set[str] = set()

    for selector in [".locWr", ".location", ".tab_depth1", ".tab_depth2", ".tab_depth3"]:
        for node in contents.select(selector):
            node.decompose()

    for anchor in contents.select("a[href]"):
        href = (anchor.get("href") or "").strip()
        if not href or href == "#" or href.lower().startswith("javascript:"):
            continue
        url = urljoin(page_url, href)
        if not is_internal_detail_url(url):
            continue
        key = normalize_url(url)
        if key in seen:
            continue
        seen.add(key)
        label = normalize_space(anchor.get_text(" ", strip=True))
        links.append((label, url))

    return links


def fetch_html(session: requests.Session, url: str, timeout: int) -> requests.Response:
    response = session.get(url, timeout=timeout)
    js_redirect_url = find_javascript_redirect(response.text, response.url)
    if js_redirect_url:
        response = session.get(js_redirect_url, timeout=timeout)
    return response


def scrape_detail_page(
    session: requests.Session,
    label: str,
    url: str,
    parent_menu_path: str,
    timeout: int,
) -> DeepPage:
    try:
        response = fetch_html(session, url, timeout)
        title, breadcrumbs, text = extract_main_text(response.text)
        if is_login_redirect(response.url, response.text, text):
            status = "login_required"
        elif response.status_code >= 400:
            status = "http_error"
        elif not text:
            status = "empty"
        else:
            status = "ok"
        return DeepPage(
            source_type="detail",
            label=label or title,
            url=url,
            final_url=response.url,
            parent_menu_path=parent_menu_path,
            http_status=response.status_code,
            scrape_status=status,
            title=title,
            breadcrumbs=breadcrumbs,
            text=text,
            text_length=len(text),
        )
    except Exception as exc:
        return DeepPage(
            source_type="detail",
            label=label,
            url=url,
            final_url="",
            parent_menu_path=parent_menu_path,
            http_status=None,
            scrape_status="error",
            title="",
            breadcrumbs="",
            text="",
            text_length=0,
            error=f"{type(exc).__name__}: {exc}",
        )


def discover_detail_links(
    session: requests.Session,
    menu_url: str,
    timeout: int,
    delay: float,
    max_pages: int | None,
) -> list[tuple[str, str]]:
    first = fetch_html(session, menu_url, timeout)
    page_count = max_page_from_html(first.text)
    if max_pages:
        page_count = min(page_count, max_pages)

    links = extract_detail_links(first.text, first.url)
    seen = {normalize_url(url) for _, url in links}

    for page_no in range(2, page_count + 1):
        response = fetch_html(session, with_page_no(menu_url, page_no), timeout)
        for label, url in extract_detail_links(response.text, response.url):
            key = normalize_url(url)
            if key in seen:
                continue
            seen.add(key)
            links.append((label, url))
        if delay:
            time.sleep(delay)

    return links


def menu_page_to_deep(page, source_type: str = "menu") -> DeepPage:
    return DeepPage(
        source_type=source_type,
        label=page.label,
        url=page.url,
        final_url=page.final_url,
        parent_menu_path=page.menu_path,
        http_status=page.http_status,
        scrape_status=page.scrape_status,
        title=page.title,
        breadcrumbs=page.breadcrumbs,
        text=page.text,
        text_length=page.text_length,
        error=page.error,
    )


def faq_to_deep(row: FaqItem) -> DeepPage:
    return DeepPage(
        source_type="faq",
        label=row.title,
        url=row.source_url,
        final_url=row.source_url,
        parent_menu_path=f"자주찾는질문 FAQ > {row.node_path}",
        http_status=200 if row.scrape_status == "ok" else None,
        scrape_status=row.scrape_status,
        title=row.title,
        breadcrumbs=row.node_path,
        text=row.answer,
        text_length=len(row.answer),
        kb_id=row.kb_id,
        node_id=row.node_id,
        error=row.error,
    )


def load_existing_faq(path: Path) -> list[FaqItem]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fp:
        rows = list(csv.DictReader(fp))
    items: list[FaqItem] = []
    for row in rows:
        items.append(
            FaqItem(
                kb_id=row.get("kb_id", ""),
                node_id=row.get("node_id", ""),
                title=row.get("title", ""),
                answer=row.get("answer", ""),
                node_name=row.get("node_name", ""),
                node_path=row.get("node_path", ""),
                created_date=row.get("created_date", ""),
                updated_date=row.get("updated_date", ""),
                hit_count=int(row["hit_count"]) if row.get("hit_count") else None,
                source_url=row.get("source_url", ""),
                scrape_status=row.get("scrape_status", ""),
                error=row.get("error", ""),
            )
        )
    return items


def write_rows(rows: Iterable[DeepPage], csv_path: Path, jsonl_path: Path) -> None:
    rows = list(rows)
    fieldnames = list(asdict(rows[0]).keys()) if rows else list(DeepPage.__annotations__)

    with csv_path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))

    with jsonl_path.open("w", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape BC Card customer-center menu pages, board detail pages, and FAQ items."
    )
    parser.add_argument("--start-url", default=DEFAULT_START_URL)
    parser.add_argument("--out-dir", default="sources/bc_cs_notice/generated")
    parser.add_argument("--delay", type=float, default=0.02)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--max-pages-per-list", type=int, default=None)
    parser.add_argument("--skip-faq", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    session = make_session()
    start_response = session.get(args.start_url, timeout=args.timeout)
    start_response.raise_for_status()
    start_soup = BeautifulSoup(start_response.text, "lxml")
    menu_items = dedupe_by_url(iter_menu_items(start_soup))

    rows: list[DeepPage] = []
    seen_detail_urls: set[str] = set()

    for index, item in enumerate(menu_items, start=1):
        menu_page = scrape_page(session, item, timeout=args.timeout)
        rows.append(menu_page_to_deep(menu_page))

        detail_links = discover_detail_links(
            session=session,
            menu_url=item.url,
            timeout=args.timeout,
            delay=args.delay,
            max_pages=args.max_pages_per_list,
        )
        new_links = []
        for label, url in detail_links:
            key = normalize_url(url)
            if key in seen_detail_urls:
                continue
            seen_detail_urls.add(key)
            new_links.append((label, url))

        print(
            f"[menu {index:03d}/{len(menu_items):03d}] "
            f"{menu_page.scrape_status:14s} details={len(new_links):4d} {item.menu_path}"
        )

        for label, url in new_links:
            rows.append(
                scrape_detail_page(
                    session=session,
                    label=label,
                    url=url,
                    parent_menu_path=item.menu_path,
                    timeout=args.timeout,
                )
            )
            if args.delay:
                time.sleep(args.delay)

    if not args.skip_faq:
        faq_path = out_dir / "bc_faq_items.csv"
        faq_rows = load_existing_faq(faq_path)
        if not faq_rows:
            faq_rows = scrape_faqs(delay=args.delay, timeout=args.timeout)
        rows.extend(faq_to_deep(row) for row in faq_rows)
        print(f"[faq] rows={len(faq_rows)}")

    csv_path = out_dir / "bc_customer_center_deep.csv"
    jsonl_path = out_dir / "bc_customer_center_deep.jsonl"
    write_rows(rows, csv_path, jsonl_path)

    summary: dict[str, int] = {}
    type_summary: dict[str, int] = {}
    for row in rows:
        summary[row.scrape_status] = summary.get(row.scrape_status, 0) + 1
        type_summary[row.source_type] = type_summary.get(row.source_type, 0) + 1

    print("\nSummary")
    print(json.dumps({"status": summary, "source_type": type_summary}, ensure_ascii=False, indent=2))
    print(f"CSV:   {csv_path}")
    print(f"JSONL: {jsonl_path}")


if __name__ == "__main__":
    main()


