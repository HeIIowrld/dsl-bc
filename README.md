# LLM Regression & Benchmark Evaluation Platform

로컬 모델, 사내 모델, 외부 API 모델을 같은 평가 포맷에 올려놓고 **회귀테스트, 벤치마크, Judge 기반 품질 평가**를 수행하는 LLM 평가 플랫폼입니다.

사용자가 보유한 모델과 평가 데이터를 직접 연결해 모델 변경 전후의 성능 차이와 답변 품질을 반복적으로 검증하기 위한 파이프라인입니다. 데이터셋, 모델 설정, Judge 기준, 프롬프트를 교체하면 QA, 상담, RAG, 업무 자동화, 사내 지식검색 등 다양한 도메인의 모델 평가에 사용할 수 있습니다.

---

## Repository Description

```text
A local LLM regression and benchmark evaluation pipeline with model onboarding,
cached answer generation, multi-judge scoring, conflict review, and dashboard-based
result inspection.
```

한국어 소개:

```text
로컬/사내/외부 LLM을 연결해 회귀테스트, 벤치마크, Judge 채점, 결과 대시보드까지 실행하는 모델 평가 플랫폼입니다.
```

---

## Overview

이 플랫폼은 LLM 평가 과정을 다음 흐름으로 자동화합니다.

```text
평가 데이터 준비
      ↓
모델 설정 등록
      ↓
모델 답변 생성
      ↓
답변 저장 및 캐싱
      ↓
Judge 모델 채점
      ↓
복수 Judge 결과 병합
      ↓
충돌 케이스 검토
      ↓
웹 대시보드에서 결과 확인
```

주요 목적은 다음과 같습니다.

- 모델 버전 변경 후 품질이 떨어졌는지 확인하는 회귀테스트
- 여러 모델을 동일한 질문 세트로 비교하는 벤치마크
- 답변 생성과 Judge 채점을 분리한 재현 가능한 평가
- 정확성, 완결성, 수치 정확성, 환각 여부를 분리한 품질 진단
- 평가 결과를 로컬 UI에서 확인하고 비교하는 운영형 평가 환경 구축

---

## Key Features

- 여러 모델을 동일한 평가 데이터로 비교
- 로컬 Ollama 모델, 외부 API 모델, 사내 HTTP 모델 연동 가능
- 답변 생성 단계와 Judge 채점 단계 분리
- 저장된 답변 재사용을 통한 반복 채점 지원
- 복수 Judge 모델 평가 및 충돌 검토 지원
- Judge별 비중 입력 및 복수 Judge 합산 방식 선택 지원
- Benchmark / Regression 데이터셋 분리 운영
- 평가 결과 확인용 로컬 웹 대시보드 제공
- YAML/JSON 기반 모델 및 평가 설정 관리
- JSON Schema 기반 데이터 구조 검증
- 주요 파이프라인 단위 테스트 제공

---

## Use Cases

### 1. 모델 회귀테스트

기존 모델을 새 버전으로 교체하기 전에 동일한 회귀 테스트셋을 실행해 품질 저하 여부를 확인합니다.

```text
기존 모델 v1 답변 생성
새 모델 v2 답변 생성
Judge 점수 비교
실패 케이스 확인
배포 여부 판단
```

회귀테스트는 다음과 같은 상황에서 특히 유용합니다.

- 모델 버전 교체
- 프롬프트 수정
- RAG 검색 설정 변경
- 후처리 로직 변경
- 배포 전 품질 검증

### 2. 모델 벤치마크

여러 모델을 동일한 질문 세트에 대해 실행하고 결과를 비교합니다.

```text
model_a
model_b
model_c
```

각 모델의 답변을 생성한 뒤 동일한 Judge 기준으로 채점하여 모델별 품질을 비교할 수 있습니다.

### 3. Judge 평가 실험

동일한 모델 답변을 여러 Judge 모델로 채점하고, Judge 간 평가 차이를 확인할 수 있습니다.

```text
Judge A
Judge B
Judge C
Local Judge
Custom Judge
```

Judge 결과가 서로 다른 케이스는 conflict review 대상으로 분리할 수 있습니다.

