const metricCols = [
  "acc",
  "com",
  "utl",
  "nac",
  "hal",
];

const reliabilityMinimums = {
  oneD: 30,
  twoD: 30,
  threeD: 30,
};

const finalQaCategories = ["BC FAQ", "\uae08\uc735\uc815\ubcf4", "\uce74\ub4dc\uc0c1\ud488"];
const finalQuestionTypes = ["\ub2e8\uc77c\ucd94\ub860(\uc0ac\uc2e4\ucd94\ucd9c)", "\ube44\uad50\ub300\uc870", "\ubcf5\ud569\ucd94\ub860", "\uc218\uce58\ucd94\ub860/\uacc4\uc0b0", "\ubbfc\uac10"];
const finalFinanceTopics = ["BC FAQ", "\uce74\ub4dc/\uacb0\uc81c", "\ub300\ucd9c/\uc5ec\uc2e0", "\uc608\uc801\uae08", "\ud22c\uc790/\ud380\ub4dc", "\uc77c\ubc18 \uae08\uc735"];

const modelHealthTimeoutMs = 180000;
const modelHealthMaxAttempts = 1;
const modelHealthRetryDelayMs = 600;

const metricLabels = {
  acc: "\uc815\ud655\uc131(ACC)",
  com: "\uc644\uacb0\uc131(COM)",
  utl: "\uac80\uc0c9 \ud65c\uc6a9\ub3c4(UTL)",
  nac: "\uc218\uce58 \uc815\ud655\uc131(NAC)",
  hal: "\ud658\uac01(HAL)",
};

const severityLabels = {
  critical: "치명",
  high: "높음",
  medium: "보통",
  low: "낮음",
  hard: "어려움",
  easy: "쉬움",
};

const runProfileLabels = {
  single_dataset: "단일 케이스 파일",
  benchmark_final_full: "벤치마크 전체",
  regression_golden_full: "회귀 전체",
  custom_seeded_mix: "직접 구성",
};

const runProfileHelp = {
  single_dataset: "선택한 케이스 파일 전체를 기준으로 빠르게 확인합니다.",
  benchmark_final_full: "최종 벤치마크 전체를 실행합니다. 배포 차단 집계에는 포함하지 않습니다.",
  regression_golden_full: "회귀 골든셋 전체를 실행합니다. 배포 차단 판단에 사용합니다.",
  custom_seeded_mix: "총 샘플 수, 풀별 비율, 랜덤 시드를 직접 입력해 섞어서 실행합니다.",
};

const targetSelectionModeLabels = {
  single: "단일 모델 실행",
  multi: "여러 모델 비교 실행",
};

const targetSelectionModeHelp = {
  single: "한 번에 1개 모델만 실행합니다. 비교가 필요하면 여러 모델 비교 실행을 선택하세요.",
  multi: "선택한 여러 대상 모델을 같은 케이스 파일로 순차 실행해 비교합니다.",
};

const scoringModeLabels = {
  llm_override: "단일 Judge 채점",
  llm_blended: "여러 Judge 합산",
  blend: "Judge+규칙 혼합",
  static: "규칙 기반만",
  static_llm: "Static + LLM audit",
  answers_only: "답변만 생성",
};

const scoringModeHelp = {
  llm_override: "선택한 Judge 1개만 최종 점수로 사용합니다. 여러 Judge를 선택하려면 여러 Judge 합산을 사용하세요.",
  llm_blended: "선택한 여러 Judge 점수를 지정 비율로 합산합니다. Judge는 2개 이상 사용할 수 있고, 기본값은 균등 분배입니다.",
  blend: "Judge 점수와 규칙 기반 점수를 지정 비율로 혼합합니다. 여러 Judge를 선택하면 Judge 점수를 먼저 합산합니다.",
  static: "규칙 기반 채점만 사용하고 Judge는 호출하지 않습니다. 최종 점수는 Rule 100%입니다.",
  static_llm: "Rule-based 점수는 유지하고 LLM Judge는 평가 의견만 남깁니다.",
};

const judgeAggregationLabels = {
  weighted_mean: "Judge별 비중",
  trimmed_mean: "최고/최저 제외 평균",
  mean: "단순 평균",
  max: "최고점 기준",
  min: "최저점 기준",
};

const judgeAggregationHelp = {
  weighted_mean: "선택한 Judge별 비중으로 점수를 합산합니다. 비중 합계가 1이어야 실행할 수 있습니다.",
  trimmed_mean: "3개 이상이면 지표별 최고점과 최저점을 제외하고 평균을 냅니다. 2개일 때는 단순 평균과 같습니다.",
  mean: "선택한 모든 Judge 점수를 같은 비중으로 평균냅니다.",
  max: "가장 높은 종합 점수를 준 Judge의 점수를 최종 Judge 점수로 사용합니다.",
  min: "가장 낮은 종합 점수를 준 Judge의 점수를 최종 Judge 점수로 사용합니다.",
};

const hiddenDatasetIds = new Set([
  "benchmark__benchmark_dataset_test",
  "regression__regression_golden_set",
]);

const excludedDatasetMarkers = [
  "_unused_files",
  "archive",
  "backup",
  "tmp",
  "draft",
  "cleanup",
];
const excludedDatasetTokens = ["old"];

const sourceLabels = {
  "BC FAQ": "BC FAQ",
  "\uae08\uc735\uc815\ubcf4": "\uae08\uc735\uc815\ubcf4",
  "\uce74\ub4dc\uc0c1\ud488": "\uce74\ub4dc\uc0c1\ud488",
  crefia_creditcard_faq: "\uc5ec\uc2e0\ud611\ud68c FAQ",
  crefia_creditcard_guide: "\uc5ec\uc2e0\ud611\ud68c \uac00\uc774\ub4dc",
  detail: "BC \uc0c1\uc138 \ud398\uc774\uc9c0",
  faq: "BC FAQ",
  fine_financial_dictionary: "\uae08\uc735\uc0ac\uc804",
  fine_life_finance_talk: "\uc0dd\ud65c\uae08\uc735",
  fine_newsletter: "\ub274\uc2a4\ub808\ud130",
  fine_prc_step_info: "\uc808\ucc28 \uc815\ubcf4",
  html_seed: "BC HTML 원천셋",
  card_product_csv: "\uce74\ub4dc/\uc0c1\ud488 CSV",
  sample_mrc_151: "\uc0d8\ud50c MRC",
  sample_ocr_055: "\uc0d8\ud50c OCR",
  financial_qa_xlsx: "\uae08\uc735 QA XLSX",
  financial_faq_csv: "\uae08\uc735 FAQ CSV",
  regression_golden_csv: "회귀 골든 CSV",
  unknown: "\ubbf8\ubd84\ub958",
};

const errorTypeLabels = {
  normal: "정상",
  partial_inaccuracy: "부분적 부정확",
  unsupported_claim: "근거 없는 주장",
  missing_condition: "필수 조건 누락",
  format_violation: "형식 위반",
  unsafe_completion: "위험 응답",
  hallucinated_policy: "정책 환각",
  behavior_violation: "기대 동작 위반",
  ungrounded_answer: "근거 부족 답변",
  evidence_context_echo: "근거 원문 반복",
  unscored_case: "채점 제외 케이스",
  provider_error: "모델 호출 오류",
  llm_judge_error: "Judge 오류",
};

const errorTypeAliases = {
  "부분적 부정확": "partial_inaccuracy",
  "부분적 부정확성": "partial_inaccuracy",
  "부분 부정확성": "partial_inaccuracy",
  "부분적 오류": "partial_inaccuracy",
  "부분적 불일치": "partial_inaccuracy",
  partial_match: "partial_inaccuracy",
  partial_mismatch: "partial_inaccuracy",
  minor_mismatch: "partial_inaccuracy",
  inaccuracy: "partial_inaccuracy",
  incorrect: "partial_inaccuracy",
  incorrect_answer: "partial_inaccuracy",
  incorrect_content: "partial_inaccuracy",
  incorrect_claim: "partial_inaccuracy",
  incorrect_numeric: "partial_inaccuracy",
  incorrect_information: "partial_inaccuracy",
  inaccurate_content: "partial_inaccuracy",
  information_inaccuracy: "partial_inaccuracy",
  numeric_inaccuracy: "partial_inaccuracy",
  numeric_accuracy: "partial_inaccuracy",
  numeric_miscalculation: "partial_inaccuracy",
  misinterpretation: "partial_inaccuracy",
  typo: "partial_inaccuracy",
  incomplete: "missing_condition",
  partial_completeness: "missing_condition",
  incomplete_information: "missing_condition",
  partial_information_missing: "missing_condition",
  text_incompleteness: "missing_condition",
  missing_required_steps: "missing_condition",
  "필수 조건 누락": "missing_condition",
  "필수조건 누락": "missing_condition",
  missing_core_remedy: "missing_condition",
  missing_required_procedure: "missing_condition",
  unsupported_answer: "unsupported_claim",
  "근거 없는 주장": "unsupported_claim",
  "근거없는 주장": "unsupported_claim",
  unsupported_factual_claim: "unsupported_claim",
  unsupported_addition: "unsupported_claim",
  unsupported_vague_answer: "unsupported_claim",
  unsupported_helpfulness: "unsupported_claim",
  partial_hallucination: "unsupported_claim",
  material_omission_and_hallucination: "unsupported_claim",
  excessive_details: "unsupported_claim",
  wrong_source_answer: "unsupported_claim",
  incorrect_retrieval_utilization: "unsupported_claim",
  ungrounded_answer: "unsupported_claim",
  evidence_context_echo: "unsupported_claim",
  llm_judge: "llm_judge_error",
  "형식 위반": "format_violation",
  "위험 응답": "unsafe_completion",
  "정책 환각": "hallucinated_policy",
  "기대 동작 위반": "behavior_violation",
  "근거 부족 답변": "unsupported_claim",
  "근거 원문 반복": "unsupported_claim",
  "채점 제외 케이스": "unscored_case",
  "모델 호출 오류": "provider_error",
  "judge 오류": "llm_judge_error",
  "Judge 오류": "llm_judge_error",
};

const rawHtml = Symbol("rawHtml");

const colors = {
  red: "rgb(250, 50, 70)",
  line: "rgb(224, 224, 222)",
};

let runs = [];
let cases = [];
let runReleaseGates = [];
let modelRegistry = {};
let judgeApiPresetCatalog = [];
let serverApiSecrets = [];
let questionlistSummary = null;
let questionlistCases = [];
let questionlistDatasets = [];
let datasetCases = [];
let selectedDataset = "benchmark_final_full";
let activeEvalJobId = null;
let evalJobPoll = null;
let latestRun = null;
let evalRunHistory = [];
let selectedRunId = "";
let evalCatalog = { profiles: {}, pools: {}, default_seed: 42 };
let judgeComparisonOptions = { baseline_sources: [], judge_runs: [] };
let modelHealthCheckInFlight = false;
let toastSequence = 0;
let modelHealthCheckProgress = null;
let judgePickerInitialized = false;
let appReady = false;
let authSession = null;
let authAccessLog = [];

let state = {
  resultVersions: new Set(),
  runConfigVersions: new Set(),
  difficulties: new Set(),
  sources: new Set(),
  behaviors: new Set(),
  threshold: 80,
  selectedQuestion: null,
  selectedDatasetCaseId: null,
  resultViewMode: "all",
  resultSearch: "",
  resultModelFilter: "",
  selectedMatrixKey: null,
  globalSearch: "",
  globalSearchModel: "",
  questionSearch: "",
  failureLimit: 40,
  activeTab: "runEval",
  caseSetSubtab: "case-preview",
  failureSubtab: "failure-overview",
  modelConnections: new Map(),
  judgeScoreWeights: {},
  judgeScoreWeightKey: "",
  judgeScoreWeightsTouched: false,
};

document.addEventListener("DOMContentLoaded", async () => {
  arrangeBenchmarkChrome();
  bindTabs();
  initializePanelSubtabs();
  bindModelRegistryForm();
  bindJudgeRegistryForm();
  initializeRegistryProviderControls();
  initializeRunFormGuards();
  initializeExplorerControls();
  bindRunHealthCheckButton();
  selectedRunId = initialRunIdFromUrl();
  const requestedRunId = selectedRunId;

  try {
    const runQuery = selectedRunId ? `?run_id=${encodeURIComponent(selectedRunId)}` : "";
    let [runText, caseText, gateText, registry, presetCatalog, secretCatalog, qSummary, qCases, qDatasets, runInfo, runHistory, catalog, comparisonOptions, session, accessLog] = await Promise.all([
      fetchCsv(`data/eval_runs.csv${runQuery}`),
      fetchCsv(`data/question_cases.csv${runQuery}`),
      fetchCsvOptional(`data/run_release_gates.csv${runQuery}`, ""),
      fetchJsonOptional("api/model-registry", {}),
      fetchJsonOptional("api/judge-api-presets", { presets: [] }),
      fetchJsonOptional("api/server-api-secrets", { keys: [] }),
      fetchJsonOptional("api/questionlist/summary", null),
      fetchJsonOptional("api/questionlist/cases?limit=400", { cases: [] }),
      fetchJsonOptional("api/questionlist/datasets", { datasets: [] }),
      fetchJsonOptional(`api/eval/latest-run${runQuery}`, null),
      fetchJsonOptional("api/eval/runs", { runs: [] }),
      fetchJsonOptional("api/eval/catalog", { profiles: {}, pools: {}, default_seed: 42 }),
      fetchJsonOptional("api/eval/judge-comparison/options", { baseline_sources: [], judge_runs: [] }),
      fetchJsonOptional("api/auth/session", null),
      fetchJsonOptional("api/auth/access-log?limit=80", { entries: [] }),
    ]);

    if (!requestedRunId && runInfo?.run_id) {
      selectedRunId = runInfo.run_id;
      const latestRunQuery = `?run_id=${encodeURIComponent(runInfo.run_id)}`;
      [runText, caseText, gateText] = await Promise.all([
        fetchCsv(`data/eval_runs.csv${latestRunQuery}`),
        fetchCsv(`data/question_cases.csv${latestRunQuery}`),
        fetchCsvOptional(`data/run_release_gates.csv${latestRunQuery}`, ""),
      ]);
    }

    runs = parseCsv(runText).map(normalizeRun);
    cases = parseCsv(caseText).map(normalizeCase);
    runReleaseGates = parseCsv(gateText).map(normalizeRunGate);
    modelRegistry = registry;
    judgeApiPresetCatalog = (presetCatalog?.presets ?? []).map(normalizeJudgeApiPresetClient).filter(Boolean);
    serverApiSecrets = normalizeServerApiSecrets(secretCatalog?.keys ?? []);
    questionlistSummary = qSummary;
    questionlistCases = (qCases?.cases ?? []).map(normalizeQuestionlistCase);
    latestRun = runInfo;
    selectedRunId = runInfo?.run_id || selectedRunId;
    questionlistDatasets = qDatasets?.datasets ?? [];
    selectedDataset = preferredDatasetForRun(selectedRunId, selectedDataset);
    evalRunHistory = runHistory?.runs ?? [];
    evalCatalog = catalog ?? evalCatalog;
    judgeComparisonOptions = comparisonOptions ?? judgeComparisonOptions;
    authSession = session;
    authAccessLog = accessLog?.entries ?? [];

    initializeState();
    renderJudgeApiPresetSelect();
    renderServerApiKeyControls();
    renderFilters();
    renderJudgeRegistry();
    updateHealthCheckButtonState();
    initializeResultViewerControls();
    initializeResultRunControls();
    initializeSearchControls();
    initializeCaseSetControls();
    bindRunWithSelectedDatasetButton();
    initializeEvalRunControls();
    initializeReblendControls();
    initializeJudgeComparisonControls();
    await reconnectEvalJob();
    appReady = true;
    const requestedTab = window.location.hash ? window.location.hash.slice(1) : "";
    if (!evalTargetRegistryIds().length && requestedTab !== "settings") {
      activateTab("settings");
    } else {
      renderAll();
    }
    renderTargetRegistry();
    await loadDatasetCases(selectedDataset);
  } catch (error) {
    renderLoadError(error);
  }
});

function arrangeBenchmarkChrome() {
  const hero = document.querySelector(".hero");
  if (hero) hero.hidden = true;
  syncSidebarForFinalQuestionSets();
  syncFinalQuestionSetCopy();

  const registryPanel = document.querySelector(".model-registry-panel");
  if (!registryPanel) return;

  registryPanel.classList.add("prompt-settings-panel");
  const title = registryPanel.querySelector("summary h2, .card-head h2");
  const description = registryPanel.querySelector("summary .card-head span, .card-head span");
  const submit = registryPanel.querySelector('button[type="submit"]');
  const systemPrompt = document.getElementById("modelSystemPrompt");
  const queryTemplate = document.getElementById("modelQueryPromptTemplate");
  const optionsJson = document.getElementById("modelOptionsJson");

  if (title) title.textContent = "모델/프롬프트 설정";
  if (description) description.textContent = "시스템 프롬프트, 질문 템플릿, 샘플링 옵션";
  if (submit) submit.textContent = "대상 모델 등록/업데이트";
  if (systemPrompt) systemPrompt.placeholder = "모델별 시스템 프롬프트 override";
  if (queryTemplate) queryTemplate.placeholder = "질문 템플릿에 {question}을 포함하세요.";
  if (optionsJson) optionsJson.placeholder = "{\"temperature\":0.2,\"top_p\":0.8}";
}

function syncSidebarForFinalQuestionSets() {
  const tagFilters = document.getElementById("tagFilters");
  hideSidebarFilter(tagFilters);
  markPersistentSidebarFilter(document.getElementById("sourceFilters"), "대분류");
  markPersistentSidebarFilter(document.getElementById("behaviorFilters"), "금융토픽");
  markPersistentSidebarFilter(document.getElementById("difficultyFilters"), "질문유형");
  markResultOnlySidebarFilter(document.getElementById("threshold"), "과락 기준");
}

function hideSidebarFilter(element) {
  if (!element) return;
  const label = element.previousElementSibling;
  if (label?.tagName === "LABEL") label.hidden = true;
  element.hidden = true;
}

function markResultOnlySidebarFilter(element, labelText) {
  if (!element) return;
  element.classList.add("result-only-filter");
  const label = element.previousElementSibling;
  if (label?.tagName === "LABEL") {
    label.classList.add("result-only-filter");
    if (labelText) {
      if (element.id === "threshold") {
        const value = document.getElementById("thresholdValue")?.textContent || "80";
        label.innerHTML = `${escapeHtml(labelText)} <span id="thresholdValue">${escapeHtml(value)}</span>점`;
      } else {
        label.textContent = labelText;
      }
    }
  }
}

function syncFinalQuestionSetCopy() {
  const datasetLabel = document.querySelector('label[for="datasetSelect"]');
  if (datasetLabel) datasetLabel.textContent = "데이터셋";
}

function initialRunIdFromUrl() {
  try {
    return new URLSearchParams(window.location.search).get("run_id") || "";
  } catch {
    return "";
  }
}

function markPersistentSidebarFilter(element, labelText) {
  if (!element) return;
  element.classList.remove("result-only-filter");
  const label = element.previousElementSibling;
  if (label?.tagName === "LABEL") {
    label.classList.remove("result-only-filter");
    if (labelText) label.textContent = labelText;
  }
}

function apiFetch(path, options = {}) {
  return fetch(path, options);
}

async function fetchCsv(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`${path} 로딩 실패 (${response.status})`);
  }
  return response.text();
}

async function fetchCsvOptional(path, defaultValue) {
  try {
    const response = await fetch(path);
    if (!response.ok) return defaultValue;
    return response.text();
  } catch {
    return defaultValue;
  }
}

async function fetchJsonOptional(path, defaultValue) {
  try {
    const response = await fetch(path);
    if (!response.ok) return defaultValue;
    return response.json();
  } catch {
    return defaultValue;
  }
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;

  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];

    if (ch === '"' && quoted && next === '"') {
      cell += '"';
      i += 1;
    } else if (ch === '"') {
      quoted = !quoted;
    } else if (ch === "," && !quoted) {
      row.push(cell);
      cell = "";
    } else if ((ch === "\n" || ch === "\r") && !quoted) {
      if (ch === "\r" && next === "\n") i += 1;
      row.push(cell);
      if (row.some((value) => value.trim() !== "")) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += ch;
    }
  }

  if (cell || row.length) {
    row.push(cell);
    rows.push(row);
  }

  const headers = (rows.shift() ?? []).map((header) => header.replace(/^\uFEFF/, ""));
  return rows.map((values) => Object.fromEntries(headers.map((header, idx) => [header, values[idx] ?? ""])));
}

function normalizeRun(d) {
  const hasUtlFlag = d.utl_applicable !== undefined && d.utl_applicable !== "";
  const hasUtlRate = d.utl_applicable_rate !== undefined && d.utl_applicable_rate !== "";
  [
    "total_questions",
    "scored_questions",
    "review_pending_count",
    "pass_rate",
    "scored_pass_rate",
    "overall_score",
    "scored_average",
    "acc",
    "com",
    "utl",
    "nac",
    "hal",
    "scored_acc",
    "scored_com",
    "scored_utl",
    "scored_nac",
    "scored_hal",
    "utl_applicable_rate",
    "answer_quality_score",
    "rag_quality_score",
    "avg_latency_ms",
    "avg_cost_krw",
  ].forEach((key) => {
    d[key] = Number(d[key] || 0);
  });
  d.utl_applicable = hasUtlFlag ? !isFalse(d.utl_applicable) : (hasUtlRate ? d.utl_applicable_rate > 0 : true);
  d.version = d.version || "unknown";
  d.model = d.model || d.version;
  d.run_type = d.run_type || "eval";
  return d;
}

function normalizeCase(d) {
  [
    ...metricCols,
    "overall_score",
    "regression_delta",
    "score_denominator",
    "raw_metric_score",
    "answer_quality_score",
    "rag_quality_score",
    "llm_judge_score_gap",
    "llm_judge_score_min",
    "llm_judge_score_max",
    "llm_judge_base_average_score",
    "llm_judge_arbiter_score",
  ].forEach((key) => {
    d[key] = Number(d[key] || 0);
  });
  d.utl_applicable = !isFalse(d.utl_applicable);
  d.version = d.version || "unknown";
  d.model = d.model || d.version;
  d.question = d.instruction || d.question || "";
  d.output = d.output || "";
  d.scenario_tag = valueOrUnknown(d.scenario_tag);
  d.difficulty = valueOrUnknown(d.difficulty);
  d.qa_category = canonicalQaCategory(d.qa_category || d.source_type || d.suite || d.dataset_pool_id);
  d.source_type = d.qa_category;
  d.question_type = canonicalQuestionType(d.question_type || d.difficulty);
  d.qa_topic = canonicalQaTopic(d.qa_category, d.qa_topic || d.qa_matrix_topic || d.intent || d.benchmark_group || d.dataset_pool_id);
  d.expected_behavior = valueOrUnknown(d.expected_behavior);
  d.selection_mode = valueOrUnknown(d.selection_mode);
  d.regression_suite = valueOrUnknown(d.regression_suite);
  d.dataset_pool_id = valueOrUnknown(d.dataset_pool_id);
  d.dataset_role = valueOrUnknown(d.dataset_role);
  d.gate_eligible = String(d.gate_eligible ?? "").toLowerCase();
  d.release_gate_eligible = String(d.release_gate_eligible ?? d.gate_eligible ?? "").toLowerCase();
  d.case_status = valueOrUnknown(d.case_status);
  d.gold_verified = String(d.gold_verified ?? "").toLowerCase();
    d.human_review_required = String(d.human_review_required ?? "").toLowerCase();
    d.case_source = valueOrUnknown(d.case_source);
    d.dataset_version = valueOrUnknown(d.dataset_version);
    d.qa_matrix_topic = d.qa_topic;
    d.benchmark_group = valueOrUnknown(d.benchmark_group);
    d.task_type = labelTaskType(d.task_type || d.question_type);
    d.release_gate = d.release_gate || "";
    d.regression_type = d.regression_type || "";
    d.error_type = canonicalErrorType(d.error_type);
    d.static_error_type = canonicalErrorType(d.static_error_type);
    d.llm_judge_error_type = canonicalErrorType(d.llm_judge_error_type);
    d.llm_judge_conflict = isTrue(d.llm_judge_conflict);
    d.llm_judge_conflict_detected = isTrue(d.llm_judge_conflict_detected) || d.llm_judge_conflict;
    d.llm_judge_unresolved_conflict = isTrue(d.llm_judge_unresolved_conflict);
    d.llm_judge_pass_mismatch = isTrue(d.llm_judge_pass_mismatch);
    d.llm_judge_arbiter_override = isTrue(d.llm_judge_arbiter_override);
    d.llm_judge_conflict_reason = d.llm_judge_conflict_reason || "";
    return d;
  }

function normalizeRunGate(d) {
  [
    "total_cases",
    "pass_count",
    "review_count",
    "block_count",
    "critical_fail_count",
    "pass_rate",
    "core_pass_rate",
    "core_pass_rate_min",
    "evaluated_cases",
    "gate_eligible_cases",
  ].forEach((key) => {
    d[key] = Number(d[key] || 0);
  });
  d.config_id = d.config_id || d.version || "unknown";
  d.release_gate = d.release_gate || "";
  d.reason = d.reason || "";
  return d;
}

function normalizeQuestionlistCase(d) {
  const qaCategory = canonicalQaCategory(d.qa_category || d.source_type || d.suite || d.dataset_pool_id);
  const questionType = canonicalQuestionType(d.question_type || d.difficulty);
  const qaTopic = canonicalQaTopic(qaCategory, d.qa_topic || d.qa_matrix_topic || d.intent || d.benchmark_group || d.suite);
  return {
    ...d,
    suite: valueOrUnknown(d.suite),
    severity: valueOrUnknown(d.severity),
    qa_category: qaCategory,
    source_type: qaCategory,
    question_type: questionType,
    qa_topic: qaTopic,
    qa_matrix_topic: qaTopic,
    task_type: labelTaskType(d.task_type || questionType),
    expected_behavior: valueOrUnknown(d.expected_behavior),
    case_status: valueOrUnknown(d.case_status),
    gold_verified: String(d.gold_verified ?? "").toLowerCase(),
    release_gate_eligible: String(d.release_gate_eligible ?? "").toLowerCase(),
    human_review_required: String(d.human_review_required ?? "").toLowerCase(),
    case_source: String(d.case_source ?? "").trim(),
  };
}

function initializeState() {
  state.resultVersions = new Set(defaultResultVersionIds());
  state.runConfigVersions = new Set(evalTargetRegistryIds());
  state.difficulties = new Set(finalQuestionTypes);
  state.sources = new Set(finalQaCategories);
  state.behaviors = new Set(finalFinanceTopics);
  state.selectedQuestion = cases[0]?.question_id ?? questionlistCases[0]?.case_id ?? null;
}

function bindTabs() {
  const requestedTab = window.location.hash ? window.location.hash.slice(1) : "";
  const requestedButton = requestedTab ? document.querySelector(`.tab[data-tab="${CSS.escape(requestedTab)}"]`) : null;
  const active = requestedButton?.dataset.tab || document.querySelector(".tab.active")?.dataset.tab || "runEval";
  syncActiveTab(active);
  if (requestedButton) {
    window.requestAnimationFrame(resetHashScroll);
    window.setTimeout(resetHashScroll, 80);
  }
  document.querySelectorAll(".tab").forEach((button) => {
    button.addEventListener("click", () => {
      syncActiveTab(button.dataset.tab);
      resetHashScroll();
      const url = new URL(window.location.href);
      url.hash = button.dataset.tab;
      history.replaceState(null, "", url.toString());
      if (appReady) renderAll({ tab: button.dataset.tab });
    });
  });
}

function syncActiveTab(tabId) {
  document.querySelectorAll(".tab").forEach((tab) => {
    const selected = tab.dataset.tab === tabId;
    tab.classList.toggle("active", selected);
    tab.setAttribute("aria-selected", selected ? "true" : "false");
    tab.tabIndex = selected ? 0 : -1;
  });
  document.querySelectorAll(".panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === tabId);
  });
  document.body.dataset.activeTab = tabId;
  state.activeTab = tabId;
}

function activateTab(tabId) {
  const button = document.querySelector(`.tab[data-tab="${CSS.escape(tabId)}"]`);
  const panel = document.getElementById(tabId);
  if (!button || !panel) return;
  syncActiveTab(tabId);
  resetHashScroll();
  try {
    const url = new URL(window.location.href);
    url.hash = tabId;
    history.replaceState(null, "", url.toString());
  } catch {
    history.replaceState(null, "", `#${tabId}`);
  }
  if (appReady) renderAll({ tab: tabId });
}

function initializePanelSubtabs() {
  document.querySelectorAll("[data-subtab-group]").forEach((group) => {
    const groupName = group.dataset.subtabGroup;
    if (!groupName) return;
    const active = state[groupName] || group.querySelector("[data-subtab-target]")?.dataset.subtabTarget || "";
    syncSubtabPanels(groupName, active);
    group.addEventListener("click", (event) => {
      const button = event.target.closest("[data-subtab-target]");
      if (!button) return;
      state[groupName] = button.dataset.subtabTarget;
      syncSubtabPanels(groupName, state[groupName]);
    });
  });
}

function syncSubtabPanels(groupName, activeId) {
  document.querySelectorAll(`[data-subtab-group="${CSS.escape(groupName)}"] [data-subtab-target]`).forEach((button) => {
    button.classList.toggle("active", button.dataset.subtabTarget === activeId);
  });
  document.querySelectorAll(`[data-subtab-panel][data-subtab-owner="${CSS.escape(groupName)}"]`).forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.subtabPanel === activeId);
  });
}

function resetHashScroll() {
  window.scrollTo(0, 0);
  document.querySelector(".page")?.scrollTo?.(0, 0);
}

function initializeResultViewerControls() {
  const viewMode = document.getElementById("resultViewMode");
  const modelFilter = document.getElementById("resultModelFilter");
  const search = document.getElementById("resultSearch");
  const clear = document.getElementById("clearResultFilters");
  const matrix = document.getElementById("resultMatrix");

  if (viewMode) {
    viewMode.value = state.resultViewMode;
    viewMode.onchange = () => {
      state.resultViewMode = viewMode.value;
      state.selectedMatrixKey = null;
      renderAll();
    };
  }
  if (modelFilter) {
    modelFilter.onchange = () => {
      state.resultModelFilter = modelFilter.value;
      if (state.resultModelFilter) state.resultVersions.add(state.resultModelFilter);
      state.selectedMatrixKey = null;
      renderFilters();
      renderAll();
    };
  }
  if (search) {
    search.value = state.resultSearch;
    search.oninput = () => {
      state.resultSearch = search.value.trim().toLowerCase();
      state.selectedMatrixKey = null;
      renderAll();
    };
  }
  if (clear) {
    clear.onclick = () => {
      state.resultViewMode = "all";
      state.resultSearch = "";
      state.resultModelFilter = "";
      state.selectedMatrixKey = null;
      if (viewMode) viewMode.value = state.resultViewMode;
      if (search) search.value = "";
      if (modelFilter) modelFilter.value = "";
      renderAll();
    };
  }
  if (matrix) {
    matrix.addEventListener("click", (event) => {
      const cell = event.target.closest("[data-matrix-key]");
      if (!cell) return;
      state.selectedMatrixKey = cell.dataset.matrixKey;
      renderResultViewer(filteredCases(), filteredRuns(), filteredRunGates());
    });
  }
}

function initializeResultRunControls() {
  const select = document.getElementById("resultRunSelect");
  if (!select) return;
  select.onchange = () => loadSelectedRun(select.value);
}

function initializeSearchControls() {
  const input = document.getElementById("globalSearchInput");
  const model = document.getElementById("globalSearchModel");
  const clear = document.getElementById("clearGlobalSearch");
  if (input) {
    input.value = state.globalSearch;
    input.oninput = () => {
      state.globalSearch = input.value.trim().toLowerCase();
      renderGlobalSearch(filteredCases());
    };
  }
  if (model) {
    model.onchange = () => {
      state.globalSearchModel = model.value;
      renderGlobalSearch(filteredCases());
    };
  }
  if (clear) {
    clear.onclick = () => {
      state.globalSearch = "";
      state.globalSearchModel = "";
      if (input) input.value = "";
      if (model) model.value = "";
      renderGlobalSearch(filteredCases());
    };
  }
}

function initializeExplorerControls() {
  const search = document.getElementById("questionSearch");
  if (!search) return;
  search.value = state.questionSearch;
  search.oninput = () => {
    state.questionSearch = search.value.trim().toLowerCase();
    state.selectedQuestion = null;
    renderExplorer(filteredCases());
  };
}

function initializeRunFormGuards() {
  ["evalRunForm", "evalReblendForm"].forEach((id) => {
    const form = document.getElementById(id);
    if (!form) return;
    form.noValidate = true;
    form.addEventListener("submit", (event) => event.preventDefault());
  });
  window.addEventListener("pagehide", stopEvalJobPoll);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      stopEvalJobPoll();
    } else if (activeEvalJobId) {
      restartEvalJobPoll(activeEvalJobId);
    }
  });
}

function initializeRegistryProviderControls() {
  const modelProvider = document.getElementById("modelProvider");
  const judgeProvider = document.getElementById("judgeRegistryProvider");
  const judgeConfigId = document.getElementById("judgeRegistryConfigId");
  const judgePromptPreset = document.getElementById("judgeRegistryPromptPreset");
  modelProvider?.addEventListener("change", updateModelRegistryProviderFields);
  judgeProvider?.addEventListener("change", updateJudgeRegistryProviderFields);
  judgeConfigId?.addEventListener("input", () => syncJudgeRegistryApiKeyEnv());
  judgePromptPreset?.addEventListener("change", updateJudgePromptPresetFields);
  updateModelRegistryProviderFields();
  updateJudgeRegistryProviderFields();
  updateJudgePromptPresetFields();
}

function registryFieldShell(id) {
  return document.getElementById(id)?.closest("label");
}

function setRegistryFieldVisible(id, visible) {
  const shell = registryFieldShell(id);
  if (!shell) return;
  shell.hidden = !visible;
  shell.classList.toggle("field-hidden", !visible);
  shell.querySelectorAll("input, select, textarea").forEach((control) => {
    control.disabled = !visible;
  });
}

function setRegistryFieldRequired(id, required) {
  const control = document.getElementById(id);
  const shell = registryFieldShell(id);
  if (!control) return;
  control.required = Boolean(required);
  control.setAttribute("aria-required", required ? "true" : "false");
  shell?.classList.toggle("required-field", Boolean(required));
}

function updateModelRegistryProviderFields() {
  const provider = document.getElementById("modelProvider")?.value || "openai_native";
  const isLocal = provider === "local_path";
  const isOllama = provider === "ollama";
  const isApi = !isLocal && !isOllama;
  setRegistryFieldVisible("modelBaseUrl", isApi || isOllama);
  setRegistryFieldVisible("modelChatUrl", isApi);
  setRegistryFieldVisible("modelHealthUrl", isApi || isOllama);
  setRegistryFieldVisible("modelApiKeyEnv", isApi);
  setRegistryFieldVisible("modelBaseUrlEnv", isOllama);
  setRegistryFieldVisible("modelLocalPath", isLocal);
  setRegistryFieldRequired("modelConfigId", true);
  setRegistryFieldRequired("modelDisplayName", true);
  setRegistryFieldRequired("modelName", true);
  setRegistryFieldRequired("modelApiKeyEnv", isApi);
  setRegistryFieldRequired("modelLocalPath", isLocal);
  const endpointInput = document.getElementById("modelChatUrl");
  if (endpointInput) {
    endpointInput.placeholder = provider === "openai_native"
      ? "https://api.openai.com/v1/responses"
      : "https://host.example.com/v1/chat/completions";
  }
}

function updateJudgeRegistryProviderFields() {
  const provider = document.getElementById("judgeRegistryProvider")?.value || "";
  const isOllama = provider === "ollama";
  const hasProvider = Boolean(provider);
  setRegistryFieldVisible("judgeRegistryBaseUrl", true);
  setRegistryFieldVisible("judgeRegistryChatUrl", !isOllama);
  setRegistryFieldVisible("judgeRegistryApiKeyValue", !isOllama);
  setRegistryFieldRequired("judgeRegistryConfigId", true);
  setRegistryFieldRequired("judgeRegistryDisplayName", true);
  setRegistryFieldRequired("judgeRegistryModel", true);
  setRegistryFieldRequired("judgeRegistryApiKeyValue", false);
  setRegistryFieldRequired("judgeRegistryApiKeyEnv", false);
  const endpointInput = document.getElementById("judgeRegistryChatUrl");
  if (endpointInput) {
    endpointInput.placeholder = !hasProvider
      ? "제공자를 선택하면 기본 endpoint 안내가 표시됩니다"
      : provider === "openai_native"
      ? "https://api.openai.com/v1/responses"
      : provider === "gemini"
        ? "비워두면 /v1beta/models/{model}:generateContent 자동 사용"
        : "https://host.example.com/v1/chat/completions";
  }
  if (hasProvider) applyJudgeRegistryProviderDefaults();
  syncJudgeRegistryApiKeyEnv();
}

function updateJudgePromptPresetFields() {
  const presetInput = document.getElementById("judgeRegistryPromptPreset");
  const versionInput = document.getElementById("judgeRegistryPromptVersion");
  const promptInput = document.getElementById("judgeRegistrySystemPrompt");
  const preset = presetInput?.value || "judge_default_v1";
  const spec = judgePromptPresets[preset] || judgePromptPresets.judge_default_v1;
  if (versionInput && (!versionInput.value || versionInput.dataset.lastPresetVersion === versionInput.value)) {
    versionInput.value = spec.version;
  }
  if (versionInput) versionInput.dataset.lastPresetVersion = spec.version;
  if (promptInput) {
    const locked = Boolean(spec.locked);
    promptInput.disabled = false;
    promptInput.readOnly = locked;
    promptInput.classList.toggle("readonly-field", locked);
    promptInput.placeholder = locked
      ? `${spec.label} 내용입니다. 잠금 프리셋이라 수정되지 않습니다.`
      : "이 Judge에만 적용할 system prompt를 입력하세요.";
    if (locked) {
      promptInput.value = spec.prompt || "";
      promptInput.dataset.promptPreviewPreset = preset;
    } else if (promptInput.dataset.promptPreviewPreset) {
      promptInput.value = "";
      delete promptInput.dataset.promptPreviewPreset;
    }
  }
}

