# Data Directory

`data/`는 모델 평가에 필요한 대용량 원천과 보관본만 둡니다. 생성된 질문셋과 평가 케이스는 `questionlist/`와 `out/test_cases/`가 기준 위치입니다.

## Current Layout

| Path | Role | Notes |
| --- | --- | --- |
| `raw/sample_data/` | 외부 샘플 원천 데이터 | MRC/OCR/법률/약관 등 대용량 JSON, 이미지, XML 원천입니다. `scripts/eval/build_sample_data_cases.py`가 사용합니다. |
| `raw/card_product/` | 카드/상품 CSV 원천 데이터 | 현재는 50개 더미 QA row가 있으며, 실제 카드 상품 CSV가 들어오면 `scripts/eval/build_card_product_cases.py`로 바로 JSONL 케이스를 생성합니다. |
| `archive/old/` | 이전 실험/캐시 보관본 | `BCAI-Finance-Kor-1862K`, chunk zip, parquet cache, PDF 등 재현용 보관 자료입니다. 기본 파이프라인에서는 직접 사용하지 않습니다. |

## Moved Out

| Previous Path | New Path | Reason |
| --- | --- | --- |
| `data/bc_cs_notice/` | `sources/bc_cs_notice/` | 활성 크롤링 corpus와 수집 스크립트는 source package로 분리했습니다. |
| `data/샘플데이터/` | `data/raw/sample_data/` | 대용량 원천은 `data/raw` 아래로 모았습니다. 스크립트는 새 경로와 구 경로를 모두 탐색합니다. |
| `data/old/` | `data/archive/old/` | 현재 파이프라인의 활성 입력이 아닌 예전 raw/cache를 archive로 분리했습니다. |

## Question Sets

질문셋/회귀테스트 케이스의 기준 위치는 다음입니다.

- 원본 확장 질문셋: `questionlist/`
- 실행용 테스트 케이스: `out/test_cases/`
- 웹 UI가 노출하는 데이터셋: `final_UI/server.py`의 `QUESTIONLIST_DATASET_FILES`

자세한 목록은 `data/QUESTION_SETS.md`를 보세요.
