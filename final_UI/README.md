# Final UI

LLM 평가 실행과 결과 확인을 위한 로컬 웹 대시보드입니다. 모델 등록, 답변 생성, 저장된 답변 재채점, 결과 비교, 문항별 응답 확인을 한 화면에서 처리합니다.

## 실행

저장소 루트에서 실행합니다.

```powershell
python -m pip install -r .\requirements.txt
```

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_final_ui.ps1 -Port 8512 -StopExisting
```

접속 주소:

```text
http://localhost:8512
```

외부 기기에서 접속해야 하면 인증 정보를 먼저 설정한 뒤 공개 바인딩으로 실행합니다.

```powershell
$env:FINAL_UI_AUTH_USERS = "admin:your-password:admin"
powershell -ExecutionPolicy Bypass -File .\scripts\run_final_ui.ps1 -Port 8512 -HostName 0.0.0.0 -StopExisting
```

## 주요 화면

| 화면 | 역할 |
| --- | --- |
| 설정 | 모델 등록, Judge 비중 설정, 접속 기록 확인 |
| 테스트셋 | 평가 데이터셋 구성과 문항 분포 확인 |
| 실행 | 답변 생성, 저장 답변 재채점, CSV import/export |
| 결과 | 실행별 KPI, 모델별 점수, 배포 차단 현황 확인 |
| 비교 | 모델별 점수와 문항별 차이 비교 |
| 통과/실패 문항 개요 | 실패, 회귀, 탐색 케이스 요약 |
| 문항별 모델 상세 응답 | 문항 단위 모델 답변과 Judge 판단 확인 |
| 전체 검색 | 질문, 답변, Judge 사유, 오류 유형 검색 |

## 모델 연결 확인

`연결 확인` 버튼은 등록된 대상 모델을 순차적으로 확인합니다. Ollama 모델은 단순 태그 조회만으로 `연결됨` 처리하지 않고, 해당 모델을 짧게 로드해 응답 가능 여부를 확인한 뒤 언로드 요청을 보냅니다. 따라서 모델 수와 크기에 따라 확인 시간이 걸릴 수 있습니다.

| Provider | 확인 방식 |
| --- | --- |
| Ollama | `/api/tags`로 태그 존재 확인 후 `mode=load_unload` healthcheck에서 짧은 생성 요청과 언로드 수행 |
| API 모델 | 등록된 `health_url` 또는 provider 기본 health endpoint 호출 |
| local_path | 로컬 경로 존재 여부 확인 |

관련 환경 변수:

| 환경 변수 | 설명 |
| --- | --- |
| `MODEL_HEALTH_TIMEOUT_SECONDS` | 태그 조회, health endpoint, `/api/ps` 확인 timeout |
| `MODEL_LIVE_HEALTH_TIMEOUT_SECONDS` | Ollama 모델 실제 로드 확인 timeout |

## 로컬 데이터 폴더

업로드본에는 로컬 데이터와 실행 결과를 채울 폴더가 준비되어 있습니다.

```text
final_UI/data/   UI가 바로 읽을 CSV/JSON 데이터
out/eval_runs/   평가 실행 결과
```

각 폴더의 `.gitkeep`은 폴더 구조 유지용입니다. 실제 CSV, JSON, JSONL, 로그 파일은 로컬에서 생성하거나 복사해 채워 넣습니다. 데이터가 아직 채워지지 않은 상태에서도 UI는 실행됩니다.

## 인증

기본적으로 공개 바인딩(`0.0.0.0`)에서는 인증이 필요합니다.

| 환경 변수 | 설명 |
| --- | --- |
| `FINAL_UI_AUTH_USERS` | `admin:password:admin,user:password:user` 형식의 계정 목록 |
| `FINAL_UI_AUTH_TOKEN` | 토큰 기반 관리자 접근 |
| `FINAL_UI_AUTH_DISABLED` | 로컬 개발용 인증 비활성화 |

비밀번호와 API key는 `.env` 또는 실행 환경 변수로만 관리하고 GitHub에 올리지 않습니다.

## 주요 파일

```text
index.html       화면 구조
styles.css       BC카드 폰트, 반응형 레이아웃, 상태 표시
app.js           데이터 로딩, 화면 렌더링, 실행 제어
server.py        정적 파일 서버와 로컬 API
assets/          UI 로고 이미지
data/.gitkeep    로컬 데이터 폴더 유지용 파일
```

## 점검

```powershell
python -m py_compile .\final_UI\server.py
python -m unittest discover -s tests -p "test*.py"
```