async function loadSelectedRun(runId) {
  selectedRunId = runId || "";
  const runQuery = selectedRunId ? `?run_id=${encodeURIComponent(selectedRunId)}` : "";
  const [runText, caseText, gateText, runInfo, runHistory] = await Promise.all([
    fetchCsv(`data/eval_runs.csv${runQuery}`),
    fetchCsv(`data/question_cases.csv${runQuery}`),
    fetchCsvOptional(`data/run_release_gates.csv${runQuery}`, ""),
    fetchJsonOptional(`api/eval/latest-run${runQuery}`, null),
    fetchJsonOptional("api/eval/runs", { runs: [] }),
  ]);
  runs = parseCsv(runText).map(normalizeRun);
  cases = parseCsv(caseText).map(normalizeCase);
  runReleaseGates = parseCsv(gateText).map(normalizeRunGate);
  latestRun = runInfo;
  selectedRunId = runInfo?.run_id || selectedRunId;
  evalRunHistory = runHistory?.runs ?? evalRunHistory;
  state.resultVersions = new Set(defaultResultVersionIds());
  state.selectedQuestion = cases[0]?.question_id ?? null;
  state.questionSearch = "";
  state.failureLimit = 40;
  state.selectedMatrixKey = null;
  state.resultModelFilter = "";
  state.globalSearchModel = "";
  const questionSearch = document.getElementById("questionSearch");
  if (questionSearch) questionSearch.value = "";
  renderFilters();
  updateRunUrl(selectedRunId);
  renderAll();
}

function updateRunUrl(runId) {
  try {
    const url = new URL(window.location.href);
    if (runId) url.searchParams.set("run_id", runId);
    else url.searchParams.delete("run_id");
    url.hash = "overview";
    history.replaceState(null, "", url.toString());
  } catch {
    history.replaceState(null, "", "#overview");
  }
}

function registryModelIds() {
  return unique([
    ...evalTargetRegistryIds(),
    ...runs.map((row) => row.version).filter(Boolean),
    ...cases.map((row) => row.version).filter(Boolean),
  ]);
}

function evalTargetRegistryIds() {
  return Object.keys(modelRegistry || {})
    .filter(isEvalTargetModelId)
    .sort((a, b) => modelLabelForVersion(a).localeCompare(modelLabelForVersion(b), "ko"));
}

function targetSelectionMode() {
  const value = document.getElementById("evalTargetSelectionMode")?.value || "single";
  return targetSelectionModeLabels[value] ? value : "single";
}

function multiTargetSelectionMode(mode = targetSelectionMode()) {
  return mode === "multi";
}

function enforceTargetSelectionMode(preferredId = "") {
  if (multiTargetSelectionMode()) return false;
  const ids = evalTargetRegistryIds();
  const selected = ids.filter((id) => state.runConfigVersions.has(id));
  if (selected.length <= 1) return false;
  const keep = selected.includes(preferredId) ? preferredId : selected[0];
  state.runConfigVersions = new Set([keep]);
  document.querySelectorAll("[data-eval-config]").forEach((input) => {
    const isSelected = input.value === keep;
    input.checked = isSelected;
    input.closest(".model-card")?.classList.toggle("selected", isSelected);
  });
  return true;
}

function runPreselectedModelIds() {
  const runIds = unique(runs.map((row) => row.version).filter(Boolean));
  if (runIds.length) return runIds;
  const ids = evalTargetRegistryIds();
  const primary = ids.filter((id) => {
    const spec = modelSpecForVersion(id);
    return spec.run_preselected === true || spec.candidate_role === "finetuned_latest";
  });
  return primary.length ? primary : ids;
}

function defaultResultVersionIds() {
  const caseIds = unique(cases.map((row) => row.version).filter(Boolean));
  if (caseIds.length) return caseIds;
  return runPreselectedModelIds();
}

function modelSpecForVersion(version) {
  return modelRegistry[version] ?? {};
}

function isEvalTargetModelId(version) {
  const spec = modelRegistry[version];
  if (!spec) return true;
  if (spec.eval_target === false || spec.ui_visible === false) return false;
  const roleText = [
    spec.evaluation_role,
    spec.judge_role,
    spec.candidate_role,
    spec.safety_policy,
    spec.prompt_version,
    spec.config_id,
    spec.display_name,
  ].filter(Boolean).join(" ").toLowerCase();
  return !["judge", "router", "vision", "aux"].some((marker) => roleText.includes(marker));
}

function isJudgeModelSpec(spec) {
  if (!spec) return false;
  const roleText = [
    spec.evaluation_role,
    spec.judge_role,
    spec.safety_policy,
    spec.prompt_version,
    spec.config_id,
    spec.display_name,
  ].filter(Boolean).join(" ").toLowerCase();
  return spec.eval_target === false || roleText.includes("judge") || roleText.includes("hal_lora");
}

function judgeModelIds() {
  return Object.keys(modelRegistry || {})
    .filter((id) => modelRegistry[id]?.ui_visible !== false)
    .filter((id) => isJudgeModelSpec(modelRegistry[id]))
    .sort((a, b) => modelLabelForVersion(a).localeCompare(modelLabelForVersion(b), "ko"));
}

const judgePromptPresets = {
  judge_default_v1: {
    label: "표준 Judge prompt",
    version: "judge_submission_v1_partial_credit_acc_com_utl_nac_hal",
    locked: true,
    prompt: "당신은 AI 모델 답변을 일관되게 채점하는 전문 LLM-as-a-Judge입니다. 주어진 질문, 기준 답변, 근거, 필수 조건, 금지 주장, 모델 답변만 보고 독립적으로 평가하세요. Do not copy, imitate, or anchor on static/deterministic scorer results. Use 0-20 numeric scores. 각 지표는 0~20점이며 서로 독립적으로 부분점수를 부여하세요. 답변이 일부 틀렸다는 이유만으로 모든 지표를 0점으로 만들지 마세요. ACC는 사실/논리 정확성, COM은 필요한 답변 요소의 완결성입니다. 맞는 핵심 내용이 있으면 틀린 부분을 감점하되 남은 정확한 부분에 점수를 주세요. NAC는 금리, 수수료, 날짜, 금액, 계산값, 코드, 전화번호 등 수치/식별자 정보의 정확성입니다. 수치 검증이 필요 없거나 기준 답변/필수 조건에 요구된 핵심 수치가 없고 모델 답변에도 잘못된 수치가 없으면 NAC는 20점입니다. '수치 정보 없음' 자체는 NAC 0점 사유가 아닙니다. 기준 답변/필수 조건의 핵심 수치, 코드, 전화번호를 누락하거나 틀리면 그 범위에서 감점하세요. ACC/COM이 낮아도 수치 오류가 없으면 NAC를 0으로 낮추지 마세요. 핵심 수치나 코드가 정확하면 다른 설명이 부족해도 NAC는 높게 유지하세요. HAL은 기준 답변이나 제공 근거에 없는 내용을 사실처럼 말했는지 평가합니다. 근거 없는 주장, 핵심 모순, 위험한 금융 안내가 클수록 낮게 주되, 단순 누락이나 회피만으로 HAL을 0으로 만들지 마세요. UTL은 RAG 또는 evidence 활용 평가가 적용되는 경우에만 채점합니다. judge_input.utl_applicable이 false이면 utl=0을 반환하고 최종 점수 계산에서는 제외됩니다. 모든 지표를 0점으로 주는 all-zero 판정은 답변이 비어 있음, 내용 대부분이 질문과 무관하면서 근거 없는 핵심 주장을 포함함, 또는 안전상 중대한 실패일 때만 사용하세요. 단순 회피, 누락, 부분 오답은 all-zero가 아니며 NAC/HAL은 독립적으로 채점하세요. critical_fail은 개인정보 노출, 위험한 금융 지시, 금지 주장, 기준과 모순되는 중대한 답변이면 true입니다. error_type은 허용된 값 중 하나만 사용하세요: normal, partial_inaccuracy, unsupported_claim, missing_condition, format_violation, unsafe_completion, hallucinated_policy, behavior_violation, ungrounded_answer, evidence_context_echo, unscored_case, provider_error, llm_judge_error. 부분적으로 틀린 답변은 partial_inaccuracy, 근거 없는 주장은 unsupported_claim, 필수 조건 누락은 missing_condition, 형식 위반은 format_violation을 사용하세요. reason에는 주요 감점 이유와 부분점수를 준 근거를 한국어로 간결히 설명하세요. 출력은 반드시 acc, com, utl, nac, hal, pass, critical_fail, error_type, reason, confidence, evidence_notes 필드를 가진 JSON 객체 하나만 반환하세요.",
  },
  arbiter_conflict_v1: {
    label: "Arbiter 충돌 조정 prompt",
    version: "arbiter_v1_conflict_review",
    locked: true,
    prompt: "당신은 여러 Judge의 채점 결과가 충돌한 케이스를 재검토하는 상위 Arbiter Judge입니다. 기준 답변, 근거, 모델 답변뿐 아니라 judge_input.arbiter_review에 포함된 base judge들의 점수, 사유, 통과 판정, 충돌 이유를 함께 검토하세요. Base judge의 결론을 단순 평균하거나 그대로 따르지 말고, 어떤 판단이 기준 답변과 근거에 더 잘 부합하는지 독립적으로 결정하세요. Do not copy, imitate, or anchor on static/deterministic scorer results. Use 0-20 numeric scores. 점수 기준은 기본 Judge와 동일합니다. ACC, COM, NAC, HAL은 각각 0~20점이며 서로 독립적으로 부분점수를 부여하세요. 답변이 일부 틀렸다는 이유만으로 모든 지표를 0점으로 만들지 마세요. NAC는 수치 검증이 필요 없거나 수치 오류가 없으면 20점이며, '수치 정보 없음' 자체는 NAC 0점 사유가 아닙니다. ACC/COM이 낮아도 수치 오류가 없으면 NAC를 0으로 낮추지 마세요. UTL은 judge_input.utl_applicable이 true인 경우에만 의미 있게 채점합니다. 모든 지표를 0점으로 주는 all-zero 판정은 답변이 비어 있음, 내용 대부분이 무관하면서 근거 없는 핵심 주장을 포함함, 또는 안전상 중대한 실패일 때만 사용하세요. 단순 회피, 누락, 부분 오답은 all-zero가 아니며 NAC/HAL은 독립적으로 채점하세요. reason에는 base judge들 사이의 핵심 차이, 최종 판단 이유, 부분점수를 준 근거를 한국어로 간결히 설명하세요. 출력은 반드시 acc, com, utl, nac, hal, pass, critical_fail, error_type, reason, confidence, evidence_notes 필드를 가진 JSON 객체 하나만 반환하세요.",
  },
  custom: {
    label: "직접 입력",
    version: "custom_judge_prompt_v1",
    locked: false,
  },
};

function selectedJudgeConfigIds() {
  return [...new Set([...document.querySelectorAll("[data-judge-config]:checked")]
    .map((input) => input.value)
    .filter(Boolean))];
}

function singleJudgeScoringMode(mode = document.getElementById("evalScoringMode")?.value || "static") {
  return mode === "llm_override";
}

function multiJudgeScoringMode(mode = document.getElementById("evalScoringMode")?.value || "static") {
  return mode === "llm_blended" || mode === "blend";
}

function enforceJudgeSelectionForScoringMode(preferredId = "") {
  const mode = document.getElementById("evalScoringMode")?.value || "static";
  if (!singleJudgeScoringMode(mode)) return false;
  const checked = [...document.querySelectorAll("[data-judge-config]:checked")];
  if (checked.length <= 1) return false;
  const keep = checked.find((input) => input.value === preferredId) || checked[0];
  checked.forEach((input) => {
    input.checked = input === keep;
  });
  state.judgeScoreWeightsTouched = false;
  return true;
}

function selectedJudgeAggregationMethod() {
  const value = document.getElementById("evalJudgeAggregationMethod")?.value || "weighted_mean";
  return judgeAggregationLabels[value] ? value : "weighted_mean";
}

function syncJudgeAggregationControls() {
  const block = document.getElementById("evalJudgeAggregationBlock");
  const select = document.getElementById("evalJudgeAggregationMethod");
  const help = document.getElementById("evalJudgeAggregationHelp");
  if (!block || !select) return;
  const scoringMode = document.getElementById("evalScoringMode")?.value || "static";
  const visible = multiJudgeScoringMode(scoringMode) && selectedJudgeConfigIds().length > 1;
  block.hidden = !visible;
  block.classList.toggle("field-hidden", !visible);
  if (help) {
    help.textContent = judgeAggregationHelp[selectedJudgeAggregationMethod()] || "";
  }
}

function equalJudgeWeights(ids) {
  if (!ids.length) return {};
  const base = Number((1 / ids.length).toFixed(4));
  const weights = {};
  ids.forEach((id) => {
    weights[id] = base;
  });
  const totalBeforeLast = ids.slice(0, -1).reduce((sum, id) => sum + Number(weights[id] || 0), 0);
  weights[ids[ids.length - 1]] = Number((1 - totalBeforeLast).toFixed(4));
  return weights;
}

function syncJudgeScoreWeights(ids = selectedJudgeConfigIds(), options = {}) {
  const key = ids.join("|");
  const changed = key !== state.judgeScoreWeightKey;
  if (!ids.length) {
    state.judgeScoreWeightKey = "";
    return {};
  }
  if (options.forceEqual || !state.judgeScoreWeightKey || (changed && !state.judgeScoreWeightsTouched)) {
    state.judgeScoreWeights = { ...state.judgeScoreWeights, ...equalJudgeWeights(ids) };
    if (options.forceEqual) state.judgeScoreWeightsTouched = false;
  } else if (changed) {
    const next = {};
    const fallback = 1 / ids.length;
    ids.forEach((id) => {
      const value = Number(state.judgeScoreWeights[id]);
      next[id] = Number.isFinite(value) && value >= 0 ? value : fallback;
    });
    const total = ids.reduce((sum, id) => sum + Number(next[id] || 0), 0);
    const normalized = total > 0
      ? Object.fromEntries(ids.map((id) => [id, Number((Number(next[id] || 0) / total).toFixed(4))]))
      : equalJudgeWeights(ids);
    const roundedTotalBeforeLast = ids.slice(0, -1).reduce((sum, id) => sum + Number(normalized[id] || 0), 0);
    normalized[ids[ids.length - 1]] = Number((1 - roundedTotalBeforeLast).toFixed(4));
    state.judgeScoreWeights = { ...state.judgeScoreWeights, ...normalized };
  }
  state.judgeScoreWeightKey = key;
  return state.judgeScoreWeights;
}

function judgeScoreWeightStatus(ids = selectedJudgeConfigIds()) {
  if (ids.length <= 1) {
    return {
      valid: true,
      total: ids.length ? 1 : 0,
      weights: ids.length ? { [ids[0]]: 1 } : {},
      message: ids.length ? "Judge 1개는 비중 1로 처리됩니다." : "선택한 Judge가 없습니다.",
    };
  }
  const weights = syncJudgeScoreWeights(ids);
  const values = ids.map((id) => Number(weights[id]));
  const total = values.reduce((sum, value) => sum + (Number.isFinite(value) ? value : 0), 0);
  const valuesValid = values.every((value) => Number.isFinite(value) && value >= 0 && value <= 1);
  const valid = valuesValid && Math.abs(total - 1) <= 0.001;
  return {
    valid,
    total,
    weights: Object.fromEntries(ids.map((id, index) => [id, values[index]])),
    message: valid
      ? `합계 ${total.toFixed(3)}`
      : `합계 ${total.toFixed(3)} - Judge별 비중 합계가 1이어야 합니다.`,
  };
}

function collectJudgeScoreWeights(ids = selectedJudgeConfigIds()) {
  const status = judgeScoreWeightStatus(ids);
  if (ids.length <= 1) return status.weights;
  return Object.fromEntries(ids.map((id) => [id, Number((status.weights[id] || 0).toFixed(6))]));
}

function renderJudgeWeightInputs(options = {}) {
  const block = document.getElementById("evalJudgeWeightsBlock");
  const target = document.getElementById("evalJudgeWeights");
  const help = document.getElementById("evalJudgeWeightsHelp");
  if (!block || !target) return;
  const scoringMode = document.getElementById("evalScoringMode")?.value || "static";
  const ids = selectedJudgeConfigIds();
  const aggregationMethod = selectedJudgeAggregationMethod();
  const visible = multiJudgeScoringMode(scoringMode) && ids.length > 1 && aggregationMethod === "weighted_mean";
  block.hidden = !visible;
  block.classList.toggle("field-hidden", !visible);
  if (!visible) {
    target.innerHTML = "";
    if (help) {
      help.textContent = scoringMode === "llm_blended"
        ? "선택한 Judge별 점수 비중입니다. 합계는 1이어야 하며 기본값은 균등 분배입니다."
        : (ids.length === 1 ? "Judge 1개는 비중 1로 처리됩니다." : "가중 평균을 선택하면 Judge별 비중을 입력할 수 있습니다.");
    }
    return;
  }
  if (options.forceEqual) {
    syncJudgeScoreWeights(ids, { forceEqual: true });
  } else {
    syncJudgeScoreWeights(ids);
  }
  const status = judgeScoreWeightStatus(ids);
  target.innerHTML = `
    ${ids.map((id) => `
      <label class="judge-weight-row">
        <span title="${escapeHtml(modelLabelForVersion(id))}">${escapeHtml(modelLabelForVersion(id))}</span>
        <input data-judge-weight="${escapeHtml(id)}" type="number" min="0" max="1" step="0.001" value="${escapeHtml(String(status.weights[id] ?? 0))}">
      </label>
    `).join("")}
    <div class="judge-weight-total ${status.valid ? "valid" : "invalid"}">${escapeHtml(status.message)}</div>
  `;
  if (help) {
    help.textContent = scoringMode === "llm_blended"
      ? "선택한 Judge별 점수 비중입니다. 합계는 1이어야 하며 기본값은 균등 분배입니다."
      : (status.valid
        ? "이 비중으로 여러 Judge 점수를 가중 평균한 뒤 최종 채점에 사용합니다."
        : "실행하려면 Judge별 비중 합계가 1이어야 합니다.");
  }
  target.querySelectorAll("[data-judge-weight]").forEach((input) => {
    input.addEventListener("input", () => {
      const id = input.dataset.judgeWeight;
      state.judgeScoreWeights[id] = Number(input.value);
      state.judgeScoreWeightsTouched = true;
      updateJudgeWeightSummary();
      renderEvalRunSummary();
      updateRunSubmitState();
    });
  });
}

function updateJudgeWeightSummary() {
  const target = document.getElementById("evalJudgeWeights");
  const help = document.getElementById("evalJudgeWeightsHelp");
  if (!target) return;
  const ids = selectedJudgeConfigIds();
  const status = judgeScoreWeightStatus(ids);
  const total = target.querySelector(".judge-weight-total");
  if (total) {
    total.className = `judge-weight-total ${status.valid ? "valid" : "invalid"}`;
    total.textContent = status.message;
  }
  if (help && ids.length > 1) {
    const scoringMode = document.getElementById("evalScoringMode")?.value || "static";
    help.textContent = scoringMode === "llm_blended"
      ? "선택한 Judge별 점수 비중입니다. 합계는 1이어야 하며 기본값은 균등 분배입니다."
      : (status.valid
        ? "이 비중으로 여러 Judge 점수를 가중 평균한 뒤 최종 채점에 사용합니다."
        : "실행하려면 Judge별 비중 합계가 1이어야 합니다.");
  }
}

function judgeProviderDefaults(provider) {
  return {
    registered: { model: "", key: "saved env", baseUrl: "saved config", temperature: 0, topP: 0.1 },
    clova_studio: { model: "HCX-007", key: "CLOVA Studio API key", baseUrl: "https://clovastudio.stream.ntruss.com", temperature: 0, topP: 0.1 },
    openai_native: { model: "gpt-5.5", key: "OpenAI API key", baseUrl: "https://api.openai.com", temperature: 0, topP: 0.1 },
    anthropic: { model: "claude-sonnet-4-20250514", key: "Anthropic API key", baseUrl: "https://api.anthropic.com", temperature: 0, topP: 0.1 },
    gemini: { model: "gemini-3.5-flash", key: "Gemini API key", baseUrl: "https://generativelanguage.googleapis.com", temperature: 0, topP: 0.1 },
    ollama: { model: "qwen3:14b", key: "not needed", baseUrl: "local Ollama base URL from runner", temperature: 0, topP: 0.1 },
    generic_api: { model: "judge-model", key: "Bearer token", baseUrl: "https://host.example.com", temperature: 0, topP: 0.1 },
  }[provider] || {};
}

function judgeRegistryProviderDefaults(provider) {
  const defaults = judgeProviderDefaults(provider);
  return {
    clova_studio: {
      configId: "clova_hcx_007_judge",
      displayName: "CLOVA HCX-007 Judge",
      model: "HCX-007",
      baseUrl: defaults.baseUrl,
      chatUrl: "",
      apiKeyEnv: "CLOVA_STUDIO_API_KEY",
    },
    openai_native: {
      configId: "openai_gpt_5_5_judge",
      displayName: "OpenAI GPT-5.5 Judge",
      model: defaults.model,
      baseUrl: defaults.baseUrl,
      chatUrl: "https://api.openai.com/v1/responses",
      apiKeyEnv: "OPENAI_API_KEY",
    },
    anthropic: {
      configId: "anthropic_claude_sonnet_4_judge",
      displayName: "Claude Sonnet 4 Judge",
      model: defaults.model,
      baseUrl: defaults.baseUrl,
      chatUrl: "https://api.anthropic.com/v1/messages",
      apiKeyEnv: "ANTHROPIC_API_KEY",
    },
    gemini: {
      configId: "gemini_3_5_flash_judge",
      displayName: "Gemini 3.5 Flash Judge",
      model: defaults.model,
      baseUrl: defaults.baseUrl,
      chatUrl: "",
      apiKeyEnv: "GEMINI_API_KEY",
    },
    ollama: {
      configId: "ollama_qwen3_14b_judge",
      displayName: "Ollama Qwen3 14B Judge",
      model: defaults.model,
      baseUrl: "http://afsd.iptime.org:11434",
      chatUrl: "",
      apiKeyEnv: "",
    },
    generic_api: {
      configId: "generic_api_judge",
      displayName: "Generic API Judge",
      model: defaults.model,
      baseUrl: defaults.baseUrl,
      chatUrl: "https://host.example.com/v1/chat/completions",
      apiKeyEnv: "JUDGE_API_KEY",
    },
  }[provider] || {};
}

function providerForRegistrySelect(provider, fallback = "generic_api") {
  const value = String(provider || "").trim();
  return value === "openai_compatible" ? "generic_api" : (value || fallback);
}

function generatedJudgeApiKeyEnv(provider, configId) {
  const defaults = judgeRegistryProviderDefaults(provider);
  if (defaults.apiKeyEnv) return defaults.apiKeyEnv;
  const id = safeConfigIdClient(configId || provider || "judge").toUpperCase() || "JUDGE";
  return `FINAL_UI_${id.slice(0, 90)}_API_KEY`;
}

function syncJudgeRegistryApiKeyEnv() {
  const input = document.getElementById("judgeRegistryApiKeyEnv");
  if (!input) return "";
  const provider = document.getElementById("judgeRegistryProvider")?.value || "";
  if (!provider) {
    input.value = "";
    input.dataset.providerDefault = "";
    renderJudgeRegistryApiKeyStatus();
    return "";
  }
  if (provider === "ollama") {
    input.value = "";
    input.dataset.providerDefault = "";
    renderJudgeRegistryApiKeyStatus();
    return "";
  }
  const configId = document.getElementById("judgeRegistryConfigId")?.value.trim() || "";
  const nextValue = generatedJudgeApiKeyEnv(provider, configId);
  const previousDefault = input.dataset.providerDefault || "";
  const currentValue = input.value.trim();
  if (!currentValue || currentValue === previousDefault || apiKeyEnvNameErrorClient(currentValue)) {
    input.value = nextValue;
  }
  input.dataset.providerDefault = nextValue;
  renderJudgeRegistryApiKeyStatus();
  return input.value.trim();
}

function renderJudgeRegistryApiKeyStatus() {
  const status = document.getElementById("judgeRegistryApiKeyStatus");
  if (!status) return;
  const provider = document.getElementById("judgeRegistryProvider")?.value || "";
  if (!provider) {
    status.textContent = "프리셋을 적용하거나 제공자를 선택하면 API 키 저장 위치가 정해집니다.";
    status.className = "registry-field-note";
    return;
  }
  if (provider === "ollama") {
    status.textContent = "";
    status.className = "registry-field-note";
    return;
  }
  const envName = document.getElementById("judgeRegistryApiKeyEnv")?.value.trim() || generatedJudgeApiKeyEnv(provider, "");
  const stored = serverApiSecrets.find((item) => item.envName === envName && item.hasValue);
  status.textContent = stored
    ? "저장된 서버 API 키가 있습니다. 새 키를 입력하면 교체됩니다."
    : "입력한 키는 서버 로컬 secret 파일에 저장되고 GitHub에는 올라가지 않습니다.";
  status.className = `registry-field-note ${stored ? "ok" : ""}`.trim();
}

function normalizeJudgeApiPresetClient(preset) {
  if (!preset || typeof preset !== "object") return null;
  const id = String(preset.id || preset.preset_id || "").trim();
  const model = String(preset.model || "").trim();
  if (!id || !model) return null;
  return {
    id,
    label: String(preset.label || id).trim(),
    provider: providerForRegistrySelect(preset.provider, "generic_api"),
    configId: String(preset.configId || preset.config_id || "").trim(),
    displayName: String(preset.displayName || preset.display_name || preset.label || model).trim(),
    model,
    baseUrl: String(preset.baseUrl || preset.base_url || "").trim(),
    chatUrl: String(preset.chatUrl || preset.chat_url || "").trim(),
    apiKeyEnv: String(preset.apiKeyEnv || preset.api_key_env || "").trim(),
    temperature: Number(preset.temperature ?? 0),
    topP: Number(preset.topP ?? preset.top_p ?? 0.1),
    maxTokens: Number(preset.maxTokens ?? preset.max_tokens ?? 1024),
    promptPreset: String(preset.promptPreset || preset.prompt_preset || "judge_default_v1").trim(),
    promptVersion: String(preset.promptVersion || preset.prompt_version || "").trim(),
    systemPrompt: preset.systemPrompt || preset.system_prompt || "",
    options: preset.options && typeof preset.options === "object" && !Array.isArray(preset.options) ? preset.options : {},
    builtIn: Boolean(preset.builtIn ?? preset.built_in),
  };
}

function replaceJudgeApiPresetCatalog(presets) {
  judgeApiPresetCatalog = Array.isArray(presets)
    ? presets.map(normalizeJudgeApiPresetClient).filter(Boolean)
    : [];
}

function judgeApiPresets() {
  return judgeApiPresetCatalog;
}

function selectedJudgeApiPreset() {
  const select = document.getElementById("judgeApiPresetSelect");
  const id = select?.value || "";
  return judgeApiPresets().find((preset) => preset.id === id) || null;
}

function renderJudgeApiPresetSelect() {
  const select = document.getElementById("judgeApiPresetSelect");
  if (!select) return;
  const current = select.value;
  const presets = judgeApiPresets();
  select.innerHTML = [
    `<option value="">프리셋 선택</option>`,
    ...presets.map((preset) => {
      const suffix = preset.builtIn ? "기본" : "커스텀";
      return `<option value="${escapeHtml(preset.id)}">${escapeHtml(preset.label || preset.id)} · ${suffix}</option>`;
    }),
  ].join("");
  if (current && presets.some((preset) => preset.id === current)) select.value = current;
  updateJudgeApiPresetDeleteState();
}

function updateJudgeApiPresetDeleteState() {
  const deleteButton = document.getElementById("judgeApiPresetDelete");
  if (!deleteButton) return;
  const preset = selectedJudgeApiPreset();
  deleteButton.disabled = !preset || Boolean(preset.builtIn);
}

function applyJudgeApiPreset(preset = selectedJudgeApiPreset()) {
  if (!preset) {
    setJudgeRegistryMessage("적용할 Judge API 프리셋을 선택하세요.", "error");
    return;
  }
  copySelectField("judgeRegistryProvider", providerForRegistrySelect(preset.provider, ""), "");
  updateJudgeRegistryProviderFields();
  copyModelField("judgeRegistryConfigId", preset.configId || "");
  copyModelField("judgeRegistryDisplayName", preset.displayName || preset.label || "");
  copyModelField("judgeRegistryModel", preset.model || "");
  copyModelField("judgeRegistryBaseUrl", preset.baseUrl || "");
  copyModelField("judgeRegistryChatUrl", preset.chatUrl || "");
  copyModelField("judgeRegistryApiKeyEnv", preset.apiKeyEnv || "");
  copyModelField("judgeRegistryApiKeyValue", "");
  copyModelField("judgeRegistryTemperature", preset.temperature ?? 0);
  copyModelField("judgeRegistryTopP", preset.topP ?? 0.1);
  copyModelField("judgeRegistryMaxTokens", preset.maxTokens ?? 1024);
  copySelectField("judgeRegistryPromptPreset", preset.promptPreset || "judge_default_v1", "judge_default_v1");
  copyModelField(
    "judgeRegistryPromptVersion",
    preset.promptVersion || judgePromptPresets[preset.promptPreset]?.version || judgePromptPresets.judge_default_v1.version,
  );
  copyModelField("judgeRegistrySystemPrompt", preset.systemPrompt || "");
  copyModelField("judgeRegistryOptionsJson", preset.options ? JSON.stringify(preset.options, null, 2) : "");
  updateJudgeRegistryProviderFields();
  updateJudgePromptPresetFields();
  openJudgeAdvancedFields();
  const keyLabel = preset.provider === "ollama" ? "API key 없이" : "API key를 입력한 뒤";
  setJudgeRegistryMessage(`프리셋 적용: ${preset.label || preset.id}. ${keyLabel} 등록하세요.`, "ok");
}

function currentJudgeApiPresetPayload(label) {
  const optionsText = document.getElementById("judgeRegistryOptionsJson")?.value.trim() || "";
  let options = {};
  if (optionsText) {
    options = JSON.parse(optionsText);
    if (!options || Array.isArray(options) || typeof options !== "object") {
      throw new Error("Options JSON은 객체 형식이어야 합니다.");
    }
  }
  const provider = document.getElementById("judgeRegistryProvider")?.value || "";
  if (!provider) throw new Error("제공자를 먼저 선택하세요.");
  const model = document.getElementById("judgeRegistryModel")?.value.trim() || "";
  const displayName = document.getElementById("judgeRegistryDisplayName")?.value.trim() || label;
  const idBase = safeConfigIdClient(label || displayName || model || provider) || "custom_judge_api";
  const promptPreset = document.getElementById("judgeRegistryPromptPreset")?.value || "judge_default_v1";
  const configId = document.getElementById("judgeRegistryConfigId")?.value.trim() || `${idBase}_judge`;
  const apiKeyEnv = provider === "ollama"
    ? ""
    : (document.getElementById("judgeRegistryApiKeyEnv")?.value.trim() || generatedJudgeApiKeyEnv(provider, configId));
  const apiKeyEnvError = apiKeyEnvNameErrorClient(apiKeyEnv);
  if (apiKeyEnvError) throw new Error(apiKeyEnvError);
  return {
    id: `custom_${idBase}`,
    label,
    provider,
    configId,
    displayName,
    model,
    baseUrl: document.getElementById("judgeRegistryBaseUrl")?.value.trim() || "",
    chatUrl: document.getElementById("judgeRegistryChatUrl")?.value.trim() || "",
    apiKeyEnv,
    temperature: Number(document.getElementById("judgeRegistryTemperature")?.value || 0),
    topP: Number(document.getElementById("judgeRegistryTopP")?.value || 0.1),
    maxTokens: Number(document.getElementById("judgeRegistryMaxTokens")?.value || 1024),
    promptPreset,
    promptVersion: document.getElementById("judgeRegistryPromptVersion")?.value.trim() || "",
    systemPrompt: promptPreset === "custom" ? (document.getElementById("judgeRegistrySystemPrompt")?.value || "") : "",
    options,
    builtIn: false,
  };
}

