from __future__ import annotations

import argparse
import csv
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://customer.crefia.or.kr"
DEFAULT_LIST_URL = "https://customer.crefia.or.kr/customer/board/boardDataList.do?boardid=bbs007"


@dataclass
class CreditcardFaqItem:
    source_type: str
    board_id: str
    data_id: str
    number: str
    category: str
    title: str
    date: str
    list_page: int
    list_url: str
    detail_url: str
    attachments_json: str
    page_text: str
    content: str
    text_length: int
    scrape_status: str
    error: str = ""


def safe_print(message: str) -> None:
    print(message.encode("cp949", errors="replace").decode("cp949"))


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
            "Referer": DEFAULT_LIST_URL,
        }
    )
    return session


def request_with_retry(
    session: requests.Session,
    url: str,
    timeout: int,
    retries: int,
    delay: float,
    params: dict[str, object] | None = None,
) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            response = session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(delay * (attempt + 1))
    raise last_error or RuntimeError("request failed")


def with_query_params(url: str, **updates: object) -> str:
    parsed = urlparse(url)
    query = {key: values[-1] for key, values in parse_qs(parsed.query, keep_blank_values=True).items()}
    for key, value in updates.items():
        query[key] = str(value)
    return urlunparse(parsed._replace(query=urlencode(query)))


def max_page_from_soup(soup: BeautifulSoup) -> int:
    text = normalize_space((soup.select_one("#contents") or soup).get_text(" ", strip=True))
    match = re.search(r"\d+\s*/\s*(\d+)\s*페이지", text)
    if match:
        return int(match.group(1))
    pages = []
    for anchor in soup.select("a[href]"):
        match = re.search(r"fn_search\(['\"]?(\d+)['\"]?\)", anchor.get("href") or "")
        if match:
            pages.append(int(match.group(1)))
    return max(pages, default=1)


def parse_list_page(
    session: requests.Session,
    list_url: str,
    page: int,
    timeout: int,
    retries: int,
    delay: float,
) -> tuple[list[dict[str, str]], int, str]:
    response = request_with_retry(session, with_query_params(list_url, boardid="bbs007", page=page), timeout, retries, delay)
    soup = BeautifulSoup(response.text, "lxml")
    max_page = max_page_from_soup(soup)
    items: list[dict[str, str]] = []
    for row in soup.select("#contents table tr"):
        hidden_id = row.select_one("input[name=id]")
        cells = [normalize_space(td.get_text(" ", strip=True)) for td in row.find_all("td")]
        if not hidden_id or len(cells) < 3:
            continue
        data_id = hidden_id.get("value") or ""
        title_anchor = row.select_one("a")
        title = normalize_space(title_anchor.get_text(" ", strip=True) if title_anchor else cells[2])
        items.append(
            {
                "data_id": data_id,
                "number": cells[0],
                "category": cells[1],
                "title": title,
                "list_page": str(page),
                "list_url": response.url,
                "detail_url": f"{BASE_URL}/customer/board/boardDataDetail.do?boardid=bbs007&dataid={data_id}&page={page}",
            }
        )
    return items, max_page, response.url


def extract_detail_text_and_attachments(soup: BeautifulSoup, response_url: str) -> tuple[str, str, str, list[dict[str, str]]]:
    contents = soup.select_one("#contents") or soup.body or soup
    node = BeautifulSoup(str(contents), "lxml")
    for bad in node.select("script, style, noscript, iframe, .location_wrap, .btn_wrap, button"):
        bad.decompose()
    for img in node.select("img"):
        alt = normalize_multiline(img.get("alt") or "")
        if alt:
            img.replace_with("\n" + alt + "\n")
        else:
            img.decompose()

    attachments: list[dict[str, str]] = []
    for anchor in node.select("a[onclick], a[href]"):
        label = normalize_space(anchor.get_text(" ", strip=True))
        onclick = anchor.get("onclick") or ""
        href = anchor.get("href") or ""
        if "fn_downloadFile" in onclick:
            filename_match = re.search(r"fn_downloadFile\(['\"](.+?)['\"]", onclick)
            filename = filename_match.group(1) if filename_match else label
            attachments.append({"filename": filename, "label": label, "onclick": onclick})
        elif href and not href.startswith(("#", "javascript:")):
            attachments.append({"filename": label, "label": label, "url": urljoin(response_url, href)})

    text = normalize_multiline(node.get_text("\n", strip=True))
    lines = text.splitlines()
    category = lines[1] if len(lines) > 1 and lines[0] == "HOME" else ""
    title = lines[2] if len(lines) > 2 and lines[0] == "HOME" else ""
    date = ""
    for line in lines[:8]:
        if re.match(r"\d{4}\.\d{2}\.\d{2}", line):
            date = line
            break
    return text, title, date, attachments


