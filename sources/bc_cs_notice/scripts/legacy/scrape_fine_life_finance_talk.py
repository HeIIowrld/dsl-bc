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
DEFAULT_LIST_URL = (
    "https://fine.fss.or.kr/fine/bbs/B0000341/list.do"
    "?menuNo=900023&pageIndex=1"
)


@dataclass
class FinePost:
    source_type: str
    board_id: str
    ntt_id: str
    category: str
    title: str
    department: str
    author: str
    date: str
    views: str
    url: str
    list_page: int
    attachments_json: str
    image_urls_json: str
    page_text: str
    image_alt_text: str
    content: str
    image_count: int
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
        }
    )
    return session


def max_page_from_list(soup: BeautifulSoup) -> int:
    end_values: list[int] = []
    for anchor in soup.select(".pagination-set a[data-endpage], .pagination a[data-endpage]"):
        value = anchor.get("data-endpage")
        if value and value.isdigit():
            end_values.append(int(value))
    if end_values:
        return max(end_values)

    count_text = soup.select_one(".count-total")
    if count_text:
        match = re.search(r"/\s*(\d+)\s*페이지", count_text.get_text(" ", strip=True))
        if match:
            return int(match.group(1))

    values: list[int] = []
    for anchor in soup.select(".pagination-set a[data-pageindex], .pagination a[data-pageindex]"):
        value = anchor.get("data-pageindex")
        if value and value.isdigit():
            values.append(int(value))
    return max(values, default=1)


def get_query_id(url: str, key: str) -> str:
    return (parse_qs(urlparse(url).query).get(key) or [""])[0]


def with_page_index(url: str, page_index: int) -> str:
    parsed = urlparse(url)
    query = {key: values[-1] for key, values in parse_qs(parsed.query, keep_blank_values=True).items()}
    query["pageIndex"] = str(page_index)
    return urlunparse(parsed._replace(query=urlencode(query)))


def parse_list_page(
    session: requests.Session,
    list_url: str,
    page_index: int,
    timeout: int,
) -> tuple[list[dict[str, object]], int]:
    response = session.get(with_page_index(list_url, page_index), timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    max_page = max_page_from_list(soup)

    items: list[dict[str, object]] = []
    for row in soup.select("#content .bd-list tbody tr"):
        cells = row.find_all("td", recursive=False)
        title_anchor = row.select_one("td.title a[href]")
        if not title_anchor:
            continue
        detail_url = urljoin(response.url, title_anchor.get("href") or "")
        title = normalize_space(title_anchor.get_text(" ", strip=True))
        category = normalize_space(cells[1].get_text(" ", strip=True)) if len(cells) > 1 else ""
        department = normalize_space(cells[3].get_text(" ", strip=True)) if len(cells) > 3 else ""
        date = normalize_space(cells[4].get_text(" ", strip=True)) if len(cells) > 4 else ""
        views = normalize_space(cells[-1].get_text(" ", strip=True)) if cells else ""

        attachments = []
        for attach in row.select(".file-group a[href]"):
            name = normalize_space(attach.get_text(" ", strip=True))
            href = urljoin(response.url, attach.get("href") or "")
            if name or href:
                attachments.append({"name": name, "url": href})

        items.append(
            {
                "ntt_id": get_query_id(detail_url, "nttId"),
                "category": category,
                "title": title,
                "department": department,
                "date": date,
                "views": views,
                "url": detail_url,
                "list_page": page_index,
                "attachments": attachments,
            }
        )

    return items, max_page


def metadata_from_detail(content: BeautifulSoup) -> dict[str, str]:
    meta: dict[str, str] = {}
    for dl in content.select(".bd-view > dl"):
        dts = dl.find_all("dt", recursive=False)
        dds = dl.find_all("dd", recursive=False)
        for dt, dd in zip(dts, dds):
            key = normalize_space(dt.get_text(" ", strip=True))
            val = normalize_space(dd.get_text(" ", strip=True))
            if key:
                meta[key] = val
    return meta


def parse_detail_page(
    session: requests.Session,
    item: dict[str, object],
    timeout: int,
) -> FinePost:
    try:
        url = str(item["url"])
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        content = soup.select_one("#content") or soup.body or soup
        title = normalize_space(
            (content.select_one(".bd-view .subject") or content.select_one("h2") or soup.title)
            .get_text(" ", strip=True)
        )
        meta = metadata_from_detail(content)

        for node in content.select("script, style, noscript, .file-group__set, .btnSet, .pagination-set"):
            node.decompose()

        image_urls: list[str] = []
        image_alts: list[str] = []
        for img in content.select("img"):
            src = urljoin(response.url, img.get("src") or "")
            alt = normalize_multiline(img.get("alt") or "")
            if "ajax-loader" in src:
                img.decompose()
                continue
            if src:
                image_urls.append(src)
            if alt:
                image_alts.append(alt)
            img.decompose()

        page_text = normalize_multiline(content.get_text("\n", strip=True))
        image_alt_text = "\n\n".join(image_alts)

        parts = [
            f"제목: {title}",
            f"분류: {item.get('category') or ''}".strip(),
            f"담당부서: {meta.get('담당부서') or item.get('department') or ''}".strip(),
            f"등록일: {meta.get('등록일') or item.get('date') or ''}".strip(),
            image_alt_text,
        ]
        content_text = "\n".join(part for part in parts if part and not part.endswith(":"))

        return FinePost(
            source_type="fine_life_finance_talk",
            board_id="B0000341",
            ntt_id=str(item.get("ntt_id") or get_query_id(url, "nttId")),
            category=str(item.get("category") or ""),
            title=title or str(item.get("title") or ""),
            department=meta.get("담당부서") or str(item.get("department") or ""),
            author=meta.get("담당자") or "",
            date=meta.get("등록일") or str(item.get("date") or ""),
            views=meta.get("조회수") or str(item.get("views") or ""),
            url=response.url,
            list_page=int(item.get("list_page") or 0),
            attachments_json=json.dumps(item.get("attachments") or [], ensure_ascii=False),
            image_urls_json=json.dumps(image_urls, ensure_ascii=False),
            page_text=page_text,
            image_alt_text=image_alt_text,
            content=content_text,
            image_count=len(image_urls),
            text_length=len(content_text),
            scrape_status="ok" if content_text else "empty",
        )
    except Exception as exc:
        return FinePost(
            source_type="fine_life_finance_talk",
            board_id="B0000341",
            ntt_id=str(item.get("ntt_id") or ""),
            category=str(item.get("category") or ""),
            title=str(item.get("title") or ""),
            department=str(item.get("department") or ""),
            author="",
            date=str(item.get("date") or ""),
            views=str(item.get("views") or ""),
            url=str(item.get("url") or ""),
            list_page=int(item.get("list_page") or 0),
            attachments_json=json.dumps(item.get("attachments") or [], ensure_ascii=False),
            image_urls_json="[]",
            page_text="",
            image_alt_text="",
            content="",
            image_count=0,
            text_length=0,
            scrape_status="error",
            error=f"{type(exc).__name__}: {exc}",
        )


def write_rows(rows: list[FinePost], csv_path: Path, jsonl_path: Path) -> None:
    fieldnames = list(asdict(rows[0]).keys()) if rows else list(FinePost.__annotations__)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))
    with jsonl_path.open("w", encoding="utf-8") as fp:
        for row in rows:
            fp.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")