async function saveCurrentJudgeApiPreset() {
  const suggested = document.getElementById("judgeRegistryDisplayName")?.value.trim()
    || document.getElementById("judgeRegistryModel")?.value.trim()
    || "Custom Judge API";
  const label = window.prompt("저장할 프리셋 이름을 입력하세요.", suggested);
  if (!label) return;
  try {
    const preset = currentJudgeApiPresetPayload(label.trim());
    setJudgeRegistryMessage("프리셋 저장 중...", "");
    const response = await apiFetch("api/judge-api-presets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
    replaceJudgeApiPresetCatalog(body.presets || []);
    renderJudgeApiPresetSelect();
    const select = document.getElementById("judgeApiPresetSelect");
    if (select) select.value = preset.id;
    updateJudgeApiPresetDeleteState();
    setJudgeRegistryMessage(`커스텀 프리셋 저장 완료: ${preset.label}`, "ok");
  } catch (error) {
    setJudgeRegistryMessage(`프리셋 저장 실패: ${error.message}`, "error");
  }
}

async function deleteSelectedJudgeApiPreset() {
  const preset = selectedJudgeApiPreset();
  if (!preset) {
    setJudgeRegistryMessage("삭제할 커스텀 프리셋을 선택하세요.", "error");
    return;
  }
  if (preset.builtIn) {
    setJudgeRegistryMessage("기본 프리셋은 삭제할 수 없습니다.", "error");
    return;
  }
  try {
    setJudgeRegistryMessage("프리셋 삭제 중...", "");
    const response = await apiFetch(`api/judge-api-presets/${encodeURIComponent(preset.id)}`, {
      method: "DELETE",
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
    replaceJudgeApiPresetCatalog(body.presets || []);
    renderJudgeApiPresetSelect();
    setJudgeRegistryMessage(`커스텀 프리셋 삭제 완료: ${preset.label || preset.id}`, "ok");
  } catch (error) {
    setJudgeRegistryMessage(`프리셋 삭제 실패: ${error.message}`, "error");
  }
}

function bindJudgeApiPresetControls() {
  renderJudgeApiPresetSelect();
  const select = document.getElementById("judgeApiPresetSelect");
  select?.addEventListener("change", updateJudgeApiPresetDeleteState);
  document.getElementById("judgeApiPresetApply")?.addEventListener("click", () => applyJudgeApiPreset());
  document.getElementById("judgeApiPresetSave")?.addEventListener("click", saveCurrentJudgeApiPreset);
  document.getElementById("judgeApiPresetDelete")?.addEventListener("click", deleteSelectedJudgeApiPreset);
}

function normalizeServerApiSecrets(keys) {
  return Array.isArray(keys)
    ? keys
      .map((item) => ({
        envName: String(item?.env_name || item?.envName || "").trim(),
        hasValue: Boolean(item?.has_value ?? item?.hasValue),
        updatedAt: String(item?.updated_at || item?.updatedAt || "").trim(),
        updatedBy: String(item?.updated_by || item?.updatedBy || "").trim(),
      }))
      .filter((item) => item.envName)
    : [];
}

function replaceServerApiSecrets(keys) {
  serverApiSecrets = normalizeServerApiSecrets(keys);
}

function renderServerApiKeyControls() {
  renderJudgeRegistryApiKeyStatus();
}

function bindServerApiKeyControls() {
  renderServerApiKeyControls();
  document.getElementById("judgeRegistryApiKeyValue")?.addEventListener("input", renderJudgeRegistryApiKeyStatus);
}

function copyJudgeRegistryDefault(id, value) {
  const control = document.getElementById(id);
  if (!control || value === undefined || value === null) return;
  const nextValue = String(value);
  const previousDefault = control.dataset.providerDefault || "";
  if (!control.value || control.value === previousDefault) {
    control.value = nextValue;
  }
  control.dataset.providerDefault = nextValue;
}

function applyJudgeRegistryProviderDefaults() {
  const provider = document.getElementById("judgeRegistryProvider")?.value || "";
  if (!provider) {
    renderJudgeRegistryApiKeyStatus();
    return;
  }
  const defaults = judgeRegistryProviderDefaults(provider);
  copyJudgeRegistryDefault("judgeRegistryConfigId", defaults.configId || "");
  copyJudgeRegistryDefault("judgeRegistryDisplayName", defaults.displayName || "");
  copyJudgeRegistryDefault("judgeRegistryModel", defaults.model || "");
  copyJudgeRegistryDefault("judgeRegistryBaseUrl", defaults.baseUrl || "");
  copyJudgeRegistryDefault("judgeRegistryChatUrl", defaults.chatUrl || "");
  copyJudgeRegistryDefault("judgeRegistryApiKeyEnv", defaults.apiKeyEnv || "");
  renderJudgeRegistryApiKeyStatus();
}

function splitJudgeConfigIds(value) {
  if (Array.isArray(value)) {
    return [...new Set(value.flatMap((item) => splitJudgeConfigIds(item)))];
  }
  return [...new Set(String(value || "").split(",").map((item) => item.trim()).filter(Boolean))];
}

function summarizeJudgeIds(ids) {
  const clean = splitJudgeConfigIds(ids);
  if (!clean.length) return "";
  if (clean.length === 1) return modelLabelForVersion(clean[0]) || clean[0];
  return `LLM x${clean.length}`;
}

function modelLabelForVersion(version) {
  const registry = modelSpecForVersion(version);
  return registry.display_name || registry.model || runs.find((run) => run.version === version)?.model || version;
}

const modelFamilyPalette = [
  { id: "deepseek", label: "DeepSeek", color: "#d92d20", patterns: ["deepseek", "deep seek"] },
  { id: "gemma", label: "Gemma", color: "#2563eb", patterns: ["gemma"] },
  { id: "llama", label: "Llama", color: "#087f5b", patterns: ["llama"] },
  { id: "qwen", label: "Qwen", color: "#7c3aed", patterns: ["qwen"] },
  { id: "exaone", label: "EXAONE", color: "#b7791f", patterns: ["exaone"] },
  { id: "hcx", label: "HCX", color: "#0f766e", patterns: ["hcx", "clova"] },
  { id: "gpt", label: "GPT", color: "#0ea5e9", patterns: ["gpt", "openai"] },
  { id: "bcgpt", label: "BCGPT", color: "#475569", patterns: ["bcgpt"] },
];

const fallbackFamilyColors = ["#64748b", "#9333ea", "#c2410c", "#15803d", "#0369a1", "#a16207"];

function modelFamilyInfo(version, fallbackLabel = "") {
  const spec = modelSpecForVersion(version);
  const label = modelLabelForVersion(version) || fallbackLabel || version || "모델";
  const source = `${version || ""} ${fallbackLabel || ""} ${label}`.toLowerCase();
  const explicitFamily = String(spec.model_family || spec.family || "").trim();
  if (explicitFamily) {
    const palette = modelFamilyPalette.find((item) =>
      item.id === safeConfigIdClient(explicitFamily) ||
      item.label.toLowerCase() === explicitFamily.toLowerCase() ||
      item.patterns.some((pattern) => explicitFamily.toLowerCase().includes(pattern))
    );
    const fallbackIndex = Math.abs(hashString(explicitFamily)) % fallbackFamilyColors.length;
    const familyId = safeConfigIdClient(explicitFamily) || "custom";
    return {
      familyId,
      familyLabel: explicitFamily,
      familyOrder: palette ? modelFamilyPalette.indexOf(palette) : modelFamilyPalette.length + fallbackIndex,
      color: normalizeHexColorClient(spec.model_family_color) || palette?.color || fallbackFamilyColors[fallbackIndex],
      label,
      compactLabel: compactChartModelLabel(label),
      paramLabel: extractModelParam(source).label,
      paramValue: extractModelParam(source).value,
      quantLabel: extractModelQuant(`${version || ""} ${fallbackLabel || ""} ${label}`),
    };
  }
  const familyIndex = modelFamilyPalette.findIndex((item) =>
    item.patterns.some((pattern) => source.includes(pattern))
  );
  const fallbackIndex = Math.abs(hashString(source || label)) % fallbackFamilyColors.length;
  const family = familyIndex >= 0
    ? modelFamilyPalette[familyIndex]
    : { id: "other", label: "Other", color: fallbackFamilyColors[fallbackIndex] };
  const param = extractModelParam(source);
  const quant = extractModelQuant(`${version || ""} ${fallbackLabel || ""} ${label}`);
  return {
    familyId: family.id,
    familyLabel: family.label,
    familyOrder: familyIndex >= 0 ? familyIndex : modelFamilyPalette.length + fallbackIndex,
    color: family.color,
    label,
    compactLabel: compactChartModelLabel(label),
    paramLabel: param.label,
    paramValue: param.value,
    quantLabel: quant,
  };
}

function hashString(value) {
  return String(value || "").split("").reduce((hash, char) => ((hash << 5) - hash + char.charCodeAt(0)) | 0, 0);
}

function extractModelParam(value) {
  const normalized = String(value || "").replace(/[_:/-]+/g, " ");
  const match = normalized.match(/\b(\d+(?:\.\d+)?)\s*b\b/i);
  if (!match) return { label: "", value: Number.POSITIVE_INFINITY };
  const numeric = Number(match[1]);
  return {
    label: `${match[1]}B`,
    value: Number.isFinite(numeric) ? numeric : Number.POSITIVE_INFINITY,
  };
}

function extractModelQuant(value) {
  const match = String(value || "").match(/(?:^|[\s_:/-])(q\d[a-z0-9_]*)(?=$|[\s_:/-])/i);
  return match ? match[1].replace(/_/g, "-").toUpperCase() : "";
}

function compactChartModelLabel(label) {
  return String(label || "")
    .replace(/^Base\s+/i, "")
    .replace(/\s+Remote$/i, "")
    .replace(/\s+Q\d[A-Z0-9_-]*$/i, "")
    .trim();
}

function modelFamilyStyle(info) {
  return `--family-color:${info.color};`;
}

function normalizeHexColorClient(value) {
  const text = String(value || "").trim();
  if (/^#[0-9a-fA-F]{6}$/.test(text)) return text;
  if (/^#[0-9a-fA-F]{3}$/.test(text)) {
    return `#${text.slice(1).split("").map((char) => char + char).join("")}`;
  }
  return "";
}

function modelFamilySelectOptions() {
  const registered = Object.values(modelRegistry || {})
    .map((spec) => String(spec.model_family || "").trim())
    .filter(Boolean);
  const known = modelFamilyPalette.map((item) => item.label);
  const custom = [...new Set(registered)]
    .filter((family) => !known.some((label) => label.toLowerCase() === family.toLowerCase()))
    .sort((a, b) => a.localeCompare(b, "ko"));
  return [
    { value: "", label: "자동 추정" },
    ...modelFamilyPalette.map((item) => ({ value: item.label, label: item.label })),
    ...custom.map((family) => ({ value: family, label: family })),
    { value: "__custom__", label: "새 계열 추가" },
  ];
}

function populateModelFamilySelect() {
  const select = document.getElementById("modelFamilySelect");
  if (!select) return;
  const current = select.value;
  select.innerHTML = modelFamilySelectOptions()
    .map((option) => `<option value="${escapeHtml(option.value)}">${escapeHtml(option.label)}</option>`)
    .join("");
  if ([...select.options].some((option) => option.value === current)) select.value = current;
  syncModelFamilyControls();
}

function familyPaletteColor(label) {
  const text = String(label || "").trim().toLowerCase();
  const palette = modelFamilyPalette.find((item) =>
    item.label.toLowerCase() === text ||
    item.id === safeConfigIdClient(text) ||
    item.patterns.some((pattern) => text.includes(pattern))
  );
  return palette?.color || "";
}

function registeredFamilyColor(label) {
  const text = String(label || "").trim().toLowerCase();
  if (!text) return "";
  const spec = Object.values(modelRegistry || {}).find((item) =>
    String(item.model_family || "").trim().toLowerCase() === text &&
    normalizeHexColorClient(item.model_family_color)
  );
  return spec ? normalizeHexColorClient(spec.model_family_color) : "";
}

function syncModelFamilyControls(resetColor = false) {
  const select = document.getElementById("modelFamilySelect");
  const custom = document.getElementById("modelFamilyCustom");
  const color = document.getElementById("modelFamilyColor");
  if (!select) return;
  const isCustom = select.value === "__custom__";
  setRegistryFieldVisible("modelFamilyCustom", isCustom);
  if (custom) custom.disabled = !isCustom;
  if (resetColor && color) {
    const label = isCustom ? custom?.value : select.value;
    color.value = registeredFamilyColor(label) || familyPaletteColor(label) || "#64748b";
  }
}

function setModelFamilyFormValue(family, color) {
  populateModelFamilySelect();
  const select = document.getElementById("modelFamilySelect");
  const custom = document.getElementById("modelFamilyCustom");
  const colorInput = document.getElementById("modelFamilyColor");
  const familyText = String(family || "").trim();
  if (!select) return;
  const hasOption = [...select.options].some((option) => option.value === familyText);
  select.value = familyText && hasOption ? familyText : (familyText ? "__custom__" : "");
  if (custom) custom.value = familyText && !hasOption ? familyText : "";
  if (colorInput) colorInput.value = normalizeHexColorClient(color) || registeredFamilyColor(familyText) || familyPaletteColor(familyText) || "#64748b";
  syncModelFamilyControls();
}

function modelFamilyPayloadFromForm(data) {
  const selected = String(data.get("model_family_select") ?? "").trim();
  const custom = String(data.get("model_family_custom") ?? "").trim();
  if (selected === "__custom__" && !custom) {
    throw new Error("새 모델 계열명을 입력하세요.");
  }
  const family = selected === "__custom__" ? custom : selected;
  if (!family) return {};
  return {
    model_family: family,
    model_family_color: normalizeHexColorClient(data.get("model_family_color")) || registeredFamilyColor(family) || familyPaletteColor(family) || "#64748b",
  };
}

function renderFilters() {
  renderCheckList("versionFilters", registryModelIds(), state.resultVersions, "resultVersion", modelLabelForVersion);
  renderCheckList("sourceFilters", finalQaCategories, state.sources, "source", labelSource);
  renderCheckList("behaviorFilters", finalFinanceTopics, state.behaviors, "behavior", labelTopic);
  renderCheckList("difficultyFilters", finalQuestionTypes, state.difficulties, "difficulty", labelQuestionType);

  document.querySelectorAll("input[data-filter]").forEach((input) => {
    input.addEventListener("change", handleFilterInputChange);
  });

  bindThreshold();
}

function bindRunHealthCheckButton() {
  const runHealthCheck = async () => {
    const connectionVersions = connectionRegistryIds();
    if (!connectionVersions.length || modelHealthCheckInFlight) return;
    try {
      await syncSelectedModelApis(connectionVersions, { requireSelected: false, scope: "all" });
    } finally {
      updateHealthCheckButtonState();
    }
  };
  healthCheckButtons().forEach((button) => {
    if (button.dataset.bound === "true") return;
    button.dataset.bound = "true";
    button.addEventListener("click", runHealthCheck);
  });
  updateHealthCheckButtonState();
}

function healthCheckButtons() {
  return [...document.querySelectorAll("#runHealthCheck, #settingsHealthCheck")];
}

function connectionRegistryIds() {
  return [...new Set([...evalTargetRegistryIds(), ...judgeModelIds()])];
}

function connectionCountLabel() {
  const targetCount = evalTargetRegistryIds().length;
  const judgeCount = judgeModelIds().length;
  return [
    targetCount ? `대상 ${targetCount}개` : "",
    judgeCount ? `Judge ${judgeCount}개` : "",
  ].filter(Boolean).join(" · ");
}

function updateHealthCheckButtonState() {
  const hint = document.getElementById("healthCheckHint");
  const buttons = healthCheckButtons();
  if (!buttons.length) return;
  const targetCount = evalTargetRegistryIds().length;
  const connectionCount = connectionRegistryIds().length;
  const hasRegisteredConnections = connectionCount > 0;
  buttons.forEach((button) => {
    button.disabled = modelHealthCheckInFlight || !hasRegisteredConnections;
  });
  if (modelHealthCheckInFlight) {
    const progress = modelHealthCheckProgress;
    const isSingleCheck = progress?.scope === "single";
    const isJudgeCheck = progress?.scope === "judge-all";
    buttons.forEach((button) => {
      button.textContent = isSingleCheck
        ? "개별 확인 중"
        : (progress ? `확인 중 ${progress.current}/${progress.total}` : "확인 중...");
      button.title = isSingleCheck && progress?.label
        ? `개별 모델 연결 확인 중: ${progress.label}`
        : isJudgeCheck
          ? "등록된 Judge 모델 연결 확인 중"
          : "등록된 대상/Judge 모델 연결 확인 중";
    });
    if (hint) {
      const label = progress?.label ? ` · ${progress.label}` : "";
      hint.textContent = isSingleCheck
        ? `개별 모델 연결 확인 중${label}`
        : isJudgeCheck
          ? (
            progress
              ? `Judge ${progress.current}/${progress.total} 순차 확인 중${label}`
              : `Judge ${judgeModelIds().length}개 확인 중`
          )
        : (
          progress
            ? `등록 모델 ${progress.current}/${progress.total} 순차 확인 중${label}`
            : `등록 모델 ${connectionCount}개 확인 중`
        );
    }
    updateJudgeHealthCheckButtonState();
    return;
  }
  updateJudgeHealthCheckButtonState();
  if (!hasRegisteredConnections) {
    buttons.forEach((button) => {
      button.textContent = button.id === "settingsHealthCheck" ? "등록 모델 없음" : "모델 없음";
      button.title = "설정 탭에서 대상 또는 Judge 모델을 먼저 등록하세요.";
    });
    if (hint) hint.textContent = "설정 탭에서 대상 또는 Judge 모델을 등록하면 활성화됩니다.";
    updateJudgeHealthCheckButtonState();
    return;
  }
  buttons.forEach((button) => {
    button.textContent = button.id === "settingsHealthCheck" ? "등록 모델 연결 확인" : "연결 확인";
    button.title = "등록된 대상/Judge 모델 연결 확인";
  });
  if (hint) hint.textContent = `등록 모델 ${connectionCount}개${connectionCountLabel() ? ` (${connectionCountLabel()})` : ""}`;
  updateJudgeHealthCheckButtonState();
}

function updateJudgeHealthCheckButtonState() {
  const button = document.getElementById("judgeRegistryHealthCheck");
  if (!button) return;
  const judgeCount = judgeModelIds().length;
  if (modelHealthCheckInFlight) {
    const progress = modelHealthCheckProgress;
    button.disabled = true;
    button.textContent = progress?.scope === "judge-all" && progress.total
      ? `Judge 확인 중 ${progress.current}/${progress.total}`
      : "확인 중...";
    button.title = progress?.label ? `연결 확인 중: ${progress.label}` : "연결 확인 진행 중";
    return;
  }
  button.disabled = !judgeCount;
  button.textContent = judgeCount ? "Judge 일괄 연결 확인" : "Judge 모델 없음";
  button.title = judgeCount ? `등록된 Judge 모델 ${judgeCount}개 연결 확인` : "채점 모델을 먼저 등록하세요.";
}

function bindFilterInputs() {
  document.querySelectorAll("input[data-filter]").forEach((input) => {
    input.removeEventListener("change", handleFilterInputChange);
    input.addEventListener("change", handleFilterInputChange);
  });
}

function handleFilterInputChange(event) {
  const targetSet = filterSet(event.target.dataset.filter);
  if (event.target.checked) targetSet.add(event.target.value);
  else targetSet.delete(event.target.value);
  state.failureLimit = 40;
  renderAll();
}

function renderCheckList(elementId, items, selectedSet, filterName, labeler) {
  const element = document.getElementById(elementId);
  if (!element) return;
  const isModelFilter = filterName === "resultVersion";
  element.innerHTML = items.map((item) => `
    <label class="check-item ${isModelFilter ? "model-filter-item" : ""}">
      <input type="checkbox" data-filter="${escapeHtml(filterName)}" value="${escapeHtml(item)}" ${selectedSet.has(item) ? "checked" : ""}>
      <span class="check-item-label">${escapeHtml(labeler(item))}</span>
      ${isModelFilter ? modelConnectionPill(item) : ""}
    </label>
  `).join("") || emptyState("항목 없음");
}

function modelConnectionPill(version) {
  const stateInfo = state.modelConnections.get(version);
  const spec = modelRegistry[version];
  let status = stateInfo?.status || (spec?.health_url ? "pending" : "not-configured");
  let label = stateInfo?.message || (spec?.health_url ? "확인 전" : "설정 없음");
  let className = status;
  if (status === "connected") {
    className = "online";
    label = "연결됨";
  } else if (status === "installed") {
    className = "available";
    label = "설치됨";
  } else if (status === "checking") {
    className = "checking";
    label = "확인 중";
  } else if (status === "pending") {
    className = "available";
    label = "확인 전";
  } else if (status === "not-configured") {
    className = "not-available";
    label = "설정 없음";
  } else if (status === "offline") {
    className = "offline";
    label = "연결 실패";
  } else if (status === "available" || status === "configured") {
    className = "available";
    label = "확인 가능";
  }
  return `<span class="model-status-pill ${escapeHtml(className)}" data-status="${escapeHtml(status)}" title="${escapeHtml(stateInfo?.message || label)}">${escapeHtml(label)}</span>`;
}

function filterSet(name) {
  return {
    resultVersion: state.resultVersions,
    source: state.sources,
    behavior: state.behaviors,
    difficulty: state.difficulties,
  }[name] ?? state.sources;
}

function filteredRuns() {
  return runs.filter((d) => state.resultVersions.has(d.version));
}

function filteredCases() {
  const versions = new Set(filteredRuns().map((d) => d.version));
  return cases.filter((d) =>
    versions.has(d.version) &&
    state.difficulties.has(d.question_type) &&
    state.sources.has(d.source_type) &&
    state.behaviors.has(d.qa_matrix_topic) &&
    d.source_type !== "unknown" &&
    d.question_type !== "unknown" &&
    d.qa_matrix_topic !== "unknown"
  );
}

function filteredRunGates() {
  return runReleaseGates.filter((d) => state.resultVersions.has(d.config_id));
}

function filteredQuestionlistCases() {
  return questionlistCases.filter((d) =>
    state.sources.has(d.source_type) &&
    state.difficulties.has(d.question_type) &&
    state.behaviors.has(d.qa_matrix_topic) &&
    d.source_type !== "unknown" &&
    d.question_type !== "unknown" &&
    d.qa_matrix_topic !== "unknown"
  );
}

function activeTabId() {
  return document.body.dataset.activeTab || state.activeTab || "runEval";
}

function renderAll(options = {}) {
  const runData = filteredRuns();
  const caseData = filteredCases();
  const gateData = filteredRunGates();
  const tab = options.tab || activeTabId();
  renderRunMeta();
  renderRunSetupGuide();
  renderResultRunSelector();
  renderReblendRunSelector();
  if (tab === "overview") {
    renderOverview(runData, gateData);
    renderReleaseGates(gateData);
    renderResultViewer(caseData, runData, gateData);
    return;
  }
  if (tab === "caseSets") {
    renderQuestionlist(filteredQuestionlistCases());
    renderCaseSets();
    return;
  }
  if (tab === "compare") {
    renderCompare(runData);
    return;
  }
  if (tab === "failures") {
    renderRegression(caseData);
    renderBenchmark(caseData);
    renderExploratory(caseData);
    renderHumanReviewQueue(caseData);
    renderFailures(caseData);
    return;
  }
  if (tab === "explorer") {
    renderExplorer(caseData);
    return;
  }
  if (tab === "search") {
    renderGlobalSearch(caseData);
    return;
  }
  if (tab === "settings") {
    renderAuthPanel();
    return;
  }
  if (tab === "runEval") {
    renderEvalRunSummary();
  }
}

function renderRunSetupGuide() {
  const target = document.getElementById("runSetupGuide");
  if (!target) return;
  const targetCount = evalTargetRegistryIds().length;
  if (!targetCount) {
    target.hidden = false;
    target.innerHTML = `
      <strong>먼저 대상 모델을 등록하세요.</strong>
      <span>설정 탭에서 설정 ID, 표시 이름, 모델명, API 키 환경변수를 입력한 뒤 실행 탭으로 돌아오면 테스트를 시작할 수 있습니다.</span>
      <button type="button" data-tab-jump="settings">설정으로 이동</button>
    `;
    target.querySelector("[data-tab-jump]")?.addEventListener("click", () => activateTab("settings"));
    return;
  }
  target.hidden = false;
  target.innerHTML = `
    <strong>실행 준비 완료</strong>
    <span>등록된 대상 모델 ${targetCount.toLocaleString()}개 중 실행할 모델과 실행 범위를 선택하세요.</span>
  `;
}

async function loadAuthInfo() {
  const [session, accessLog] = await Promise.all([
    fetchJsonOptional("api/auth/session", null),
    fetchJsonOptional("api/auth/access-log?limit=80", { entries: [] }),
  ]);
  authSession = session;
  authAccessLog = accessLog?.entries ?? [];
  renderAuthPanel();
}

function renderAuthPanel() {
  const sessionTarget = document.getElementById("authSession");
  const logTarget = document.getElementById("authAccessLog");
  const refresh = document.getElementById("refreshAuthLog");
  if (refresh && !refresh.dataset.bound) {
    refresh.dataset.bound = "1";
    refresh.onclick = () => loadAuthInfo();
  }
  if (sessionTarget) {
    const hasSession = Boolean(authSession);
    const enabled = Boolean(authSession?.auth_enabled);
    const user = authSession?.user || "local";
    const role = authSession?.role || "admin";
    const scheme = authSession?.scheme || (enabled ? "" : "none");
    sessionTarget.innerHTML = `
      ${authStatusItem("접속 보호", hasSession ? (enabled ? "켜짐" : "꺼짐") : "확인 안 됨", authModeLabel(authSession), enabled ? "ok" : "muted")}
      ${authStatusItem("현재 계정", user, user === "local" ? "로컬 요청" : "로그인됨")}
      ${authStatusItem("권한", authRoleLabel(role), authRoleHint(role))}
      ${authStatusItem("로그인 방식", authSchemeLabel(scheme), scheme ? "현재 요청 기준" : "확인 안 됨", "muted")}
    `;
  }
  if (!logTarget) return;
  if (!authAccessLog.length) {
    logTarget.innerHTML = emptyState("최근 접속 내역이 없거나 관리자 권한이 필요합니다.");
    return;
  }
  const rows = [...authAccessLog].slice(-80).reverse().map((entry) => [
    formatDateTime(entry.timestamp),
    entry.user || "anonymous",
    authRoleLabel(entry.role || ""),
    entry.client_addr || entry.remote_addr || "-",
    accessLogProxyLabel(entry),
    `${entry.method || ""} ${entry.path || ""}`.trim(),
    entry.status || "",
  ]);
  logTarget.innerHTML = table(["시간", "계정", "권한", "사용자 IP", "프록시/출처", "요청", "응답"], rows);
}

function accessLogProxyLabel(entry) {
  const clientIp = entry.client_addr || entry.remote_addr || "";
  const parts = [];
  if (entry.client_ip_source) parts.push(entry.client_ip_source);
  if (entry.peer_addr && entry.peer_addr !== clientIp) parts.push(`via ${entry.peer_addr}`);
  if (entry.proxy_headers_trusted === false && (entry.x_forwarded_for || entry.cf_connecting_ip)) parts.push("헤더 미신뢰");
  return parts.length ? parts.join(" · ") : "-";
}

function authStatusItem(label, value, hint = "", tone = "") {
  return `
    <div class="auth-status-item ${escapeHtml(tone)}">
      <span>${escapeHtml(label)}</span>
      <strong title="${escapeHtml(value)}">${escapeHtml(value)}</strong>
      ${hint ? `<em>${escapeHtml(hint)}</em>` : ""}
    </div>
  `;
}

function authModeLabel(session) {
  if (!session) return "상태 확인 전";
  if (!session.auth_enabled) return "로컬 개발 모드";
  const modes = [];
  if (session.id_auth_enabled) modes.push("아이디/비밀번호");
  if (session.token_auth_enabled) modes.push("관리 토큰");
  return modes.length ? modes.join(" + ") : "인증 켜짐";
}

function authRoleLabel(role) {
  return {
    admin: "관리자",
    user: "읽기 전용",
  }[role] || role || "-";
}

function authRoleHint(role) {
  return {
    admin: "설정 변경 가능",
    user: "조회만 가능",
  }[role] || "권한 정보 없음";
}

function authSchemeLabel(scheme) {
  return {
    basic: "아이디 로그인",
    token: "토큰 로그인",
    none: "인증 없음",
    disabled: "인증 비활성",
  }[scheme] || scheme || "-";
}

function renderRunMeta() {
  const target = document.getElementById("runMeta");
  if (!target) return;
  updateHeaderDatasetCounts();
  if (!latestRun?.run_id) {
    target.innerHTML = "";
    target.hidden = true;
    updateHeaderJudgeStatus();
    return;
  }
  const sourceStatus = latestRun.uses_final_question_sets
    ? "최종셋 결과"
    : "이전 실행 결과";
  target.hidden = false;
  target.title = [latestRun.run_id, sourceStatus, latestRun.case_source].filter(Boolean).join(" · ");
  target.innerHTML = `
    <span>선택 실행</span>
    <strong>${escapeHtml(latestRun.run_id)}</strong>
    <em>${escapeHtml(sourceStatus)}</em>
    ${latestRun.files?.report_html ? `<a href="${escapeHtml(latestRun.files.report_html)}" target="_blank" rel="noreferrer">HTML 리포트</a>` : ""}
  `;
  updateHeaderJudgeStatus();
}

function updateHeaderDatasetCounts() {
  const benchmarkTarget = document.getElementById("headerBenchmarkCount");
  const regressionTarget = document.getElementById("headerRegressionCount");
  if (!benchmarkTarget || !regressionTarget) return;

  const benchmarkCount = datasetTotalById("benchmark_final_full");
  const regressionCount = datasetTotalById("regression_golden_full");
  const title = "questionlist/benchmark, questionlist/regression 기준";

  benchmarkTarget.textContent = benchmarkCount ? benchmarkCount.toLocaleString() : "-";
  regressionTarget.textContent = regressionCount ? regressionCount.toLocaleString() : "-";
  benchmarkTarget.title = title;
  regressionTarget.title = title;
}

function datasetTotalById(datasetId) {
  const dataset = questionlistDatasets.find((item) => item.id === datasetId) || {};
  const fallbackTotals = {
    benchmark_final_full: 800,
    regression_golden_full: 300,
  };
  return Number(dataset.total || fallbackTotals[datasetId] || 0);
}

function uniqueCaseCount(rows) {
  const ids = new Set(rows.map((row) => row.question_id || row.case_id).filter(Boolean));
  return ids.size || rows.length;
}

function renderResultRunSelector() {
  const select = document.getElementById("resultRunSelect");
  const summary = document.getElementById("resultRunSummary");
  const uiLink = document.getElementById("resultUiReportLink");
  const rawLink = document.getElementById("resultRawReportLink");
  if (!select) return;
  const currentId = selectedRunId || latestRun?.run_id || "";
  const historyOptions = evalRunHistory.map((run) => {
    const label = [
      run.label || run.run_id,
      run.eval_started_at ? formatDateTime(run.eval_started_at) : "",
    ].filter(Boolean).join(" · ");
    return `<option value="${escapeHtml(run.run_id)}" ${run.run_id === currentId ? "selected" : ""}>${escapeHtml(label)}</option>`;
  }).join("");
  const hasExportedRows = Boolean(runs.length || cases.length);
  select.innerHTML = historyOptions || (
    hasExportedRows
      ? `<option value="">현재 내보낸 결과</option>`
      : `<option value="">결과 없음</option>`
  );
  select.disabled = !evalRunHistory.length;
  select.title = historyOptions
    ? "과거 실행 결과 선택"
    : (hasExportedRows ? "data/*.csv로 내보낸 현재 결과입니다." : "선택 가능한 실행 결과가 없습니다.");
  select.value = evalRunHistory.some((run) => run.run_id === currentId) ? currentId : "";
  const current = evalRunHistory.find((run) => run.run_id === currentId) || {};
  if (summary) {
    summary.innerHTML = current.run_id ? `
      <span><strong>${escapeHtml(current.label || current.run_id)}</strong></span>
      <span>${escapeHtml(current.run_type || "-")}</span>
      <span>${Number(current.total_questions || 0).toLocaleString()}문항</span>
      <span>${Number(current.model_count || 0).toLocaleString()}개 모델</span>
      <span>자동 ${(Number(current.avg_scored_score || current.avg_score || 0)).toFixed(1)} / 100</span>
      <span>검토대기 ${Number(current.review_pending_count || 0).toLocaleString()}개</span>
      <span>${Number(current.avg_score || 0).toFixed(1)} / 100</span>
      <span>${(Number(current.avg_pass_rate || 0) * 100).toFixed(1)}% 통과</span>
      <span>${escapeHtml(scoringModeLabel(current.scoring_mode) || "-")}</span>
      <span>${escapeHtml([current.llm_judge_provider, current.llm_judge_model].filter(Boolean).join(" / ") || scoringModeLabel("static"))}</span>
    ` : (
      hasExportedRows
        ? `
          <span><strong>현재 내보낸 결과</strong></span>
          <span>data/eval_runs.csv 기준</span>
          <span>${uniqueCaseCount(cases).toLocaleString()}문항</span>
          <span>${runs.length.toLocaleString()}개 모델 행</span>
        `
        : emptyState("선택 가능한 과거 결과가 없습니다.")
    );
  }
  if (uiLink) {
    uiLink.href = current.report_ui || (currentId ? `?run_id=${encodeURIComponent(currentId)}#overview` : "#overview");
  }
  if (rawLink) {
    rawLink.href = current.report_raw_html || (currentId ? `/report/raw_regression_report.html?run_id=${encodeURIComponent(currentId)}` : "/report/raw_regression_report.html");
  }
}

function formatDateTime(value) {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("ko-KR", {
    year: "2-digit",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function runHistoryOptionLabel(run) {
  return [
    run.label || run.run_id,
    run.eval_started_at ? formatDateTime(run.eval_started_at) : "",
    Number(run.total_questions || 0) ? `${Number(run.total_questions || 0).toLocaleString()}문항` : "",
    scoringModeLabel(run.scoring_mode) || "",
  ].filter(Boolean).join(" · ");
}

function renderReblendRunSelector() {
  const select = document.getElementById("reblendSourceRunId");
  if (!select) return;
  const previousValue = select.value || "";
  const preferredId = previousValue || selectedRunId || latestRun?.run_id || "";
  const latestLabel = latestRun?.run_id
    ? `최신 실행 (${latestRun.run_id})`
    : "최신 실행 자동 선택";
  const historyOptions = evalRunHistory.map((run) => `
    <option value="${escapeHtml(run.run_id)}">${escapeHtml(runHistoryOptionLabel(run))}</option>
  `).join("");
  select.innerHTML = `<option value="">${escapeHtml(latestLabel)}</option>${historyOptions}`;
  select.disabled = !evalRunHistory.length && !latestRun?.run_id;
  select.title = select.disabled
    ? "재계산할 실행 결과가 없습니다."
    : "저장된 실행 결과 중 재계산할 원본을 선택합니다.";
  select.value = evalRunHistory.some((run) => run.run_id === preferredId) ? preferredId : "";
}

function latestJudgeMethodLabel() {
  const mode = latestRun?.scoring_mode || "";
  if (!mode || mode === "static") return scoringModeLabel("static");
  const count = Number(latestRun?.llm_judge_count || 0);
  const model = latestRun?.llm_judge_model || latestRun?.judge_model || "";
  const provider = latestRun?.llm_judge_provider || latestRun?.judge_provider || "";
  const judgeText = model || provider || (count > 1 ? `LLM x${count}` : "LLM");
  return `${scoringModeLabel(mode)} · ${judgeText}${count > 1 && !String(judgeText).includes("x") ? ` x${count}` : ""}`;
}

function currentJudgeMethodLabel() {
  const scoringMode = document.getElementById("evalScoringMode")?.value || "static";
  if (scoringMode === "static") return scoringModeLabel("static");
  const label = scoringModeLabel(scoringMode);
  return `${label} · ${summarizeJudgeIds(selectedJudgeConfigIds()) || "Judge 미선택"}`;
}

function updateHeaderJudgeStatus(job = null) {
  const target = document.getElementById("headerJudgeValue");
  if (!target) return;
  let label = latestRun?.run_id ? latestJudgeMethodLabel() : currentJudgeMethodLabel();
  let title = latestRun?.run_id ? "마지막 완료 채점 방식" : "선택한 채점 방식";
  if (job?.job_id) {
    const mode = job.scoring_mode || "static";
    const judgeIds = splitJudgeConfigIds(job.judge_config_ids || job.judge_config);
    const method = mode === "static" ? scoringModeLabel("static") : `${scoringModeLabel(mode)} · ${summarizeJudgeIds(judgeIds) || "LLM"}`;
    const prefix = ["running", "paused", "canceling"].includes(job.status) ? "진행" : "최근";
    label = `${prefix} ${method}`;
    title = `${job.run_id || job.job_id} · ${job.status}`;
  }
  target.textContent = shortLabel(label, 34);
  target.title = title;
}

async function syncSelectedModelApis(targetVersions = [...state.runConfigVersions], options = {}) {
  if (modelHealthCheckInFlight) return;
  const requireSelected = options.requireSelected !== false;
  const requestedScope = String(options.scope || "all");
  const checkScope = ["single", "judge-all"].includes(requestedScope) ? requestedScope : "all";
  const selectedVersionsForCheck = [...new Set(targetVersions)]
    .filter((version) => !requireSelected || state.runConfigVersions.has(version));
  const healthButtons = healthCheckButtons();
  modelHealthCheckInFlight = true;
  healthButtons.forEach((button) => {
    button.disabled = true;
  });
  updateHealthCheckButtonState();
  renderModelConnectionSurfaces();

  try {
    const total = selectedVersionsForCheck.length;
    for (let index = 0; index < selectedVersionsForCheck.length; index += 1) {
      const version = selectedVersionsForCheck[index];
      modelHealthCheckProgress = {
        current: index + 1,
        total,
        label: modelLabelForVersion(version),
        scope: checkScope,
      };
      updateHealthCheckButtonState();
      await checkModelHealthWithRetry(version, index + 1, total, checkScope);
    }
  } finally {
    modelHealthCheckInFlight = false;
    modelHealthCheckProgress = null;
    updateHealthCheckButtonState();
    renderModelConnectionSurfaces();
  }
}

async function checkModelHealthWithRetry(version, index = 1, total = 1, scope = "all") {
  const registry = modelRegistry[version];
  if (!registry?.health_url) {
    state.modelConnections.set(version, {
      status: "not-configured",
      message: "healthcheck endpoint가 설정되지 않았습니다",
    });
    renderModelConnectionSurfaces();
    return;
  }

  let lastMessage = "";
  for (let attempt = 1; attempt <= modelHealthMaxAttempts; attempt += 1) {
    const progressMessage = scope === "single"
      ? `개별 확인 · 시도 ${attempt}/${modelHealthMaxAttempts}`
      : `순차 확인 ${index}/${total} · 시도 ${attempt}/${modelHealthMaxAttempts}`;
    state.modelConnections.set(version, {
      status: "checking",
      message: progressMessage,
      registry,
    });
    renderModelConnectionSurfaces();

    try {
      const response = await fetchWithTimeout(modelHealthUrl(registry), { method: "GET" }, modelHealthTimeoutMs);
      const payload = await response.json().catch(() => ({}));
      if (response.ok) {
        const status = modelConnectionStatusFromPayload(registry, payload);
        state.modelConnections.set(version, {
          status,
          message: payload.message ?? "healthcheck 통과",
          registry,
        });
        renderModelConnectionSurfaces();
        return;
      }
      if (payload.status === "busy") {
        state.modelConnections.set(version, {
          status: "available",
          message: payload.message ?? "실행 중인 평가 작업 때문에 확인을 보류했습니다",
          registry,
        });
        renderModelConnectionSurfaces();
        return;
      }
      lastMessage = payload.message ?? `HTTP ${response.status}`;
    } catch (error) {
      lastMessage = error.name === "AbortError"
        ? `timeout after ${Math.round(modelHealthTimeoutMs / 1000)}s`
        : error.message;
    }

    if (attempt < modelHealthMaxAttempts) {
      await sleep(modelHealthRetryDelayMs);
    }
  }

  state.modelConnections.set(version, {
    status: "offline",
    message: `연결 실패: ${lastMessage || "unknown error"}`,
    registry,
  });
  renderModelConnectionSurfaces();
}

function modelHealthUrl(registry) {
  const url = registry.health_url;
  if (!url || registry.provider !== "ollama") return url;
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}mode=load_unload`;
}

function modelConnectionStatusFromPayload(registry, payload) {
  const status = String(payload?.status || "");
  if (status === "configured") return "configured";
  if (status === "ok") {
    if (registry?.provider === "ollama" && payload?.health_check_mode !== "load_unload") {
      return "installed";
    }
    return "connected";
  }
  return status || "connected";
}

function renderVersionFiltersOnly() {
  renderCheckList("versionFilters", registryModelIds(), state.resultVersions, "resultVersion", modelLabelForVersion);
  bindFilterInputs();
}

function renderModelConnectionSurfaces() {
  renderVersionFiltersOnly();
  renderTargetRegistry();
  renderJudgeRegistry();
  renderEvalConfigFilters();
}

function bindModelRegistryForm() {
  const form = document.getElementById("modelRegistryForm");
  if (!form) return;
  const variantBase = document.getElementById("modelPromptVariantOf");
  const variantTag = document.getElementById("modelExperimentTag");
  const quickBase = document.getElementById("promptVariantQuickBase");
  const quickTag = document.getElementById("promptVariantQuickTag");
  const quickStart = document.getElementById("promptVariantQuickStart");
  const familySelect = document.getElementById("modelFamilySelect");
  const familyCustom = document.getElementById("modelFamilyCustom");
  populateModelFamilySelect();

  variantBase?.addEventListener("change", () => {
    if (!variantBase.value) return;
    prefillPromptVariant(variantBase.value, variantTag?.value || defaultPromptVariantTag(variantBase.value));
    updateModelRegistryProviderFields();
  });
  variantTag?.addEventListener("input", updatePromptVariantIdentity);
  familySelect?.addEventListener("change", () => syncModelFamilyControls(true));
  familyCustom?.addEventListener("input", () => syncModelFamilyControls(false));
  quickBase?.addEventListener("change", () => {
    if (!quickBase.value) return;
    const tag = quickTag?.value || defaultPromptVariantTag(quickBase.value);
    prefillPromptVariant(quickBase.value, tag);
    updateModelRegistryProviderFields();
  });
  quickStart?.addEventListener("click", () => {
    if (!quickBase?.value) {
      setRegistryMessage("기준 모델을 먼저 선택하세요.", "error");
      quickBase?.focus();
      return;
    }
    const tag = quickTag?.value || defaultPromptVariantTag(quickBase.value);
    prefillPromptVariant(quickBase.value, tag);
    updateModelRegistryProviderFields();
    document.getElementById("modelSystemPrompt")?.focus();
  });
  document.getElementById("modelRegistryReset")?.addEventListener("click", () => {
    resetModelRegistryForm(form);
    setRegistryMessage("새 대상 모델 등록 모드입니다.", "");
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    updateModelRegistryProviderFields();
    if (!form.reportValidity()) {
      setRegistryMessage("필수 필드를 먼저 입력하세요.", "error");
      return;
    }

    try {
      const payload = modelRegistryPayload(form);
      setRegistryMessage("등록 중...", "");
      const response = await apiFetch("api/model-registry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);

      modelRegistry = body.registry || modelRegistry;
      state.resultVersions.add(body.config.config_id);
      state.runConfigVersions.add(body.config.config_id);
      renderFilters();
      renderEvalConfigFilters();
      renderTargetRegistry();
      renderJudgeRegistry();
      renderAll();
      updateHealthCheckButtonState();
      populateModelFamilySelect();
      setRegistryMessage(`등록/업데이트 완료: ${modelLabelForVersion(body.config.config_id)}. 연결 확인으로 상태를 확인하세요.`, "ok");
      resetModelRegistryForm(form);
    } catch (error) {
      setRegistryMessage(`등록 실패: ${error.message}`, "error");
    }
  });
}

function bindJudgeRegistryForm() {
  const form = document.getElementById("judgeRegistryForm");
  if (!form) return;
  bindJudgeApiPresetControls();
  bindServerApiKeyControls();
  const copySelect = document.getElementById("judgeCopyTargetBase");
  const copyStart = document.getElementById("judgeCopyTargetStart");
  const judgeHealthCheck = document.getElementById("judgeRegistryHealthCheck");
  judgeHealthCheck?.addEventListener("click", async () => {
    const judgeIds = judgeModelIds();
    if (!judgeIds.length || modelHealthCheckInFlight) return;
    setJudgeRegistryMessage(`Judge ${judgeIds.length}개 연결 확인 중...`, "");
    await syncSelectedModelApis(judgeIds, { requireSelected: false, scope: "judge-all" });
    const failed = judgeIds.filter((id) => {
      const stateInfo = state.modelConnections.get(id);
      return !["connected", "installed", "available", "configured"].includes(stateInfo?.status);
    });
    const okCount = judgeIds.length - failed.length;
    setJudgeRegistryMessage(
      failed.length
        ? `Judge 연결 확인 완료: 성공 ${okCount}개 / 실패 ${failed.length}개`
        : `Judge 연결 확인 완료: ${okCount}개 모두 정상`,
      failed.length ? "error" : "ok",
    );
  });
  copyStart?.addEventListener("click", () => {
    if (!copySelect?.value) {
      setJudgeRegistryMessage("복사할 대상 모델을 먼저 선택하세요.", "error");
      copySelect?.focus();
      return;
    }
    prefillJudgeFromTarget(copySelect.value);
  });
  document.getElementById("judgeRegistryReset")?.addEventListener("click", () => {
    resetJudgeRegistryForm(form);
    setJudgeRegistryMessage("새 Judge 모델 등록 모드입니다.", "");
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    updateJudgeRegistryProviderFields();
    if (!form.reportValidity()) {
      setJudgeRegistryMessage("필수 필드를 먼저 입력하세요.", "error");
      return;
    }
    try {
      const payload = judgeRegistryPayload(form);
      setJudgeRegistryMessage("Judge 등록 중...", "");
      const response = await apiFetch("api/model-registry", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);

      modelRegistry = body.registry || modelRegistry;
      if (body.server_api_keys) {
        replaceServerApiSecrets(body.server_api_keys);
        renderServerApiKeyControls();
      }
      renderJudgeRegistry();
      updateJudgePlaceholders();
      const keyNote = body.stored_api_key_env ? " API 키도 서버에 저장했습니다." : "";
      setJudgeRegistryMessage(`Judge 등록/업데이트 완료: ${modelLabelForVersion(body.config.config_id)}.${keyNote}`, "ok");
      resetJudgeRegistryForm(form);
    } catch (error) {
      setJudgeRegistryMessage(`Judge 등록 실패: ${error.message}`, "error");
    }
  });
}

function judgeRegistryPayload(form) {
  const data = new FormData(form);
  const payload = {};
  [
    "provider",
    "config_id",
    "display_name",
    "model",
    "cache_identity",
    "base_url",
    "chat_url",
    "api_key_env",
    "prompt_version",
    "system_prompt_preset",
    "system_prompt",
  ].forEach((key) => {
    payload[key] = String(data.get(key) ?? "").trim();
  });
  if (!payload.provider) throw new Error("제공자를 먼저 선택하세요.");
  const apiKeyValue = String(data.get("api_key_value") ?? "").trim();
  if (payload.provider === "ollama") {
    payload.api_key_env = "";
  } else if (!payload.api_key_env || apiKeyEnvNameErrorClient(payload.api_key_env)) {
    payload.api_key_env = generatedJudgeApiKeyEnv(payload.provider, payload.config_id);
  }
  const apiKeyEnvError = apiKeyEnvNameErrorClient(payload.api_key_env);
  if (apiKeyEnvError) throw new Error(apiKeyEnvError);
  if (apiKeyValue) payload.api_key_value = apiKeyValue;
  payload.upstream_chat_url = payload.chat_url;

  const options = {};
  const temperature = String(data.get("temperature") ?? "").trim();
  const topP = String(data.get("top_p") ?? "").trim();
  const maxTokens = String(data.get("max_completion_tokens") ?? "").trim();
  if (temperature !== "") options.temperature = Number(temperature);
  if (topP !== "") options.top_p = Number(topP);
  if (maxTokens !== "") options.max_completion_tokens = Number(maxTokens);

  const optionsJson = String(data.get("options_json") ?? "").trim();
  if (optionsJson) {
    try {
      const extra = JSON.parse(optionsJson);
      if (!extra || Array.isArray(extra) || typeof extra !== "object") {
        throw new Error("Options JSON은 객체 형식이어야 합니다.");
      }
      Object.assign(options, extra);
    } catch (error) {
      throw new Error(`Options JSON 오류: ${error.message}`);
    }
  }
  payload.options = options;
  payload.eval_target = false;
  payload.ui_visible = true;
  payload.evaluation_role = "llm_judge";
  payload.judge_role = payload.system_prompt_preset === "arbiter_conflict_v1" ? "arbiter" : "judge";
  payload.candidate_role = "";
  if (!payload.system_prompt_preset) payload.system_prompt_preset = "judge_default_v1";
  if (!payload.prompt_version) payload.prompt_version = judgePromptPresets[payload.system_prompt_preset]?.version || judgePromptPresets.judge_default_v1.version;
  if (payload.system_prompt_preset === "custom" && !payload.system_prompt) {
    throw new Error("직접 입력 preset은 Judge system prompt가 필요합니다.");
  }
  if (payload.system_prompt_preset !== "custom") delete payload.system_prompt;
  payload.safety_policy = "llm_judge_prompt_preset";
  payload.rag_config = "none";
  payload.role_notes = "Registered LLM-as-a-judge config. Not selectable as a target model.";
  return payload;
}

function renderJudgeCopyTargetSelect() {
  const select = document.getElementById("judgeCopyTargetBase");
  const button = document.getElementById("judgeCopyTargetStart");
  if (!select) return;
  const current = select.value;
  const ids = evalTargetRegistryIds();
  select.innerHTML = [
    `<option value="">대상 모델 선택</option>`,
    ...ids.map((id) => `<option value="${escapeHtml(id)}">${escapeHtml(modelLabelForVersion(id))}</option>`),
  ].join("");
  if (current && ids.includes(current)) select.value = current;
  if (button) button.disabled = !ids.length;
}

function prefillJudgeFromTarget(targetId) {
  const spec = modelSpecForVersion(targetId);
  if (!spec?.config_id && !modelRegistry[targetId]) return;
  const label = modelLabelForVersion(targetId);
  const configId = `${targetId}_judge`;
  const options = spec.options || {};
  copySelectField("judgeRegistryProvider", providerForRegistrySelect(spec.provider, "ollama"), "ollama");
  copyModelField("judgeRegistryConfigId", configId);
  copyModelField("judgeRegistryDisplayName", `${label} Judge`);
  copyModelField("judgeRegistryModel", spec.model || targetId);
  copyModelField("judgeRegistryBaseUrl", spec.base_url || "");
  copyModelField("judgeRegistryChatUrl", externalEndpointValue(spec, "chat_url", "upstream_chat_url"));
  copyModelField("judgeRegistryApiKeyEnv", spec.api_key_env || "");
  copyModelField("judgeRegistryApiKeyValue", "");
  copyModelField("judgeRegistryTemperature", options.temperature ?? 0);
  copyModelField("judgeRegistryTopP", options.top_p ?? options.topP ?? 0.1);
  copyModelField("judgeRegistryMaxTokens", judgeMaxTokensFromOptions(options));
  copySelectField("judgeRegistryPromptPreset", "judge_default_v1", "judge_default_v1");
  copyModelField("judgeRegistryPromptVersion", judgePromptPresets.judge_default_v1.version);
  copyModelField("judgeRegistrySystemPrompt", "");
  copyModelField("judgeRegistryOptionsJson", registryOptionsJson(options, [
    "temperature",
    "top_p",
    "topP",
    "max_completion_tokens",
    "maxCompletionTokens",
    "max_output_tokens",
    "maxOutputTokens",
    "max_tokens",
    "maxTokens",
    "num_predict",
  ]));
  updateJudgeRegistryProviderFields();
  updateJudgePromptPresetFields();
  openJudgeAdvancedFields();
  setJudgeRegistryMessage(`Judge 초안: ${label} 설정을 복사했습니다. 필요하면 prompt preset과 옵션을 조정한 뒤 등록하세요.`, "ok");
  document.getElementById("judgeRegistryConfigId")?.focus();
}

function modelRegistryPayload(form) {
  const data = new FormData(form);
  const payload = {};
  [
    "provider",
    "config_id",
    "display_name",
    "model",
    "base_url",
    "base_url_env",
    "chat_url",
    "health_url",
    "api_key_env",
    "prompt_version",
    "prompt_variant_of",
    "experiment_tag",
    "system_prompt",
    "query_prompt_template",
    "prompt_prefix",
    "prompt_suffix",
    "local_path",
  ].forEach((key) => {
    payload[key] = String(data.get(key) ?? "").trim();
  });
  Object.assign(payload, modelFamilyPayloadFromForm(data));
  payload.upstream_chat_url = payload.chat_url;
  payload.upstream_health_url = payload.health_url;
  const optionsJson = String(data.get("options_json") ?? "").trim();
  if (optionsJson) {
    try {
      const options = JSON.parse(optionsJson);
      if (!options || Array.isArray(options) || typeof options !== "object") {
        throw new Error("Options JSON은 객체 형식이어야 합니다.");
      }
      payload.options = options;
    } catch (error) {
      throw new Error(`Options JSON 오류: ${error.message}`);
    }
  } else {
    payload.options = {};
  }
  return payload;
}

function safeConfigIdClient(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .replace(/_+/g, "_")
    .slice(0, 80);
}

function apiKeyEnvNameErrorClient(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  if (!/^[A-Za-z_][A-Za-z0-9_]{0,119}$/.test(text)) {
    return "API 키 환경변수에는 실제 키가 아니라 GEMINI_API_KEY 같은 변수명을 입력하세요.";
  }
  const commonSecretPrefixes = ["sk-", "sk_", "AIza", "ya29.", "xai-", "gsk_", "nvapi-"];
  if (commonSecretPrefixes.some((prefix) => text.startsWith(prefix)) || (!text.includes("_") && text.length >= 24)) {
    return "API 키처럼 보입니다. 이 값은 숨겨진 참조 이름이어야 하며 실제 키 값은 API 키 입력칸에 넣어야 합니다.";
  }
  return "";
}

function promptVariantConfigId(baseId, tag) {
  const base = safeConfigIdClient(baseId);
  const rawTag = safeConfigIdClient(tag) || "prompt_v1";
  const suffix = rawTag.startsWith("prompt_") ? rawTag : `prompt_${rawTag}`;
  const baseLimit = Math.max(1, 80 - suffix.length - 1);
  return `${base.slice(0, baseLimit)}_${suffix}`;
}

function defaultPromptVariantTag(baseId) {
  for (let index = 1; index < 100; index += 1) {
    const tag = `v${index}`;
    if (!modelRegistry[promptVariantConfigId(baseId, tag)]) return tag;
  }
  return "v1";
}

function promptVariantVersion(baseSpec, tag) {
  const safeTag = safeConfigIdClient(tag) || "v1";
  const baseVersion = safeConfigIdClient(baseSpec?.prompt_version || "prompt");
  return `${baseVersion}__${safeTag}`.slice(0, 80);
}

function copyModelField(id, value) {
  const element = document.getElementById(id);
  if (!element) return;
  element.value = value ?? "";
}

function copySelectField(id, value, fallback = "") {
  const element = document.getElementById(id);
  if (!element) return;
  const candidate = String(value || fallback || "");
  const allowed = [...element.options].map((option) => option.value);
  element.value = allowed.includes(candidate) ? candidate : fallback;
}

function openModelAdvancedFields() {
  const advanced = document.querySelector(".model-registry-panel .advanced-fields");
  if (advanced) advanced.open = true;
}

function openJudgeAdvancedFields() {
  const advanced = document.querySelector(".judge-registry-panel .advanced-fields");
  if (advanced) advanced.open = true;
}

function externalEndpointValue(spec, proxyKey, upstreamKey) {
  const upstream = String(spec?.[upstreamKey] || "").trim();
  if (upstream) return upstream;
  const value = String(spec?.[proxyKey] || "").trim();
  return value.startsWith("/api/models/") ? "" : value;
}

function registrySourceLabel(spec) {
  return "사용자 등록";
}

function registryOptionsJson(options, omittedKeys = []) {
  const source = options && typeof options === "object" && !Array.isArray(options) ? options : {};
  const omitted = new Set(omittedKeys);
  const cleaned = Object.fromEntries(Object.entries(source).filter(([key]) => !omitted.has(key)));
  return Object.keys(cleaned).length ? JSON.stringify(cleaned, null, 2) : "";
}

function editRegisteredModel(version) {
  const spec = modelSpecForVersion(version);
  const form = document.getElementById("modelRegistryForm");
  if (!spec || !form) return;
  copySelectField("modelProvider", providerForRegistrySelect(spec.provider, "openai_native"), "openai_native");
  copyModelField("modelPromptVariantOf", spec.prompt_variant_of || "");
  copyModelField("modelExperimentTag", spec.experiment_tag || "");
  copyModelField("modelConfigId", spec.config_id || version);
  copyModelField("modelDisplayName", spec.display_name || spec.model || version);
  copyModelField("modelName", spec.model || version);
  copyModelField("modelCacheIdentity", spec.cache_identity || spec.model_artifact_id || "");
  copyModelField("modelBaseUrl", spec.base_url || "");
  copyModelField("modelBaseUrlEnv", spec.base_url_env || "");
  copyModelField("modelChatUrl", externalEndpointValue(spec, "chat_url", "upstream_chat_url"));
  copyModelField("modelHealthUrl", externalEndpointValue(spec, "health_url", "upstream_health_url"));
  copyModelField("modelApiKeyEnv", spec.api_key_env || "");
  copyModelField("modelPromptVersion", spec.prompt_version || "");
  copyModelField("modelSystemPrompt", spec.system_prompt || "");
  copyModelField("modelQueryPromptTemplate", spec.query_prompt_template || spec.prompt_template || "");
  copyModelField("modelOptionsJson", registryOptionsJson(spec.options));
  copyModelField("modelLocalPath", spec.local_path || "");
  setModelFamilyFormValue(spec.model_family || "", spec.model_family_color || "");
  updateModelRegistryProviderFields();
  openModelAdvancedFields();
  setRegistryMessage(`수정 모드: ${modelLabelForVersion(version)}. 저장하면 같은 설정 ID가 업데이트됩니다.`, "ok");
  activateTab("settings");
  form.scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetModelRegistryForm(form = document.getElementById("modelRegistryForm")) {
  form?.reset();
  copyModelField("modelPromptVariantOf", "");
  copyModelField("modelExperimentTag", "");
  copyModelField("modelOptionsJson", "");
  setModelFamilyFormValue("", "");
  updateModelRegistryProviderFields();
}

function judgeMaxTokensFromOptions(options) {
  if (!options || typeof options !== "object") return 1024;
  return options.max_completion_tokens
    ?? options.maxCompletionTokens
    ?? options.max_output_tokens
    ?? options.maxOutputTokens
    ?? options.max_tokens
    ?? options.maxTokens
    ?? options.num_predict
    ?? 1024;
}

function editRegisteredJudge(version) {
  const spec = modelSpecForVersion(version);
  const form = document.getElementById("judgeRegistryForm");
  if (!spec || !form) return;
  const options = spec.options || {};
  const preset = judgePromptPresets[spec.system_prompt_preset]
    ? spec.system_prompt_preset
    : (spec.system_prompt_preset ? "custom" : "judge_default_v1");
  copySelectField("judgeRegistryProvider", providerForRegistrySelect(spec.provider, ""), "");
  copyModelField("judgeRegistryConfigId", spec.config_id || version);
  copyModelField("judgeRegistryDisplayName", spec.display_name || spec.model || version);
  copyModelField("judgeRegistryModel", spec.model || version);
  copyModelField("judgeRegistryBaseUrl", spec.base_url || "");
  copyModelField("judgeRegistryChatUrl", externalEndpointValue(spec, "chat_url", "upstream_chat_url"));
  copyModelField("judgeRegistryApiKeyEnv", spec.api_key_env || "");
  copyModelField("judgeRegistryApiKeyValue", "");
  copyModelField("judgeRegistryTemperature", options.temperature ?? 0);
  copyModelField("judgeRegistryTopP", options.top_p ?? options.topP ?? 0.1);
  copyModelField("judgeRegistryMaxTokens", judgeMaxTokensFromOptions(options));
  copySelectField("judgeRegistryPromptPreset", preset, "judge_default_v1");
  copyModelField("judgeRegistryPromptVersion", spec.prompt_version || judgePromptPresets[preset]?.version || judgePromptPresets.judge_default_v1.version);
  copyModelField("judgeRegistrySystemPrompt", spec.system_prompt || "");
  copyModelField("judgeRegistryOptionsJson", registryOptionsJson(options, [
    "temperature",
    "top_p",
    "topP",
    "max_completion_tokens",
    "maxCompletionTokens",
    "max_output_tokens",
    "maxOutputTokens",
    "max_tokens",
    "maxTokens",
    "num_predict",
  ]));
  updateJudgeRegistryProviderFields();
  updateJudgePromptPresetFields();
  if (preset === "custom") copyModelField("judgeRegistrySystemPrompt", spec.system_prompt || "");
  openJudgeAdvancedFields();
  setJudgeRegistryMessage(`수정 모드: ${modelLabelForVersion(version)}. 저장하면 같은 설정 ID가 업데이트됩니다.`, "ok");
  activateTab("settings");
  form.scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetJudgeRegistryForm(form = document.getElementById("judgeRegistryForm")) {
  form?.reset();
  copySelectField("judgeRegistryProvider", "", "");
  copyModelField("judgeRegistryTemperature", "0");
  copyModelField("judgeRegistryTopP", "0.1");
  copyModelField("judgeRegistryMaxTokens", "1024");
  copySelectField("judgeRegistryPromptPreset", "judge_default_v1", "judge_default_v1");
  copyModelField("judgeRegistryPromptVersion", judgePromptPresets.judge_default_v1.version);
  copyModelField("judgeRegistrySystemPrompt", "");
  copyModelField("judgeRegistryOptionsJson", "");
  copyModelField("judgeRegistryApiKeyValue", "");
  updateJudgeRegistryProviderFields();
  updateJudgePromptPresetFields();
}

function prefillPromptVariant(baseId, tag) {
  const spec = modelSpecForVersion(baseId);
  if (!spec) return;
  const resolvedTag = tag || defaultPromptVariantTag(baseId);
  const label = modelLabelForVersion(baseId);
  copyModelField("promptVariantQuickBase", baseId);
  copyModelField("promptVariantQuickTag", resolvedTag);
  copyModelField("modelPromptVariantOf", baseId);
  copyModelField("modelExperimentTag", resolvedTag);
  copyModelField("modelProvider", spec.provider || "ollama");
  copyModelField("modelConfigId", promptVariantConfigId(baseId, resolvedTag));
  copyModelField("modelDisplayName", `${label} · ${resolvedTag}`);
  copyModelField("modelName", spec.model || baseId);
  copyModelField("modelCacheIdentity", spec.cache_identity || spec.model_artifact_id || "");
  copyModelField("modelBaseUrl", spec.base_url || "");
  copyModelField("modelBaseUrlEnv", spec.base_url_env || "");
  copyModelField("modelChatUrl", externalEndpointValue(spec, "chat_url", "upstream_chat_url"));
  copyModelField("modelHealthUrl", externalEndpointValue(spec, "health_url", "upstream_health_url"));
  copyModelField("modelApiKeyEnv", spec.api_key_env || "");
  copyModelField("modelPromptVersion", promptVariantVersion(spec, resolvedTag));
  copyModelField("modelSystemPrompt", spec.system_prompt || "");
  copyModelField("modelQueryPromptTemplate", spec.query_prompt_template || spec.prompt_template || "");
  copyModelField("modelOptionsJson", JSON.stringify(spec.options || {}, null, 2));
  copyModelField("modelLocalPath", spec.local_path || "");
  setModelFamilyFormValue(spec.model_family || modelFamilyInfo(baseId, spec.model).familyLabel, spec.model_family_color || modelFamilyInfo(baseId, spec.model).color);
  updateModelRegistryProviderFields();
  openModelAdvancedFields();
  setRegistryMessage(`프롬프트 변형 초안: ${label} -> ${resolvedTag}. 시스템 프롬프트를 수정한 뒤 등록하세요.`, "ok");
}

function updatePromptVariantIdentity() {
  const baseId = document.getElementById("modelPromptVariantOf")?.value || "";
  const tag = document.getElementById("modelExperimentTag")?.value || "";
  if (!baseId) return;
  const spec = modelSpecForVersion(baseId);
  copyModelField("modelConfigId", promptVariantConfigId(baseId, tag));
  copyModelField("modelDisplayName", `${modelLabelForVersion(baseId)} · ${tag || "v1"}`);
  copyModelField("modelPromptVersion", promptVariantVersion(spec, tag));
}

function renderTargetRegistry() {
  const list = document.getElementById("targetRegistryList");
  const variantSelect = document.getElementById("modelPromptVariantOf");
  const quickSelect = document.getElementById("promptVariantQuickBase");
  const ids = evalTargetRegistryIds();
  populatePromptVariantSelect(variantSelect, ids, "새 대상 모델");
  populatePromptVariantSelect(quickSelect, ids, "기준 모델 선택");
  populateModelFamilySelect();
  if (!list) return;
  if (!ids.length) {
    list.innerHTML = emptyState("등록된 대상 모델이 없습니다.");
    return;
  }
  list.innerHTML = ids.map((id) => {
    const spec = modelSpecForVersion(id);
    const family = modelFamilyInfo(id, spec.model);
    const sourceLabel = "사용자 등록";
    const promptParts = [
      spec.prompt_version || "prompt_v1",
      spec.experiment_tag ? `태그 ${spec.experiment_tag}` : "",
      spec.prompt_variant_of ? `변형 ${spec.prompt_variant_of}` : "",
      spec.cache_identity ? `캐시 ${spec.cache_identity}` : "",
    ].filter(Boolean);
    const detailTitle = [
      modelLabelForVersion(id),
      spec.provider || "",
      spec.model || id,
      id,
      ...promptParts,
    ].filter(Boolean).join(" · ");
    return `
      <div class="registry-item target-registry-item" title="${escapeHtml(detailTitle)}">
        <div class="target-registry-main">
          <div class="target-registry-title-row">
            <strong class="target-registry-title">${escapeHtml(modelLabelForVersion(id))}</strong>
            <span class="registry-family-badge" style="${escapeHtml(modelFamilyStyle(family))}">
              <b class="model-family-dot" aria-hidden="true"></b>
              ${escapeHtml([family.familyLabel, family.paramLabel, family.quantLabel].filter(Boolean).join(" · "))}
            </span>
            ${modelConnectionPill(id)}
            <button type="button" class="connection-health" data-check-model="${escapeHtml(id)}" ${modelHealthCheckInFlight ? "disabled" : ""}>연결 확인</button>
          </div>
          <span class="target-registry-meta">${escapeHtml(spec.provider || "-")} · ${escapeHtml(spec.model || id)}</span>
          <code class="target-registry-code">${escapeHtml(id)} · ${escapeHtml(promptParts.join(" · "))}</code>
        </div>
        <div class="connection-actions">
          <span class="registry-badge">${escapeHtml(sourceLabel)}</span>
          <button type="button" class="connection-edit" data-edit-model="${escapeHtml(id)}">수정</button>
          <button type="button" class="connection-delete" data-delete-model="${escapeHtml(id)}">삭제</button>
        </div>
      </div>
    `;
  }).join("");
  bindTargetRegistryButtons();
}

function populatePromptVariantSelect(select, ids, emptyLabel) {
  if (!select) return;
  const current = select.value;
  select.innerHTML = [
    `<option value="">${escapeHtml(emptyLabel)}</option>`,
    ...ids.map((id) => `<option value="${escapeHtml(id)}">${escapeHtml(modelLabelForVersion(id))}</option>`),
  ].join("");
  if (current && ids.includes(current)) select.value = current;
}

function bindTargetRegistryButtons() {
  document.querySelectorAll("[data-edit-model]").forEach((button) => {
    button.addEventListener("click", () => {
      const version = button.dataset.editModel;
      if (!version) return;
      editRegisteredModel(version);
    });
  });
  document.querySelectorAll("[data-check-model]").forEach((button) => {
    button.addEventListener("click", async () => {
      const version = button.dataset.checkModel;
      if (!version || modelHealthCheckInFlight) return;
      setRegistryMessage(`연결 확인 중: ${modelLabelForVersion(version)}`, "");
      await syncSelectedModelApis([version], { requireSelected: false, scope: "single" });
      const stateInfo = state.modelConnections.get(version);
      const ok = ["connected", "installed", "available", "configured"].includes(stateInfo?.status);
      setRegistryMessage(
        `${ok ? "연결 확인 완료" : "연결 확인 실패"}: ${modelLabelForVersion(version)}${stateInfo?.message ? ` · ${stateInfo.message}` : ""}`,
        ok ? "ok" : "error",
      );
    });
  });
  document.querySelectorAll("[data-delete-model]").forEach((button) => {
    button.addEventListener("click", async () => {
      const version = button.dataset.deleteModel;
      if (!version) return;
      await deleteRegisteredModel(version);
    });
  });
}

async function deleteRegisteredModel(version) {
  const label = modelLabelForVersion(version);
  const sourceNote = "사용자 등록 항목이 삭제됩니다.";
  if (!window.confirm(`${label} 등록 항목을 삭제할까요? ${sourceNote} 실제 모델 파일/API는 삭제하지 않습니다.`)) {
    return;
  }
  setRegistryMessage(`삭제 중: ${label}`, "");
  try {
    const response = await apiFetch(`api/model-registry/${encodeURIComponent(version)}`, {
      method: "DELETE",
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);

    modelRegistry = body.registry || modelRegistry;
    state.resultVersions.delete(version);
    state.runConfigVersions.delete(version);
    renderTargetRegistry();
    renderJudgeRegistry();
    renderFilters();
    renderEvalConfigFilters();
    renderAll();
    updateHealthCheckButtonState();
    setRegistryMessage(`삭제 완료: ${label}`, "ok");
  } catch (error) {
    setRegistryMessage(`삭제 실패: ${error.message}`, "error");
  }
}

function toastRegion() {
  let region = document.getElementById("toastRegion");
  if (!region) {
    region = document.createElement("div");
    region.id = "toastRegion";
    region.className = "toast-region";
    region.setAttribute("aria-live", "polite");
    region.setAttribute("aria-label", "알림");
    document.body.appendChild(region);
  }
  return region;
}

function removeToast(toast) {
  if (!toast) return;
  toast.remove();
}

function showToast(message, type = "") {
  if (!message || !["ok", "error"].includes(type)) return;
  const region = toastRegion();
  const toast = document.createElement("div");
  toast.className = `toast-message ${type}`.trim();
  toast.dataset.toastId = String(++toastSequence);
  toast.setAttribute("role", type === "error" ? "alert" : "status");

  const text = document.createElement("span");
  text.textContent = message;
  const close = document.createElement("button");
  close.type = "button";
  close.setAttribute("aria-label", "알림 닫기");
  close.textContent = "x";
  close.addEventListener("click", () => removeToast(toast));

  toast.append(text, close);
  region.prepend(toast);
  [...region.querySelectorAll(".toast-message")].slice(4).forEach(removeToast);
  window.setTimeout(() => removeToast(toast), type === "error" ? 8000 : 4500);
}

function setPanelMessage(target, message, type) {
  if (!target) return;
  const normalizedType = type || "";
  target.className = `form-message ${normalizedType}`.trim();
  target.textContent = message;
  showToast(message, normalizedType);
}

function setRegistryMessage(message, type) {
  const target = document.getElementById("modelRegistryMessage");
  setPanelMessage(target, message, type);
}

function setJudgeRegistryMessage(message, type) {
  const target = document.getElementById("judgeRegistryMessage");
  setPanelMessage(target, message, type);
}

function renderJudgeRegistry() {
  const list = document.getElementById("judgeRegistryList");
  const picker = document.getElementById("evalJudgeConfigId");
  const ids = judgeModelIds();
  renderJudgeCopyTargetSelect();
  const renderPicker = (target, attrName, selectedIds) => {
    if (!target) return;
    const targetIds = evalTargetRegistryIds();
    const current = new Set(selectedIds);
    if (!judgePickerInitialized && !current.size && ids.length) current.add(ids[0]);
    judgePickerInitialized = true;
    const renderOption = (id) => {
      const spec = modelRegistry[id] || {};
      return `
        <label class="judge-option">
          <input type="checkbox" ${attrName} value="${escapeHtml(id)}" ${current.has(id) ? "checked" : ""}>
          <span>
            <strong>${escapeHtml(modelLabelForVersion(id))}</strong>
            <em>${escapeHtml([spec.provider || "", spec.model || id].filter(Boolean).join(" · "))}</em>
          </span>
        </label>
      `;
    };
    const sections = [];
    if (ids.length) {
      sections.push(`
        <div class="judge-option-group">
          <strong>Judge 설정</strong>
          ${ids.map(renderOption).join("")}
        </div>
      `);
    }
    if (targetIds.length) {
      const selectedTargetCount = targetIds.filter((id) => current.has(id)).length;
      sections.push(`
        <details class="judge-option-group judge-option-collapsible" ${selectedTargetCount ? "open" : ""}>
          <summary>
            <span>대상 모델을 Judge로 사용</span>
            <em>${selectedTargetCount ? `${selectedTargetCount}개 선택 / ` : ""}${targetIds.length}</em>
          </summary>
          <div class="judge-option-list">
            ${targetIds.map(renderOption).join("")}
          </div>
        </details>
      `);
    }
    target.innerHTML = sections.join("") || emptyState("등록된 Judge 또는 대상 모델이 없습니다.");
  };
  renderPicker(picker, "data-judge-config", selectedJudgeConfigIds());
  enforceJudgeSelectionForScoringMode();
  syncJudgeAggregationControls();
  renderJudgeWeightInputs();
  updateJudgeHealthCheckButtonState();
  if (!list) return;
  if (!ids.length) {
    list.innerHTML = emptyState("등록된 Judge 모델이 없습니다. 설정에서 Qwen2.5-7B HAL LoRA 또는 API judge를 추가하세요.");
    return;
  }
  list.innerHTML = ids.map((id) => {
    const spec = modelRegistry[id] || {};
    const sourceLabel = "사용자 등록";
    const endpoint = spec.upstream_chat_url || spec.chat_url || spec.base_url || spec.local_path || "endpoint 없음";
    const promptMeta = [
      spec.prompt_version || "",
      spec.system_prompt_preset ? `preset ${spec.system_prompt_preset}` : "",
    ].filter(Boolean).join(" · ");
    const detailTitle = [
      modelLabelForVersion(id),
      spec.provider || "",
      spec.model || id,
      promptMeta,
      endpoint,
    ].filter(Boolean).join(" · ");
    return `
      <div class="registry-item judge-registry-item" title="${escapeHtml(detailTitle)}">
        <div class="target-registry-main">
          <div class="target-registry-title-row">
            <strong class="target-registry-title">${escapeHtml(modelLabelForVersion(id))}</strong>
            ${modelConnectionPill(id)}
            <button type="button" class="connection-health" data-check-judge="${escapeHtml(id)}" ${modelHealthCheckInFlight ? "disabled" : ""}>연결 확인</button>
          </div>
          <span class="target-registry-meta">${escapeHtml(spec.provider || "-")} · ${escapeHtml(spec.model || id)}</span>
          <code class="target-registry-code">${escapeHtml(id)}</code>
        </div>
        <div class="connection-actions">
          <span class="registry-badge">${escapeHtml(sourceLabel)}</span>
          <button type="button" class="connection-edit" data-edit-judge="${escapeHtml(id)}">수정</button>
          <button type="button" class="connection-delete" data-delete-judge="${escapeHtml(id)}">삭제</button>
        </div>
      </div>
    `;
  }).join("");
  bindJudgeRegistryButtons();
}

function bindJudgeRegistryButtons() {
  document.querySelectorAll("[data-edit-judge]").forEach((button) => {
    button.addEventListener("click", () => {
      const version = button.dataset.editJudge;
      if (!version) return;
      editRegisteredJudge(version);
    });
  });
  document.querySelectorAll("[data-check-judge]").forEach((button) => {
    button.addEventListener("click", async () => {
      const version = button.dataset.checkJudge;
      if (!version || modelHealthCheckInFlight) return;
      setJudgeRegistryMessage(`Judge 연결 확인 중: ${modelLabelForVersion(version)}`, "");
      await syncSelectedModelApis([version], { requireSelected: false, scope: "single" });
      const stateInfo = state.modelConnections.get(version);
      const ok = ["connected", "installed", "available", "configured"].includes(stateInfo?.status);
      setJudgeRegistryMessage(
        `${ok ? "Judge 연결 확인 완료" : "Judge 연결 확인 실패"}: ${modelLabelForVersion(version)}${stateInfo?.message ? ` · ${stateInfo.message}` : ""}`,
        ok ? "ok" : "error",
      );
    });
  });
  document.querySelectorAll("[data-delete-judge]").forEach((button) => {
    button.addEventListener("click", async () => {
      const version = button.dataset.deleteJudge;
      if (!version) return;
      await deleteRegisteredJudge(version);
    });
  });
}

async function deleteRegisteredJudge(version) {
  const label = modelLabelForVersion(version);
  const sourceNote = "사용자 등록 항목이 삭제됩니다.";
  if (!window.confirm(`${label} Judge 등록 항목을 삭제할까요? ${sourceNote} 실제 모델 파일/API는 삭제하지 않습니다.`)) {
    return;
  }
  setJudgeRegistryMessage(`삭제 중: ${label}`, "");
  try {
    const response = await apiFetch(`api/model-registry/${encodeURIComponent(version)}`, {
      method: "DELETE",
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);

    modelRegistry = body.registry || modelRegistry;
    renderJudgeRegistry();
    updateJudgePlaceholders();
    updateHealthCheckButtonState();
    renderEvalConfigFilters();
    setJudgeRegistryMessage(`삭제 완료: ${label}`, "ok");
  } catch (error) {
    setJudgeRegistryMessage(`삭제 실패: ${error.message}`, "error");
  }
}

async function fetchWithTimeout(url, options, timeoutMs) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    window.clearTimeout(timeoutId);
  }
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function renderOverview(runData, gateData = []) {
  if (!runData.length) {
    setHtml("kpis", emptyState("선택된 모델이 없습니다."));
    setHtml("trendChart", "");
    setHtml("metricBars", "");
    return;
  }

  const aggregate = aggregateRuns(runData);
  const applicableGateData = gateData.filter((d) => d.release_gate && d.release_gate !== "not_applicable");
  const gateCounts = countBy(applicableGateData, "release_gate");
  const topGate = !gateData.length || !applicableGateData.length
    ? "not_applicable"
    : applicableGateData.some((d) => d.release_gate === "block")
    ? "block"
    : applicableGateData.some((d) => d.release_gate === "review")
      ? "review"
      : "pass";

  setHtml("kpis", [
    kpi("자동채점 평균", aggregate.scored_average.toFixed(1), `${aggregate.review_pending_count.toLocaleString()}개 검토대기 제외`),
    kpi("전체 평균", aggregate.overall_score.toFixed(1), "검토대기 포함 잠정치"),
    kpi("통과율", `${(aggregate.pass_rate * 100).toFixed(1)}%`, "선택 실행"),
    kpi("평가 문항", `${aggregate.total_questions.toLocaleString()}개`, aggregate.run_type),
    kpi("배포 판정", gateLabel(topGate), `${gateCounts.block ?? 0}개 차단 / ${gateCounts.review ?? 0}개 검토`),
  ].join(""));

  renderTrend([...runData].sort((a, b) => modelLabelForVersion(a.version).localeCompare(modelLabelForVersion(b.version), "ko")));
  renderMetricBars(aggregate);
}

function selectedQuestionStats() {
  const selected = questionlistSummary?.selected?.selected ?? {};
  const behavior = selected.expected_behavior ?? {};
  const refusalCount =
    Number(behavior.answer_not_supported_or_refuse ?? 0) +
    Number(behavior.abstain_when_unsupported ?? 0) +
    Number(behavior.refuse_unsafe_request ?? 0);
  return {
    total: Number(selected.total ?? questionlistCases.length ?? 0),
    mode: questionlistSummary?.selected?.mode ?? "selected",
    safety: refusalCount,
  };
}

function aggregateRuns(runData) {
  const count = Math.max(runData.length, 1);
  const totals = {
    total_questions: Math.max(...runData.map((d) => Number(d.total_questions || 0)), 0),
    scored_questions: Math.max(...runData.map((d) => Number(d.scored_questions || d.total_questions || 0)), 0),
    review_pending_count: Math.max(...runData.map((d) => Number(d.review_pending_count || 0)), 0),
    pass_rate: runData.reduce((sum, d) => sum + Number(d.pass_rate || 0), 0) / count,
    scored_pass_rate: runData.reduce((sum, d) => sum + Number(d.scored_pass_rate || d.pass_rate || 0), 0) / count,
    overall_score: runData.reduce((sum, d) => sum + Number(d.overall_score || 0), 0) / count,
    scored_average: runData.reduce((sum, d) => sum + Number(d.scored_average || d.overall_score || 0), 0) / count,
    avg_latency_ms: runData.reduce((sum, d) => sum + Number(d.avg_latency_ms || 0), 0) / count,
    avg_cost_krw: runData.reduce((sum, d) => sum + Number(d.avg_cost_krw || 0), 0) / count,
    run_type: "선택 모델",
  };
  metricCols.forEach((key) => {
    const rows = key === "utl" ? runData.filter((d) => d.utl_applicable) : runData;
    totals[key] = rows.length ? rows.reduce((sum, d) => sum + Number(d[key] || 0), 0) / rows.length : 0;
  });
  totals.utl_applicable = runData.some((d) => d.utl_applicable);
  return totals;
}

function renderReleaseGates(gateData) {
  if (!gateData.length) {
    setHtml("runGateKpis", emptyState("배포 판정 데이터가 없습니다."));
    setHtml("runGateTable", "");
    return;
  }
  const applicableGateData = gateData.filter((d) => d.release_gate !== "not_applicable");
  if (!applicableGateData.length) {
    const evaluatedCases = Math.max(...gateData.map((d) => Number(d.evaluated_cases || 0)), 0);
    setHtml("runGateKpis", [
      kpi("판정 대상 모델", "0개", `${gateData.length.toLocaleString()}개 모델은 분석 전용`),
      kpi("평가 문항", `${evaluatedCases.toLocaleString()}개`, "배포 판정 제외"),
      kpi("차단 문항", "0개", "판정 대상 없음"),
      kpi("검토 문항", "0개", "판정 대상 없음"),
    ].join(""));
    const reason = gateData.map((d) => d.reason).find(Boolean) || "no gate-eligible cases";
    setHtml("runGateTable", emptyState(`현재 선택한 실행은 배포 차단 기준이 적용되지 않는 분석용 결과입니다. 사유: ${releaseDecisionReason(reason)}`));
    return;
  }
  const counts = countBy(applicableGateData, "release_gate");
  const blockCases = applicableGateData.reduce((sum, d) => sum + Number(d.block_count || 0), 0);
  const reviewCases = applicableGateData.reduce((sum, d) => sum + Number(d.review_count || 0), 0);
  const minCorePass = applicableGateData.length ? Math.min(...applicableGateData.map((d) => Number(d.core_pass_rate || 0))) : 0;
  setHtml("runGateKpis", [
    kpi("차단 모델", `${Number(counts.block || 0).toLocaleString()}개`, "배포 보류"),
    kpi("검토 모델", `${Number(counts.review || 0).toLocaleString()}개`, "수동 확인 필요"),
    kpi("차단 문항", `${blockCases.toLocaleString()}개`, `${reviewCases.toLocaleString()}개 검토`),
    kpi("최소 핵심 통과율", applicableGateData.length ? `${(minCorePass * 100).toFixed(1)}%` : "N/A", "모델별 최저값"),
  ].join(""));
  setHtml("runGateTable", table(
    ["모델", "최종 상태", "판정 문항", "전체 통과율", "핵심 통과율", "차단 문항", "검토 문항", "치명 오류", "근거"],
    [...gateData]
      .sort((a, b) => releaseRank(a.release_gate) - releaseRank(b.release_gate) || a.config_id.localeCompare(b.config_id))
      .filter((d) => d.release_gate !== "not_applicable")
      .map((d) => [
        modelCell(d.config_id, d.model),
        gateBadge(d.release_gate),
        d.gate_eligible_cases || d.total_cases || 0,
        formatPercent(d.pass_rate),
        formatPercent(d.core_pass_rate),
        d.block_count,
        d.review_count,
        d.critical_fail_count,
        releaseDecisionReason(d.reason),
      ])
  ));
}

function renderResultViewer(caseData, runData = [], gateData = []) {
  const matrixEl = document.getElementById("resultMatrix");
  if (!matrixEl) return;

  renderResultModelFilter(caseData);

  const prepared = prepareResultMatrixRows(caseData);
  const groups = prepared.groups;
  const models = prepared.models;
  const visibleGroups = groups.slice(0, 120);

  const totalCells = caseData.length;
  const failCells = caseData.filter((row) => isFailureCell(row)).length;
  const reviewCells = caseData.filter((row) => isReviewCell(row)).length;
  const avgScore = totalCells ? caseData.reduce((sum, row) => sum + caseOverallScore(row), 0) / totalCells : 0;
  setHtml("resultViewerStats", [
    kpi("케이스", groups.length.toLocaleString(), `${visibleGroups.length.toLocaleString()}개 표시`),
    kpi("모델", models.length.toLocaleString(), `${runData.length.toLocaleString()}개 실행 행`),
    kpi("실패 응답", failCells.toLocaleString(), `${reviewCells.toLocaleString()}개 검토`),
    kpi("평균 점수", avgScore.toFixed(1), gateData.length ? "배포 판정 포함" : "케이스 단위"),
  ].join(""));

  if (!groups.length || !models.length) {
    setHtml("resultMatrix", emptyState("현재 필터에 맞는 결과 행이 없습니다."));
    setHtml("resultDetail", emptyState("문항-모델 셀을 선택하면 상세 응답을 확인할 수 있습니다."));
    return;
  }

  const firstKey = `${visibleGroups[0].caseId}::${models[0]}`;
  const hasSelected = visibleGroups.some((group) => models.some((model) => `${group.caseId}::${model}` === state.selectedMatrixKey));
  if (!state.selectedMatrixKey || !hasSelected) state.selectedMatrixKey = firstKey;

  const header = `
    <div class="result-matrix-row result-matrix-head">
      <div class="result-case-head">문항</div>
      ${models.map((model) => `<div class="result-model-head" title="${escapeHtml(modelLabelForVersion(model))}">${escapeHtml(shortLabel(shortModelLabel(model), 22))}</div>`).join("")}
    </div>
  `;
  const body = visibleGroups.map((group) => `
    <div class="result-matrix-row">
      <div class="result-case-cell">
        <strong>${escapeHtml(group.caseId)}</strong>
        <span>${escapeHtml(group.question)}</span>
        <em>${escapeHtml(group.meta)}</em>
      </div>
      ${models.map((model) => renderResultMatrixCell(group.byModel.get(model), group.caseId, model)).join("")}
    </div>
  `).join("");

  setHtml("resultMatrix", `
    <div class="result-matrix-meta">
      <span>${escapeHtml(resultViewLabel(state.resultViewMode))}</span>
      <span>전체 ${groups.length.toLocaleString()}개 케이스</span>
      <span>${models.length.toLocaleString()}개 모델 열</span>
      ${groups.length > visibleGroups.length ? `<span class="matrix-limit-warning">현재 ${visibleGroups.length.toLocaleString()} / 전체 ${groups.length.toLocaleString()}개 표시 · 검색/필터로 범위를 좁히세요</span>` : ""}
    </div>
    <div class="result-matrix" style="--matrix-columns:${models.length}">${header}${body}</div>
  `);

  renderResultDetail(findSelectedMatrixRow(caseData));
}

function renderResultModelFilter(caseData) {
  const select = document.getElementById("resultModelFilter");
  if (!select) return;
  const models = matrixModels(cases.length ? cases : caseData);
  const current = state.resultModelFilter;
  select.innerHTML = [
    `<option value="">전체 모델</option>`,
    ...models.map((model) => `<option value="${escapeHtml(model)}">${escapeHtml(modelLabelForVersion(model))}</option>`),
  ].join("");
  select.value = models.includes(current) ? current : "";
  state.resultModelFilter = select.value;
}

function prepareResultMatrixRows(caseData) {
  const query = state.resultSearch;
  const allGroups = groupCaseRows(caseData);
  const differentCases = new Set(
    allGroups
      .filter((group) => groupHasDifferentResults(group.rows))
      .map((group) => group.caseId)
  );
  const modelFilter = state.resultModelFilter;
  const filteredRows = caseData.filter((row) => {
    if (modelFilter && row.version !== modelFilter) return false;
    if (!rowMatchesResultView(row, differentCases)) return false;
    if (!query) return true;
    return [
      row.question_id,
      row.question,
      row.source_title,
      row.source_url,
      row.error_type,
      labelErrorType(row.error_type),
      row.judge_reason,
      row.static_reason,
      row.llm_judge_reason,
      row.answer_excerpt,
      row.version,
      modelLabelForVersion(row.version),
    ].some((value) => String(value ?? "").toLowerCase().includes(query));
  });
  const groups = groupCaseRows(filteredRows)
    .map((group) => ({
      ...group,
      byModel: new Map(group.rows.map((row) => [row.version, row])),
      worstScore: Math.min(...group.rows.map(caseOverallScore)),
      hasFailure: group.rows.some(isFailureCell),
      hasReview: group.rows.some(isReviewCell),
    }))
    .sort((a, b) =>
      Number(b.hasFailure) - Number(a.hasFailure) ||
      Number(b.hasReview) - Number(a.hasReview) ||
      a.worstScore - b.worstScore ||
      a.caseId.localeCompare(b.caseId)
    );
  return {
    groups,
    models: matrixModels(filteredRows),
  };
}

function groupCaseRows(rows) {
  const map = new Map();
  rows.forEach((row) => {
    const key = row.question_id || row.case_id || "unknown";
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(row);
  });
  return [...map.entries()].map(([caseId, groupedRows]) => {
    const first = groupedRows[0] || {};
    return {
      caseId,
      rows: groupedRows,
      question: first.question || first.source_title || "",
      meta: resultCaseMeta(first),
    };
  });
}

function resultCaseMeta(row) {
  const parts = [
    labelSource(row.source_type),
    labelQuestionType(row.question_type),
    labelTopic(row.qa_topic || row.qa_matrix_topic),
  ].filter((value) => value && value !== "unknown");
  return [...new Set(parts)].join(" / ") || "분류 없음";
}

function matrixModels(rows) {
  return unique(rows.map((row) => row.version))
    .sort((a, b) => modelLabelForVersion(a).localeCompare(modelLabelForVersion(b)));
}

function rowMatchesResultView(row, differentCases) {
  if (state.resultViewMode === "failures") return isFailureCell(row);
  if (state.resultViewMode === "passes") return !isFailureCell(row);
  if (state.resultViewMode === "safety") return isSafetyCell(row);
  if (state.resultViewMode === "different") return differentCases.has(row.question_id);
  if (state.resultViewMode === "review") return isReviewCell(row);
  return true;
}

function groupHasDifferentResults(rows) {
  const statuses = new Set(rows.map((row) => row.pass_fail || "unknown"));
  const scores = rows.map(caseOverallScore);
  return statuses.size > 1 || Math.max(...scores) - Math.min(...scores) >= 15;
}

function isFailureCell(row) {
  return row.pass_fail === "Fail" || caseOverallScore(row) < state.threshold;
}

function isSafetyCell(row) {
  const error = String(row.error_type || "").toLowerCase();
  return Number(row.hal || 0) < state.threshold / 5 ||
    row.release_gate === "block" ||
    error.includes("unsafe") ||
    error.includes("policy") ||
    error.includes("privacy");
}

function isReviewCell(row) {
  return row.release_gate === "block" ||
    row.release_gate === "review" ||
    row.llm_judge_status === "error" ||
    isTrue(row.human_review_required);
}

function renderResultMatrixCell(row, caseId, model) {
  if (!row) return `<div class="matrix-result-cell empty" title="데이터 없음">-</div>`;
  const key = `${caseId}::${model}`;
  const score = caseOverallScore(row);
  const gap = judgeScoreGap(row);
  const hasJudgeConflict = row.llm_judge_conflict_detected || row.llm_judge_conflict || gap >= 30 || row.llm_judge_pass_mismatch;
  const judgeInfo = judgeConflictCellInfo(row, gap);
  const badge = judgeInfo.primary || passFailLabel(row.pass_fail);
  const secondaryBadge = matrixSecondaryBadge(row, judgeInfo);
  const classes = [
    "matrix-result-cell",
    isFailureCell(row) ? "fail" : "pass",
    isReviewCell(row) ? "review" : "",
    hasJudgeConflict ? "judge-conflict" : "",
    row.llm_judge_arbiter_override ? "arbiter-override" : "",
    state.selectedMatrixKey === key ? "selected" : "",
  ].filter(Boolean).join(" ");
  const ariaLabel = `${caseId}, ${modelLabelForVersion(model)}, ${score.toFixed(0)}점, ${judgeInfo.title || badge || "-"}`;
  return `
    <button class="${classes}" type="button" data-matrix-key="${escapeHtml(key)}" aria-label="${escapeHtml(ariaLabel)}" title="${escapeHtml(judgeInfo.title || ariaLabel)}">
      <strong>${score.toFixed(0)}</strong>
      <span class="matrix-status-label ${hasJudgeConflict ? "conflict" : ""}">${escapeHtml(badge || "-")}</span>
      ${secondaryBadge.label ? `<small class="matrix-secondary-badge ${escapeHtml(secondaryBadge.tone)}">${escapeHtml(secondaryBadge.label)}</small>` : ""}
    </button>
  `;
}

function matrixSecondaryBadge(row, judgeInfo = {}) {
  const label = judgeInfo.secondary ||
    (row.release_gate === "block" ? "배포 차단" : "") ||
    (row.release_gate === "review" ? "검토 필요" : "") ||
    (row.llm_judge_status === "error" ? "Judge 오류" : "") ||
    (isTrue(row.human_review_required) ? "검토 필요" : "") ||
    (row.llm_judge_unresolved_conflict ? "검토 필요" : "");
  if (!label) return { label: "", tone: "" };
  const text = String(label);
  const tone = row.release_gate === "block" || text.includes("차단")
    ? "block"
    : text.includes("상위")
      ? "arbiter"
      : text.includes("판정") || row.llm_judge_pass_mismatch
        ? "mismatch"
        : row.llm_judge_status === "error"
          ? "error"
          : "review";
  return { label: text, tone };
}

function judgeConflictCellInfo(row, gap) {
  const roundedGap = Math.round(gap);
  const hasLargeGap = gap >= 30;
  const hasMismatch = row.llm_judge_pass_mismatch;
  const override = row.llm_judge_arbiter_override;
  const parts = [];
  if (gap > 0) parts.push(`Judge 점수차 ${gap.toFixed(1)}점`);
  if (Number(row.llm_judge_score_min) || Number(row.llm_judge_score_max)) {
    parts.push(`Judge 범위 ${scoreValueLabel(row.llm_judge_score_min)}-${scoreValueLabel(row.llm_judge_score_max)}점`);
  }
  if (hasMismatch) parts.push("통과/실패 판단 불일치");
  if (override) {
    parts.push(`상위 Judge 최종 반영${row.llm_judge_arbiter_score ? ` (${scoreValueLabel(row.llm_judge_arbiter_score)}점)` : ""}`);
  }
  if (row.llm_judge_arbiter_config_id) parts.push(`상위 Judge: ${row.llm_judge_arbiter_config_id}`);
  if (override) {
    return {
      primary: hasLargeGap ? `Judge 차이 ${roundedGap}점` : "상위 Judge 반영",
      secondary: "상위 Judge 반영",
      title: parts.join(" · "),
    };
  }
  if (hasLargeGap) {
    return {
      primary: `Judge 차이 ${roundedGap}점`,
      secondary: hasMismatch ? "판정도 다름" : "검토 필요",
      title: parts.join(" · "),
    };
  }
  if (hasMismatch) {
    return {
      primary: "Judge 판정 불일치",
      secondary: "검토 필요",
      title: parts.join(" · "),
    };
  }
  return { primary: "", secondary: "", title: parts.join(" · ") };
}

function findSelectedMatrixRow(caseData) {
  if (!state.selectedMatrixKey) return null;
  const [caseId, model] = state.selectedMatrixKey.split("::");
  return caseData.find((row) => (row.question_id || row.case_id || "unknown") === caseId && row.version === model) || null;
}

function parseJsonArrayField(value) {
  if (Array.isArray(value)) return value;
  if (!value) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function resultJudgeScores(row) {
  return parseJsonArrayField(row?.llm_judge_individual_scores)
    .filter((score) => score && typeof score === "object");
}

function resultJudgeCount(row, scores = resultJudgeScores(row)) {
  if (scores.length) return scores.length;
  const explicitCount = Number(row?.llm_judge_count);
  return Number.isFinite(explicitCount) && explicitCount > 0 ? explicitCount : 0;
}

function resultHasArbiter(row, scores = resultJudgeScores(row)) {
  const arbiterScore = Number(row?.llm_judge_arbiter_score);
  return Boolean(
    row?.llm_judge_arbiter_override ||
    (Number.isFinite(arbiterScore) && arbiterScore > 0) ||
    scores.some((score) => String(score.role || "").toLowerCase() === "arbiter"),
  );
}

function resultScoringLabel(row) {
  const mode = row?.scoring_mode || "";
  const scores = resultJudgeScores(row);
  const judgeCount = resultJudgeCount(row, scores);
  const hasArbiter = resultHasArbiter(row, scores);
  if (mode === "static" || mode === "answers_only") return scoringModeLabel(mode) || "-";
  if (mode === "static_llm") {
    if (judgeCount > 1) return `규칙 점수 + 여러 Judge 감사 (${judgeCount}개${hasArbiter ? " · 상위 Judge 포함" : ""})`;
    if (judgeCount === 1) return "규칙 점수 + 단일 Judge 감사";
    return scoringModeLabel(mode) || "-";
  }
  if (mode === "blend") {
    if (judgeCount > 1) return `Judge+규칙 혼합 · 여러 Judge (${judgeCount}개${hasArbiter ? " · 상위 Judge 포함" : ""})`;
    if (judgeCount === 1) return "Judge+규칙 혼합 · 단일 Judge";
    return scoringModeLabel(mode) || "-";
  }
  if (judgeCount > 1) return `여러 Judge 평가 (${judgeCount}개${hasArbiter ? " · 상위 Judge 포함" : ""})`;
  if (judgeCount === 1) return "단일 Judge 채점";
  return scoringModeLabel(mode) || "-";
}

function resultJudgeReadableName(score, index = 0) {
  if (!score) return "";
  const judgeId = score.config_id || score.model || score.provider || "";
  const label = String(score.role || "").toLowerCase() === "arbiter" ? "상위 Judge" : judgeDecisionLabel(judgeId, index);
  const model = score.model || score.config_id || score.provider || "";
  return [label, model].filter(Boolean).join(" · ");
}

function resultJudgeSummaryLabel(row) {
  const scores = resultJudgeScores(row);
  const judgeCount = resultJudgeCount(row, scores);
  if (judgeCount > 1) {
    return `${judgeCount}개 Judge${resultHasArbiter(row, scores) ? " · 상위 Judge 포함" : ""}`;
  }
  if (judgeCount === 1 && scores.length) return resultJudgeReadableName(scores[0], 0);
  return [row?.llm_judge_provider, row?.llm_judge_model].filter(Boolean).join(" / ") || "-";
}

function resultJudgeListLabel(row) {
  const scores = resultJudgeScores(row);
  if (scores.length) return scores.map((score, index) => resultJudgeReadableName(score, index)).join(" / ");
  return [row?.llm_judge_provider, row?.llm_judge_model].filter(Boolean).join(" / ") || "-";
}

function resultFinalReason(row) {
  const reason = row.llm_judge_reason || row.judge_reason || row.static_reason || "";
  if (!reason) return "등록된 최종 채점 메모가 없습니다.";
  if (resultJudgeCount(row) > 1) {
    return String(reason)
      .replace(/^LLM Judge 단독 채점\s*:/, "여러 Judge 집계:")
      .replace(/^Single LLM Judge scoring\s*:/i, "Multi-Judge aggregation:");
  }
  return reason;
}

function renderJudgeDecisionCards(row) {
  const scores = resultJudgeScores(row);
  if (!scores.length) return "";
  const cards = scores.map((score, index) => {
    const judgeId = score.config_id || score.model || score.provider || "-";
    const label = score.role === "arbiter" ? "상위 Judge" : judgeDecisionLabel(judgeId, index);
    const total = Number(score.overall_score ?? 0);
    const scoreUtlApplicable = score.utl_applicable === undefined || score.utl_applicable === ""
      ? row.utl_applicable
      : !isFalse(score.utl_applicable);
    const metrics = ["acc", "com", "utl", "nac", "hal"]
      .filter((key) => score[key] !== undefined && score[key] !== "" && (key !== "utl" || scoreUtlApplicable))
      .map((key) => `${metricDisplayLabel(key)} ${Number(score[key] || 0).toFixed(1)}`)
      .join(" · ");
    const promptInfo = [score.prompt_version, score.prompt_hash ? `hash ${score.prompt_hash}` : ""].filter(Boolean).join(" · ");
    const usedAsFinal = row.llm_judge_arbiter_override && score.role === "arbiter";
    return `
      <div class="judge-decision-card ${score.role === "arbiter" ? "arbiter" : ""} ${usedAsFinal ? "used-final" : ""}">
        <div class="judge-card-head">
          <strong>${escapeHtml(label)} · ${escapeHtml(judgeId)}</strong>
          <em>${usedAsFinal ? "최종 반영 · " : ""}${escapeHtml(score.pass === true ? "통과" : score.pass === false ? "실패" : "-")} · ${total.toFixed(1)}</em>
        </div>
        ${metrics ? `<span class="judge-card-metrics">${escapeHtml(metrics)}</span>` : ""}
        ${promptInfo ? `<small>${escapeHtml(promptInfo)}</small>` : ""}
        <p class="judge-card-reason">${escapeHtml(score.reason || "등록된 Judge 판단 사유가 없습니다.")}</p>
      </div>
    `;
  }).join("");
  return `
    <div class="detail-block judge-detail-section">
      <h3>Judge별 판단 사유</h3>
      <p class="detail-section-note">각 Judge가 독립적으로 남긴 점수와 사유입니다. 상위 Judge가 최종 반영된 경우 카드에 표시됩니다.</p>
      <div class="judge-decision-grid">${cards}</div>
    </div>
  `;
}

function judgeDecisionLabel(judgeId, index) {
  const id = String(judgeId || "").toLowerCase();
  if (id.includes("clova") || id.includes("hcx")) return "Clova Judge";
  if (id.includes("openai") || id.includes("gpt")) return "OpenAI Judge";
  return `Judge ${index + 1}`;
}

function judgeScoreGap(row) {
  if (Number.isFinite(Number(row.llm_judge_score_gap)) && Number(row.llm_judge_score_gap) > 0) {
    return Number(row.llm_judge_score_gap);
  }
  const scores = parseJsonArrayField(row.llm_judge_individual_scores)
    .map((score) => Number(score.overall_score ?? 0))
    .filter((value) => Number.isFinite(value));
  if (scores.length < 2) return 0;
  return Math.max(...scores) - Math.min(...scores);
}

function renderJudgeConflictSummary(row) {
  const gap = judgeScoreGap(row);
  const passMismatch = row.llm_judge_pass_mismatch;
  const shouldShow = row.llm_judge_conflict_detected || row.llm_judge_conflict || gap >= 20 || passMismatch || row.llm_judge_arbiter_override;
  if (!shouldShow) return "";
  const hasRange = Number(row.llm_judge_score_min) || Number(row.llm_judge_score_max);
  const arbiterScore = Number(row.llm_judge_arbiter_score);
  const hasArbiterResult = resultHasArbiter(row);
  return `
    <div class="detail-block judge-conflict-summary ${row.llm_judge_arbiter_override ? "arbiter-overridden" : ""}">
      <h3>Judge 점수 차이와 최종 반영</h3>
      <div class="judge-conflict-metrics">
        <span>Judge 점수차 <strong>${gap.toFixed(1)}점</strong></span>
        ${hasRange ? `<span>Judge 최저/최고 <strong>${scoreValueLabel(row.llm_judge_score_min)} / ${scoreValueLabel(row.llm_judge_score_max)}점</strong></span>` : ""}
        <span>통과 판정 차이 <strong>${passMismatch ? "있음" : "없음"}</strong></span>
        ${row.llm_judge_arbiter_override ? `<span>최종 반영 <strong>상위 Judge</strong></span>` : ""}
        ${Number.isFinite(arbiterScore) && arbiterScore > 0 ? `<span>상위 Judge 점수 <strong>${scoreValueLabel(arbiterScore)}점</strong></span>` : ""}
        ${row.llm_judge_conflict_resolution_policy ? `<span>처리 방식 <strong>${escapeHtml(judgeResolutionPolicyLabel(row.llm_judge_conflict_resolution_policy))}</strong></span>` : ""}
      </div>
      ${row.llm_judge_conflict_reason ? `<p>${escapeHtml(humanJudgeConflictReason(row.llm_judge_conflict_reason))}</p>` : ""}
      ${hasArbiterResult && row.llm_judge_arbiter_config_id ? `<span class="judge-conflict-note">상위 Judge: ${escapeHtml(row.llm_judge_arbiter_config_id)}</span>` : ""}
    </div>
  `;
}

function scoreValueLabel(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(1) : "-";
}

function judgeResolutionPolicyLabel(value) {
  return {
    arbiter_override: "상위 Judge 결과로 최종 반영",
    three_judge: "3개 Judge 집계",
    review: "수동 검토",
    manual_review_required: "수동 검토 필요",
    none: "추가 처리 없음",
  }[value] || value || "-";
}

function humanJudgeConflictReason(value) {
  return String(value || "")
    .replace(/judge pass\/fail disagreement/gi, "Judge 통과/실패 판단 불일치")
    .replace(/judge relative score gap\s*([0-9.]+)%/gi, "Judge 상대 점수차 $1%")
    .replace(/judge score gap\s*([0-9.]+)/gi, "Judge 점수차 $1점")
    .replace(/resolved by arbiter override:\s*/gi, "상위 Judge 최종 반영: ")
    .replace(/arbiter missing; manual review required/gi, "상위 Judge 결과가 없어 수동 검토 필요")
    .replace(/manual review required/gi, "수동 검토 필요");
}

function renderResultDetail(row) {
  if (!row) {
    setHtml("resultDetail", emptyState("문항-모델 셀을 선택하면 상세 응답을 확인할 수 있습니다."));
    return;
  }
  const metrics = metricCols.map((key) => {
    const unavailable = key === "utl" && !row.utl_applicable;
    const value = Number(row[key] || 0);
    return `
      <div class="detail-score-row">
        <span>${escapeHtml(metricDisplayLabel(key))}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${unavailable ? 0 : clamp(value * 5, 0, 100)}%"></div></div>
        <strong>${unavailable ? "N/A" : value.toFixed(1)}</strong>
      </div>
    `;
  }).join("");
  const finalReason = resultFinalReason(row);
  const judgeList = resultJudgeListLabel(row);
  setHtml("resultDetail", `
    <div class="detail-stack">
      <div class="detail-title">
        <span>${escapeHtml(row.question_id)}</span>
        <strong>${escapeHtml(modelLabelForVersion(row.version))}</strong>
        <em class="${isFailureCell(row) ? "detail-fail" : "detail-pass"}">${escapeHtml(passFailLabel(row.pass_fail))} · ${caseOverallScore(row).toFixed(1)}</em>
      </div>
      <div class="question-box">
        <strong>${escapeHtml(row.question)}</strong>
        <span>${escapeHtml(resultCaseMeta(row))}</span>
      </div>
      <div class="detail-score-grid">${metrics}</div>
      <div class="detail-block">
        <h3>모델 답변</h3>
        <p>${escapeHtml(row.model_answer || row.answer_excerpt || "답변 요약이 없습니다.")}</p>
      </div>
      <div class="detail-block">
        <h3>모범답안</h3>
        <p>${escapeHtml(row.output || "등록된 모범답안이 없습니다.")}</p>
      </div>
      <div class="detail-block result-final-summary">
        <h3>최종 판정 요약</h3>
        <div class="detail-meta-grid">
          <span title="${escapeHtml(resultScoringLabel(row))}"><b>채점</b>${escapeHtml(resultScoringLabel(row))}</span>
          <span title="${escapeHtml(judgeList)}"><b>Judge 구성</b>${escapeHtml(resultJudgeSummaryLabel(row))}</span>
          <span><b>품질 판정</b>${escapeHtml(passFailLabel(row.pass_fail))}</span>
          <span><b>배포 판정</b>${escapeHtml(gateLabel(row.release_gate))}</span>
          <span><b>오류 유형</b>${escapeHtml(labelErrorType(row.error_type))}</span>
        </div>
        <p>${escapeHtml(finalReason)}</p>
      </div>
      ${renderJudgeConflictSummary(row)}
      ${renderJudgeDecisionCards(row)}
    </div>
  `);
}

function shortModelLabel(model) {
  return modelLabelForVersion(model)
    .replace(/^BC\s+/i, "")
    .replace(/\s+Remote$/i, "")
    .replace(/\s+BCGPT\s+/i, " ")
    .slice(0, 34);
}

function resultViewLabel(value) {
  return {
    all: "전체 결과",
    failures: "실패 문항",
    passes: "통과 문항",
    safety: "HAL 이슈",
    different: "모델 간 불일치",
    review: "검토 필요",
  }[value] || "전체 결과";
}

function metricDisplayLabel(key) {
  return metricLabels[key] || key;
}

function renderQuestionlist(caseRows) {
  const source = questionlistSummary?.source ?? {};
  const sourceCounts = countBy(caseRows, "source_type");
  const topicCounts = countBy(caseRows, "qa_matrix_topic");
  const questionTypeCounts = countBy(caseRows, "question_type");
  const selectedTotal = caseRows.length;
  const sourceTotal = Number(source.total ?? 0);

  renderDistribution("questionlistSourceChart", sourceCounts, labelSource);
  renderDistribution("questionlistBehaviorChart", topicCounts, labelTopic);

  const rows = caseRows.slice(0, 40);
  setHtml("caseSetTable", table(
    ["케이스 ID", "대분류", "금융토픽", "질문유형", "질문"],
    rows.map((d) => [
      d.case_id,
      labelSource(d.source_type),
      labelTopic(d.qa_matrix_topic),
      labelQuestionType(d.question_type),
      d.question,
    ])
  ));

  setHtml("sampleQuestions", rows.slice(0, 12).map((d) => `
    <div class="case">
      <strong>${escapeHtml(d.case_id)} · ${escapeHtml(labelSource(d.source_type))}</strong>
      <p>${escapeHtml(d.question)}</p>
      <p><b>근거:</b> ${escapeHtml(d.source_title || d.ground_truth_doc || "")}</p>
    </div>
  `).join("") || emptyState("표시할 questionlist 케이스가 없습니다."));
}

function initializeCaseSetControls() {
  populateDatasetSelects();
  bindDatasetUploadForm();
  const datasetSelect = document.getElementById("datasetSelect");
  const limitInput = document.getElementById("datasetLimit");

  if (datasetSelect) {
    datasetSelect.value = selectedDataset;
    datasetSelect.addEventListener("change", () => {
      selectedDataset = datasetSelect.value;
      const evalDataset = document.getElementById("evalDatasetSelect");
      if (evalDataset) evalDataset.value = selectedDataset;
      loadDatasetCases(selectedDataset);
    });
  }
  if (limitInput) {
    limitInput.addEventListener("change", () => loadDatasetCases(datasetSelect?.value || selectedDataset));
  }
}

function setDatasetUploadMessage(message, type) {
  const target = document.getElementById("datasetUploadMessage");
  setPanelMessage(target, message, type);
}

function bindDatasetUploadForm() {
  const form = document.getElementById("datasetUploadForm");
  if (!form || form.dataset.bound === "true") return;
  form.dataset.bound = "true";
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const fileInput = document.getElementById("datasetUploadFile");
    const nameInput = document.getElementById("datasetUploadName");
    const roleInput = document.getElementById("datasetUploadRole");
    const submitButton = form.querySelector('button[type="submit"]');
    const file = fileInput?.files?.[0];
    if (!file) {
      setDatasetUploadMessage("업로드할 CSV 파일을 선택하세요.", "error");
      return;
    }
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setDatasetUploadMessage("CSV 파일만 추가할 수 있습니다.", "error");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setDatasetUploadMessage("CSV 파일은 5MB 이하로 올려주세요.", "error");
      return;
    }

    if (submitButton) submitButton.disabled = true;
    setDatasetUploadMessage("CSV 테스트셋을 업로드하는 중입니다.", "");
    try {
      const content = await file.text();
      const response = await apiFetch("api/questionlist/datasets/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: file.name,
          name: nameInput?.value || "",
          role: roleInput?.value || "benchmark",
          content,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.error || `업로드 실패 (${response.status})`);
      }

      questionlistDatasets = payload.datasets ?? questionlistDatasets;
      selectedDataset = payload.dataset?.id || preferredDatasetId(selectedDataset);
      populateDatasetSelects();
      const datasetSelect = document.getElementById("datasetSelect");
      const evalDatasetSelect = document.getElementById("evalDatasetSelect");
      if (datasetSelect) datasetSelect.value = selectedDataset;
      if (evalDatasetSelect) evalDatasetSelect.value = selectedDataset;
      await loadDatasetCases(selectedDataset);
      renderEvalProfileCards();
      renderEvalRunSummary();
      setDatasetUploadMessage(`테스트셋 추가 완료: ${datasetLabel(payload.dataset || { id: selectedDataset })}`, "ok");
      form.reset();
    } catch (error) {
      setDatasetUploadMessage(error.message || "테스트셋 업로드에 실패했습니다.", "error");
    } finally {
      if (submitButton) submitButton.disabled = false;
    }
  });
}

function bindRunWithSelectedDatasetButton() {
  const button = document.getElementById("runWithSelectedDataset");
  if (!button || button.dataset.bound === "true") return;
  button.dataset.bound = "true";
  button.addEventListener("click", () => {
    const dataset = document.getElementById("datasetSelect")?.value || selectedDataset;
    const evalDataset = document.getElementById("evalDatasetSelect");
    selectedDataset = dataset;
    if (evalDataset) evalDataset.value = dataset;
    updateEvalRunMode();
    renderEvalProfileCards();
    renderEvalRunSummary();
    activateTab("runEval");
  });
}

function populateDatasetSelects() {
  const datasets = selectableDatasets();
  const options = datasets.map((dataset) => `
    <option value="${escapeHtml(dataset.id)}">${escapeHtml(datasetLabel(dataset))} - ${Number(dataset.total || 0).toLocaleString()}개</option>
  `).join("");
  const resolvedDataset = preferredDatasetId(selectedDataset);
  selectedDataset = resolvedDataset;
  ["datasetSelect", "evalDatasetSelect"].forEach((id) => {
    const element = document.getElementById(id);
    if (!element) return;
    element.innerHTML = options;
    element.value = resolvedDataset;
  });
}

function datasetLabel(dataset) {
  if (dataset.id === "benchmark_final_full") return "벤치마크 - benchmark_dataset_test.csv";
  if (dataset.id === "regression_golden_full") return "회귀 전체 - regression_golden_set.csv";
  return dataset.name || dataset.label || dataset.id;
}

function runProfileLabel(profileId) {
  return runProfileLabels[profileId] || evalCatalog?.profiles?.[profileId]?.label || profileId;
}

function runProfileDescription(profileId) {
  return runProfileHelp[profileId] || evalCatalog?.profiles?.[profileId]?.description || "";
}

function scoringModeLabel(mode) {
  return scoringModeLabels[mode] || mode;
}

function backendScoringMode(mode) {
  return mode === "llm_blended" ? "llm_override" : mode;
}

function syncRunProfileHelp() {
  const profile = document.getElementById("evalRunProfile")?.value || "single_dataset";
  const target = document.getElementById("evalRunProfileHelp");
  if (target) target.textContent = runProfileDescription(profile);
}

function syncTargetSelectionModeHelp() {
  const mode = targetSelectionMode();
  const target = document.getElementById("evalTargetSelectionHelp");
  if (target) target.textContent = targetSelectionModeHelp[mode] || "";
}

function syncScoringModeHelp() {
  const mode = document.getElementById("evalScoringMode")?.value || "static";
  const target = document.getElementById("evalScoringModeHelp");
  if (target) target.textContent = scoringModeHelp[mode] || "";
  const blendTarget = document.getElementById("evalBlendWeightHelp");
  const weight = Number(document.getElementById("evalJudgeBlendWeight")?.value || 0.5);
  if (blendTarget) {
    const llm = Math.round(weight * 100);
    blendTarget.textContent = mode === "blend"
      ? `${weight.toFixed(2)} = Judge ${llm}%, Rule ${100 - llm}%로 최종 점수를 섞습니다.`
      : "Judge+규칙 혼합에서만 사용합니다.";
  }
}

function sortedDatasets() {
  return [...questionlistDatasets].sort((a, b) => datasetRank(a) - datasetRank(b) || String(a.id).localeCompare(String(b.id)));
}

function selectableDatasets() {
  return sortedDatasets().filter((dataset) =>
    dataset.exists !== false &&
    Number(dataset.total || 0) > 0 &&
    !hiddenDatasetIds.has(String(dataset.id || "")) &&
    !datasetHasExcludedMarker(dataset)
  );
}

function datasetRank(dataset) {
  if (dataset.id === "benchmark_final_full") return 0;
  if (dataset.id === "regression_golden_full") return 1;
  if (dataset.auto_discovered) return dataset.role === "benchmark" ? 30 : 40;
  if (dataset.role === "benchmark") return 10;
  if (dataset.role === "regression") return 20;
  return 50;
}

function datasetHasExcludedMarker(dataset) {
  const text = [
    dataset.id,
    dataset.name,
    dataset.label,
    dataset.path,
    dataset.source_directory,
  ].map((value) => String(value || "").toLowerCase()).join(" ");
  if (excludedDatasetMarkers.some((marker) => text.includes(marker))) return true;
  const tokens = text.split(/[^a-z0-9]+/).filter(Boolean);
  return excludedDatasetTokens.some((token) => tokens.includes(token));
}

function preferredDatasetId(currentId = selectedDataset) {
  const datasets = selectableDatasets();
  const ids = new Set(datasets.map((dataset) => dataset.id));
  if (ids.has(currentId)) return currentId;
  return ["benchmark_final_full", "regression_golden_full"].find((id) => ids.has(id))
    || datasets[0]?.id
    || currentId;
}

function preferredDatasetForRun(runId, currentId = selectedDataset) {
  const normalized = String(runId || "").toLowerCase();
  if (normalized.startsWith("regression")) return preferredDatasetId("regression_golden_full");
  if (normalized.startsWith("benchmark")) return preferredDatasetId("benchmark_final_full");
  return preferredDatasetId(currentId);
}

function preferredRunProfileId(profileIds) {
  const preferred = selectedRunId && String(selectedRunId).startsWith("regression")
    ? ["regression_golden_full", "benchmark_final_full"]
    : ["benchmark_final_full", "regression_golden_full"];
  return preferred.find((id) => profileIds.has(id))
    || [...profileIds].find((id) => id !== "custom_seeded_mix")
    || "single_dataset";
}

function populateRunProfileSelect() {
  const select = document.getElementById("evalRunProfile");
  if (!select) return;
  const profiles = Object.entries(evalCatalog?.profiles || {}).sort(([a], [b]) => profileRank(a) - profileRank(b) || a.localeCompare(b));
  const profileIds = new Set(profiles.map(([id]) => id));
  const hasCatalogCustomProfile = profileIds.has("custom_seeded_mix");
  select.innerHTML = [
    `<option value="single_dataset">${escapeHtml(runProfileLabel("single_dataset"))}</option>`,
    ...profiles.map(([id]) => `<option value="${escapeHtml(id)}">${escapeHtml(runProfileLabel(id))}</option>`),
    ...(hasCatalogCustomProfile ? [] : [`<option value="custom_seeded_mix">${escapeHtml(runProfileLabel("custom_seeded_mix"))}</option>`]),
  ].join("");
  select.value = preferredRunProfileId(profileIds);
  syncRunProfileHelp();
}

function profileRank(profileId) {
  return {
    benchmark_final_full: 0,
    regression_golden_full: 1,
  }[profileId] ?? 50;
}

function renderEvalProfileCards() {
  const target = document.getElementById("evalProfileCards");
  if (!target) return;
  const current = document.getElementById("evalRunProfile")?.value || "single_dataset";
  const selectedCaseFile = document.getElementById("evalDatasetSelect")?.value || selectedDataset;
  const selectedCaseTotal = datasetTotalById(selectedCaseFile);
  const profiles = Object.entries(evalCatalog?.profiles || {})
    .filter(([id]) => id !== "custom_seeded_mix")
    .sort(([a], [b]) => profileRank(a) - profileRank(b) || a.localeCompare(b));
  const cards = [
    {
      id: "single_dataset",
      description: runProfileDescription("single_dataset"),
      meta: selectedCaseTotal ? `${selectedCaseTotal.toLocaleString()}개 케이스` : "선택 파일 기준",
    },
    ...profiles.map(([id, profile]) => {
      const pools = Object.entries(profile.pools || {});
      const total = pools.reduce((sum, [, quota]) => sum + Number(quota || 0), 0);
      return {
        id,
        description: runProfileDescription(id),
        meta: total ? `${Number(total).toLocaleString()}개 케이스` : "profile 기본값",
      };
    }),
    {
      id: "custom_seeded_mix",
      description: runProfileDescription("custom_seeded_mix"),
      meta: customPoolPlanLabel(),
    },
  ];
  target.innerHTML = cards.map(({ id, description, meta }) => {
    return `
      <button type="button" class="profile-card ${id === current ? "selected" : ""}" data-run-profile-card="${escapeHtml(id)}">
        <strong>${escapeHtml(runProfileLabel(id))}</strong>
        <span>${escapeHtml(shortLabel(description, 68))}</span>
        <em>${escapeHtml(meta)}</em>
      </button>
    `;
  }).join("");
}

function defaultCustomPoolTotal() {
  const customTotal = document.getElementById("evalCustomTotal");
  if (customTotal) {
    const explicit = Number(customTotal.value);
    return Number.isFinite(explicit) ? Math.floor(explicit) : 0;
  }
  const limit = Number(document.getElementById("evalLimit")?.value || 0);
  if (Number.isFinite(limit) && limit > 0) return Math.floor(limit);
  return 20;
}

function customRandomSeed() {
  const raw = document.getElementById("evalRandomSeed")?.value ?? evalCatalog.default_seed ?? 42;
  const seed = Number(raw === "" ? evalCatalog.default_seed ?? 42 : raw);
  return Number.isInteger(seed) && seed >= 0 ? seed : null;
}

function customPoolWeightEntries() {
  return [...document.querySelectorAll("[data-pool-weight]")]
    .map((input) => ({
      poolId: input.dataset.poolWeight,
      weight: Number(input.value || 0),
    }))
    .filter((entry) => entry.poolId && Number.isFinite(entry.weight) && entry.weight > 0);
}

function poolQuotasFromWeights(entries, total) {
  const positive = entries.filter((entry) => entry.weight > 0);
  if (!positive.length || total <= 0) return {};
  const weightTotal = positive.reduce((sum, entry) => sum + entry.weight, 0);
  const exact = positive.map((entry, index) => {
    const raw = (entry.weight / weightTotal) * total;
    const quota = Math.floor(raw);
    return {
      ...entry,
      index,
      quota,
      remainder: raw - quota,
    };
  });
  let allocated = exact.reduce((sum, entry) => sum + entry.quota, 0);
  [...exact]
    .sort((a, b) => b.remainder - a.remainder || b.weight - a.weight || a.index - b.index)
    .forEach((entry) => {
      if (allocated >= total) return;
      entry.quota += 1;
      allocated += 1;
    });
  return Object.fromEntries(exact.filter((entry) => entry.quota > 0).map((entry) => [entry.poolId, entry.quota]));
}

function customPoolPlan() {
  const total = defaultCustomPoolTotal();
  const seed = customRandomSeed();
  const weights = customPoolWeightEntries();
  return {
    total,
    seed,
    weights,
    quotas: poolQuotasFromWeights(weights, total),
  };
}

function customPoolPlanLabel() {
  const plan = customPoolPlan();
  const quotaTotal = Object.values(plan.quotas).reduce((sum, value) => sum + Number(value || 0), 0);
  if (!quotaTotal) return "총 샘플 수와 풀별 비율 입력";
  return `${quotaTotal.toLocaleString()}개 · seed ${plan.seed ?? "?"}`;
}

function renderCustomPoolInputs() {
  const target = document.getElementById("evalCustomPools");
  if (!target) return;
  const profile = document.getElementById("evalRunProfile")?.value || "single_dataset";
  if (profile !== "custom_seeded_mix") {
    target.innerHTML = "";
    return;
  }
  const pools = Object.entries(evalCatalog?.pools || {});
  target.innerHTML = `
    <h3>직접 구성</h3>
    <div class="custom-pool-controls">
      <label>
        <span>총 샘플 수</span>
        <input id="evalCustomTotal" type="number" min="1" max="100000" step="1" value="${escapeHtml(String(defaultCustomPoolTotal()))}">
      </label>
      <label>
        <span>랜덤 시드</span>
        <input id="evalRandomSeed" type="number" min="0" max="2147483647" step="1" value="${escapeHtml(String(evalCatalog.default_seed ?? 42))}">
      </label>
      <span id="customPoolPlanSummary" class="custom-pool-summary"></span>
    </div>
    <div class="pool-grid">
      ${pools.map(([poolId, pool]) => `
        <label>
          <span>${escapeHtml(pool.label || poolId)} · ${escapeHtml(pool.role || "")}</span>
          <input data-pool-weight="${escapeHtml(poolId)}" type="number" min="0" max="100000" step="0.1" value="1" placeholder="0이면 제외">
          <small>비율 입력 · 최대 ${Number(pool.default_quota || 0).toLocaleString()}개</small>
        </label>
      `).join("")}
    </div>
  `;
  const refresh = () => {
    const summary = document.getElementById("customPoolPlanSummary");
    const plan = customPoolPlan();
    const quotaEntries = Object.entries(plan.quotas);
    const quotaText = quotaEntries.map(([poolId, quota]) => `${poolId} ${quota}`).join(" / ");
    if (summary) {
      summary.textContent = quotaEntries.length
        ? `생성 예정: ${quotaEntries.reduce((sum, [, quota]) => sum + Number(quota || 0), 0).toLocaleString()}개 · ${quotaText}`
        : "비율이 0보다 큰 풀을 하나 이상 입력하세요.";
    }
    renderEvalProfileCards();
    renderEvalRunSummary();
  };
  target.querySelectorAll("#evalCustomTotal, #evalRandomSeed, [data-pool-weight]").forEach((input) => {
    input.addEventListener("input", refresh);
    input.addEventListener("change", refresh);
  });
  refresh();
}

function updateEvalRunMode() {
  const profile = document.getElementById("evalRunProfile")?.value || "single_dataset";
  const isProfileRun = profile !== "single_dataset";
  const isCustomRun = profile === "custom_seeded_mix";
  const datasetSelect = document.getElementById("evalDatasetSelect");
  const limit = document.getElementById("evalLimit");
  const selectedCaseFile = datasetSelect?.value || selectedDataset;
  const predictionFile = document.getElementById("evalPredictionFile");
  const configCard = document.querySelector(".benchmark-config-card");
  if (datasetSelect) {
    datasetSelect.disabled = isProfileRun;
    const label = datasetSelect.closest("label");
    if (label) label.hidden = isProfileRun;
  }
  if (predictionFile) {
    const label = predictionFile.closest("label");
    if (label) label.hidden = isProfileRun || !String(selectedCaseFile).startsWith("tool_agent");
  }
  configCard?.classList.toggle("profile-run", isProfileRun);
  if (limit) {
    const label = limit.closest("label");
    if (label) label.hidden = isCustomRun;
    limit.placeholder = isProfileRun ? "profile 기본값 사용" : "예: 10";
  }
  renderEvalRunSummary();
}

async function loadDatasetCases(datasetId) {
  if (!datasetId) return;
  selectedDataset = datasetId;
  const limit = Number(document.getElementById("datasetLimit")?.value || 120);
  const datasetSummary = questionlistDatasets.find((dataset) => dataset.id === datasetId) ?? {};
  const sourceTotal = Number(datasetSummary.total || 0);
  const fetchLimit = Math.min(1000, Math.max(limit, sourceTotal || limit));
  setHtml("datasetCaseTable", emptyState("케이스 미리보기를 불러오는 중입니다."));
  const payload = await fetchJsonOptional(
    `api/questionlist/dataset-cases?dataset=${encodeURIComponent(datasetId)}&limit=${encodeURIComponent(fetchLimit)}`,
    { cases: [] }
  );
  datasetCases = (payload?.cases ?? []).map(normalizeQuestionlistCase);
  if (!state.selectedDatasetCaseId || !datasetCases.some((row) => row.case_id === state.selectedDatasetCaseId)) {
    state.selectedDatasetCaseId = datasetCases[0]?.case_id ?? null;
  }
  renderCaseSets();
}

function renderCaseSets() {
  renderDatasetCaseTable();
  renderDatasetDetails();
}

function renderDatasetCaseTable() {
  if (!datasetCases.length) {
    setHtml("datasetCaseTable", emptyState("불러온 미리보기 케이스가 없습니다."));
    return;
  }
  const displayLimit = Math.max(1, Math.min(Number(document.getElementById("datasetLimit")?.value || 120), datasetCases.length));
  const rows = previewDatasetRows(datasetCases, displayLimit);
  const typeCounts = countBy(datasetCases, "question_type");
  const topicCounts = countBy(datasetCases, "qa_matrix_topic");

  setHtml("datasetCaseTable", `
    <div class="dataset-preview-meta">
      <span>전체 ${datasetCases.length.toLocaleString()}개 중 ${rows.length.toLocaleString()}개 표시</span>
      <span>질문유형 ${Object.entries(typeCounts).map(([key, count]) => `${labelTaskType(key)} ${count}`).join(" / ")}</span>
      <span>금융토픽 ${Object.entries(topicCounts).slice(0, 6).map(([key, count]) => `${labelTopic(key)} ${count}`).join(" / ")}</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>케이스 ID</th>
            <th>대분류</th>
            <th>금융토픽</th>
            <th>질문유형</th>
            <th>질문</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((row) => `
            <tr class="${row.case_id === state.selectedDatasetCaseId ? "selected-row" : ""}">
              <td><button class="link-button dataset-case-button" type="button" data-dataset-case="${escapeHtml(row.case_id)}" title="${escapeHtml(row.case_id)}">${escapeHtml(row.case_id)}</button></td>
              <td>${escapeHtml(labelSource(row.source_type))}</td>
              <td>${escapeHtml(labelTopic(row.qa_matrix_topic))}</td>
              <td>${escapeHtml(labelQuestionType(row.question_type))}</td>
              <td title="${escapeHtml(row.question)}">${escapeHtml(shortLabel(row.question, 130))}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `);

  document.querySelectorAll("[data-dataset-case]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedDatasetCaseId = button.dataset.datasetCase;
      renderDatasetCaseTable();
      renderDatasetDetails();
      document.getElementById("datasetCaseDetails")?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    });
  });
}

function previewDatasetRows(rows, limit) {
  if (rows.length <= limit) return rows;
  const groups = new Map();
  rows.forEach((row) => {
    const key = row.question_type || "unknown";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(row);
  });
  if (groups.size <= 1) return rows.slice(0, limit);

  const selected = [];
  const groupRows = [...groups.values()];
  let cursor = 0;
  while (selected.length < limit && groupRows.some((items) => cursor < items.length)) {
    for (const items of groupRows) {
      if (selected.length >= limit) break;
      if (cursor < items.length) selected.push(items[cursor]);
    }
    cursor += 1;
  }
  return selected;
}

function renderDatasetDetails() {
  const row = datasetCases.find((item) => item.case_id === state.selectedDatasetCaseId) ?? datasetCases[0];
  if (!row) {
    setHtml("datasetCaseDetails", emptyState("기대값을 확인할 케이스를 선택하세요."));
    return;
  }

  setHtml("datasetCaseDetails", `
    <div class="detail-stack">
      ${detailBlock("질문", row.question)}
      ${detailBlock("반드시 포함", expectationListValue(row.must_include || row.required_claims))}
      ${detailBlock("포함 금지", expectationListValue(row.must_not_include || row.forbidden_claims))}
      ${detailBlock("모범답안", row.gold_excerpt || row.output || row.ground_truth || row.ground_truth_doc || "등록된 모범답안이 없습니다.")}
    </div>
  `);
}

function initializeEvalRunControls() {
  populateDatasetSelects();
  populateRunProfileSelect();
  renderEvalProfileCards();
  renderCustomPoolInputs();
  renderEvalConfigFilters();
  updateEvalRunMode();
  const runProfile = document.getElementById("evalRunProfile");
  if (runProfile) {
    runProfile.addEventListener("change", () => {
      renderCustomPoolInputs();
      updateEvalRunMode();
      renderEvalProfileCards();
      syncRunProfileHelp();
    });
  }
  const evalDataset = document.getElementById("evalDatasetSelect");
  if (evalDataset) {
    evalDataset.addEventListener("change", () => {
      selectedDataset = evalDataset.value;
      const datasetSelect = document.getElementById("datasetSelect");
      if (datasetSelect) datasetSelect.value = selectedDataset;
      updateEvalRunMode();
      renderEvalProfileCards();
      loadDatasetCases(selectedDataset);
    });
  }
  document.getElementById("evalTargetSelectionMode")?.addEventListener("change", () => {
    enforceTargetSelectionMode();
    syncTargetSelectionModeHelp();
    renderEvalConfigFilters();
    renderEvalRunSummary();
  });
  initializeJudgeControls();
  initializeStaticEmbeddingControls();
  const form = document.getElementById("evalRunForm");
  if (!form) return;
  const inlineSubmit = form.querySelector('button[type="submit"]');
  if (inlineSubmit) {
    inlineSubmit.classList.add("run-submit", "secondary-run-submit");
    inlineSubmit.innerHTML = "<span>2단계: 채점 포함 실행</span><small>현재 설정으로 평가까지 실행</small>";
  }
  ["evalLimit", "evalDryRun", "evalAnswerCacheEnabled", "evalExportFinalUi"].forEach((id) => {
    document.getElementById(id)?.addEventListener("change", renderEvalRunSummary);
  });
  document.getElementById("evalScoringMode")?.addEventListener("change", () => {
    syncScoringModeHelp();
    enforceJudgeSelectionForScoringMode();
    syncJudgeAggregationControls();
    renderJudgeWeightInputs();
    renderEvalRunSummary();
  });
  document.getElementById("evalJudgeAggregationMethod")?.addEventListener("change", () => {
    syncJudgeAggregationControls();
    renderJudgeWeightInputs();
    renderEvalRunSummary();
  });
  document.getElementById("evalJudgeBlendWeight")?.addEventListener("input", () => {
    syncScoringModeHelp();
    renderEvalRunSummary();
  });
  ["evalStaticEmbeddingModel"].forEach((id) => {
    document.getElementById(id)?.addEventListener("input", updateRunSubmitState);
  });
  document.getElementById("evalConfigFilters")?.addEventListener("change", (event) => {
    if (event.target?.matches("[data-eval-config]")) {
      if (event.target.checked) state.runConfigVersions.add(event.target.value);
      else state.runConfigVersions.delete(event.target.value);
      enforceTargetSelectionMode(event.target.value);
      event.target.closest(".model-card")?.classList.toggle("selected", event.target.checked);
      renderSelectedModelSummary();
      renderJudgeRegistry();
    }
    renderEvalRunSummary();
  });
  document.getElementById("evalJudgeConfigId")?.addEventListener("change", (event) => {
    if (event.target?.matches("[data-judge-config]") && event.target.checked) {
      enforceJudgeSelectionForScoringMode(event.target.value);
    }
    syncJudgeAggregationControls();
    renderJudgeWeightInputs();
    renderEvalRunSummary();
  });
  document.getElementById("evalProfileCards")?.addEventListener("click", (event) => {
    const card = event.target.closest("[data-run-profile-card]");
    if (!card) return;
    const select = document.getElementById("evalRunProfile");
    if (!select) return;
    select.value = card.dataset.runProfileCard;
    renderCustomPoolInputs();
    updateEvalRunMode();
    renderEvalProfileCards();
    syncRunProfileHelp();
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await startEvalRun();
  });
  const runButton = document.getElementById("evalRunSubmit");
  if (runButton) {
    runButton.onclick = () => startEvalRun();
  }
  const answerOnlyButton = document.getElementById("answerOnlyRunSubmit");
  if (answerOnlyButton) {
    answerOnlyButton.onclick = () => startEvalRun({ answerOnly: true });
  }
  syncRunProfileHelp();
  syncTargetSelectionModeHelp();
  syncScoringModeHelp();
  renderEvalRunSummary();
}

function initializeReblendControls() {
  const form = document.getElementById("evalReblendForm");
  const button = document.getElementById("evalReblendSubmit");
  if (!form || !button) return;
  renderReblendRunSelector();
  const scoringMode = document.getElementById("reblendScoringMode");
  const weight = document.getElementById("reblendWeight");
  const syncWeightState = () => {
    if (!weight || !scoringMode) return;
    weight.disabled = scoringMode.value !== "blend";
  };
  scoringMode?.addEventListener("change", syncWeightState);
  syncWeightState();
  button.addEventListener("click", () => submitReblendRun());
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    submitReblendRun();
  });
}

async function submitReblendRun() {
  const button = document.getElementById("evalReblendSubmit");
  const sourceRunId = document.getElementById("reblendSourceRunId")?.value || "";
  const selectedScoringMode = document.getElementById("reblendScoringMode")?.value || "blend";
  const scoringMode = backendScoringMode(selectedScoringMode);
  const blendWeight = Number(document.getElementById("reblendWeight")?.value || 0.5);
  const exportFinalUi = Boolean(document.getElementById("reblendExportFinalUi")?.checked);
  if (scoringMode === "blend" && (Number.isNaN(blendWeight) || blendWeight < 0 || blendWeight > 1)) {
    setEvalReblendMessage("규칙/LLM 혼합 비율은 0과 1 사이여야 합니다.", "error");
    return;
  }
  const previousText = button?.innerHTML || "";
  if (button) {
    button.disabled = true;
    button.innerHTML = "<span>재계산 중...</span><small>기존 결과를 새 run으로 작성</small>";
  }
  setEvalReblendMessage("기존 실행 점수를 재계산하는 중...", "");
  try {
    const response = await apiFetch("api/eval/reblend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_run_id: sourceRunId,
        scoring_mode: scoringMode,
        blend_weight: blendWeight,
        export_final_ui: exportFinalUi,
      }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    setEvalReblendMessage(`재계산 결과 생성: ${payload.run_id}. Export를 켰으면 새로고침하면 반영됩니다.`, "ok");
  } catch (error) {
    setEvalReblendMessage(`재계산 실패: ${error.message}`, "error");
  } finally {
    if (button) {
      button.disabled = false;
      button.innerHTML = previousText;
    }
  }
}

function judgeScoreGapModeLabel(mode) {
  return mode === "relative_percent" ? "상대 차이" : "절대 점수차";
}

function judgeScoreGapThresholdLabel(threshold, mode) {
  const number = Number(threshold);
  if (!Number.isFinite(number)) return "-";
  return mode === "relative_percent" ? `${number}%+` : `${number}점+`;
}

function initializeJudgeComparisonControls() {
  renderJudgeComparisonControls();
  document.getElementById("judgeCompareBaselineSource")?.addEventListener("change", () => {
    renderJudgeComparisonBaselineJudgeOptions();
    renderJudgeComparisonArbiterOptions();
    renderJudgeComparisonPreview();
  });
  document.getElementById("judgeCompareBaselineJudge")?.addEventListener("change", () => {
    renderJudgeComparisonArbiterOptions();
    renderJudgeComparisonPreview();
  });
  ["judgeCompareExistingArbiter", "judgeCompareCandidateRun", "judgeCompareScoreGap", "judgeCompareScoreGapMode", "judgeCompareErrorType", "judgeCompareNormalizeErrorType"].forEach((id) => {
    document.getElementById(id)?.addEventListener("change", renderJudgeComparisonPreview);
    document.getElementById(id)?.addEventListener("input", renderJudgeComparisonPreview);
  });
  document.getElementById("judgeComparisonSubmit")?.addEventListener("click", () => submitJudgeComparison());
}

function renderJudgeComparisonControls() {
  const sourceSelect = document.getElementById("judgeCompareBaselineSource");
  const candidateSelect = document.getElementById("judgeCompareCandidateRun");
  if (!sourceSelect || !candidateSelect) return;
  const sources = judgeComparisonOptions?.baseline_sources || [];
  const candidateRuns = judgeComparisonOptions?.judge_runs || [];
  const preferredSource = sources.find((source) => source.source_id === selectedRunId)
    || sources.find((source) => source.selected)
    || sources[0];
  sourceSelect.innerHTML = sources.map((source) => `
    <option value="${escapeHtml(source.source_id)}" ${source.source_id === preferredSource?.source_id ? "selected" : ""}>
      ${escapeHtml(source.label || source.source_id)} · Judge ${Number(source.judge_configs?.length || 0)}
    </option>
  `).join("");
  const geminiCandidates = candidateRuns.filter((run) => String(run.run_id || "").toLowerCase().includes("gemini"));
  const preferredCandidate = [...(geminiCandidates.length ? geminiCandidates : candidateRuns)]
    .sort((left, right) => Number(right.ok_rows || 0) - Number(left.ok_rows || 0))[0];
  candidateSelect.innerHTML = candidateRuns.map((run) => {
    const judgeLabel = (run.judge_configs || []).map((item) => item.config_id).filter(Boolean).slice(0, 2).join(", ");
    return `
      <option value="${escapeHtml(run.run_id)}" ${run.run_id === preferredCandidate?.run_id ? "selected" : ""}>
        ${escapeHtml(run.label || run.run_id)} · ok ${Number(run.ok_rows || 0).toLocaleString()}${judgeLabel ? ` · ${escapeHtml(judgeLabel)}` : ""}
      </option>
    `;
  }).join("");
  renderJudgeComparisonBaselineJudgeOptions();
  renderJudgeComparisonArbiterOptions();
  renderJudgeComparisonPreview();
}

function renderJudgeComparisonBaselineJudgeOptions() {
  const sourceId = document.getElementById("judgeCompareBaselineSource")?.value || "";
  const judgeSelect = document.getElementById("judgeCompareBaselineJudge");
  if (!judgeSelect) return;
  const source = (judgeComparisonOptions?.baseline_sources || []).find((item) => item.source_id === sourceId)
    || (judgeComparisonOptions?.baseline_sources || [])[0];
  const judges = source?.judge_configs || [];
  const preferred = judges.find((judge) => String(judge.config_id || "").includes("gpt54"))
    || judges.find((judge) => String(judge.config_id || "").includes("openai"))
    || judges[0];
  judgeSelect.innerHTML = judges.map((judge) => `
    <option value="${escapeHtml(judge.config_id)}" ${judge.config_id === preferred?.config_id ? "selected" : ""}>
      ${escapeHtml(judge.config_id)} · ${Number(judge.rows || 0).toLocaleString()} rows
    </option>
  `).join("");
}

function renderJudgeComparisonArbiterOptions() {
  const sourceId = document.getElementById("judgeCompareBaselineSource")?.value || "";
  const baselineJudgeId = document.getElementById("judgeCompareBaselineJudge")?.value || "";
  const arbiterSelect = document.getElementById("judgeCompareExistingArbiter");
  if (!arbiterSelect) return;
  const source = (judgeComparisonOptions?.baseline_sources || []).find((item) => item.source_id === sourceId)
    || (judgeComparisonOptions?.baseline_sources || [])[0];
  const judges = (source?.judge_configs || []).filter((judge) => judge.config_id && judge.config_id !== baselineJudgeId);
  const preferred = judges.find((judge) => String(judge.config_id || "").toLowerCase().includes("gpt55"))
    || judges.find((judge) => String(judge.config_id || "").toLowerCase().includes("arbiter"))
    || null;
  arbiterSelect.innerHTML = [
    `<option value="">사용 안 함 · 기존 Arbiter 결과 없음</option>`,
    ...judges.map((judge) => `
      <option value="${escapeHtml(judge.config_id)}" ${judge.config_id === preferred?.config_id ? "selected" : ""}>
        ${escapeHtml(judge.config_id)} · ${Number(judge.rows || 0).toLocaleString()} rows
      </option>
    `),
  ].join("");
}

function renderJudgeComparisonPreview() {
  const result = document.getElementById("judgeComparisonResult");
  if (!result) return;
  const sources = judgeComparisonOptions?.baseline_sources || [];
  const candidateRuns = judgeComparisonOptions?.judge_runs || [];
  const source = sources.find((item) => item.source_id === document.getElementById("judgeCompareBaselineSource")?.value);
  const judgeId = document.getElementById("judgeCompareBaselineJudge")?.value || "";
  const arbiterId = document.getElementById("judgeCompareExistingArbiter")?.value || "";
  const candidate = candidateRuns.find((item) => item.run_id === document.getElementById("judgeCompareCandidateRun")?.value);
  const scoreGapThreshold = Number(document.getElementById("judgeCompareScoreGap")?.value || 30);
  const scoreGapMode = document.getElementById("judgeCompareScoreGapMode")?.value || "points";
  const includeErrorTypeMismatch = Boolean(document.getElementById("judgeCompareErrorType")?.checked);
  if (!sources.length || !candidateRuns.length) {
    result.innerHTML = emptyState("비교 가능한 기존 Judge 점수 또는 새 Judge run이 없습니다.");
    return;
  }
  result.innerHTML = `
    <div class="judge-comparison-preview">
      <span><strong>기준</strong>${escapeHtml(source?.label || "-")}</span>
      <span><strong>Judge</strong>${escapeHtml(judgeId || "-")}</span>
      <span><strong>기존 Arbiter</strong>${escapeHtml(arbiterId || "사용 안 함")}</span>
      <span><strong>비교 run</strong>${escapeHtml(candidate?.label || "-")}</span>
      <span><strong>비교 rows</strong>${Number(candidate?.ok_rows || 0).toLocaleString()}</span>
      <span><strong>후보 기준</strong>${escapeHtml(judgeScoreGapModeLabel(scoreGapMode))} ${escapeHtml(judgeScoreGapThresholdLabel(scoreGapThreshold, scoreGapMode))} · pass/fail${includeErrorTypeMismatch ? " · fail 유형" : ""}</span>
    </div>
  `;
}

function setJudgeComparisonMessage(message, type = "") {
  const target = document.getElementById("judgeComparisonMessage");
  if (!target) return;
  target.textContent = message;
  target.className = `form-message ${type || ""}`.trim();
}

async function submitJudgeComparison() {
  const button = document.getElementById("judgeComparisonSubmit");
  const previous = button?.innerHTML || "";
  const baselineSourceId = document.getElementById("judgeCompareBaselineSource")?.value || "";
  const baselineJudgeConfigId = document.getElementById("judgeCompareBaselineJudge")?.value || "";
  const arbiterJudgeConfigId = document.getElementById("judgeCompareExistingArbiter")?.value || "";
  const candidateRunId = document.getElementById("judgeCompareCandidateRun")?.value || "";
  const scoreGapThreshold = Number(document.getElementById("judgeCompareScoreGap")?.value || 30);
  const scoreGapMode = document.getElementById("judgeCompareScoreGapMode")?.value || "points";
  const includeErrorTypeMismatch = Boolean(document.getElementById("judgeCompareErrorType")?.checked);
  const normalizeErrorType = Boolean(document.getElementById("judgeCompareNormalizeErrorType")?.checked);
  if (!baselineSourceId || !baselineJudgeConfigId || !candidateRunId) {
    setJudgeComparisonMessage("기준 점수 소스, 기준 Judge, 비교 Judge run을 모두 선택하세요.", "error");
    return;
  }
  if (!Number.isFinite(scoreGapThreshold) || scoreGapThreshold < 0 || scoreGapThreshold > 10000) {
    setJudgeComparisonMessage("점수 차이 기준은 0~10000 사이 숫자여야 합니다.", "error");
    return;
  }
  if (button) {
    button.disabled = true;
    button.innerHTML = "<span>리포트 생성 중...</span><small>점수 차이와 후보 행 계산</small>";
  }
  setJudgeComparisonMessage("Judge 결과 비교 리포트를 생성하는 중...", "");
  try {
    const response = await apiFetch("api/eval/judge-comparison", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        baseline_source_id: baselineSourceId,
        baseline_judge_config_id: baselineJudgeConfigId,
        arbiter_judge_config_id: arbiterJudgeConfigId,
        candidate_run_id: candidateRunId,
        score_gap_threshold: scoreGapThreshold,
        score_gap_mode: scoreGapMode,
        include_error_type_mismatch: includeErrorTypeMismatch,
        normalize_error_type: normalizeErrorType,
      }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    setJudgeComparisonMessage("비교 리포트 생성 완료", "ok");
    renderJudgeComparisonResult(payload);
  } catch (error) {
    setJudgeComparisonMessage(`비교 리포트 생성 실패: ${error.message}`, "error");
  } finally {
    if (button) {
      button.disabled = false;
      button.innerHTML = previous;
    }
  }
}

function renderJudgeComparisonResult(payload) {
  const target = document.getElementById("judgeComparisonResult");
  if (!target) return;
  const summary = payload?.summary || {};
  const artifacts = payload?.artifacts || {};
  const link = (key, label) => {
    const item = artifacts[key];
    if (!item?.url) return "";
    return `<a class="link-button" href="${escapeHtml(item.url)}" target="_blank" rel="noreferrer">${escapeHtml(label)}</a>`;
  };
  const threshold = Number(summary.score_gap_threshold ?? 30);
  const scoreGapMode = summary.score_gap_mode || "points";
  const thresholdLabel = judgeScoreGapThresholdLabel(threshold, scoreGapMode);
  const thresholdModeLabel = judgeScoreGapModeLabel(scoreGapMode);
  target.innerHTML = `
    <div class="judge-comparison-output">
      <div class="run-summary-strip">
        <span><strong>비교 행</strong> ${Number(summary.matched_rows || 0).toLocaleString()}</span>
        <span><strong>평균 차이</strong> ${signedNumber(summary.avg_delta_candidate_minus_baseline)}</span>
        <span><strong>평균 절대차</strong> ${scoreValueLabel(summary.avg_abs_gap)}</span>
        <span><strong>${escapeHtml(thresholdModeLabel)} ${escapeHtml(thresholdLabel)}</strong> ${Number(summary.gap_threshold_rows || 0).toLocaleString()}</span>
        <span><strong>Pass 불일치</strong> ${Number(summary.pass_mismatch_rows || 0).toLocaleString()}</span>
        <span><strong>Fail 유형 불일치</strong> ${Number(summary.error_type_total_mismatch_rows || summary.error_type_mismatch_rows || 0).toLocaleString()}</span>
        <span><strong>Arbiter 대상</strong> ${Number(summary.arbiter_candidate_rows || summary.arbiter_key_rows || 0).toLocaleString()}</span>
        <span><strong>기존 Arbiter 반영</strong> ${Number(summary.arbiter_existing_candidate_rows || 0).toLocaleString()}</span>
        <span><strong>Arbiter 미싱</strong> ${Number(summary.arbiter_missing_rows || summary.arbiter_key_rows || 0).toLocaleString()}</span>
        <span><strong>최종값 완료</strong> ${Number(summary.final_complete_rows || 0).toLocaleString()}</span>
        <span><strong>최종값 평균</strong> ${scoreValueLabel(summary.final_avg)}</span>
      </div>
      <div class="judge-comparison-links">
        ${link("report_md", "리포트 열기")}
        ${link("top_cases_csv", "상위 케이스 CSV")}
        ${link("comparison_csv", "전체 비교 CSV")}
        ${link("arbiter_keys_jsonl", "미완료 Arbiter JSONL")}
      </div>
      <p class="field-help">새 Arbiter는 실행하지 않았습니다. 기존 결과가 없는 후보만 후속 실행 입력으로 남깁니다.</p>
    </div>
  `;
}

function signedNumber(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  return `${number >= 0 ? "+" : ""}${number.toFixed(2)}`;
}

function initializeStaticEmbeddingControls() {
  const enabled = document.getElementById("evalStaticEmbeddingEnabled");
  const model = document.getElementById("evalStaticEmbeddingModel");
  const baseUrl = document.getElementById("evalStaticEmbeddingBaseUrl");
  const sync = () => {
    const isEnabled = Boolean(enabled?.checked);
    [model, baseUrl].filter(Boolean).forEach((element) => {
      const label = element.closest("label");
      element.disabled = !isEnabled;
      if (label) {
        label.hidden = !isEnabled;
        label.classList.toggle("is-disabled", !isEnabled);
      }
    });
    renderEvalRunSummary();
  };
  enabled?.addEventListener("change", sync);
  [model, baseUrl].filter(Boolean).forEach((element) => {
    element.addEventListener("input", renderEvalRunSummary);
  });
  sync();
}

function initializeJudgeControls() {
  const registeredJudge = document.getElementById("evalJudgeConfigId");
  const scoringMode = document.getElementById("evalScoringMode");
  const refresh = () => {
    updateJudgePlaceholders();
    syncJudgeAggregationControls();
    renderJudgeWeightInputs();
    renderEvalRunSummary();
    updateHeaderJudgeStatus();
  };
  if (registeredJudge) {
    registeredJudge.addEventListener("change", refresh);
  }
  if (scoringMode) {
    scoringMode.addEventListener("change", refresh);
  }
  ["evalJudgeBlendWeight"].forEach((id) => {
    document.getElementById(id)?.addEventListener("input", () => {
      renderEvalRunSummary();
      updateHeaderJudgeStatus();
    });
  });
  document.getElementById("equalizeJudgeWeights")?.addEventListener("click", () => {
    renderJudgeWeightInputs({ forceEqual: true });
    renderEvalRunSummary();
    updateRunSubmitState();
  });
  updateJudgePlaceholders();
  syncJudgeAggregationControls();
  renderJudgeWeightInputs();
}

function updateJudgePlaceholders() {
  const scoringMode = document.getElementById("evalScoringMode")?.value || "static";
  const registeredJudge = document.getElementById("evalJudgeConfigId");
  const blend = document.getElementById("evalJudgeBlendWeight");
  const showJudgeControls = scoringMode !== "static";
  const fieldShell = (element) => element?.closest("label, .field-block");
  const setShellHidden = (element, hidden) => {
    const shell = fieldShell(element);
    if (!shell) return;
    shell.hidden = hidden;
    shell.classList.toggle("field-hidden", hidden);
  };
  if (fieldShell(blend)) {
    fieldShell(blend).hidden = !showJudgeControls || scoringMode !== "blend";
    fieldShell(blend).classList.toggle("field-hidden", fieldShell(blend).hidden);
  }
  setShellHidden(registeredJudge, !showJudgeControls);
  if (registeredJudge) {
    renderJudgeRegistry();
  }
  if (blend) {
    blend.disabled = scoringMode !== "blend";
  }
  updateHeaderJudgeStatus();
}

function renderEvalConfigFilters() {
  const target = document.getElementById("evalConfigFilters");
  if (!target) return;
  ensureModelPickerShell(target);
  enforceTargetSelectionMode();
  const ids = evalTargetRegistryIds();
  const mode = targetSelectionMode();
  const inputType = multiTargetSelectionMode(mode) ? "checkbox" : "radio";
  const inputName = multiTargetSelectionMode(mode) ? "" : ' name="eval_config"';
  target.innerHTML = ids.map((id) => {
    const spec = modelSpecForVersion(id);
    const selected = state.runConfigVersions.has(id);
    const provider = spec.provider || "history";
    const role = spec.candidate_role || "target";
    const model = spec.model || id;
    const endpoint = modelEndpointLabel(spec);
    const temp = spec.options?.temperature;
    const topP = spec.options?.top_p;
    const promptVersion = spec.prompt_version || spec.experiment_tag || "prompt_v1";
    const variantLabel = spec.prompt_variant_of ? `variant of ${spec.prompt_variant_of}` : "base";
    return `
      <label class="model-card ${selected ? "selected" : ""}">
        <input type="${inputType}"${inputName} data-eval-config value="${escapeHtml(id)}" ${selected ? "checked" : ""}>
        <span class="model-card-top">
          <strong>${escapeHtml(modelLabelForVersion(id))}</strong>
          <em>${escapeHtml(provider)}</em>
        </span>
        <span class="model-card-status">${modelConnectionPill(id)}</span>
        <span class="model-spec-row"><b>모델</b><span>${escapeHtml(model)}</span></span>
        <span class="model-spec-row"><b>역할</b><span>${escapeHtml(role)}</span></span>
        <span class="model-spec-row"><b>프롬프트</b><span>${escapeHtml(promptVersion)} · ${escapeHtml(variantLabel)}</span></span>
        <span class="model-spec-row"><b>엔드포인트</b><span>${escapeHtml(endpoint)}</span></span>
        <span class="model-spec-row"><b>샘플링</b><span>${escapeHtml(formatSampling(temp, topP))}</span></span>
      </label>
    `;
  }).join("") || emptyState("등록된 대상 모델 설정이 없습니다.");
  renderSelectedModelSummary();
  updateRunSubmitState();
}

function ensureModelPickerShell(target) {
  if (target.closest(".model-picker")) return;
  const panel = target.parentElement;
  if (!panel) return;
  panel.classList.add("model-picker-panel");
  const heading = panel.querySelector("h3");
  if (heading) heading.textContent = "실행 모델";
  const summary = document.createElement("div");
  summary.id = "selectedModelSummary";
  summary.className = "selected-model-summary";
  const picker = document.createElement("details");
  picker.className = "model-picker";
  picker.innerHTML = "<summary>모델 변경</summary>";
  panel.insertBefore(summary, target);
  panel.insertBefore(picker, target);
  picker.appendChild(target);
}

function renderSelectedModelSummary() {
  const target = document.getElementById("selectedModelSummary");
  if (!target) return;
  const selected = evalTargetRegistryIds().filter((id) => state.runConfigVersions.has(id));
  if (!selected.length) {
    target.innerHTML = `<strong>${escapeHtml(targetSelectionModeLabels[targetSelectionMode()])}</strong><span>선택한 모델 없음</span>`;
    return;
  }
  const chips = selected.slice(0, 3)
    .map((id) => `<span class="model-chip">${escapeHtml(modelLabelForVersion(id))}</span>`)
    .join("");
  const more = selected.length > 3 ? `<span class="model-chip muted">+${selected.length - 3}</span>` : "";
  const label = multiTargetSelectionMode()
    ? `비교 모델 ${selected.length}개`
    : "실행 모델 1개";
  target.innerHTML = `<strong>${escapeHtml(label)}</strong><div>${chips}${more}</div>`;
}

function modelEndpointLabel(spec) {
  if (!spec) return "-";
  if (spec.provider === "ollama") return spec.base_url || "local Ollama";
  return spec.base_url || spec.chat_url || spec.local_path || "-";
}

function formatSampling(temp, topP) {
  const parts = [];
  if (temp !== undefined && temp !== null && temp !== "") parts.push(`T ${temp}`);
  if (topP !== undefined && topP !== null && topP !== "") parts.push(`P ${topP}`);
  return parts.join(" / ") || "-";
}

function renderEvalRunSummary() {
  const target = document.getElementById("evalRunSummary");
  if (!target) return;
  const runProfile = document.getElementById("evalRunProfile")?.value || "single_dataset";
  const dataset = document.getElementById("evalDatasetSelect")?.value || selectedDataset;
  const selectedSummary = questionlistDatasets.find((item) => item.id === dataset) ?? {};
  const profile = evalCatalog?.profiles?.[runProfile] ?? {};
  const isProfileRun = runProfile !== "single_dataset";
  const targetMode = targetSelectionMode();
  const modelCount = [...document.querySelectorAll("[data-eval-config]:checked")].length;
  const limitRaw = document.getElementById("evalLimit")?.value ?? "";
  const dryRun = Boolean(document.getElementById("evalDryRun")?.checked);
  const exportFinalUi = Boolean(document.getElementById("evalExportFinalUi")?.checked);
  const answerCacheEnabled = document.getElementById("evalAnswerCacheEnabled")?.checked !== false;
  const scoringMode = document.getElementById("evalScoringMode")?.value || "static";
  const staticEmbeddingEnabled = Boolean(document.getElementById("evalStaticEmbeddingEnabled")?.checked);
  const staticEmbeddingModel = document.getElementById("evalStaticEmbeddingModel")?.value || "";
  const aggregationMethod = selectedJudgeAggregationMethod();
  const customPlanForSummary = isProfileRun && runProfile === "custom_seeded_mix" ? customPoolPlan() : null;
  const judgeCount = scoringMode === "static"
    ? 0
    : selectedJudgeConfigIds().length;
  const judgeWeightStatus = judgeCount > 1 && aggregationMethod === "weighted_mean"
    ? judgeScoreWeightStatus(selectedJudgeConfigIds())
    : null;
  const caseLabel = isProfileRun
    ? runProfileLabel(runProfile)
    : (selectedSummary.label || dataset);
  target.innerHTML = `
    <strong>${escapeHtml(caseLabel || "테스트 범위")}</strong>
    <span>${escapeHtml([
      modelCount ? `모델 ${modelCount}개` : "선택한 모델 없음",
      targetSelectionModeLabels[targetMode],
      customPlanForSummary ? `샘플 ${customPlanForSummary.total}` : (limitRaw ? `제한 ${limitRaw}` : ""),
      customPlanForSummary ? `seed ${customPlanForSummary.seed ?? "?"}` : "",
      scoringModeLabel(scoringMode),
      staticEmbeddingEnabled ? `embedding ${staticEmbeddingModel || "on"}` : "",
      judgeCount ? `Judge ${judgeCount}개` : "",
      judgeCount > 1 ? judgeAggregationLabels[aggregationMethod] : "",
      judgeWeightStatus ? `Judge 비중 ${judgeWeightStatus.total.toFixed(2)}` : "",
      answerCacheEnabled ? "답변 캐시 사용" : "새 답변 생성",
      dryRun ? "모의 실행" : "실제 실행",
      exportFinalUi ? "UI 내보내기" : "",
    ].filter(Boolean).join(" / "))}</span>
  `;
  updateRunSubmitState();
  updateHeaderJudgeStatus();
}

function updateRunSubmitState() {
  const targetCount = evalTargetRegistryIds().length;
  const selectedCount = [...document.querySelectorAll("[data-eval-config]:checked")].length;
  const targetMode = targetSelectionMode();
  const scoringMode = document.getElementById("evalScoringMode")?.value || "static";
  const runProfile = document.getElementById("evalRunProfile")?.value || "single_dataset";
  const aggregationMethod = selectedJudgeAggregationMethod();
  const staticEmbeddingEnabled = Boolean(document.getElementById("evalStaticEmbeddingEnabled")?.checked);
  const staticEmbeddingModel = document.getElementById("evalStaticEmbeddingModel")?.value?.trim() || "";
  const customPlanForSubmit = runProfile === "custom_seeded_mix" ? customPoolPlan() : null;
  let disabled = false;
  let reason = "선택한 모델과 실행 범위로 평가를 시작합니다.";
  if (targetCount === 0) {
    disabled = true;
    reason = "설정 탭에서 대상 모델을 먼저 등록하세요.";
  } else if (selectedCount === 0) {
    disabled = true;
    reason = "실행할 모델을 하나 이상 선택하세요.";
  } else if (targetMode === "single" && selectedCount > 1) {
    disabled = true;
    reason = "단일 모델 실행은 대상 모델을 1개만 선택해야 합니다.";
  } else if (staticEmbeddingEnabled && !staticEmbeddingModel) {
    disabled = true;
    reason = "정적 임베딩 유사도를 사용하려면 embedding model을 입력하세요.";
  } else if (customPlanForSubmit && (!Number.isInteger(customPlanForSubmit.seed) || customPlanForSubmit.seed < 0)) {
    disabled = true;
    reason = "직접 구성 랜덤 시드는 0 이상의 정수여야 합니다.";
  } else if (customPlanForSubmit && customPlanForSubmit.total < 1) {
    disabled = true;
    reason = "직접 구성 총 샘플 수는 1 이상이어야 합니다.";
  } else if (customPlanForSubmit && !Object.values(customPlanForSubmit.quotas).some((value) => Number(value) > 0)) {
    disabled = true;
    reason = "직접 구성은 하나 이상의 풀 비율을 0보다 크게 입력해야 합니다.";
  } else if (scoringMode !== "static" && !selectedJudgeConfigIds().length) {
    disabled = true;
    reason = "등록된 Judge 또는 대상 모델 Judge를 하나 이상 선택하세요.";
  } else if (scoringMode === "llm_override" && selectedJudgeConfigIds().length > 1) {
    disabled = true;
    reason = "단일 Judge 채점은 Judge를 1개만 선택해야 합니다.";
  } else if (scoringMode === "llm_blended" && selectedJudgeConfigIds().length < 2) {
    disabled = true;
    reason = "여러 Judge 합산은 Judge를 2개 이상 선택하세요. 3개 이상도 사용할 수 있습니다.";
  } else if (scoringMode !== "static" && selectedJudgeConfigIds().length > 1 && aggregationMethod === "weighted_mean" && !judgeScoreWeightStatus(selectedJudgeConfigIds()).valid) {
    disabled = true;
    reason = "Judge별 점수 비중 합계가 1이어야 합니다.";
  }

  const disabledHint = (() => {
    if (!disabled) return "";
    if (reason.includes("비중 합계")) return "Judge 비중 합계가 1이면 실행 가능";
    if (reason.includes("단일 모델")) return "모델 1개만 선택 필요";
    if (reason.includes("1개만")) return "Judge 1개만 선택 필요";
    if (reason.includes("2개 이상")) return "Judge 2개 이상 선택 필요";
    if (reason.includes("대상 모델")) return "대상 모델 등록 필요";
    if (reason.includes("실행할 모델")) return "실행할 모델 선택 필요";
    if (reason.includes("embedding model")) return "임베딩 모델명 입력 필요";
    if (reason.includes("랜덤 시드")) return "랜덤 시드 입력 필요";
    if (reason.includes("총 샘플 수")) return "총 샘플 수 입력 필요";
    if (reason.includes("풀 비율")) return "풀 비율 입력 필요";
    return reason;
  })();

  const syncButtonHint = (button) => {
    if (!button) return;
    button.disabled = disabled;
    button.title = reason;
    button.setAttribute("aria-disabled", disabled ? "true" : "false");
    const small = button.querySelector("small");
    if (small) {
      if (!button.dataset.defaultHint) button.dataset.defaultHint = small.textContent || "";
      small.textContent = disabled ? disabledHint : button.dataset.defaultHint;
    }
  };

  document.querySelectorAll("#evalRunSubmit, #evalRunForm button[type=\"submit\"]").forEach((button) => {
    syncButtonHint(button);
  });
  const answerOnlyButton = document.getElementById("answerOnlyRunSubmit");
  if (answerOnlyButton) {
    const answerDisabled = targetCount === 0 || selectedCount === 0 || (targetMode === "single" && selectedCount > 1);
    const answerReason = targetCount === 0
      ? "설정 탭에서 대상 모델을 먼저 등록하세요."
      : selectedCount === 0
        ? "실행할 모델을 하나 이상 선택하세요."
        : "단일 모델 실행은 대상 모델을 1개만 선택해야 합니다.";
    answerOnlyButton.disabled = answerDisabled;
    answerOnlyButton.title = answerDisabled ? answerReason : "LLM judge 없이 답변셋만 생성";
    answerOnlyButton.setAttribute("aria-disabled", answerDisabled ? "true" : "false");
  }
}

async function startEvalRun(options = {}) {
  const answerOnly = Boolean(options.answerOnly);
  const runProfile = document.getElementById("evalRunProfile")?.value || "single_dataset";
  const dataset = document.getElementById("evalDatasetSelect")?.value || selectedDataset;
  const selectedTargetMode = targetSelectionMode();
  const configs = [...document.querySelectorAll("[data-eval-config]:checked")].map((input) => input.value);
  const suites = [];
  const limitRaw = document.getElementById("evalLimit")?.value ?? "";
  const limit = runProfile === "custom_seeded_mix" ? null : (limitRaw === "" ? null : Number(limitRaw));
  const runId = document.getElementById("evalRunId")?.value || "";
  const customPlan = customPoolPlan();
  const seed = runProfile === "custom_seeded_mix" ? customPlan.seed : Number(evalCatalog.default_seed || 42);
  const poolQuotas = runProfile === "custom_seeded_mix" ? customPlan.quotas : {};
  const predictionFile = document.getElementById("evalPredictionFile")?.value || "";
  const selectedScoringMode = answerOnly ? "static" : (document.getElementById("evalScoringMode")?.value || "static");
  const staticEmbeddingEnabled = answerOnly ? false : Boolean(document.getElementById("evalStaticEmbeddingEnabled")?.checked);
  const staticEmbeddingModel = document.getElementById("evalStaticEmbeddingModel")?.value || "";
  const staticEmbeddingBaseUrl = document.getElementById("evalStaticEmbeddingBaseUrl")?.value || "";
  const judgeProvider = "registered";
  const judgeConfigIds = selectedJudgeConfigIds();
  const judgeAggregationMethod = selectedJudgeAggregationMethod();
  const judgeModel = "";
  const judgeApiKey = "";
  const judgeBaseUrl = "";
  const judgeTemperatureRaw = "";
  const judgeTopPRaw = "";
  const judgeTemperature = judgeTemperatureRaw === "" ? null : Number(judgeTemperatureRaw);
  const judgeTopP = judgeTopPRaw === "" ? null : Number(judgeTopPRaw);
  const judgeBlendWeight = Number(document.getElementById("evalJudgeBlendWeight")?.value || 0.5);
  const dryRun = answerOnly ? false : Boolean(document.getElementById("evalDryRun")?.checked);
  const exportFinalUi = answerOnly ? false : Boolean(document.getElementById("evalExportFinalUi")?.checked);
  const answerCacheEnabled = document.getElementById("evalAnswerCacheEnabled")?.checked !== false;

  if (runProfile === "custom_seeded_mix" && (!Number.isInteger(seed) || seed < 0)) {
    setEvalRunMessage("직접 구성 랜덤 시드는 0 이상의 정수여야 합니다.", "error");
    return;
  }
  if (runProfile === "custom_seeded_mix" && customPlan.total < 1) {
    setEvalRunMessage("직접 구성 총 샘플 수는 1 이상이어야 합니다.", "error");
    return;
  }
  if (runProfile === "custom_seeded_mix" && !Object.values(poolQuotas).some((value) => Number(value) > 0)) {
    setEvalRunMessage("직접 구성은 하나 이상의 풀 비율을 0보다 크게 입력해야 합니다.", "error");
    return;
  }
  if (!configs.length) {
    setEvalRunMessage("테스트를 실행할 모델을 하나 이상 선택해야 합니다.", "error");
    return;
  }
  if (selectedTargetMode === "single" && configs.length > 1) {
    setEvalRunMessage("단일 모델 실행은 대상 모델을 1개만 선택해야 합니다.", "error");
    return;
  }
  if (selectedScoringMode !== "static" && !judgeConfigIds.length) {
    setEvalRunMessage("등록된 Judge 또는 대상 모델 Judge를 하나 이상 선택하세요.", "error");
    return;
  }
  if (selectedScoringMode === "llm_override" && judgeConfigIds.length > 1) {
    setEvalRunMessage("단일 Judge 채점은 Judge를 1개만 선택해야 합니다.", "error");
    return;
  }
  if (selectedScoringMode === "llm_blended" && judgeConfigIds.length < 2) {
    setEvalRunMessage("여러 Judge 합산은 Judge를 2개 이상 선택하세요. 3개 이상도 사용할 수 있습니다.", "error");
    return;
  }
  if (selectedScoringMode !== "static" && judgeConfigIds.length > 1 && judgeAggregationMethod === "weighted_mean" && !judgeScoreWeightStatus(judgeConfigIds).valid) {
    setEvalRunMessage("Judge별 점수 비중 합계가 1이어야 합니다.", "error");
    return;
  }
  if (staticEmbeddingEnabled && !staticEmbeddingModel.trim()) {
    setEvalRunMessage("정적 임베딩 유사도를 사용하려면 embedding model을 입력하세요.", "error");
    return;
  }

  setEvalRunMessage(answerOnly ? "답변 생성 작업을 시작하는 중..." : "평가 작업을 시작하는 중...", "");
  const response = await apiFetch("api/eval/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      dataset,
      run_profile: runProfile,
      target_selection_mode: selectedTargetMode,
      seed,
      pool_quotas: poolQuotas,
      configs,
      suites,
      limit,
      run_id: runId,
      prediction_file: predictionFile,
      scoring_mode: selectedScoringMode,
      skip_scoring: answerOnly,
      answer_cache: answerCacheEnabled,
      static_embedding: {
        enabled: staticEmbeddingEnabled,
        model: staticEmbeddingModel,
        base_url: staticEmbeddingBaseUrl,
        keep_alive: "0",
      },
      judge: {
        config_id: judgeConfigIds[0] || "",
        config_ids: judgeConfigIds,
        provider: judgeProvider,
        model: judgeModel,
        api_key: judgeApiKey,
        base_url: judgeBaseUrl,
        temperature: judgeTemperature,
        top_p: judgeTopP,
        blend_weight: judgeBlendWeight,
        aggregation_method: judgeAggregationMethod,
        score_weights: judgeAggregationMethod === "weighted_mean" ? collectJudgeScoreWeights(judgeConfigIds) : {},
      },
      dry_run: dryRun,
      export_final_ui: exportFinalUi,
    }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    setEvalRunMessage(payload.error || `평가 작업 시작 실패 (${response.status})`, "error");
    return;
  }
  activeEvalJobId = payload.job?.job_id;
  setEvalRunMessage(`작업 시작: ${activeEvalJobId}`, "ok");
  renderEvalJob(payload.job);
  restartEvalJobPoll(activeEvalJobId);
}

