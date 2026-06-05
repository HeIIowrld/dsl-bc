from __future__ import annotations

import argparse
import csv
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import parse_qs, quote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://customer.crefia.or.kr"
DEFAULT_START_URL = (
    "https://customer.crefia.or.kr/common/forward.xx"
    "?url=/customer/guard/guardCreditcardUseGuide1"
)


@dataclass
class CreditcardGuidePage:
    source_type: str
    guide_no: int
    title: str
    section_title: str
    url: str
    target_path: str
    links_json: str
    image_urls_json: str
    image_alt_text: str
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


def safe_print(message: str) -> None:
    print(message.encode("cp949", errors="replace").decode("cp949"))


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
            ),
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://customer.crefia.or.kr/customer/main/main.xx",
        }
    )
    return session


def forward_url(target_path: str) -> str:
    return f"{BASE_URL}/common/forward.xx?url={quote(target_path, safe='/')}"


def guide_no_from_url(url: str) -> int:
    parsed = urlparse(url)
    target = parse_qs(parsed.query).get("url", [""])[0] or parsed.path
    match = re.search(r"guardCreditcardUseGuide(\d+)$", target)
    return int(match.group(1)) if match else 0


def target_path_from_url(url: str) -> str:
    parsed = urlparse(url)
    return parse_qs(parsed.query).get("url", [""])[0] or parsed.path


def request_with_retry(session: requests.Session, url: str, timeout: int, retries: int, delay: float) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(delay * (attempt + 1))
    raise last_error or RuntimeError("request failed")


def discover_guide_urls(session: requests.Session, start_url: str, timeout: int, retries: int, delay: float) -> list[str]:
    response = request_with_retry(session, start_url, timeout, retries, delay)
    soup = BeautifulSoup(response.text, "lxml")
    found: dict[int, str] = {}
    for anchor in soup.select("a[href]"):
        href = urljoin(response.url, anchor.get("href") or "")
        no = guide_no_from_url(href)
        if no:
            found[no] = forward_url(f"/customer/guard/guardCreditcardUseGuide{no}")
    if not found:
        found[1] = forward_url("/customer/guard/guardCreditcardUseGuide1")
    return [found[no] for no in sorted(found)]


