# Final UI

BC 금융 RAG 회귀 평가 결과를 확인하는 로컬 대시보드입니다. 모델 등록, 평가 실행, 저장된 실행 결과 선택, 모델별 비교, 문항별 응답과 Judge 사유 확인을 한 화면에서 처리합니다.

## 실행

저장소 루트에서 의존성을 설치합니다.

```powershell
python -m pip install -r .\requirements.txt
```

로컬 UI 서버를 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_final_ui.ps1 -Port 8512 -StopExisting
```

접속 주소:

```text
http://localhost:8512
```

다른 기기에서 접속해야 한다면 인증 정보를 먼저 설정한 뒤 공개 바인딩으로 실행합니다.

```powershell
$env:FINAL_UI_AUTH_USERS = "admin:your-password:admin"
powershell -ExecutionPolicy Bypass -File .\scripts\run_final_ui.ps1 -Port 8512 -HostName 0.0.0.0 -StopExisting
```

## 주요 화면

| 화면 | 역할 |
| --- | --- |
| 설정 | 대상 모델, Judge 모델, 프롬프트 변형, API 연결 상태를 관리합니다. |
| 테스트셋 | 평가 데이터셋 구성, 문항 분포, 업로드 CSV 미리보기를 확인합니다. |
| 실행 | 대상 모델과 Judge 조합을 선택해 평가를 실행하고 진행 상태를 확인합니다. |
| 결과 | 실행별 KPI, 배포 판정, 문항-모델 결과표, 모델 점수 차트를 확인합니다. |
| 비교 | 선택한 모델만 남겨 지표별 점수와 통과율을 비교합니다. |
| 통과/실패 문항 개요 | 실패, 검토 필요, 탐색 케이스를 요약합니다. |
| 문항별 모델 상세 응답 | 특정 문항의 모델 답변, 모범답안, Judge 판단 사유를 확인합니다. |
| 전체 검색 | 질문, 답변, Judge 사유, 오류 유형을 통합 검색합니다. |

## UI/UX 확인 포인트

- 결과 차트는 x축에 긴 모델명을 직접 표시하지 않고 `M1`, `M2` 축 표기와 하단 범례를 사용합니다.
- 차트 막대나 점에 포인터를 올리면 모델명, 종합 점수, 통과율을 확인할 수 있습니다.
- 문항별 결과표는 첫 문항 열과 헤더가 고정되며, 긴 Judge 라벨은 셀 안에서 2줄까지 표시됩니다.
- 일반 표는 가로 스크롤과 sticky 헤더를 사용해 긴 모델명, 경로, 한국어 문장이 레이아웃을 밀지 않게 처리합니다.

## 데이터 파일

UI는 아래 파일을 우선 읽습니다.

```text
final_UI/data/active_run.json
final_UI/data/eval_runs.csv
final_UI/data/question_cases.csv
final_UI/data/run_release_gates.csv
final_UI/data/registered_target_models.json
final_UI/data/registered_judge_models.json
```

파일이 없으면 `final_UI/samples/`의 샘플 데이터를 사용해 화면 구조를 확인합니다. 실제 API 키와 비밀번호는 `.env`, 환경변수, 또는 로컬 전용 `final_UI/data/server_api_secrets.json`으로만 관리하고 GitHub에 올리지 않습니다.

## 질문셋 확장

CSV 업로드나 `config/eval_dataset_catalog.yaml`에 등록된 dataset pool을 통해 benchmark/regression 후보를 확장할 수 있습니다. 최소 입력은 질문과 기준 답변입니다.

| 개념 | 권장 컬럼 | 허용 alias |
| --- | --- | --- |
| 질문 | `question` | `instruction`, `input`, `prompt`, `query`, `문제`, `질문` |
| 기준 답변 | `ground_truth` | `output`, `answer`, `gold_answer`, `expected_output`, `정답` |
| 질문 유형 | `question_type` | `qtype`, `type`, `task_type`, `문제유형`, `질문유형` |

`qa_category`, `qa_topic`, `question_type` 값은 필터와 요약에 표시됩니다. 기본 점수 지표는 ACC, COM, UTL, NAC, HAL입니다.

## 검증

```powershell
python -m py_compile .\final_UI\server.py
python -m unittest discover -s tests -p "test*.py"
```