### 4. RAG / Evidence 기반 모델 평가

검색 근거를 사용하는 모델의 경우 답변 정확도뿐 아니라 evidence 활용 여부까지 별도로 평가할 수 있습니다.

```text
질문
근거 문서
모델 답변
Judge 평가
Evidence 활용 여부
```

---

## Project Structure

```text
.
├─ config/          모델 레지스트리, 평가 설정, 분류 설정
├─ docs/            설계, 운영, 채점 기준 문서
├─ final_UI/        평가 결과 확인용 로컬 웹 대시보드와 API 서버
├─ questionlist/    Benchmark / Regression 실행 문항
├─ schemas/         데이터 구조 검증용 JSON Schema
├─ scripts/         평가 실행, Judge 채점, 점검 스크립트
└─ tests/           주요 파이프라인 단위 테스트
```

업로드본에는 평가 데이터와 실행 결과를 넣을 위치가 미리 만들어져 있습니다. 각 환경에서 준비한 파일을 아래 폴더에 채워 넣고 실행하면 됩니다.

| 폴더 | 넣을 내용 |
| --- | --- |
| `data/` | 로컬 메타데이터, 보조 입력 파일 |
| `questionlist/benchmark/` | 벤치마크 평가 문항 CSV 또는 JSONL |
| `questionlist/regression/` | 회귀테스트 평가 문항 CSV 또는 JSONL |
| `final_UI/data/` | 대시보드에서 바로 읽을 CSV/JSON 데이터 |

`final_UI/data/`의 모델 등록 파일은 역할별로 분리됩니다. `registered_target_models.json`은 답변을 생성하고 비교할 대상 모델을 저장하고, `registered_judge_models.json`은 채점 전용 Judge/Arbiter 모델을 저장합니다. repo에 함께 제공하는 seed 대상 모델은 `config/seeded_target_models.yaml`에 둡니다.

원천 수집 자료, 모델 제작 노트북, raw 데이터, 실행 결과, API key, 개인 환경 파일은 공유용 runtime package에서 제외합니다. 이 작업 중 분리한 개발 자료는 로컬 `_unused_files/runtime_cleanup_20260606/` 아래에 보관했습니다.

---

## Quick Start

Windows PowerShell에서 저장소 루트 기준으로 실행합니다.

의존성을 먼저 설치합니다.

```powershell
python -m pip install -r .\requirements.txt
```

UI 흐름 감사 스크립트(`scripts/audit_final_ui_flow.py`)까지 실행하려면 Playwright 브라우저도 한 번 설치합니다.

```powershell
python -m playwright install chromium
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_final_ui.ps1 -Port 8512 -StopExisting
```

브라우저에서 다음 주소로 접속합니다.

```text
http://localhost:8512
```

평가 결과 데이터가 아직 없는 경우에도 UI는 실행됩니다. 다만 로컬 실행 결과가 없으면 결과 화면은 비어 있거나 안내 문구만 표시될 수 있습니다.

---

## External Access

다른 기기에서 UI에 접속해야 하는 경우 공개 바인딩으로 실행할 수 있습니다. 공개 바인딩을 사용할 때는 반드시 인증 정보를 먼저 설정합니다.

```powershell
$env:FINAL_UI_AUTH_USERS = "admin:your-password:admin"

powershell -ExecutionPolicy Bypass -File .\scripts\run_final_ui.ps1 `
  -Port 8512 `
  -HostName 0.0.0.0 `
  -StopExisting
```

브라우저에서 서버 IP와 포트를 사용해 접속합니다.

```text
http://{server-ip}:8512
```

---

## Environment Variables

API key와 접속 정보는 `.env` 또는 실행 환경 변수로 관리합니다.

| 이름 | 용도 |
| --- | --- |
| `FINAL_UI_AUTH_USERS` | UI 로그인 계정. 예: `admin:password:admin,user:password:user` |
| `FINAL_UI_AUTH_TOKEN` | 토큰 기반 관리자 접근 |
| `FINAL_UI_AUTH_DISABLED` | 로컬 개발용 인증 비활성화 |
| `OLLAMA_BASE_URL` | Ollama 서버 주소. 기본값: `http://afsd.iptime.org:11434` |
| `CLOVA_STUDIO_API_KEY` | CLOVA Studio 모델 또는 Judge 호출용 API key |
| `OPENAI_API_KEY` | OpenAI 모델 또는 Judge 호출용 API key |