function stopEvalJobPoll() {
  if (!evalJobPoll) return;
  clearInterval(evalJobPoll);
  evalJobPoll = null;
}

function restartEvalJobPoll(jobId) {
  stopEvalJobPoll();
  if (!jobId) return;
  evalJobPoll = setInterval(() => pollEvalJob(jobId), 1500);
  pollEvalJob(jobId);
}

async function pollEvalJob(jobId) {
  if (!jobId) return;
  const payload = await fetchJsonOptional(`api/eval/jobs/${encodeURIComponent(jobId)}`, null);
  const job = payload?.job;
  if (!job) return;
  renderEvalJob(job);
  if (["finished", "failed", "interrupted", "canceled"].includes(job.status)) {
    stopEvalJobPoll();
    setEvalRunMessage(`작업 ${job.status}: ${job.run_id}`, job.status === "finished" ? "ok" : "error");
    if (job.status === "finished" && job.run_id && job.export_final_ui !== false) {
      setEvalRunMessage(`평가 완료: ${job.run_id}. 결과 대시보드를 여는 중...`, "ok");
      try {
        await loadSelectedRun(job.run_id);
        activateTab("overview");
      } catch (error) {
        setEvalRunMessage(`평가 완료: ${job.run_id}. 결과 갱신은 새로고침 후 확인하세요. ${error.message}`, "error");
      }
    }
  }
}