def extract_links(node: BeautifulSoup, base_url: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for anchor in node.select("a[href]"):
        href = anchor.get("href") or ""
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        label = normalize_space(anchor.get_text(" ", strip=True))
        links.append({"label": label, "url": urljoin(base_url, href)})
    return links


def extract_content_and_media(
    soup: BeautifulSoup,
    response_url: str,
) -> tuple[str, list[str], list[str], list[dict[str, str]], str, str]:
    title = normalize_space((soup.select_one(".title_inner h3") or soup.select_one("h3") or soup.title or soup).get_text(" ", strip=True))
    content_node = soup.select_one(".tap_cont_box") or soup.select_one("#contents") or soup.body or soup
    node = BeautifulSoup(str(content_node), "lxml")

    image_urls: list[str] = []
    image_alts: list[str] = []
    for img in node.select("img"):
        src = urljoin(response_url, img.get("src") or "")
        alt = normalize_multiline(img.get("alt") or "")
        if src:
            image_urls.append(src)
        if alt:
            image_alts.append(alt)
            img.replace_with("\n" + alt + "\n")
        else:
            img.decompose()

    links = extract_links(node, response_url)
    section_title = normalize_space((node.select_one("h4") or node.select_one(".blue_tit") or node).get_text(" ", strip=True))
    text = normalize_multiline(node.get_text("\n", strip=True))
    return text, image_urls, image_alts, links, title or "신용카드 이용자 가이드", section_title


def scrape_page(
    session: requests.Session,
    url: str,
    timeout: int,
    retries: int,
    delay: float,
) -> CreditcardGuidePage:
    guide_no = guide_no_from_url(url)
    target_path = target_path_from_url(url)
    try:
        response = request_with_retry(session, url, timeout, retries, delay)
        text, image_urls, image_alts, links, title, section_title = extract_content_and_media(
            BeautifulSoup(response.text, "lxml"),
            response.url,
        )
        content = "\n".join(
            part
            for part in [
                f"제목: {title}",
                f"섹션: {section_title}" if section_title else "",
                f"URL: {response.url}",
                text,
            ]
            if part
        )
        return CreditcardGuidePage(
            source_type="crefia_creditcard_guide",
            guide_no=guide_no,
            title=title,
            section_title=section_title,
            url=response.url,
            target_path=target_path,
            links_json=json.dumps(links, ensure_ascii=False),
            image_urls_json=json.dumps(image_urls, ensure_ascii=False),
            image_alt_text="\n".join(image_alts),
            content=content,
            text_length=len(content),
            scrape_status="ok" if text else "empty",
        )
    except Exception as exc:
        return CreditcardGuidePage(
            source_type="crefia_creditcard_guide",
            guide_no=guide_no,
            title="",
            section_title="",
            url=url,
            target_path=target_path,
            links_json="[]",
            image_urls_json="[]",
            image_alt_text="",
            content="",
            text_length=0,
            scrape_status="error",
            error=f"{type(exc).__name__}: {exc}",
        )


def scrape_guides(start_url: str, timeout: int, retries: int, delay: float) -> list[CreditcardGuidePage]:
    session = make_session()
    urls = discover_guide_urls(session, start_url, timeout, retries, delay)
    pages: list[CreditcardGuidePage] = []
    for index, url in enumerate(urls, start=1):
        page = scrape_page(session, url, timeout, retries, delay)
        pages.append(page)
        safe_print(f"[crefia-guide] {index}/{len(urls)} {page.scrape_status}: {page.section_title or page.url}")
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


def build_corpus_rows(pages: list[CreditcardGuidePage]) -> list[dict[str, object]]:
    rows = []
    for page in pages:
        if page.scrape_status != "ok" or not page.content.strip():
            continue
        rows.append(
            {
                "doc_id": f"crefia_creditcard_guide_{page.guide_no:02d}",
                "source_type": page.source_type,
                "title": page.section_title or page.title,
                "path": "신용카드 이용자 가이드",
                "url": page.url,
                "guide_no": page.guide_no,
                "content": page.content,
                "char_count": len(page.content),
            }
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape CREFIA credit card user guide pages.")
    parser.add_argument("--start-url", default=DEFAULT_START_URL, help="Start URL")
    parser.add_argument("--out-dir", default="sources/bc_cs_notice/generated", help="Output directory")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")
    parser.add_argument("--retries", type=int, default=3, help="HTTP retry count")
    parser.add_argument("--delay", type=float, default=0.25, help="Delay between requests and retries")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    pages = scrape_guides(args.start_url, args.timeout, args.retries, args.delay)
    rows = [asdict(page) for page in pages]
    corpus_rows = build_corpus_rows(pages)

    base = out_dir / "crefia_creditcard_guide"
    write_csv(base.with_suffix(".csv"), rows, list(CreditcardGuidePage.__dataclass_fields__.keys()))
    write_jsonl(base.with_suffix(".jsonl"), rows)
    write_csv(
        out_dir / "crefia_creditcard_guide_corpus.csv",
        corpus_rows,
        ["doc_id", "source_type", "title", "path", "url", "guide_no", "content", "char_count"],
    )
    write_jsonl(out_dir / "crefia_creditcard_guide_corpus.jsonl", corpus_rows)

    ok_count = sum(1 for page in pages if page.scrape_status == "ok")
    safe_print(f"[crefia-guide] total={len(pages)} ok={ok_count} corpus={len(corpus_rows)}")
    safe_print(f"[crefia-guide] wrote {base.with_suffix('.csv')}")
    safe_print(f"[crefia-guide] wrote {base.with_suffix('.jsonl')}")
    safe_print(f"[crefia-guide] wrote {out_dir / 'crefia_creditcard_guide_corpus.csv'}")
    safe_print(f"[crefia-guide] wrote {out_dir / 'crefia_creditcard_guide_corpus.jsonl'}")


if __name__ == "__main__":
    main()