예시:

```powershell
$env:OLLAMA_BASE_URL = "http://afsd.iptime.org:11434"
$env:OPENAI_API_KEY = "your-openai-api-key"
$env:CLOVA_STUDIO_API_KEY = "your-clova-api-key"
```

---

## Model Onboarding

이 플랫폼은 특정 모델 가중치나 평가 데이터를 내장하지 않습니다. 평가하려는 대상 모델은 UI의 모델 등록 화면 또는 repo seed 대상 설정인 `config/seeded_target_models.yaml`에 등록한 뒤 파이프라인에서 `--config` 값으로 선택해 실행합니다. Judge 모델은 UI에서 별도 등록하거나 `registered_judge_models.json`에 저장합니다.

연동 가능한 모델 유형은 다음과 같습니다.

- Ollama 기반 로컬 모델
- OpenAI API 모델
- CLOVA Studio API 모델
- 사내 HTTP API 모델
- 별도 래퍼를 붙인 커스텀 모델
- 로컬에서 실행되는 fine-tuned 모델

모델 등록은 보통 다음 정보를 기준으로 구성합니다.

```text
config_id
provider
model
base_url
chat_url
api_key_env
prompt_version
generation options
prompt template
```

### Ollama 모델 예시

```yaml
configs:
  - config_id: local_llm
    display_name: Local LLM
    provider: ollama
    model: your-local-model
    base_url: http://afsd.iptime.org:11434
    base_url_env: OLLAMA_BASE_URL
    prompt_version: local_prompt_v1
    eval_target: true
    ui_visible: true
    options:
      temperature: 0.0
      top_p: 0.8
      num_ctx: 4096
```

### OpenAI-compatible API 모델 예시

```yaml
configs:
  - config_id: external_api_llm
    display_name: External API LLM
    provider: generic_api
    model: your-model-name
    base_url: https://your-model-host.example.com
    chat_url: https://your-model-host.example.com/v1/chat/completions
    api_key_env: EXTERNAL_LLM_API_KEY
    prompt_version: api_prompt_v1
    eval_target: true
    ui_visible: true
    options:
      temperature: 0.0
      top_p: 0.8
```

### Judge 모델 예시

```yaml
configs:
  - config_id: local_judge
    display_name: Local Judge
    provider: ollama
    model: your-judge-model
    base_url: http://afsd.iptime.org:11434
    base_url_env: OLLAMA_BASE_URL
    prompt_version: judge_prompt_v1
    evaluation_role: llm_judge
    judge_role: judge
    eval_target: false
    ui_visible: true
    options:
      temperature: 0.0
      top_p: 0.1
```

위 YAML은 모델 등록 방식의 예시입니다. 실제 모델명, 엔드포인트, 프롬프트, 옵션은 프로젝트의 `config/` 구조와 사용 환경에 맞게 조정하면 됩니다.

---

## Dataset Preparation

평가 데이터는 Benchmark와 Regression으로 나누어 운영할 수 있습니다. 업로드본에는 아래 폴더가 준비되어 있으므로, 보유한 CSV 또는 JSONL 평가 문항을 해당 위치에 넣어 사용하면 됩니다.

```text
questionlist/benchmark/benchmark_dataset_test.csv
questionlist/regression/regression_golden_set.csv
```

프로젝트 내부에서 기본적으로 기대하는 데이터는 `schemas/test_case.schema.json` 구조를 따릅니다. CSV 또는 JSONL로 준비할 수 있으며, 최소한 다음 정보가 필요합니다.

```text
case_id
question
gold_answer 또는 expected_answer
source/category/suite 등 분류 정보
필요한 경우 evidence 또는 근거 문서
```

### Benchmark Dataset

Benchmark는 여러 모델의 전반적인 성능을 비교하기 위한 데이터셋입니다.

주로 다음 목적에 사용합니다.