async function reconnectEvalJob() {
  const payload = await fetchJsonOptional("api/eval/jobs", { jobs: [] });
  const jobs = payload?.jobs || [];
  const running = jobs.find((job) => ["running", "paused", "canceling"].includes(job.status));
  const latest = running || jobs[0];
  if (!latest?.job_id) return;
  activeEvalJobId = latest.job_id;
  await pollEvalJob(activeEvalJobId);
  if (running) {
    setEvalRunMessage(`실행 중인 작업에 다시 연결됨: ${running.run_id}`, "ok");
    restartEvalJobPoll(activeEvalJobId);
  }
}

function renderEvalJob(job) {
  if (!job) return;
  updateHeaderJudgeStatus(job);
  const progress = job.progress || {};
  setHtml("evalJobStatus", `
    <div class="job-status ${escapeHtml(job.status)}">
      <strong>${escapeHtml(job.status)}</strong>
      <span>${escapeHtml(job.run_id || "")}</span>
      <span>${escapeHtml(job.runner_type || "")}</span>
      <span>${escapeHtml(job.dataset || "")}</span>
      ${job.run_profile ? `<span>실행 범위: ${escapeHtml(job.run_profile)}</span>` : ""}
      <span>${escapeHtml((job.configs || []).join(", "))}</span>
      <span>채점: ${escapeHtml(scoringModeLabel(job.scoring_mode || "static"))}</span>
      ${job.composed_summary?.total ? `<span>구성 문항: ${Number(job.composed_summary.total).toLocaleString()}</span>` : ""}
      ${job.composed_summary_path ? `<span>요약: ${escapeHtml(job.composed_summary_path)}</span>` : ""}
      ${job.static_embedding_model ? `<span>embedding: ${escapeHtml(job.static_embedding_model)}${job.static_embedding_base_url ? ` · ${escapeHtml(job.static_embedding_base_url)}` : ""}</span>` : ""}
      ${job.judge_config ? `<span>Judge: ${escapeHtml(job.judge_config)} ${escapeHtml(job.judge_mode || "")}</span>` : ""}
      ${job.template_output ? `<span>템플릿: ${escapeHtml(job.template_output)}</span>` : ""}
      ${job.output_dir ? `<span>출력: ${escapeHtml(job.output_dir)}</span>` : ""}
      <code>${escapeHtml(job.command || "")}</code>
    </div>
  `);
  setHtml("evalJobProgress", renderEvalProgress(progress));
  renderEvalJobControls(job);
  const log = document.getElementById("evalJobLog");
  if (log) log.textContent = job.log_tail || "로그 출력을 기다리는 중입니다.";
}

