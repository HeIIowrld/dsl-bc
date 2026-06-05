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


BASE_URL = "https://fine.fss.or.kr"
DEFAULT_LIST_URL = "https://fine.fss.or.kr/fine/bbs/B0000342/list.do?menuNo=900024"


@dataclass
class Newsletter:
    source_type: str
    board_id: str
    ntt_id: str
    title: str
    department: str
    date: str
    views: str
    list_url: str
    popup_url: str
    list_page: int
    image_urls_json: str
    image_alt_text: str
    area_links_json: str
    linked_docs_json: str
    popup_text: str
    content: str
    image_count: int
    link_count: int
    linked_doc_count: int
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
        match = re.search(r"/\s*(\d+)\s*페이지", count_text.get_text(" ", strip=True))
        if match:
            return int(match.group(1))
    values = []
    for anchor in soup.select(".pagination a[data-pageindex]"):
        value = anchor.get("data-pageindex")
        if value and value.isdigit():
            values.append(int(value))
    return max(values, default=1)


def parse_popup_id(href: str) -> str:
    match = re.search(r"popupList\(['\"]?(\d+)['\"]?\)", href or "")
    return match.group(1) if match else ""


def parse_list_page(
    session: requests.Session,
    list_url: str,
    page_index: int,
    timeout: int,
) -> tuple[list[dict[str, object]], int]:
    url = with_page_index(list_url, page_index)
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    max_page = max_page_from_list(soup)

    items: list[dict[str, object]] = []
    for row in soup.select("#content .bd-list tbody tr"):
        cells = row.find_all("td", recursive=False)
        anchor = row.select_one("td.title a[href]")
        if not anchor:
            continue
        ntt_id = parse_popup_id(anchor.get("href") or "")
        title = normalize_space(anchor.get_text(" ", strip=True))
        department = normalize_space(cells[2].get_text(" ", strip=True)) if len(cells) > 2 else ""
        date = normalize_space(cells[3].get_text(" ", strip=True)) if len(cells) > 3 else ""
        views = normalize_space(cells[4].get_text(" ", strip=True)) if len(cells) > 4 else ""
        popup_url = (
            f"{BASE_URL}/fine/bbs/B0000342/popupView.do"
            f"?viewType=CONTBODY&menuNo=900024&nttId={ntt_id}"
        )
        items.append(
            {
                "ntt_id": ntt_id,
                "title": title,
                "department": department,
                "date": date,
                "views": views,
                "list_url": response.url,
                "popup_url": popup_url,
                "list_page": page_index,
            }
        )
    return items, max_page


def is_followable_fss_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc not in {"www.fss.or.kr", "fine.fss.or.kr"}:
        return False
    return "/bbs/" in parsed.path and "/view.do" in parsed.path


def clean_page_text(soup: BeautifulSoup) -> str:
    node = soup.select_one("#content") or soup.select_one("main") or soup.body or soup
    for bad in node.select("script, style, noscript, iframe, object, embed, .pagination-set, .btnSet"):
        bad.decompose()
    for img in node.select("img"):
        alt = normalize_multiline(img.get("alt") or "")
        if alt:
            img.replace_with("\n" + alt + "\n")
        else:
            img.decompose()
    return normalize_multiline(node.get_text("\n", strip=True))


def scrape_linked_doc(session: requests.Session, url: str, timeout: int) -> dict[str, str]:
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        title = normalize_space(
            (soup.select_one("#content h2, #content .subject, main h1, title") or soup)
            .get_text(" ", strip=True)
        )
        text = clean_page_text(soup)
        return {"url": response.url, "title": title, "text": text[:6000], "status": "ok"}
    except Exception as exc:
        return {"url": url, "title": "", "text": "", "status": f"error: {type(exc).__name__}: {exc}"}