- 신규 모델 성능 비교
- 모델 후보군 선별
- Judge 기준별 평균 점수 비교
- 도메인별 강점/약점 분석

### Regression Dataset

Regression은 이미 중요하다고 확인된 질문, 장애 재현 케이스, 운영상 반드시 맞아야 하는 질문을 모아둔 데이터셋입니다.

주로 다음 목적에 사용합니다.

- 모델 변경 전후 품질 저하 확인
- 프롬프트 수정 영향 검증
- RAG 설정 변경 영향 검증
- 배포 전 필수 통과 테스트

---

## Evaluation Workflow

### 1. Generate Model Answers

먼저 평가 대상 모델의 답변을 생성합니다.

```powershell
python .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\questionlist\benchmark\benchmark_dataset_test.csv `
  --config your_model_config `
  --run-id BENCHMARK_ANSWERS_YYYYMMDD `
  --skip-scoring `
  --answer-cache `
  --resume
```

주요 옵션:

| 옵션 | 설명 |
| --- | --- |
| `--cases-file` | 평가에 사용할 질문 파일 |
| `--config` | 사용할 모델 설정 이름 |
| `--run-id` | 실행 결과를 구분하는 ID |
| `--skip-scoring` | 답변 생성만 수행하고 채점은 생략 |
| `--answer-cache` | 기존 답변 캐시 사용 |
| `--resume` | 중단된 실행 재개 |

Regression 데이터셋으로 실행하는 예시는 다음과 같습니다.

```powershell
python .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\questionlist\regression\regression_golden_set.csv `
  --config internal_llm_v2 `
  --run-id REGRESSION_ANSWERS_YYYYMMDD `
  --skip-scoring `
  --answer-cache `
  --resume
```

### 2. Score Saved Answers with Judge

생성된 답변을 Judge 모델로 채점합니다.

```powershell
python .\scripts\eval\judge_saved_answers.py `
  --source-run-id BENCHMARK_ANSWERS_YYYYMMDD `
  --run-id BENCHMARK_JUDGE_YYYYMMDD `
  --complete-only `
  --judge-config your_judge_config `
  --workers 2 `
  --resume
```

주요 옵션:

| 옵션 | 설명 |
| --- | --- |
| `--source-run-id` | 채점할 답변이 저장된 run id |
| `--run-id` | Judge 결과를 저장할 run id |
| `--judge-config` | 사용할 Judge 모델 설정 |
| `--complete-only` | 완성된 답변만 채점 |
| `--workers` | 병렬 처리 worker 수 |
| `--resume` | 중단된 채점 재개 |

### 3. Run Independent Judge Pipeline

서로 다른 Judge 결과를 함께 생성하고, 충돌 케이스를 검토할 수 있습니다.

```powershell
python .\scripts\eval\run_independent_judge_pipeline.py `
  --source-run-id BENCHMARK_ANSWERS_YYYYMMDD `
  --run-id BENCHMARK_JUDGE_PAIR_YYYYMMDD `
  --judge-config judge_config_1 `
  --judge-config judge_config_2 `
  --conflict-policy review `
  --workers 2 `
  --resume
```

이 방식은 다음 상황에 유용합니다.

- Judge 모델 하나의 평가 편향을 줄이고 싶은 경우
- 서로 다른 Judge의 판정 차이를 보고 싶은 경우
- 중요한 배포 전 케이스를 보수적으로 검토하고 싶은 경우
- 자동 채점 후 사람이 볼 케이스를 선별하고 싶은 경우

---

## Multi-Judge Scoring

복수 Judge를 사용할 때는 웹 UI에서 Judge별 점수 합산 방식을 선택할 수 있습니다.

| 합산 방식 | 설명 |
| --- | --- |
| Judge별 비중으로 합산 | Judge마다 점수 비중을 직접 입력합니다. 비중 합계가 1이어야 실행할 수 있습니다. |
| 최고/최저 제외 평균 | 3개 이상 Judge에서 지표별 최고점과 최저점을 제외하고 평균을 냅니다. |
| 단순 평균 | 선택한 모든 Judge 점수를 같은 비중으로 평균냅니다. |
| 가장 높은 Judge 점수 | 가장 높은 종합 점수를 준 Judge의 점수를 최종 Judge 점수로 사용합니다. |
| 가장 낮은 Judge 점수 | 가장 낮은 종합 점수를 준 Judge의 점수를 최종 Judge 점수로 사용합니다. |

CLI에서 `run_multi_model_eval.py`를 직접 실행할 때는 다음 옵션을 사용할 수 있습니다.

```powershell
python .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\questionlist\benchmark\benchmark_dataset_test.csv `
  --config your_model_config `
  --judge-config judge_config_1 `
  --judge-config judge_config_2 `
  --judge-config judge_config_3 `
  --judge-mode override `
  --judge-aggregation-method trimmed_mean
