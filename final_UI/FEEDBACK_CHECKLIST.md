# Final UI Feedback Checklist

작성일: 2026-05-26

발표/공유 전 Final UI와 평가 파이프라인을 점검하기 위한 체크리스트입니다.

## 현재 완료

- [x] Benchmark 800건, regression 300건 기준으로 데이터셋 catalog 정리
- [x] 테스트셋 탭에서 `qa_category`, `qa_topic`, `question_type` 기준 표시
- [x] target 모델과 judge 모델 등록 UI 분리
- [x] 대상 모델 연결 확인을 모델별 순차 load/unload 방식으로 정리
- [x] prompt variant를 모델 복사 대신 config row 복제로 관리
- [x] 답변 생성 run과 saved-answer judge run 분리
- [x] 외부 CSV 답변 import와 template 다운로드 흐름 추가
- [x] answer cache/fingerprint 기반 재사용 구조 추가
- [x] timeout/provider error row repair pass 추가
- [x] 복수 Judge 독립 실행 가능
- [x] Judge 3개 이상에서도 가중 합산과 규칙형 합산 정책 선택 가능
- [x] judge conflict 발생 시 `review`, `arbiter_override`, `three_judge` 정책 지원
- [x] UTL은 RAG/evidence 대상에만 활성화하고 비대상은 100점 정규화
- [x] 통과/실패 문항 개요, 문항별 모델 상세 응답 탭 용어 정리
- [x] 업로드본 placeholder 폴더와 `.gitignore` 정리
- [x] 접근 로그 `.gitignore` 및 로그 회전 처리
- [x] 공개 접속용 admin/user 인증 계층 추가

## 운영 중 확인 필요

- [ ] active judge run 종료 후 최종 `judge_scores.jsonl` 중복 key 검사
- [ ] Ollama 연결 확인 후 `/api/ps`에서 불필요하게 남은 모델이 없는지 샘플 점검
- [ ] 복수 Judge 결과 병합 후 conflict queue 샘플 검토
- [ ] arbiter 판단을 최종 점수로 쓸지, 3-judge 집계로 쓸지 run별 기록
- [ ] 신규 데이터 import 후 benchmark와 regression 모두 UTL 적용 대상이 올바른지 확인
- [ ] Final UI의 결과/문항별 모델 상세 응답 탭에서 Judge 판단 사유가 잘리지 않는지 확인
- [ ] 외부 공개 서버 종료 전 `final_UI/data/access_log*.jsonl` 보관/삭제 정책 확인

## 남은 개선 후보

- [ ] 비교 탭에 모델별 radar chart 또는 inline bar 추가
- [ ] 문항 상세 검색을 큰 select 대신 검색형 combobox로 완전 전환
- [ ] judge run ETA를 UI에서 provider별로 표시
- [ ] active run과 CLI 독립 run을 UI에서 함께 모니터링
- [ ] CSV import preview에서 case_id 불일치와 빈 답변을 사전 경고

## 공유 전 필수 확인

- [ ] `.env`가 GitHub 대상에서 제외되어 있는지 확인
- [ ] `out/eval_runs/`, `final_UI/data/`, `questionlist/`의 폴더 구조는 유지되고 실제 로컬 산출물은 제외되는지 확인
- [ ] `final_UI/data/access_log*.jsonl`, `_unused_files/`가 제외되어 있는지 확인
- [ ] `docs/`는 ignore하지 않고 포함하는지 확인
- [ ] README와 `docs/`가 현재 실행 방식과 같은 용어를 쓰는지 확인
- [ ] active judge process가 있을 때는 `out/eval_runs` 안의 파일을 이동하지 않기
