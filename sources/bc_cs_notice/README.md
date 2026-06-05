# BC/FINE/CREFIA Crawling Corpus

사내 LLM 회귀테스트용 데이터베이스를 만들기 위한 크롤링 작업 디렉토리입니다.

## Directory Layout

- `scripts/`: 출처별 크롤링 스크립트와 통합 corpus 생성 스크립트
- `scripts/legacy/`: 현재 통합 파이프라인의 기본 경로에서는 빠졌지만 과거 수집 재현에 필요할 수 있는 크롤러
- `corpus/`: 현재 설정에서 참조하는 통합 corpus
- `generated/`: 크롤러를 다시 실행할 때 쓰는 기본 산출물 디렉터리(git 제외)

## Main Output

- `corpus/llm_regression_all_sources.jsonl`

## Pipeline

1. `scripts/scrape_bc_links_from_html.py`
   - BC카드 고객센터 저장 HTML 기반 링크/게시판/FAQ 수집
2. `scripts/scrape_fine_life_finance_talk_all.py`
   - FINE 생활금융톡톡 전체 수집
3. `scripts/scrape_fine_newsletter.py`
   - FINE 뉴스레터 수집
4. `scripts/scrape_fine_financial_dictionary.py`
   - FINE 금융용어사전 수집
5. `scripts/scrape_fine_prc_step_info.py`
   - FINE 금융상품 거래 단계별 핵심정보 수집
6. `scripts/scrape_crefia_creditcard_guide.py`
   - 여신금융협회 신용카드 이용자 가이드 수집
7. `scripts/scrape_crefia_creditcard_faq.py`
   - 여신금융협회 신용카드 FAQ 수집
8. `scripts/build_llm_regression_corpus_all.py`
   - 전체 corpus 통합

## Usage

이전 크롤링 노트북과 원천 수집 산출물은 `_unused_files/20260524_dev_cleanup/sources/bc_cs_notice/` 아래에 보관했습니다.

BC카드 저장 HTML 기반 재수집이 필요하면 크롤링 스크립트의 기본 `--out-dir`인 `sources/bc_cs_notice/generated`에 산출물을 만든 뒤, 필요한 통합 corpus만 `corpus/`로 승격하세요.

통합 corpus만 다시 만들려면:

```powershell
& 'C:\rdna4-rocm-clean\Scripts\python.exe' .\sources\bc_cs_notice\scripts\build_llm_regression_corpus_all.py
```

최종 활성 corpus로 반영할 때는 생성된 `generated/llm_regression_all_sources.jsonl`을 검토한 뒤 `corpus/llm_regression_all_sources.jsonl`로 교체합니다.

