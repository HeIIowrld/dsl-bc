from __future__ import annotations

import argparse
import csv
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, NavigableString


BASE_URL = "https://www.bccard.com"
DEFAULT_START_URL = (
    "https://www.bccard.com/app/card/ContentsLinkActn.do?pgm_id=ind1077"
)


@dataclass(frozen=True)
class MenuItem:
    label: str
    url: str
    menu_path: str
    depth: int


@dataclass
class ScrapedPage:
    label: str
    url: str
    final_url: str
    menu_path: str
    depth: int
    http_status: int | None
    scrape_status: str
    title: str
    breadcrumbs: str
    text: str
    text_length: int
    error: str = ""


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def get_title(soup: BeautifulSoup) -> str:
    if not soup.title:
        return ""
    return normalize_space(soup.title.get_text(" ", strip=True))


def get_breadcrumbs(contents: BeautifulSoup) -> str:
    crumbs = []
    for node in contents.select(".location li"):
        text = normalize_space(node.get_text(" ", strip=True))
        if text and text.upper() != "HOME":
            crumbs.append(text)
    return " > ".join(crumbs)


def find_javascript_redirect(html: str, current_url: str) -> str | None:
    match = re.search(
        r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]",
        html,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return urljoin(current_url, match.group(1).strip())


def replace_images_with_alt(node: BeautifulSoup) -> None:
    for img in node.find_all("img"):
        alt = normalize_space(img.get("alt") or "")
        if alt:
            img.insert_before(NavigableString(f"\n{alt}\n"))
        img.decompose()


def extract_main_text(html: str) -> tuple[str, str, str]:
    soup = BeautifulSoup(html, "lxml")
    title = get_title(soup)
    contents = soup.select_one("#contents") or soup.select_one("#security") or soup.body
    if contents is None:
        return title, "", ""

    # Keep the breadcrumb separately; remove navigation/tab furniture from body text.
    breadcrumbs = get_breadcrumbs(contents)
    for selector in [
        ".locWr",
        ".location",
        ".tab_depth1",
        ".tab_depth2",
        ".tab_depth3",
        ".conTitWr",
    ]:
        for node in contents.select(selector):
            node.decompose()

    for node in contents.select(
        "script, style, noscript, iframe, object, embed, input, select, textarea, button"
    ):
        node.decompose()

    replace_images_with_alt(contents)
    raw_text = contents.get_text("\n", strip=True)

    lines: list[str] = []
    previous = ""
    for line in raw_text.splitlines():
        line = normalize_space(line)
        if line and line != previous:
            lines.append(line)
        previous = line

    return title, breadcrumbs, "\n".join(lines)


def is_login_redirect(final_url: str, html: str, text: str) -> bool:
    if "GenericFwd.do" in final_url or "openCookieSignin.jsp" in html:
        return True
    return not text and "SsoLoginSave.do" in html


def iter_menu_items(soup: BeautifulSoup, section: str | None = None) -> Iterable[MenuItem]:
    lnb = soup.select_one("#lnb ul.depth2")
    if lnb is None:
        return

    def walk(li, parent_path: list[str], depth: int) -> Iterable[MenuItem]:
        direct_anchor = li.find("a", recursive=False)
        label = normalize_space(direct_anchor.get_text(" ", strip=True)) if direct_anchor else ""
        path = [*parent_path, label] if label else parent_path

        if direct_anchor:
            href = (direct_anchor.get("href") or "").strip()
            if href and href != "#" and not href.lower().startswith("javascript:"):
                yield MenuItem(
                    label=label,
                    url=urljoin(BASE_URL, href),
                    menu_path=" > ".join(path),
                    depth=depth,
                )

        for child_ul in li.find_all("ul", recursive=False):
            for child_li in child_ul.find_all("li", recursive=False):
                yield from walk(child_li, path, depth + 1)

    top_level_lis = lnb.find_all("li", recursive=False)
    for top_li in top_level_lis:
        top_anchor = top_li.find("a", recursive=False)
        top_label = (
            normalize_space(top_anchor.get_text(" ", strip=True)) if top_anchor else ""
        )
        if section and top_label != section:
            continue
        yield from walk(top_li, [], 2)


