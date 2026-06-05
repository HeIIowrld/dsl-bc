from __future__ import annotations

import argparse
import csv
import json
import re
import time
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://fine.fss.or.kr"
DEFAULT_START_URL = "https://fine.fss.or.kr/main/prc/main.jsp?menuNo=900513"

PRODUCT_BY_PREFIX = {
    "dp": "예·적금",
    "lo": "대출",
    "cd": "카드",
    "is": "보험",
    "fu": "펀드",
    "ps": "연금",
}


@dataclass
class PrcPage:
    source_type: str
    title: str
    product: str
    menu_no: str
    url: str
    path: str
    depth: int
    image_urls_json: str
    image_alt_text: str
    links_json: str
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


def canonical_url(url: str) -> str:
    parsed = urlparse(urljoin(BASE_URL, url))
    if parsed.path == "/main/prc/main.jsp":
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    menu_no = ""
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key == "menuNo":
            match = re.match(r"(\d+)", value)
            if match:
                menu_no = match.group(1)
            break
    query = urlencode({"menuNo": menu_no}) if menu_no else ""
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", query, ""))


def is_prc_html_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme in {"http", "https"}
        and parsed.netloc == "fine.fss.or.kr"
        and parsed.path.startswith("/main/prc/")
        and parsed.path.endswith((".jsp", ".do"))
        and "/static/" not in parsed.path
    )