def parse_popup(
    session: requests.Session,
    item: dict[str, object],
    timeout: int,
    follow_links: bool,
    delay: float,
) -> Newsletter:
    try:
        popup_url = str(item["popup_url"])
        response = session.get(popup_url, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        image_urls = []
        image_alts = []
        for img in soup.select("img"):
            src = urljoin(response.url, img.get("src") or "")
            alt = normalize_multiline(img.get("alt") or "")
            if src:
                image_urls.append(src)
            if alt:
                image_alts.append(alt)

        area_links = []
        for area in soup.select("area[href]"):
            href = urljoin(response.url, area.get("href") or "")
            label = normalize_space(area.get("title") or area.get("alt") or "")
            area_links.append({"label": label, "url": href})

        linked_docs = []
        if follow_links:
            seen = set()
            for link in area_links:
                url = link["url"]
                if url in seen or not is_followable_fss_url(url):
                    continue
                seen.add(url)
                linked_docs.append(scrape_linked_doc(session, url, timeout))
                if delay:
                    time.sleep(delay)

        for bad in soup.select("script, style, map"):
            bad.decompose()
        popup_text = clean_page_text(soup)
        image_alt_text = "\n\n".join(image_alts)

        linked_text_parts = []
        for link in linked_docs:
            if link.get("status") == "ok":
                linked_text_parts.append(
                    "\n".join(
                        part
                        for part in [
                            f"링크 제목: {link.get('title', '')}",
                            f"링크 URL: {link.get('url', '')}",
                            link.get("text", ""),
                        ]
                        if part
                    )
                )

        content = "\n\n".join(
            part
            for part in [
                f"제목: {item.get('title', '')}",
                f"담당부서: {item.get('department', '')}",
                f"등록일: {item.get('date', '')}",
                "이미지 ALT:\n" + image_alt_text if image_alt_text else "",
                "이미지맵 링크:\n"
                + "\n".join(f"- {link['label']}: {link['url']}" for link in area_links)
                if area_links
                else "",
                "연결 문서 본문:\n" + "\n\n".join(linked_text_parts) if linked_text_parts else "",
            ]
            if part
        )

        return Newsletter(
            source_type="fine_newsletter",
            board_id="B0000342",
            ntt_id=str(item.get("ntt_id") or ""),
            title=str(item.get("title") or ""),
            department=str(item.get("department") or ""),
            date=str(item.get("date") or ""),
            views=str(item.get("views") or ""),
            list_url=str(item.get("list_url") or ""),
            popup_url=response.url,
            list_page=int(item.get("list_page") or 0),
            image_urls_json=json.dumps(image_urls, ensure_ascii=False),
            image_alt_text=image_alt_text,
            area_links_json=json.dumps(area_links, ensure_ascii=False),
            linked_docs_json=json.dumps(linked_docs, ensure_ascii=False),
            popup_text=popup_text,
            content=content,
            image_count=len(image_urls),
            link_count=len(area_links),
            linked_doc_count=sum(1 for doc in linked_docs if doc.get("status") == "ok"),
            text_length=len(content),
            scrape_status="ok" if content else "empty",
        )
    except Exception as exc:
        return Newsletter(
            source_type="fine_newsletter",
            board_id="B0000342",
            ntt_id=str(item.get("ntt_id") or ""),
            title=str(item.get("title") or ""),
            department=str(item.get("department") or ""),
            date=str(item.get("date") or ""),
            views=str(item.get("views") or ""),
            list_url=str(item.get("list_url") or ""),
            popup_url=str(item.get("popup_url") or ""),
            list_page=int(item.get("list_page") or 0),
            image_urls_json="[]",
            image_alt_text="",
            area_links_json="[]",
            linked_docs_json="[]",
            popup_text="",
            content="",
            image_count=0,
            link_count=0,
            linked_doc_count=0,
            text_length=0,
            scrape_status="error",
            error=f"{type(exc).__name__}: {exc}",
        )


def write_rows(rows: list[Newsletter], csv_path: Path, jsonl_path: Path) -> None:
    fieldnames = list(asdict(rows[0]).keys()) if rows else list(Newsletter.__annotations__)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
    with jsonl_path.open("w", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")


def write_corpus(rows: list[Newsletter], csv_path: Path, jsonl_path: Path) -> None:
    corpus = []
    for index, row in enumerate([r for r in rows if r.scrape_status == "ok" and r.content], start=1):
        corpus.append(
            {
                "doc_id": f"fine_newsletter_{index:05d}",
                "source_type": row.source_type,
                "title": row.title,
                "path": "파인 > 뉴스레터",
                "url": row.popup_url,
                "ntt_id": row.ntt_id,
                "content": row.content,
                "char_count": len(row.content),
            }
        )
    fieldnames = list(corpus[0].keys()) if corpus else [
        "doc_id",
        "source_type",
        "title",
        "path",
        "url",
        "ntt_id",
        "content",
        "char_count",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(corpus)
    with jsonl_path.open("w", encoding="utf-8") as fp:
        for row in corpus:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape FINE newsletter list and popup contents.")
    parser.add_argument("--list-url", default=DEFAULT_LIST_URL)
    parser.add_argument("--out-dir", default="sources/bc_cs_notice/generated")
    parser.add_argument("--delay", type=float, default=0.03)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--no-follow-links", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    session = make_session()
    first_items, max_page = parse_list_page(session, args.list_url, 1, args.timeout)
    items = first_items[:]
    print(f"max_page={max_page} first_page_items={len(first_items)}")
    for page_index in range(2, max_page + 1):
        page_items, _ = parse_list_page(session, args.list_url, page_index, args.timeout)
        items.extend(page_items)
        print(f"[list {page_index}/{max_page}] cumulative={len(items)}")
        if args.delay:
            time.sleep(args.delay)

    if args.limit:
        items = items[: args.limit]

    rows: list[Newsletter] = []
    seen = set()
    unique_items = []
    for item in items:
        ntt_id = str(item.get("ntt_id") or "")
        if ntt_id in seen:
            continue
        seen.add(ntt_id)
        unique_items.append(item)

    for index, item in enumerate(unique_items, start=1):
        row = parse_popup(
            session=session,
            item=item,
            timeout=args.timeout,
            follow_links=not args.no_follow_links,
            delay=args.delay,
        )
        rows.append(row)
        print(
            f"[popup {index:03d}/{len(unique_items):03d}] "
            f"{row.scrape_status:5s} imgs={row.image_count:02d} links={row.link_count:02d} "
            f"docs={row.linked_doc_count:02d} {row.title}"
        )
        if args.delay:
            time.sleep(args.delay)

    raw_csv = out_dir / "fine_newsletter.csv"
    raw_jsonl = out_dir / "fine_newsletter.jsonl"
    corpus_csv = out_dir / "fine_newsletter_corpus.csv"
    corpus_jsonl = out_dir / "fine_newsletter_corpus.jsonl"
    write_rows(rows, raw_csv, raw_jsonl)
    write_corpus(rows, corpus_csv, corpus_jsonl)

    summary = {}
    for row in rows:
        summary[row.scrape_status] = summary.get(row.scrape_status, 0) + 1
    print("\nSummary")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"CSV:    {raw_csv}")
    print(f"JSONL:  {raw_jsonl}")
    print(f"Corpus: {corpus_csv}")
    print(f"Corpus: {corpus_jsonl}")


if __name__ == "__main__":
    main()