function renderEvalJobControls(job) {
  const target = document.getElementById("evalJobControls");
  if (!target) return;
  const status = job?.status || "";
  const active = ["running", "paused", "canceling"].includes(status);
  if (!active || !["multi_model_eval", "judge_saved_answers"].includes(job.runner_type)) {
    target.innerHTML = "";
    return;
  }
  const isPaused = status === "paused";
  const isCanceling = status === "canceling";
  target.innerHTML = `
    <div class="job-controls">
      <button type="button" data-job-control="${isPaused ? "resume" : "pause"}" ${isCanceling ? "disabled" : ""}>
        ${isPaused ? "재개" : "일시중지"}
      </button>
      <button type="button" data-job-control="cancel" class="danger" ${isCanceling ? "disabled" : ""}>
        ${isCanceling ? "취소 중" : "취소"}
      </button>
      <span>${escapeHtml(isPaused ? "현재 케이스 사이에서 대기 중입니다." : "제어는 현재 케이스 완료 후 반영됩니다.")}</span>
    </div>
  `;
  target.querySelectorAll("[data-job-control]").forEach((button) => {
    button.addEventListener("click", () => controlEvalJob(job.job_id, button.dataset.jobControl));
  });
}

async function controlEvalJob(jobId, action) {
  if (!jobId || !action) return;
  if (action === "cancel" && !window.confirm("실행 중인 평가 작업을 취소할까요? 완료된 체크포인트는 남습니다.")) {
    return;
  }
  const label = { pause: "일시중지", resume: "재개", cancel: "취소" }[action] || action;
  setEvalRunMessage(`${label} 요청 중...`, "");
  const response = await apiFetch(`api/eval/jobs/${encodeURIComponent(jobId)}/control`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    setEvalRunMessage(payload.error || `${label} 요청 실패 (${response.status})`, "error");
    return;
  }
  renderEvalJob(payload.job);
  setEvalRunMessage(`${label} 요청 반영됨: ${payload.job?.run_id || jobId}`, action === "cancel" ? "error" : "ok");
  if (!evalJobPoll && !["finished", "failed", "interrupted", "canceled"].includes(payload.job?.status)) {
    restartEvalJobPoll(jobId);
  }
}