def dedupe_by_url(items: Iterable[MenuItem]) -> list[MenuItem]:
    seen: set[str] = set()
    unique: list[MenuItem] = []
    for item in items:
        if item.url in seen:
            continue
        seen.add(item.url)
        unique.append(item)
    return unique


def scrape_page(session: requests.Session, item: MenuItem, timeout: int) -> ScrapedPage:
    try:
        response = session.get(item.url, timeout=timeout)
        js_redirect_url = find_javascript_redirect(response.text, response.url)
        if js_redirect_url:
            response = session.get(js_redirect_url, timeout=timeout)

        title, breadcrumbs, text = extract_main_text(response.text)
        if is_login_redirect(response.url, response.text, text):
            scrape_status = "login_required"
        elif response.status_code >= 400:
            scrape_status = "http_error"
        elif not text:
            scrape_status = "empty"
        else:
            scrape_status = "ok"

        return ScrapedPage(
            label=item.label,
            url=item.url,
            final_url=response.url,
            menu_path=item.menu_path,
            depth=item.depth,
            http_status=response.status_code,
            scrape_status=scrape_status,
            title=title,
            breadcrumbs=breadcrumbs,
            text=text,
            text_length=len(text),
        )
    except Exception as exc:
        return ScrapedPage(
            label=item.label,
            url=item.url,
            final_url="",
            menu_path=item.menu_path,
            depth=item.depth,
            http_status=None,
            scrape_status="error",
            title="",
            breadcrumbs="",
            text="",
            text_length=0,
            error=f"{type(exc).__name__}: {exc}",
        )


def write_jsonl(rows: list[ScrapedPage], path: Path) -> None:
    with path.open("w", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")


def write_csv(rows: list[ScrapedPage], path: Path) -> None:
    fieldnames = list(asdict(rows[0]).keys()) if rows else list(ScrapedPage.__annotations__)
    with path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape BC Card customer-center pages from the left navigation menu."
    )
    parser.add_argument("--start-url", default=DEFAULT_START_URL)
    parser.add_argument(
        "--section",
        default=None,
        help='Top-level left-menu section to scrape, e.g. "소비자 보호체계". Omit for all.',
    )
    parser.add_argument("--out-dir", default="sources/bc_cs_notice/generated")
    parser.add_argument("--delay", type=float, default=0.2)
    parser.add_argument("--timeout", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

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

    start_response = session.get(args.start_url, timeout=args.timeout)
    start_response.raise_for_status()
    start_soup = BeautifulSoup(start_response.text, "lxml")
    menu_items = dedupe_by_url(iter_menu_items(start_soup, section=args.section))

    rows: list[ScrapedPage] = []
    for index, item in enumerate(menu_items, start=1):
        row = scrape_page(session, item, timeout=args.timeout)
        rows.append(row)
        print(
            f"[{index:03d}/{len(menu_items):03d}] "
            f"{row.scrape_status:14s} {row.text_length:5d} {item.menu_path}"
        )
        if args.delay:
            time.sleep(args.delay)

    suffix = "all" if not args.section else re.sub(r"[^0-9A-Za-z가-힣_-]+", "_", args.section)
    jsonl_path = out_dir / f"bc_customer_pages_{suffix}.jsonl"
    csv_path = out_dir / f"bc_customer_pages_{suffix}.csv"
    write_jsonl(rows, jsonl_path)
    write_csv(rows, csv_path)

    summary: dict[str, int] = {}
    for row in rows:
        summary[row.scrape_status] = summary.get(row.scrape_status, 0) + 1

    print("\nSummary")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"JSONL: {jsonl_path}")
    print(f"CSV:   {csv_path}")


if __name__ == "__main__":
    main()