def write_corpus(rows: list[FinePost], csv_path: Path, jsonl_path: Path) -> None:
    corpus = []
    for index, row in enumerate([row for row in rows if row.scrape_status == "ok" and row.content], start=1):
        corpus.append(
            {
                "doc_id": f"fine_talk_{index:05d}",
                "source_type": row.source_type,
                "title": row.title,
                "path": f"파인 > 생활금융톡톡 > {row.category}",
                "url": row.url,
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
    parser = argparse.ArgumentParser(
        description="Scrape FINE 생활금융톡톡 posts and image-alt text."
    )
    parser.add_argument("--list-url", default=DEFAULT_LIST_URL)
    parser.add_argument("--out-dir", default="sources/bc_cs_notice/generated")
    parser.add_argument("--delay", type=float, default=0.05)
    parser.add_argument("--timeout", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    session = make_session()
    first_items, max_page = parse_list_page(session, args.list_url, 1, args.timeout)
    list_items = first_items[:]
    print(f"max_page={max_page} first_page_items={len(first_items)}")

    for page_index in range(2, max_page + 1):
        items, _ = parse_list_page(session, args.list_url, page_index, args.timeout)
        list_items.extend(items)
        print(f"[list {page_index}/{max_page}] cumulative={len(list_items)}")
        if args.delay:
            time.sleep(args.delay)

    seen: set[str] = set()
    unique_items = []
    for item in list_items:
        ntt_id = str(item.get("ntt_id") or item.get("url") or "")
        if ntt_id in seen:
            continue
        seen.add(ntt_id)
        unique_items.append(item)

    rows: list[FinePost] = []
    for index, item in enumerate(unique_items, start=1):
        row = parse_detail_page(session, item, args.timeout)
        rows.append(row)
        print(
            f"[detail {index:03d}/{len(unique_items):03d}] "
            f"{row.scrape_status:5s} images={row.image_count:02d} {row.title}"
        )
        if args.delay:
            time.sleep(args.delay)

    raw_csv = out_dir / "fine_life_finance_talk_cl1Cd7.csv"
    raw_jsonl = out_dir / "fine_life_finance_talk_cl1Cd7.jsonl"
    corpus_csv = out_dir / "fine_life_finance_talk_cl1Cd7_corpus.csv"
    corpus_jsonl = out_dir / "fine_life_finance_talk_cl1Cd7_corpus.jsonl"
    write_rows(rows, raw_csv, raw_jsonl)
    write_corpus(rows, corpus_csv, corpus_jsonl)

    summary: dict[str, int] = {}
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


