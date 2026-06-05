from __future__ import annotations

import argparse
import csv
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

from scrape_bc_customer_center_deep import (
    DeepPage,
    discover_detail_links,
    faq_to_deep,
    make_session,
    normalize_url,
    scrape_detail_page,
)
from scrape_bc_customer_pages import (
    BASE_URL,
    MenuItem,
    extract_main_text,
    find_javascript_redirect,
    is_login_redirect,
    normalize_space,
)
from scrape_bc_faq import FaqItem, scrape_faqs


@dataclass(frozen=True)
class SeedLink:
    label: str
    url: str
    source_file: str


def strip_fragment(url: str) -> str:
    parsed = urlparse(url)
    return urlunparse(parsed._replace(fragment=""))


def clean_tracking_query(url: str) -> str:
    parsed = urlparse(strip_fragment(url))
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    # Keep query parameters because many BC pages are keyed by pgm_id/newsno.
    return urlunparse(parsed._replace(query=urlencode(pairs)))


def is_bc_app_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc in {"www.bccard.com", "bccard.com"} and parsed.path.startswith(
        "/app/card/"
    )


def read_html(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8", "cp949", "euc-kr"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def extract_seed_links(path: Path) -> list[SeedLink]:
    soup = BeautifulSoup(read_html(path), "lxml")
    seeds: list[SeedLink] = []
    seen: set[str] = set()

    for anchor in soup.select("a[href]"):
        href = (anchor.get("href") or "").strip()
        if not href or href == "#" or href.lower().startswith(("javascript:", "mailto:", "tel:")):
            continue
        url = clean_tracking_query(urljoin(BASE_URL + "/app/card/", href))
        if not is_bc_app_url(url):
            continue
        key = normalize_url(url)
        if key in seen:
            continue
        seen.add(key)
        label = normalize_space(anchor.get_text(" ", strip=True))
        seeds.append(SeedLink(label=label, url=url, source_file=str(path)))

    return seeds


def fetch_html(session: requests.Session, url: str, timeout: int) -> requests.Response:
    response = session.get(url, timeout=timeout)
    redirect_url = find_javascript_redirect(response.text, response.url)
    if redirect_url:
        response = session.get(redirect_url, timeout=timeout)
    return response


def scrape_seed_page(session: requests.Session, seed: SeedLink, timeout: int) -> DeepPage:
    try:
        response = fetch_html(session, seed.url, timeout)
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
            source_type="html_seed",
            label=seed.label or title,
            url=seed.url,
            final_url=response.url,
            parent_menu_path=seed.label,
            http_status=response.status_code,
            scrape_status=status,
            title=title,
            breadcrumbs=breadcrumbs,
            text=text,
            text_length=len(text),
        )
    except Exception as exc:
        return DeepPage(
            source_type="html_seed",
            label=seed.label,
            url=seed.url,
            final_url="",
            parent_menu_path=seed.label,
            http_status=None,
            scrape_status="error",
            title="",
            breadcrumbs="",
            text="",
            text_length=0,
            error=f"{type(exc).__name__}: {exc}",
        )


def load_existing_faq(path: Path) -> list[FaqItem]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fp:
        rows = list(csv.DictReader(fp))
    faq_rows: list[FaqItem] = []
    for row in rows:
        faq_rows.append(
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
    return faq_rows


def write_rows(rows: list[DeepPage], csv_path: Path, jsonl_path: Path) -> None:
    fieldnames = list(asdict(rows[0]).keys()) if rows else list(DeepPage.__annotations__)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))

    with jsonl_path.open("w", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")


def safe_suffix(path: Path) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", path.stem).strip("_") or "html_links"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape every BC Card /app/card link found in a saved HTML file."
    )
    parser.add_argument("html_path", nargs="?", default=None)
    parser.add_argument("--out-dir", default="sources/bc_cs_notice/generated")
    parser.add_argument("--delay", type=float, default=0.02)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--expand-list-details", action="store_true", default=True)
    parser.add_argument("--skip-list-details", action="store_false", dest="expand_list_details")
    parser.add_argument("--include-faq", action="store_true", default=True)
    parser.add_argument("--skip-faq", action="store_false", dest="include_faq")
    parser.add_argument("--max-pages-per-list", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.html_path:
        html_path = Path(args.html_path)
    else:
        candidates = sorted(Path("sources/bc_cs_notice/inputs").glob("*.html"))
        if not candidates:
            candidates = sorted(Path("sources/bc_cs_notice").glob("*.html"))
        if not candidates:
            raise FileNotFoundError("No .html files found in sources/bc_cs_notice/inputs")
        html_path = candidates[0]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    session = make_session()
    seeds = extract_seed_links(html_path)
    rows: list[DeepPage] = []
    seen_detail_urls: set[str] = set()

    print(f"Source HTML: {html_path}")
    print(f"Unique BC /app/card links: {len(seeds)}")

    for index, seed in enumerate(seeds, start=1):
        row = scrape_seed_page(session, seed, timeout=args.timeout)
        rows.append(row)

        detail_count = 0
        if args.expand_list_details:
            detail_links = discover_detail_links(
                session=session,
                menu_url=seed.url,
                timeout=args.timeout,
                delay=args.delay,
                max_pages=args.max_pages_per_list,
            )
            for label, url in detail_links:
                key = normalize_url(url)
                if key in seen_detail_urls:
                    continue
                seen_detail_urls.add(key)
                rows.append(
                    scrape_detail_page(
                        session=session,
                        label=label,
                        url=url,
                        parent_menu_path=seed.label,
                        timeout=args.timeout,
                    )
                )
                detail_count += 1
                if args.delay:
                    time.sleep(args.delay)

        print(
            f"[{index:03d}/{len(seeds):03d}] "
            f"{row.scrape_status:14s} details={detail_count:4d} {seed.label or seed.url}"
        )
        if args.delay:
            time.sleep(args.delay)

    if args.include_faq and any("FaqListActn.do" in seed.url for seed in seeds):
        faq_path = out_dir / "bc_faq_items.csv"
        faq_rows = load_existing_faq(faq_path)
        if not faq_rows:
            faq_rows = scrape_faqs(delay=args.delay, timeout=args.timeout)
        rows.extend(faq_to_deep(row) for row in faq_rows)
        print(f"[faq] rows={len(faq_rows)}")

    suffix = safe_suffix(html_path)
    csv_path = out_dir / f"bc_links_from_{suffix}.csv"
    jsonl_path = out_dir / f"bc_links_from_{suffix}.jsonl"
    write_rows(rows, csv_path, jsonl_path)

    status_summary: dict[str, int] = {}
    type_summary: dict[str, int] = {}
    for row in rows:
        status_summary[row.scrape_status] = status_summary.get(row.scrape_status, 0) + 1
        type_summary[row.source_type] = type_summary.get(row.source_type, 0) + 1

    print("\nSummary")
    print(
        json.dumps(
            {"status": status_summary, "source_type": type_summary},
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"CSV:   {csv_path}")
    print(f"JSONL: {jsonl_path}")


if __name__ == "__main__":
    main()