def product_from_path(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    try:
        prefix = parts[2]
    except IndexError:
        return ""
    return PRODUCT_BY_PREFIX.get(prefix, "")


def page_title(soup: BeautifulSoup, product: str) -> str:
    body = soup.find("body")
    if body and "main" in (body.get("class") or []):
        title_node = soup.select_one("title")
        if title_node:
            return normalize_space(title_node.get_text(" ", strip=True))
    candidates = [
        soup.select_one("#content h2"),
        soup.select_one("#content h3"),
        soup.select_one("#container h2"),
        soup.select_one("#container h3"),
        soup.select_one("title"),
    ]
    for node in candidates:
        if node:
            title = normalize_space(node.get_text(" ", strip=True))
            title = re.sub(r"\s*\|\s*금융감독원.*$", "", title).strip()
            if title:
                return title
    return product or "금융상품 거래 단계별 핵심정보"


def remove_noise(node: BeautifulSoup) -> None:
    selectors = [
        "script",
        "style",
        "noscript",
        "iframe",
        "object",
        "embed",
        "#header",
        "#footer",
        "#gnb",
        "#mobileGnb",
        "#lnb",
        "#mobile-lnb",
        ".gnb",
        ".gnbSet",
        ".mobileGnb",
        ".subTab",
        ".fixMenu",
        ".npSet",
        ".skip",
        ".sns-wrap",
    ]
    for bad in node.select(", ".join(selectors)):
        bad.decompose()


def extract_content_and_media(soup: BeautifulSoup, response_url: str) -> tuple[str, list[str], list[str], list[dict[str, str]]]:
    node = soup.select_one("#content") or soup.select_one("#container") or soup.body or soup
    node = BeautifulSoup(str(node), "lxml")
    remove_noise(node)

    image_urls: list[str] = []
    image_alts: list[str] = []
    for img in node.select("img"):
        src = urljoin(response_url, img.get("src") or "")
        alt = normalize_multiline(img.get("alt") or "")
        if src and not src.startswith("http://wlg.fss.or.kr"):
            image_urls.append(src)
        if alt:
            image_alts.append(alt)
            img.replace_with("\n" + alt + "\n")
        else:
            img.decompose()

    links: list[dict[str, str]] = []
    for anchor in node.select("a[href]"):
        href = anchor.get("href") or ""
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        label = normalize_space(anchor.get_text(" ", strip=True))
        full_url = urljoin(response_url, href)
        if label or full_url:
            links.append({"label": label, "url": full_url})

    text = normalize_multiline(node.get_text("\n", strip=True))
    return text, image_urls, image_alts, links


def fetch_page(session: requests.Session, url: str, depth: int, timeout: int) -> tuple[PrcPage, list[str]]:
    canonical = canonical_url(url)
    try:
        response = session.get(canonical, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        parsed = urlparse(response.url)
        product = product_from_path(parsed.path)
        title = page_title(soup, product)
        content_text, image_urls, image_alts, content_links = extract_content_and_media(soup, response.url)

        intro = [f"제목: {title}"]
        if product:
            intro.append(f"상품군: {product}")
        intro.append(f"URL: {response.url}")
        if content_text:
            intro.append(content_text)
        content = "\n".join(intro)

        discovered: list[str] = []
        for anchor in soup.select("a[href]"):
            href = anchor.get("href") or ""
            if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            next_url = canonical_url(urljoin(response.url, href))
            if is_prc_html_url(next_url):
                discovered.append(next_url)

        return (
            PrcPage(
                source_type="fine_prc_step_info",
                title=title,
                product=product,
                menu_no=dict(parse_qsl(urlparse(response.url).query)).get("menuNo", ""),
                url=response.url,
                path=parsed.path,
                depth=depth,
                image_urls_json=json.dumps(image_urls, ensure_ascii=False),
                image_alt_text="\n".join(image_alts),
                links_json=json.dumps(content_links, ensure_ascii=False),
                content=content,
                text_length=len(content),
                scrape_status="ok" if content_text else "empty",
            ),
            discovered,
        )
    except Exception as exc:
        parsed = urlparse(canonical)
        return (
            PrcPage(
                source_type="fine_prc_step_info",
                title="",
                product=product_from_path(parsed.path),
                menu_no=dict(parse_qsl(parsed.query)).get("menuNo", ""),
                url=canonical,
                path=parsed.path,
                depth=depth,
                image_urls_json="[]",
                image_alt_text="",
                links_json="[]",
                content="",
                text_length=0,
                scrape_status="error",
                error=f"{type(exc).__name__}: {exc}",
            ),
            [],
        )


def crawl(start_url: str, timeout: int, delay: float, max_pages: int | None) -> list[PrcPage]:
    session = make_session()
    queue: deque[tuple[str, int]] = deque([(canonical_url(start_url), 0)])
    seen: set[str] = set()
    pages: list[PrcPage] = []

    while queue:
        url, depth = queue.popleft()
        url = canonical_url(url)
        if url in seen or not is_prc_html_url(url):
            continue
        if max_pages and len(seen) >= max_pages:
            break
        seen.add(url)
        page, discovered = fetch_page(session, url, depth, timeout)
        pages.append(page)
        print(f"[fine-prc] {len(pages)} {page.scrape_status}: {page.title or url} ({len(discovered)} links)")
        for next_url in discovered:
            if next_url not in seen:
                queue.append((next_url, depth + 1))
        if delay:
            time.sleep(delay)
    return pages


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


def build_corpus_rows(pages: list[PrcPage]) -> list[dict[str, object]]:
    rows = []
    for page in pages:
        if page.scrape_status != "ok" or not page.content.strip():
            continue
        menu_part = page.menu_no or re.sub(r"\W+", "_", page.path).strip("_")
        rows.append(
            {
                "doc_id": f"fine_prc_step_info_{menu_part}",
                "source_type": page.source_type,
                "title": page.title,
                "path": page.product,
                "url": page.url,
                "menu_no": page.menu_no,
                "content": page.content,
                "char_count": len(page.content),
            }
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape FINE financial product transaction step information.")
    parser.add_argument("--start-url", default=DEFAULT_START_URL, help="Start URL")
    parser.add_argument("--out-dir", default="sources/bc_cs_notice/generated", help="Output directory")
    parser.add_argument("--timeout", type=int, default=25, help="HTTP timeout in seconds")
    parser.add_argument("--delay", type=float, default=0.02, help="Delay between requests")
    parser.add_argument("--max-pages", type=int, default=None, help="Limit page count for testing")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    pages = crawl(args.start_url, args.timeout, args.delay, args.max_pages)
    rows = [asdict(page) for page in pages]
    corpus_rows = build_corpus_rows(pages)

    base = out_dir / "fine_prc_step_info"
    write_csv(base.with_suffix(".csv"), rows, list(PrcPage.__dataclass_fields__.keys()))
    write_jsonl(base.with_suffix(".jsonl"), rows)
    write_csv(
        out_dir / "fine_prc_step_info_corpus.csv",
        corpus_rows,
        ["doc_id", "source_type", "title", "path", "url", "menu_no", "content", "char_count"],
    )
    write_jsonl(out_dir / "fine_prc_step_info_corpus.jsonl", corpus_rows)

    ok_count = sum(1 for page in pages if page.scrape_status == "ok")
    print(f"[fine-prc] total={len(pages)} ok={ok_count} corpus={len(corpus_rows)}")
    print(f"[fine-prc] wrote {base.with_suffix('.csv')}")
    print(f"[fine-prc] wrote {base.with_suffix('.jsonl')}")
    print(f"[fine-prc] wrote {out_dir / 'fine_prc_step_info_corpus.csv'}")
    print(f"[fine-prc] wrote {out_dir / 'fine_prc_step_info_corpus.jsonl'}")


if __name__ == "__main__":
    main()