def scrape_detail(
    session: requests.Session,
    item: dict[str, str],
    timeout: int,
    retries: int,
    delay: float,
) -> CreditcardFaqItem:
    try:
        response = request_with_retry(session, item["detail_url"], timeout, retries, delay)
        soup = BeautifulSoup(response.text, "lxml")
        page_text, detail_title, date, attachments = extract_detail_text_and_attachments(soup, response.url)
        title = detail_title or item["title"]
        category = item["category"]

        content_parts = [
            f"제목: {title}",
            f"분류: {category}" if category else "",
            f"작성일: {date}" if date else "",
            f"URL: {response.url}",
            page_text,
        ]
        if attachments:
            content_parts.append(
                "첨부파일:\n"
                + "\n".join(f"- {attachment.get('filename') or attachment.get('label')}" for attachment in attachments)
            )
        content = "\n".join(part for part in content_parts if part)

        return CreditcardFaqItem(
            source_type="crefia_creditcard_faq",
            board_id="bbs007",
            data_id=item["data_id"],
            number=item["number"],
            category=category,
            title=title,
            date=date,
            list_page=int(item["list_page"]),
            list_url=item["list_url"],
            detail_url=response.url,
            attachments_json=json.dumps(attachments, ensure_ascii=False),
            page_text=page_text,
            content=content,
            text_length=len(content),
            scrape_status="ok" if page_text else "empty",
        )
    except Exception as exc:
        return CreditcardFaqItem(
            source_type="crefia_creditcard_faq",
            board_id="bbs007",
            data_id=item.get("data_id", ""),
            number=item.get("number", ""),
            category=item.get("category", ""),
            title=item.get("title", ""),
            date="",
            list_page=int(item.get("list_page", 0) or 0),
            list_url=item.get("list_url", ""),
            detail_url=item.get("detail_url", ""),
            attachments_json="[]",
            page_text="",
            content="",
            text_length=0,
            scrape_status="error",
            error=f"{type(exc).__name__}: {exc}",
        )


def scrape_faq(list_url: str, timeout: int, retries: int, delay: float, limit_pages: int | None) -> list[CreditcardFaqItem]:
    session = make_session()
    first_items, max_page, _ = parse_list_page(session, list_url, 1, timeout, retries, delay)
    total_pages = min(max_page, limit_pages) if limit_pages else max_page
    list_items = first_items
    safe_print(f"[crefia-faq] page 1/{total_pages}: {len(first_items)} rows")
    for page in range(2, total_pages + 1):
        page_items, _, _ = parse_list_page(session, list_url, page, timeout, retries, delay)
        list_items.extend(page_items)
        safe_print(f"[crefia-faq] page {page}/{total_pages}: {len(page_items)} rows")
        if delay:
            time.sleep(delay)

    results: list[CreditcardFaqItem] = []
    for index, item in enumerate(list_items, start=1):
        result = scrape_detail(session, item, timeout, retries, delay)
        results.append(result)
        safe_print(f"[crefia-faq] detail {index}/{len(list_items)} {result.scrape_status}: {result.title}")
        if delay:
            time.sleep(delay)
    return results


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


def build_corpus_rows(items: list[CreditcardFaqItem]) -> list[dict[str, object]]:
    rows = []
    for item in items:
        if item.scrape_status != "ok" or not item.content.strip():
            continue
        rows.append(
            {
                "doc_id": f"crefia_creditcard_faq_{item.data_id}",
                "source_type": item.source_type,
                "title": item.title,
                "path": item.category,
                "url": item.detail_url,
                "data_id": item.data_id,
                "content": item.content,
                "char_count": len(item.content),
            }
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape CREFIA credit card FAQ board.")
    parser.add_argument("--url", default=DEFAULT_LIST_URL, help="FAQ board list URL")
    parser.add_argument("--out-dir", default="sources/bc_cs_notice/generated", help="Output directory")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")
    parser.add_argument("--retries", type=int, default=4, help="HTTP retry count")
    parser.add_argument("--delay", type=float, default=0.15, help="Delay between requests and retries")
    parser.add_argument("--limit-pages", type=int, default=None, help="Limit page count for testing")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    items = scrape_faq(args.url, args.timeout, args.retries, args.delay, args.limit_pages)
    rows = [asdict(item) for item in items]
    corpus_rows = build_corpus_rows(items)

    base = out_dir / "crefia_creditcard_faq"
    write_csv(base.with_suffix(".csv"), rows, list(CreditcardFaqItem.__dataclass_fields__.keys()))
    write_jsonl(base.with_suffix(".jsonl"), rows)
    write_csv(
        out_dir / "crefia_creditcard_faq_corpus.csv",
        corpus_rows,
        ["doc_id", "source_type", "title", "path", "url", "data_id", "content", "char_count"],
    )
    write_jsonl(out_dir / "crefia_creditcard_faq_corpus.jsonl", corpus_rows)

    ok_count = sum(1 for item in items if item.scrape_status == "ok")
    safe_print(f"[crefia-faq] total={len(items)} ok={ok_count} corpus={len(corpus_rows)}")
    safe_print(f"[crefia-faq] wrote {base.with_suffix('.csv')}")
    safe_print(f"[crefia-faq] wrote {base.with_suffix('.jsonl')}")
    safe_print(f"[crefia-faq] wrote {out_dir / 'crefia_creditcard_faq_corpus.csv'}")
    safe_print(f"[crefia-faq] wrote {out_dir / 'crefia_creditcard_faq_corpus.jsonl'}")


if __name__ == "__main__":
    main()