```

가중 평균을 사용할 때는 Judge별 비중을 JSON으로 전달할 수 있습니다.

```powershell
python .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\questionlist\benchmark\benchmark_dataset_test.csv `
  --config your_model_config `
  --judge-config judge_config_1 `
  --judge-config judge_config_2 `
  --judge-mode override `
  --judge-aggregation-method weighted_mean `
  --judge-score-weights "{`"judge_config_1`":0.7,`"judge_config_2`":0.3}"
```

---

## Scoring Metrics

기본 Judge 지표는 다음과 같습니다.

| 지표 | 의미 |
| --- | --- |
| `ACC` | 기준 답변과 사실/논리가 일치하는지 |
| `COM` | 필요한 답변 요소를 빠짐없이 포함했는지 |
| `NAC` | 금액, 날짜, 수수료, 계산값 등 수치 정보가 정확한지 |
| `HAL` | 근거 없는 내용을 만들어내지 않았는지 |

RAG 또는 evidence 기반 모델을 평가하는 경우 `UTL` 지표를 추가로 사용할 수 있습니다.

| 지표 | 의미 |
| --- | --- |
| `UTL` | 제공된 근거, 문서, evidence를 적절히 활용했는지 |

일반적인 비 RAG 모델 평가는 `ACC`, `COM`, `NAC`, `HAL` 중심으로 수행합니다.

---

## Dashboard

평가 결과는 로컬 웹 대시보드에서 확인할 수 있습니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_final_ui.ps1 -Port 8512 -StopExisting
```

접속 주소:

```text
http://localhost:8512
```

대시보드에서는 다음과 같은 정보를 확인할 수 있습니다.

- run id별 평가 결과
- 모델별 점수 비교
- Judge별 채점 결과
- 실패 케이스 확인
- 충돌 케이스 검토
- 회귀테스트 결과 확인
- 전체 문항/답변/채점 사유 검색

### 모델 연결 확인

UI의 `연결 확인`은 등록된 대상 모델을 순차적으로 확인합니다. Ollama 모델은 단순 설치 여부만 보지 않고, 모델을 짧게 로드해 응답 가능 여부를 확인한 뒤 언로드 요청을 보냅니다. 여러 모델을 등록한 경우 `확인 중 1/N`처럼 진행 순서가 표시되며, 큰 모델은 확인 시간이 걸릴 수 있습니다.

API 모델은 등록된 health endpoint를 호출하고, `local_path` 모델은 경로 존재 여부를 확인합니다.

기존 실행 결과를 UI에서 확인하려면 로컬 산출물이 다음 경로 중 하나에 있어야 합니다.

```text
out/eval_runs/{run_id}/
final_UI/data/
```

해당 폴더는 업로드본에 준비되어 있습니다. 직접 실행한 결과는 `out/eval_runs/`에 두고, UI용으로 고정해 볼 데이터는 `final_UI/data/`에 둘 수 있습니다.

---

## Benchmark vs Regression

이 플랫폼은 Benchmark와 Regression을 구분해서 운영하는 것을 권장합니다.

### Benchmark

Benchmark는 모델의 전체적인 성능을 비교하기 위한 평가입니다.

```text
목적: 모델 간 성능 비교
데이터: 넓은 범위의 질문
실행 주기: 신규 모델 도입, 주요 변경 시
판단 기준: 평균 점수, 지표별 강약점, 도메인별 성능
```

### Regression