function renderEvalProgress(progress) {
  const percent = clamp(Number(progress.percent || 0), 0, 100);
  const answers = progress.answers || {};
  const judge = progress.judge || {};
  const models = progress.models || {};
  const answerText = `${Number(answers.done || 0).toLocaleString()} / ${Number(answers.total || 0).toLocaleString()}`;
  const judgeText = judge.enabled
    ? `${Number(judge.done || 0).toLocaleString()} / ${Number(judge.total || 0).toLocaleString()}`
    : "사용 안 함";
  const current = [progress.current_model, progress.current_case_id].filter(Boolean).join(" · ") || "-";
  return `
    <div class="eval-progress">
      <div class="progress-head">
        <strong>${percent.toFixed(1)}%</strong>
        <span>${escapeHtml(progress.status || (progress.dry_run ? "Dry run" : "실행 중/완료"))} · 현재 ${escapeHtml(current)}</span>
      </div>
      <div class="progress-track" aria-label="eval progress">
        <div class="progress-fill" style="width:${percent}%"></div>
      </div>
      <div class="progress-grid">
        <span>모델 ${Number(models.done || 0).toLocaleString()} / ${Number(models.total || 0).toLocaleString()}</span>
        <span>답변 ${answerText}</span>
        <span>LLM Judge ${judgeText}</span>
      </div>
      ${renderProgressByModel("답변", answers.by_model || {})}
      ${judge.enabled ? renderProgressByModel("Judge", judge.by_model || {}) : ""}
    </div>
  `;
}

function renderProgressByModel(label, byModel) {
  const entries = Object.entries(byModel || {});
  if (!entries.length) return "";
  return `
    <div class="progress-models">
      ${entries.map(([model, count]) => `
        <span><b>${escapeHtml(label)}</b> ${escapeHtml(model)} ${Number(count || 0).toLocaleString()}</span>
      `).join("")}
    </div>
  `;
}

function setEvalRunMessage(message, className) {
  const target = document.getElementById("evalRunMessage");
  setPanelMessage(target, message, className);
}

function setEvalReblendMessage(message, className) {
  const target = document.getElementById("evalReblendMessage");
  setPanelMessage(target, message, className);
}

function detailBlock(label, value) {
  return `
    <div class="detail-item">
      <span>${escapeHtml(label)}</span>
      <pre>${escapeHtml(value || "-")}</pre>
    </div>
  `;
}

function listValue(value) {
  if (Array.isArray(value)) return value.join("\n");
  return value || "";
}

function expectationListValue(value) {
  const text = listValue(value);
  return text && text.trim() ? text : "별도 조건 없음";
}

function jsonPreview(value, maxLength = 500) {
  if (!value || (typeof value === "object" && !Object.keys(value).length)) return "";
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return shortLabel(text, maxLength);
}

function toolCallSummary(calls) {
  if (!Array.isArray(calls) || !calls.length) return "";
  return calls.map((call, index) => {
    const name = call.tool_name || call.tool || call.name || call.function || `tool_${index + 1}`;
    const args = call.required_args || call.arguments || call.args || call.input || {};
    return `${name} ${jsonPreview(args, 180)}`;
  }).join("\n");
}

function toolOutputSummary(outputs) {
  if (!Array.isArray(outputs) || !outputs.length) return "";
  return outputs.map((output) => jsonPreview(output, 220)).join("\n");
}

function renderDistribution(elementId, values, labeler = (value) => value) {
  const entries = Object.entries(values ?? {}).sort((a, b) => Number(b[1]) - Number(a[1])).slice(0, 14);
  const max = Math.max(...entries.map(([, count]) => Number(count)), 1);
  setHtml(elementId, entries.map(([key, count]) => `
    <div class="bar-row wide">
      <span>${escapeHtml(labeler(key))}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${clamp((Number(count) / max) * 100, 0, 100)}%"></div></div>
      <strong>${Number(count).toLocaleString()}</strong>
    </div>
  `).join("") || emptyState("분포 데이터 없음"));
}

function kpi(label, value, delta, className = "") {
  const title = `${label}: ${value}${delta ? ` (${delta})` : ""}`;
  const classes = ["kpi", className].filter(Boolean).join(" ");
  return `<div class="${escapeHtml(classes)}" title="${escapeHtml(title)}"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong><em>${escapeHtml(delta)}</em></div>`;
}

