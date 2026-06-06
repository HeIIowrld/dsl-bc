# Final UI User Manual

이 문서는 Final UI를 사용해 벤치마크/회귀 점검 답변을 생성하고, 저장된 답변을 LLM 평가 모델로 다시 채점하는 절차를 설명합니다.

## 1. 접속

로컬 실행:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_final_ui.ps1 -Port 8512 -StopExisting
```

외부 공개 실행:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_final_ui.ps1 -Port 8517 -HostName 0.0.0.0 -StopExisting
```

외부 공개 시에는 로그인 계정을 사용합니다. `admin`은 실행/수정 권한, `user`는 조회 권한입니다.

## 2. 설정 탭

설정 탭에서는 평가 대상 모델과 judge 모델을 관리합니다.

### Target 모델 등록

1. Provider를 선택합니다.
2. `config_id`, `display_name`, `model`, endpoint 또는 local path를 입력합니다.
3. API key는 직접 저장하지 않고 환경 변수 이름만 입력합니다.
4. 등록 후 좌측 모델 필터와 실행 탭에 나타나는지 확인합니다.

같은 모델을 다른 system prompt로 비교하려면 `프롬프트 변형`을 사용합니다. 모델 파일이나 Ollama alias를 복사하지 않고, config row만 새로 만듭니다.

### 모델 연결 확인

설정 탭 또는 좌측 사이드바의 `연결 확인`은 등록된 대상 모델을 한 번에 병렬 호출하지 않고, 모델별로 순차 확인합니다.

Ollama 모델은 다음 순서로 확인합니다.

1. 등록된 `base_url`의 `/api/tags`에서 모델 태그가 있는지 확인합니다.
2. 해당 모델에 짧은 생성 요청을 보내 실제 로드와 응답 가능 여부를 확인합니다.
3. 확인이 끝나면 언로드 요청을 보내 VRAM 점유를 줄입니다.
4. 실행 중인 평가 작업이 있으면 로드/언로드 확인을 건너뛰고 상태를 보류합니다.

큰 모델은 로드 확인에 시간이 걸릴 수 있습니다. 버튼과 상태 배지에는 `확인 중 1/N`처럼 현재 확인 중인 모델 순서가 표시됩니다.

### 채점 모델 등록

채점 모델은 평가 대상 모델과 별도로 등록합니다. CLOVA Studio, OpenAI 호환 API, Ollama, 사내 HTTP API 기반 채점 모델을 같은 방식으로 등록할 수 있지만, 운영에서는 제공자별 호출 제한과 비용을 분리해서 봅니다.

## 3. 테스트셋 탭

테스트셋 탭에서는 benchmark/regression 데이터가 제대로 파싱되는지 확인합니다.

확인할 항목:

- 총 case 수
- `qa_category`, `qa_topic`, `question_type` 분포
- sample question과 기준 정답
- case_id와 question_type이 서로 맞게 표시되는지

현재 기준:

| Dataset | Cases |
| --- | ---: |
| 벤치마크 - `benchmark_dataset_test.csv` | 800 |
| 회귀 전체 - `regression_golden_set.csv` | 300 |

## 4. 실행 탭

실행 탭에서는 두 가지 흐름을 선택합니다.

### 답변 생성 실행

평가 대상 모델을 호출해 답변 파일만 만듭니다. LLM 평가 모델은 호출하지 않습니다. 장시간 실행은 이어서 실행과 답변 캐시를 켜는 것을 권장합니다.

좋은 사용 예:

- 새 벤치마크 데이터셋에 대해 모든 평가 대상 모델 답변 생성
- 중간에 중지된 실행 이어서 진행
- timeout이나 빈 답변만 repair pass로 재시도

### 저장된 답변 다시 채점

이미 생성된 답변 파일을 재사용해 채점만 수행합니다. 평가 대상 모델은 다시 호출하지 않습니다.

좋은 사용 예:

- 여러 Judge를 각각 독립 실행
- 같은 답변셋을 새 rubric으로 재평가
- 외부 CSV로 받은 답변을 내부 표준 형식으로 변환 후 평가

### 평가 및 점수 합산 방식

실행 탭의 점수 합산 방식은 운영 목적에 맞게 선택합니다.

| 방식 | 의미 |
| --- | --- |
| LLM only | 선택한 Judge 점수만 최종 점수로 사용 |
| LLM blended | 여러 Judge 점수를 사용자 지정 비율로 합산 |
| LLM+Static blended | Judge 점수와 rule 기반 점수를 함께 합산 |
| Rule-based only | Judge 호출 없이 rule 기반 점수만 사용 |

Judge가 3개 이상이어도 동일하게 사용할 수 있습니다. 가중 합산을 선택하면 각 Judge 비중의 총합이 1.0일 때만 적용합니다. 최고점/최저점 제외 평균, 단순 평균, 최고점 기준, 최저점 기준 같은 규칙형 합산은 실행 설정에서 별도 정책으로 기록합니다.

## 5. 외부 CSV import

실행 탭에서 import template을 다운로드한 뒤 아래 컬럼을 채웁니다.

```text
case_id, question_id, config_id, model, model_answer
```

권장 사항:

- `case_id`는 내부 benchmark/regression case와 정확히 일치해야 합니다.
- 비교 축은 `config_id`입니다.
- endpoint나 prompt가 바뀐 모델은 다른 `config_id`로 분리합니다.
- 빈 답변은 import 전에 제거하거나 별도 실패로 표시합니다.

## 6. 결과 탭

결과 탭에서는 실행 단위 KPI와 모델별 점수를 봅니다.

확인할 항목:

- 총점과 pass rate
- ACC/COM/NAC/HAL 세부 점수
- RAG/evidence 모델의 UTL 활성 여부
- 비용과 평균 latency
- 실행 선택 드롭다운에서 과거 결과 선택

## 7. 통과/실패 문항 개요 탭

통과/실패 문항 개요 탭은 단순 실행 실패뿐 아니라 Judge 충돌과 사람이 검토해야 할 케이스도 함께 보여줍니다.

주요 상태:

| 상태 | 의미 |
| --- | --- |
| target error | 평가 대상 모델 답변 생성 실패 |
| judge error | Judge API 호출 또는 JSON parse 실패 |
| conflict | Judge 간 점수 차이 또는 통과/실패 불일치 |
| review needed | 사람이 확인해야 하는 케이스 |

충돌이 있으면 상위 Judge로 재평가하거나 사람이 최종 판단을 선택합니다. 개별 Judge 판단과 최종 채택 정책은 모두 보존합니다.

## 8. 문항별 모델 상세 응답 탭

문항별 모델 상세 응답 탭에서는 하나의 case에 대해 모델별 답변과 Judge 판단 사유를 비교합니다.

확인할 항목:

- 문제와 기준 정답
- 모델 답변
- 개별 Judge 판단
- 점수 차이가 큰 경우 재평가 또는 최종 채택 판단
- 최종 채택 정책

## 9. 운영 팁

- 긴 실행은 같은 실행 ID로 이어서 실행합니다.
- Judge provider는 provider별로 독립 실행해도 됩니다.
- 서로 다른 Judge가 같은 row를 동시에 끝낼 때까지 기다릴 필요는 없습니다.
- Ollama 연결 확인은 실제 로드/언로드를 수행하므로, 평가 실행 중에는 누르지 않는 것을 권장합니다.
- `out/eval_runs`에는 실행 결과를 채워 넣고, 업로드 시에는 폴더 구조만 유지합니다.
- `.env`와 접근 로그는 공유하지 않습니다.