Regression은 기존에 잘 되던 케이스가 계속 잘 되는지 확인하기 위한 평가입니다.

```text
목적: 품질 저하 방지
데이터: 중요 질문, 장애 재현 케이스, 운영 필수 케이스
실행 주기: 프롬프트 변경, 모델 변경, RAG 설정 변경, 배포 전
판단 기준: 실패 케이스 수, 중요 케이스 통과 여부
```

---

## Recommended Workflow

일반적인 운영 흐름은 다음과 같습니다.

```text
1. 새 모델 또는 새 프롬프트 준비
2. Regression set으로 빠른 품질 저하 여부 확인
3. Benchmark set으로 전체 성능 비교
4. Judge 결과 확인
5. 충돌 또는 실패 케이스 검토
6. 필요한 경우 프롬프트, 모델, RAG 설정 수정
7. 동일 run을 재실행하여 개선 여부 확인
8. 배포 또는 추가 실험 결정
```

---

## Example: Compare Two Models

예를 들어 `model_v1`과 `model_v2`를 같은 데이터셋으로 비교하려면 다음과 같이 실행합니다.

### Generate answers for model v1

```powershell
python .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\questionlist\benchmark\benchmark_dataset_test.csv `
  --config model_v1 `
  --run-id BENCHMARK_MODEL_V1_YYYYMMDD `
  --skip-scoring `
  --answer-cache `
  --resume
```

### Generate answers for model v2

```powershell
python .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\questionlist\benchmark\benchmark_dataset_test.csv `
  --config model_v2 `
  --run-id BENCHMARK_MODEL_V2_YYYYMMDD `
  --skip-scoring `
  --answer-cache `
  --resume
```

### Score model v1

```powershell
python .\scripts\eval\judge_saved_answers.py `
  --source-run-id BENCHMARK_MODEL_V1_YYYYMMDD `
  --run-id JUDGE_MODEL_V1_YYYYMMDD `
  --complete-only `
  --judge-config your_judge_config `
  --workers 2 `
  --resume
```

### Score model v2

```powershell
python .\scripts\eval\judge_saved_answers.py `
  --source-run-id BENCHMARK_MODEL_V2_YYYYMMDD `
  --run-id JUDGE_MODEL_V2_YYYYMMDD `
  --complete-only `
  --judge-config your_judge_config `
  --workers 2 `
  --resume
```

이후 UI에서 두 run의 결과를 비교합니다.

---

## Example: Run Regression Test Before Deployment

배포 전 회귀테스트는 다음과 같이 실행할 수 있습니다.

```powershell
python .\scripts\eval\run_multi_model_eval.py `
  --cases-file .\questionlist\regression\regression_golden_set.csv `
  --config release_candidate_model `
  --run-id REGRESSION_RC_YYYYMMDD `
  --skip-scoring `
  --answer-cache `
  --resume
```

```powershell
python .\scripts\eval\judge_saved_answers.py `
  --source-run-id REGRESSION_RC_YYYYMMDD `
  --run-id REGRESSION_RC_JUDGE_YYYYMMDD `
  --complete-only `
  --judge-config your_judge_config `
  --workers 2 `
  --resume
```

회귀테스트 결과에서 중요한 케이스가 실패하면 배포 전 모델, 프롬프트, 검색 설정, 후처리 로직을 다시 점검합니다.

---

## Tests

주요 단위 테스트는 다음 명령으로 실행할 수 있습니다.

```powershell
python -m unittest tests.test_regression_pipeline
```

---

## Notes

- `questionlist/`, `out/eval_runs/`, `final_UI/data/` 폴더가 준비되어 있습니다. 각 환경의 평가 데이터와 실행 결과를 해당 위치에 채워 사용하세요.
- 실제 평가를 실행하려면 모델 설정, API key, 평가 데이터셋을 로컬 환경에 맞게 준비해야 합니다.
- OpenAI API 등 유료 API Judge를 사용할 때는 비용이 발생할 수 있으므로 실행 전 설정을 확인하세요.
- 공개 바인딩(`0.0.0.0`)으로 UI를 실행할 때는 반드시 인증을 설정하세요.