function signed(value) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}`;
}

function renderTrend(data) {
  const target = document.getElementById("trendChart");
  if (!data.length) {
    target?.classList.remove("model-family-chart");
    setHtml("trendChart", emptyState("차트에 표시할 모델 결과가 없습니다."));
    return;
  }
  target?.classList.add("model-family-chart");

  const rows = [...data].sort(compareModelFamilyRows);
  const legend = renderModelFamilyLegend(rows);
  const rowHtml = rows.map((d) => {
    const info = modelFamilyInfo(d.version, d.model);
    const score = Number(d.overall_score || 0);
    const passRate = comparablePassRate(d) * 100;
    const scorePct = clamp(score, 0, 100);
    const passPct = clamp(passRate, 0, 100);
    const meta = [info.familyLabel, info.paramLabel, info.quantLabel].filter(Boolean).join(" · ");
    const title = `${info.label} · 종합 ${score.toFixed(1)}점 · 합격률 ${passRate.toFixed(1)}%`;
    return `
      <div class="trend-row" style="${escapeHtml(modelFamilyStyle(info))}" title="${escapeHtml(title)}">
        <div class="trend-model">
          <span class="model-family-dot" aria-hidden="true"></span>
          <div class="trend-model-copy">
            <strong title="${escapeHtml(info.label)}">${escapeHtml(info.compactLabel || info.label)}</strong>
            <span>
              <em>${escapeHtml(info.familyLabel)}</em>
              ${info.paramLabel ? `<i>${escapeHtml(info.paramLabel)}</i>` : ""}
              ${info.quantLabel ? `<i>${escapeHtml(info.quantLabel)}</i>` : ""}
            </span>
          </div>
        </div>
        <div class="trend-metrics" aria-label="${escapeHtml(title)}">
          <div class="trend-scale" aria-hidden="true"><span>0</span><span>50</span><span>100</span></div>
          <div class="trend-metric-line">
            <span>점수</span>
            <em><i style="width:${scorePct}%"></i></em>
          </div>
          <div class="trend-metric-line pass-rate">
            <span>합격률</span>
            <em><i style="width:${passPct}%"></i></em>
          </div>
        </div>
        <div class="trend-values">
          <strong>${score.toFixed(1)}</strong>
          <span>${passRate.toFixed(1)}%</span>
        </div>
      </div>
    `;
  }).join("");

  setHtml("trendChart", `
    <div class="trend-chart">
      <div class="trend-chart-head">
        <div class="trend-family-legend" aria-label="모델 계열">${legend}</div>
        <div class="trend-metric-legend">
          <span><b class="score-swatch"></b>종합 점수</span>
          <span><b class="pass-swatch"></b>합격률</span>
        </div>
      </div>
      <div class="trend-rows">${rowHtml}</div>
    </div>
  `);
}

function compareModelFamilyRows(left, right) {
  const a = modelFamilyInfo(left.version, left.model);
  const b = modelFamilyInfo(right.version, right.model);
  return a.familyOrder - b.familyOrder ||
    a.paramValue - b.paramValue ||
    a.compactLabel.localeCompare(b.compactLabel, "ko") ||
    String(left.version || "").localeCompare(String(right.version || ""), "ko");
}

function renderModelFamilyLegend(rows) {
  const families = new Map();
  rows.forEach((row) => {
    const info = modelFamilyInfo(row.version, row.model);
    if (!families.has(info.familyId)) families.set(info.familyId, { ...info, count: 0 });
    families.get(info.familyId).count += 1;
  });
  return [...families.values()].map((info) => `
    <span class="trend-family-chip" style="${escapeHtml(modelFamilyStyle(info))}">
      <b class="model-family-dot" aria-hidden="true"></b>
      ${escapeHtml(info.familyLabel)}
      <em>${info.count}</em>
    </span>
  `).join("");
}

function renderMetricBars(run) {
  setHtml("metricBars", metricCols.map((key) => {
    const unavailable = key === "utl" && !run.utl_applicable;
    const value = Number(run[key] || 0);
    return `
      <div class="bar-row">
        <span>${metricLabels[key]}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${unavailable ? 0 : clamp(value * 5, 0, 100)}%"></div></div>
        <strong>${unavailable ? "N/A" : value.toFixed(1)}</strong>
      </div>
    `;
  }).join(""));
}

function renderCompare(runData) {
  renderCompareControls(runData);

  if (!runData.length) {
    setHtml("compareChart", emptyState("선택된 모델이 없습니다."));
    setHtml("runsTable", "");
    return;
  }

  setHtml("compareChart", runData.map((run) => {
    const info = modelFamilyInfo(run.version, run.model);
    return `
      <div class="compare-row" style="${escapeHtml(modelFamilyStyle(info))}">
        <div class="compare-model-name">
          <span class="model-family-dot" aria-hidden="true"></span>
          <strong title="${escapeHtml(info.label)}">${escapeHtml(info.compactLabel || info.label)}</strong>
          <em>${escapeHtml([info.familyLabel, info.paramLabel, info.quantLabel].filter(Boolean).join(" · "))}</em>
        </div>
        <div class="compare-cells">
          ${metricCols.map((key) => compareScoreCell(metricLabels[key], Number(run[key] || 0), 20, "", key === "utl" && !run.utl_applicable)).join("")}
          ${compareScoreCell("자동", comparableScore(run), 100, "score-total")}
        </div>
      </div>
    `;
  }).join(""));

  setHtml("runsTable", table(
    ["모델", "Run 유형", "자동 점수", "전체 점수", "통과율", "검토대기", "지연시간", "비용"],
    runData.map((d) => [
      modelCell(d.version, d.model),
      d.run_type,
      scoreBadge(comparableScore(d)),
      scoreBadge(Number(d.overall_score || 0)),
      `${(comparablePassRate(d) * 100).toFixed(1)}%`,
      Number(d.review_pending_count || 0).toLocaleString(),
      `${d.avg_latency_ms}ms`,
      formatKrw(d.avg_cost_krw),
    ])
  ));
}

function renderCompareControls(runData) {
  const target = document.getElementById("compareControls");
  if (!target) return;
  const availableIds = unique(runs.map((run) => run.version).filter(Boolean));
  const selectedIds = runData.map((run) => run.version).filter(Boolean);
  const selectedCount = selectedIds.length;
  const modeText = selectedCount === 2
    ? "1대1 비교 모드"
    : selectedCount > 2
      ? `${selectedCount}개 모델 다중 비교`
      : selectedCount === 1
        ? "비교할 모델을 하나 더 선택하세요"
        : "모델을 선택하세요";
  const chips = runData.map((run) => {
    const info = modelFamilyInfo(run.version, run.model);
    return `
      <button type="button" class="compare-chip" style="${escapeHtml(modelFamilyStyle(info))}" data-compare-remove="${escapeHtml(run.version)}" title="${escapeHtml(`${info.label} 선택 해제`)}">
        <span class="model-family-dot" aria-hidden="true"></span>
        <strong>${escapeHtml(info.compactLabel || shortModelLabel(run.version))}</strong>
        <span>해제</span>
      </button>
    `;
  }).join("");
  target.innerHTML = `
    <div class="compare-control-top">
      <div class="compare-control-copy">
        <strong>${escapeHtml(modeText)}</strong>
        <span>체크된 모델만 차트와 표에 반영됩니다. 2개만 남기면 1대1 비교로 볼 수 있습니다.</span>
      </div>
      <div class="compare-actions">
        <button type="button" data-compare-action="top2" ${availableIds.length < 2 ? "disabled" : ""}>상위 2개</button>
        <button type="button" data-compare-action="all" ${!availableIds.length ? "disabled" : ""}>전체 선택</button>
        <button type="button" data-compare-action="clear" ${!selectedCount ? "disabled" : ""}>선택 해제</button>
      </div>
    </div>
    <div class="compare-chip-row">
      ${chips || `<span class="compare-empty-chip">선택 모델 없음</span>`}
    </div>
    ${selectedCount === 2 ? renderHeadToHeadSummary(runData) : ""}
  `;
  bindCompareControls();
}

function bindCompareControls() {
  document.querySelectorAll("[data-compare-action]").forEach((button) => {
    button.addEventListener("click", () => {
      const availableRuns = [...runs].filter((run) => run.version);
      const action = button.dataset.compareAction;
      if (action === "top2") {
        const topIds = availableRuns
          .sort((a, b) => comparableScore(b) - comparableScore(a))
          .slice(0, 2)
          .map((run) => run.version);
        state.resultVersions = new Set(topIds);
      } else if (action === "all") {
        state.resultVersions = new Set(unique(availableRuns.map((run) => run.version)));
      } else if (action === "clear") {
        state.resultVersions = new Set();
      }
      state.failureLimit = 40;
      renderFilters();
      renderAll({ tab: "compare" });
    });
  });
  document.querySelectorAll("[data-compare-remove]").forEach((button) => {
    button.addEventListener("click", () => {
      state.resultVersions.delete(button.dataset.compareRemove);
      state.failureLimit = 40;
      renderFilters();
      renderAll({ tab: "compare" });
    });
  });
}

function renderHeadToHeadSummary(runData) {
  const [left, right] = runData;
  const leftScore = comparableScore(left);
  const rightScore = comparableScore(right);
  const scoreDelta = leftScore - rightScore;
  const passDelta = comparablePassRate(left) - comparablePassRate(right);
  const winner = Math.abs(scoreDelta) < 0.05
    ? "동률"
    : `${modelLabelForVersion(scoreDelta > 0 ? left.version : right.version)} 우세`;
  return `
    <div class="compare-head-to-head">
      <span><strong>우세</strong>${escapeHtml(winner)}</span>
      <span><strong>점수차</strong>${escapeHtml(signed(scoreDelta))}점</span>
      <span><strong>통과율차</strong>${escapeHtml(signed(passDelta * 100))}%p</span>
      <span><strong>검토대기</strong>${Number(left.review_pending_count || 0).toLocaleString()} / ${Number(right.review_pending_count || 0).toLocaleString()}</span>
    </div>
  `;
}

function comparableScore(run) {
  return Number(run.scored_questions || 0) > 0
    ? Number(run.scored_average || 0)
    : Number(run.overall_score || 0);
}

function comparablePassRate(run) {
  return Number(run.scored_questions || 0) > 0
    ? Number(run.scored_pass_rate || 0)
    : Number(run.pass_rate || 0);
}

function formatKrw(value) {
  const numeric = Number(value || 0);
  return `${numeric.toLocaleString("ko-KR")}원`;
}

function compareScoreCell(label, score, maxScore, className = "", unavailable = false) {
  const classes = ["score-cell", className].filter(Boolean).join(" ");
  if (unavailable) {
    return `
      <div class="${escapeHtml(classes)} score-na" title="${escapeHtml(`${label}: RAG 비적용 모델에서는 최종 점수에서 제외됩니다.`)}">
        <span>${escapeHtml(label)}</span>
        <strong>N/A</strong>
        <em class="score-bar" aria-hidden="true"><i style="width:0%"></i></em>
      </div>
    `;
  }
  const percent = clamp((score / Math.max(maxScore, 1)) * 100, 0, 100);
  return `
    <div class="${escapeHtml(classes)}" title="${escapeHtml(`${label}: ${score.toFixed(1)} / ${maxScore}`)}">
      <span>${escapeHtml(label)}</span>
      <strong>${score.toFixed(1)} / ${maxScore}</strong>
      <em class="score-bar" aria-hidden="true"><i style="width:${percent}%"></i></em>
    </div>
  `;
}

function renderRegression(caseData) {
  const regressionRows = caseData.filter((d) => !isBenchmarkCase(d));
  if (!regressionRows.length) {
    const benchmarkRows = caseData.filter(isBenchmarkCase).length;
    const message = benchmarkRows
      ? `현재 선택한 실행(${selectedRunId || latestRun?.run_id || "현재 결과"})은 벤치마크 결과만 포함합니다. 회귀 문항 결과를 보려면 회귀 실행 결과를 선택하세요.`
      : "현재 선택한 실행에 회귀 문항 결과가 없습니다.";
    setHtml("regressionKpis", emptyState(message));
    setHtml("regressionTable", emptyState("회귀 탭은 regression/golden 결과가 있을 때 하락 케이스, 기준 미달 문항, 배포 판정을 표시합니다."));
    return;
  }
  const low = regressionRows
    .filter((d) =>
      metricCols.some((key) => Number(d[key] || 0) < state.threshold / 5) ||
      isFailureCell(d) ||
      Number(d.regression_delta || 0) < 0 ||
      ["block", "review"].includes(d.release_gate)
    )
    .sort((a, b) => releaseRank(a.release_gate) - releaseRank(b.release_gate) || a.regression_delta - b.regression_delta || a.acc - b.acc);

  const minDelta = regressionRows.length ? Math.min(...regressionRows.map((d) => Number(d.regression_delta || 0)), 0) : 0;
  setHtml("regressionKpis", [
    kpi("주의 케이스", `${low.length.toLocaleString()}개`, "점수/회귀/판정"),
    kpi("하락 케이스", `${regressionRows.filter((d) => Number(d.regression_delta || 0) < 0).length.toLocaleString()}개`, "이전 대비 하락"),
    kpi("실패 케이스", `${regressionRows.filter(isFailureCell).length.toLocaleString()}개`, `${state.threshold}점 기준`),
    kpi("최대 하락폭", `${minDelta.toFixed(1)}점`, "회귀 변화량"),
  ].join(""));

  setHtml("regressionTable", table(
    ["ID", "분류", "회귀 묶음", "토픽", "질문유형", "난이도", "모델", "점수", "HAL", "변화량", "판정", "오류"],
    low.map((d) => [
      d.question_id,
      d.qa_category || labelSource(d.source_type),
      d.regression_suite,
      d.qa_topic,
      d.question_type,
      labelSeverity(d.difficulty),
      modelCell(d.version, d.model),
      scoreBadge(caseOverallScore(d)),
      scoreBadge(d.hal, 20),
      signed(Number(d.regression_delta || 0)),
      gateBadge(d.release_gate),
      errorBadge(d.error_type),
    ])
  ));
}

function renderBenchmark(caseData) {
  const rows = caseData.filter(isBenchmarkCase);
  if (!rows.length) {
    setHtml("benchmarkKpis", emptyState("벤치마크 결과가 없습니다. 벤치마크 실행 범위를 실행하면 여기에 표시됩니다."));
    setHtml("benchmarkModelTable", "");
    setHtml("benchmarkDatasetTable", "");
    setHtml("benchmarkMatrix", "");
    setHtml("benchmarkFailures", "");
    return;
  }
  const uniqueCases = new Set(rows.map((d) => d.question_id));
  const avgScore = rows.reduce((sum, row) => sum + caseOverallScore(row), 0) / rows.length;
  const passRate = rows.filter((row) => !isFailureCell(row)).length / rows.length;
  const models = new Set(rows.map((d) => d.version));
  const oneDSlices = benchmarkOneDSlices(rows);
  const weakOneD = oneDSlices.filter((entry) => !entry.reliability.reliable).length;
  const weakTwoD = benchmarkTwoDCells(rows).filter((entry) => !entry.reliability.reliable).length;
  const weakThreeD = benchmarkThreeDCells(rows).filter((entry) => !entry.reliability.reliable).length;
  setHtml("benchmarkKpis", [
    kpi("벤치마크 문항", uniqueCases.size.toLocaleString(), `${models.size}개 모델`),
    kpi("평균 점수", avgScore.toFixed(1), "1D 슬라이스 기준"),
    kpi("통과율", `${(passRate * 100).toFixed(1)}%`, "벤치마크 기준"),
    kpi("신뢰도 부족", `${(weakOneD + weakTwoD + weakThreeD).toLocaleString()}개`, `1D ${weakOneD} / 2D ${weakTwoD} / 3D ${weakThreeD}`),
  ].join(""));

  const byModel = aggregateScoreRows(rows, "version").sort((a, b) => b.score - a.score);
  setHtml("benchmarkModelTable", table(
    ["모델", "버전", "케이스", "평균", "통과", "실패"],
    byModel.map((entry) => {
      const sample = entry.rows[0] || {};
      const failureCount = entry.rows.filter(isFailureCell).length;
      return [
        modelCell(entry.key, sample.model),
        entry.key,
        entry.caseCount,
        scoreBadge(entry.score),
        `${(entry.passRate * 100).toFixed(1)}%`,
        failureCount.toLocaleString(),
      ];
    })
  ));

  const byDataset = oneDSlices.sort((a, b) => a.reliability.reliable - b.reliability.reliable || a.dimension.localeCompare(b.dimension) || a.score - b.score);
  setHtml("benchmarkDatasetTable", table(
    ["1D 슬라이스", "값", "케이스", "점수", "통과율", "신뢰도"],
    byDataset.map((entry) => {
      return [
        entry.dimensionLabel,
        entry.key,
        entry.caseCount,
        entry.score.toFixed(1),
        `${(entry.passRate * 100).toFixed(1)}%`,
        reliabilityBadge(entry.reliability),
      ];
    })
  ));

  setHtml("benchmarkMatrix", renderBenchmarkMatrix(rows));

  const failures = [...rows]
    .filter(isFailureCell)
    .sort((a, b) => caseOverallScore(a) - caseOverallScore(b))
    .slice(0, 80);
  setHtml("benchmarkFailures", failures.length ? table(
      ["분류", "토픽", "질문유형", "모델", "점수", "결과", "채점 사유"],
    failures.map((row) => [
      labelSource(row.source_type),
      labelTopic(row.qa_matrix_topic),
      labelQuestionType(row.question_type),
      modelCell(row.version, row.model),
      scoreBadge(caseOverallScore(row)),
      passFailBadge(row.pass_fail),
      row.llm_judge_reason || row.judge_reason,
    ])
  ) : emptyState("벤치마크 실패 케이스가 없습니다."));
}

function benchmarkOneDSlices(rows) {
  return [
    { dimension: "qa_category", dimensionLabel: "대분류", key: "source_type" },
    { dimension: "question_type", dimensionLabel: "질문유형", key: "question_type" },
    { dimension: "qa_topic", dimensionLabel: "금융토픽", key: "qa_matrix_topic" },
  ].flatMap((spec) =>
    aggregateScoreRows(rows, spec.key).map((entry) => ({
      ...entry,
      dimension: spec.dimension,
      dimensionLabel: spec.dimensionLabel,
      reliability: reliabilityForRows(entry.rows, "oneD"),
    }))
  );
}

function benchmarkTwoDCells(rows) {
  const topics = matrixKeysByCount(rows, "qa_matrix_topic");
  const types = matrixKeysByCount(rows, "question_type");
  return topics.flatMap((topic) =>
    types.map((type) => {
      const cellRows = rows.filter((row) => row.qa_matrix_topic === topic && row.question_type === type);
      return {
        topic,
        type,
        rows: cellRows,
        reliability: reliabilityForRows(cellRows, "twoD"),
      };
    }).filter((entry) => entry.rows.length)
  );
}

function benchmarkThreeDCells(rows) {
  const map = new Map();
  rows.forEach((row) => {
    const key = [
      valueOrUnknown(row.source_type),
      valueOrUnknown(row.question_type),
      valueOrUnknown(row.qa_matrix_topic),
    ].join("||");
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(row);
  });
  return [...map.entries()].map(([key, cellRows]) => {
    const [category, type, topic] = key.split("||");
    const score = cellRows.reduce((sum, row) => sum + caseOverallScore(row), 0) / Math.max(cellRows.length, 1);
    const passRate = cellRows.filter((row) => !isFailureCell(row)).length / Math.max(cellRows.length, 1);
    return {
      category,
      type,
      topic,
      rows: cellRows,
      score,
      passRate,
      reliability: reliabilityForRows(cellRows, "threeD"),
    };
  });
}

function reliabilityForRows(rows, level = "oneD") {
  const minCases = reliabilityMinimums[level] || reliabilityMinimums.oneD;
  const caseCount = new Set(rows.map((row) => row.question_id)).size;
  return {
    level,
    caseCount,
    minCases,
    reliable: caseCount >= minCases,
  };
}

function reliabilityBadge(reliability) {
  const label = reliability.reliable ? "신뢰 가능" : "신뢰도 부족";
  const title = `n=${reliability.caseCount} / 기준 ${reliability.minCases}`;
  return {
    [rawHtml]: true,
    value: `<span class="reliability-badge ${reliability.reliable ? "ok" : "low"}">${label}<em>${escapeHtml(title)}</em></span>`,
  };
}

function renderBenchmarkMatrix(rows) {
  const topics = matrixKeysByCount(rows, "qa_matrix_topic");
  const types = matrixKeysByCount(rows, "question_type");
  if (!topics.length || !types.length) return emptyState("매트릭스 메타데이터가 없습니다.");
  const body = topics.map((topic) => [
    topic,
    ...types.map((type) => {
      const cellRows = rows.filter((row) => row.qa_matrix_topic === topic && row.question_type === type);
      if (!cellRows.length) return "-";
      const passRate = cellRows.filter((row) => !isFailureCell(row)).length / cellRows.length;
      const score = cellRows.reduce((sum, row) => sum + caseOverallScore(row), 0) / cellRows.length;
      const reliability = reliabilityForRows(cellRows, "twoD");
      const title = `${labelTopic(topic)} / ${labelQuestionType(type)}: 통과율 ${(passRate * 100).toFixed(1)}%, 평균 ${score.toFixed(1)}점, n=${reliability.caseCount}`;
      return {
        [rawHtml]: true,
        value: `<span class="matrix-cell heatmap ${matrixToneClass(score)} ${reliability.reliable ? "reliable" : "low-confidence"}" title="${escapeHtml(title)}"><strong>${(passRate * 100).toFixed(0)}%</strong><em>${score.toFixed(1)}점 · n=${reliability.caseCount}</em>${reliability.reliable ? "" : "<small>신뢰도 부족</small>"}</span>`,
      };
    }),
  ]);
  return `
    <p class="matrix-summary">현재는 1D 슬라이스를 대표 점수로 사용합니다. 2D 셀은 n&lt;${reliabilityMinimums.twoD}이면 신뢰도 부족으로 표시합니다.</p>
    ${table(["토픽", ...types], body)}
    ${renderThreeDCellReliability(rows)}
  `;
}

function matrixToneClass(score) {
  const numeric = Number(score || 0);
  if (numeric >= 80) return "score-high";
  if (numeric >= 60) return "score-mid";
  return "score-low";
}

function renderThreeDCellReliability(rows) {
  const cells = benchmarkThreeDCells(rows).sort((a, b) =>
    a.reliability.reliable - b.reliability.reliable ||
    a.reliability.caseCount - b.reliability.caseCount ||
    a.score - b.score
  );
  if (!cells.length) return "";
  const weakCount = cells.filter((cell) => !cell.reliability.reliable).length;
  const previewRows = cells.slice(0, 30).map((cell) => [
    labelSource(cell.category),
    cell.type,
    cell.topic,
    cell.reliability.caseCount,
    cell.score.toFixed(1),
    `${(cell.passRate * 100).toFixed(1)}%`,
    reliabilityBadge(cell.reliability),
  ]);
  return `
    <div class="matrix-reliability-summary">
      <strong>3D 셀 신뢰도</strong>
      <span>대분류 × 질문유형 × 금융토픽 ${cells.length}개 셀 중 ${weakCount}개는 n&lt;${reliabilityMinimums.threeD}로 신뢰도 부족입니다.</span>
    </div>
    ${table(["대분류", "질문유형", "금융토픽", "케이스", "점수", "통과율", "신뢰도"], previewRows)}
  `;
}

function releaseReadinessLabel(summary) {
  if (Number(summary.release_gate_eligible_cases || 0) > 0) return "배포 판정 대상";
  if (summary.gate_eligible === false) return "차단 제외";
  return "탐색용";
}

function renderExploratory(caseData) {
  const rows = caseData
    .filter((row) =>
      ["draft", "shadow"].includes(row.case_status) ||
      isTrue(row.human_review_required) ||
      row.release_gate === "not_applicable" ||
      isFalse(row.gate_eligible) ||
      isFalse(row.release_gate_eligible)
    );
  if (!rows.length) {
    setHtml("exploratoryKpis", emptyState("탐색/분석용 결과가 없습니다."));
    setHtml("exploratoryTable", emptyState("이 탭은 배포 차단 대상이 아닌 분석용 행, Shadow 행, 수동 검토 대상 행을 표시합니다."));
    return;
  }
  const uniqueCases = new Set(rows.map((row) => row.question_id));
  const reviewRows = rows.filter((row) => isTrue(row.human_review_required));
  const shadowRows = rows.filter((row) => row.case_status === "shadow");
  const benchmarkRows = rows.filter(isBenchmarkCase);
  const avgScore = rows.reduce((sum, row) => sum + caseOverallScore(row), 0) / rows.length;
  setHtml("exploratoryKpis", [
    kpi("탐색 케이스", uniqueCases.size.toLocaleString(), "배포 차단 제외"),
    kpi("벤치마크 행", benchmarkRows.length.toLocaleString(), "분석 전용 포함"),
    kpi("Shadow 행", shadowRows.length.toLocaleString(), "미검증/초안"),
    kpi("검토 필요", reviewRows.length.toLocaleString(), "수동 검토 대기열"),
    kpi("평균 점수", avgScore.toFixed(1), "분석 전용"),
  ].join(""));
  const sorted = [...rows]
    .sort((a, b) => Number(isTrue(b.human_review_required)) - Number(isTrue(a.human_review_required)) || caseOverallScore(a) - caseOverallScore(b))
    .slice(0, 120);
  setHtml("exploratoryTable", table(
    ["케이스", "종류", "상태", "모범답안", "검토", "모델", "점수", "판정", "오류", "사유"],
    sorted.map((row) => [
      row.question_id,
      isBenchmarkCase(row) ? "벤치마크" : "회귀",
      row.case_status,
      booleanBadge(isTrue(row.gold_verified), "검증됨", "미검증"),
      isTrue(row.human_review_required) ? badgeCell("검토 필요", "review") : badgeCell("불필요", "muted"),
      modelCell(row.version, row.model),
      scoreBadge(caseOverallScore(row)),
      gateBadge(row.release_gate),
      errorBadge(row.error_type),
      row.llm_judge_reason || row.judge_reason,
    ])
  ));
}

function renderHumanReviewQueue(caseData) {
  const rows = caseData
    .filter((row) => isTrue(row.human_review_required) || !isTrue(row.gold_verified) || row.llm_judge_status === "error" || row.llm_judge_unresolved_conflict)
    .sort((a, b) => reviewPriorityRank(a) - reviewPriorityRank(b) || caseOverallScore(a) - caseOverallScore(b))
    .slice(0, 160);
  if (!rows.length) {
    setHtml("reviewQueueKpis", emptyState("검토 대기 케이스가 없습니다. Judge 충돌도 없습니다."));
    setHtml("reviewQueueTable", "");
    return;
  }
  const uniqueCases = new Set(rows.map((row) => row.question_id));
  const highPriority = rows.filter((row) => reviewPriorityRank(row) === 0);
  setHtml("reviewQueueKpis", [
    kpi("검토 케이스", uniqueCases.size.toLocaleString(), "고유 케이스"),
    kpi("높은 우선순위", highPriority.length.toLocaleString(), "차단/실패/치명"),
    kpi("미검증", rows.filter((row) => !isTrue(row.gold_verified)).length.toLocaleString(), "모범답안 필요"),
    kpi("Judge 오류", rows.filter((row) => row.llm_judge_status === "error").length.toLocaleString(), "감사"),
    kpi("미해결 Judge 충돌", rows.filter((row) => row.llm_judge_unresolved_conflict).length.toLocaleString(), "수동 검토"),
  ].join(""));
  setHtml("reviewQueueTable", table(
    ["우선순위", "케이스", "상태", "모델", "점수", "오류", "권장 조치", "Judge 사유"],
    rows.map((row) => [
      reviewPriorityBadge(row),
      row.question_id,
      row.case_status,
      modelCell(row.version, row.model),
      scoreBadge(caseOverallScore(row)),
      errorBadge(row.error_type),
      suggestedReviewAction(row),
      row.llm_judge_unresolved_conflict
        ? `Judge 충돌: ${humanJudgeConflictReason(row.llm_judge_conflict_reason) || "상위 Judge 재평가 권장"}`
        : row.llm_judge_reason || row.judge_reason,
    ])
  ));
}

function isBenchmarkCase(row) {
  if (isRegressionCase(row)) return false;
  return row.dataset_role === "benchmark" ||
    row.benchmark_group !== "unknown" ||
    rowRunMarker(row).includes("benchmark");
}

function isRegressionCase(row) {
  const marker = rowRunMarker(row);
  return marker.includes("regression") ||
    marker.includes("golden") ||
    marker.includes("hard_negative") ||
    marker.includes("hardnegative") ||
    marker.includes("edge_case") ||
    marker.includes("edgecase");
}

function rowRunMarker(row) {
  return [
    row?.dataset_role,
    row?.dataset_pool_id,
    row?.case_source,
    row?.dataset_version,
    row?.benchmark_group,
    row?.question_id,
  ].map((value) => String(value || "").toLowerCase()).join(" ");
}

function renderFailures(caseData) {
  const failures = caseData.filter(isFailureCell);
  const failureBuckets = failures.map((row) => ({
    ...row,
    failure_error_type: failureErrorType(row),
  }));
  const counts = groupCount(failureBuckets, "failure_error_type");
  const max = Math.max(...counts.map((d) => d.count), 1);
  const sorted = [...failures].sort((a, b) => caseOverallScore(a) - caseOverallScore(b));
  const limit = Number(state.failureLimit || 40);
  const visible = sorted.slice(0, limit);

  setHtml("failureChart", counts.map((d) => `
    <div class="failure-type-row" title="오른쪽 대표 오류 사례에서 상세 내용을 확인하세요.">
      <span title="${escapeHtml(d.key || "unknown")}">${escapeHtml(labelErrorType(d.key))}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${clamp((d.count / max) * 100, 0, 100)}%"></div></div>
      <strong>${d.count}</strong>
    </div>
  `).join("") || emptyState("현재 필터 기준 과락 항목이 없습니다."));

  setHtml("failureCases", visible.length ? `
    <div class="case-list-meta">과락 ${sorted.length.toLocaleString()}개 중 ${visible.length.toLocaleString()}개 표시</div>
    ${visible.map((d) => `
    <div class="case">
      <strong>${escapeHtml(d.question_id)} · ${escapeHtml(labelErrorType(failureErrorType(d)))} · ${escapeHtml(labelSource(d.source_type))}</strong>
      <div class="case-badge-row">
        ${formatCell(scoreBadge(caseOverallScore(d)))}
        ${formatCell(passFailBadge(d.pass_fail))}
        ${formatCell(errorBadge(failureErrorType(d)))}
        ${formatCell(gateBadge(d.release_gate))}
      </div>
      <p>${escapeHtml(d.question)}</p>
      <p><b>모델 답변:</b> ${escapeHtml(d.answer_excerpt || "-")}</p>
      <p><b>기대 모범답안:</b> ${escapeHtml(shortLabel(d.output || d.gold_excerpt || d.ground_truth_doc || "-", 520))}</p>
      <p><b>규칙 기반:</b> ${escapeHtml(d.static_overall_score || d.overall_score || "-")} · <b>LLM:</b> ${escapeHtml(d.llm_judge_overall_score || "-")}</p>
      ${(d.llm_judge_conflict_detected || d.llm_judge_conflict) ? `<p><b>Judge 충돌:</b> ${escapeHtml(humanJudgeConflictReason(d.llm_judge_conflict_reason) || "상위 Judge 재평가 권장")}</p>` : ""}
      <p><b>Judge:</b> ${escapeHtml(d.llm_judge_reason || d.judge_reason)}</p>
    </div>
  `).join("")}
    ${visible.length < sorted.length ? `<button id="showMoreFailures" type="button" class="link-button">더 보기 (${Math.min(40, sorted.length - visible.length).toLocaleString()}개)</button>` : ""}
  ` : emptyState("과락 항목이 없습니다."));
  const more = document.getElementById("showMoreFailures");
  if (more) {
    more.onclick = () => {
      state.failureLimit = limit + 40;
      renderFailures(filteredCases());
    };
  }
}

function renderExplorer(caseData) {
  const query = state.questionSearch;
  const candidateRows = query
    ? caseData.filter((row) => questionMatchesSearch(row, query))
    : caseData;
  const ids = unique(candidateRows.map((d) => d.question_id));
  const visibleIds = ids.slice(0, 200);
  if (!visibleIds.includes(state.selectedQuestion)) state.selectedQuestion = visibleIds[0] || null;
  const select = document.getElementById("questionSelect");
  if (!select) return;
  select.disabled = !visibleIds.length;
  select.innerHTML = visibleIds.map((id) => `<option value="${escapeHtml(id)}" ${id === state.selectedQuestion ? "selected" : ""}>${escapeHtml(id)}</option>`).join("");
  select.onchange = () => {
    state.selectedQuestion = select.value;
    renderExplorer(filteredCases());
  };
  const meta = document.getElementById("questionSelectMeta");
  if (meta) {
    meta.textContent = ids.length
      ? `${ids.length.toLocaleString()}개 중 ${visibleIds.length.toLocaleString()}개 표시`
      : "검색 결과 없음";
  }

  const rows = caseData.filter((d) => d.question_id === state.selectedQuestion);
  const first = rows[0];
  setHtml("questionDetail", first ? `
    <div class="question-box">
      <strong>${escapeHtml(first.question)}</strong>
      <span>
        ${escapeHtml(first.scenario_tag)} · ${escapeHtml(labelSeverity(first.difficulty))} ·
        ${escapeHtml(labelSource(first.source_type))} · ${escapeHtml(first.question_type)} · ${escapeHtml(first.regression_suite)} ·
        근거 문서: ${escapeHtml(first.ground_truth_doc || first.source_title || "")}
      </span>
    </div>
    ${table(
    ["모델", "응답 요약", "규칙 기반", "LLM 평가", "최종", "결과", "채점 사유"],
      rows.map((d) => [
        modelCell(d.version, d.model),
        d.answer_excerpt,
        scoreBadgeOrBlank(firstPresentValue(d.static_overall_score, d.overall_score)),
        scoreBadgeOrBlank(d.llm_judge_overall_score),
        scoreBadgeOrBlank(d.overall_score),
        passFailBadge(d.pass_fail),
        d.llm_judge_reason || d.judge_reason,
      ])
    )}
  ` : emptyState("선택 가능한 질문이 없습니다."));

  const grouped = aggregateBy(caseData, "source_type");
  setHtml("tagSummary", grouped.map((d) => `
    <div class="bar-row wide">
      <span>${escapeHtml(labelSource(d.key))}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${clamp(d.score, 0, 100)}%"></div></div>
      <strong>${d.score.toFixed(1)}</strong>
    </div>
  `).join(""));
}

function questionMatchesSearch(row, query) {
  return [
    row.question_id,
    row.question,
    row.model,
    row.version,
    row.answer_excerpt,
    row.llm_judge_reason,
    row.judge_reason,
  ].some((value) => String(value ?? "").toLowerCase().includes(query));
}

function renderGlobalSearch(caseData) {
  const modelSelect = document.getElementById("globalSearchModel");
  const resultTarget = document.getElementById("globalSearchResults");
  if (!resultTarget) return;
  const searchRows = cases.length ? cases : caseData;
  const models = matrixModels(searchRows);
  if (modelSelect) {
    const current = state.globalSearchModel;
    modelSelect.innerHTML = [
      `<option value="">전체 모델</option>`,
      ...models.map((model) => `<option value="${escapeHtml(model)}">${escapeHtml(modelLabelForVersion(model))}</option>`),
    ].join("");
    modelSelect.value = models.includes(current) ? current : "";
    state.globalSearchModel = modelSelect.value;
  }
  const query = state.globalSearch;
  const matchedRows = searchRows
    .filter((row) => !state.globalSearchModel || row.version === state.globalSearchModel)
    .filter((row) => {
      if (!query) return true;
      return [
        row.question_id,
        row.question,
        row.answer_excerpt,
        row.llm_judge_reason,
        row.judge_reason,
        row.static_reason,
        row.error_type,
        labelErrorType(row.error_type),
        row.llm_judge_conflict_reason,
        row.version,
        modelLabelForVersion(row.version),
      ].some((value) => String(value ?? "").toLowerCase().includes(query));
    })
    .sort((a, b) => Number(isFailureCell(b)) - Number(isFailureCell(a)) || caseOverallScore(a) - caseOverallScore(b));
  const rows = matchedRows.slice(0, 120);
  if (!query && !state.globalSearchModel) {
    resultTarget.innerHTML = emptyState("검색어를 입력하거나 모델을 선택하세요.");
    return;
  }
  resultTarget.innerHTML = rows.length ? `
    <div class="search-result-meta">총 ${matchedRows.length.toLocaleString()}개 중 ${rows.length.toLocaleString()}개 표시</div>
    <div class="case-list search-result-list">
      ${rows.map((row) => `
        <div class="case">
          <strong>${escapeHtml(row.question_id)} · ${escapeHtml(modelLabelForVersion(row.version))} · ${caseOverallScore(row).toFixed(1)} / 100</strong>
          <div class="case-badge-row">
            ${formatCell(scoreBadge(caseOverallScore(row)))}
            ${formatCell(passFailBadge(row.pass_fail))}
            ${formatCell(gateBadge(row.release_gate))}
            ${formatCell(errorBadge(row.error_type))}
          </div>
          <p>${escapeHtml(row.question)}</p>
          <p><b>응답:</b> ${escapeHtml(row.answer_excerpt || "-")}</p>
          <p><b>Judge:</b> ${escapeHtml(row.llm_judge_reason || row.judge_reason || row.static_reason || "-")}</p>
        </div>
      `).join("")}
    </div>
  ` : emptyState("검색 결과가 없습니다.");
}

function groupCount(items, key) {
  const map = new Map();
  items.forEach((item) => map.set(item[key], (map.get(item[key]) ?? 0) + 1));
  return [...map.entries()].map(([entryKey, count]) => ({ key: entryKey, count })).sort((a, b) => b.count - a.count);
}

function countBy(items, key) {
  const counts = {};
  items.forEach((item) => {
    const value = valueOrUnknown(item[key]);
    counts[value] = (counts[value] ?? 0) + 1;
  });
  return counts;
}

function isTrue(value) {
  return String(value ?? "").toLowerCase() === "true";
}

function isFalse(value) {
  return ["false", "0", "no", "off", "none", "null", "n/a", "na"].includes(String(value ?? "").trim().toLowerCase());
}

function reviewPriorityRank(row) {
  if (row.release_gate === "block" || row.error_type === "unsafe_completion" || row.error_type === "hallucinated_policy") return 0;
  if (row.llm_judge_unresolved_conflict) return 1;
  if (isFailureCell(row) || row.llm_judge_status === "error") return 1;
  return 2;
}

function reviewPriorityLabel(row) {
  return ["높음", "보통", "낮음"][reviewPriorityRank(row)] || "낮음";
}

function suggestedReviewAction(row) {
  if (!isTrue(row.gold_verified)) return "모범답안 승인/수정";
  if (row.llm_judge_unresolved_conflict) return "중재 Judge 포함 수동 검토";
  if (row.llm_judge_status === "error") return "Judge 재실행";
  if (isFailureCell(row)) return "실패 원인 확인";
  return "승인";
}

function matrixKeysByCount(items, key) {
  return Object.entries(countBy(items, key))
    .sort(([leftValue, leftCount], [rightValue, rightCount]) => {
      if (leftValue === "unknown" && rightValue !== "unknown") return 1;
      if (rightValue === "unknown" && leftValue !== "unknown") return -1;
      if (rightCount !== leftCount) return rightCount - leftCount;
      return leftValue.localeCompare(rightValue);
    })
    .map(([value]) => value);
}

function aggregateBy(items, key) {
  const map = new Map();
  items.forEach((item) => {
    if (!map.has(item[key])) map.set(item[key], []);
    map.get(item[key]).push(item);
  });

  return [...map.entries()].map(([entryKey, rows]) => {
    const score = rows.reduce((sum, row) => sum + caseOverallScore(row), 0) / rows.length;
    return { key: entryKey, score };
  }).sort((a, b) => a.score - b.score);
}

function aggregateScoreRows(items, key) {
  const map = new Map();
  items.forEach((item) => {
    const entryKey = valueOrUnknown(item[key]);
    if (!map.has(entryKey)) map.set(entryKey, []);
    map.get(entryKey).push(item);
  });

  return [...map.entries()].map(([entryKey, rows]) => {
    const score = rows.reduce((sum, row) => sum + caseOverallScore(row), 0) / Math.max(rows.length, 1);
    const passRate = rows.filter((row) => !isFailureCell(row)).length / Math.max(rows.length, 1);
    const caseCount = new Set(rows.map((row) => row.question_id)).size;
    return { key: entryKey, rows, score, passRate, caseCount };
  });
}

function averageMetric(row) {
  const keys = row.utl_applicable ? metricCols : metricCols.filter((key) => key !== "utl");
  const raw = keys.reduce((acc, key) => acc + Number(row[key] || 0), 0);
  return keys.length ? (raw / (keys.length * 20)) * 100 : 0;
}

function caseOverallScore(row) {
  return Number(row.overall_score || 0) || averageMetric(row);
}

function badgeCell(label, tone = "", title = "") {
  const text = String(label ?? "").trim() || "-";
  const classes = ["ui-badge", tone].filter(Boolean).join(" ");
  return {
    [rawHtml]: true,
    value: `<span class="${escapeHtml(classes)}" title="${escapeHtml(title || text)}">${escapeHtml(text)}</span>`,
  };
}

function scoreBadge(value, maxScore = 100) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return badgeCell("N/A", "muted");
  const percent = clamp((numeric / Math.max(Number(maxScore) || 1, 1)) * 100, 0, 100);
  const tone = percent >= 80 ? "pass" : percent >= 60 ? "review" : "fail";
  const suffix = maxScore === 100 ? "점" : `/${maxScore}`;
  return {
    [rawHtml]: true,
    value: `<span class="ui-badge score ${tone}" title="${escapeHtml(`${numeric.toFixed(1)} / ${maxScore}`)}"><b style="width:${percent}%"></b>${escapeHtml(numeric.toFixed(1))}${escapeHtml(suffix)}</span>`,
  };
}

function firstPresentValue(...values) {
  return values.find((value) => value !== undefined && value !== null && String(value).trim() !== "");
}

function scoreBadgeOrBlank(value, maxScore = 100) {
  return value === undefined || value === null || String(value).trim() === "" ? "" : scoreBadge(value, maxScore);
}

function passFailBadge(value) {
  if (!value) return badgeCell("-", "muted");
  const isPass = value === "Pass";
  return badgeCell(passFailLabel(value), isPass ? "pass" : "fail", value || "");
}

function gateBadge(value) {
  const gate = String(value || "");
  const tone = gate === "block" ? "block" : gate === "review" ? "review" : gate === "pass" ? "pass" : "muted";
  return badgeCell(gateLabel(gate), tone, gate || gateLabel(gate));
}

function errorBadge(value) {
  const key = canonicalErrorType(value);
  const label = labelErrorType(key);
  const tone = key === "normal"
    ? "muted"
    : /unsafe|privacy|policy|hallucinated|critical|off_topic/.test(key)
      ? "block"
      : /unsupported|inaccuracy|missing|conflict|judge/.test(key)
        ? "review"
        : "fail";
  return badgeCell(label, tone, key);
}

function reviewPriorityBadge(row) {
  const rank = reviewPriorityRank(row);
  return badgeCell(reviewPriorityLabel(row), rank === 0 ? "block" : rank === 1 ? "review" : "muted");
}

function booleanBadge(value, trueLabel = "예", falseLabel = "아니오") {
  return badgeCell(value ? trueLabel : falseLabel, value ? "pass" : "muted");
}

function modelCell(version, fallbackModel = "") {
  const info = modelFamilyInfo(version, fallbackModel);
  const title = info.label || fallbackModel || version || "-";
  return {
    [rawHtml]: true,
    value: `
      <span class="table-model-cell" style="${escapeHtml(modelFamilyStyle(info))}" title="${escapeHtml(title)}">
        <b class="model-family-dot" aria-hidden="true"></b>
        <span>${escapeHtml(info.compactLabel || title)}</span>
        <em>${escapeHtml([info.familyLabel, info.paramLabel, info.quantLabel].filter(Boolean).join(" · "))}</em>
      </span>
    `,
  };
}

function status(value) {
  return passFailBadge(value);
}

function passFailLabel(value) {
  return {
    Pass: "통과",
    Fail: "실패",
  }[value] || value || "-";
}

function table(headers, rows) {
  return `
    <div class="table-wrap">
      <table>
        <thead><tr>${headers.map((h) => `<th>${escapeHtml(h)}</th>`).join("")}</tr></thead>
        <tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td${cellTitle(cell) ? ` title="${escapeHtml(cellTitle(cell))}"` : ""}>${formatCell(cell)}</td>`).join("")}</tr>`).join("")}</tbody>
      </table>
    </div>
  `;
}

function formatCell(cell) {
  return cell && cell[rawHtml] ? cell.value : escapeHtml(cell);
}

function cellTitle(cell) {
  return cell && cell[rawHtml] ? "" : String(cell ?? "");
}

function tableText(value, className = "") {
  const text = String(value ?? "");
  return {
    [rawHtml]: true,
    value: `<span class="${escapeHtml(className)}" title="${escapeHtml(text)}">${escapeHtml(text)}</span>`,
  };
}

function displayPath(value) {
  return String(value ?? "").replace(/\\/g, "/");
}

function bindThreshold() {
  const threshold = document.getElementById("threshold");
  if (!threshold) return;
  threshold.oninput = () => {
    state.threshold = Number(threshold.value);
    const label = document.getElementById("thresholdValue");
    if (label) label.textContent = threshold.value;
    renderAll();
  };
}

function releaseRank(value) {
  return { block: 0, review: 1, pass: 2, not_applicable: 3, "": 4 }[value] ?? 4;
}

function gateLabel(value) {
  return {
    block: "차단",
    review: "검토 필요",
    pass: "통과",
    not_applicable: "판정 제외",
  }[value] || "-";
}

function formatPercent(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${(number * 100).toFixed(1)}%` : "N/A";
}

function releaseDecisionReason(value) {
  const text = String(value || "").trim();
  if (!text) return "-";
  const parts = text.split(";").map((part) => part.trim()).filter(Boolean);
  const labels = {
    no_active_gold_cases: "배포 판정용으로 확정된 골든 케이스가 없음",
    "no gate-eligible cases": "배포 판정 대상 문항이 없음",
    pass: "배포 기준 통과",
    review: "수동 검토 필요",
    block: "배포 보류 기준에 걸림",
  };
  return parts.map((part) => labels[part] || part).join(" / ");
}

function labelSeverity(value) {
  return severityLabels[value] ?? valueOrUnknown(value);
}

function labelSource(value) {
  return sourceLabels[value] ?? valueOrUnknown(value);
}

function labelTopic(value) {
  return valueOrUnknown(value);
}

function labelErrorType(value) {
  const key = canonicalErrorType(value);
  return errorTypeLabels[key] ?? valueOrUnknown(value);
}

function failureErrorType(row) {
  const key = canonicalErrorType(row?.error_type);
  if (!isFailureCell(row)) return key;
  if (key === "normal") return "partial_inaccuracy";
  if (key === "ungrounded_answer" || key === "evidence_context_echo") return "unsupported_claim";
  return key;
}

function labelQuestionType(value) {
  return valueOrUnknown(value);
}

function labelTaskType(value) {
  const text = String(value ?? "").trim();
  const compact = text.toLowerCase().replace(/[\s_-]+/g, "");
  if (!text) return "단일추론(사실추출)";
  if (finalQuestionTypes.includes(text)) return text;
  if (includesAny(compact, ["groundedqa", "qa", "fact", "single"])) return "단일추론(사실추출)";
  if (includesAny(compact, ["comparison", "compare"])) return "비교대조";
  if (includesAny(compact, ["multihop", "complex"])) return "복합추론";
  if (includesAny(compact, ["numeric", "calculation"])) return "수치추론/계산";
  if (includesAny(compact, ["safety", "refusal", "sensitive"])) return "민감";
  if (includesAny(compact, ["format"])) return "형식 제한 QA";
  if (includesAny(compact, ["toolagent", "tool"])) return "툴 사용";
  if (includesAny(compact, ["clarification"])) return "추가 확인";
  return text;
}

function includesAny(text, tokens) {
  return tokens.some((token) => text.includes(token));
}

function canonicalQaCategory(value) {
  const text = String(value ?? "").trim();
  const compact = text.toLowerCase().replace(/\s+/g, "");
  if (includesAny(compact, ["card_product", "card_qa", "\uce74\ub4dc\uc0c1\ud488", "\uce74\ub4dc/\uc0c1\ud488"])) return "\uce74\ub4dc\uc0c1\ud488";
  if (includesAny(compact, ["internal", "inhouse", "company_faq", "bcfaq", "html_seed"])) return "BC FAQ";
  if (includesAny(compact, ["financial", "finance", "regression", "general", "hard_negative", "hardnegative", "edge_case", "edgecase", "\uae08\uc735\uc815\ubcf4", "financial_qa", "financial_faq"])) return "\uae08\uc735\uc815\ubcf4";
  if (compact.includes("faq")) return "BC FAQ";
  return text || "\uae08\uc735\uc815\ubcf4";
}

function canonicalErrorType(value) {
  const text = String(value ?? "").trim();
  if (!text) return "normal";
  const compact = text.toLowerCase().replace(/[\s-]+/g, "_").replace(/^_+|_+$/g, "");
  const alias = errorTypeAliases[text] || errorTypeAliases[compact];
  if (alias) return alias;
  if (errorTypeLabels[compact]) return compact;
  return "partial_inaccuracy";
}

function canonicalQuestionType(value) {
  const text = String(value ?? "").trim();
  const compact = text.toLowerCase().replace(/\s+/g, "");
  if (includesAny(compact, ["\ubbfc\uac10", "sensitive"])) return "\ubbfc\uac10";
  if (includesAny(compact, ["\uc218\uce58", "numerical", "numeric", "calculation", "\uacc4\uc0b0"])) return "\uc218\uce58\ucd94\ub860/\uacc4\uc0b0";
  if (includesAny(compact, ["\ubcf5\ud569", "multi-hop", "multihop"])) return "\ubcf5\ud569\ucd94\ub860";
  if (includesAny(compact, ["\ube44\uad50", "comparison", "compare", "\ub300\uc870"])) return "\ube44\uad50\ub300\uc870";
  if (includesAny(compact, ["\ub2e8\uc77c", "\uc0ac\uc2e4", "single", "single-hop", "singlehop", "fact"])) return "\ub2e8\uc77c\ucd94\ub860(\uc0ac\uc2e4\ucd94\ucd9c)";
  return text || "\ub2e8\uc77c\ucd94\ub860(\uc0ac\uc2e4\ucd94\ucd9c)";
}

function canonicalQaTopic(category, value) {
  const text = String(value ?? "").trim();
  const compact = text.toLowerCase().replace(/\s+/g, "");
  if (category === "BC FAQ" || includesAny(compact, ["bcfaq", "faq"])) return "BC FAQ";
  if (includesAny(compact, ["\uce74\ub4dc/\uacb0\uc81c", "\uce74\ub4dc\uacb0\uc81c", "\uce74\ub4dc\ubc0f\uacb0\uc81c", "card", "payment", "\uacb0\uc81c", "\uce74\ub4dc"])) return "\uce74\ub4dc/\uacb0\uc81c";
  if (includesAny(compact, ["\ub300\ucd9c/\uc5ec\uc2e0", "\ub300\ucd9c", "\uc5ec\uc2e0", "loan", "credit"])) return "\ub300\ucd9c/\uc5ec\uc2e0";
  if (includesAny(compact, ["\uc608\uc801\uae08", "\uc608/\uc801\uae08", "\uc608\uae08", "\uc801\uae08", "deposit", "savings"])) return "\uc608\uc801\uae08";
  if (includesAny(compact, ["\ud22c\uc790/\ud380\ub4dc", "\ud22c\uc790", "\ud380\ub4dc", "investment", "fund"])) return "\ud22c\uc790/\ud380\ub4dc";
  if (category === "\uce74\ub4dc\uc0c1\ud488") return "\uce74\ub4dc/\uacb0\uc81c";
  return "\uc77c\ubc18 \uae08\uc735";
}

function valueOrUnknown(value) {
  const text = String(value ?? "").trim();
  return text || "unknown";
}

function unique(values) {
  return [...new Set(values.map(valueOrUnknown))].filter(Boolean);
}

function shortLabel(value, maxLength) {
  const text = String(value ?? "");
  return text.length > maxLength ? `${text.slice(0, maxLength - 3)}...` : text;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function emptyState(message) {
  return `<p class="empty-state">${escapeHtml(message)}</p>`;
}

function renderLoadError(error) {
  setHtml("kpis", emptyState(`데이터를 불러오지 못했습니다. ${error.message}`));
}

function setHtml(id, html) {
  const element = document.getElementById(id);
  if (element) element.innerHTML = html;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
