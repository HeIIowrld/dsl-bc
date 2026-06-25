from __future__ import annotations

import csv
import base64
import gzip
import hashlib
import ipaddress
import io
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import uuid
from collections import Counter, defaultdict
from email.utils import formatdate
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from datetime import datetime
from urllib import error as urlerror
from urllib import request as urlrequest
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
DOTENV_PATH = PROJECT_ROOT / ".env"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.eval.compose_eval_dataset import (  # noqa: E402
    compose_dataset,
    write_jsonl as write_composed_jsonl,
)
from scripts.eval.eval_dataset_catalog import (  # noqa: E402
    build_runtime_eval_dataset_catalog,
    dataset_id_matches_role as runtime_dataset_id_matches_role,
    load_config as load_eval_catalog_config,
    load_question_dataset_settings as runtime_load_question_dataset_settings,
    question_dataset_defaults as runtime_question_dataset_defaults,
    question_dataset_pool_quota as runtime_question_dataset_pool_quota,
    question_dataset_pool_specs as runtime_question_dataset_pool_specs,
    write_question_dataset_settings as runtime_write_question_dataset_settings,
)
from scripts.eval.run_multi_model_eval import (  # noqa: E402
    DEFAULT_REFUSAL_KEYWORDS,
    SCORE_METRIC_KEYS,
    aggregate_llm_judge_scores as eval_aggregate_llm_judge_scores,
    aggregate_release_gates as eval_aggregate_release_gates,
    aggregate_runs as eval_aggregate_runs,
    anthropic_chat_url,
    anthropic_payload,
    apply_llm_judge as eval_apply_llm_judge,
    attach_static_score_fields as eval_attach_static_score_fields,
    build_regression_diff as eval_build_regression_diff,
    canonical_error_type as eval_canonical_error_type,
    clova_chat_url,
    clova_payload,
    export_final_ui as eval_export_final_ui,
    gemini_chat_url,
    gemini_payload,
    metric_keys_for_score as eval_metric_keys_for_score,
    openai_chat_url,
    openai_responses_url,
    qa_slice_score_rows as eval_qa_slice_score_rows,
    question_case_rows as eval_question_case_rows,
    raw_metric_score as eval_raw_metric_score,
    read_cases_path as eval_read_cases_path,
    read_jsonl as eval_read_jsonl,
    safe_filename as eval_safe_filename,
    score_denominator as eval_score_denominator,
    score_output as eval_score_output,
    score_total_from_metrics as eval_score_total_from_metrics,
    write_csv as eval_write_csv,
    write_html_report as eval_write_html_report,
    write_jsonl as eval_write_jsonl,
    write_partitioned_eval_artifacts as eval_write_partitioned_eval_artifacts,
    write_xlsx as eval_write_xlsx,
)

REGISTERED_TARGET_MODELS_PATH = ROOT / "data" / "registered_target_models.json"
REGISTERED_JUDGE_MODELS_PATH = ROOT / "data" / "registered_judge_models.json"
JUDGE_API_PRESETS_PATH = ROOT / "data" / "judge_api_presets.json"
SERVER_API_SECRETS_PATH = ROOT / "data" / "server_api_secrets.json"
QUESTION_DATASET_SETTINGS_PATH = ROOT / "data" / "question_dataset_settings.json"
SEEDED_TARGET_MODELS_PATH = PROJECT_ROOT / "config" / "seeded_target_models.yaml"
EVAL_DATASET_CATALOG_PATH = PROJECT_ROOT / "config" / "eval_dataset_catalog.yaml"
EVAL_RUNS_ROOT = PROJECT_ROOT / "out" / "eval_runs"
EVAL_ARCHIVE_ROOT = EVAL_RUNS_ROOT / "archive"
WEB_JOBS_ROOT = EVAL_ARCHIVE_ROOT / "web_jobs"
CURRENT_UI_DATA_RUN_ID = "__ui_runtime_data__"
LEGACY_UI_DATA_RUN_ID = "__final_ui_data__"
CURRENT_UI_DATA_RUN_ALIASES = {CURRENT_UI_DATA_RUN_ID, LEGACY_UI_DATA_RUN_ID}
CURRENT_UI_DATA_LABEL = "현재 내보낸 전체 결과"
BENCHMARK_CSV_ROOT = PROJECT_ROOT / "questionlist" / "benchmark"
REGRESSION_CSV_ROOT = PROJECT_ROOT / "questionlist" / "regression"
USER_UPLOAD_CSV_ROOT = PROJECT_ROOT / "questionlist" / "user_uploads"
FINAL_BENCHMARK_CASES_PATH = BENCHMARK_CSV_ROOT / "benchmark_dataset_test.csv"
FINAL_REGRESSION_CASES_PATH = REGRESSION_CSV_ROOT / "regression_golden_set.csv"
FINAL_QUESTION_SET_SUMMARY_PATH = PROJECT_ROOT / "questionlist" / "question_sets.summary.json"
QUESTIONLIST_CASES_PATH = FINAL_BENCHMARK_CASES_PATH
QUESTIONLIST_SUMMARY_PATH = FINAL_QUESTION_SET_SUMMARY_PATH
QUESTIONLIST_SOURCE_PATH = FINAL_BENCHMARK_CASES_PATH
QUESTIONLIST_DATASET_FILES: dict[str, Path] = {}
QUESTIONLIST_CSV_DIRS = [
    BENCHMARK_CSV_ROOT,
    REGRESSION_CSV_ROOT,
    USER_UPLOAD_CSV_ROOT / "benchmark",
    USER_UPLOAD_CSV_ROOT / "regression",
]

def is_current_ui_data_run_id(run_id: str) -> bool:
    return str(run_id or "").strip() in CURRENT_UI_DATA_RUN_ALIASES
EXCLUDED_DATASET_PATH_MARKERS = (
    "_unused_files",
    "archive",
    "backup",
    "tmp",
    "draft",
    "cleanup",
)
EXCLUDED_DATASET_NAME_TOKENS = ("old",)
ACTIVE_RUN_PATHS = [
    ROOT / "data" / "active_run.json",
    EVAL_RUNS_ROOT / "active_run.json",
]
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://afsd.iptime.org:11434").rstrip("/")
MODEL_HEALTH_TIMEOUT_SECONDS = float(os.environ.get("MODEL_HEALTH_TIMEOUT_SECONDS", "8"))
MODEL_LIVE_HEALTH_TIMEOUT_SECONDS = float(os.environ.get("MODEL_LIVE_HEALTH_TIMEOUT_SECONDS", "180"))
MAX_JSON_BODY_BYTES = int(os.environ.get("FINAL_UI_MAX_JSON_BODY_BYTES", str(8 * 1024 * 1024)))
RUN_EXCLUDE_MARKERS = ("SMOKE", "DEBUG", "TEST")
RESERVED_EVAL_RUN_NAMES = {"archive", "_answer_cache", "_judge_cache", "_archive_fragments_20260526", "_archive_fragments_20260527", "_judge_jobs"}
MIN_DISPLAY_QUESTIONS = 10
EMPTY_LATEST_RUN_CSV = {
    "eval_runs.csv": "run_id,model,version,run_type,eval_date,eval_started_at,total_questions,scored_questions,review_pending_count,pass_rate,overall_score,scored_pass_rate,scored_average,acc,com,nac,hal,hal_rate,hal_pass,answer_quality_score,rag_quality_score,avg_latency_ms,avg_cost_krw,score_schema\n",
    "question_cases.csv": "question_id,qa_category,question_type,qa_topic,instruction,output,ground_truth_doc,source_type,expected_behavior,selection_mode,regression_suite,metamorphic_relation,dataset_pool_id,dataset_role,gate_eligible,release_gate_eligible,case_status,gold_verified,human_review_required,case_source,dataset_version,qa_matrix_topic,benchmark_group,source_hash,source_title,source_url,priority,task_type,model,version,answer_excerpt,model_answer,acc,com,nac,hal,hal_rate,hal_pass,applicable_metrics,score_denominator,raw_metric_score,canonical_metric_count,answer_quality_score,rag_quality_score,overall_score,pass_fail,score_schema,score_scale,metric_source_hal,scoring_mode,static_overall_score,static_pass_fail,llm_judge_count,llm_judge_overall_score,llm_judge_pass_fail,llm_judge_status,llm_judge_provider,llm_judge_model,llm_judge_prompt_version,llm_judge_prompt_hash,llm_judge_prompt_preset,llm_judge_hal_pass,llm_judge_omnieval_accuracy,llm_judge_omnieval_completeness,llm_judge_omnieval_numerical_accuracy,llm_judge_omnieval_hallucination,llm_judge_omnieval_scores,llm_judge_applicable_metrics,llm_judge_scores,llm_judge_individual_scores,llm_judge_conflict,llm_judge_conflict_detected,llm_judge_unresolved_conflict,llm_judge_conflict_reason,llm_judge_conflict_resolution_policy,llm_judge_arbiter_config_id,llm_judge_arbitration_status,llm_judge_provider_refused,llm_judge_provider_refusal_reason,llm_judge_sanitized_eval,llm_judge_score_gap,llm_judge_score_min,llm_judge_score_max,llm_judge_pass_mismatch,llm_judge_base_average_score,llm_judge_arbiter_score,llm_judge_arbiter_override,regression_delta,regression_type,release_gate,error_type,judge_reason,static_reason,llm_judge_reason,metric_source_acc,metric_source_com,metric_source_nac\n",
    "qa_slice_scores.csv": "version,model,slice_level,slice_dimension,slice_value,case_count,row_count,min_reliable_cases,reliability_status,pass_rate,overall_score,acc,com,nac,hal,hal_rate,hal_pass,score_schema\n",
    "run_release_gates.csv": "run_id,config_id,model,release_gate,total_cases,evaluated_cases,gate_eligible_cases,pass_count,review_count,block_count,critical_fail_count,pass_rate,core_pass_rate,core_pass_rate_min,reason\n",
    "regression_diff.csv": "question_id,version,baseline_version,overall_score,baseline_overall_score,delta,regression_type\n",
}
ALLOWED_PROVIDERS = {
    "ollama",
    "openai_native",
    "openai_compatible",
    "generic_api",
    "clova_studio",
    "anthropic",
    "gemini",
    "local_path",
}


def eval_runner_python() -> str:
    override = os.environ.get("EVAL_RUNNER_PYTHON", "").strip()
    candidate_cmds: list[list[str]] = []
    if override:
        candidate_cmds.append([override])
    if os.name == "nt":
        candidate_cmds.extend([["py", "-3.11"], ["py", "-3"]])
    candidate_cmds.extend([[sys.executable], ["python"]])

    fallback = sys.executable
    probe = "import platform,sys; print(sys.executable); print(platform.architecture()[0])"
    for candidate in candidate_cmds:
        try:
            completed = subprocess.run(
                [*candidate, "-c", probe],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if completed.returncode != 0:
            continue
        lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        executable = lines[0] if lines else candidate[0]
        arch = lines[1].lower() if len(lines) > 1 else ""
        if override or os.name != "nt" or "64" in arch:
            return executable
        fallback = executable or fallback
    return fallback


EVAL_JOBS: dict[str, dict] = {}
EVAL_JOBS_LOCK = threading.Lock()
CASE_SUMMARY_CACHE: dict[tuple[str, str, int, int], dict] = {}
CASE_SUMMARY_CACHE_LOCK = threading.Lock()
PROJECTED_RUN_TABLES_CACHE: dict[tuple, dict] = {}
PROJECTED_RUN_TABLES_CACHE_LOCK = threading.Lock()
PROJECTED_RUN_TABLES_CACHE_MAX = 4
JUDGE_SCORE_RUN_SUMMARY_CACHE: dict[tuple, dict] = {}
JUDGE_SCORE_RUN_SUMMARY_CACHE_LOCK = threading.Lock()
JUDGE_SCORE_RUN_SUMMARY_CACHE_MAX = 16
QUESTION_CASES_JUDGE_COUNTS_CACHE: dict[tuple, tuple[Counter, int]] = {}
QUESTION_CASES_JUDGE_COUNTS_CACHE_LOCK = threading.Lock()
QUESTION_CASES_JUDGE_COUNTS_CACHE_MAX = 8
UI_CASE_SUMMARY_CACHE_VERSION = 8
UI_CASE_SUMMARY_CACHE_ROOT = PROJECT_ROOT / "out" / "final_ui_cache" / "case_summary"
UI_CASE_SUMMARY_MEMORY_CACHE: dict[str, dict] = {}
UI_CASE_SUMMARY_CACHE_LOCK = threading.Lock()
UI_CASE_SUMMARY_MEMORY_CACHE_MAX = 4
UI_CASE_SUMMARY_FIELDS = (
    "question_id",
    "source_type",
    "question_type",
    "qa_matrix_topic",
    "instruction",
    "output",
    "ground_truth_doc",
    "source_title",
    "scenario_tag",
    "difficulty",
    "regression_suite",
    "dataset_pool_id",
    "dataset_role",
    "gate_eligible",
    "release_gate_eligible",
    "case_status",
    "gold_verified",
    "human_review_required",
    "case_source",
    "dataset_version",
    "benchmark_group",
    "task_type",
    "model",
    "version",
    "answer_excerpt",
    "acc",
    "com",
    "nac",
    "hal",
    "hal_rate",
    "hal_pass",
    "applicable_metrics",
    "score_denominator",
    "raw_metric_score",
    "answer_quality_score",
    "rag_quality_score",
    "overall_score",
    "pass_fail",
    "score_schema",
    "score_scale",
    "scoring_mode",
    "static_overall_score",
    "llm_judge_count",
    "llm_judge_overall_score",
    "llm_judge_hal_pass",
    "llm_judge_pass_fail",
    "llm_judge_status",
    "llm_judge_config_id",
    "llm_judge_provider",
    "llm_judge_model",
    "judge_config_id",
    "judge_provider",
    "judge_model",
    "llm_judge_conflict",
    "llm_judge_conflict_detected",
    "llm_judge_unresolved_conflict",
    "llm_judge_conflict_reason",
    "llm_judge_conflict_resolution_policy",
    "llm_judge_arbiter_config_id",
    "llm_judge_score_gap",
    "llm_judge_score_min",
    "llm_judge_score_max",
    "llm_judge_pass_mismatch",
    "llm_judge_arbiter_score",
    "llm_judge_arbiter_override",
    "regression_delta",
    "regression_type",
    "release_gate",
    "error_type",
    "static_error_type",
    "llm_judge_error_type",
    "judge_reason",
    "static_reason",
    "llm_judge_reason",
)
UI_CASE_SUMMARY_NUMERIC_FIELDS = {
    "acc",
    "com",
    "nac",
    "hal",
    "hal_rate",
    "hal_pass",
    "score_denominator",
    "raw_metric_score",
    "answer_quality_score",
    "rag_quality_score",
    "overall_score",
    "static_overall_score",
    "llm_judge_count",
    "llm_judge_overall_score",
    "llm_judge_hal_pass",
    "llm_judge_score_gap",
    "llm_judge_score_min",
    "llm_judge_score_max",
    "llm_judge_arbiter_score",
    "regression_delta",
}
UI_CASE_SUMMARY_TEXT_LIMITS = {
    "instruction": 260,
    "output": 260,
    "ground_truth_doc": 180,
    "source_title": 180,
    "answer_excerpt": 320,
    "judge_reason": 320,
    "static_reason": 320,
    "llm_judge_reason": 420,
    "llm_judge_conflict_reason": 260,
}
PROVIDER_ENV_ALIASES = {
    "ollama": {"base_url": ["OLLAMA_BASE_URL"]},
    "clova_studio": {
        "api_key": ["clova_api_key", "CLOVA_STUDIO_API_KEY"],
        "base_url": ["clova_api_url", "CLOVA_STUDIO_API_URL"],
    },
    "openai_native": {
        "api_key": ["openai_api_key", "OPENAI_API_KEY"],
        "base_url": ["openai_responses_url", "OPENAI_RESPONSES_URL", "OPENAI_BASE_URL", "openai_api_url"],
    },
    "openai_compatible": {
        "api_key": ["openai_api_key", "OPENAI_API_KEY"],
        "base_url": ["openai_api_url", "OPENAI_BASE_URL"],
    },
    "gemini": {"api_key": ["gemini_api_key", "GEMINI_API_KEY"], "base_url": ["gemini_api_url", "GEMINI_API_URL"]},
    "anthropic": {"api_key": ["anthropic_api_key", "ANTHROPIC_API_KEY"], "base_url": ["anthropic_api_url", "ANTHROPIC_API_URL"]},
}


def load_dotenv(path: Path = DOTENV_PATH) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name and name not in os.environ:
            os.environ[name] = value


load_dotenv()


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name, "")
    if not raw:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def parse_auth_users(raw: str) -> dict[str, dict[str, str]]:
    users: dict[str, dict[str, str]] = {}
    for item in re.split(r"[,\n;]+", raw or ""):
        item = item.strip()
        if not item:
            continue
        parts = item.split(":", 2)
        if len(parts) == 2:
            username, password = parts
            role = "user"
        elif len(parts) == 3:
            username, password, role = parts
        else:
            continue
        username = username.strip()
        password = password.strip()
        role = role.strip().lower()
        if username and password and role in {"admin", "user"}:
            users[username] = {"password": password, "role": role}
    return users


DEFAULT_FINAL_UI_AUTH_USERS_RAW = "admin:admin:admin,user:user:user"

FINAL_UI_AUTH_TOKEN = (
    os.environ.get("FINAL_UI_AUTH_TOKEN", "").strip()
    or os.environ.get("FINAL_UI_ADMIN_TOKEN", "").strip()
)
FINAL_UI_AUTH_USERS_RAW = os.environ.get("FINAL_UI_AUTH_USERS")
FINAL_UI_AUTH_USERS = parse_auth_users(
    FINAL_UI_AUTH_USERS_RAW
    if FINAL_UI_AUTH_USERS_RAW is not None and FINAL_UI_AUTH_USERS_RAW.strip()
    else DEFAULT_FINAL_UI_AUTH_USERS_RAW
)
FINAL_UI_AUTH_USERS_SOURCE = "env" if FINAL_UI_AUTH_USERS_RAW is not None and FINAL_UI_AUTH_USERS_RAW.strip() else "default"
FINAL_UI_AUTH_DISABLED = env_flag("FINAL_UI_AUTH_DISABLED", default=False)
PUBLIC_BIND_HOSTS = {"", "0.0.0.0", "::", "[::]"}
AUTH_ROLE_RANK = {"user": 1, "admin": 2}
ACCESS_LOG_PATH = ROOT / "data" / "access_log.jsonl"
ACCESS_LOG_LOCK = threading.Lock()
ACCESS_LOG_MAX_BYTES = int(os.environ.get("FINAL_UI_ACCESS_LOG_MAX_BYTES", str(512 * 1024)))
ACCESS_LOG_KEEP_LINES = int(os.environ.get("FINAL_UI_ACCESS_LOG_KEEP_LINES", "2000"))
LOCAL_PROXY_CIDRS = (
    "127.0.0.0/8",
    "::1/128",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "169.254.0.0/16",
    "fc00::/7",
    "fe80::/10",
)
CLOUDFLARE_PROXY_CIDRS = (
    "173.245.48.0/20",
    "103.21.244.0/22",
    "103.22.200.0/22",
    "103.31.4.0/22",
    "141.101.64.0/18",
    "108.162.192.0/18",
    "190.93.240.0/20",
    "188.114.96.0/20",
    "197.234.240.0/22",
    "198.41.128.0/17",
    "162.158.0.0/15",
    "104.16.0.0/13",
    "104.24.0.0/14",
    "172.64.0.0/13",
    "131.0.72.0/22",
    "2400:cb00::/32",
    "2606:4700::/32",
    "2803:f800::/32",
    "2405:b500::/32",
    "2405:8100::/32",
    "2a06:98c0::/29",
    "2c0f:f248::/32",
)
LOCAL_PROXY_NETWORKS = tuple(ipaddress.ip_network(cidr) for cidr in LOCAL_PROXY_CIDRS)
CLOUDFLARE_PROXY_NETWORKS = tuple(ipaddress.ip_network(cidr) for cidr in CLOUDFLARE_PROXY_CIDRS)


def env_first(names: list[str]) -> tuple[str, str]:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value, name
    return "", names[0] if names else ""


def provider_env_value(config: dict, kind: str) -> tuple[str, str]:
    provider = str(config.get("provider") or "")
    explicit_name = str(config.get(f"{kind}_env") or "").strip()
    names = [explicit_name] if explicit_name else []
    names.extend(name for name in PROVIDER_ENV_ALIASES.get(provider, {}).get(kind, []) if name and name not in names)
    return env_first(names)
SOURCE_EXPECTED_BEHAVIORS = {
    "answer_from_source",
    "answer_from_source_with_json_format",
    "answer_from_sample_evidence",
    "answer_from_sample_evidence_without_pii",
}
REFUSAL_EXPECTED_BEHAVIORS = {
    "answer_not_supported_or_refuse",
    "abstain_when_unsupported",
    "refuse_unsafe_request",
}
FORMAT_EXPECTED_BEHAVIORS = {
    "answer_from_source_with_json_format",
    "structured_output_required",
}
TOOL_EXPECTED_BEHAVIORS = {
    "tool_call_then_grounded_answer",
    "tool_call_then_answer",
    "tool_result_synthesis",
    "tool_creation_and_use",
}
CLARIFICATION_EXPECTED_BEHAVIORS = {"ask_clarifying_question"}


def case_metadata(row: dict):
    return row.get("metadata") if isinstance(row.get("metadata"), dict) else {}


def text_value(*values):
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


CSV_QUESTION_FIELD_ALIASES = (
    "instruction",
    "question",
    "input",
    "prompt",
    "query",
    "user_question",
    "질문",
    "문제",
    "주관식 문제",
)
CSV_ANSWER_FIELD_ALIASES = (
    "output",
    "ground_truth",
    "answer",
    "gold_answer",
    "expected_answer",
    "expected_output",
    "reference_answer",
    "target_answer",
    "정답",
    "모범답안",
    "기준답변",
)
CSV_QA_CATEGORY_FIELD_ALIASES = ("qa_category", "category", "source_type", "topic", "대분류", "카테고리")
CSV_QA_TOPIC_FIELD_ALIASES = ("qa_topic", "qa_matrix_topic", "topic", "intent", "source_term", "금융토픽", "출처_용어")
CSV_QUESTION_TYPE_FIELD_ALIASES = ("question_type", "qtype", "type", "task_type", "문제유형", "질문유형")
CSV_FORBIDDEN_FIELD_ALIASES = (
    "forbidden_claims",
    "must_not_include",
    "hallucination_trap",
    "hallucination_trap(모델이 틀리기 쉬운 오답)",
    "오답_유형",
)
CSV_CASE_ID_FIELD_ALIASES = ("case_id", "id", "question_id", "qid")
CSV_ORDINAL_FIELD_ALIASES = ("no", "row_no", "번호")


def csv_row_value(row: dict, *aliases: str) -> str:
    normalized = {str(key or "").strip().lstrip("\ufeff").lower(): value for key, value in row.items()}
    for alias in aliases:
        key = str(alias or "").strip().lstrip("\ufeff")
        direct = text_value(row.get(key))
        if direct:
            return direct
        folded = key.lower()
        if folded in normalized:
            value = text_value(normalized.get(folded))
            if value:
                return value
    return ""


def canonical_qa_category(*values):
    text = " ".join(str(value or "") for value in values).lower()
    if any(token in text for token in ("card_product", "card_qa", "카드상품", "카드 상품")):
        return "카드상품"
    if any(token in text for token in ("internal", "inhouse", "company_faq", "bc_faq", "bc faq", "html_seed")):
        return "BC FAQ"
    if any(token in text for token in ("financial", "finance", "regression", "금융정보", "금융 정보", "financial_qa", "financial_faq")):
        return "금융정보"
    if "faq" in text:
        return "BC FAQ"
    return text_value(*values) or "금융정보"


def canonical_question_type(*values):
    text = " ".join(str(value or "") for value in values).lower()
    if any(token in text for token in ("민감", "sensitive")):
        return "민감"
    if any(token in text for token in ("수치", "numerical", "numeric", "calculation", "계산")):
        return "수치추론/계산"
    if any(token in text for token in ("복합", "multi-hop", "multihop", "multi hop")):
        return "복합추론"
    if any(token in text for token in ("비교", "comparison", "compare", "대조")):
        return "비교대조"
    if any(token in text for token in ("단일", "사실", "single", "single-hop", "single hop", "fact")):
        return "단일추론(사실추출)"
    return text_value(*values) or "단일추론(사실추출)"


def canonical_qa_topic(category: str, *values):
    text = " ".join(str(value or "") for value in values).lower().replace(" ", "")
    if any(token in text for token in ("카드/결제", "카드결제", "카드및결제", "card", "payment", "결제", "카드")):
        return "카드/결제"
    if any(token in text for token in ("대출/여신", "대출", "여신", "loan", "credit")):
        return "대출/여신"
    if any(token in text for token in ("예적금", "예/적금", "예금", "적금", "deposit", "savings")):
        return "예적금"
    if any(token in text for token in ("투자/펀드", "투자", "펀드", "investment", "fund")):
        return "투자/펀드"
    if category == "카드상품":
        return "카드/결제"
    return "일반 금융"


def optional_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().lower()
    if text in {"true", "1", "yes", "y", "verified", "eligible"}:
        return True
    if text in {"false", "0", "no", "n", "unverified", "not_eligible"}:
        return False
    return None


def dataset_case_status(row: dict):
    metadata = case_metadata(row)
    status = str(row.get("case_status") or metadata.get("case_status") or "").strip().lower()
    if status in {"draft", "shadow", "active", "deprecated"}:
        return status
    source_status = str(row.get("status") or metadata.get("status") or "").strip().lower()
    if source_status in {"shadow", "draft", "deprecated"}:
        return source_status
    if source_status in {"candidate", "generated"}:
        return "draft"
    if source_status == "active" and dataset_gold_verified(row):
        return "active"
    role = str(row.get("dataset_role") or metadata.get("dataset_role") or "").strip().lower()
    return "shadow" if role == "benchmark" else "shadow"


def dataset_gold_verified(row: dict):
    metadata = case_metadata(row)
    value = optional_bool(row.get("gold_verified"))
    if value is not None:
        return value
    value = optional_bool(metadata.get("gold_verified"))
    if value is not None:
        return value
    return False


def dataset_release_gate_eligible(row: dict):
    metadata = case_metadata(row)
    value = optional_bool(row.get("release_gate_eligible"))
    if value is None:
        value = optional_bool(metadata.get("release_gate_eligible"))
    if value is None:
        value = optional_bool(row.get("gate_eligible"))
    if value is None:
        value = optional_bool(metadata.get("gate_eligible"))
    if value is False:
        return False
    return bool(dataset_case_status(row) == "active" and dataset_gold_verified(row) and value is True)


def dataset_human_review_required(row: dict):
    metadata = case_metadata(row)
    value = optional_bool(row.get("human_review_required"))
    if value is None:
        value = optional_bool(metadata.get("human_review_required"))
    if value is not None:
        return value
    return dataset_case_status(row) in {"draft", "shadow"} or not dataset_gold_verified(row)


def case_expected_tool_calls(row: dict):
    if isinstance(row.get("expected_tool_calls"), list):
        return row.get("expected_tool_calls")
    if isinstance(row.get("expected_actions"), list):
        return row.get("expected_actions")
    return []


def case_format_requirements(row: dict):
    return row.get("format_requirements") if isinstance(row.get("format_requirements"), dict) else {}


def infer_expected_behavior(row: dict):
    metadata = case_metadata(row)
    behavior = str(row.get("expected_behavior") or metadata.get("expected_behavior") or "").strip()
    if behavior:
        return behavior
    stage_targets = row.get("stage_targets") if isinstance(row.get("stage_targets"), list) else []
    if "tool_creation" in stage_targets:
        return "tool_creation_and_use"
    if "tool_result_refinement" in stage_targets:
        return "tool_result_synthesis"
    if case_expected_tool_calls(row):
        return "tool_call_then_grounded_answer"
    if case_format_requirements(row) or str(metadata.get("expected_format") or "").lower().startswith("json"):
        return "structured_output_required"
    return ""


def infer_task_type(row: dict):
    metadata = case_metadata(row)
    behavior = infer_expected_behavior(row)
    if row.get("task_type"):
        return row.get("task_type")
    if case_expected_tool_calls(row) or behavior in TOOL_EXPECTED_BEHAVIORS:
        return "tool_agent"
    if behavior in REFUSAL_EXPECTED_BEHAVIORS:
        return "safety_refusal"
    if behavior in FORMAT_EXPECTED_BEHAVIORS:
        return "format_constrained_grounded_qa"
    if behavior in CLARIFICATION_EXPECTED_BEHAVIORS:
        return "clarification"
    return row.get("question_type") or metadata.get("question_type") or row.get("category") or "grounded_qa"


def first_evidence_for_case(row: dict):
    evidence = row.get("gold_evidence")
    if isinstance(evidence, list):
        return next((item for item in evidence if isinstance(item, dict)), {})
    if isinstance(evidence, str):
        return {
            "source_id": row.get("gold_evidence_doc_id") or row.get("expected_source_doc_id") or "",
            "title": row.get("gold_evidence_title") or row.get("source_title") or "",
            "url": row.get("gold_evidence_url") or row.get("source_url") or "",
            "excerpt": evidence,
        }
    return {}


class FinalUiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.current_actor = "anonymous"
        self.current_role = ""
        self.current_auth_scheme = ""
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def guess_type(self, path):
        content_type = super().guess_type(path)
        bare_type = content_type.split(";", 1)[0].lower()
        if bare_type in {"text/html", "text/css", "text/javascript", "application/javascript"}:
            return f"{bare_type}; charset=utf-8"
        return content_type

    def do_GET(self):
        if not self.require_read_auth():
            return
        parsed = urlparse(self.path)
        if parsed.path == "/api/auth/session":
            self.handle_auth_session()
            return
        if parsed.path == "/api/auth/access-log":
            self.handle_auth_access_log(parsed.query)
            return
        if parsed.path == "/favicon.ico":
            self.send_no_content()
            return
        if parsed.path == "/api/model-registry":
            self.handle_dynamic_model_registry()
            return
        if parsed.path == "/api/judge-api-presets":
            self.handle_judge_api_presets()
            return
        if parsed.path == "/api/server-api-secrets":
            self.handle_server_api_secrets()
            return
        if parsed.path.startswith("/api/models/"):
            self.handle_model_api(parsed.path, parsed.query)
            return
        if parsed.path == "/api/questionlist/summary":
            self.handle_questionlist_summary()
            return
        if parsed.path == "/api/questionlist/cases":
            self.handle_questionlist_cases(parsed.query)
            return
        if parsed.path == "/api/questionlist/datasets":
            self.handle_questionlist_datasets()
            return
        if parsed.path == "/api/questionlist/datasets/sample-csv":
            self.handle_question_dataset_sample_csv_download()
            return
        if parsed.path == "/api/questionlist/dataset-cases":
            self.handle_questionlist_dataset_cases(parsed.query)
            return
        if parsed.path == "/api/eval/catalog":
            self.handle_eval_catalog()
            return
        if parsed.path == "/api/eval/latest-run":
            self.handle_latest_run(parsed.query)
            return
        if parsed.path == "/api/eval/runs":
            self.handle_eval_runs()
            return
        if parsed.path == "/api/eval/case-summary":
            self.handle_eval_case_summary(parsed.query)
            return
        if parsed.path == "/api/eval/case-detail":
            self.handle_eval_case_detail(parsed.query)
            return
        if parsed.path == "/api/eval/judge-comparison/options":
            self.handle_judge_comparison_options()
            return
        if parsed.path == "/api/eval/judge-comparison/artifact":
            self.handle_judge_comparison_artifact(parsed.query)
            return
        if parsed.path == "/api/eval/jobs":
            self.handle_eval_jobs()
            return
        if parsed.path == "/api/eval/answers-template":
            self.handle_answers_template_download(parsed.query)
            return
        if parsed.path.startswith("/api/eval/jobs/"):
            self.handle_eval_job(unquote(parsed.path.rsplit("/", 1)[-1]))
            return
        if parsed.path in {
            "/data/eval_runs.csv",
            "/data/question_cases.csv",
            "/data/run_release_gates.csv",
            "/data/regression_diff.csv",
        }:
            self.handle_latest_run_file(parsed.path.rsplit("/", 1)[-1], parsed.query)
            return
        if parsed.path == "/report/regression_report.html":
            self.handle_latest_report(parsed.query)
            return
        if parsed.path == "/report/raw_regression_report.html":
            self.handle_raw_report(parsed.query)
            return
        super().do_GET()

    def do_HEAD(self):
        if not self.require_read_auth():
            return
        parsed = urlparse(self.path)
        if parsed.path == "/favicon.ico":
            self.send_no_content()
            return
        dynamic_paths = {
            "/api/auth/session",
            "/api/auth/access-log",
            "/api/model-registry",
            "/api/judge-api-presets",
            "/api/server-api-secrets",
            "/api/questionlist/summary",
            "/api/questionlist/cases",
            "/api/questionlist/datasets",
            "/api/questionlist/dataset-cases",
            "/api/eval/catalog",
            "/api/eval/latest-run",
            "/api/eval/runs",
            "/api/eval/case-summary",
            "/api/eval/case-detail",
            "/api/eval/judge-comparison/options",
            "/api/eval/judge-comparison/artifact",
            "/api/eval/jobs",
            "/api/eval/answers-template",
            "/data/eval_runs.csv",
            "/data/question_cases.csv",
            "/data/run_release_gates.csv",
            "/data/regression_diff.csv",
            "/report/regression_report.html",
            "/report/raw_regression_report.html",
        }
        is_dynamic = (
            parsed.path in dynamic_paths
            or parsed.path.startswith("/api/models/")
            or parsed.path.startswith("/api/eval/jobs/")
        )
        if not is_dynamic:
            super().do_HEAD()
            return
        self._head_only = True
        try:
            self.do_GET()
        finally:
            self._head_only = False

    def do_POST(self):
        parsed = urlparse(self.path)
        if not self.require_write_auth():
            return
        if parsed.path == "/api/model-registry":
            self.handle_save_model_registry_entry()
            return
        if parsed.path == "/api/judge-api-presets":
            self.handle_save_judge_api_preset()
            return
        if parsed.path == "/api/server-api-secrets":
            self.handle_save_server_api_secret()
            return
        if parsed.path == "/api/questionlist/datasets/upload":
            self.handle_upload_question_dataset()
            return
        if parsed.path == "/api/questionlist/datasets/default":
            self.handle_set_question_dataset_default()
            return
        if parsed.path == "/api/eval/run":
            self.handle_start_eval_run()
            return
        if parsed.path == "/api/eval/reblend":
            self.handle_reblend_eval_run()
            return
        if parsed.path == "/api/eval/judge-saved":
            self.handle_start_saved_answer_judge()
            return
        if parsed.path == "/api/eval/judge-comparison":
            self.handle_create_judge_comparison()
            return
        control_match = re.match(r"^/api/eval/jobs/([^/]+)/control$", parsed.path)
        if control_match:
            self.handle_eval_job_control(unquote(control_match.group(1)))
            return
        self.send_json({"error": "not found"}, status=404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if not self.require_write_auth():
            return
        if parsed.path.startswith("/api/model-registry/"):
            config_id = unquote(parsed.path.rsplit("/", 1)[-1])
            self.handle_delete_model_registry_entry(config_id)
            return
        if parsed.path.startswith("/api/judge-api-presets/"):
            preset_id = unquote(parsed.path.rsplit("/", 1)[-1])
            self.handle_delete_judge_api_preset(preset_id)
            return
        if parsed.path.startswith("/api/server-api-secrets/"):
            env_name = unquote(parsed.path.rsplit("/", 1)[-1])
            self.handle_delete_server_api_secret(env_name)
            return
        if parsed.path.startswith("/api/questionlist/datasets/"):
            dataset_id = unquote(parsed.path.rsplit("/", 1)[-1])
            self.handle_delete_question_dataset(dataset_id)
            return
        self.send_json({"error": "not found"}, status=404)

    def do_OPTIONS(self):
        if self.headers.get("Origin") and not self.cors_origin():
            self.send_response(403)
            self.end_headers()
            return
        self.send_response(204)
        self.send_cors_headers()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Final-UI-Token, Authorization")
        self.end_headers()

    def cors_origin(self) -> str:
        origin = str(self.headers.get("Origin") or "").strip()
        if not origin:
            return ""
        allowed = {
            value.strip()
            for value in os.environ.get("FINAL_UI_ALLOWED_ORIGINS", "").split(",")
            if value.strip()
        }
        if origin in allowed:
            return origin
        try:
            origin_host = urlparse(origin).netloc.lower()
        except ValueError:
            origin_host = ""
        request_host = str(self.headers.get("Host") or "").strip().lower()
        if origin_host and request_host and origin_host == request_host:
            return origin
        return ""

    def send_cors_headers(self) -> None:
        origin = self.cors_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def request_auth_token(self) -> str:
        bearer = str(self.headers.get("Authorization") or "").strip()
        if bearer.lower().startswith("bearer "):
            return bearer[7:].strip()
        return str(self.headers.get("X-Final-UI-Token") or "").strip()

    def require_read_auth(self) -> bool:
        if FINAL_UI_AUTH_DISABLED or not FINAL_UI_AUTH_USERS:
            self.current_actor = "local"
            self.current_role = "admin"
            self.current_auth_scheme = "none"
            return True
        return self.authenticate_request("user")

    def require_write_auth(self) -> bool:
        if FINAL_UI_AUTH_DISABLED:
            self.current_actor = "local"
            self.current_role = "admin"
            self.current_auth_scheme = "disabled"
            return True
        if FINAL_UI_AUTH_USERS:
            return self.authenticate_request("admin")
        if not FINAL_UI_AUTH_TOKEN:
            self.current_actor = "local"
            self.current_role = "admin"
            self.current_auth_scheme = "none"
            return True
        if secrets.compare_digest(self.request_auth_token(), FINAL_UI_AUTH_TOKEN):
            self.current_actor = "token"
            self.current_role = "admin"
            self.current_auth_scheme = "token"
            return True
        self.send_auth_required("Admin token is required for write APIs.")
        return False

    def authenticate_request(self, minimum_role: str) -> bool:
        identity = self.auth_identity_from_headers()
        if not identity:
            self.send_auth_required("User ID login is required.")
            return False
        username, role, scheme = identity
        self.current_actor = username
        self.current_role = role
        self.current_auth_scheme = scheme
        if AUTH_ROLE_RANK.get(role, 0) < AUTH_ROLE_RANK.get(minimum_role, 1):
            self.send_json(
                {
                    "error": f"{minimum_role} role is required.",
                    "code": "forbidden",
                    "user": username,
                    "role": role,
                },
                status=403,
            )
            return False
        return True

    def auth_identity_from_headers(self) -> tuple[str, str, str] | None:
        token = self.request_auth_token()
        if FINAL_UI_AUTH_TOKEN and token and secrets.compare_digest(token, FINAL_UI_AUTH_TOKEN):
            return ("token", "admin", "token")
        authorization = str(self.headers.get("Authorization") or "").strip()
        if not authorization.lower().startswith("basic "):
            return None
        try:
            decoded = base64.b64decode(authorization.split(" ", 1)[1], validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return None
        if ":" not in decoded:
            return None
        username, password = decoded.split(":", 1)
        user = FINAL_UI_AUTH_USERS.get(username)
        if not user:
            return None
        if not secrets.compare_digest(password, user.get("password", "")):
            return None
        return (username, user.get("role", "user"), "basic")

    def send_auth_required(self, message: str) -> None:
        body = json.dumps({"error": message, "code": "auth_required"}, ensure_ascii=False).encode("utf-8")
        self.send_response(401)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("WWW-Authenticate", 'Basic realm="User ID"')
        self.send_cors_headers()
        self.end_headers()
        if not getattr(self, "_head_only", False):
            self.wfile.write(body)

    def handle_auth_session(self) -> None:
        self.send_json(
            {
                "auth_enabled": bool(FINAL_UI_AUTH_USERS or FINAL_UI_AUTH_TOKEN) and not FINAL_UI_AUTH_DISABLED,
                "id_auth_enabled": bool(FINAL_UI_AUTH_USERS) and not FINAL_UI_AUTH_DISABLED,
                "token_auth_enabled": bool(FINAL_UI_AUTH_TOKEN) and not FINAL_UI_AUTH_DISABLED,
                "user": self.current_actor,
                "role": self.current_role,
                "scheme": self.current_auth_scheme,
            }
        )

    def handle_auth_access_log(self, query: str) -> None:
        if not FINAL_UI_AUTH_DISABLED and FINAL_UI_AUTH_USERS and not self.authenticate_request("admin"):
            return
        params = parse_qs(query)
        limit = self.safe_int((params.get("limit") or ["100"])[0], default=100, minimum=1, maximum=1000)
        entries = []
        if ACCESS_LOG_PATH.exists():
            try:
                lines = ACCESS_LOG_PATH.read_text(encoding="utf-8").splitlines()[-limit:]
            except OSError:
                lines = []
            for line in lines:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        self.send_json({"entries": entries, "count": len(entries)})

    def parse_ip_literal(self, value: str) -> str:
        text = str(value or "").strip().strip('"').strip("'")
        if not text:
            return ""
        if text.startswith("[") and "]" in text:
            text = text[1 : text.index("]")]
        elif text.count(":") == 1 and "." in text:
            text = text.rsplit(":", 1)[0]
        if "%" in text:
            text = text.split("%", 1)[0]
        try:
            return str(ipaddress.ip_address(text))
        except ValueError:
            return ""

    def first_forwarded_ip(self, value: str) -> str:
        for part in str(value or "").split(","):
            parsed = self.parse_ip_literal(part)
            if parsed:
                return parsed
        return ""

    def proxy_networks_from_env(self):
        networks = []
        for item in os.environ.get("FINAL_UI_TRUSTED_PROXIES", "").split(","):
            cidr = item.strip()
            if not cidr:
                continue
            try:
                networks.append(ipaddress.ip_network(cidr, strict=False))
            except ValueError:
                continue
        return tuple(networks)

    def ip_in_networks(self, value: str, networks) -> bool:
        parsed = self.parse_ip_literal(value)
        if not parsed:
            return False
        address = ipaddress.ip_address(parsed)
        return any(address in network for network in networks)

    def proxy_headers_trusted(self, peer_addr: str) -> bool:
        mode = os.environ.get("FINAL_UI_TRUST_PROXY_HEADERS", "cloudflare").strip().lower()
        if mode in {"0", "false", "no", "off", "none"}:
            return False
        if mode in {"1", "true", "yes", "on", "all"}:
            return True
        env_networks = self.proxy_networks_from_env()
        if env_networks and self.ip_in_networks(peer_addr, env_networks):
            return True
        if mode in {"strict_cloudflare", "cloudflare_strict"}:
            return self.ip_in_networks(peer_addr, CLOUDFLARE_PROXY_NETWORKS)
        if mode in {"cloudflare", "cf", ""}:
            trusted_networks = (*CLOUDFLARE_PROXY_NETWORKS, *LOCAL_PROXY_NETWORKS)
            return self.ip_in_networks(peer_addr, trusted_networks)
        return self.ip_in_networks(peer_addr, env_networks)

    def request_ip_info(self) -> dict:
        headers = getattr(self, "headers", {}) or {}
        peer_addr = self.parse_ip_literal(self.client_address[0] if getattr(self, "client_address", None) else "")
        header_values = {
            "cf_connecting_ip": str(headers.get("CF-Connecting-IP") or "").strip(),
            "cf_connecting_ipv6": str(headers.get("CF-Connecting-IPv6") or "").strip(),
            "true_client_ip": str(headers.get("True-Client-IP") or "").strip(),
            "x_real_ip": str(headers.get("X-Real-IP") or "").strip(),
            "x_forwarded_for": str(headers.get("X-Forwarded-For") or "").strip(),
        }
        trusted = self.proxy_headers_trusted(peer_addr)
        client_addr = peer_addr
        source = "socket"
        if trusted:
            candidates = [
                ("CF-Connecting-IP", header_values["cf_connecting_ip"]),
                ("CF-Connecting-IPv6", header_values["cf_connecting_ipv6"]),
                ("True-Client-IP", header_values["true_client_ip"]),
                ("X-Real-IP", header_values["x_real_ip"]),
                ("X-Forwarded-For", self.first_forwarded_ip(header_values["x_forwarded_for"])),
            ]
            for candidate_source, candidate in candidates:
                parsed = self.parse_ip_literal(candidate)
                if parsed:
                    client_addr = parsed
                    source = candidate_source
                    break
        result = {
            "remote_addr": client_addr,
            "client_addr": client_addr,
            "peer_addr": peer_addr,
            "client_ip_source": source,
            "proxy_headers_trusted": trusted,
        }
        result.update({key: value for key, value in header_values.items() if value})
        return result

    def log_request(self, code="-", size="-") -> None:
        super().log_request(code, size)
        try:
            status = int(code)
        except (TypeError, ValueError):
            status = 0
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            **self.request_ip_info(),
            "method": self.command,
            "path": urlparse(self.path).path,
            "status": status,
            "size": size,
            "user": getattr(self, "current_actor", "anonymous"),
            "role": getattr(self, "current_role", ""),
        }
        try:
            ACCESS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with ACCESS_LOG_LOCK:
                self.rotate_access_log_if_needed()
                with ACCESS_LOG_PATH.open("a", encoding="utf-8") as file:
                    file.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        except OSError:
            pass

    def rotate_access_log_if_needed(self) -> None:
        if ACCESS_LOG_MAX_BYTES <= 0 or not ACCESS_LOG_PATH.exists():
            return
        try:
            if ACCESS_LOG_PATH.stat().st_size <= ACCESS_LOG_MAX_BYTES:
                return
            keep_lines = max(0, ACCESS_LOG_KEEP_LINES)
            lines = ACCESS_LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
            retained_reversed = []
            retained_bytes = 0
            if keep_lines:
                for line in reversed(lines):
                    line_bytes = len((line + "\n").encode("utf-8", errors="replace"))
                    if len(retained_reversed) >= keep_lines:
                        break
                    if retained_reversed and retained_bytes + line_bytes > ACCESS_LOG_MAX_BYTES:
                        break
                    retained_reversed.append(line)
                    retained_bytes += line_bytes
            retained = list(reversed(retained_reversed))
            archive_path = ACCESS_LOG_PATH.with_name(
                f"access_log.{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            )
            ACCESS_LOG_PATH.replace(archive_path)
            ACCESS_LOG_PATH.write_text(
                ("\n".join(retained) + "\n") if retained else "",
                encoding="utf-8",
            )
        except OSError:
            return

    def handle_model_api(self, path: str, query: str = ""):
        parts = [unquote(part) for part in path.strip("/").split("/")]
        if len(parts) != 4 or parts[0] != "api" or parts[1] != "models":
            self.send_json({"error": "not found"}, status=404)
            return

        _, _, version, action = parts
        registry = self.load_registry()
        model_spec = registry.get(version)
        if not model_spec:
            self.send_json({"error": f"unknown model version: {version}"}, status=404)
            return

        if action == "health":
            self.handle_model_health(version, model_spec, query)
            return

        if action == "eval":
            self.send_json({
                "status": "ready",
                "version": version,
                "message": "Evaluation endpoint is registered. Wire this to the real model runner when available.",
            })
            return

        self.send_json({"error": "not found"}, status=404)

    def load_registry(self):
        seeded_target_registry = self.load_seeded_target_models()
        target_registry = self.load_registered_target_models_file()
        judge_registry = self.load_registered_judge_models_file()
        self.mark_registry_source(seeded_target_registry, "user", deletable=True)
        self.mark_registry_source(target_registry, "user", deletable=True)
        self.mark_registry_source(judge_registry, "user", deletable=True)
        return {**seeded_target_registry, **target_registry, **judge_registry}

    def load_seeded_target_models(self):
        registry = self.load_json_registry(SEEDED_TARGET_MODELS_PATH)
        return {
            config_id: spec
            for config_id, spec in registry.items()
            if spec.get("eval_target") is not False
        }

    def mark_registry_source(self, registry: dict, source: str, *, deletable: bool):
        for spec in registry.values():
            spec["registry_source"] = source
            spec["deletable"] = deletable

    def load_json_registry(self, path: Path):
        if not path.exists():
            return {}
        try:
            raw = self.load_structured_file(path)
        except (OSError, json.JSONDecodeError, RuntimeError):
            return {}
        return self.normalize_registry_payload(raw)

    def normalize_registry_payload(self, raw):
        if not raw:
            return {}
        configs = raw.get("configs") if isinstance(raw, dict) and isinstance(raw.get("configs"), list) else None
        if configs is None and isinstance(raw, dict):
            configs = [
                {"config_id": config_id, **spec}
                for config_id, spec in raw.items()
                if isinstance(spec, dict)
            ]
        registry = {}
        for config in configs or []:
            normalized = self.normalize_model_config(config)
            if normalized:
                registry[normalized["config_id"]] = normalized
        return registry

    def normalize_model_config(self, config: dict):
        config_id = self.safe_config_id(config.get("config_id") or config.get("model") or config.get("display_name"))
        if not config_id:
            return None
        provider = str(config.get("provider") or "generic_api").strip()
        if provider == "api":
            provider = "generic_api"
        if provider not in ALLOWED_PROVIDERS:
            provider = "generic_api"
        chat_url = self.external_http_url(config.get("chat_url"))
        upstream_health_url = self.external_http_url(config.get("upstream_health_url") or config.get("external_health_url"))
        upstream_chat_url = self.external_http_url(config.get("upstream_chat_url") or config.get("external_chat_url"))
        if self.external_http_url(config.get("health_url")):
            upstream_health_url = self.external_http_url(config.get("health_url"))
        if self.external_http_url(config.get("api_url")):
            upstream_chat_url = self.external_http_url(config.get("api_url"))
        responses_url = self.external_http_url(config.get("responses_url") or config.get("response_url"))
        raw_candidate_role = str(config.get("candidate_role") or "").strip()
        judge_role = str(config.get("judge_role") or "").strip()
        evaluation_role = str(config.get("evaluation_role") or config.get("usage_role") or "").strip()
        if not judge_role and "arbiter" in evaluation_role.lower():
            judge_role = "arbiter"
        elif not judge_role and "judge" in evaluation_role.lower():
            judge_role = "judge"
        normalized = {
            "config_id": config_id,
            "display_name": config.get("display_name") or config.get("name") or config.get("model") or config_id,
            "provider": provider,
            "model": config.get("model") or config_id,
            "cache_identity": str(config.get("cache_identity") or config.get("model_artifact_id") or "").strip(),
            "base_url": str(config.get("base_url") or "").rstrip("/"),
            "chat_url": str(chat_url or upstream_chat_url or "").strip(),
            "responses_url": responses_url,
            "health_url": f"/api/models/{config_id}/health",
            "api_url": f"/api/models/{config_id}/eval",
            "upstream_health_url": str(upstream_health_url or "").strip(),
            "upstream_chat_url": str(upstream_chat_url or chat_url or "").strip(),
            "api_key_env": str(config.get("api_key_env") or "").strip(),
            "base_url_env": str(config.get("base_url_env") or "").strip(),
            "local_path": str(config.get("local_path") or config.get("model_path") or "").strip(),
            "prompt_version": config.get("prompt_version"),
            "system_prompt_preset": str(config.get("system_prompt_preset") or config.get("judge_prompt_preset") or "").strip(),
            "system_prompt": config.get("system_prompt") or "",
            "system_prompt_snapshot": config.get("system_prompt_snapshot") or "",
            "system_prompt_snapshot_version": str(config.get("system_prompt_snapshot_version") or config.get("prompt_version") or "").strip(),
            "prompt_template": config.get("prompt_template") or "",
            "query_prompt_template": config.get("query_prompt_template") or "",
            "prompt_prefix": config.get("prompt_prefix") or "",
            "prompt_suffix": config.get("prompt_suffix") or "",
            "prompt_variant_of": self.safe_config_id(config.get("prompt_variant_of") or ""),
            "experiment_tag": str(config.get("experiment_tag") or config.get("prompt_variant_tag") or "").strip(),
            "include_evidence_context": config.get("include_evidence_context", True),
            "rag_config": config.get("rag_config"),
            "safety_policy": config.get("safety_policy"),
            "role_notes": config.get("role_notes") or "",
            "model_group": config.get("model_group") or "",
            "model_family": str(config.get("model_family") or config.get("family") or "").strip(),
            "model_family_color": self.safe_hex_color(config.get("model_family_color") or config.get("family_color") or ""),
            "candidate_role": raw_candidate_role,
            "evaluation_role": evaluation_role,
            "judge_role": judge_role,
            "visibility_status": str(config.get("visibility_status") or "").strip(),
            "eval_target": self.config_bool(config.get("eval_target"), default=True),
            "ui_visible": self.config_bool(config.get("ui_visible"), default=True),
            "run_preselected": self.config_bool(config.get("run_preselected"), default=False),
            "unload_after_health_check": self.config_bool(
                config.get("unload_after_health_check"),
                default=provider == "ollama",
            ),
            "options": config.get("options", {}) if isinstance(config.get("options", {}), dict) else {},
            "response_path": config.get("response_path") or "",
        }
        return normalized

    def config_bool(self, value, *, default: bool):
        parsed = optional_bool(value)
        return default if parsed is None else parsed

    def is_eval_target_model(self, config: dict):
        if not config:
            return False
        if not bool(config.get("eval_target", True)):
            return False
        role_text = " ".join(
            str(config.get(key) or "")
            for key in ("evaluation_role", "judge_role", "safety_policy", "prompt_version", "config_id", "display_name")
        ).lower()
        blocked_markers = ("judge", "router", "vision", "aux")
        return not any(marker in role_text for marker in blocked_markers)

    def is_judge_registry_config(self, config: dict):
        if not config:
            return False
        if str(config.get("visibility_status") or "").strip().lower() == "hidden_by_user":
            return False
        if str(config.get("safety_policy") or "").strip().lower() == "hidden_by_user":
            return False
        role_text = " ".join(
            str(config.get(key) or "")
            for key in ("evaluation_role", "judge_role", "safety_policy", "prompt_version", "config_id", "display_name")
        ).lower()
        return "judge" in role_text or "arbiter" in role_text or "hal_lora" in role_text

    def safe_config_id(self, value):
        text = str(value or "").strip().lower()
        text = "".join(ch if ch.isalnum() else "_" for ch in text)
        text = "_".join(part for part in text.split("_") if part)
        return text[:80]

    def safe_hex_color(self, value):
        text = str(value or "").strip()
        if re.fullmatch(r"#[0-9a-fA-F]{6}", text):
            return text
        if re.fullmatch(r"#[0-9a-fA-F]{3}", text):
            return "#" + "".join(char * 2 for char in text[1:])
        return ""

    def external_http_url(self, value):
        text = str(value or "").strip()
        if not text:
            return ""
        parsed = urlparse(text)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return text
        return ""

    def judge_config_ids_from_payload(self, judge_payload: dict):
        raw_values = []
        config_ids = judge_payload.get("config_ids")
        if isinstance(config_ids, list):
            raw_values.extend(config_ids)
        elif config_ids:
            raw_values.extend(str(config_ids).split(","))
        config_id = judge_payload.get("config_id")
        if config_id:
            raw_values.extend(str(config_id).split(","))
        cleaned = [self.safe_config_id(value) for value in raw_values]
        return list(dict.fromkeys(item for item in cleaned if item))

    def judge_score_weights_from_payload(self, judge_payload: dict, judge_config_ids: list[str]):
        if len(judge_config_ids) <= 1:
            return ({judge_config_ids[0]: 1.0} if judge_config_ids else {}), ""
        raw_weights = judge_payload.get("score_weights")
        if raw_weights is None or raw_weights == "":
            weight = round(1.0 / len(judge_config_ids), 6)
            weights = {config_id: weight for config_id in judge_config_ids}
            weights[judge_config_ids[-1]] = round(1.0 - sum(weights[config_id] for config_id in judge_config_ids[:-1]), 6)
            return weights, ""
        if not isinstance(raw_weights, dict):
            return {}, "judge.score_weights must be an object keyed by judge config_id."
        normalized_raw = {
            self.safe_config_id(key): value
            for key, value in raw_weights.items()
        }
        weights: dict[str, float] = {}
        missing = [config_id for config_id in judge_config_ids if config_id not in normalized_raw]
        if missing:
            return {}, "Missing Judge weight for: " + ", ".join(missing)
        for config_id in judge_config_ids:
            try:
                weight = float(normalized_raw[config_id])
            except (TypeError, ValueError):
                return {}, f"Invalid Judge weight for {config_id}."
            if weight < 0 or weight > 1:
                return {}, f"Judge weight for {config_id} must be between 0 and 1."
            weights[config_id] = round(weight, 6)
        total = sum(weights.values())
        if abs(total - 1.0) > 0.001:
            return {}, f"Judge weight total must be 1. Current total: {total:.3f}."
        return weights, ""

    def judge_aggregation_method_from_payload(self, judge_payload: dict):
        method = str(judge_payload.get("aggregation_method") or "weighted_mean").strip()
        allowed = {"weighted_mean", "mean", "trimmed_mean", "max", "min", "auto"}
        return method if method in allowed else "weighted_mean"

    def handle_judge_api_presets(self):
        self.send_json({"status": "ok", "presets": self.load_judge_api_presets_file()})

    def handle_save_judge_api_preset(self):
        payload = self.read_json_body()
        if payload is None:
            self.send_json_body_error()
            return
        preset = payload.get("preset") if isinstance(payload.get("preset"), dict) else payload
        if not isinstance(preset, dict):
            self.send_json({"error": "preset object is required"}, status=400)
            return
        if self.payload_contains_raw_secret(preset):
            self.send_json({"error": "Do not submit raw secrets. Set apiKeyEnv instead."}, status=400)
            return
        normalized = self.normalize_judge_api_preset(preset)
        if not normalized:
            self.send_json({"error": "preset id, provider, and model are required"}, status=400)
            return
        api_key_env_error = self.api_key_env_name_error(normalized.get("apiKeyEnv"))
        if api_key_env_error:
            self.send_json({"error": api_key_env_error}, status=400)
            return
        presets = self.load_judge_api_presets_file()
        existing = next((item for item in presets if item["id"] == normalized["id"]), None)
        if existing and existing.get("builtIn"):
            self.send_json({"error": "built-in presets cannot be overwritten"}, status=409)
            return
        presets = [item for item in presets if item["id"] != normalized["id"]]
        presets.append(normalized)
        self.write_judge_api_presets_file(presets)
        self.send_json({"status": "ok", "preset": normalized, "presets": presets})

    def handle_delete_judge_api_preset(self, preset_id: str):
        normalized_id = self.safe_config_id(preset_id)
        if not normalized_id:
            self.send_json({"error": "preset id is required"}, status=400)
            return
        presets = self.load_judge_api_presets_file()
        existing = next((item for item in presets if item["id"] == normalized_id), None)
        if not existing:
            self.send_json({"error": f"unknown judge API preset: {normalized_id}"}, status=404)
            return
        if existing.get("builtIn"):
            self.send_json({"error": "built-in presets cannot be deleted"}, status=400)
            return
        presets = [item for item in presets if item["id"] != normalized_id]
        self.write_judge_api_presets_file(presets)
        self.send_json({"status": "ok", "deleted": existing, "presets": presets})

    def handle_server_api_secrets(self):
        if not self.require_write_auth():
            return
        self.send_json({"status": "ok", "keys": self.server_api_secret_summaries()})

    def handle_save_server_api_secret(self):
        payload = self.read_json_body()
        if payload is None:
            self.send_json_body_error()
            return
        env_name = self.safe_env_name(payload.get("env_name") or payload.get("name"))
        value = str(payload.get("value") or "").strip()
        if not env_name:
            self.send_json({"error": "env_name is required"}, status=400)
            return
        env_name_error = self.api_key_env_name_error(env_name)
        if env_name_error:
            self.send_json({"error": env_name_error}, status=400)
            return
        if not value:
            self.send_json({"error": "API key value is required"}, status=400)
            return
        secrets_store = self.store_server_api_secret_value(env_name, value)
        self.send_json({"status": "ok", "env_name": env_name, "keys": self.server_api_secret_summaries(secrets_store)})

    def handle_delete_server_api_secret(self, env_name: str):
        normalized_name = self.safe_env_name(env_name)
        if not normalized_name:
            self.send_json({"error": "env_name is required"}, status=400)
            return
        secrets_store = self.load_server_api_secrets_file()
        if normalized_name not in secrets_store:
            self.send_json({"error": f"unknown stored API key: {normalized_name}"}, status=404)
            return
        deleted = {key: value for key, value in secrets_store[normalized_name].items() if key != "value"}
        secrets_store.pop(normalized_name, None)
        self.write_server_api_secrets_file(secrets_store)
        self.send_json({"status": "ok", "deleted": {"env_name": normalized_name, **deleted}, "keys": self.server_api_secret_summaries(secrets_store)})

    def load_server_api_secrets_file(self):
        if not SERVER_API_SECRETS_PATH.exists():
            return {}
        try:
            raw = self.load_structured_file(SERVER_API_SECRETS_PATH)
        except (OSError, json.JSONDecodeError, RuntimeError):
            return {}
        raw_secrets = raw.get("secrets") if isinstance(raw, dict) else {}
        if not isinstance(raw_secrets, dict):
            return {}
        secrets_store = {}
        for name, spec in raw_secrets.items():
            env_name = self.safe_env_name(name)
            if not env_name:
                continue
            if isinstance(spec, dict):
                value = str(spec.get("value") or "")
                updated_at = str(spec.get("updated_at") or "")
                updated_by = str(spec.get("updated_by") or "")
            else:
                value = str(spec or "")
                updated_at = ""
                updated_by = ""
            if value:
                secrets_store[env_name] = {
                    "value": value,
                    "updated_at": updated_at,
                    "updated_by": updated_by,
                }
        return secrets_store

    def write_server_api_secrets_file(self, secrets_store: dict):
        SERVER_API_SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
        serializable = {
            key: {
                "value": str(value.get("value") or ""),
                "updated_at": str(value.get("updated_at") or ""),
                "updated_by": str(value.get("updated_by") or ""),
            }
            for key, value in sorted(secrets_store.items())
            if self.safe_env_name(key) and str(value.get("value") or "")
        }
        SERVER_API_SECRETS_PATH.write_text(
            json.dumps({"secrets": serializable}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def server_api_secret_summaries(self, secrets_store: dict | None = None):
        source = secrets_store if secrets_store is not None else self.load_server_api_secrets_file()
        return [
            {
                "env_name": env_name,
                "has_value": bool(spec.get("value")),
                "updated_at": spec.get("updated_at") or "",
                "updated_by": spec.get("updated_by") or "",
            }
            for env_name, spec in sorted(source.items())
        ]

    def server_api_secret_value(self, env_name: str):
        normalized_name = self.safe_env_name(env_name)
        if not normalized_name:
            return ""
        return str(self.load_server_api_secrets_file().get(normalized_name, {}).get("value") or "")

    def store_server_api_secret_value(self, env_name: str, value: str):
        normalized_name = self.safe_env_name(env_name)
        if not normalized_name:
            return self.load_server_api_secrets_file()
        secrets_store = self.load_server_api_secrets_file()
        secrets_store[normalized_name] = {
            "value": str(value or ""),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "updated_by": getattr(self, "current_actor", "anonymous"),
        }
        self.write_server_api_secrets_file(secrets_store)
        return secrets_store

    def provider_api_key_value(self, config: dict):
        provider = str(config.get("provider") or "")
        explicit_name = str(config.get("api_key_env") or "").strip()
        names = [explicit_name] if explicit_name else []
        names.extend(name for name in PROVIDER_ENV_ALIASES.get(provider, {}).get("api_key", []) if name and name not in names)
        for name in names:
            value = os.environ.get(name)
            if value:
                return value, name
        for name in names:
            stored_token = self.server_api_secret_value(name)
            if stored_token:
                return stored_token, name
        return "", names[0] if names else ""

    def load_judge_api_presets_file(self):
        if not JUDGE_API_PRESETS_PATH.exists():
            return []
        try:
            raw = self.load_structured_file(JUDGE_API_PRESETS_PATH)
        except (OSError, json.JSONDecodeError, RuntimeError):
            return []
        presets = raw.get("presets") if isinstance(raw, dict) else raw
        if not isinstance(presets, list):
            return []
        normalized = []
        seen = set()
        for preset in presets:
            if self.payload_contains_raw_secret(preset):
                continue
            item = self.normalize_judge_api_preset(preset)
            if not item or item["id"] in seen:
                continue
            normalized.append(item)
            seen.add(item["id"])
        return normalized

    def write_judge_api_presets_file(self, presets: list[dict]):
        JUDGE_API_PRESETS_PATH.parent.mkdir(parents=True, exist_ok=True)
        JUDGE_API_PRESETS_PATH.write_text(
            json.dumps({"presets": presets}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def openai_reasoning_judge_model(self, model: str, options: dict | None = None):
        options = options if isinstance(options, dict) else {}
        reasoning = options.get("reasoning")
        model_id = str(model or "").strip().lower()
        return bool(
            options.get("reasoning_effort")
            or options.get("reasoningEffort")
            or (isinstance(reasoning, dict) and reasoning.get("effort"))
            or model_id.startswith(("gpt-5", "o1", "o3", "o4"))
        )

    def judge_sampling_controls_enabled(self, provider: str, model: str, options: dict | None = None):
        return not (provider == "openai_native" and self.openai_reasoning_judge_model(model, options))

    def normalize_judge_api_preset(self, preset: dict):
        if not isinstance(preset, dict):
            return None
        provider = str(preset.get("provider") or "generic_api").strip()
        if provider == "api":
            provider = "generic_api"
        if provider not in ALLOWED_PROVIDERS or provider == "local_path":
            provider = "generic_api"
        model = str(preset.get("model") or "").strip()
        preset_id = self.safe_config_id(preset.get("id") or preset.get("preset_id") or preset.get("label") or model)
        if not preset_id or not model:
            return None
        config_id = self.safe_config_id(preset.get("configId") or preset.get("config_id") or f"{preset_id}_judge")
        prompt_preset = str(preset.get("promptPreset") or preset.get("prompt_preset") or "judge_default_v1").strip()
        options = preset.get("options", {}) if isinstance(preset.get("options"), dict) else {}
        sampling_enabled = self.judge_sampling_controls_enabled(provider, model, options)
        if not sampling_enabled:
            options = dict(options)
            for key in ("temperature", "temp", "top_p", "topP"):
                options.pop(key, None)
        normalized = {
            "id": preset_id,
            "label": str(preset.get("label") or preset_id).strip(),
            "provider": provider,
            "configId": config_id or f"{preset_id}_judge",
            "displayName": str(preset.get("displayName") or preset.get("display_name") or preset.get("label") or model).strip(),
            "model": model,
            "baseUrl": str(preset.get("baseUrl") or preset.get("base_url") or "").strip(),
            "chatUrl": str(preset.get("chatUrl") or preset.get("chat_url") or "").strip(),
            "apiKeyEnv": str(preset.get("apiKeyEnv") or preset.get("api_key_env") or "").strip(),
            "maxTokens": self.safe_int(preset.get("maxTokens") or preset.get("max_tokens"), default=1024, minimum=1, maximum=100000),
            "promptPreset": prompt_preset or "judge_default_v1",
            "promptVersion": str(preset.get("promptVersion") or preset.get("prompt_version") or "").strip(),
            "systemPrompt": preset.get("systemPrompt") or preset.get("system_prompt") or "",
            "options": options,
            "builtIn": self.config_bool(preset.get("builtIn") if "builtIn" in preset else preset.get("built_in"), default=False),
        }
        if sampling_enabled:
            normalized["temperature"] = self.safe_float(preset.get("temperature"), default=0.0, minimum=0.0, maximum=2.0)
            normalized["topP"] = self.safe_float(preset.get("topP") if "topP" in preset else preset.get("top_p"), default=0.1, minimum=0.0, maximum=1.0)
        return normalized

    def payload_contains_raw_secret(self, payload) -> bool:
        secret_keys = {"api_key", "apikey", "apiKey", "token", "secret", "password", "authorization", "bearer"}
        if isinstance(payload, dict):
            for key, value in payload.items():
                key_text = str(key)
                if key_text in {"apiKeyEnv", "api_key_env"}:
                    continue
                if key_text in secret_keys or key_text.lower() in {item.lower() for item in secret_keys}:
                    return True
                if self.payload_contains_raw_secret(value):
                    return True
        elif isinstance(payload, list):
            return any(self.payload_contains_raw_secret(item) for item in payload)
        return False

    def safe_env_name(self, value):
        text = str(value or "").strip()
        if not text or not re.match(r"^[A-Za-z_][A-Za-z0-9_]{0,119}$", text):
            return ""
        return text

    def api_key_env_name_error(self, value):
        text = str(value or "").strip()
        if not text:
            return ""
        if not self.safe_env_name(text):
            return "api_key_env must be an environment variable name such as GEMINI_API_KEY, not a raw API key."
        common_secret_prefixes = ("sk-", "sk_", "AIza", "ya29.", "xai-", "gsk_", "nvapi-")
        if text.startswith(common_secret_prefixes) or ("_" not in text and len(text) >= 24):
            return "api_key_env looks like a raw API key. Submit the key value as api_key_value and keep api_key_env as GEMINI_API_KEY."
        return ""

    def default_api_key_env_name(self, provider: str, config_id: str = ""):
        aliases = PROVIDER_ENV_ALIASES.get(str(provider or ""), {}).get("api_key", [])
        for name in aliases:
            if self.safe_env_name(name) and name.upper() == name:
                return name
        for name in aliases:
            if self.safe_env_name(name):
                return name
        base = re.sub(r"[^A-Za-z0-9_]+", "_", str(config_id or provider or "judge")).strip("_").upper()
        if not base:
            base = "JUDGE"
        if not re.match(r"^[A-Z_]", base):
            base = f"JUDGE_{base}"
        return self.safe_env_name(f"FINAL_UI_{base[:90]}_API_KEY") or "FINAL_UI_JUDGE_API_KEY"

    def handle_save_model_registry_entry(self):
        payload = self.read_json_body()
        if payload is None:
            self.send_json_body_error()
            return
        config = payload.get("config") if isinstance(payload.get("config"), dict) else payload
        incoming_config_id = self.safe_config_id(config.get("config_id") or config.get("model") or config.get("display_name"))
        existing_config = self.load_registry().get(incoming_config_id, {}) if incoming_config_id else {}
        if existing_config:
            config = {**existing_config, **config}
        stored_api_key_env = ""
        stored_api_key_summaries = []
        api_key_value = str(config.pop("api_key_value", "") or config.pop("server_api_key_value", "") or "").strip()
        if api_key_value and str(config.get("provider") or "").strip() != "ollama":
            raw_env_name = str(config.get("api_key_env") or "").strip()
            if raw_env_name:
                env_name_error = self.api_key_env_name_error(raw_env_name)
                if env_name_error:
                    self.send_json({"error": env_name_error}, status=400)
                    return
                env_name = self.safe_env_name(raw_env_name)
            else:
                env_name = self.default_api_key_env_name(config.get("provider"), incoming_config_id)
            secrets_store = self.store_server_api_secret_value(env_name, api_key_value)
            stored_api_key_env = env_name
            stored_api_key_summaries = self.server_api_secret_summaries(secrets_store)
            config["api_key_env"] = env_name
        if any(key in config for key in ("api_key", "token", "secret")):
            self.send_json({"error": "Do not submit raw secrets. Set api_key_env instead."}, status=400)
            return
        if str(config.get("system_prompt_preset") or "").strip() == "custom" and not str(config.get("system_prompt") or "").strip():
            self.send_json({"error": "system_prompt is required when system_prompt_preset is custom."}, status=400)
            return
        normalized = self.normalize_model_config(config)
        if not normalized:
            self.send_json({"error": "config_id or model is required"}, status=400)
            return
        env_base_url, _ = provider_env_value(normalized, "base_url")
        if normalized["provider"] in {"openai_native", "openai_compatible", "generic_api"} and not (
            normalized["provider"] == "openai_native"
            or normalized.get("base_url")
            or normalized.get("upstream_chat_url")
            or normalized.get("chat_url")
            or env_base_url
        ):
            self.send_json({"error": "base_url or chat_url is required for API models"}, status=400)
            return
        if normalized["provider"] in {"openai_native", "clova_studio", "anthropic", "gemini"} and not normalized.get("model"):
            self.send_json({"error": f"model is required for {normalized['provider']} models"}, status=400)
            return
        api_key_env_error = self.api_key_env_name_error(normalized.get("api_key_env"))
        if api_key_env_error:
            self.send_json({"error": api_key_env_error}, status=400)
            return
        if normalized["provider"] == "local_path" and not normalized.get("local_path"):
            self.send_json({"error": "local_path is required for local_path provider"}, status=400)
            return

        target_registry = self.load_registered_target_models_file()
        judge_registry = self.load_registered_judge_models_file()
        if self.is_judge_registry_config(normalized):
            target_registry.pop(normalized["config_id"], None)
            judge_registry[normalized["config_id"]] = normalized
        else:
            judge_registry.pop(normalized["config_id"], None)
            target_registry[normalized["config_id"]] = normalized
        self.write_registered_registry_files(target_registry, judge_registry)
        response = {"status": "ok", "config": normalized, "registry": self.load_registry()}
        if stored_api_key_env:
            response["stored_api_key_env"] = stored_api_key_env
            response["server_api_keys"] = stored_api_key_summaries
        self.send_json(response)

    def handle_delete_model_registry_entry(self, config_id: str):
        normalized_id = self.safe_config_id(config_id)
        if not normalized_id:
            self.send_json({"error": "config_id is required"}, status=400)
            return

        target_registry = self.load_registered_target_models_file()
        judge_registry = self.load_registered_judge_models_file()
        seeded_target_registry = self.load_seeded_target_models()
        if normalized_id in seeded_target_registry:
            deleted = target_registry.pop(normalized_id, seeded_target_registry[normalized_id])
            judge_registry.pop(normalized_id, None)
            target_registry[normalized_id] = self.hidden_registry_override(normalized_id, deleted)
        elif normalized_id in target_registry:
            deleted = target_registry.pop(normalized_id)
            judge_registry.pop(normalized_id, None)
        elif normalized_id in judge_registry:
            deleted = judge_registry.pop(normalized_id)
        else:
            self.send_json({"error": f"unknown registered model: {normalized_id}"}, status=404)
            return

        self.write_registered_registry_files(target_registry, judge_registry)
        self.send_json({"status": "ok", "deleted": deleted, "registry": self.load_registry()})

    def hidden_registry_override(self, config_id: str, source_spec: dict):
        return {
            "config_id": config_id,
            "display_name": source_spec.get("display_name") or source_spec.get("model") or config_id,
            "provider": source_spec.get("provider") or "generic_api",
            "model": source_spec.get("model") or config_id,
            "base_url": source_spec.get("base_url") or "",
            "base_url_env": source_spec.get("base_url_env") or "",
            "chat_url": source_spec.get("chat_url") or "",
            "api_key_env": source_spec.get("api_key_env") or "",
            "prompt_version": source_spec.get("prompt_version") or "",
            "system_prompt_preset": source_spec.get("system_prompt_preset") or "",
            "prompt_variant_of": source_spec.get("prompt_variant_of") or "",
            "experiment_tag": source_spec.get("experiment_tag") or "",
            "rag_config": source_spec.get("rag_config") or "none",
            "safety_policy": "hidden_by_user",
            "role_notes": "Hidden from the model registry by user request.",
            "model_group": source_spec.get("model_group") or "",
            "model_family": source_spec.get("model_family") or "",
            "model_family_color": source_spec.get("model_family_color") or "",
            "candidate_role": source_spec.get("candidate_role") or "",
            "evaluation_role": source_spec.get("evaluation_role") or "",
            "judge_role": source_spec.get("judge_role") or "",
            "visibility_status": "hidden_by_user",
            "eval_target": False,
            "ui_visible": False,
            "run_preselected": False,
            "options": source_spec.get("options", {}) if isinstance(source_spec.get("options"), dict) else {},
        }

    def write_registry_file(self, path: Path, registry: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"configs": list(registry.values())}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def write_registered_registry_files(self, target_registry: dict, judge_registry: dict):
        self.write_registry_file(REGISTERED_TARGET_MODELS_PATH, target_registry)
        self.write_registry_file(REGISTERED_JUDGE_MODELS_PATH, judge_registry)

    def load_registered_target_models_file(self):
        if REGISTERED_TARGET_MODELS_PATH.exists():
            return self.load_json_registry(REGISTERED_TARGET_MODELS_PATH)
        return {}

    def load_registered_judge_models_file(self):
        if REGISTERED_JUDGE_MODELS_PATH.exists():
            return self.load_json_registry(REGISTERED_JUDGE_MODELS_PATH)
        return {}

    def read_json_body(self):
        self._json_body_error = ""
        self._json_body_status = 400
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        if length > MAX_JSON_BODY_BYTES:
            self._json_body_error = f"JSON request body is too large. Limit is {MAX_JSON_BODY_BYTES} bytes."
            self._json_body_status = 413
            return None
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json_body_error = "Invalid JSON body"
            self._json_body_status = 400
            return None

    def send_json_body_error(self, default_message: str = "Invalid JSON body") -> None:
        self.send_json(
            {"error": getattr(self, "_json_body_error", "") or default_message},
            status=int(getattr(self, "_json_body_status", 400) or 400),
        )

    def load_structured_file(self, path: Path):
        text = path.read_text(encoding="utf-8-sig")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            try:
                import yaml  # type: ignore
            except ImportError as exc:
                raise RuntimeError(f"{path} is not JSON and PyYAML is not installed") from exc
            return yaml.safe_load(text)

    def handle_model_health(self, version: str, model_spec: dict, query: str = ""):
        provider = model_spec.get("provider")
        model = model_spec.get("model")
        if provider == "local_path":
            local_path = Path(str(model_spec.get("local_path") or ""))
            exists = local_path.exists()
            self.send_json(
                {
                    "status": "ok" if exists else "missing_path",
                    "version": version,
                    "provider": provider,
                    "model": model,
                    "message": f"Local path {'exists' if exists else 'does not exist'}: {local_path}",
                },
                status=200,
            )
            return
        if provider in {"openai_native", "openai_compatible", "generic_api", "clova_studio", "anthropic", "gemini"}:
            self.handle_external_api_health(version, model_spec)
            return
        if provider != "ollama":
            self.send_json(
                {
                    "status": "configured",
                    "version": version,
                    "provider": provider,
                    "model": model,
                    "message": "Provider is registered; live health is implemented for Ollama only.",
                }
            )
            return

        base_url = self.ollama_base_url(model_spec)
        params = parse_qs(query or "")
        live_mode = self.query_bool(params, "live") or self.query_bool(params, "load") or (
            str((params.get("mode") or [""])[0]).strip().lower() in {"load", "live", "load_unload"}
        )
        try:
            installed = self.ollama_models(base_url)
        except (urlerror.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            self.send_json(
                {
                    "status": "offline",
                    "version": version,
                    "provider": provider,
                    "model": model,
                    "message": f"Ollama is not reachable at {base_url}: {exc}",
                },
                status=200,
            )
            return

        if model in installed:
            if not live_mode:
                self.send_json(
                    {
                        "status": "ok",
                        "version": version,
                        "provider": provider,
                        "model": model,
                        "message": "Ollama model tag is installed. Live load check was not requested.",
                        "health_check_mode": "installed_only",
                    }
                )
                return

            if self.has_running_eval_job():
                self.send_json(
                    {
                        "status": "busy",
                        "version": version,
                        "provider": provider,
                        "model": model,
                        "message": "Eval job is running, so live load/unload healthcheck was skipped.",
                        "health_check_mode": "load_unload",
                    },
                    status=200,
                )
                return

            loaded_before = None
            unload_status = "not_checked"
            loaded_after_unload = None
            loaded_after_probe = None
            unload_error = ""
            try:
                loaded_models = self.ollama_loaded_models(base_url)
                loaded_before = model in loaded_models
            except (urlerror.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
                unload_status = "ps_unavailable"
                unload_error = str(exc)

            should_unload = bool(model_spec.get("unload_after_health_check", True))
            try:
                self.ollama_probe_model(base_url, str(model))
                try:
                    loaded_after_probe = model in self.ollama_loaded_models(base_url)
                except (urlerror.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
                    loaded_after_probe = None
                    unload_error = str(exc)
            except (urlerror.HTTPError, urlerror.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
                self.send_json(
                    {
                        "status": "load_failed",
                        "version": version,
                        "provider": provider,
                        "model": model,
                        "message": f"Model tag exists, but live load check failed: {exc}",
                        "health_check_mode": "load_unload",
                        "loaded_before_health": loaded_before,
                        "loaded_after_probe": loaded_after_probe,
                    },
                    status=200,
                )
                return

            if should_unload:
                try:
                    self.ollama_unload_model(
                        base_url,
                        str(model),
                        timeout=MODEL_LIVE_HEALTH_TIMEOUT_SECONDS,
                    )
                    unload_status = "requested"
                    try:
                        loaded_after_unload = model in self.ollama_loaded_models(base_url)
                    except (urlerror.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
                        loaded_after_unload = None
                        unload_error = str(exc)
                except (urlerror.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
                    unload_status = "error"
                    unload_error = str(exc)
            else:
                unload_status = "disabled"

            if unload_status == "requested":
                message = "Model loaded successfully for healthcheck; an unload request was sent."
            elif unload_status == "disabled":
                message = "Model loaded successfully for healthcheck; unload is disabled for this config."
            else:
                message = "Model loaded successfully for healthcheck."
            self.send_json(
                {
                    "status": "ok",
                    "version": version,
                    "provider": provider,
                    "model": model,
                    "message": message,
                    "health_check_mode": "load_unload",
                    "loaded_before_health": loaded_before,
                    "loaded_after_probe": loaded_after_probe,
                    "unload_after_health_check": should_unload,
                    "unload_status": unload_status,
                    "loaded_after_unload": loaded_after_unload,
                    "unload_error": unload_error,
                }
            )
            return

        self.send_json(
            {
                "status": "missing_model",
                "version": version,
                "provider": provider,
                "model": model,
                "message": f"Model is not installed in Ollama at {base_url}.",
            },
            status=200,
        )

    def query_bool(self, params: dict[str, list[str]], name: str, default: bool = False) -> bool:
        raw = (params.get(name) or [""])[0]
        if raw == "":
            return default
        return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}

    def external_api_live_probe_request(self, model_spec: dict) -> tuple[str, dict]:
        model_spec = self.external_probe_model_spec(model_spec)
        provider = str(model_spec.get("provider") or "")
        model = str(model_spec.get("model") or "")
        messages = [{"role": "user", "content": "ping"}]
        if provider == "openai_native":
            return openai_responses_url(model_spec), {
                "model": model,
                "input": "ping",
                "max_output_tokens": 16,
                "store": False,
            }
        if provider == "openai_compatible":
            return openai_chat_url(model_spec), {
                "model": model,
                "messages": messages,
                "max_tokens": 1,
            }
        if provider == "clova_studio":
            return clova_chat_url(model_spec), clova_payload(
                messages=messages,
                options={"max_completion_tokens": 1, "includeAiFilters": False},
            )
        if provider == "anthropic":
            return anthropic_chat_url(model_spec), anthropic_payload(
                model=model,
                messages=messages,
                options={"max_tokens": 1},
            )
        if provider == "gemini":
            return gemini_chat_url(model_spec), gemini_payload(
                messages=messages,
                options={"maxOutputTokens": 1},
            )
        return str(model_spec.get("chat_url") or model_spec.get("api_url") or model_spec.get("base_url") or "").strip(), {
            "model": model,
            "messages": messages,
            "options": {"max_tokens": 1, "max_completion_tokens": 1, "max_output_tokens": 1},
        }

    def external_probe_model_spec(self, model_spec: dict) -> dict:
        spec = dict(model_spec)
        upstream_chat_url = self.external_http_url(spec.get("upstream_chat_url"))
        if upstream_chat_url:
            spec["chat_url"] = upstream_chat_url
        for key in ("chat_url", "api_url", "responses_url", "response_url"):
            value = self.external_http_url(spec.get(key))
            if value:
                spec[key] = value
            else:
                spec.pop(key, None)
        return spec

    def handle_external_api_health(self, version: str, model_spec: dict):
        health_url = self.external_http_url(model_spec.get("upstream_health_url"))
        provider = str(model_spec.get("provider") or "")
        headers = self.auth_headers(model_spec)
        if headers is None:
            env_error = self.api_key_env_name_error(model_spec.get("api_key_env"))
            self.send_json(
                {
                    "status": "missing_secret",
                    "version": version,
                    "provider": model_spec.get("provider"),
                    "model": model_spec.get("model"),
                    "message": env_error or f"Environment variable or stored server API key is not set: {model_spec.get('api_key_env')}",
                },
                status=200,
            )
            return
        is_live_probe = not bool(health_url)
        if is_live_probe:
            health_url, payload = self.external_api_live_probe_request(model_spec)
        else:
            payload = None
        health_url = self.external_http_url(health_url)
        if not health_url:
            self.send_json(
                {
                    "status": "missing_endpoint",
                    "version": version,
                    "provider": model_spec.get("provider"),
                    "model": model_spec.get("model"),
                    "message": "chat_url, base_url, or health_url is required for API health checks.",
                    "health_check_mode": "live_probe",
                },
                status=200,
            )
            return
        try:
            request_kwargs = {"method": "POST" if is_live_probe else "GET", "headers": headers}
            if payload is not None:
                request_kwargs["data"] = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            request = urlrequest.Request(health_url, **request_kwargs)
            with urlrequest.urlopen(request, timeout=MODEL_HEALTH_TIMEOUT_SECONDS) as response:
                self.send_json(
                    {
                        "status": "ok",
                        "version": version,
                        "provider": model_spec.get("provider"),
                        "model": model_spec.get("model"),
                        "message": (
                            f"Live model probe responded HTTP {response.status}."
                            if is_live_probe
                            else f"Health endpoint responded HTTP {response.status}."
                        ),
                        "health_check_mode": "live_probe" if is_live_probe else "health_endpoint",
                    }
                )
        except urlerror.HTTPError as exc:
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            body_preview = re.sub(r"\s+", " ", body).strip()[:600]
            if exc.code == 405 and not is_live_probe:
                status = "connected"
            elif exc.code in {401, 403}:
                status = "auth_failed"
            elif exc.code == 404:
                status = "endpoint_not_found"
            else:
                status = "offline"
            target_label = "Live model probe" if is_live_probe else "Health endpoint"
            self.send_json(
                {
                    "status": status,
                    "version": version,
                    "provider": model_spec.get("provider"),
                    "model": model_spec.get("model"),
                    "message": (
                        f"{target_label} was not found (HTTP 404). Check base_url/chat_url/health_url."
                        if exc.code == 404
                        else f"{target_label} rejected the configured API key or permission (HTTP {exc.code})."
                        if exc.code in {401, 403}
                        else f"{target_label} responded HTTP {exc.code}."
                    ),
                    "upstream_error": body_preview,
                    "health_check_mode": "live_probe" if is_live_probe else "health_endpoint",
                },
                status=200,
            )
        except (urlerror.URLError, TimeoutError, ValueError) as exc:
            self.send_json(
                {
                    "status": "offline",
                    "version": version,
                    "provider": model_spec.get("provider"),
                    "model": model_spec.get("model"),
                    "message": f"API is not reachable: {exc}",
                    "health_check_mode": "live_probe" if is_live_probe else "health_endpoint",
                },
                status=200,
            )

    def auth_headers(self, model_spec: dict):
        headers = {"Content-Type": "application/json"}
        provider = str(model_spec.get("provider") or "")
        if self.api_key_env_name_error(model_spec.get("api_key_env")):
            return None
        token, api_key_env = self.provider_api_key_value(model_spec)
        if api_key_env:
            if not token:
                return None
            if provider == "anthropic":
                headers["x-api-key"] = token
            elif provider == "gemini":
                headers["x-goog-api-key"] = token
            else:
                headers["Authorization"] = f"Bearer {token}"
        if provider == "anthropic":
            options = model_spec.get("options") if isinstance(model_spec.get("options"), dict) else {}
            headers["anthropic-version"] = str(
                model_spec.get("api_version") or options.get("anthropic_version") or "2023-06-01"
            )
        if provider == "clova_studio":
            headers["X-NCP-CLOVASTUDIO-REQUEST-ID"] = uuid.uuid4().hex
        return headers

    def ollama_base_url(self, model_spec: dict):
        explicit_env = str(model_spec.get("base_url_env") or "").strip()
        if explicit_env and os.environ.get(explicit_env):
            return os.environ[explicit_env].rstrip("/")
        configured = str(model_spec.get("base_url") or model_spec.get("ollama_base_url") or "").strip()
        if configured:
            return configured.rstrip("/")
        env_url, _ = provider_env_value({"provider": "ollama"}, "base_url")
        return str(env_url or OLLAMA_BASE_URL).rstrip("/")

    def ollama_models(self, base_url: str | None = None):
        resolved_base_url = str(base_url or OLLAMA_BASE_URL).rstrip("/")
        with urlrequest.urlopen(f"{resolved_base_url}/api/tags", timeout=MODEL_HEALTH_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
        return {item.get("name", "") for item in data.get("models", [])}

    def ollama_loaded_models(self, base_url: str | None = None):
        resolved_base_url = str(base_url or OLLAMA_BASE_URL).rstrip("/")
        with urlrequest.urlopen(f"{resolved_base_url}/api/ps", timeout=MODEL_HEALTH_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
        return {
            str(item.get("name") or item.get("model") or "")
            for item in data.get("models", [])
            if isinstance(item, dict)
        }

    def ollama_probe_model(self, base_url: str, model: str):
        payload = json.dumps(
            {
                "model": model,
                "prompt": "ping",
                "stream": False,
                "keep_alive": "30s",
                "options": {
                    "num_predict": 1,
                },
            }
        ).encode("utf-8")
        request = urlrequest.Request(
            f"{str(base_url).rstrip('/')}/api/generate",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urlrequest.urlopen(request, timeout=MODEL_LIVE_HEALTH_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}

    def ollama_unload_model(self, base_url: str, model: str, timeout: float | None = None):
        payload = json.dumps(
            {
                "model": model,
                "prompt": "",
                "stream": False,
                "keep_alive": 0,
            }
        ).encode("utf-8")
        request = urlrequest.Request(
            f"{str(base_url).rstrip('/')}/api/generate",
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urlrequest.urlopen(request, timeout=timeout or MODEL_HEALTH_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else {}

    def has_running_eval_job(self):
        with EVAL_JOBS_LOCK:
            return any(job.get("status") == "running" for job in EVAL_JOBS.values())

    def handle_dynamic_model_registry(self):
        self.send_json(self.load_registry())

    def handle_latest_run_file(self, filename: str, query: str = ""):
        requested_run_id = self.requested_run_id(query)
        if is_current_ui_data_run_id(requested_run_id) or (
            not requested_run_id and not self.explicit_run_id() and self.current_ui_data_run_summary(selected=False)
        ):
            exported_path = ROOT / "data" / filename
            if exported_path.exists():
                self.serve_path(exported_path, content_type="text/csv; charset=utf-8")
                return
            empty_csv = EMPTY_LATEST_RUN_CSV.get(filename)
            if empty_csv is not None:
                self.send_text(empty_csv, content_type="text/csv; charset=utf-8")
                return
            self.send_json({"error": "exported UI file not found", "file": filename}, status=404)
            return
        latest = self.run_dir_by_id(requested_run_id) if requested_run_id else self.latest_run_dir()
        if requested_run_id and not latest:
            self.send_json({"error": "unknown eval run", "run_id": requested_run_id}, status=404)
            return
        if latest:
            current_path = latest / filename
            if self.has_partitioned_run_source(latest) and self.projected_file_is_current(latest, filename):
                self.serve_path(current_path, content_type="text/csv; charset=utf-8")
                return
            projected = self.projected_run_csv(latest, filename)
            if projected is not None:
                self.send_text(projected, content_type="text/csv; charset=utf-8")
                return
        if latest and (latest / filename).exists():
            self.serve_path(latest / filename, content_type="text/csv; charset=utf-8")
            return
        exported_path = ROOT / "data" / filename
        if not requested_run_id and exported_path.exists():
            self.serve_path(exported_path, content_type="text/csv; charset=utf-8")
            return
        empty_csv = EMPTY_LATEST_RUN_CSV.get(filename)
        if empty_csv is not None:
            self.send_text(empty_csv, content_type="text/csv; charset=utf-8")
            return
        if requested_run_id:
            self.send_json({"error": "run file not found", "run_id": requested_run_id, "file": filename}, status=404)
            return
        self.serve_path(exported_path, content_type="text/csv; charset=utf-8")

    def projected_run_csv(self, run_dir: Path, filename: str) -> str | None:
        if filename not in {"eval_runs.csv", "question_cases.csv", "run_release_gates.csv", "regression_diff.csv"}:
            return None
        tables = self.projected_run_tables(run_dir)
        if not tables:
            return None
        key_by_filename = {
            "eval_runs.csv": "summary",
            "question_cases.csv": "question_rows",
            "run_release_gates.csv": "run_release_gates",
            "regression_diff.csv": "regression_diff",
        }
        rows = tables.get(key_by_filename[filename], [])
        return self.csv_text(rows, empty_csv=EMPTY_LATEST_RUN_CSV.get(filename, ""))

    def csv_text(self, rows: list[dict], *, empty_csv: str = "") -> str:
        if not rows:
            return empty_csv
        fieldnames: list[str] = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return buffer.getvalue()

    def has_partitioned_run_source(self, run_dir: Path) -> bool:
        return (run_dir / "by_target_model").is_dir() or (run_dir / "by_judge").is_dir()

    def projected_run_tables(self, run_dir: Path) -> dict | None:
        if not self.has_partitioned_run_source(run_dir):
            return None
        config = self.run_config(run_dir)
        cache_key = self.projected_run_cache_key(run_dir, config)
        with PROJECTED_RUN_TABLES_CACHE_LOCK:
            cached = PROJECTED_RUN_TABLES_CACHE.get(cache_key)
        if cached is not None:
            return cached
        tables = self.build_projected_run_tables(run_dir, config)
        if tables:
            with PROJECTED_RUN_TABLES_CACHE_LOCK:
                PROJECTED_RUN_TABLES_CACHE[cache_key] = tables
                while len(PROJECTED_RUN_TABLES_CACHE) > PROJECTED_RUN_TABLES_CACHE_MAX:
                    PROJECTED_RUN_TABLES_CACHE.pop(next(iter(PROJECTED_RUN_TABLES_CACHE)))
        return tables

    def build_projected_run_tables(self, run_dir: Path, config: dict) -> dict | None:
        cases = self.projected_run_cases(config)
        outputs = self.load_partitioned_outputs(run_dir)
        if not cases or not outputs:
            return None
        configs = self.projected_run_configs(config, outputs)
        if not configs:
            return None
        scores = self.projected_run_scores(run_dir, config, cases, configs, outputs)
        baseline_config = str(config.get("baseline_config") or (configs[0].get("config_id") if configs else ""))
        matrix = config.get("matrix") if isinstance(config.get("matrix"), dict) else {}
        release_gate_config = matrix.get("release_gates") if isinstance(matrix.get("release_gates"), dict) else {}
        eval_started_at = str(config.get("eval_started_at") or "")
        regression_diff = eval_build_regression_diff(cases=cases, scores=scores, baseline_config=baseline_config)
        summary = eval_aggregate_runs(
            run_id=run_dir.name,
            configs=configs,
            scores=scores,
            outputs=outputs,
            eval_started_at=eval_started_at,
        )
        run_release_gates = eval_aggregate_release_gates(
            run_id=run_dir.name,
            cases=cases,
            configs=configs,
            scores=scores,
            release_gate_config=release_gate_config,
        )
        if self.uses_sparse_output_projection(config, cases=cases, configs=configs, outputs=outputs):
            question_rows = self.sparse_question_case_rows(
                cases=cases,
                configs=configs,
                outputs=outputs,
                scores=scores,
                regression_diff=regression_diff,
            )
        else:
            question_rows = eval_question_case_rows(
                cases=cases,
                configs=configs,
                outputs=outputs,
                scores=scores,
                regression_diff=regression_diff,
            )
        return {
            "outputs": outputs,
            "scores": scores,
            "summary": summary,
            "regression_diff": regression_diff,
            "run_release_gates": run_release_gates,
            "question_rows": question_rows,
        }

    def projected_run_cache_key(self, run_dir: Path, config: dict) -> tuple:
        return (
            str(run_dir.resolve(strict=False)),
            self.projected_run_source_signatures(run_dir, config),
        )

    def projected_run_source_signatures(self, run_dir: Path, config: dict | None = None) -> tuple:
        config = config if isinstance(config, dict) else self.run_config(run_dir)
        paths: list[Path] = [self.run_config_path(run_dir), REGISTERED_TARGET_MODELS_PATH]
        case_source = str(config.get("case_source") or "").strip()
        if case_source:
            try:
                paths.append(self.resolve_project_path(case_source))
            except (OSError, ValueError):
                pass
        for pattern in (
            "by_target_model/*/model_outputs.jsonl",
            "by_target_model/*/normalized_answers.jsonl",
            "by_target_model/*/raw_responses.jsonl",
            "by_judge/*/judge_scores.jsonl",
            "by_judge/*/judge_scores.csv",
        ):
            paths.extend(sorted(run_dir.glob(pattern)))
        fallback_sources = [
            ("by_target_model", "model_outputs.jsonl"),
            ("by_judge", "judge_scores.jsonl"),
            ("by_judge", "judge_scores.csv"),
        ]
        for partition_dir, fallback_name in fallback_sources:
            path = run_dir / fallback_name
            if path.exists() and not (run_dir / partition_dir).is_dir():
                paths.append(path)
        return tuple(self.file_signature(path) for path in paths)

    def file_signature(self, path: Path) -> tuple[str, int, int]:
        resolved = str(path.resolve(strict=False))
        try:
            stat = path.stat()
        except OSError:
            return (resolved, 0, 0)
        return (resolved, stat.st_mtime_ns, stat.st_size)

    def projected_sources_mtime_ns(self, run_dir: Path, config: dict | None = None) -> int:
        signatures = self.projected_run_source_signatures(run_dir, config)
        return max((int(item[1]) for item in signatures), default=0)

    def projected_file_is_current(self, run_dir: Path, filename: str, config: dict | None = None) -> bool:
        path = run_dir / filename
        if not path.exists():
            return False
        try:
            return path.stat().st_mtime_ns >= self.projected_sources_mtime_ns(run_dir, config)
        except OSError:
            return False

    def projected_csv_rows_if_current(self, run_dir: Path, filename: str) -> list[dict] | None:
        if not self.has_partitioned_run_source(run_dir) or not self.projected_file_is_current(run_dir, filename):
            return None
        path = run_dir / filename
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                return list(csv.DictReader(handle))
        except (OSError, csv.Error, UnicodeDecodeError):
            return None

    def first_projected_question_row_if_current(self, run_dir: Path) -> dict | None:
        if not self.has_partitioned_run_source(run_dir) or not self.projected_file_is_current(run_dir, "question_cases.csv"):
            return None
        try:
            with (run_dir / "question_cases.csv").open("r", encoding="utf-8-sig", newline="") as handle:
                return next(csv.DictReader(handle), None)
        except (OSError, csv.Error, UnicodeDecodeError):
            return None

    def uses_sparse_output_projection(self, config: dict, *, cases: list[dict], configs: list[dict], outputs: list[dict]) -> bool:
        run_type = str(config.get("run_type") or "").lower()
        scoring_mode = str(config.get("scoring_mode") or "").lower()
        if "reconciled" in run_type or "arbiter_report" in run_type or "dual_judge_arbiter" in scoring_mode:
            return True
        expected_dense_rows = len(cases) * len(configs)
        return expected_dense_rows > 0 and len(outputs) < expected_dense_rows

    def sparse_question_case_rows(
        self,
        *,
        cases: list[dict],
        configs: list[dict],
        outputs: list[dict],
        scores: list[dict],
        regression_diff: list[dict],
    ) -> list[dict]:
        case_by_id = {str(case.get("case_id") or ""): case for case in cases}
        config_by_id = {str(config.get("config_id") or ""): config for config in configs}
        score_by_key = {(str(row.get("case_id") or ""), str(row.get("config_id") or "")): row for row in scores}
        diff_by_key = {
            (str(row.get("case_id") or ""), str(row.get("candidate_config") or "")): row
            for row in regression_diff
        }
        rows: list[dict] = []
        for output in outputs:
            case_id = str(output.get("case_id") or "")
            config_id = str(output.get("config_id") or "")
            if not case_id or not config_id:
                continue
            case = case_by_id.get(case_id) or {
                "case_id": case_id,
                "question": output.get("instruction", ""),
                "gold_answer": output.get("output", ""),
                "metadata": {},
            }
            config = config_by_id.get(config_id) or {
                "config_id": config_id,
                "model": output.get("model") or config_id,
            }
            score = score_by_key.get((case_id, config_id), {})
            diff = diff_by_key.get((case_id, config_id), {})
            rows.extend(
                eval_question_case_rows(
                    cases=[case],
                    configs=[config],
                    outputs=[output],
                    scores=[score],
                    regression_diff=[diff] if diff else [],
                )
            )
        return rows

    def projected_run_cases(self, config: dict) -> list[dict]:
        case_source = str(config.get("case_source") or "").strip()
        if not case_source:
            return []
        try:
            case_path = self.resolve_project_path(case_source)
            return eval_read_cases_path(case_path)
        except (OSError, csv.Error, json.JSONDecodeError, UnicodeDecodeError, ValueError):
            return []

    def projected_run_configs(self, config: dict, outputs: list[dict]) -> list[dict]:
        raw_configs = [item for item in config.get("configs", []) if isinstance(item, dict)]
        by_id = {str(item.get("config_id") or ""): dict(item) for item in raw_configs if item.get("config_id")}
        registry = self.load_registry()
        config_ids = sorted({str(row.get("config_id") or "") for row in outputs if row.get("config_id")})
        configs = []
        for config_id in config_ids:
            item = by_id.get(config_id) or registry.get(config_id) or {"config_id": config_id, "model": config_id}
            configs.append(dict(item))
        return configs

    def load_partitioned_outputs(self, run_dir: Path) -> list[dict]:
        target_root = run_dir / "by_target_model"
        rows: list[dict] = []
        if target_root.is_dir():
            for path in sorted(target_root.glob("*/model_outputs.jsonl")):
                rows.extend(eval_read_jsonl(path))
        if rows:
            return rows
        fallback = run_dir / "model_outputs.jsonl"
        return eval_read_jsonl(fallback) if fallback.exists() else []

    def load_partitioned_judge_rows(self, run_dir: Path) -> list[dict]:
        judge_root = run_dir / "by_judge"
        rows: list[dict] = []
        if judge_root.is_dir():
            for judge_dir in sorted(path for path in judge_root.iterdir() if path.is_dir()):
                jsonl_path = judge_dir / "judge_scores.jsonl"
                csv_path = judge_dir / "judge_scores.csv"
                if jsonl_path.exists():
                    rows.extend(eval_read_jsonl(jsonl_path))
                elif csv_path.exists():
                    rows.extend(self.read_csv_rows(csv_path))
        return rows

    def projected_run_scores(self, run_dir: Path, config: dict, cases: list[dict], configs: list[dict], outputs: list[dict]) -> list[dict]:
        case_by_id = {str(case.get("case_id") or ""): case for case in cases}
        config_by_id = {str(item.get("config_id") or ""): item for item in configs}
        settings = self.projected_scoring_settings(config, has_judge_rows=(run_dir / "by_judge").is_dir())
        judge_rows_by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for row in self.load_partitioned_judge_rows(run_dir):
            target_config_id = str(row.get("target_config_id") or row.get("config_id") or "").strip()
            case_id = str(row.get("case_id") or "").strip()
            if target_config_id and case_id:
                judge_rows_by_key[(target_config_id, case_id)].append(row)
        fallback_jsonl_path = run_dir / "judge_scores.jsonl"
        fallback_csv_path = run_dir / "judge_scores.csv"
        if fallback_jsonl_path.exists():
            fallback_rows = eval_read_jsonl(fallback_jsonl_path)
        elif fallback_csv_path.exists():
            fallback_rows = self.read_csv_rows(fallback_csv_path)
        else:
            fallback_rows = []
        fallback_scores = {
            (str(row.get("config_id") or ""), str(row.get("case_id") or "")): row
            for row in fallback_rows
        }
        scores = []
        for output in outputs:
            config_id = str(output.get("config_id") or "")
            case_id = str(output.get("case_id") or "")
            case = case_by_id.get(case_id)
            target_config = config_by_id.get(config_id)
            if not case or not target_config:
                fallback = fallback_scores.get((config_id, case_id))
                if fallback:
                    scores.append(dict(fallback))
                continue
            score = self.project_score_from_partition(
                case=case,
                output=output,
                target_config=target_config,
                judge_rows=judge_rows_by_key.get((config_id, case_id), []),
                settings=settings,
            )
            score.update({"run_id": output.get("run_id") or run_dir.name, "config_id": config_id, "case_id": case_id})
            scores.append(score)
        return scores

    def projected_scoring_settings(self, config: dict, *, has_judge_rows: bool) -> dict:
        matrix = config.get("matrix") if isinstance(config.get("matrix"), dict) else {}
        resolved = config.get("resolved_scoring") if isinstance(config.get("resolved_scoring"), dict) else {}
        judge_settings = matrix.get("llm_judge") if isinstance(matrix.get("llm_judge"), dict) else {}
        scoring_mode = str(resolved.get("scoring_mode") or matrix.get("scoring_mode") or ("llm_override" if has_judge_rows else "static")).strip()
        judge_mode = str(resolved.get("judge_mode") or judge_settings.get("mode") or ("override" if scoring_mode == "llm_override" else "audit")).strip()
        weights = resolved.get("judge_score_weights") or judge_settings.get("score_weights") or {}
        if isinstance(weights, str) and weights.strip():
            try:
                weights = json.loads(weights)
            except json.JSONDecodeError:
                weights = {}
        if not isinstance(weights, dict):
            weights = {}
        return {
            "scoring_mode": scoring_mode,
            "judge_mode": judge_mode,
            "judge_blend_weight": self.safe_float(
                resolved.get("judge_blend_weight", matrix.get("judge_blend_weight", 0.5)),
                default=0.5,
                minimum=0.0,
                maximum=1.0,
            ),
            "judge_aggregation_method": str(resolved.get("judge_aggregation_method") or judge_settings.get("aggregation_method") or "auto").strip(),
            "judge_score_weights": {str(key): self.safe_float(value, default=0.0, minimum=0.0, maximum=100000.0) for key, value in weights.items()},
            "pass_threshold": self.safe_float(
                resolved.get("pass_threshold", config.get("pass_threshold", matrix.get("pass_threshold", 0.6))),
                default=0.6,
                minimum=0.0,
                maximum=1.0,
            ),
        }

    def project_score_from_partition(self, *, case: dict, output: dict, target_config: dict, judge_rows: list[dict], settings: dict) -> dict:
        deterministic = eval_score_output(
            case=case,
            output=output,
            config=target_config,
            pass_threshold=settings["pass_threshold"],
            refusal_keywords=DEFAULT_REFUSAL_KEYWORDS,
            similarity_scorer=None,
        )
        if not judge_rows:
            return eval_attach_static_score_fields(dict(deterministic), deterministic, "static")
        judge_scores = [self.partition_judge_row_to_score(row) for row in judge_rows]
        aggregate = eval_aggregate_llm_judge_scores(
            judge_scores,
            score_weights=settings["judge_score_weights"],
            aggregation_method=settings["judge_aggregation_method"],
        )
        judge_config = {
            "config_id": aggregate.get("config_id", ""),
            "model": aggregate.get("model", ""),
            "provider": aggregate.get("provider", ""),
        }
        score = eval_apply_llm_judge(
            deterministic,
            aggregate,
            judge_config=judge_config,
            mode=settings["judge_mode"],
            blend_weight=settings["judge_blend_weight"],
            pass_threshold=settings["pass_threshold"],
            scoring_mode=settings["scoring_mode"],
        )
        score["output_fingerprint"] = output.get("output_fingerprint", "")
        score["score_fingerprint"] = next((row.get("score_fingerprint") for row in judge_rows if row.get("score_fingerprint")), "")
        return score

    def partition_judge_row_to_score(self, row: dict) -> dict:
        omnieval_scores = row.get("omnieval_scores") or row.get("llm_judge_omnieval_scores") or {}
        if isinstance(omnieval_scores, str):
            try:
                omnieval_scores = json.loads(omnieval_scores)
            except json.JSONDecodeError:
                omnieval_scores = {}
        score = {
            "config_id": row.get("judge_config_id") or row.get("llm_judge_config_id") or row.get("config_id", ""),
            "provider": row.get("judge_provider") or row.get("llm_judge_provider") or row.get("provider", ""),
            "model": row.get("judge_model") or row.get("llm_judge_model") or row.get("model", ""),
            "prompt_version": row.get("prompt_version", ""),
            "prompt_hash": row.get("prompt_hash", ""),
            "system_prompt_preset": row.get("system_prompt_preset", ""),
            "omnieval_accuracy": row.get("omnieval_accuracy", row.get("llm_judge_omnieval_accuracy", "")),
            "omnieval_completeness": row.get("omnieval_completeness", row.get("llm_judge_omnieval_completeness", "")),
            "omnieval_numerical_accuracy": row.get("omnieval_numerical_accuracy", row.get("llm_judge_omnieval_numerical_accuracy", "")),
            "omnieval_hallucination": row.get("omnieval_hallucination", row.get("llm_judge_omnieval_hallucination", "")),
            "omnieval_scores": omnieval_scores,
            **{key: self.safe_float(row.get(key), default=0.0, minimum=0.0, maximum=1.0) for key in SCORE_METRIC_KEYS},
            "applicable_metrics": row.get("applicable_metrics", ""),
            "score_denominator": row.get("score_denominator", ""),
            "raw_metric_score": row.get("raw_metric_score", ""),
            "answer_quality_score": row.get("answer_quality_score", ""),
            "rag_quality_score": row.get("rag_quality_score", ""),
            "overall_score": row.get("overall_score", ""),
            "pass": self.judge_bool_value(row.get("pass")),
            "critical_fail": self.judge_bool_value(row.get("critical_fail")),
            "error_type": row.get("error_type", ""),
            "reason": row.get("reason", ""),
        }
        if not score["applicable_metrics"] and isinstance(omnieval_scores, dict):
            applicable_metrics = ["acc"]
            if self.safe_int(omnieval_scores.get("completeness"), default=-1, minimum=-1, maximum=2) >= 0:
                applicable_metrics.append("com")
            if self.safe_int(omnieval_scores.get("numerical_accuracy"), default=-1, minimum=-1, maximum=1) >= 0:
                applicable_metrics.append("nac")
            applicable_metrics.append("hal_pass")
            score["applicable_metrics"] = ",".join(applicable_metrics)
        if score["overall_score"] in ("", None):
            score["applicable_metrics"] = ",".join(eval_metric_keys_for_score(score))
            score["score_denominator"] = eval_score_denominator(score)
            score["raw_metric_score"] = eval_raw_metric_score(score)
            score["overall_score"] = eval_score_total_from_metrics(score)
        return score

    def write_projected_run_files(self, run_dir: Path) -> bool:
        tables = self.projected_run_tables(run_dir)
        if not tables:
            return False
        eval_write_jsonl(run_dir / "model_outputs.jsonl", tables["outputs"])
        eval_write_jsonl(run_dir / "judge_scores.jsonl", tables["scores"])
        eval_write_jsonl(run_dir / "regression_diff.jsonl", tables["regression_diff"])
        eval_write_jsonl(run_dir / "run_release_gates.jsonl", tables["run_release_gates"])
        eval_write_csv(run_dir / "model_outputs.csv", tables["outputs"])
        eval_write_csv(run_dir / "judge_scores.csv", tables["scores"])
        eval_write_csv(run_dir / "regression_diff.csv", tables["regression_diff"])
        eval_write_csv(run_dir / "run_release_gates.csv", tables["run_release_gates"])
        eval_write_csv(run_dir / "eval_runs.csv", tables["summary"])
        eval_write_csv(run_dir / "question_cases.csv", tables["question_rows"])
        return True

    def handle_latest_run(self, query: str = ""):
        requested_run_id = self.requested_run_id(query)
        if is_current_ui_data_run_id(requested_run_id):
            summary = self.current_ui_data_run_summary(selected=True)
            if not summary:
                self.send_json({"status": "missing", "message": "No exported UI data found."}, status=404)
                return
            self.send_json(
                {
                    "status": "ok",
                    **summary,
                    "path": str(ROOT / "data"),
                    "case_source": "ui_runtime_export",
                    "uses_final_question_sets": True,
                    "baseline_config": "",
                    "judge_config_ids": [],
                    "files": {
                        "eval_runs": "/data/eval_runs.csv",
                        "question_cases": "/data/question_cases.csv",
                        "run_release_gates": "/data/run_release_gates.csv",
                        "regression_diff": "/data/regression_diff.csv",
                        "report_html": "/report/regression_report.html",
                        "report_raw_html": "",
                        "report_ui": "/#overview",
                    },
                }
            )
            return
        if not requested_run_id and not self.explicit_run_id():
            summary = self.current_ui_data_run_summary(selected=True)
            if summary:
                self.send_json(
                    {
                        "status": "ok",
                        **summary,
                        "path": str(ROOT / "data"),
                        "case_source": "ui_runtime_export",
                        "uses_final_question_sets": True,
                        "baseline_config": "",
                        "judge_config_ids": [],
                        "files": {
                            "eval_runs": "/data/eval_runs.csv",
                            "question_cases": "/data/question_cases.csv",
                            "run_release_gates": "/data/run_release_gates.csv",
                            "regression_diff": "/data/regression_diff.csv",
                            "report_html": "/report/regression_report.html",
                            "report_raw_html": "",
                            "report_ui": "/#overview",
                        },
                    }
                )
                return
        latest = self.run_dir_by_id(requested_run_id) if requested_run_id else self.latest_run_dir()
        if requested_run_id and not latest:
            self.send_json({"status": "missing", "error": "unknown eval run", "run_id": requested_run_id}, status=404)
            return
        if not latest:
            self.send_json({"status": "missing", "message": "No eval run found."})
            return
        config = self.run_config(latest)
        case_source = config.get("case_source", "")
        uses_final_sets = self.run_uses_final_question_sets(latest)
        judge_summary = self.latest_judge_summary(latest, config)
        self.send_json(
            {
                "status": "ok",
                "run_id": latest.name,
                "path": str(latest),
                "updated_at": latest.stat().st_mtime,
                "case_source": case_source,
                "uses_final_question_sets": uses_final_sets,
                "case_source_status": "final" if uses_final_sets else "previous",
                "baseline_config": config.get("baseline_config", ""),
                "scoring_mode": judge_summary.get("scoring_mode", ""),
                "judge_config_ids": judge_summary.get("judge_config_ids", []),
                "llm_judge_count": judge_summary.get("llm_judge_count", 0),
                "llm_judge_provider": judge_summary.get("llm_judge_provider", ""),
                "llm_judge_model": judge_summary.get("llm_judge_model", ""),
                "files": {
                    "eval_runs": f"/data/eval_runs.csv?run_id={latest.name}",
                    "question_cases": f"/data/question_cases.csv?run_id={latest.name}",
                    "run_release_gates": f"/data/run_release_gates.csv?run_id={latest.name}",
                    "regression_diff": f"/data/regression_diff.csv?run_id={latest.name}",
                    "report_html": f"/report/regression_report.html?run_id={latest.name}",
                    "report_raw_html": f"/report/raw_regression_report.html?run_id={latest.name}",
                    "report_ui": f"/?run_id={latest.name}#overview",
                },
            }
        )

    def handle_eval_runs(self):
        self.send_json({"status": "ok", "runs": self.eval_run_summaries()})

    def handle_eval_case_summary(self, query: str = ""):
        run_id = self.requested_run_id(query) or self.default_selected_run_id()
        if not run_id:
            self.send_json({"status": "missing", "message": "No eval run found."}, status=404)
            return
        try:
            cache_path = self.ensure_eval_case_summary_cache_path(run_id)
        except FileNotFoundError:
            self.send_json({"status": "missing", "error": "question_cases source not found", "run_id": run_id}, status=404)
            return
        except (OSError, csv.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.send_json({"status": "error", "error": str(exc), "run_id": run_id}, status=500)
            return
        if is_current_ui_data_run_id(run_id):
            try:
                self.send_json(self.eval_case_summary_payload(run_id))
            except (OSError, csv.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
                self.send_json({"status": "error", "error": str(exc), "run_id": run_id}, status=500)
            return
        self.serve_path(cache_path, content_type="application/json; charset=utf-8")

    def handle_eval_case_detail(self, query: str = ""):
        params = parse_qs(query or "")
        run_id = self.requested_run_id(query) or self.default_selected_run_id()
        question_id = str((params.get("question_id") or params.get("case_id") or [""])[0]).strip()
        version = str((params.get("version") or params.get("model") or [""])[0]).strip()
        if not question_id or not version:
            self.send_json({"status": "error", "error": "question_id and version are required"}, status=400)
            return
        source = self.eval_case_summary_source(run_id)
        if not source:
            self.send_json({"status": "missing", "error": "question_cases source not found", "run_id": run_id}, status=404)
            return
        try:
            row = self.find_eval_case_detail_row(source, question_id, version)
        except (OSError, csv.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.send_json({"status": "error", "error": str(exc), "run_id": run_id}, status=500)
            return
        if row is None:
            self.send_json(
                {"status": "missing", "error": "case detail not found", "run_id": source["run_id"], "question_id": question_id, "version": version},
                status=404,
            )
            return
        self.send_json({"status": "ok", "run_id": source["run_id"], "question_id": question_id, "version": version, "row": row})

    def find_eval_case_detail_row(self, source: dict, question_id: str, version: str) -> dict | None:
        for row in self.iter_eval_case_summary_rows(source):
            row_case_id = str(row.get("question_id") or row.get("case_id") or "").strip()
            row_version = str(row.get("version") or row.get("model") or "").strip()
            if row_case_id == question_id and row_version == version:
                return dict(row)
        return None

    def ensure_eval_case_summary_cache_path(self, run_id: str) -> Path:
        source = self.eval_case_summary_source(run_id)
        if not source:
            raise FileNotFoundError(run_id)
        cache_key, _ = self.eval_case_summary_cache_key(source)
        cache_path = self.ui_case_summary_cache_path(cache_key)
        if cache_path.exists():
            self.ensure_gzip_sidecar(cache_path)
            return cache_path
        with UI_CASE_SUMMARY_CACHE_LOCK:
            if cache_path.exists():
                self.ensure_gzip_sidecar(cache_path)
                return cache_path
            payload = self.build_eval_case_summary_payload(source, cache_key)
            self.write_ui_case_summary_cache(cache_key, payload)
        if not cache_path.exists():
            raise OSError(f"failed to write UI case summary cache: {cache_path}")
        return cache_path

    def eval_case_summary_cache_key(self, source: dict) -> tuple[str, dict]:
        source_key = {
            "version": UI_CASE_SUMMARY_CACHE_VERSION,
            "run_id": source.get("cache_run_id") or source["run_id"],
            "source_kind": source["source_kind"],
            "source_signature": source["source_signature"],
        }
        key_text = json.dumps(source_key, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(key_text.encode("utf-8")).hexdigest(), source_key

    def eval_case_summary_payload(self, run_id: str) -> dict:
        source = self.eval_case_summary_source(run_id)
        if not source:
            raise FileNotFoundError(run_id)
        cache_key, _ = self.eval_case_summary_cache_key(source)

        with UI_CASE_SUMMARY_CACHE_LOCK:
            cached = UI_CASE_SUMMARY_MEMORY_CACHE.get(cache_key)
        if cached is not None:
            return self.normalize_eval_case_summary_payload(dict(cached), source)

        disk_payload = self.read_ui_case_summary_cache(cache_key)
        if disk_payload is not None:
            normalized_payload = self.normalize_eval_case_summary_payload(dict(disk_payload), source)
            with UI_CASE_SUMMARY_CACHE_LOCK:
                UI_CASE_SUMMARY_MEMORY_CACHE[cache_key] = normalized_payload
                self.trim_ui_case_summary_memory_cache()
            return normalized_payload

        payload = self.build_eval_case_summary_payload(source, cache_key)
        self.write_ui_case_summary_cache(cache_key, payload)
        with UI_CASE_SUMMARY_CACHE_LOCK:
            UI_CASE_SUMMARY_MEMORY_CACHE[cache_key] = payload
            self.trim_ui_case_summary_memory_cache()
        return payload

    def normalize_eval_case_summary_payload(self, payload: dict, source: dict) -> dict:
        payload["run_id"] = source["run_id"]
        payload["source_label"] = source.get("source_label", payload.get("source_label", ""))
        return payload

    def build_eval_case_summary_payload(self, source: dict, cache_key: str) -> dict:
        compact_rows = [self.compact_ui_case_row(row) for row in self.iter_eval_case_summary_rows(source)]
        columns = [
            field
            for field in UI_CASE_SUMMARY_FIELDS
            if any(field in row for row in compact_rows)
        ]
        rows = [[row.get(column, "") for column in columns] for row in compact_rows]
        dictionaries = self.dictionary_encode_case_summary_rows(columns, rows)
        question_ids = {
            row.get("question_id") or row.get("case_id")
            for row in compact_rows
            if row.get("question_id") or row.get("case_id")
        }
        model_ids = {row.get("version") for row in compact_rows if row.get("version")}
        payload = {
            "status": "ok",
            "format": "compact_case_summary_table_dict",
            "version": UI_CASE_SUMMARY_CACHE_VERSION,
            "run_id": source["run_id"],
            "source_kind": source["source_kind"],
            "source_label": source.get("source_label", ""),
            "cache_key": cache_key,
            "source_signature": source["source_signature"],
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "row_count": len(rows),
            "unique_question_count": len(question_ids),
            "model_count": len(model_ids),
            "columns": columns,
            "dictionaries": dictionaries,
            "rows": rows,
        }
        return payload

    def dictionary_encode_case_summary_rows(self, columns: list[str], rows: list[list]) -> dict:
        dictionaries: dict[str, list[str]] = {}
        for column_index, column in enumerate(columns):
            if column in UI_CASE_SUMMARY_NUMERIC_FIELDS:
                continue
            values = [
                row[column_index]
                for row in rows
                if column_index < len(row) and isinstance(row[column_index], str) and row[column_index] != ""
            ]
            if len(values) < 100:
                continue
            unique_values = list(dict.fromkeys(values))
            raw_chars = sum(len(value) for value in values)
            dict_chars = sum(len(value) for value in unique_values)
            repeated_enough = len(unique_values) <= max(32, int(len(values) * 0.75))
            saves_enough = raw_chars - dict_chars >= len(values) * 2
            if not repeated_enough or not saves_enough:
                continue
            value_to_index = {value: index + 1 for index, value in enumerate(unique_values)}
            for row in rows:
                value = row[column_index] if column_index < len(row) else ""
                row[column_index] = value_to_index.get(value, 0) if value else 0
            dictionaries[column] = unique_values
        return dictionaries

    def eval_case_summary_source(self, run_id: str) -> dict | None:
        run_id = str(run_id or "").strip() or self.default_selected_run_id()
        if is_current_ui_data_run_id(run_id):
            path = ROOT / "data" / "question_cases.csv"
            if not path.exists():
                return None
            return {
                "run_id": CURRENT_UI_DATA_RUN_ID,
                "cache_run_id": LEGACY_UI_DATA_RUN_ID,
                "source_kind": "file",
                "source_label": "ui_runtime_data/question_cases.csv",
                "path": path,
                "source_signature": self.file_signature(path),
            }
        run_dir = self.run_dir_by_id(run_id)
        if not run_dir:
            return None
        current_path = run_dir / "question_cases.csv"
        if self.has_partitioned_run_source(run_dir) and not self.projected_file_is_current(run_dir, "question_cases.csv"):
            config = self.run_config(run_dir)
            return {
                "run_id": run_dir.name,
                "source_kind": "projected",
                "source_label": f"{run_dir.name}/projected question_cases",
                "run_dir": run_dir,
                "config": config,
                "source_signature": self.projected_run_cache_key(run_dir, config),
            }
        if current_path.exists():
            return {
                "run_id": run_dir.name,
                "source_kind": "file",
                "source_label": f"{run_dir.name}/question_cases.csv",
                "path": current_path,
                "source_signature": self.file_signature(current_path),
            }
        return None

    def iter_eval_case_summary_rows(self, source: dict):
        if source.get("source_kind") == "projected":
            tables = self.projected_run_tables(source["run_dir"])
            for row in (tables or {}).get("question_rows", []):
                yield row
            return
        path = source.get("path")
        if not path:
            return
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            yield from csv.DictReader(handle)

    def compact_ui_case_row(self, row: dict) -> dict:
        compact: dict = {}
        aliases = {
            "case_id": row.get("case_id") or row.get("question_id"),
            "question_id": row.get("question_id") or row.get("case_id"),
            "question": row.get("question") or row.get("instruction"),
            "instruction": row.get("instruction") or row.get("question"),
            "source_type": row.get("source_type") or row.get("qa_category"),
            "qa_category": row.get("qa_category") or row.get("source_type"),
            "qa_matrix_topic": row.get("qa_matrix_topic") or row.get("qa_topic"),
            "qa_topic": row.get("qa_topic") or row.get("qa_matrix_topic"),
        }
        for field in UI_CASE_SUMMARY_FIELDS:
            value = aliases.get(field, row.get(field))
            if value is None or value == "":
                continue
            if field in UI_CASE_SUMMARY_NUMERIC_FIELDS:
                compact[field] = self.compact_number(value)
                continue
            text = str(value)
            limit = UI_CASE_SUMMARY_TEXT_LIMITS.get(field)
            if limit and len(text) > limit:
                text = text[:limit].rstrip() + "..."
            compact[field] = text
        return compact

    def compact_number(self, value):
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0
        if number.is_integer():
            return int(number)
        return round(number, 4)

    def ui_case_summary_cache_path(self, cache_key: str) -> Path:
        safe_key = re.sub(r"[^a-f0-9]", "", str(cache_key).lower())[:64]
        return UI_CASE_SUMMARY_CACHE_ROOT / f"{safe_key}.json"

    def read_ui_case_summary_cache(self, cache_key: str) -> dict | None:
        path = self.ui_case_summary_cache_path(cache_key)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None
        if payload.get("cache_key") != cache_key or payload.get("version") != UI_CASE_SUMMARY_CACHE_VERSION:
            return None
        if not isinstance(payload.get("rows"), list):
            return None
        return payload

    def write_ui_case_summary_cache(self, cache_key: str, payload: dict) -> None:
        path = self.ui_case_summary_cache_path(cache_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(".tmp")
        cache_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        try:
            with tmp_path.open("w", encoding="utf-8") as handle:
                handle.write(cache_text)
            tmp_path.replace(path)
            self.ensure_gzip_sidecar(path)
        except OSError:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            try:
                path.write_text(cache_text, encoding="utf-8")
                self.ensure_gzip_sidecar(path)
            except OSError:
                pass

    def gzip_sidecar_path(self, path: Path) -> Path:
        return path.with_name(f"{path.name}.gz")

    def gzip_sidecar_is_current(self, path: Path, gzip_path: Path) -> bool:
        try:
            return gzip_path.exists() and gzip_path.stat().st_mtime_ns >= path.stat().st_mtime_ns
        except OSError:
            return False

    def ensure_gzip_sidecar(self, path: Path) -> Path | None:
        if not path.exists():
            return None
        gzip_path = self.gzip_sidecar_path(path)
        if self.gzip_sidecar_is_current(path, gzip_path):
            return gzip_path
        tmp_path = gzip_path.with_name(f"{gzip_path.name}.tmp")
        try:
            with path.open("rb") as source, tmp_path.open("wb") as raw_target, gzip.GzipFile(fileobj=raw_target, mode="wb", compresslevel=6, mtime=0) as target:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    target.write(chunk)
            tmp_path.replace(gzip_path)
            return gzip_path
        except OSError:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            return None

    def trim_ui_case_summary_memory_cache(self) -> None:
        while len(UI_CASE_SUMMARY_MEMORY_CACHE) > UI_CASE_SUMMARY_MEMORY_CACHE_MAX:
            UI_CASE_SUMMARY_MEMORY_CACHE.pop(next(iter(UI_CASE_SUMMARY_MEMORY_CACHE)))

    def handle_judge_comparison_options(self):
        self.send_json(
            {
                "status": "ok",
                "baseline_sources": self.judge_comparison_baseline_sources(),
                "judge_runs": self.judge_comparison_run_sources(),
                "comparison_reports": self.judge_comparison_report_sources(),
            }
        )

    def handle_judge_comparison_artifact(self, query: str = ""):
        raw_path = parse_qs(query or "").get("path", [""])[0]
        if not raw_path:
            self.send_json({"error": "artifact path is required"}, status=400)
            return
        try:
            path = self.resolve_project_path(raw_path)
            path.resolve(strict=False).relative_to(EVAL_RUNS_ROOT.resolve(strict=False))
        except (ValueError, OSError) as exc:
            self.send_json({"error": str(exc)}, status=400)
            return
        suffix = path.suffix.lower()
        content_type = {
            ".md": "text/markdown; charset=utf-8",
            ".csv": "text/csv; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".jsonl": "application/x-ndjson; charset=utf-8",
        }.get(suffix, "text/plain; charset=utf-8")
        self.serve_path(path, content_type=content_type)

    def handle_create_judge_comparison(self):
        payload = self.read_json_body()
        if payload is None:
            self.send_json_body_error()
            return
        baseline_source_id = str(payload.get("baseline_source_id") or "").strip()
        baseline_judge_config_id = str(payload.get("baseline_judge_config_id") or "").strip()
        candidate_run_id = str(payload.get("candidate_run_id") or "").strip()
        candidate_judge_config_id = str(payload.get("candidate_judge_config_id") or "").strip()
        if not baseline_source_id or not baseline_judge_config_id or not candidate_run_id:
            self.send_json(
                {"error": "baseline_source_id, baseline_judge_config_id, candidate_run_id are required"},
                status=400,
            )
            return
        baseline_path, baseline_label = self.resolve_judge_comparison_baseline(baseline_source_id)
        if not baseline_path or not baseline_path.exists():
            self.send_json({"error": f"baseline question_cases.csv not found: {baseline_source_id}"}, status=404)
            return
        candidate_dir = self.resolve_judge_score_run_dir(candidate_run_id)
        if not candidate_dir:
            self.send_json({"error": f"candidate judge run not found: {candidate_run_id}"}, status=404)
            return
        candidate_judges = self.judge_score_run_summary(candidate_dir).get("judge_configs", [])
        candidate_judge_ids = [str(item.get("config_id") or "").strip() for item in candidate_judges if item.get("config_id")]
        if not candidate_judge_config_id and len(candidate_judge_ids) == 1:
            candidate_judge_config_id = candidate_judge_ids[0]
        if not candidate_judge_config_id:
            self.send_json({"error": "candidate_judge_config_id is required when a candidate run has multiple judges"}, status=400)
            return
        if candidate_judge_config_id not in candidate_judge_ids:
            self.send_json({"error": f"candidate judge not found in run: {candidate_judge_config_id}"}, status=404)
            return
        score_gap_mode = str(payload.get("score_gap_mode") or "points").strip().lower()
        if score_gap_mode not in {"points", "relative_percent"}:
            score_gap_mode = "points"
        threshold_default = 30.0 if score_gap_mode == "relative_percent" else 0.3
        threshold_max = 10000.0 if score_gap_mode == "relative_percent" else 1.0
        threshold = self.safe_float(payload.get("score_gap_threshold"), default=threshold_default, minimum=0.0, maximum=threshold_max)
        include_error_type = self.judge_bool_value(payload.get("include_error_type_mismatch", False))
        normalize_error_type = True
        if "normalize_error_type" in payload:
            normalize_error_type = self.judge_bool_value(payload.get("normalize_error_type"))
        arbiter_judge_config_id = str(payload.get("arbiter_judge_config_id") or "").strip()
        default_comparison_id = self.default_judge_comparison_id(
            baseline_judge_config_id=baseline_judge_config_id,
            candidate_judge_config_id=candidate_judge_config_id,
            candidate_run_id=candidate_dir.name,
        )
        comparison_id = self.safe_run_id(payload.get("comparison_id") or default_comparison_id)
        out_dir = candidate_dir / "judge_comparisons" / comparison_id
        try:
            result = self.build_judge_comparison_report(
                baseline_path=baseline_path,
                baseline_label=baseline_label,
                baseline_judge_config_id=baseline_judge_config_id,
                candidate_dir=candidate_dir,
                candidate_judge_config_id=candidate_judge_config_id,
                out_dir=out_dir,
                score_gap_threshold=threshold,
                score_gap_mode=score_gap_mode,
                include_error_type_mismatch=include_error_type,
                normalize_error_type=normalize_error_type,
                arbiter_judge_config_id=arbiter_judge_config_id,
            )
        except (OSError, RuntimeError) as exc:
            self.send_json({"error": str(exc)}, status=400)
            return
        self.send_json({"status": "ok", **result})

    def default_judge_comparison_id(self, *, baseline_judge_config_id: str, candidate_judge_config_id: str, candidate_run_id: str) -> str:
        judge_key = self.safe_run_id(baseline_judge_config_id).replace("_judge", "")
        candidate_judge_key = self.safe_run_id(candidate_judge_config_id).replace("_judge", "")
        candidate_key = hashlib.sha1(candidate_run_id.encode("utf-8")).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"cmp_{judge_key[:24]}_vs_{candidate_judge_key[:24]}_{candidate_key}_{timestamp}"

    def judge_comparison_baseline_sources(self):
        sources = []
        exported = ROOT / "data" / "question_cases.csv"
        if exported.exists():
            sources.append(
                self.judge_comparison_baseline_summary(
                    CURRENT_UI_DATA_RUN_ID,
                    "현재 UI 데이터",
                    exported,
                    selected=True,
                )
            )
        if EVAL_RUNS_ROOT.exists():
            candidates = [path for path in EVAL_RUNS_ROOT.iterdir() if self.is_eval_run_dir(path)]
            candidates.sort(key=self.run_sort_key, reverse=True)
            for path in candidates:
                sources.append(self.judge_comparison_baseline_summary_for_run(path, selected=False))
        return [source for source in sources if source.get("judge_configs")]

    def judge_comparison_run_sources(self):
        sources = []
        if not EVAL_RUNS_ROOT.exists():
            return sources
        candidates = [
            path
            for path in EVAL_RUNS_ROOT.iterdir()
            if path.is_dir()
            and (
                (path / "judge_scores.jsonl").exists()
                or (path / "judge_scores.csv").exists()
                or (path / "by_judge").is_dir()
            )
        ]
        candidates.sort(key=self.run_sort_key, reverse=True)
        for path in candidates:
            sources.append(self.judge_score_run_summary(path))
        return sorted(
            [source for source in sources if source.get("ok_rows")],
            key=lambda source: (int(source.get("ok_rows") or 0), float(source.get("updated_at") or 0)),
            reverse=True,
        )

    def judge_comparison_report_sources(self):
        reports = []
        if not EVAL_RUNS_ROOT.exists():
            return reports
        for summary_path in sorted(EVAL_RUNS_ROOT.glob("*/judge_comparisons/*/judge_comparison_summary.json")):
            try:
                summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                continue
            report_dir = summary_path.parent
            report_path = report_dir / "judge_score_diff_report.md"
            if not report_path.exists():
                report_path = report_dir / "judge_comparison_report.md"
            reports.append(
                {
                    "id": f"{summary_path.parents[2].name}/{report_dir.name}",
                    "run_id": summary_path.parents[2].name,
                    "comparison_id": report_dir.name,
                    "updated_at": summary_path.stat().st_mtime,
                    "matched_rows": self.safe_int(summary.get("matched_rows"), default=0, minimum=0, maximum=1000000),
                    "arbiter_candidate_rows": self.safe_int(summary.get("arbiter_candidate_rows"), default=0, minimum=0, maximum=1000000),
                    "arbiter_existing_candidate_rows": self.safe_int(summary.get("arbiter_existing_candidate_rows"), default=0, minimum=0, maximum=1000000),
                    "arbiter_missing_rows": self.safe_int(summary.get("arbiter_missing_rows"), default=0, minimum=0, maximum=1000000),
                    "score_gap_threshold": summary.get("score_gap_threshold", ""),
                    "score_gap_mode": summary.get("score_gap_mode", ""),
                    "include_error_type_mismatch": bool(summary.get("include_error_type_mismatch")),
                    "summary_url": "/api/eval/judge-comparison/artifact?path=" + self.display_path(summary_path).replace("\\", "/"),
                    "report_url": "/api/eval/judge-comparison/artifact?path=" + self.display_path(report_path).replace("\\", "/") if report_path.exists() else "",
                }
            )
        reports.sort(key=lambda item: float(item.get("updated_at") or 0), reverse=True)
        return reports

    def judge_comparison_baseline_summary(self, source_id: str, label: str, path: Path, *, selected: bool):
        judge_counts, rows = self.question_cases_judge_counts(path)
        return {
            "source_id": source_id,
            "label": label,
            "path": self.display_path(path),
            "selected": selected,
            "rows": rows,
            "judge_configs": [
                {"config_id": config_id, "rows": count}
                for config_id, count in judge_counts.most_common()
            ],
        }

    def judge_comparison_baseline_summary_for_run(self, path: Path, *, selected: bool):
        if self.has_partitioned_run_source(path):
            judge_counts, rows = self.partitioned_run_judge_counts(path)
            if judge_counts:
                return {
                    "source_id": path.name,
                    "label": path.name,
                    "path": self.display_path(path / "question_cases.csv"),
                    "selected": selected,
                    "rows": rows,
                    "judge_configs": [
                        {"config_id": config_id, "rows": count}
                        for config_id, count in judge_counts.most_common()
                    ],
                }
        return self.judge_comparison_baseline_summary(
            path.name,
            path.name,
            path / "question_cases.csv",
            selected=selected,
        )

    def partitioned_run_judge_counts(self, path: Path):
        counts = Counter()
        judge_root = path / "by_judge"
        if judge_root.is_dir():
            for judge_dir in sorted(item for item in judge_root.iterdir() if item.is_dir()):
                jsonl_path = judge_dir / "judge_scores.jsonl"
                csv_path = judge_dir / "judge_scores.csv"
                config_id = judge_dir.name
                count = self.count_jsonl_rows(jsonl_path) if jsonl_path.exists() else self.count_csv_rows(csv_path)
                if config_id and count:
                    counts[config_id] += count
        rows = self.partitioned_output_row_count(path) or (max(counts.values()) if counts else 0)
        return counts, rows

    def partitioned_output_row_count(self, path: Path) -> int:
        target_root = path / "by_target_model"
        if not target_root.is_dir():
            fallback = path / "model_outputs.jsonl"
            return self.count_jsonl_rows(fallback) if fallback.exists() else 0
        return sum(self.count_jsonl_rows(output_path) for output_path in sorted(target_root.glob("*/model_outputs.jsonl")))

    def count_jsonl_rows(self, path: Path) -> int:
        try:
            with path.open("r", encoding="utf-8") as handle:
                return sum(1 for line in handle if line.strip())
        except OSError:
            return 0

    def count_csv_rows(self, path: Path) -> int:
        if not path.exists():
            return 0
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle)
                try:
                    next(reader)
                except StopIteration:
                    return 0
                return sum(1 for _ in reader)
        except (OSError, csv.Error, UnicodeDecodeError):
            return 0

    def read_csv_rows(self, path: Path) -> list[dict]:
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                return list(csv.DictReader(handle))
        except (OSError, csv.Error, UnicodeDecodeError):
            return []

    def judge_score_run_summary(self, path: Path):
        cache_key = (
            str(path.resolve(strict=False)),
            self.judge_score_source_signatures(path),
        )
        with JUDGE_SCORE_RUN_SUMMARY_CACHE_LOCK:
            cached = JUDGE_SCORE_RUN_SUMMARY_CACHE.get(cache_key)
        if cached is not None:
            return dict(cached)
        summary = self.build_judge_score_run_summary(path)
        with JUDGE_SCORE_RUN_SUMMARY_CACHE_LOCK:
            JUDGE_SCORE_RUN_SUMMARY_CACHE[cache_key] = dict(summary)
            while len(JUDGE_SCORE_RUN_SUMMARY_CACHE) > JUDGE_SCORE_RUN_SUMMARY_CACHE_MAX:
                JUDGE_SCORE_RUN_SUMMARY_CACHE.pop(next(iter(JUDGE_SCORE_RUN_SUMMARY_CACHE)))
        return summary

    def judge_score_source_signatures(self, path: Path) -> tuple:
        paths = []
        judge_root = path / "by_judge"
        if judge_root.is_dir():
            for judge_dir in sorted(item for item in judge_root.iterdir() if item.is_dir()):
                jsonl_path = judge_dir / "judge_scores.jsonl"
                csv_path = judge_dir / "judge_scores.csv"
                if jsonl_path.exists():
                    paths.append(jsonl_path)
                elif csv_path.exists():
                    paths.append(csv_path)
        fallback_jsonl = path / "judge_scores.jsonl"
        fallback_csv = path / "judge_scores.csv"
        if fallback_jsonl.exists():
            paths.append(fallback_jsonl)
        elif fallback_csv.exists():
            paths.append(fallback_csv)
        return tuple(self.file_signature(item) for item in paths)

    def build_judge_score_run_summary(self, path: Path):
        config_counts = Counter()
        status_counts = Counter()
        row_count = 0
        ok_rows = 0
        for row in self.iter_judge_score_rows(path):
            row_count += 1
            status = str(row.get("source_llm_judge_status") or row.get("llm_judge_status") or "ok").strip().lower()
            status_counts[status or "unknown"] += 1
            if status == "ok" or self.judge_score_row_has_usable_score(row):
                ok_rows += 1
                config_id = str(row.get("llm_judge_config_id") or row.get("judge_config_id") or "").strip()
                if config_id:
                    config_counts[config_id] += 1
        return {
            "run_id": path.name,
            "label": path.name,
            "path": self.display_path(path),
            "updated_at": path.stat().st_mtime,
            "rows": row_count,
            "ok_rows": ok_rows,
            "status_counts": dict(status_counts),
            "judge_configs": [
                {"config_id": config_id, "rows": count}
                for config_id, count in config_counts.most_common()
            ],
        }

    def iter_judge_score_rows(self, path: Path):
        source_paths = []
        judge_root = path / "by_judge"
        if judge_root.is_dir():
            for judge_dir in sorted(item for item in judge_root.iterdir() if item.is_dir()):
                jsonl_path = judge_dir / "judge_scores.jsonl"
                csv_path = judge_dir / "judge_scores.csv"
                if jsonl_path.exists():
                    source_paths.append(jsonl_path)
                elif csv_path.exists():
                    source_paths.append(csv_path)
        if not source_paths:
            fallback_jsonl = path / "judge_scores.jsonl"
            fallback_csv = path / "judge_scores.csv"
            if fallback_jsonl.exists():
                source_paths.append(fallback_jsonl)
            elif fallback_csv.exists():
                source_paths.append(fallback_csv)
        for source_path in source_paths:
            if source_path.suffix.lower() == ".csv":
                yield from self.read_csv_rows(source_path)
                continue
            try:
                with source_path.open("r", encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            continue
            except OSError:
                continue

    def judge_score_row_has_usable_score(self, row: dict) -> bool:
        score = row.get("llm_judge_overall_score", row.get("overall_score"))
        if score not in (None, ""):
            try:
                float(score)
                return True
            except (TypeError, ValueError):
                pass
        for key in SCORE_METRIC_KEYS:
            if row.get(key) not in (None, ""):
                return True
        return False

    def resolve_judge_comparison_baseline(self, source_id: str):
        if is_current_ui_data_run_id(source_id):
            return ROOT / "data" / "question_cases.csv", "현재 UI 데이터"
        run_dir = self.run_dir_by_id(source_id)
        if run_dir:
            if self.has_partitioned_run_source(run_dir) and not self.projected_file_is_current(run_dir, "question_cases.csv"):
                self.write_projected_run_files(run_dir)
            return run_dir / "question_cases.csv", run_dir.name
        return None, ""

    def resolve_judge_score_run_dir(self, run_id: str):
        safe = self.safe_run_id(run_id)
        if not safe:
            return None
        candidate = EVAL_RUNS_ROOT / safe
        if candidate.is_dir() and (
            (candidate / "judge_scores.jsonl").exists()
            or (candidate / "judge_scores.csv").exists()
            or (candidate / "by_judge").is_dir()
        ):
            return candidate
        return None

    def question_cases_judge_counts(self, path: Path):
        counts = Counter()
        rows = 0
        if not path.exists():
            return counts, rows
        cache_key = (str(path.resolve(strict=False)), self.file_signature(path))
        with QUESTION_CASES_JUDGE_COUNTS_CACHE_LOCK:
            cached = QUESTION_CASES_JUDGE_COUNTS_CACHE.get(cache_key)
        if cached is not None:
            cached_counts, cached_rows = cached
            return Counter(cached_counts), cached_rows
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    rows += 1
                    for score in self.parse_json_array_field(row.get("llm_judge_individual_scores")):
                        config_id = str(score.get("config_id") or "").strip()
                        if config_id:
                            counts[config_id] += 1
        except (OSError, csv.Error):
            return Counter(), 0
        with QUESTION_CASES_JUDGE_COUNTS_CACHE_LOCK:
            QUESTION_CASES_JUDGE_COUNTS_CACHE[cache_key] = (Counter(counts), rows)
            while len(QUESTION_CASES_JUDGE_COUNTS_CACHE) > QUESTION_CASES_JUDGE_COUNTS_CACHE_MAX:
                QUESTION_CASES_JUDGE_COUNTS_CACHE.pop(next(iter(QUESTION_CASES_JUDGE_COUNTS_CACHE)))
        return counts, rows

    def load_baseline_judge_scores(self, path: Path, judge_config_id: str):
        scores = {}
        metadata = {}
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                config_id = str(row.get("version") or row.get("config_id") or "").strip()
                case_id = str(row.get("question_id") or row.get("case_id") or "").strip()
                if not config_id or not case_id:
                    continue
                key = (config_id, case_id)
                metadata.setdefault(
                    key,
                    {
                        "qa_category": row.get("qa_category") or row.get("source_type") or "",
                        "question_type": row.get("question_type") or "",
                        "qa_topic": row.get("qa_topic") or row.get("qa_matrix_topic") or "",
                        "instruction": row.get("instruction") or "",
                        "expected_output": row.get("output") or "",
                        "model_answer": row.get("model_answer") or row.get("answer_excerpt") or "",
                    },
                )
                for item in self.parse_json_array_field(row.get("llm_judge_individual_scores")):
                    if str(item.get("config_id") or "").strip() == judge_config_id:
                        scores[key] = self.normalized_judge_score(item, source="baseline")
                        break
        return scores, metadata

    def load_candidate_judge_scores(self, run_dir: Path, judge_config_id: str = ""):
        scores = {}
        rows = self.load_partitioned_judge_rows(run_dir)
        if not rows and (run_dir / "judge_scores.jsonl").exists():
            rows = eval_read_jsonl(run_dir / "judge_scores.jsonl")
        if not rows and (run_dir / "judge_scores.csv").exists():
            rows = self.read_csv_rows(run_dir / "judge_scores.csv")
        for row in rows:
            row_judge_id = str(row.get("llm_judge_config_id") or row.get("judge_config_id") or "").strip()
            if judge_config_id and row_judge_id != judge_config_id:
                continue
            status = str(row.get("source_llm_judge_status") or row.get("llm_judge_status") or "ok").strip().lower()
            if status != "ok" and not self.judge_score_row_has_usable_score(row):
                continue
            config_id = str(row.get("target_config_id") or row.get("config_id") or "").strip()
            case_id = str(row.get("case_id") or row.get("question_id") or "").strip()
            if config_id and case_id:
                scores[(config_id, case_id)] = self.normalized_judge_score(row, source="candidate")
        return scores

    def build_judge_comparison_report(
        self,
        *,
        baseline_path: Path,
        baseline_label: str,
        baseline_judge_config_id: str,
        candidate_dir: Path,
        candidate_judge_config_id: str,
        out_dir: Path,
        score_gap_threshold: float,
        score_gap_mode: str,
        include_error_type_mismatch: bool,
        normalize_error_type: bool,
        arbiter_judge_config_id: str,
    ):
        baseline_scores, case_meta = self.load_baseline_judge_scores(baseline_path, baseline_judge_config_id)
        arbiter_requested = bool(arbiter_judge_config_id)
        arbiter_scores = {}
        if arbiter_requested:
            arbiter_scores, _ = self.load_baseline_judge_scores(baseline_path, arbiter_judge_config_id)
        candidate_scores = self.load_candidate_judge_scores(candidate_dir, candidate_judge_config_id)
        if not baseline_scores:
            raise RuntimeError(f"No baseline rows found for judge config: {baseline_judge_config_id}")
        if not candidate_scores:
            raise RuntimeError(f"No ok candidate judge rows found: {candidate_dir.name}")

        matched_keys = sorted(set(baseline_scores) & set(candidate_scores))
        rows = []
        arbiter_keys = []
        for config_id, case_id in matched_keys:
            base = baseline_scores[(config_id, case_id)]
            cand = candidate_scores[(config_id, case_id)]
            base_score = self.safe_score(base.get("overall_score"))
            cand_score = self.safe_score(cand.get("overall_score"))
            delta = round(cand_score - base_score, 4)
            gap = round(abs(delta), 4)
            relative_gap = round(gap / max(abs(base_score), 1.0) * 100.0, 2)
            selected_gap = relative_gap if score_gap_mode == "relative_percent" else gap
            score_gap_threshold_met = bool(selected_gap >= score_gap_threshold)
            base_error = str(base.get("error_type") or "")
            cand_error = str(cand.get("error_type") or "")
            compare_base_error = eval_canonical_error_type(base_error) if normalize_error_type else base_error
            compare_cand_error = eval_canonical_error_type(cand_error) if normalize_error_type else cand_error
            base_pass = self.judge_bool_value(base.get("pass")) if base.get("pass") not in {"", None} else base_score >= 0.6
            cand_pass = self.judge_bool_value(cand.get("pass")) if cand.get("pass") not in {"", None} else cand_score >= 0.6
            pass_mismatch = base_pass != cand_pass
            error_mismatch = bool(include_error_type_mismatch and compare_base_error != compare_cand_error)
            reasons = []
            if pass_mismatch:
                reasons.append("judge pass decision disagreement")
            if score_gap_threshold_met:
                if score_gap_mode == "relative_percent":
                    reasons.append(f"judge relative score gap {relative_gap:.2f}%")
                else:
                    reasons.append(f"judge score gap {gap:.2f}")
            if error_mismatch:
                reasons.append(f"judge error-type disagreement: {compare_base_error}, {compare_cand_error}")
            meta = case_meta.get((config_id, case_id), {})
            conflict_detected = bool(reasons)
            conflict_for_arbiter = conflict_detected
            arbiter = arbiter_scores.get((config_id, case_id), {}) if arbiter_scores else {}
            has_arbiter = bool(arbiter)
            arbiter_score = self.safe_score(arbiter.get("overall_score")) if has_arbiter else ""
            arbiter_pass = (
                self.judge_bool_value(arbiter.get("pass"))
                if has_arbiter and arbiter.get("pass") not in {"", None}
                else (arbiter_score >= 0.6)
                if has_arbiter
                else ""
            )
            arbiter_error = str(arbiter.get("error_type") or "") if has_arbiter else ""
            if not conflict_detected:
                arbiter_status = "not_required"
                final_status = "not_required"
            elif not arbiter_requested:
                arbiter_status = "not_configured"
                final_status = "comparison_only"
            elif has_arbiter:
                arbiter_status = "existing_arbiter_applied"
                final_status = "complete"
            else:
                arbiter_status = "missing_arbiter"
                final_status = "missing_arbiter"
            row = {
                "config_id": config_id,
                "case_id": case_id,
                "qa_category": meta.get("qa_category", ""),
                "question_type": meta.get("question_type", ""),
                "qa_topic": meta.get("qa_topic", ""),
                "baseline_judge": baseline_judge_config_id,
                "candidate_judge": cand.get("config_id", ""),
                "baseline_score": base_score,
                "candidate_score": cand_score,
                "delta_candidate_minus_baseline": delta,
                "abs_score_gap": gap,
                "relative_score_gap_percent": relative_gap,
                "score_gap_mode": score_gap_mode,
                "selected_score_gap_value": selected_gap,
                "score_gap_threshold_met": score_gap_threshold_met,
                "baseline_pass": base_pass,
                "candidate_pass": cand_pass,
                "pass_mismatch": pass_mismatch,
                "baseline_error_type": base_error,
                "candidate_error_type": cand_error,
                "baseline_canonical_error_type": compare_base_error,
                "candidate_canonical_error_type": compare_cand_error,
                "error_type_mismatch": error_mismatch,
                "conflict_detected": conflict_detected,
                "conflict_for_arbiter": conflict_for_arbiter,
                "conflict_reason": "; ".join(reasons),
                "existing_arbiter_available": has_arbiter,
                "existing_arbiter_judge": arbiter_judge_config_id if has_arbiter else "",
                "existing_arbiter_score": arbiter_score,
                "existing_arbiter_pass": arbiter_pass,
                "existing_arbiter_error_type": arbiter_error,
                "existing_arbiter_reason": arbiter.get("reason", "") if has_arbiter else "",
                "arbiter_status": arbiter_status,
                "resolved_judge": arbiter_judge_config_id if conflict_for_arbiter and has_arbiter else "",
                "resolved_score": arbiter_score if conflict_for_arbiter and has_arbiter else "",
                "resolved_pass": arbiter_pass if conflict_for_arbiter and has_arbiter else "",
                "resolved_error_type": arbiter_error if conflict_for_arbiter and has_arbiter else "",
                "resolved_reason": arbiter.get("reason", "") if conflict_for_arbiter and has_arbiter else "",
                "final_status": final_status,
                "final_judge": arbiter_judge_config_id if conflict_for_arbiter and has_arbiter else "",
                "final_score": arbiter_score if conflict_for_arbiter and has_arbiter else "",
                "final_pass": arbiter_pass if conflict_for_arbiter and has_arbiter else "",
                "final_error_type": arbiter_error if conflict_for_arbiter and has_arbiter else "",
                "final_reason": arbiter.get("reason", "") if conflict_for_arbiter and has_arbiter else "",
                "topic_key": " / ".join(
                    item
                    for item in [
                        meta.get("qa_category", ""),
                        meta.get("question_type", ""),
                        meta.get("qa_topic", ""),
                    ]
                    if item
                ),
                "instruction": meta.get("instruction", ""),
                "expected_output": meta.get("expected_output", ""),
                "model_answer": meta.get("model_answer", ""),
                "baseline_reason": base.get("reason", ""),
                "candidate_reason": cand.get("reason", ""),
            }
            rows.append(row)
            if conflict_for_arbiter and not has_arbiter:
                arbiter_keys.append(
                    {
                        "config_id": config_id,
                        "case_id": case_id,
                        "reason": row["conflict_reason"],
                        "arbiter_context": {
                            "comparison_target": f"{baseline_judge_config_id}_vs_{cand.get('config_id', '')}",
                            "score_gap": gap,
                            "relative_score_gap_percent": relative_gap,
                            "score_gap_mode": score_gap_mode,
                            "selected_score_gap_value": selected_gap,
                            "score_min": min(base_score, cand_score),
                            "score_max": max(base_score, cand_score),
                            "pass_mismatch": pass_mismatch,
                            "base_judges": [
                                {**base, "label": baseline_judge_config_id},
                                {**cand, "label": cand.get("config_id", "")},
                            ],
                        },
                    }
                )

        summary = self.judge_comparison_summary(
            rows=rows,
            baseline_scores=baseline_scores,
            candidate_scores=candidate_scores,
            baseline_label=baseline_label,
            baseline_judge_config_id=baseline_judge_config_id,
            candidate_judge_config_id=candidate_judge_config_id,
            candidate_run_id=candidate_dir.name,
            score_gap_threshold=score_gap_threshold,
            score_gap_mode=score_gap_mode,
            include_error_type_mismatch=include_error_type_mismatch,
            normalize_error_type=normalize_error_type,
            arbiter_judge_config_id=arbiter_judge_config_id,
            arbiter_scores=arbiter_scores,
            arbiter_key_rows=len(arbiter_keys),
        )
        if not rows:
            raise RuntimeError("No matching config_id/case_id rows between the selected sources.")

        out_dir.mkdir(parents=True, exist_ok=True)
        files = {
            "comparison_jsonl": out_dir / "judge_comparison.jsonl",
            "comparison_csv": out_dir / "judge_comparison.csv",
            "arbiter_keys_jsonl": out_dir / "judge_comparison_arbiter_keys.jsonl",
            "summary_json": out_dir / "judge_comparison_summary.json",
            "report_md": out_dir / "judge_score_diff_report.md",
            "top_cases_csv": out_dir / "judge_score_diff_top_cases.csv",
            "by_model_csv": out_dir / "judge_score_diff_by_model.csv",
            "by_category_csv": out_dir / "judge_score_diff_by_category.csv",
            "by_topic_csv": out_dir / "judge_score_diff_by_topic.csv",
        }
        eval_write_jsonl(files["comparison_jsonl"], rows)
        eval_write_csv(files["comparison_csv"], rows)
        eval_write_jsonl(files["arbiter_keys_jsonl"], arbiter_keys)
        files["summary_json"].write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        by_model = self.judge_group_rows(rows, "config_id")
        by_category = self.judge_group_rows(rows, "qa_category")
        by_topic = self.judge_group_rows(rows, "topic_key")
        eval_write_csv(files["by_model_csv"], by_model)
        eval_write_csv(files["by_category_csv"], by_category)
        eval_write_csv(files["by_topic_csv"], by_topic)
        top_rows = self.judge_top_diff_rows(rows)
        eval_write_csv(files["top_cases_csv"], top_rows)
        files["report_md"].write_text(
            self.judge_comparison_markdown(summary, by_model, by_category, by_topic, top_rows),
            encoding="utf-8",
        )
        return {
            "summary": summary,
            "artifacts": {
                key: {
                    "path": self.display_path(path),
                    "url": "/api/eval/judge-comparison/artifact?path=" + self.display_path(path).replace("\\", "/"),
                }
                for key, path in files.items()
            },
        }

    def parse_json_array_field(self, value):
        if not value:
            return []
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        try:
            parsed = json.loads(str(value))
        except (TypeError, json.JSONDecodeError):
            return []
        return [item for item in parsed if isinstance(item, dict)] if isinstance(parsed, list) else []

    def safe_score(self, value):
        return self.safe_float(value, default=0.0, minimum=0.0, maximum=1.0)

    def judge_overall_points(self, value, row: dict) -> float:
        return self.safe_score(value)

    def judge_metric_points(self, value, row: dict) -> float:
        return self.safe_float(value, default=0.0, minimum=0.0, maximum=1.0)

    def judge_bool_value(self, value):
        if isinstance(value, bool):
            return value
        return str(value or "").strip().lower() in {"1", "true", "yes", "y", "pass"}

    def normalized_judge_score(self, row: dict, *, source: str):
        if source == "candidate":
            score = row.get("llm_judge_overall_score", row.get("overall_score"))
            if score in (None, ""):
                score_row = {
                    key: self.judge_metric_points(row.get(f"llm_judge_{key}", row.get(key)), row)
                    for key in SCORE_METRIC_KEYS
                }
                score_row["applicable_metrics"] = row.get("llm_judge_applicable_metrics", row.get("applicable_metrics", ""))
                score_row["score_denominator"] = row.get("llm_judge_score_denominator", row.get("score_denominator", ""))
                score = eval_score_total_from_metrics(score_row)
            overall = self.judge_overall_points(score, row)
            critical_fail = self.judge_bool_value(row.get("llm_judge_critical_fail", row.get("critical_fail")))
            return {
                "config_id": row.get("llm_judge_config_id") or row.get("judge_config_id") or row.get("config_id", ""),
                "provider": row.get("llm_judge_provider") or row.get("judge_provider") or row.get("provider", ""),
                "model": row.get("llm_judge_model") or row.get("judge_model") or row.get("model", ""),
                "overall_score": overall,
                "pass": overall >= 0.6 and not critical_fail,
                "critical_fail": critical_fail,
                "error_type": row.get("llm_judge_error_type", row.get("error_type", "")),
                "reason": row.get("llm_judge_reason", row.get("judge_reason", "")),
            }
        score = row.get("overall_score")
        if score in (None, ""):
            score_row = {
                key: self.judge_metric_points(row.get(key), row)
                for key in SCORE_METRIC_KEYS
            }
            score_row["applicable_metrics"] = row.get("applicable_metrics", "")
            score_row["score_denominator"] = row.get("score_denominator", "")
            score = eval_score_total_from_metrics(score_row)
        overall = self.judge_overall_points(score, row)
        critical_fail = self.judge_bool_value(row.get("critical_fail"))
        return {
            "config_id": row.get("config_id", ""),
            "provider": row.get("provider", ""),
            "model": row.get("model", ""),
            "overall_score": overall,
            "pass": overall >= 0.6 and not critical_fail,
            "critical_fail": critical_fail,
            "error_type": row.get("error_type", ""),
            "reason": row.get("reason", ""),
        }

    def judge_comparison_summary(
        self,
        *,
        rows: list[dict],
        baseline_scores: dict,
        candidate_scores: dict,
        baseline_label: str,
        baseline_judge_config_id: str,
        candidate_judge_config_id: str,
        candidate_run_id: str,
        score_gap_threshold: float,
        score_gap_mode: str,
        include_error_type_mismatch: bool,
        normalize_error_type: bool,
        arbiter_judge_config_id: str,
        arbiter_scores: dict,
        arbiter_key_rows: int,
    ):
        deltas = [self.safe_float(row.get("delta_candidate_minus_baseline"), default=0.0, minimum=-100.0, maximum=100.0) for row in rows]
        gaps = [abs(delta) for delta in deltas]
        selected_gaps = [
            self.safe_float(row.get("selected_score_gap_value"), default=0.0, minimum=0.0, maximum=1000000.0)
            for row in rows
        ]
        baseline_values = [self.safe_score(row.get("baseline_score")) for row in rows]
        candidate_values = [self.safe_score(row.get("candidate_score")) for row in rows]
        conflict_rows = sum(1 for row in rows if row.get("conflict_detected", row.get("conflict_for_arbiter")))
        arbiter_candidate_rows = sum(1 for row in rows if row.get("conflict_for_arbiter"))
        arbiter_existing_rows = sum(1 for row in rows if row.get("existing_arbiter_available"))
        arbiter_existing_candidate_rows = sum(
            1 for row in rows if row.get("conflict_for_arbiter") and row.get("existing_arbiter_available")
        )
        final_rows = [row for row in rows if row.get("final_status") == "complete"]
        final_candidate_rows = [row for row in final_rows if row.get("conflict_for_arbiter")]
        error_type_total_mismatch_rows = sum(
            1
            for row in rows
            if row.get("baseline_canonical_error_type") != row.get("candidate_canonical_error_type")
        )
        return {
            "baseline_label": baseline_label,
            "baseline_judge_config_id": baseline_judge_config_id,
            "candidate_judge_config_id": candidate_judge_config_id,
            "candidate_run_id": candidate_run_id,
            "score_gap_threshold": score_gap_threshold,
            "score_gap_mode": score_gap_mode,
            "score_gap_mode_label": "relative_percent" if score_gap_mode == "relative_percent" else "points",
            "relative_gap_denominator": "baseline_score_min_1",
            "include_error_type_mismatch": include_error_type_mismatch,
            "normalize_error_type": normalize_error_type,
            "arbiter_judge_config_id": arbiter_judge_config_id,
            "arbiter_configured": bool(arbiter_judge_config_id),
            "arbiter_source_rows": len(arbiter_scores),
            "baseline_source_rows": len(baseline_scores),
            "candidate_source_rows": len(candidate_scores),
            "matched_rows": len(rows),
            "missing_baseline_rows": len(set(candidate_scores) - set(baseline_scores)),
            "missing_candidate_rows": len(set(baseline_scores) - set(candidate_scores)),
            "baseline_avg": self.round_mean(baseline_values),
            "candidate_avg": self.round_mean(candidate_values),
            "avg_delta_candidate_minus_baseline": self.round_mean(deltas),
            "avg_abs_gap": self.round_mean(gaps),
            "median_abs_gap": self.round_quantile(gaps, 0.5),
            "p90_abs_gap": self.round_quantile(gaps, 0.9),
            "p95_abs_gap": self.round_quantile(gaps, 0.95),
            "avg_selected_gap": self.round_mean(selected_gaps),
            "p90_selected_gap": self.round_quantile(selected_gaps, 0.9),
            "candidate_higher_rows": sum(1 for delta in deltas if delta > 0),
            "baseline_higher_rows": sum(1 for delta in deltas if delta < 0),
            "same_score_rows": sum(1 for delta in deltas if delta == 0),
            "gap_threshold_rows": sum(1 for row in rows if row.get("score_gap_threshold_met")),
            "pass_mismatch_rows": sum(1 for row in rows if row.get("pass_mismatch")),
            "error_type_total_mismatch_rows": error_type_total_mismatch_rows,
            "error_type_mismatch_rows": sum(1 for row in rows if row.get("error_type_mismatch")),
            "conflict_rows": conflict_rows,
            "comparison_only_conflict_rows": conflict_rows - arbiter_candidate_rows,
            "arbiter_candidate_rows": arbiter_candidate_rows,
            "arbiter_existing_rows": arbiter_existing_rows,
            "arbiter_existing_candidate_rows": arbiter_existing_candidate_rows,
            "arbiter_missing_rows": arbiter_candidate_rows - arbiter_existing_candidate_rows,
            "arbiter_not_required_rows": sum(
                1 for row in rows if not row.get("conflict_detected", row.get("conflict_for_arbiter"))
            ),
            "arbiter_key_rows": arbiter_key_rows,
            "final_complete_rows": len(final_rows),
            "final_complete_candidate_rows": len(final_candidate_rows),
            "final_missing_candidate_rows": arbiter_candidate_rows - len(final_candidate_rows),
            "final_avg": self.round_mean([row.get("final_score") for row in final_rows]),
            "final_pass_rows": sum(1 for row in final_rows if row.get("final_pass")),
            "baseline_pass_rows": sum(1 for row in rows if row.get("baseline_pass")),
            "candidate_pass_rows": sum(1 for row in rows if row.get("candidate_pass")),
            "gap_bands": self.judge_gap_bands(gaps),
        }

    def round_mean(self, values):
        clean = [float(value) for value in values if value is not None]
        return round(sum(clean) / len(clean), 2) if clean else 0.0

    def round_quantile(self, values, quantile: float):
        clean = sorted(float(value) for value in values if value is not None)
        if not clean:
            return 0.0
        if len(clean) == 1:
            return round(clean[0], 2)
        position = (len(clean) - 1) * quantile
        lower = int(position)
        upper = min(lower + 1, len(clean) - 1)
        fraction = position - lower
        return round(clean[lower] * (1 - fraction) + clean[upper] * fraction, 2)

    def judge_gap_bands(self, gaps):
        bands = [
            ("0", lambda gap: gap == 0),
            ("0 초과~5 미만", lambda gap: 0 < gap < 5),
            ("5~10 미만", lambda gap: 5 <= gap < 10),
            ("10~20 미만", lambda gap: 10 <= gap < 20),
            ("20~30 미만", lambda gap: 20 <= gap < 30),
            ("30 이상", lambda gap: gap >= 30),
        ]
        total = len(gaps)
        return [
            {"band": label, "rows": count, "rate": round(count / total * 100, 1) if total else 0.0}
            for label, predicate in bands
            for count in [sum(1 for gap in gaps if predicate(gap))]
        ]

    def judge_group_rows(self, rows: list[dict], field: str):
        groups: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            key = str(row.get(field) or "미분류")
            groups[key].append(row)
        output = []
        for key, group in sorted(groups.items()):
            deltas = [self.safe_float(row.get("delta_candidate_minus_baseline"), default=0.0, minimum=-100.0, maximum=100.0) for row in group]
            gaps = [abs(delta) for delta in deltas]
            output.append(
                {
                    field: key,
                    "rows": len(group),
                    "baseline_avg": self.round_mean([row.get("baseline_score") for row in group]),
                    "candidate_avg": self.round_mean([row.get("candidate_score") for row in group]),
                    "avg_delta": self.round_mean(deltas),
                    "avg_abs_gap": self.round_mean(gaps),
                    "p90_abs_gap": self.round_quantile(gaps, 0.9),
                    "gap_threshold_rows": sum(1 for row in group if row.get("score_gap_threshold_met")),
                    "pass_mismatch_rows": sum(1 for row in group if row.get("pass_mismatch")),
                    "error_type_mismatch_rows": sum(1 for row in group if row.get("error_type_mismatch")),
                }
            )
        return sorted(output, key=lambda row: (-abs(float(row.get("avg_delta") or 0)), str(row.get(field) or "")))

    def judge_top_diff_rows(self, rows: list[dict]):
        output = []
        selected = [
            ("candidate_higher", sorted(rows, key=lambda row: self.safe_float(row.get("delta_candidate_minus_baseline"), default=0.0, minimum=-100.0, maximum=100.0), reverse=True)[:30]),
            ("baseline_higher", sorted(rows, key=lambda row: self.safe_float(row.get("delta_candidate_minus_baseline"), default=0.0, minimum=-100.0, maximum=100.0))[:30]),
            ("largest_abs_gap", sorted(rows, key=lambda row: self.safe_score(row.get("abs_score_gap")), reverse=True)[:100]),
        ]
        for direction, group in selected:
            for rank, row in enumerate(group, 1):
                output.append(
                    {
                        "rank": rank,
                        "direction": direction,
                        **{
                            key: row.get(key, "")
                            for key in (
                                "config_id",
                                "case_id",
                                "qa_category",
                                "question_type",
                                "qa_topic",
                                "baseline_score",
                                "candidate_score",
                                "delta_candidate_minus_baseline",
                                "abs_score_gap",
                                "baseline_pass",
                                "candidate_pass",
                                "baseline_error_type",
                                "candidate_error_type",
                                "relative_score_gap_percent",
                                "score_gap_mode",
                                "selected_score_gap_value",
                                "score_gap_threshold_met",
                                "final_status",
                                "final_judge",
                                "final_score",
                                "final_pass",
                                "final_error_type",
                                "instruction",
                                "expected_output",
                                "model_answer",
                                "baseline_reason",
                                "candidate_reason",
                            )
                        },
                    }
                )
        return output

    def judge_comparison_markdown(self, summary: dict, by_model: list[dict], by_category: list[dict], by_topic: list[dict], top_rows: list[dict]):
        def table(headers, rows):
            lines = [
                "| " + " | ".join(headers) + " |",
                "| " + " | ".join(["---"] + ["---:"] * (len(headers) - 1)) + " |",
            ]
            for row in rows:
                lines.append("| " + " | ".join(str(item).replace("|", "/") for item in row) + " |")
            return "\n".join(lines)

        def trunc(value, limit=72):
            text = " ".join(str(value or "").split())
            return text if len(text) <= limit else text[: limit - 1] + "..."

        score_gap_mode = str(summary.get("score_gap_mode") or "points")
        threshold_default = 30.0 if score_gap_mode == "relative_percent" else 0.3
        threshold_max = 10000.0 if score_gap_mode == "relative_percent" else 1.0
        threshold = self.safe_float(summary.get("score_gap_threshold"), default=threshold_default, minimum=0.0, maximum=threshold_max)
        threshold_label = f"{threshold:g}% 상대차+" if score_gap_mode == "relative_percent" else f"{threshold:g} score gap+"
        arbiter_judge = str(summary.get("arbiter_judge_config_id") or "").strip()
        model_rows = [
            [
                row.get("config_id", ""),
                row.get("rows", 0),
                row.get("baseline_avg", 0),
                row.get("candidate_avg", 0),
                f"{float(row.get('avg_delta') or 0):+.2f}",
                row.get("avg_abs_gap", 0),
                row.get("p90_abs_gap", 0),
                row.get("gap_threshold_rows", 0),
                row.get("pass_mismatch_rows", 0),
            ]
            for row in by_model
        ]
        category_rows = [
            [
                row.get("qa_category", ""),
                row.get("rows", 0),
                row.get("baseline_avg", 0),
                row.get("candidate_avg", 0),
                f"{float(row.get('avg_delta') or 0):+.2f}",
                row.get("avg_abs_gap", 0),
                row.get("gap_threshold_rows", 0),
                row.get("pass_mismatch_rows", 0),
            ]
            for row in by_category
        ]
        topic_rows = [
            [
                row.get("topic_key", ""),
                row.get("rows", 0),
                f"{float(row.get('avg_delta') or 0):+.2f}",
                row.get("avg_abs_gap", 0),
                row.get("p90_abs_gap", 0),
                row.get("gap_threshold_rows", 0),
                row.get("pass_mismatch_rows", 0),
            ]
            for row in sorted(by_topic, key=lambda item: -float(item.get("avg_abs_gap") or 0))[:12]
        ]
        positive = [row for row in top_rows if row.get("direction") == "candidate_higher"][:10]
        negative = [row for row in top_rows if row.get("direction") == "baseline_higher"][:10]
        top_headers_with_final = ["모델", "문항", "분류", "유형", "기준 점수", "비교 점수", "반영 점수", "차이", "질문"]
        positive_rows = [
            [
                row.get("config_id", ""),
                row.get("case_id", ""),
                row.get("qa_category", ""),
                row.get("question_type", ""),
                row.get("baseline_score", ""),
                row.get("candidate_score", ""),
                row.get("final_score", ""),
                f"{float(row.get('delta_candidate_minus_baseline') or 0):+.2f}",
                trunc(row.get("instruction")),
            ]
            for row in positive
        ]
        negative_rows = [
            [
                row.get("config_id", ""),
                row.get("case_id", ""),
                row.get("qa_category", ""),
                row.get("question_type", ""),
                row.get("baseline_score", ""),
                row.get("candidate_score", ""),
                row.get("final_score", ""),
                f"{float(row.get('delta_candidate_minus_baseline') or 0):+.2f}",
                trunc(row.get("instruction")),
            ]
            for row in negative
        ]
        if arbiter_judge:
            threshold_scope_label = "중재 Judge 후보 점수 차이 기준"
            arbiter_run_note = "- 새 중재 Judge는 실행하지 않았고, 기존 결과가 없는 후보 행만 후속 입력으로 산출했습니다."
            arbiter_summary_lines = [
                f"- 중재 Judge 대상 후보: {summary.get('arbiter_candidate_rows', 0):,}건",
                f"- 기존 중재 Judge 반영 가능 후보: {summary.get('arbiter_existing_candidate_rows', 0):,}건",
                f"- 기존 중재 Judge가 없는 후보: {summary.get('arbiter_missing_rows', 0):,}건",
                f"- 후속 중재 Judge 입력 JSONL 행: {summary.get('arbiter_key_rows', 0):,}건",
                f"- 부분 반영값 완료 행: {summary.get('final_complete_rows', 0):,}건",
                f"- 부분 반영값 평균: {summary.get('final_avg')}",
            ]
            arbiter_detail_lines = [
                "## 기존 중재 Judge 부분 반영",
                "",
                f"- 기존 중재 Judge 원본 행: {summary.get('arbiter_source_rows', 0):,}건",
                f"- 비교 전체 중 기존 중재 Judge 결과가 있는 행: {summary.get('arbiter_existing_rows', 0):,}건",
                f"- 중재 Judge 후보 중 반영값 완료 행: {summary.get('final_complete_candidate_rows', 0):,}건",
                f"- 중재 Judge 후보 중 반영값 미완료 행: {summary.get('final_missing_candidate_rows', 0):,}건",
                f"- 반영값 완료 행 중 통과: {summary.get('final_pass_rows', 0):,}건",
                f"- 후보가 아니어서 중재 Judge가 필요 없는 행: {summary.get('arbiter_not_required_rows', 0):,}건",
                f"- 기존 결과가 없는 후보는 새 호출 없이 `judge_comparison_arbiter_keys.jsonl`에만 남겼습니다.",
            ]
        else:
            threshold_scope_label = "충돌 후보 점수 차이 기준"
            arbiter_run_note = "- 중재 Judge를 선택하지 않아 기존 중재 Judge 조회와 후속 중재 Judge 입력 생성을 모두 건너뛰었습니다."
            arbiter_summary_lines = [
                f"- 충돌 행: {summary.get('conflict_rows', 0):,}건",
                f"- 중재 Judge 대상 후보: {summary.get('arbiter_candidate_rows', 0):,}건",
                f"- 후속 중재 Judge 입력 JSONL 행: {summary.get('arbiter_key_rows', 0):,}건",
                "- 부분 반영값: 중재 Judge를 선택하지 않은 비교 전용 리포트",
            ]
            arbiter_detail_lines = [
                "## 중재 Judge 미사용 비교",
                "",
                f"- 비교 전용 충돌 행: {summary.get('comparison_only_conflict_rows', 0):,}건",
                "- 중재 Judge를 선택하지 않아 기존 결과를 조회하지 않았고, 후속 중재 Judge 입력도 만들지 않았습니다.",
            ]
        lines = [
            "# Judge-vs-Judge 점수 차이 리포트",
            "",
            "## 범위",
            "",
            f"- 기준 Judge: {summary.get('baseline_judge_config_id')} ({summary.get('baseline_label')})",
            f"- 비교 Judge 실행: {summary.get('candidate_run_id')}",
            "- 기준 점수 차이: `비교 Judge 점수 - 기준 Judge 점수`",
            f"- {threshold_scope_label}: {threshold_label} ({'기준 Judge 대비 상대 차이' if score_gap_mode == 'relative_percent' else 'normalized score gap'})",
            f"- 기존 중재 Judge 결과: {arbiter_judge or '선택 안 함'}",
            arbiter_run_note,
            "",
            "## 핵심 요약",
            "",
            f"- 비교 가능 행: {summary.get('matched_rows', 0):,}건",
            f"- 기준 Judge 평균: {summary.get('baseline_avg')}",
            f"- 비교 Judge 평균: {summary.get('candidate_avg')}",
            f"- 평균 차이: {float(summary.get('avg_delta_candidate_minus_baseline') or 0):+.2f}",
            f"- 평균 절대 차이: {summary.get('avg_abs_gap')}",
            f"- P90 절대 차이: {summary.get('p90_abs_gap')}",
            f"- {threshold_label} 차이: {summary.get('gap_threshold_rows', 0):,}건",
            f"- 통과 판정 불일치: {summary.get('pass_mismatch_rows', 0):,}건",
            f"- 실패 유형 불일치 전체: {summary.get('error_type_total_mismatch_rows', 0):,}건",
            f"- 실패 유형 불일치 후보 포함: {'예' if summary.get('include_error_type_mismatch') else '아니오'}",
            *arbiter_summary_lines,
            "",
            *arbiter_detail_lines,
            "",
            "## 절대 점수 차이 구간",
            "",
            table(["절대 점수 차이", "건수", "비율"], [[row["band"], f"{row['rows']:,}", f"{row['rate']}%"] for row in summary.get("gap_bands", [])]),
            "",
            "## 모델별 차이",
            "",
            table(["모델", "행", "기준 평균", "비교 평균", "평균 차이", "평균 절대차", "P90 절대차", threshold_label, "통과 판정 불일치"], model_rows),
            "",
            "## 대분류별 차이",
            "",
            table(["대분류", "행", "기준 평균", "비교 평균", "평균 차이", "평균 절대차", threshold_label, "통과 판정 불일치"], category_rows),
            "",
            "## 세부 주제별 변동이 큰 영역",
            "",
            table(["분류 / 유형 / 토픽", "행", "평균 차이", "평균 절대차", "P90 절대차", threshold_label, "통과 판정 불일치"], topic_rows),
            "",
            "## 비교 Judge가 더 높게 준 대표 케이스",
            "",
            table(top_headers_with_final, positive_rows),
            "",
            "## 기준 Judge가 더 높게 준 대표 케이스",
            "",
            table(top_headers_with_final, negative_rows),
            "",
            "## 해석 메모",
            "",
            "- 평균 차이는 전반적인 채점 성향을, 평균 절대 차이는 행 단위 판단 흔들림을 보여줍니다.",
            "- 중재 Judge 후보는 통과 판정 불일치, 점수 차이 기준, 선택 시 실패 유형 불일치의 합집합입니다.",
            "- 실패 유형 불일치는 기본적으로 중재 Judge 후보에서 제외하고, 별도 선택 시에만 포함합니다.",
            "- 실패 유형 비교는 정규화된 error_type 기준으로 계산할 수 있습니다.",
            "",
        ]
        return "\n".join(lines)

    def latest_judge_summary(self, latest: Path, config: dict):
        matrix = config.get("matrix") if isinstance(config.get("matrix"), dict) else {}
        judge_settings = matrix.get("llm_judge") if isinstance(matrix.get("llm_judge"), dict) else {}
        judge_config_ids = []
        if isinstance(judge_settings.get("config_ids"), list):
            judge_config_ids = [str(item).strip() for item in judge_settings.get("config_ids", []) if str(item).strip()]
        elif judge_settings.get("config_id"):
            judge_config_ids = [str(judge_settings.get("config_id")).strip()]
        summary = {
            "scoring_mode": str(matrix.get("scoring_mode") or judge_settings.get("scoring_mode") or "").strip(),
            "judge_config_ids": judge_config_ids,
            "llm_judge_count": len(judge_config_ids),
            "llm_judge_provider": "",
            "llm_judge_model": "",
        }
        row = self.first_projected_question_row_if_current(latest)
        if row is None:
            projected = self.projected_run_tables(latest) if self.has_partitioned_run_source(latest) else None
            projected_rows = projected.get("question_rows", []) if projected else []
            row = projected_rows[0] if projected_rows else None
        if row:
            row_scoring_mode = str(row.get("scoring_mode") or "").strip()
            if row_scoring_mode:
                summary["scoring_mode"] = row_scoring_mode
            summary["llm_judge_provider"] = str(row.get("llm_judge_provider") or "").strip()
            summary["llm_judge_model"] = str(row.get("llm_judge_model") or "").strip()
            row_count = self.safe_int(row.get("llm_judge_count"), default=0, minimum=0, maximum=100)
            if row_count:
                summary["llm_judge_count"] = row_count
            if not summary["scoring_mode"]:
                summary["scoring_mode"] = "static"
            return summary
        question_cases_path = latest / "question_cases.csv"
        if not question_cases_path.exists():
            if not summary["scoring_mode"]:
                summary["scoring_mode"] = "static"
            return summary
        try:
            with question_cases_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    row_scoring_mode = str(row.get("scoring_mode") or "").strip()
                    if row_scoring_mode:
                        summary["scoring_mode"] = row_scoring_mode
                    summary["llm_judge_provider"] = str(row.get("llm_judge_provider") or "").strip()
                    summary["llm_judge_model"] = str(row.get("llm_judge_model") or "").strip()
                    row_count = self.safe_int(row.get("llm_judge_count"), default=0, minimum=0, maximum=100)
                    if row_count:
                        summary["llm_judge_count"] = row_count
                    break
        except (OSError, csv.Error):
            pass
        if not summary["scoring_mode"]:
            summary["scoring_mode"] = "static"
        return summary

    def merge_independent_judge_summary(self, latest: Path):
        summary_path = latest / "merge_independent_judges_summary.json"
        if not summary_path.exists():
            return {}
        try:
            summary = self.load_structured_file(summary_path)
        except (OSError, RuntimeError, json.JSONDecodeError):
            return {}
        return summary if isinstance(summary, dict) else {}

    def handle_latest_report(self, query: str = ""):
        requested_run_id = self.requested_run_id(query)
        if is_current_ui_data_run_id(requested_run_id) or (
            not requested_run_id and not self.explicit_run_id() and self.current_ui_data_run_summary(selected=False)
        ):
            self.send_text(self.ui_report_html(CURRENT_UI_DATA_RUN_ID), content_type="text/html; charset=utf-8")
            return
        latest = self.run_dir_by_id(requested_run_id) if requested_run_id else self.latest_run_dir()
        if requested_run_id and not latest:
            self.send_json({"error": "unknown eval run", "run_id": requested_run_id}, status=404)
            return
        if latest:
            self.send_text(self.ui_report_html(latest.name), content_type="text/html; charset=utf-8")
            return
        self.send_json({"error": "not found", "path": "regression_report.html"}, status=404)

    def handle_raw_report(self, query: str = ""):
        requested_run_id = self.requested_run_id(query)
        if is_current_ui_data_run_id(requested_run_id):
            requested_run_id = ""
        latest = self.run_dir_by_id(requested_run_id) if requested_run_id else self.latest_run_dir()
        if requested_run_id and not latest:
            self.send_json({"error": "unknown eval run", "run_id": requested_run_id}, status=404)
            return
        if latest and (latest / "regression_report.html").exists():
            self.serve_path(latest / "regression_report.html", content_type="text/html; charset=utf-8")
            return
        self.send_json({"error": "not found", "path": "regression_report.html"}, status=404)

    def ui_report_html(self, run_id: str):
        is_current = is_current_ui_data_run_id(run_id)
        target = "/#overview" if is_current else f"/?run_id={run_id}#overview"
        display = CURRENT_UI_DATA_LABEL if is_current else run_id
        return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="0; url={target}">
  <title>Eval UI Report · {display}</title>
  <script>window.location.replace({json.dumps(target)});</script>
</head>
<body>
  <p>Opening UI report for <a href="{target}">{display}</a>.</p>
</body>
</html>
"""

    def requested_run_id(self, query: str):
        return parse_qs(query or "").get("run_id", [""])[0].strip()

    def run_dir_by_id(self, run_id: str):
        run_id = str(run_id or "").strip()
        if not run_id or "/" in run_id or "\\" in run_id:
            return None
        candidate = EVAL_RUNS_ROOT / run_id
        if self.is_eval_run_dir(candidate):
            return candidate
        return None

    def eval_run_summaries(self):
        summaries = []
        selected_id = self.default_selected_run_id()
        exported = self.current_ui_data_run_summary(selected=is_current_ui_data_run_id(selected_id))
        if exported:
            summaries.append(exported)
        if not EVAL_RUNS_ROOT.exists():
            return summaries
        candidates = [
            path
            for path in EVAL_RUNS_ROOT.iterdir()
            if self.is_eval_run_dir(path)
        ]
        candidates.sort(key=self.run_sort_key, reverse=True)
        summaries.extend(
            self.eval_run_summary(path, selected=path.name == selected_id)
            for path in candidates
        )
        return summaries

    def current_ui_data_run_summary(self, selected: bool = False):
        eval_path = ROOT / "data" / "eval_runs.csv"
        case_path = ROOT / "data" / "question_cases.csv"
        if not eval_path.exists() or not case_path.exists():
            return None
        rows = []
        try:
            with eval_path.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
        except (OSError, csv.Error):
            rows = []
        models = [row.get("model") or row.get("version") or "" for row in rows if row.get("model") or row.get("version")]
        scores = [
            self.safe_float(row.get("overall_score"), default=0.0, minimum=0.0, maximum=1.0)
            for row in rows
        ]
        scored_scores = [
            self.safe_float(row.get("scored_average"), default=0.0, minimum=0.0, maximum=1.0)
            for row in rows
            if row.get("scored_average") not in {None, ""}
        ]
        pass_rates = [self.safe_float(row.get("pass_rate"), default=0.0, minimum=0.0, maximum=1.0) for row in rows]
        scored_pass_rates = [
            self.safe_float(row.get("scored_pass_rate"), default=0.0, minimum=0.0, maximum=1.0)
            for row in rows
            if row.get("scored_pass_rate") not in {None, ""}
        ]
        review_pending_counts = [
            self.safe_float(row.get("review_pending_count"), default=0.0, minimum=0.0, maximum=1000000.0)
            for row in rows
            if row.get("review_pending_count") not in {None, ""}
        ]
        total_questions = max(
            [
                self.safe_int(row.get("total_questions"), default=0, minimum=0, maximum=1000000)
                for row in rows
            ]
            or [0]
        )
        case_ids = set()
        case_count = 0
        if not total_questions:
            try:
                with case_path.open("r", encoding="utf-8-sig", newline="") as handle:
                    for row in csv.DictReader(handle):
                        case_count += 1
                        case_id = row.get("question_id") or row.get("case_id") or ""
                        if case_id:
                            case_ids.add(case_id)
            except (OSError, csv.Error):
                case_count = 0
        updated_at = max(eval_path.stat().st_mtime, case_path.stat().st_mtime)
        scoring_mode = next((row.get("scoring_mode") for row in rows if row.get("scoring_mode")), "static")
        return {
            "run_id": CURRENT_UI_DATA_RUN_ID,
            "label": CURRENT_UI_DATA_LABEL,
            "selected": selected,
            "updated_at": updated_at,
            "eval_started_at": datetime.fromtimestamp(updated_at).isoformat(timespec="seconds"),
            "run_type": "ui_runtime_export",
            "case_source": "ui_runtime_data",
            "case_source_status": "exported",
            "total_questions": total_questions or len(case_ids) or case_count,
            "model_count": len(rows),
            "models": models,
            "avg_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
            "avg_scored_score": round(sum(scored_scores) / len(scored_scores), 4) if scored_scores else 0.0,
            "avg_pass_rate": round(sum(pass_rates) / len(pass_rates), 4) if pass_rates else 0.0,
            "avg_scored_pass_rate": round(sum(scored_pass_rates) / len(scored_pass_rates), 4) if scored_pass_rates else 0.0,
            "review_pending_count": int(max(review_pending_counts)) if review_pending_counts else 0,
            "provider_refused_count": 0,
            "sanitized_eval_count": 0,
            "unresolved_conflict_count": 0,
            "scoring_mode": scoring_mode,
            "reblend_eligible": False,
            "llm_judge_provider": next((row.get("llm_judge_provider") for row in rows if row.get("llm_judge_provider")), ""),
            "llm_judge_model": next((row.get("llm_judge_model") for row in rows if row.get("llm_judge_model")), ""),
            "report_html": "/report/regression_report.html",
            "report_raw_html": "",
            "report_ui": "/#overview",
        }

    def eval_run_summary(self, path: Path, selected: bool = False):
        config = self.run_config(path)
        rows = self.projected_csv_rows_if_current(path, "eval_runs.csv")
        if rows is None:
            if self.has_partitioned_run_source(path):
                projected = self.projected_run_tables(path)
                rows = projected.get("summary", []) if projected else self.read_csv_rows(path / "eval_runs.csv")
            else:
                rows = self.read_csv_rows(path / "eval_runs.csv")
        models = [row.get("model") or row.get("version") or "" for row in rows if row.get("model") or row.get("version")]
        scores = [
            self.safe_float(row.get("overall_score"), default=0.0, minimum=0.0, maximum=1.0)
            for row in rows
        ]
        scored_scores = [
            self.safe_float(row.get("scored_average"), default=0.0, minimum=0.0, maximum=1.0)
            for row in rows
            if row.get("scored_average") not in {None, ""}
        ]
        pass_rates = [self.safe_float(row.get("pass_rate"), default=0.0, minimum=0.0, maximum=1.0) for row in rows]
        scored_pass_rates = [
            self.safe_float(row.get("scored_pass_rate"), default=0.0, minimum=0.0, maximum=1.0)
            for row in rows
            if row.get("scored_pass_rate") not in {None, ""}
        ]
        review_pending_counts = [
            self.safe_float(row.get("review_pending_count"), default=0.0, minimum=0.0, maximum=1000000.0)
            for row in rows
            if row.get("review_pending_count") not in {None, ""}
        ]
        judge_summary = self.latest_judge_summary(path, config)
        merge_summary = self.merge_independent_judge_summary(path)
        merged_review_pending = self.safe_int(
            merge_summary.get("manual_review_required_rows"),
            default=-1,
            minimum=-1,
            maximum=1000000,
        )
        review_pending_count = (
            merged_review_pending
            if merged_review_pending >= 0
            else int(max(review_pending_counts)) if review_pending_counts else 0
        )
        return {
            "run_id": path.name,
            "selected": selected,
            "updated_at": path.stat().st_mtime,
            "eval_started_at": config.get("eval_started_at", ""),
            "run_type": config.get("run_type", rows[0].get("run_type", "") if rows else ""),
            "case_source_status": "final" if self.run_uses_final_question_sets(path) else "previous",
            "total_questions": self.run_question_count(path),
            "model_count": len(rows),
            "models": models,
            "avg_score": round(sum(scores) / len(scores), 4) if scores else 0.0,
            "avg_scored_score": round(sum(scored_scores) / len(scored_scores), 4) if scored_scores else 0.0,
            "avg_pass_rate": round(sum(pass_rates) / len(pass_rates), 4) if pass_rates else 0.0,
            "avg_scored_pass_rate": round(sum(scored_pass_rates) / len(scored_pass_rates), 4) if scored_pass_rates else 0.0,
            "review_pending_count": review_pending_count,
            "provider_refused_count": self.safe_int(
                merge_summary.get("provider_refused_rows"),
                default=0,
                minimum=0,
                maximum=1000000,
            ),
            "sanitized_eval_count": self.safe_int(
                merge_summary.get("sanitized_eval_rows"),
                default=0,
                minimum=0,
                maximum=1000000,
            ),
            "unresolved_conflict_count": self.safe_int(
                merge_summary.get("unresolved_conflict_rows"),
                default=0,
                minimum=0,
                maximum=1000000,
            ),
            "scoring_mode": judge_summary.get("scoring_mode", ""),
            "reblend_eligible": self.is_reblend_source_dir(path),
            "llm_judge_provider": judge_summary.get("llm_judge_provider", ""),
            "llm_judge_model": judge_summary.get("llm_judge_model", ""),
            "report_html": f"/report/regression_report.html?run_id={path.name}",
            "report_raw_html": f"/report/raw_regression_report.html?run_id={path.name}",
            "report_ui": f"/?run_id={path.name}#overview",
        }

    def latest_run_dir(self):
        explicit = self.explicit_run_dir()
        if explicit:
            return explicit
        if not EVAL_RUNS_ROOT.exists():
            return None
        candidates = sorted(
            [
                path
                for path in EVAL_RUNS_ROOT.iterdir()
                if self.is_eval_run_dir(path)
            ],
            key=self.run_sort_key,
            reverse=True,
        )
        if not candidates:
            return None
        final_candidates = [path for path in candidates if self.run_uses_final_question_sets(path)]
        preferred_candidates = final_candidates or candidates
        non_smoke_candidates = [path for path in preferred_candidates if not self.is_smoke_run(path)]
        display_candidates = [
            path
            for path in non_smoke_candidates
            if self.run_question_count(path) >= MIN_DISPLAY_QUESTIONS
        ]
        if display_candidates:
            return display_candidates[0]
        if non_smoke_candidates:
            return non_smoke_candidates[0]
        return preferred_candidates[0]

    def default_selected_run_id(self) -> str:
        explicit_id = self.explicit_run_id()
        if explicit_id:
            return explicit_id
        if self.current_ui_data_run_summary(selected=False):
            return CURRENT_UI_DATA_RUN_ID
        latest = self.latest_run_dir()
        return latest.name if latest else ""

    def explicit_run_id(self) -> str:
        run_id = os.environ.get("FINAL_UI_RUN_ID")
        for path in ACTIVE_RUN_PATHS:
            if run_id:
                break
            if not path.exists():
                continue
            try:
                raw = path.read_text(encoding="utf-8").strip()
                payload = json.loads(raw)
                run_id = payload.get("run_id") if isinstance(payload, dict) else str(payload)
            except json.JSONDecodeError:
                run_id = raw
        return str(run_id or "").strip()

    def explicit_run_dir(self):
        run_id = self.explicit_run_id()
        if not run_id:
            return None
        candidate = EVAL_RUNS_ROOT / run_id
        if self.is_eval_run_dir(candidate):
            return candidate
        return None

    def is_reserved_eval_run_name(self, name: str) -> bool:
        return name in RESERVED_EVAL_RUN_NAMES or name.startswith("_") or "__pre_" in name.lower()

    def is_eval_run_dir(self, path: Path) -> bool:
        return (
            path.is_dir()
            and not self.is_reserved_eval_run_name(path.name)
            and (
                ((path / "eval_runs.csv").exists() and (path / "question_cases.csv").exists())
                or self.has_partitioned_run_source(path)
            )
        )

    def is_reblend_source_dir(self, path: Path) -> bool:
        if not self.is_eval_run_dir(path):
            return False
        has_outputs = (path / "model_outputs.jsonl").exists() or self.partitioned_output_row_count(path) > 0
        has_scores = (path / "judge_scores.jsonl").exists() or (path / "judge_scores.csv").exists() or (path / "by_judge").is_dir()
        return bool(has_outputs and has_scores)

    def latest_reblend_run_dir(self):
        explicit = self.explicit_run_dir()
        if explicit and self.is_reblend_source_dir(explicit):
            return explicit
        if not EVAL_RUNS_ROOT.exists():
            return None
        candidates = sorted(
            [
                path
                for path in EVAL_RUNS_ROOT.iterdir()
                if self.is_reblend_source_dir(path)
            ],
            key=self.run_sort_key,
            reverse=True,
        )
        if not candidates:
            return None
        non_smoke_candidates = [path for path in candidates if not self.is_smoke_run(path)]
        return (non_smoke_candidates or candidates)[0]

    def is_smoke_run(self, path: Path) -> bool:
        upper_name = path.name.upper()
        if any(marker in upper_name for marker in RUN_EXCLUDE_MARKERS):
            return True
        config = self.run_config(path)
        return any(marker in str(config.get("run_id", "")).upper() for marker in RUN_EXCLUDE_MARKERS)

    def run_uses_final_question_sets(self, path: Path) -> bool:
        config = self.run_config(path)
        case_source = config.get("case_source", "")
        if self.case_source_uses_final_sets(case_source):
            return True
        summary_path = self.composed_summary_path_for_case_source(case_source)
        if not summary_path or not summary_path.exists():
            return False
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        pools = summary.get("pools") if isinstance(summary, dict) else None
        if not isinstance(pools, list):
            return False
        return any(
            self.case_source_uses_final_sets(pool.get("path", ""))
            or str(pool.get("pool_id", "")).startswith(("benchmark_final", "regression_"))
            for pool in pools
            if isinstance(pool, dict)
        )

    def case_source_uses_final_sets(self, source: str) -> bool:
        normalized = str(source or "").replace("\\", "/")
        return any(
            marker in normalized
            for marker in (
                "questionlist/final_sets/",
                "questionlist/benchmark/",
                "questionlist/regression/",
                "benchmark_final_full",
                "regression_golden_full",
            )
        )

    def composed_summary_path_for_case_source(self, source: str):
        if not source:
            return None
        path = Path(str(source))
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        name = path.name
        if name.endswith("_cases.jsonl"):
            return path.with_name(name[: -len("_cases.jsonl")] + "_cases.summary.json")
        if path.suffix == ".jsonl":
            return path.with_suffix(".summary.json")
        return None

    def run_question_count(self, path: Path) -> int:
        if self.has_partitioned_run_source(path):
            cases = self.projected_run_cases(self.run_config(path))
            if cases:
                return len(cases)
            first_outputs = next(iter(sorted((path / "by_target_model").glob("*/model_outputs.jsonl"))), None)
            if first_outputs and first_outputs.exists():
                return sum(1 for line in first_outputs.open(encoding="utf-8") if line.strip())
        csv_path = path / "eval_runs.csv"
        if not csv_path.exists():
            return 0
        with csv_path.open(encoding="utf-8-sig", newline="") as file:
            counts = []
            for row in csv.DictReader(file):
                try:
                    counts.append(int(float(row.get("total_questions") or 0)))
                except ValueError:
                    counts.append(0)
        return max(counts) if counts else 0

    def run_sort_key(self, path: Path):
        config = self.run_config(path)
        value = str(config.get("eval_started_at") or "")
        if value:
            try:
                return datetime.fromisoformat(value).timestamp()
            except ValueError:
                pass
        return path.stat().st_mtime

    def run_config(self, path: Path) -> dict:
        config_path = self.run_config_path(path)
        if not config_path.exists():
            return {}
        try:
            return self.load_structured_file(config_path)
        except Exception:
            return {}

    def run_config_path(self, path: Path) -> Path:
        for name in ("config.json", "config.yaml"):
            candidate = path / name
            if candidate.exists():
                return candidate
        return path / "config.json"

    def handle_questionlist_summary(self):
        primary_source = self.primary_question_source_dataset()
        source_path = primary_source["path"] if primary_source else QUESTIONLIST_SOURCE_PATH
        source_summary = (
            self.summarize_case_file(source_path, dataset_id=primary_source["id"], role=primary_source["role"])
            if primary_source
            else self.summarize_questionlist_source(QUESTIONLIST_SOURCE_PATH)
        )
        selected_summary = {}
        if QUESTIONLIST_SUMMARY_PATH.exists():
            try:
                selected_summary = json.loads(QUESTIONLIST_SUMMARY_PATH.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                selected_summary = {}
        self.send_json(
            {
                "status": "ok",
                "source": {
                    "path": str(source_path),
                    "source_format": primary_source["format"] if primary_source else "jsonl",
                    **source_summary,
                },
                "selected": selected_summary,
                "selected_cases_path": str(QUESTIONLIST_CASES_PATH),
            }
        )

    def handle_questionlist_cases(self, query: str):
        params = parse_qs(query)
        try:
            limit = max(1, min(int(params.get("limit", ["200"])[0]), 1000))
        except ValueError:
            limit = 200
        cases = []
        primary_source = self.primary_question_source_dataset()
        if primary_source:
            for row in self.iter_case_rows(primary_source["path"], dataset_id=primary_source["id"], role=primary_source["role"]):
                cases.append(self.normalize_dataset_case(row, primary_source["id"]))
                if len(cases) >= limit:
                    break
        elif QUESTIONLIST_CASES_PATH.exists():
            with QUESTIONLIST_CASES_PATH.open(encoding="utf-8") as file:
                for line in file:
                    if len(cases) >= limit:
                        break
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
                    evidence = row.get("gold_evidence") if isinstance(row.get("gold_evidence"), list) else []
                    first_evidence = next((item for item in evidence if isinstance(item, dict)), {})
                    qa_category = canonical_qa_category(
                        row.get("qa_category"),
                        metadata.get("qa_category"),
                        metadata.get("source_type"),
                        row.get("suite"),
                    )
                    question_type = canonical_question_type(
                        row.get("question_type"),
                        metadata.get("question_type"),
                    )
                    qa_topic = canonical_qa_topic(
                        qa_category,
                        row.get("qa_topic"),
                        metadata.get("qa_topic"),
                        metadata.get("qa_matrix_topic"),
                        row.get("intent"),
                        metadata.get("topic"),
                        row.get("suite"),
                    )
                    cases.append(
                        {
                            "case_id": row.get("case_id"),
                            "suite": row.get("suite"),
                            "severity": row.get("severity"),
                            "priority": row.get("priority"),
                            "question": row.get("question"),
                            "intent": row.get("intent"),
                            "task_type": row.get("task_type"),
                            "qa_category": qa_category,
                            "source_type": qa_category,
                            "question_type": question_type,
                            "qa_topic": qa_topic,
                            "qa_matrix_topic": qa_topic,
                            "expected_behavior": metadata.get("expected_behavior"),
                            "selection_mode": metadata.get("selection_mode"),
                            "source_title": metadata.get("source_title") or first_evidence.get("title"),
                            "source_url": metadata.get("source_url") or first_evidence.get("url"),
                            "ground_truth_doc": metadata.get("expected_source_doc_id") or first_evidence.get("source_id"),
                            "gold_excerpt": first_evidence.get("excerpt"),
                        }
                    )
        self.send_json({"status": "ok", "count": len(cases), "cases": cases})

    def questionlist_datasets_payload(self):
        datasets = []
        seen_dataset_ids = set()
        catalog = self.load_eval_dataset_catalog()
        pools = catalog.get("pools") if isinstance(catalog.get("pools"), dict) else {}
        defaults = self.question_dataset_defaults(pools)
        catalog_paths = set()
        for pool in pools.values():
            if not isinstance(pool, dict) or not pool.get("path"):
                continue
            try:
                path = self.resolve_project_path(str(pool.get("path") or ""))
            except ValueError:
                continue
            if self.catalog_dataset_visible(pool, path):
                catalog_paths.add(str(path.resolve()).lower())
        for dataset in self.discover_question_csv_datasets().values():
            path = dataset["path"]
            if str(path.resolve()).lower() in catalog_paths:
                continue
            role = dataset["role"]
            datasets.append(
                self.dataset_payload_with_default_flags(
                    {
                        "id": dataset["id"],
                        "name": dataset["name"],
                        "path": self.display_path(path),
                        "exists": path.exists(),
                        "role": role,
                        "default_quota": "",
                        "gate_eligible": role != "benchmark",
                        "dataset_version": dataset["version"],
                        "source_format": "csv",
                        "source_directory": dataset["directory"],
                        "auto_discovered": True,
                        "user_uploaded": bool(dataset.get("user_uploaded")),
                        **self.summarize_case_file(path, dataset_id=dataset["id"], role=role),
                    },
                    defaults,
                )
            )
            seen_dataset_ids.add(dataset["id"])
        for dataset_id, path in QUESTIONLIST_DATASET_FILES.items():
            datasets.append(
                self.dataset_payload_with_default_flags(
                    {
                        "id": dataset_id,
                        "name": path.name,
                        "path": self.display_path(path),
                        "exists": path.exists(),
                        **self.summarize_case_file(path),
                    },
                    defaults,
                )
            )
            seen_dataset_ids.add(dataset_id)
        for pool_id, pool in pools.items():
            if str(pool_id) in seen_dataset_ids:
                continue
            try:
                path = self.resolve_project_path(str(pool.get("path") or ""))
            except ValueError:
                continue
            if not self.catalog_dataset_visible(pool, path):
                continue
            role = str(pool.get("role") or "regression")
            datasets.append(
                self.dataset_payload_with_default_flags(
                    {
                        "id": str(pool_id),
                        "name": str(pool.get("label") or path.name),
                        "path": self.display_path(path),
                        "exists": path.exists(),
                        "role": role,
                        "default_quota": pool.get("default_quota", ""),
                        "gate_eligible": bool(pool.get("gate_eligible", role != "benchmark")),
                        "dataset_version": pool.get("dataset_version", ""),
                        "is_public": bool(pool.get("is_public", False)),
                        "catalog_pool": True,
                        "auto_discovered": bool(pool.get("auto_discovered", False)),
                        "user_uploaded": bool(pool.get("user_uploaded", False)),
                        "registered_all_eligible": bool(pool.get("registered_all_eligible", True)),
                        **self.summarize_case_file(
                            path,
                            filters=pool.get("filters"),
                            dataset_id=str(pool_id),
                            role=role,
                        ),
                    },
                    defaults,
                )
            )
            seen_dataset_ids.add(str(pool_id))
        return datasets

    def handle_questionlist_datasets(self):
        self.send_json(self.questionlist_datasets_response_payload())

    def questionlist_datasets_response_payload(self):
        catalog = self.load_eval_dataset_catalog()
        pools = catalog.get("pools") if isinstance(catalog.get("pools"), dict) else {}
        return {
            "status": "ok",
            "datasets": self.questionlist_datasets_payload(),
            "defaults": self.question_dataset_defaults(pools),
        }

    def dataset_payload_with_default_flags(self, dataset: dict, defaults: dict[str, str]):
        role = self.normalize_question_dataset_role(dataset.get("role"))
        dataset["role"] = role
        dataset["is_default_for_role"] = defaults.get(role) == str(dataset.get("id") or "")
        dataset["default_role"] = role if dataset["is_default_for_role"] else ""
        return dataset

    def handle_question_dataset_sample_csv_download(self):
        buffer = io.StringIO()
        fieldnames = [
            "id",
            "question",
            "ground_truth",
            "qa_category",
            "qa_topic",
            "question_type",
            "forbidden_claims",
        ]
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(
            [
                {
                    "id": "SAMPLE_001",
                    "question": "BC카드 결제일 변경 방법을 간단히 설명해줘",
                    "ground_truth": "마이BC 또는 고객센터 등 공식 채널에서 결제일 변경 가능 여부와 절차를 확인하도록 안내한다.",
                    "qa_category": "BC FAQ",
                    "qa_topic": "카드/결제",
                    "question_type": "단일추론",
                    "forbidden_claims": "본인확인 없이 즉시 변경된다고 단정",
                },
                {
                    "id": "SAMPLE_002",
                    "question": "카드 분실 시 가장 먼저 해야 할 일은?",
                    "ground_truth": "카드 분실을 인지하면 즉시 BC카드 고객센터나 공식 앱/웹에서 분실 신고를 진행하도록 안내한다.",
                    "qa_category": "BC FAQ",
                    "qa_topic": "안전/분실",
                    "question_type": "절차안내",
                    "forbidden_claims": "신고를 늦춰도 피해 보상이 항상 된다고 안내",
                },
            ]
        )
        self.send_download(
            buffer.getvalue(),
            filename="question_dataset_sample.csv",
            content_type="text/csv; charset=utf-8",
        )

    def handle_upload_question_dataset(self):
        payload = self.read_json_body()
        if payload is None:
            self.send_json_body_error("invalid JSON body")
            return
        if not isinstance(payload, dict):
            self.send_json({"error": "request body must be an object"}, status=400)
            return

        role = self.normalize_question_dataset_role(payload.get("role"))
        filename = Path(str(payload.get("filename") or "")).name
        display_name = str(payload.get("name") or "").strip()
        content = str(payload.get("content") or "")
        if not content.strip():
            self.send_json({"error": "CSV content is empty"}, status=400)
            return
        if len(content.encode("utf-8")) > 5 * 1024 * 1024:
            self.send_json({"error": "CSV upload is too large. Keep it under 5 MB."}, status=400)
            return
        if filename and Path(filename).suffix.lower() != ".csv":
            self.send_json({"error": "Only CSV files can be uploaded."}, status=400)
            return

        validation_error = self.validate_question_dataset_csv_content(content)
        if validation_error:
            self.send_json({"error": validation_error}, status=400)
            return

        stem_source = display_name or Path(filename).stem or f"uploaded_dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        target_dir = USER_UPLOAD_CSV_ROOT / role
        target_path = self.unique_question_upload_path(target_dir, stem_source)
        normalized_content = content.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path.write_text(normalized_content, encoding="utf-8")

        with CASE_SUMMARY_CACHE_LOCK:
            CASE_SUMMARY_CACHE.clear()

        dataset_id = f"user__{role}__{target_path.stem}"
        datasets_response = self.questionlist_datasets_response_payload()
        datasets = datasets_response["datasets"]
        uploaded_dataset = next((dataset for dataset in datasets if dataset.get("id") == dataset_id), None)
        self.send_json(
            {
                "status": "ok",
                "dataset": uploaded_dataset,
                "datasets": datasets,
                "defaults": datasets_response["defaults"],
                "catalog": self.eval_catalog_response_payload(),
            }
        )

    def handle_delete_question_dataset(self, dataset_id: str):
        dataset_id = str(dataset_id or "").strip()
        if not dataset_id:
            self.send_json({"error": "dataset id is required"}, status=400)
            return

        dataset = self.discover_question_csv_datasets().get(dataset_id)
        if not dataset:
            self.send_json({"error": f"unknown dataset: {dataset_id}"}, status=404)
            return
        if not dataset.get("user_uploaded"):
            self.send_json({"error": "Only user-uploaded datasets can be deleted."}, status=403)
            return

        path = Path(dataset["path"]).resolve(strict=False)
        upload_root = USER_UPLOAD_CSV_ROOT.resolve(strict=False)
        try:
            path.relative_to(upload_root)
        except ValueError:
            self.send_json({"error": "dataset path is outside user upload directory"}, status=403)
            return
        if path.suffix.lower() != ".csv":
            self.send_json({"error": "Only uploaded CSV datasets can be deleted."}, status=400)
            return
        if not path.exists():
            self.send_json({"error": f"dataset file is missing: {self.display_path(path)}"}, status=404)
            return

        try:
            path.unlink()
        except OSError as exc:
            self.send_json({"error": f"failed to delete dataset: {exc}"}, status=500)
            return

        with CASE_SUMMARY_CACHE_LOCK:
            CASE_SUMMARY_CACHE.clear()

        self.send_json(
            {
                "status": "ok",
                "deleted_dataset": dataset_id,
                **self.questionlist_datasets_response_payload(),
                "catalog": self.eval_catalog_response_payload(),
            }
        )

    def handle_set_question_dataset_default(self):
        payload = self.read_json_body()
        if payload is None:
            self.send_json_body_error("invalid JSON body")
            return
        if not isinstance(payload, dict):
            self.send_json({"error": "request body must be an object"}, status=400)
            return

        role = self.normalize_question_dataset_role(payload.get("role"))
        dataset_id = str(payload.get("dataset_id") or payload.get("dataset") or "").strip()
        if not dataset_id:
            self.send_json({"error": "dataset_id is required"}, status=400)
            return
        path, _filters, resolved_role = self.resolve_question_dataset(dataset_id)
        if not path:
            self.send_json({"error": f"unknown dataset: {dataset_id}"}, status=404)
            return
        if not path.exists():
            self.send_json({"error": f"dataset file is missing: {self.display_path(path)}"}, status=404)
            return
        resolved_role = self.normalize_question_dataset_role(resolved_role or role)
        if resolved_role != role:
            self.send_json({"error": f"{dataset_id} is a {resolved_role} dataset, not {role}."}, status=400)
            return

        settings = self.load_question_dataset_settings()
        defaults = settings.setdefault("defaults", {})
        defaults[role] = dataset_id
        self.write_question_dataset_settings(settings)
        with CASE_SUMMARY_CACHE_LOCK:
            CASE_SUMMARY_CACHE.clear()

        self.send_json(
            {
                **self.questionlist_datasets_response_payload(),
                "catalog": self.eval_catalog_response_payload(),
            }
        )

    def normalize_question_dataset_role(self, value):
        role = str(value or "benchmark").strip().lower()
        return role if role in {"benchmark", "regression"} else "benchmark"

    def validate_question_dataset_csv_content(self, content: str):
        try:
            reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
        except csv.Error as exc:
            return f"CSV parse failed: {exc}"
        fieldnames = [str(field or "").strip().lstrip("\ufeff") for field in (reader.fieldnames or [])]
        if not fieldnames:
            return "CSV header row is required."
        normalized_fields = {field.lower() for field in fieldnames}
        question_fields = {field.lower() for field in CSV_QUESTION_FIELD_ALIASES}
        answer_fields = {field.lower() for field in CSV_ANSWER_FIELD_ALIASES}
        if not normalized_fields.intersection(question_fields):
            return "CSV must include a question column. Recommended columns: id, question, ground_truth."
        if not normalized_fields.intersection(answer_fields):
            return "CSV must include an answer column. Recommended columns: id, question, ground_truth."

        valid_rows = 0
        for row in reader:
            question = csv_row_value(row, *CSV_QUESTION_FIELD_ALIASES)
            answer = csv_row_value(row, *CSV_ANSWER_FIELD_ALIASES)
            if question and answer:
                valid_rows += 1
                break
        if not valid_rows:
            return "CSV must include at least one row with both question and answer text."
        return ""

    def unique_question_upload_path(self, target_dir: Path, stem_source: str):
        stem = self.safe_config_id(stem_source) or f"uploaded_dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        target_path = target_dir / f"{stem}.csv"
        suffix = 2
        while target_path.exists():
            target_path = target_dir / f"{stem}_{suffix}.csv"
            suffix += 1
        return target_path

    def handle_eval_catalog(self):
        catalog = self.load_eval_dataset_catalog()
        pools = catalog.get("pools") if isinstance(catalog.get("pools"), dict) else {}
        profiles = catalog.get("profiles") if isinstance(catalog.get("profiles"), dict) else {}
        pool_payload = {}
        for pool_id, pool in pools.items():
            try:
                path = self.resolve_project_path(str(pool.get("path") or ""))
            except ValueError:
                continue
            if not self.catalog_dataset_visible(pool, path):
                continue
            role = str(pool.get("role") or "regression")
            pool_payload[str(pool_id)] = {
                "id": str(pool_id),
                "label": pool.get("label") or pool_id,
                "role": role,
                "path": self.display_path(path),
                "exists": path.exists(),
                "default_quota": pool.get("default_quota", 0),
                "gate_eligible": bool(pool.get("gate_eligible", role != "benchmark")),
                "dataset_version": pool.get("dataset_version", ""),
                "is_public": bool(pool.get("is_public", False)),
                "total": pool.get("total", pool.get("default_quota", 0)),
                "auto_discovered": bool(pool.get("auto_discovered", False)),
                "user_uploaded": bool(pool.get("user_uploaded", False)),
            }
        visible_profiles = {
            profile_id: profile
            for profile_id, profile in profiles.items()
            if isinstance(profile, dict) and self.catalog_item_visible(profile)
        }
        self.send_json(self.eval_catalog_payload_from_parts(catalog, pool_payload, visible_profiles))

    def eval_catalog_response_payload(self):
        catalog = self.load_eval_dataset_catalog()
        pools = catalog.get("pools") if isinstance(catalog.get("pools"), dict) else {}
        profiles = catalog.get("profiles") if isinstance(catalog.get("profiles"), dict) else {}
        pool_payload = {}
        for pool_id, pool in pools.items():
            try:
                path = self.resolve_project_path(str(pool.get("path") or ""))
            except ValueError:
                continue
            if not self.catalog_dataset_visible(pool, path):
                continue
            role = str(pool.get("role") or "regression")
            pool_payload[str(pool_id)] = {
                "id": str(pool_id),
                "label": pool.get("label") or pool_id,
                "role": role,
                "path": self.display_path(path),
                "exists": path.exists(),
                "default_quota": pool.get("default_quota", 0),
                "total": pool.get("total", pool.get("default_quota", 0)),
                "gate_eligible": bool(pool.get("gate_eligible", role != "benchmark")),
                "dataset_version": pool.get("dataset_version", ""),
                "is_public": bool(pool.get("is_public", False)),
                "auto_discovered": bool(pool.get("auto_discovered", False)),
                "user_uploaded": bool(pool.get("user_uploaded", False)),
            }
        visible_profiles = {
            profile_id: profile
            for profile_id, profile in profiles.items()
            if isinstance(profile, dict) and self.catalog_item_visible(profile)
        }
        return self.eval_catalog_payload_from_parts(catalog, pool_payload, visible_profiles)

    def eval_catalog_payload_from_parts(self, catalog: dict, pool_payload: dict, visible_profiles: dict):
        pools = catalog.get("pools") if isinstance(catalog.get("pools"), dict) else {}
        return {
            "status": "ok",
            "default_seed": catalog.get("default_seed", 42),
            "pools": pool_payload,
            "profiles": visible_profiles,
            "defaults": self.question_dataset_defaults(pools),
        }

    def handle_questionlist_dataset_cases(self, query: str):
        params = parse_qs(query)
        dataset_id = str(params.get("dataset", ["benchmark_final_full"])[0] or "benchmark_final_full")
        path, filters, role = self.resolve_question_dataset(dataset_id)
        if not path:
            self.send_json({"error": f"unknown dataset: {dataset_id}"}, status=404)
            return
        if not path.exists():
            self.send_json({"error": f"dataset file is missing: {self.display_path(path)}"}, status=404)
            return

        limit = self.safe_int(params.get("limit", ["120"])[0], default=120, minimum=1, maximum=1000)
        cases = []
        for row in self.iter_case_rows(path, dataset_id=dataset_id, role=role):
            if not self.case_matches_filters(row, filters):
                continue
            cases.append(self.normalize_dataset_case(row, dataset_id))
            if len(cases) >= limit:
                break
        self.send_json(
            {
                "status": "ok",
                "dataset": dataset_id,
                "path": self.display_path(path),
                "limit": limit,
                "count": len(cases),
                "cases": cases,
            }
        )

    def handle_answers_template_download(self, query: str):
        params = parse_qs(query)
        dataset_id = str(params.get("dataset", ["benchmark_final_full"])[0] or "benchmark_final_full")
        config_id = self.safe_config_id(str(params.get("config_id", ["external_model_v1"])[0] or "external_model_v1"))
        model = str(params.get("model", [config_id])[0] or config_id)
        display_name = str(params.get("display_name", [model])[0] or model)
        limit = self.safe_int(params.get("limit", ["100000"])[0], default=100000, minimum=1, maximum=100000)
        path, filters, role = self.resolve_question_dataset(dataset_id)
        if not path:
            self.send_json({"error": f"unknown dataset: {dataset_id}"}, status=404)
            return
        if not path.exists():
            self.send_json({"error": f"dataset file is missing: {self.display_path(path)}"}, status=404)
            return

        buffer = io.StringIO()
        fieldnames = [
            "case_id",
            "config_id",
            "model",
            "display_name",
            "question",
            "model_answer",
            "status",
            "latency_ms",
            "raw_response",
        ]
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        count = 0
        for row in self.iter_case_rows(path, dataset_id=dataset_id, role=role):
            if not self.case_matches_filters(row, filters):
                continue
            case = self.normalize_dataset_case(row, dataset_id)
            writer.writerow(
                {
                    "case_id": case.get("case_id", ""),
                    "config_id": config_id,
                    "model": model,
                    "display_name": display_name,
                    "question": case.get("question", ""),
                    "model_answer": "",
                    "status": "ok",
                    "latency_ms": "",
                    "raw_response": "",
                }
            )
            count += 1
            if count >= limit:
                break
        filename = f"answers_template_{dataset_id}_{config_id}.csv"
        self.send_download(buffer.getvalue(), filename=filename, content_type="text/csv; charset=utf-8")

    def handle_eval_jobs(self):
        self.load_persisted_eval_jobs()
        with EVAL_JOBS_LOCK:
            jobs = [self.job_for_response(job, include_log=False) for job in EVAL_JOBS.values()]
        jobs.sort(key=lambda job: job.get("started_at", ""), reverse=True)
        self.send_json({"status": "ok", "jobs": jobs[:30]})

    def handle_eval_job(self, job_id: str):
        self.load_persisted_eval_jobs(job_id=job_id)
        with EVAL_JOBS_LOCK:
            job = EVAL_JOBS.get(job_id)
        if not job:
            self.send_json({"error": f"unknown job: {job_id}"}, status=404)
            return
        self.send_json({"status": "ok", "job": self.job_for_response(job, include_log=True)})

    def handle_eval_job_control(self, job_id: str):
        payload = self.read_json_body()
        if payload is None:
            self.send_json_body_error()
            return
        payload = payload or {}
        action = str(payload.get("action") or "").strip().lower()
        if action not in {"pause", "resume", "cancel"}:
            self.send_json({"error": "action must be one of: pause, resume, cancel"}, status=400)
            return

        self.load_persisted_eval_jobs(job_id=job_id)
        with EVAL_JOBS_LOCK:
            job = EVAL_JOBS.get(job_id)
        if not job:
            self.send_json({"error": f"unknown job: {job_id}"}, status=404)
            return
        if job.get("runner_type") not in {"multi_model_eval", "judge_saved_answers"}:
            self.send_json({"error": "pause/resume/cancel controls are only available for eval jobs."}, status=400)
            return
        if job.get("status") in {"finished", "failed", "interrupted", "canceled"}:
            self.send_json({"error": f"job is already {job.get('status')}"}, status=409)
            return

        control_path = self.job_control_path(job)
        now = datetime.now().isoformat(timespec="seconds")
        if action == "pause":
            self.write_job_control(control_path, {"action": "pause", "requested_at": now})
            job["status"] = "paused"
            job["paused_at"] = now
        elif action == "resume":
            self.clear_job_control(control_path)
            job["status"] = "running" if self.process_is_running(job.get("pid")) else "interrupted"
            job["resumed_at"] = now
        elif action == "cancel":
            self.write_job_control(control_path, {"action": "cancel", "requested_at": now})
            job["status"] = "canceling" if self.process_is_running(job.get("pid")) else "canceled"
            job["cancel_requested_at"] = now

        with EVAL_JOBS_LOCK:
            EVAL_JOBS[job_id] = job
            self.persist_eval_job(job)
        self.send_json({"status": "ok", "job": self.job_for_response(job, include_log=True)})

    def job_control_path(self, job: dict) -> Path:
        if job.get("control_path"):
            return Path(str(job["control_path"]))
        log_path = Path(str(job.get("log_path") or ""))
        if log_path:
            return log_path.with_suffix(".control.json")
        return WEB_JOBS_ROOT / f"{job.get('job_id', 'unknown')}.control.json"

    def write_job_control(self, path: Path, payload: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def clear_job_control(self, path: Path):
        try:
            path.unlink()
        except FileNotFoundError:
            return
        except OSError:
            return

    def read_job_control(self, job: dict) -> dict:
        path = self.job_control_path(job)
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def handle_start_eval_run(self):
        payload = self.read_json_body()
        if payload is None:
            self.send_json_body_error()
            return

        requested_job_id = self.safe_run_id(payload.get("job_id") or payload.get("resume_job_id") or "")
        job_id = requested_job_id or uuid.uuid4().hex[:12]
        log_dir = WEB_JOBS_ROOT
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{job_id}.log"
        control_path = log_dir / f"{job_id}.control.json"
        self.clear_job_control(control_path)

        run_profile = str(payload.get("run_profile") or payload.get("profile") or "single_dataset").strip()
        is_composed_run = run_profile not in {"", "single_dataset"}
        dataset_id = str(payload.get("dataset") or "benchmark_final_full")
        composed_summary_path = ""
        composed_summary = {}
        raw_cases_file = str(payload.get("cases_file") or payload.get("raw_cases_file") or "").strip()
        if raw_cases_file:
            try:
                cases_path = self.resolve_project_path(raw_cases_file)
            except ValueError as exc:
                self.send_json({"error": str(exc)}, status=400)
                return
            if not cases_path.exists():
                self.send_json({"error": f"cases file is missing: {self.display_path(cases_path)}"}, status=404)
                return
            is_composed_run = True
            composed_summary = {
                "profile_id": dataset_id,
                "source_format": cases_path.suffix.lstrip(".").lower() or "file",
                "source_path": self.display_path(cases_path),
            }
        elif is_composed_run:
            catalog = self.load_eval_dataset_catalog()
            profile_id = "custom" if run_profile in {"custom", "custom_seeded_mix"} else run_profile
            seed = self.safe_int(payload.get("seed"), default=int(catalog.get("default_seed", 42)), minimum=0, maximum=2_147_483_647)
            try:
                pool_overrides = self.pool_overrides_from_payload(payload.get("pool_quotas") or payload.get("pools"))
            except ValueError as exc:
                self.send_json({"error": str(exc)}, status=400)
                return
            if profile_id == "custom" and not pool_overrides:
                self.send_json({"error": "Custom Seeded Mix requires at least one pool quota greater than zero."}, status=400)
                return
            try:
                composed_cases, composed_summary = compose_dataset(
                    catalog=catalog,
                    profile_id=profile_id,
                    pool_overrides=pool_overrides,
                    seed=seed,
                )
            except (FileNotFoundError, ValueError, RuntimeError) as exc:
                self.send_json({"error": str(exc)}, status=400)
                return
            dataset_id = profile_id
            cases_path = log_dir / f"{job_id}_{profile_id}_cases.jsonl"
            summary_path = cases_path.with_suffix(".summary.json")
            write_composed_jsonl(cases_path, composed_cases)
            summary_path.write_text(json.dumps(composed_summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            composed_summary_path = str(summary_path)
        else:
            cases_path = QUESTIONLIST_DATASET_FILES.get(dataset_id)
            if not cases_path:
                pool = self.catalog_pool(dataset_id)
                if pool:
                    catalog = self.load_eval_dataset_catalog()
                    seed = self.safe_int(payload.get("seed"), default=int(catalog.get("default_seed", 42)), minimum=0, maximum=2_147_483_647)
                    quota = int(pool.get("default_quota") or 0)
                    try:
                        composed_cases, composed_summary = compose_dataset(
                            catalog=catalog,
                            profile_id="custom",
                            pool_overrides={dataset_id: quota},
                            seed=seed,
                        )
                    except (FileNotFoundError, ValueError, RuntimeError) as exc:
                        self.send_json({"error": str(exc)}, status=400)
                        return
                    cases_path = log_dir / f"{job_id}_{dataset_id}_cases.jsonl"
                    summary_path = cases_path.with_suffix(".summary.json")
                    write_composed_jsonl(cases_path, composed_cases)
                    summary_path.write_text(json.dumps(composed_summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                    composed_summary_path = str(summary_path)
                    is_composed_run = True
            if not cases_path:
                self.send_json({"error": f"unknown dataset: {dataset_id}"}, status=400)
                return
            if not cases_path.exists():
                self.send_json({"error": f"dataset file is missing: {self.display_path(cases_path)}"}, status=404)
                return

        is_tool_agent_run = dataset_id.startswith("tool_agent")
        registry = self.load_registry()
        configs = [
            self.safe_config_id(config_id)
            for config_id in payload.get("configs", [])
            if self.safe_config_id(config_id)
        ]
        configs = [config_id for config_id in configs if config_id in registry]
        target_selection_mode = str(payload.get("target_selection_mode") or "single").strip()
        if target_selection_mode not in {"single", "multi"}:
            self.send_json({"error": f"unknown target_selection_mode: {target_selection_mode}"}, status=400)
            return
        non_target_configs = [
            config_id for config_id in configs if not self.is_eval_target_model(registry.get(config_id, {}))
        ]
        if non_target_configs:
            self.send_json(
                {
                    "error": "Judge/router/auxiliary configs cannot be selected as target models: "
                    + ", ".join(non_target_configs)
                },
                status=400,
            )
            return
        if not configs and not is_tool_agent_run:
            self.send_json({"error": "Select at least one registered model config."}, status=400)
            return
        if target_selection_mode == "single" and len(configs) > 1 and not is_tool_agent_run:
            self.send_json({"error": "Single-model runs accept exactly one target model. Use multi target mode for comparisons."}, status=400)
            return

        suites = [str(suite).strip() for suite in payload.get("suites", []) if str(suite).strip()]
        limit = self.optional_limit(payload.get("limit"), default=None if is_composed_run else 10)
        dry_run = bool(payload.get("dry_run", True))
        skip_scoring = bool(payload.get("skip_scoring", False))
        answer_cache_enabled = bool(payload.get("answer_cache", True))
        judge_cache_enabled = bool(payload.get("judge_cache", True))
        arbiter_cache_enabled = bool(payload.get("arbiter_cache", True))
        if skip_scoring:
            dry_run = False
        export_final_ui = bool(payload.get("export_final_ui", False)) and not skip_scoring
        prediction_file = str(payload.get("prediction_file") or "").strip()
        raw_run_id = str(payload.get("run_id") or "").strip()
        run_id_auto_generated = not raw_run_id
        requested_run_id = self.safe_run_id(raw_run_id or f"WEB_EVAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        run_id = self.unique_eval_run_id(requested_run_id)
        run_id_deduplicated = run_id != requested_run_id
        scoring_mode = str(payload.get("scoring_mode") or "static").strip()
        requested_scoring_mode = scoring_mode
        if scoring_mode == "llm_blended":
            scoring_mode = "llm_override"
        if scoring_mode not in {"static", "static_llm", "llm_override", "blend"}:
            self.send_json({"error": f"unknown scoring_mode: {scoring_mode}"}, status=400)
            return
        static_embedding_payload = payload.get("static_embedding") if isinstance(payload.get("static_embedding"), dict) else {}
        static_embedding_enabled = bool(static_embedding_payload.get("enabled")) and not skip_scoring
        static_embedding_model = str(static_embedding_payload.get("model") or "").strip()
        static_embedding_base_url = str(static_embedding_payload.get("base_url") or "").strip()
        static_embedding_keep_alive = str(static_embedding_payload.get("keep_alive") or "0").strip()
        if static_embedding_enabled and not static_embedding_model:
            self.send_json({"error": "static_embedding.model is required when static embedding similarity is enabled."}, status=400)
            return
        judge_payload = payload.get("judge") if isinstance(payload.get("judge"), dict) else {}
        judge_config_ids = []
        judge_config_label = ""
        judge_score_weights = {}
        judge_aggregation_method = self.judge_aggregation_method_from_payload(judge_payload)
        conflict_policy = str(judge_payload.get("conflict_policy") or "review").strip()
        if conflict_policy not in {"review", "arbiter_override", "three_judge"}:
            self.send_json({"error": f"unknown conflict_policy: {conflict_policy}"}, status=400)
            return
        arbiter_config_id = self.safe_config_id(judge_payload.get("arbiter_config_id") or "")
        judge_mode = {
            "static_llm": "audit",
            "llm_override": "override",
            "blend": "blend",
        }.get(scoring_mode, "audit")
        judge_blend_weight = self.safe_float(judge_payload.get("blend_weight"), default=0.5, minimum=0.0, maximum=1.0)
        subprocess_env = os.environ.copy()
        subprocess_env.setdefault("PYTHONIOENCODING", "utf-8")
        subprocess_env.setdefault("PYTHONUNBUFFERED", "1")
        subprocess_env.setdefault("EVAL_JUDGE_JOB_DIR", str(EVAL_ARCHIVE_ROOT / "judge_jobs"))
        subprocess_env.setdefault("EVAL_JUDGE_CHILD_RUN_ROOT", str(EVAL_ARCHIVE_ROOT / "judge_runs"))

        runner_config_path = ""

        if not is_tool_agent_run and not skip_scoring and scoring_mode != "static":
            judge_result = self.prepare_judge_config(
                registry=registry,
                judge_payload=judge_payload,
                scoring_mode=scoring_mode,
                job_id=job_id,
                log_dir=log_dir,
                dry_run=dry_run,
                subprocess_env=subprocess_env,
            )
            if "error" in judge_result:
                self.send_json({"error": judge_result["error"]}, status=400)
                return
            judge_config_ids = list(judge_result.get("judge_config_ids") or [judge_result["judge_config_id"]])
            if requested_scoring_mode == "llm_override" and len(judge_config_ids) > 1:
                self.send_json({"error": "Single-Judge scoring accepts exactly one judge config. Use llm_blended for multiple judges."}, status=400)
                return
            if judge_aggregation_method == "weighted_mean":
                judge_score_weights, weight_error = self.judge_score_weights_from_payload(judge_payload, judge_config_ids)
                if weight_error:
                    self.send_json({"error": weight_error}, status=400)
                    return
            if len(judge_config_ids) > 1 and arbiter_config_id:
                if arbiter_config_id not in registry:
                    self.send_json({"error": f"unknown arbiter config: {arbiter_config_id}"}, status=400)
                    return
                arbiter_config = registry[arbiter_config_id]
                token, api_key_env = self.provider_api_key_value(arbiter_config)
                if token and api_key_env:
                    subprocess_env[api_key_env] = token
                if arbiter_config.get("provider") != "ollama" and api_key_env and not dry_run and not subprocess_env.get(api_key_env):
                    self.send_json({"error": f"API key is required for arbiter config {arbiter_config_id}."}, status=400)
                    return
                if conflict_policy == "review":
                    conflict_policy = "arbiter_override"
            elif len(judge_config_ids) <= 1:
                arbiter_config_id = ""
                conflict_policy = "review"
            elif conflict_policy in {"arbiter_override", "three_judge"}:
                self.send_json({"error": "Arbiter conflict handling requires an arbiter config."}, status=400)
                return
            judge_config_label = ", ".join(judge_config_ids)
            runner_config_path = judge_result.get("runner_config_path", "")

        if not is_tool_agent_run and not runner_config_path:
            runner_config_path = self.write_runner_model_configs(
                registry=registry,
                job_id=job_id,
                log_dir=log_dir,
            )

        runner_type = "tool_agent_trace" if is_tool_agent_run else "multi_model_eval"
        template_output = ""
        output_dir = ""
        resolved_prediction_file = ""
        runner_python = eval_runner_python()

        if is_tool_agent_run:
            cmd = [
                runner_python,
                str(PROJECT_ROOT / "scripts" / "eval" / "score_tool_agent_traces.py"),
                "--scenarios",
                str(cases_path),
            ]
            if limit is not None:
                cmd.extend(["--limit", str(limit)])
            if dry_run:
                template_path = log_dir / f"{job_id}_prediction_template.jsonl"
                template_output = str(template_path)
                cmd.extend(["--template-output", str(template_path)])
            else:
                try:
                    prediction_path = self.resolve_project_path(prediction_file)
                except ValueError as exc:
                    self.send_json({"error": str(exc)}, status=400)
                    return
                if not prediction_file or not prediction_path.exists():
                    self.send_json(
                        {
                            "error": "Tool-agent runs require an existing prediction JSONL path when Dry run is off.",
                            "prediction_file": prediction_file,
                        },
                        status=400 if prediction_file else 422,
                    )
                    return
                output_path = EVAL_RUNS_ROOT / f"{run_id}_tool_agent"
                resolved_prediction_file = str(prediction_path)
                output_dir = str(output_path)
                cmd.extend(["--predictions", str(prediction_path), "--out-dir", str(output_path)])
        else:
            cmd = [
                runner_python,
                str(PROJECT_ROOT / "scripts" / "eval" / "run_multi_model_eval.py"),
                "--cases-file",
                str(cases_path),
                "--run-id",
                run_id,
                "--control-file",
                str(control_path),
            ]
            if limit is not None:
                cmd.extend(["--limit", str(limit)])
            if runner_config_path:
                cmd.extend(["--registry", runner_config_path])
            for config_id in configs:
                cmd.extend(["--config", config_id])
            for suite in suites:
                cmd.extend(["--suite", suite])
            cmd.append("--sequential-model-eval")
            cmd.extend(["--scoring-mode", scoring_mode])
            if skip_scoring:
                cmd.append("--skip-scoring")
            if not answer_cache_enabled:
                cmd.append("--no-answer-cache")
            if not judge_cache_enabled:
                cmd.append("--no-judge-cache")
            if not arbiter_cache_enabled:
                cmd.append("--no-arbiter-cache")
            if static_embedding_enabled:
                cmd.extend(["--static-embedding-model", static_embedding_model])
                if static_embedding_base_url:
                    cmd.extend(["--static-embedding-base-url", static_embedding_base_url])
                if static_embedding_keep_alive:
                    cmd.extend(["--static-embedding-keep-alive", static_embedding_keep_alive])
            if judge_config_ids:
                for selected_judge_config_id in judge_config_ids:
                    cmd.extend(["--judge-config", selected_judge_config_id])
                cmd.extend(["--judge-mode", judge_mode])
                cmd.extend(["--judge-aggregation-method", judge_aggregation_method])
                cmd.extend(["--conflict-policy", conflict_policy])
                if arbiter_config_id:
                    cmd.extend(["--arbiter-config", arbiter_config_id])
                if judge_aggregation_method == "weighted_mean" and len(judge_score_weights) > 1:
                    cmd.extend(["--judge-score-weights", json.dumps(judge_score_weights, ensure_ascii=False, sort_keys=True)])
                if scoring_mode == "blend":
                    cmd.extend(["--judge-blend-weight", str(judge_blend_weight)])
            if dry_run:
                cmd.append("--dry-run")
            elif export_final_ui:
                cmd.append("--export-final-ui")

        job = {
            "job_id": job_id,
            "status": "running",
            "run_id": run_id,
            "requested_run_id": requested_run_id,
            "run_id_auto_generated": run_id_auto_generated,
            "run_id_deduplicated": run_id_deduplicated,
            "runner_type": runner_type,
            "dataset": dataset_id,
            "run_profile": run_profile,
            "cases_file": self.display_path(cases_path),
            "composed_summary_path": self.display_path(Path(composed_summary_path)) if composed_summary_path else "",
            "composed_summary": composed_summary,
            "configs": configs,
            "suites": suites,
            "limit": limit,
            "scoring_mode": "answers_only" if skip_scoring else scoring_mode,
            "skip_scoring": skip_scoring,
            "answer_cache": answer_cache_enabled,
            "judge_cache": judge_cache_enabled,
            "arbiter_cache": arbiter_cache_enabled,
            "static_embedding_model": static_embedding_model if static_embedding_enabled else "",
            "static_embedding_base_url": static_embedding_base_url if static_embedding_enabled else "",
            "judge_config": judge_config_label,
            "judge_config_ids": judge_config_ids,
            "judge_mode": judge_mode if judge_config_ids else "",
            "judge_blend_weight": judge_blend_weight if judge_config_ids else "",
            "judge_aggregation_method": judge_aggregation_method if judge_config_ids else "",
            "judge_score_weights": judge_score_weights if judge_config_ids else {},
            "conflict_policy": conflict_policy if judge_config_ids else "",
            "arbiter_config_id": arbiter_config_id if judge_config_ids else "",
            "dry_run": dry_run,
            "export_final_ui": export_final_ui,
            "prediction_file": resolved_prediction_file or prediction_file,
            "template_output": template_output,
            "output_dir": output_dir,
            "command": cmd,
            "python_executable": runner_python,
            "log_path": str(log_path),
            "control_path": str(control_path),
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "finished_at": "",
            "returncode": None,
        }

        try:
            log_file = log_path.open("w", encoding="utf-8")
            creationflags = 0
            if os.name == "nt":
                creationflags = subprocess.CREATE_NO_WINDOW
            process = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                env=subprocess_env,
                creationflags=creationflags,
            )
            log_file.close()
            job["pid"] = process.pid
        except OSError as exc:
            job["status"] = "failed"
            job["finished_at"] = datetime.now().isoformat(timespec="seconds")
            job["returncode"] = -1
            log_path.write_text(f"Failed to start eval runner: {exc}\n", encoding="utf-8")
            with EVAL_JOBS_LOCK:
                EVAL_JOBS[job_id] = job
            self.send_json({"status": "failed", "job": self.job_for_response(job, include_log=True)}, status=500)
            return

        with EVAL_JOBS_LOCK:
            EVAL_JOBS[job_id] = job
        self.persist_eval_job(job)

        thread = threading.Thread(target=self.wait_for_eval_job, args=(job_id, process), daemon=True)
        thread.start()
        self.send_json({"status": "ok", "job": self.job_for_response(job, include_log=False)}, status=202)

    def handle_start_saved_answer_judge(self):
        payload = self.read_json_body()
        if payload is None:
            self.send_json_body_error()
            return

        source_run_id = self.safe_run_id(payload.get("source_run_id") or "") if payload.get("source_run_id") else ""
        answers_csv = str(payload.get("answers_csv") or "").strip()
        if not source_run_id and not answers_csv:
            self.send_json({"error": "Source run ID 또는 answers CSV path 중 하나가 필요합니다."}, status=400)
            return
        if source_run_id and answers_csv:
            self.send_json({"error": "Source run ID와 answers CSV path는 동시에 사용할 수 없습니다."}, status=400)
            return

        dataset_id = str(payload.get("dataset") or "benchmark_final_full")
        cases_path = None
        if answers_csv:
            cases_path, _, _ = self.resolve_question_dataset(dataset_id)
            if not cases_path:
                self.send_json({"error": f"unknown dataset: {dataset_id}"}, status=404)
                return
            if not cases_path.exists():
                self.send_json({"error": f"dataset file is missing: {self.display_path(cases_path)}"}, status=404)
                return
            try:
                answers_path = self.resolve_project_path(answers_csv)
            except ValueError as exc:
                self.send_json({"error": str(exc)}, status=400)
                return
            if not answers_path.exists():
                self.send_json({"error": f"answers CSV not found: {self.display_path(answers_path)}"}, status=404)
                return
        else:
            source_dir = self.resolve_eval_run_dir(source_run_id)
            if not source_dir:
                self.send_json({"error": f"source eval run not found: {source_run_id}"}, status=404)
                return

        scoring_mode = str(payload.get("scoring_mode") or "static_llm").strip()
        requested_scoring_mode = scoring_mode
        if scoring_mode == "llm_blended":
            scoring_mode = "llm_override"
        if scoring_mode not in {"static", "static_llm", "llm_override", "blend"}:
            self.send_json({"error": f"unknown scoring_mode: {scoring_mode}"}, status=400)
            return
        judge_mode = {
            "static": "audit",
            "static_llm": "audit",
            "llm_override": "override",
            "blend": "blend",
        }[scoring_mode]
        judge_payload = payload.get("judge") if isinstance(payload.get("judge"), dict) else {}
        judge_blend_weight = self.safe_float(judge_payload.get("blend_weight"), default=0.5, minimum=0.0, maximum=1.0)
        conflict_policy = str(judge_payload.get("conflict_policy") or "review").strip()
        if conflict_policy not in {"review", "arbiter_override", "three_judge"}:
            self.send_json({"error": f"unknown conflict_policy: {conflict_policy}"}, status=400)
            return
        arbiter_config_id = self.safe_config_id(judge_payload.get("arbiter_config_id") or "")
        export_final_ui = bool(payload.get("export_final_ui", True))
        judge_cache_enabled = bool(payload.get("judge_cache", True))
        arbiter_cache_enabled = bool(payload.get("arbiter_cache", True))
        static_embedding_payload = payload.get("static_embedding") if isinstance(payload.get("static_embedding"), dict) else {}
        static_embedding_enabled = bool(static_embedding_payload.get("enabled"))
        static_embedding_model = str(static_embedding_payload.get("model") or "").strip()
        static_embedding_base_url = str(static_embedding_payload.get("base_url") or "").strip()
        if static_embedding_enabled and not static_embedding_model:
            self.send_json({"error": "static_embedding.model is required when static embedding similarity is enabled."}, status=400)
            return

        job_id = uuid.uuid4().hex[:12]
        log_dir = WEB_JOBS_ROOT
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"{job_id}.log"
        control_path = log_dir / f"{job_id}.control.json"
        self.clear_job_control(control_path)

        run_id = self.safe_run_id(
            payload.get("run_id")
            or (
                f"{source_run_id}_JUDGE_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                if source_run_id
                else f"IMPORTED_ANSWERS_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
        )
        registry = self.load_registry()
        subprocess_env = os.environ.copy()
        subprocess_env.setdefault("PYTHONIOENCODING", "utf-8")
        subprocess_env.setdefault("PYTHONUNBUFFERED", "1")
        subprocess_env.setdefault("EVAL_JUDGE_JOB_DIR", str(EVAL_ARCHIVE_ROOT / "judge_jobs"))
        subprocess_env.setdefault("EVAL_JUDGE_CHILD_RUN_ROOT", str(EVAL_ARCHIVE_ROOT / "judge_runs"))
        runner_config_path = ""
        judge_config_ids: list[str] = []
        judge_config_label = ""
        judge_score_weights = {}
        judge_aggregation_method = self.judge_aggregation_method_from_payload(judge_payload)
        if scoring_mode != "static":
            judge_result = self.prepare_judge_config(
                registry=registry,
                judge_payload=judge_payload,
                scoring_mode=scoring_mode,
                job_id=job_id,
                log_dir=log_dir,
                dry_run=False,
                subprocess_env=subprocess_env,
            )
            if "error" in judge_result:
                self.send_json({"error": judge_result["error"]}, status=400)
                return
            judge_config_ids = list(judge_result.get("judge_config_ids") or [judge_result["judge_config_id"]])
            if requested_scoring_mode == "llm_override" and len(judge_config_ids) > 1:
                self.send_json({"error": "Single-Judge scoring accepts exactly one judge config. Use llm_blended for multiple judges."}, status=400)
                return
            if judge_aggregation_method == "weighted_mean":
                judge_score_weights, weight_error = self.judge_score_weights_from_payload(judge_payload, judge_config_ids)
                if weight_error:
                    self.send_json({"error": weight_error}, status=400)
                    return
            if conflict_policy in {"arbiter_override", "three_judge"} and len(judge_config_ids) > 1:
                if not arbiter_config_id:
                    self.send_json({"error": "Arbiter conflict handling requires an arbiter config."}, status=400)
                    return
                if arbiter_config_id not in registry:
                    self.send_json({"error": f"unknown arbiter config: {arbiter_config_id}"}, status=400)
                    return
                arbiter_config = registry[arbiter_config_id]
                token, api_key_env = self.provider_api_key_value(arbiter_config)
                if token and api_key_env:
                    subprocess_env[api_key_env] = token
                if arbiter_config.get("provider") != "ollama" and api_key_env and not subprocess_env.get(api_key_env):
                    self.send_json({"error": f"API key is required for arbiter config {arbiter_config_id}."}, status=400)
                    return
                if arbiter_config_id not in judge_config_ids:
                    judge_config_ids.append(arbiter_config_id)
                if len(judge_config_ids) < 3:
                    self.send_json({"error": "arbiter conflict handling requires two base judges plus one arbiter config."}, status=400)
                    return
            judge_config_label = ", ".join(judge_config_ids)
            runner_config_path = judge_result.get("runner_config_path", "")

        configs = self.saved_answer_config_ids(source_run_id=source_run_id, answers_csv=answers_csv, default_config_id=payload.get("external_config_id"))
        runner_python = eval_runner_python()
        use_independent_judges = scoring_mode != "static" and len(judge_config_ids) > 1
        judge_runner_script = (
            "run_independent_judge_pipeline.py"
            if use_independent_judges
            else "judge_saved_answers.py"
        )
        cmd = [
            runner_python,
            str(PROJECT_ROOT / "scripts" / "eval" / judge_runner_script),
            "--run-id",
            run_id,
            "--out-root",
            str(EVAL_RUNS_ROOT),
            "--control-file",
            str(control_path),
            "--scoring-mode",
            scoring_mode,
        ]
        if runner_config_path:
            cmd.extend(["--registry", runner_config_path])
        if source_run_id:
            cmd.extend(["--source-run-id", source_run_id])
        else:
            cmd.extend(["--answers-csv", str(answers_path)])
            cmd.extend(["--cases-file", str(cases_path)])
            external_config_id = self.safe_config_id(payload.get("external_config_id") or "external_model_v1")
            cmd.extend(["--external-config-id", external_config_id])
        for selected_judge_config_id in judge_config_ids:
            cmd.extend(["--judge-config", selected_judge_config_id])
        if scoring_mode != "static":
            cmd.extend(["--judge-mode", judge_mode])
            cmd.extend(["--judge-aggregation-method", judge_aggregation_method])
            if judge_aggregation_method == "weighted_mean" and len(judge_score_weights) > 1:
                cmd.extend(["--judge-score-weights", json.dumps(judge_score_weights, ensure_ascii=False, sort_keys=True)])
            if scoring_mode == "blend":
                cmd.extend(["--judge-blend-weight", str(judge_blend_weight)])
            if use_independent_judges:
                cmd.extend(["--workers", "1"])
                cmd.extend(["--rate-limit-sleep-seconds", "120"])
                cmd.extend(["--min-ok-judges", "1"])
                cmd.extend(["--conflict-policy", conflict_policy])
                if arbiter_config_id:
                    cmd.extend(["--arbiter-config", arbiter_config_id])
        if not judge_cache_enabled:
            cmd.append("--no-judge-cache")
        if not arbiter_cache_enabled:
            cmd.append("--no-arbiter-cache")
        if static_embedding_enabled:
            cmd.extend(["--static-embedding-model", static_embedding_model])
            if static_embedding_base_url:
                cmd.extend(["--static-embedding-base-url", static_embedding_base_url])
        if export_final_ui:
            cmd.append("--export-final-ui")

        job = {
            "job_id": job_id,
            "status": "running",
            "run_id": run_id,
            "runner_type": "judge_saved_answers",
            "dataset": dataset_id,
            "source_run_id": source_run_id,
            "answers_csv": answers_csv,
            "cases_file": self.display_path(Path(cases_path)) if cases_path else "",
            "configs": configs,
            "suites": [],
            "limit": None,
            "scoring_mode": scoring_mode,
            "static_embedding_model": static_embedding_model if static_embedding_enabled else "",
            "static_embedding_base_url": static_embedding_base_url if static_embedding_enabled else "",
            "judge_config": judge_config_label,
            "judge_config_ids": judge_config_ids,
            "independent_judge_runs": use_independent_judges,
            "conflict_policy": conflict_policy if use_independent_judges else "",
            "arbiter_config_id": arbiter_config_id if use_independent_judges else "",
            "judge_mode": judge_mode if judge_config_ids else "",
            "judge_aggregation_method": judge_aggregation_method if judge_config_ids else "",
            "judge_blend_weight": judge_blend_weight if judge_config_ids else "",
            "judge_score_weights": judge_score_weights if judge_config_ids else {},
            "judge_cache": judge_cache_enabled,
            "arbiter_cache": arbiter_cache_enabled,
            "dry_run": False,
            "export_final_ui": export_final_ui,
            "output_dir": str(EVAL_RUNS_ROOT / run_id),
            "command": cmd,
            "python_executable": runner_python,
            "log_path": str(log_path),
            "control_path": str(control_path),
            "started_at": datetime.now().isoformat(timespec="seconds"),
            "finished_at": "",
            "returncode": None,
        }

        try:
            log_file = log_path.open("w", encoding="utf-8")
            creationflags = 0
            if os.name == "nt":
                creationflags = subprocess.CREATE_NO_WINDOW
            process = subprocess.Popen(
                cmd,
                cwd=str(PROJECT_ROOT),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
                env=subprocess_env,
                creationflags=creationflags,
            )
            log_file.close()
            job["pid"] = process.pid
        except OSError as exc:
            job["status"] = "failed"
            job["finished_at"] = datetime.now().isoformat(timespec="seconds")
            job["returncode"] = -1
            log_path.write_text(f"Failed to start saved-answer judge runner: {exc}\n", encoding="utf-8")
            with EVAL_JOBS_LOCK:
                EVAL_JOBS[job_id] = job
            self.send_json({"status": "failed", "job": self.job_for_response(job, include_log=True)}, status=500)
            return

        with EVAL_JOBS_LOCK:
            EVAL_JOBS[job_id] = job
        self.persist_eval_job(job)
        thread = threading.Thread(target=self.wait_for_eval_job, args=(job_id, process), daemon=True)
        thread.start()
        self.send_json({"status": "ok", "job": self.job_for_response(job, include_log=False)}, status=202)

    def saved_answer_config_ids(self, *, source_run_id: str, answers_csv: str, default_config_id: str | None):
        if source_run_id:
            source_dir = self.resolve_eval_run_dir(source_run_id)
            if source_dir:
                rows = self.load_partitioned_outputs(source_dir)
                ids = sorted({str(row.get("config_id") or "") for row in rows if row.get("config_id")})
                if ids:
                    return ids
            return []
        try:
            path = self.resolve_project_path(answers_csv)
        except ValueError:
            return [self.safe_config_id(default_config_id or "external_model_v1")]
        ids = []
        if path.exists():
            try:
                with path.open(encoding="utf-8-sig", newline="") as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        config_id = text_value(row.get("config_id"), row.get("model_id"), row.get("version"))
                        if config_id:
                            ids.append(config_id)
            except OSError:
                pass
        if not ids:
            ids = [self.safe_config_id(default_config_id or "external_model_v1")]
        return sorted(dict.fromkeys(ids))

    def handle_reblend_eval_run(self):
        payload = self.read_json_body()
        if payload is None:
            self.send_json_body_error()
            return
        source_run_id = self.safe_run_id(payload.get("source_run_id") or "") if payload.get("source_run_id") else ""
        source_dir = self.resolve_eval_run_dir(source_run_id)
        if not source_dir:
            self.send_json({"error": "No source eval run found."}, status=404)
            return
        scoring_mode = str(payload.get("scoring_mode") or "blend").strip()
        if scoring_mode == "llm_blended":
            scoring_mode = "llm_override"
        if scoring_mode not in {"static", "static_llm", "llm_override", "blend"}:
            self.send_json({"error": f"unknown scoring_mode: {scoring_mode}"}, status=400)
            return
        source_config = self.load_eval_run_config(source_dir)
        if "error" in source_config:
            self.send_json(source_config, status=400)
            return
        matrix = source_config.get("matrix") if isinstance(source_config.get("matrix"), dict) else {}
        pass_threshold = self.safe_float(
            payload.get("pass_threshold"),
            default=self.safe_float(matrix.get("pass_threshold"), default=0.6, minimum=0.0, maximum=1.0),
            minimum=0.0,
            maximum=1.0,
        )
        blend_weight = self.safe_float(payload.get("blend_weight"), default=0.5, minimum=0.0, maximum=1.0)
        run_id = self.safe_run_id(
            payload.get("run_id")
            or f"{source_dir.name}_REBLEND_{int(round(blend_weight * 100)):03d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        run_id = self.unique_eval_run_id(run_id)
        export_final_ui = bool(payload.get("export_final_ui", True))
        result = self.reblend_eval_run(
            source_dir=source_dir,
            source_config=source_config,
            run_id=run_id,
            scoring_mode=scoring_mode,
            blend_weight=blend_weight,
            pass_threshold=pass_threshold,
            export_final_ui=export_final_ui,
        )
        if "error" in result:
            self.send_json(result, status=400)
            return
        self.send_json({"status": "ok", **result})

    def resolve_eval_run_dir(self, run_id: str):
        if run_id:
            candidate = EVAL_RUNS_ROOT / run_id
            if not self.is_reserved_eval_run_name(candidate.name) and candidate.is_dir() and self.is_reblend_source_dir(candidate):
                return candidate
            return None
        return self.latest_reblend_run_dir()

    def load_eval_run_config(self, run_dir: Path):
        config_path = self.run_config_path(run_dir)
        if not config_path.exists():
            return {"error": f"source run has no config.json/config.yaml: {run_dir.name}"}
        try:
            loaded = self.load_structured_file(config_path)
        except Exception as exc:
            return {"error": f"source run config is not valid JSON/YAML: {exc}"}
        return loaded if isinstance(loaded, dict) else {"error": "source run config must be an object."}

    def unique_eval_run_id(self, run_id: str):
        candidate = run_id
        suffix = 2
        while self.eval_run_id_in_use(candidate):
            candidate = self.safe_run_id(f"{run_id}_{suffix}")
            suffix += 1
        return candidate

    def eval_run_id_in_use(self, run_id: str):
        if (EVAL_RUNS_ROOT / run_id).exists() or (EVAL_RUNS_ROOT / f"{run_id}_tool_agent").exists():
            return True
        with EVAL_JOBS_LOCK:
            if any(str(job.get("run_id") or "") == run_id for job in EVAL_JOBS.values()):
                return True
        for log_dir in self.eval_job_dirs():
            for path in log_dir.glob("*.job.json"):
                try:
                    job = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    continue
                if isinstance(job, dict) and str(job.get("run_id") or "") == run_id:
                    return True
        return False

    def reblend_eval_run(
        self,
        *,
        source_dir: Path,
        source_config: dict,
        run_id: str,
        scoring_mode: str,
        blend_weight: float,
        pass_threshold: float,
        export_final_ui: bool,
    ):
        try:
            cases_path = self.resolve_project_path(str(source_config.get("case_source") or ""))
        except ValueError as exc:
            return {"error": str(exc)}
        if not cases_path.exists():
            return {"error": f"case source not found: {self.display_path(cases_path)}"}
        if self.has_partitioned_run_source(source_dir):
            projected = self.projected_run_tables(source_dir)
            outputs = list(projected.get("outputs", [])) if projected else self.load_partitioned_outputs(source_dir)
            source_scores = list(projected.get("scores", [])) if projected else []
        else:
            outputs = eval_read_jsonl(source_dir / "model_outputs.jsonl")
            source_scores = eval_read_jsonl(source_dir / "judge_scores.jsonl")
        if not source_scores and (source_dir / "judge_scores.jsonl").exists():
            source_scores = eval_read_jsonl(source_dir / "judge_scores.jsonl")
        if not outputs or not source_scores:
            return {"error": "source run must contain target outputs and judge scores."}
        try:
            cases = eval_read_cases_path(cases_path)
        except (OSError, csv.Error, json.JSONDecodeError, UnicodeDecodeError) as exc:
            return {"error": f"case source could not be read: {self.display_path(cases_path)} ({exc})"}
        if not cases:
            return {"error": f"case source has no readable cases: {self.display_path(cases_path)}"}
        configs = [dict(config) for config in source_config.get("configs", []) if isinstance(config, dict)]
        if not configs:
            registry = self.load_registry()
            config_ids = sorted({str(row.get("config_id") or "") for row in outputs if row.get("config_id")})
            configs = [dict(registry[config_id]) for config_id in config_ids if config_id in registry]
        if not configs:
            return {"error": "source run has no model config metadata."}
        outputs = [{**row, "run_id": run_id} for row in outputs]
        scores = []
        for row in source_scores:
            try:
                scores.append(
                    self.reblend_score_row(
                        row,
                        run_id=run_id,
                        scoring_mode=scoring_mode,
                        blend_weight=blend_weight,
                        pass_threshold=pass_threshold,
                    )
                )
            except ValueError as exc:
                return {"error": str(exc)}
        matrix = source_config.get("matrix") if isinstance(source_config.get("matrix"), dict) else {}
        baseline_config = str(source_config.get("baseline_config") or matrix.get("baseline_config") or configs[0].get("config_id") or "")
        release_gate_config = matrix.get("release_gates") if isinstance(matrix.get("release_gates"), dict) else {}
        eval_started_at = datetime.now().isoformat(timespec="seconds")
        regression_diff = eval_build_regression_diff(cases=cases, scores=scores, baseline_config=baseline_config)
        summary = eval_aggregate_runs(
            run_id=run_id,
            configs=configs,
            scores=scores,
            outputs=outputs,
            eval_started_at=eval_started_at,
        )
        run_release_gates = eval_aggregate_release_gates(
            run_id=run_id,
            cases=cases,
            configs=configs,
            scores=scores,
            release_gate_config=release_gate_config,
        )
        question_rows = eval_question_case_rows(
            cases=cases,
            configs=configs,
            outputs=outputs,
            scores=scores,
            regression_diff=regression_diff,
        )
        slice_rows = eval_qa_slice_score_rows(question_rows)
        run_dir = EVAL_RUNS_ROOT / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        updated_matrix = dict(matrix)
        updated_matrix["scoring_mode"] = scoring_mode
        updated_matrix["judge_blend_weight"] = blend_weight
        updated_config = dict(source_config)
        updated_config.update(
            {
                "run_id": run_id,
                "eval_started_at": eval_started_at,
                "source_run_id": source_dir.name,
                "reweighted_from": source_dir.name,
                "reweight": {
                    "scoring_mode": scoring_mode,
                    "blend_weight": blend_weight,
                    "pass_threshold": pass_threshold,
                },
                "matrix": updated_matrix,
            }
        )
        run_metadata = {
            "run_id": run_id,
            "source_run_id": source_dir.name,
            "run_type": str(source_config.get("run_type") or ""),
            "eval_started_at": eval_started_at,
            "case_source": source_config.get("case_source", ""),
            "scoring_mode": scoring_mode,
            "judge_blend_weight": blend_weight,
            "pass_threshold": pass_threshold,
            "baseline_config": baseline_config,
            "configs": [config.get("config_id") for config in configs],
            "case_count": len(cases),
            "reweighted": True,
        }
        config_text = json.dumps(updated_config, ensure_ascii=False, indent=2) + "\n"
        (run_dir / "config.json").write_text(config_text, encoding="utf-8")
        (run_dir / "config.yaml").write_text(config_text, encoding="utf-8")
        (run_dir / "run_metadata.json").write_text(
            json.dumps(run_metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        eval_write_jsonl(run_dir / "model_outputs.jsonl", outputs)
        eval_write_jsonl(run_dir / "judge_scores.jsonl", scores)
        eval_write_jsonl(run_dir / "regression_diff.jsonl", regression_diff)
        eval_write_jsonl(run_dir / "run_release_gates.jsonl", run_release_gates)
        eval_write_jsonl(run_dir / "qa_slice_scores.jsonl", slice_rows)
        eval_write_csv(run_dir / "model_outputs.csv", outputs)
        eval_write_csv(run_dir / "judge_scores.csv", scores)
        eval_write_csv(run_dir / "regression_diff.csv", regression_diff)
        eval_write_csv(run_dir / "run_release_gates.csv", run_release_gates)
        eval_write_csv(run_dir / "eval_runs.csv", summary)
        eval_write_csv(run_dir / "question_cases.csv", question_rows)
        eval_write_csv(run_dir / "qa_slice_scores.csv", slice_rows)
        by_model_dir = run_dir / "by_model"
        by_model_dir.mkdir(parents=True, exist_ok=True)
        score_by_key = {(row.get("case_id"), row.get("config_id")): row for row in scores}
        for config in configs:
            config_id = config.get("config_id")
            rows = []
            for output in outputs:
                if output.get("config_id") != config_id:
                    continue
                score = score_by_key.get((output.get("case_id"), config_id), {})
                rows.append({**output, **{f"score_{key}": value for key, value in score.items() if key not in output}})
            eval_write_jsonl(by_model_dir / f"{eval_safe_filename(str(config_id))}.jsonl", rows)
        eval_write_partitioned_eval_artifacts(run_dir, outputs, scores)
        eval_write_html_report(run_dir / "regression_report.html", summary, regression_diff, run_release_gates, run_metadata)
        eval_write_xlsx(
            run_dir / "regression_report.xlsx",
            {
                "run_metadata": [run_metadata],
                "summary": summary,
                "run_release_gates": run_release_gates,
                "model_outputs": outputs,
                "judge_scores": scores,
                "regression_diff": regression_diff,
                "qa_slice_scores": slice_rows,
            },
        )
        if export_final_ui:
            eval_export_final_ui(
                final_ui_data=ROOT / "data",
                run_id=run_id,
                summary=summary,
                question_rows=question_rows,
                slice_rows=slice_rows,
                run_release_gates=run_release_gates,
                configs=configs,
            )
        return {
            "run_id": run_id,
            "source_run_id": source_dir.name,
            "path": str(run_dir),
            "files": {
                "eval_runs": "/data/eval_runs.csv",
                "question_cases": "/data/question_cases.csv",
                "run_release_gates": "/data/run_release_gates.csv",
                "report_html": "/report/regression_report.html",
            },
            "summary": {
                "models": len(summary),
                "cases": len(question_rows),
                "scoring_mode": scoring_mode,
                "blend_weight": blend_weight,
                "export_final_ui": export_final_ui,
            },
        }

    def reblend_score_row(
        self,
        row: dict,
        *,
        run_id: str,
        scoring_mode: str,
        blend_weight: float,
        pass_threshold: float,
    ):
        score = dict(row)
        score["run_id"] = run_id
        deterministic = dict(score)
        for key in SCORE_METRIC_KEYS:
            value = score.get(f"static_{key}", score.get(key))
            if key == "hal_pass" and value in {"", None}:
                value = score.get("static_hal", score.get("hal"))
            deterministic[key] = self.judge_metric_points(value, score)
        deterministic["hal"] = deterministic.get("hal", deterministic.get("hal_pass"))
        deterministic["overall_score"] = self.judge_overall_points(
            score.get("static_overall_score", score.get("overall_score")),
            score,
        )
        deterministic["critical_fail"] = self.bool_value(
            score.get("static_critical_fail"),
            self.bool_value(score.get("critical_fail"), False),
        )
        deterministic["pass"] = deterministic["overall_score"] >= pass_threshold and not deterministic["critical_fail"]
        deterministic["error_type"] = eval_canonical_error_type(score.get("static_error_type") or score.get("error_type"))
        deterministic["reason"] = score.get("static_reason") or score.get("reason") or ""
        deterministic["applicable_metrics"] = score.get("static_applicable_metrics") or ",".join(SCORE_METRIC_KEYS)
        deterministic["score_denominator"] = eval_score_denominator(deterministic)
        deterministic["raw_metric_score"] = eval_raw_metric_score(deterministic)
        answer_quality_value = score.get("answer_quality_score")
        if answer_quality_value in {"", None}:
            answer_quality_value = deterministic["overall_score"]
        rag_quality_value = score.get("rag_quality_score")
        if rag_quality_value in {"", None}:
            rag_quality_value = deterministic["overall_score"]
        deterministic["answer_quality_score"] = self.judge_overall_points(answer_quality_value, score)
        deterministic["rag_quality_score"] = self.judge_overall_points(rag_quality_value, score)
        if scoring_mode == "static":
            deterministic["scoring_mode"] = "static"
            for key in SCORE_METRIC_KEYS:
                deterministic[f"static_{key}"] = deterministic[key]
            deterministic["static_overall_score"] = deterministic["overall_score"]
            deterministic["static_pass"] = deterministic["pass"]
            deterministic["static_critical_fail"] = deterministic["critical_fail"]
            deterministic["static_error_type"] = deterministic["error_type"]
            deterministic["static_reason"] = deterministic["reason"]
            return deterministic

        if not any(self.reblend_judge_metric_value(score, key) not in {"", None} for key in SCORE_METRIC_KEYS):
            raise ValueError("원본 실행에 LLM Judge 점수가 없습니다. 규칙 기반 채점을 사용하거나 LLM Judge 평가를 먼저 실행하세요.")
        judge_score = {
            key: self.judge_metric_points(self.reblend_judge_metric_value(score, key), score)
            for key in SCORE_METRIC_KEYS
        }
        judge_score["hal"] = judge_score.get("hal", judge_score.get("hal_pass"))
        judge_critical_fail = self.bool_value(score.get("llm_judge_critical_fail"), False)
        judge_score.update(
            {
                "critical_fail": judge_critical_fail,
                "error_type": eval_canonical_error_type(score.get("llm_judge_error_type")),
                "reason": score.get("llm_judge_reason") or score.get("reason") or "",
                "confidence": self.safe_float(score.get("llm_judge_confidence"), default=0.0, minimum=0.0, maximum=1.0),
                "judge_conflict": self.bool_value(score.get("llm_judge_conflict"), False),
                "judge_conflict_reason": score.get("llm_judge_conflict_reason") or "",
                "model": score.get("llm_judge_model", ""),
                "provider": score.get("llm_judge_provider", ""),
                "config_id": score.get("llm_judge_config_id", ""),
                "judge_count": self.safe_int(score.get("llm_judge_count"), default=1, minimum=1, maximum=100),
                "individual_scores": self.json_list_value(score.get("llm_judge_individual_scores")),
                "score_schema": score.get("score_schema") or "omnieval_metrics_config_v2",
                "applicable_metrics": score.get("llm_judge_applicable_metrics") or score.get("applicable_metrics") or ",".join(SCORE_METRIC_KEYS),
                "score_denominator": score.get("llm_judge_score_denominator", ""),
                "raw_metric_score": score.get("llm_judge_raw_metric_score", ""),
                "omnieval_accuracy": score.get("llm_judge_omnieval_accuracy", ""),
                "omnieval_completeness": score.get("llm_judge_omnieval_completeness", ""),
                "omnieval_numerical_accuracy": score.get("llm_judge_omnieval_numerical_accuracy", ""),
                "omnieval_hallucination": score.get("llm_judge_omnieval_hallucination", ""),
            }
        )
        judge_score["score_denominator"] = eval_score_denominator(judge_score)
        judge_score["raw_metric_score"] = eval_raw_metric_score(judge_score)
        judge_score["overall_score"] = eval_score_total_from_metrics(judge_score)
        judge_score["pass"] = judge_score["overall_score"] >= pass_threshold and not judge_score["critical_fail"]
        mode = {
            "static_llm": "audit",
            "llm_override": "override",
            "blend": "blend",
        }[scoring_mode]
        return eval_apply_llm_judge(
            deterministic,
            judge_score,
            judge_config={
                "config_id": judge_score.get("config_id", ""),
                "model": judge_score.get("model", ""),
                "provider": judge_score.get("provider", ""),
            },
            mode=mode,
            blend_weight=blend_weight,
            pass_threshold=pass_threshold,
            scoring_mode=scoring_mode,
        )

    def reblend_judge_metric_value(self, score: dict, key: str):
        value = score.get(f"llm_judge_{key}")
        if key == "hal_pass" and value in {"", None}:
            value = score.get("llm_judge_hal", score.get("hal_pass", score.get("hal")))
        if value in {"", None}:
            value = score.get(key)
        return value

    def bool_value(self, value, default: bool):
        parsed = optional_bool(value)
        return default if parsed is None else parsed

    def json_list_value(self, value):
        if isinstance(value, list):
            return value
        if not value:
            return []
        try:
            parsed = json.loads(str(value))
        except json.JSONDecodeError:
            return []
        return parsed if isinstance(parsed, list) else []

    def wait_for_eval_job(self, job_id: str, process: subprocess.Popen):
        returncode = process.wait()
        finished_job = None
        with EVAL_JOBS_LOCK:
            job = EVAL_JOBS.get(job_id)
            if not job:
                return
            job["returncode"] = returncode
            if returncode == 0:
                job["status"] = "finished"
            elif returncode == 130 or job.get("status") == "canceling" or self.read_job_control(job).get("action") == "cancel":
                job["status"] = "canceled"
            else:
                job["status"] = "failed"
            job["finished_at"] = datetime.now().isoformat(timespec="seconds")
            self.persist_eval_job(job)
            finished_job = job
        if finished_job and finished_job.get("status") == "finished":
            self.maybe_build_eval_snapshot(finished_job)

    def maybe_build_eval_snapshot(self, job: dict) -> bool:
        if job.get("status") != "finished":
            return False
        if not bool(job.get("export_final_ui")):
            return False
        if bool(job.get("dry_run")) or bool(job.get("skip_scoring")):
            return False
        if job.get("snapshot_status") in {"running", "finished", "failed"}:
            return False
        script_path = PROJECT_ROOT / "scripts" / "eval" / "apply_omnieval_metrics_v2.py"
        job["snapshot_status"] = "running"
        job["snapshot_started_at"] = datetime.now().isoformat(timespec="seconds")
        self.persist_eval_job(job)
        try:
            completed = subprocess.run(
                [str(job.get("python_executable") or sys.executable), str(script_path)],
                cwd=str(PROJECT_ROOT),
                text=True,
                capture_output=True,
                timeout=600,
            )
            combined_output = "\n".join(part for part in [completed.stdout, completed.stderr] if part)
            job["snapshot_returncode"] = completed.returncode
            job["snapshot_status"] = "finished" if completed.returncode == 0 else "failed"
            job["snapshot_output_tail"] = combined_output[-8000:]
        except Exception as exc:
            job["snapshot_returncode"] = -1
            job["snapshot_status"] = "failed"
            job["snapshot_output_tail"] = str(exc)
        job["snapshot_finished_at"] = datetime.now().isoformat(timespec="seconds")
        self.persist_eval_job(job)
        return True

    def persist_eval_job(self, job: dict):
        log_path = Path(str(job.get("log_path") or ""))
        if not log_path:
            return
        meta_path = log_path.with_suffix(".job.json")
        try:
            meta_path.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError:
            return

    def load_persisted_eval_jobs(self, job_id: str | None = None):
        log_dirs = self.eval_job_dirs()
        candidates = (
            [path for log_dir in log_dirs for path in [log_dir / f"{job_id}.job.json"]]
            if job_id
            else [path for log_dir in log_dirs for path in sorted(log_dir.glob("*.job.json"))]
        )
        loaded: dict[str, dict] = {}
        for path in candidates:
            if not path.exists():
                continue
            try:
                job = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(job, dict) and job.get("job_id"):
                if self.refresh_persisted_job_status(job):
                    self.persist_eval_job(job)
                loaded[str(job["job_id"])] = job

        if not job_id:
            for log_dir in log_dirs:
                for log_path in sorted(log_dir.glob("*.log")):
                    inferred_id = log_path.stem
                    if inferred_id in loaded:
                        continue
                    job = self.reconstruct_job_from_log(log_path)
                    if job:
                        loaded[inferred_id] = job

        with EVAL_JOBS_LOCK:
            for loaded_id, job in loaded.items():
                EVAL_JOBS[loaded_id] = job

    def eval_job_dirs(self) -> list[Path]:
        return [WEB_JOBS_ROOT]

    def refresh_persisted_job_status(self, job: dict):
        before = self.job_status_snapshot(job)
        if job.get("status") == "finished":
            return self.maybe_build_eval_snapshot(job)
        if job.get("status") not in {"running", "paused", "canceling", "unknown"}:
            return False
        pid = job.get("pid")
        if pid and self.process_is_running(pid):
            action = str(self.read_job_control(job).get("action") or "").strip().lower()
            if action == "pause":
                job["status"] = "paused"
            elif action == "cancel":
                job["status"] = "canceling"
            else:
                job["status"] = "running"
            return self.job_status_snapshot(job) != before
        found_pid = self.find_running_eval_process(str(job.get("job_id") or ""))
        if found_pid:
            job["pid"] = found_pid
            job["status"] = "running"
            return self.job_status_snapshot(job) != before
        log_text = self.read_tail(Path(str(job.get("log_path") or "")), max_chars=200000)
        if "EVAL_CANCELLED" in log_text or self.read_job_control(job).get("action") == "cancel":
            job["status"] = "canceled"
            job["returncode"] = job.get("returncode") if job.get("returncode") is not None else 130
        elif "Traceback (most recent call last):" in log_text or "ERROR" in log_text:
            job["status"] = "failed"
            job["returncode"] = job.get("returncode") if job.get("returncode") is not None else -1
        elif "Wrote evaluation run to " in log_text or "Wrote answer-only run to " in log_text or "DRY MODEL_END" in log_text:
            job["status"] = "finished"
            job["returncode"] = job.get("returncode") if job.get("returncode") is not None else 0
        else:
            job["status"] = "interrupted"
            job["returncode"] = job.get("returncode") if job.get("returncode") is not None else -1
        if not job.get("finished_at") and job.get("status") != "running":
            job["finished_at"] = datetime.now().isoformat(timespec="seconds")
        changed = self.job_status_snapshot(job) != before
        if job.get("status") == "finished":
            changed = self.maybe_build_eval_snapshot(job) or changed
        return changed

    def job_status_snapshot(self, job: dict):
        return {
            "status": job.get("status"),
            "returncode": job.get("returncode"),
            "pid": job.get("pid"),
            "finished_at": job.get("finished_at"),
            "snapshot_status": job.get("snapshot_status"),
        }

    def process_is_running(self, pid):
        try:
            os.kill(int(pid), 0)
            return True
        except (OSError, TypeError, ValueError):
            return False

    def find_running_eval_process(self, job_id: str):
        if not job_id or os.name != "nt":
            return None
        escaped = job_id.replace("'", "''")
        command = (
            "Get-CimInstance Win32_Process | "
            f"Where-Object {{ $_.Name -like 'python*' -and $_.CommandLine -like '*run_multi_model_eval.py*' -and $_.CommandLine -like '*{escaped}*' }} | "
            "Select-Object -First 1 -ExpandProperty ProcessId"
        )
        try:
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                text=True,
                capture_output=True,
                timeout=3,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        if not lines:
            return None
        try:
            return int(lines[0])
        except ValueError:
            return None

    def reconstruct_job_from_log(self, log_path: Path):
        log_text = self.read_tail(log_path, max_chars=240000)
        if not log_text:
            return None
        run_id = self.first_log_value(log_text, "run_id") or log_path.stem
        configs = [
            item.strip()
            for item in (self.first_log_value(log_text, "configs") or "").split(",")
            if item.strip()
        ]
        scoring_mode = self.first_log_value(log_text, "scoring_mode") or "static"
        judge_line = next((line for line in log_text.splitlines() if line.startswith("llm_judge=")), "")
        judge_config_ids = self.judge_config_ids_from_log_line(judge_line)
        pid = self.find_running_eval_process(log_path.stem)
        status = "running" if pid else (
            "finished"
            if "Wrote evaluation run to " in log_text or "Wrote answer-only run to " in log_text or "DRY MODEL_END" in log_text
            else "interrupted"
        )
        if "Traceback (most recent call last):" in log_text:
            status = "failed"
        control_path = log_path.with_suffix(".control.json")
        control = {}
        if control_path.exists():
            try:
                control = json.loads(control_path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                control = {}
        action = str(control.get("action") or "").strip().lower() if isinstance(control, dict) else ""
        if pid and action == "pause":
            status = "paused"
        elif pid and action == "cancel":
            status = "canceling"
        elif "EVAL_CANCELLED" in log_text:
            status = "canceled"
        summary_paths = sorted(log_path.parent.glob(f"{log_path.stem}_*_cases.summary.json"))
        summary = {}
        dataset = ""
        if summary_paths:
            try:
                summary = json.loads(summary_paths[0].read_text(encoding="utf-8"))
                dataset = str(summary.get("profile_id") or "")
            except (OSError, json.JSONDecodeError):
                summary = {}
        return {
            "job_id": log_path.stem,
            "status": status,
            "run_id": run_id,
            "runner_type": "multi_model_eval",
            "dataset": dataset,
            "run_profile": dataset,
            "cases_file": "",
            "composed_summary_path": self.display_path(summary_paths[0]) if summary_paths else "",
            "composed_summary": summary,
            "configs": configs,
            "suites": [],
            "limit": None,
            "scoring_mode": scoring_mode,
            "judge_config": ", ".join(judge_config_ids),
            "judge_config_ids": judge_config_ids,
            "judge_mode": "audit" if judge_line else "",
            "judge_blend_weight": "",
            "dry_run": "DRY MODEL_START" in log_text,
            "export_final_ui": False,
            "prediction_file": "",
            "template_output": "",
            "output_dir": "",
            "command": [],
            "log_path": str(log_path),
            "control_path": str(control_path),
            "started_at": datetime.fromtimestamp(log_path.stat().st_mtime).isoformat(timespec="seconds"),
            "finished_at": datetime.fromtimestamp(log_path.stat().st_mtime).isoformat(timespec="seconds") if status in {"finished", "failed", "interrupted", "canceled"} else "",
            "returncode": 0 if status == "finished" else (130 if status == "canceled" else (-1 if status in {"failed", "interrupted"} else None)),
            "pid": pid,
        }

    def first_log_value(self, log_text: str, key: str):
        prefix = f"{key}="
        for line in log_text.splitlines():
            if line.startswith(prefix):
                return line[len(prefix) :].strip()
        return ""

    def judge_config_ids_from_log_line(self, line: str):
        if not line or "=" not in line:
            return []
        text = line.split("=", 1)[1].split(" mode=", 1)[0].strip()
        return [item.strip() for item in text.split(",") if item.strip()]

    def job_for_response(self, job: dict, include_log: bool):
        if self.refresh_persisted_job_status(job):
            self.persist_eval_job(job)
        response = {
            key: value
            for key, value in job.items()
            if key not in {"command"}
        }
        response["command"] = " ".join(str(part) for part in job.get("command", []))
        log_path = Path(str(job.get("log_path") or ""))
        log_text = self.read_tail(log_path, max_chars=240000)
        response["progress"] = self.eval_job_progress(job, log_text)
        if include_log:
            response["log_tail"] = log_text[-40000:]
        return response

    def read_tail(self, path: Path, max_chars: int = 12000):
        if not path.exists():
            return ""
        text = path.read_text(encoding="utf-8", errors="replace")
        return text[-max_chars:]

    def eval_job_progress(self, job: dict, log_text: str):
        configs = list(job.get("configs") or [])
        total_models = max(len(configs), 1)
        total_cases = self.progress_total_cases(job, log_text)
        total_answers = total_models * total_cases
        dry_run = bool(job.get("dry_run"))
        has_judge = bool(job.get("judge_config")) and not dry_run

        answer_done_by_model = {config_id: 0 for config_id in configs}
        answer_started_by_model = {config_id: 0 for config_id in configs}
        judge_done_by_model = {config_id: 0 for config_id in configs}
        judge_started_by_model = {config_id: 0 for config_id in configs}
        checkpoint_answers, checkpoint_judges = self.progress_checkpoint_counts(job, configs)
        if job.get("status") in {"running", "paused", "canceling"} and self.score_recompute_pending(log_text):
            checkpoint_judges = {config_id: 0 for config_id in configs}
        answer_done_by_model.update(checkpoint_answers)
        judge_done_by_model.update(checkpoint_judges)
        model_done = 0
        current_model = ""
        current_case_id = ""
        control_state = ""

        for line in log_text.splitlines():
            paused = re.search(r"^EVAL_PAUSED\s+run_id=\S+\s+config=(?P<config>\S+)\s+case=(?P<case>\S+)", line)
            if paused:
                control_state = "paused"
                current_model = "" if paused.group("config") == "-" else paused.group("config")
                current_case_id = "" if paused.group("case") == "-" else paused.group("case")
                continue
            if line.startswith("EVAL_RESUMED"):
                control_state = "running"
                continue
            if line.startswith("EVAL_CANCELLED"):
                control_state = "canceled"
                continue
            start = re.search(r"^(?:DRY\s+)?MODEL_START\s+(\d+)/(\d+)\s+(\S+)", line)
            if start:
                current_model = start.group(3)
                continue
            end = re.search(r"^(?:DRY\s+)?MODEL_END\s+(\d+)/(\d+)\s+(\S+)", line)
            if end:
                model_done = max(model_done, int(end.group(1)))
                if current_model == end.group(3):
                    current_model = ""
                continue
            case_start = re.search(r"^\[(?P<config>[^\]]+)\]\s+(?P<index>\d+)/(?P<total>\d+)\s+(?P<case>\S+)", line)
            if case_start:
                config_id = case_start.group("config")
                answer_started_by_model[config_id] = max(
                    answer_started_by_model.get(config_id, 0),
                    int(case_start.group("index")),
                )
                current_model = config_id
                current_case_id = case_start.group("case")
                continue
            answer_done = re.search(r"^ANSWER_DONE\s+\[(?P<config>[^\]]+)\]\s+(?P<index>\d+)/(?P<total>\d+)\s+(?P<case>\S+)", line)
            if answer_done:
                config_id = answer_done.group("config")
                answer_done_by_model[config_id] = max(
                    answer_done_by_model.get(config_id, 0),
                    int(answer_done.group("index")),
                )
                current_model = config_id
                current_case_id = answer_done.group("case")
                continue
            judge_start = re.search(r"^JUDGE_START\s+\[(?P<config>[^\]]+)\]\s+(?P<index>\d+)/(?P<total>\d+)\s+(?P<case>\S+)", line)
            if judge_start:
                config_id = judge_start.group("config")
                judge_started_by_model[config_id] = max(
                    judge_started_by_model.get(config_id, 0),
                    int(judge_start.group("index")),
                )
                current_model = config_id
                current_case_id = judge_start.group("case")
                continue
            judge_done = re.search(r"^JUDGE_DONE\s+\[(?P<config>[^\]]+)\]\s+(?P<index>\d+)/(?P<total>\d+)\s+(?P<case>\S+)", line)
            if judge_done:
                config_id = judge_done.group("config")
                judge_done_by_model[config_id] = max(
                    judge_done_by_model.get(config_id, 0),
                    int(judge_done.group("index")),
                )
                current_model = config_id
                current_case_id = judge_done.group("case")

        if dry_run and job.get("status") in {"finished", "failed"}:
            answer_done_by_model = {config_id: total_cases for config_id in configs}
            model_done = total_models if job.get("status") == "finished" else model_done
        elif not any(answer_done_by_model.values()):
            answer_done_by_model = dict(answer_started_by_model)

        answers_done = sum(min(total_cases, count) for count in answer_done_by_model.values())
        answer_started = sum(min(total_cases, count) for count in answer_started_by_model.values())
        judge_total = total_answers if has_judge else 0
        judge_done = sum(min(total_cases, count) for count in judge_done_by_model.values())
        judge_started = sum(min(total_cases, count) for count in judge_started_by_model.values())
        overall_units = total_answers + judge_total
        completed_units = answers_done + judge_done
        percent = round((completed_units / overall_units) * 100, 1) if overall_units else 0.0
        if job.get("status") == "finished":
            percent = 100.0

        return {
            "percent": percent,
            "status": job.get("status", ""),
            "control_state": control_state,
            "dry_run": dry_run,
            "current_model": current_model,
            "current_case_id": current_case_id,
            "models": {
                "done": model_done,
                "total": total_models,
            },
            "answers": {
                "started": answer_started,
                "done": answers_done,
                "total": total_answers,
                "by_model": answer_done_by_model,
            },
            "judge": {
                "enabled": has_judge,
                "started": judge_started,
                "done": judge_done,
                "total": judge_total,
                "by_model": judge_done_by_model,
            },
        }

    def score_recompute_pending(self, log_text: str) -> bool:
        for match in re.finditer(r"\bscore_recompute=(\d+)", log_text):
            if int(match.group(1)) > 0:
                return True
        return False

    def progress_total_cases(self, job: dict, log_text: str) -> int:
        for line in log_text.splitlines():
            match = re.search(r"^cases=(\d+)", line)
            if match:
                return max(1, int(match.group(1)))
        if job.get("limit"):
            return max(1, int(job.get("limit")))
        summary = job.get("composed_summary") if isinstance(job.get("composed_summary"), dict) else {}
        for key in ("case_count", "total"):
            if summary.get(key):
                return max(1, int(summary[key]))
        return 1

    def progress_checkpoint_counts(self, job: dict, configs: list[str]):
        run_id = str(job.get("run_id") or "")
        answer_counts = {config_id: 0 for config_id in configs}
        judge_counts = {config_id: 0 for config_id in configs}
        if not run_id:
            return answer_counts, judge_counts
        run_dir = EVAL_RUNS_ROOT / run_id
        for path, target in (
            (run_dir / "model_outputs.jsonl", answer_counts),
            (run_dir / "judge_scores.jsonl", judge_counts),
        ):
            if not path.exists():
                continue
            seen: set[tuple[str, str]] = set()
            with path.open(encoding="utf-8", errors="replace") as file:
                for line in file:
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(row, dict):
                        continue
                    config_id = str(row.get("config_id") or "")
                    case_id = str(row.get("case_id") or "")
                    key = (config_id, case_id)
                    if config_id in target and case_id and key not in seen:
                        seen.add(key)
                        target[config_id] += 1
        return answer_counts, judge_counts

    def discover_question_csv_datasets(self):
        datasets = {}
        upload_root = USER_UPLOAD_CSV_ROOT.resolve()
        for directory in QUESTIONLIST_CSV_DIRS:
            if not directory.exists():
                continue
            role = self.normalize_question_dataset_role(directory.name)
            try:
                directory.resolve().relative_to(upload_root)
                is_user_upload = True
            except ValueError:
                is_user_upload = False
            for path in sorted(directory.glob("*.csv")):
                if not is_user_upload and self.path_has_excluded_dataset_marker(path):
                    continue
                dataset_id = f"user__{role}__{path.stem}" if is_user_upload else f"{directory.name}__{path.stem}"
                datasets[dataset_id] = {
                    "id": dataset_id,
                    "name": path.stem,
                    "path": path,
                    "role": role,
                    "format": "csv",
                    "directory": self.display_path(directory),
                    "user_uploaded": is_user_upload,
                    "version": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y%m%d_%H%M%S"),
                }
        return datasets

    def resolve_question_dataset(self, dataset_id: str):
        path = QUESTIONLIST_DATASET_FILES.get(dataset_id)
        filters = None
        role = ""
        discovered_csv = self.discover_question_csv_datasets().get(dataset_id)
        if discovered_csv:
            path = discovered_csv["path"]
            role = discovered_csv["role"]
        if not path:
            pool = self.catalog_pool(dataset_id)
            if pool:
                try:
                    path = self.resolve_project_path(str(pool.get("path") or ""))
                except ValueError:
                    path = None
                filters = pool.get("filters")
                role = str(pool.get("role") or "")
        return path, filters, role

    def primary_question_source_dataset(self):
        datasets = self.discover_question_csv_datasets()
        if not datasets:
            return None
        preferred = [
            dataset
            for dataset in datasets.values()
            if dataset["path"].name == "evaluation_dataset_final.csv"
        ]
        return (preferred or list(datasets.values()))[0]

    def iter_case_rows(self, path: Path, *, dataset_id: str = "", role: str = ""):
        if path.suffix.lower() == ".csv":
            yield from self.iter_question_csv(path, dataset_id=dataset_id, role=role)
            return
        yield from self.iter_jsonl(path)

    def iter_question_csv(self, path: Path, *, dataset_id: str, role: str):
        with path.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for index, row in enumerate(reader, 1):
                question = csv_row_value(row, *CSV_QUESTION_FIELD_ALIASES)
                output = csv_row_value(row, *CSV_ANSWER_FIELD_ALIASES)
                if not question and not output:
                    continue
                qa_category = canonical_qa_category(
                    csv_row_value(row, *CSV_QA_CATEGORY_FIELD_ALIASES),
                    role,
                )
                question_type = canonical_question_type(
                    csv_row_value(row, *CSV_QUESTION_TYPE_FIELD_ALIASES),
                )
                qa_topic = canonical_qa_topic(
                    qa_category,
                    csv_row_value(row, *CSV_QA_TOPIC_FIELD_ALIASES),
                )
                suite = csv_row_value(row, "suite", "split_type", "regression_suite") or role or "question_source_csv"
                regression_suite = csv_row_value(row, "regression_suite", "split_type", "suite")
                stable_case_id = csv_row_value(row, *CSV_CASE_ID_FIELD_ALIASES)
                ordinal_case_id = csv_row_value(row, *CSV_ORDINAL_FIELD_ALIASES)
                case_id = stable_case_id or (f"{dataset_id}-{ordinal_case_id}" if ordinal_case_id else f"{dataset_id}-{index:05d}")
                is_regression = (role or "").lower() == "regression"
                trap = csv_row_value(row, *CSV_FORBIDDEN_FIELD_ALIASES)
                yield {
                    "case_id": case_id,
                    "question_id": case_id,
                    "suite": suite,
                    "severity": "",
                    "priority": "",
                    "question": question,
                    "instruction": question,
                    "output": output,
                    "gold_answer": output,
                    "intent": qa_topic,
                    "task_type": "qa",
                    "qa_category": qa_category,
                    "source_type": qa_category,
                    "question_type": question_type,
                    "qa_topic": qa_topic,
                    "qa_matrix_topic": qa_topic,
                    "expected_behavior": "answer_from_source",
                    "selection_mode": "question_source_csv",
                    "dataset_pool_id": dataset_id,
                    "dataset_role": role or "benchmark",
                    "required_conditions": [output] if output else [],
                    "forbidden_claims": [trap] if trap else [],
                    "gate_eligible": is_regression,
                    "release_gate_eligible": is_regression,
                    "case_status": "active" if is_regression else "shadow",
                    "gold_verified": is_regression,
                    "human_review_required": False,
                    "case_source": self.display_path(path),
                    "dataset_version": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y%m%d_%H%M%S"),
                    "metadata": {
                        "qa_category": qa_category,
                        "qa_topic": qa_topic,
                        "qa_matrix_topic": qa_topic,
                        "question_type": question_type,
                        "source_type": qa_category,
                        "source_title": path.stem,
                        "case_source": self.display_path(path),
                        "expected_behavior": "answer_from_source",
                        "selection_mode": "question_source_csv",
                        "dataset_pool_id": dataset_id,
                        "dataset_role": role or "benchmark",
                        **({"regression_suite": regression_suite} if is_regression and regression_suite else {}),
                    },
                }

    def summarize_case_file(self, path: Path, filters=None, dataset_id: str = "", role: str = ""):
        summary = {
            "total": 0,
            "suite": {},
            "severity": {},
            "source_type": {},
            "question_type": {},
            "qa_topic": {},
            "expected_behavior": {},
            "task_type": {},
            "case_status": {},
            "has_expected_tool_calls": 0,
            "has_expected_final_answer": 0,
            "has_format_requirements": 0,
            "active_gold_cases": 0,
            "release_gate_eligible_cases": 0,
            "gold_verified_cases": 0,
            "human_review_required_cases": 0,
        }
        if not path.exists():
            return summary

        try:
            filter_key = json.dumps(filters or {}, ensure_ascii=False, sort_keys=True)
        except TypeError:
            filter_key = str(filters)
        stat = path.stat()
        cache_key = (str(path.resolve()), filter_key, str(dataset_id or ""), str(role or ""), stat.st_mtime_ns, stat.st_size)
        with CASE_SUMMARY_CACHE_LOCK:
            cached = CASE_SUMMARY_CACHE.get(cache_key)
        if cached is not None:
            return json.loads(json.dumps(cached, ensure_ascii=False))

        for row in self.iter_case_rows(path, dataset_id=dataset_id, role=role):
            if not self.case_matches_filters(row, filters):
                continue
            summary["total"] += 1
            metadata = case_metadata(row)
            expected_final = row.get("expected_final_answer") if isinstance(row.get("expected_final_answer"), dict) else {}
            format_requirements = case_format_requirements(row)
            self.bump(summary["suite"], row.get("suite") or row.get("category"))
            self.bump(summary["severity"], row.get("severity") or row.get("difficulty"))
            self.bump(summary["task_type"], infer_task_type(row))
            status = dataset_case_status(row)
            self.bump(summary["case_status"], status)
            self.bump(summary["source_type"], row.get("source_type") or metadata.get("source_type"))
            self.bump(summary["question_type"], row.get("question_type") or metadata.get("question_type"))
            self.bump(summary["qa_topic"], row.get("qa_topic") or metadata.get("qa_topic") or metadata.get("qa_matrix_topic"))
            self.bump(summary["expected_behavior"], infer_expected_behavior(row))
            gold_verified = dataset_gold_verified(row)
            release_gate_eligible = dataset_release_gate_eligible(row)
            if status == "active" and gold_verified:
                summary["active_gold_cases"] += 1
            if release_gate_eligible:
                summary["release_gate_eligible_cases"] += 1
            if gold_verified:
                summary["gold_verified_cases"] += 1
            if dataset_human_review_required(row):
                summary["human_review_required_cases"] += 1
            if case_expected_tool_calls(row):
                summary["has_expected_tool_calls"] += 1
            if expected_final:
                summary["has_expected_final_answer"] += 1
            if format_requirements:
                summary["has_format_requirements"] += 1

        for field in ("suite", "severity", "source_type", "question_type", "qa_topic", "expected_behavior", "task_type", "case_status"):
            summary[field] = dict(sorted(summary[field].items(), key=lambda item: item[1], reverse=True)[:20])
        with CASE_SUMMARY_CACHE_LOCK:
            CASE_SUMMARY_CACHE[cache_key] = json.loads(json.dumps(summary, ensure_ascii=False))
        return summary

    def normalize_dataset_case(self, row: dict, dataset_id: str):
        metadata = case_metadata(row)
        first_evidence = first_evidence_for_case(row)
        expected_final = row.get("expected_final_answer") if isinstance(row.get("expected_final_answer"), dict) else {}
        format_requirements = case_format_requirements(row)
        expected_tool_calls = case_expected_tool_calls(row)
        tool_outputs = row.get("tool_outputs") if isinstance(row.get("tool_outputs"), list) else []
        expected_observation = row.get("expected_observation") if isinstance(row.get("expected_observation"), dict) else {}
        observations = row.get("observations") if isinstance(row.get("observations"), list) else []
        behavior = infer_expected_behavior(row)
        qa_category = canonical_qa_category(
            row.get("qa_category"),
            metadata.get("qa_category"),
            row.get("source_type"),
            metadata.get("source_type"),
            row.get("suite"),
        )
        question_type = canonical_question_type(row.get("question_type"), metadata.get("question_type"))
        qa_topic = canonical_qa_topic(
            qa_category,
            row.get("qa_topic"),
            metadata.get("qa_topic"),
            metadata.get("qa_matrix_topic"),
            row.get("intent"),
            metadata.get("topic"),
            metadata.get("benchmark_group"),
            row.get("suite"),
        )
        return {
            "dataset": dataset_id,
            "case_id": row.get("case_id") or row.get("scenario_id") or row.get("id"),
            "suite": row.get("suite") or row.get("category"),
            "severity": row.get("severity") or row.get("difficulty"),
            "priority": row.get("priority"),
            "question": row.get("instruction") or row.get("question"),
            "instruction": row.get("instruction") or row.get("question"),
            "output": row.get("output") or row.get("gold_answer"),
            "intent": row.get("qa_topic") or row.get("intent") or row.get("category") or metadata.get("question_type") or behavior,
            "task_type": infer_task_type(row),
            "qa_category": qa_category,
            "qa_topic": qa_topic,
            "source_type": qa_category,
            "question_type": question_type,
            "expected_behavior": behavior,
            "selection_mode": row.get("selection_mode") or metadata.get("selection_mode"),
            "dataset_pool_id": row.get("dataset_pool_id") or metadata.get("dataset_pool_id"),
            "dataset_role": row.get("dataset_role") or metadata.get("dataset_role"),
            "gate_eligible": row.get("gate_eligible") if "gate_eligible" in row else metadata.get("gate_eligible"),
            "release_gate_eligible": dataset_release_gate_eligible(row),
            "case_status": dataset_case_status(row),
            "gold_verified": dataset_gold_verified(row),
            "human_review_required": dataset_human_review_required(row),
            "case_source": row.get("case_source") or metadata.get("case_source"),
            "dataset_version": row.get("dataset_version") or metadata.get("dataset_version"),
            "qa_matrix_topic": qa_topic,
            "benchmark_group": metadata.get("benchmark_group"),
            "source_title": row.get("source_title") or metadata.get("source_title") or first_evidence.get("title"),
            "source_url": row.get("source_url") or metadata.get("source_url") or first_evidence.get("url"),
            "ground_truth_doc": row.get("expected_source_doc_id")
            or metadata.get("expected_source_doc_id")
            or first_evidence.get("source_id")
            or first_evidence.get("document_id")
            or row.get("gold_evidence_doc_id"),
            "gold_excerpt": row.get("output") or first_evidence.get("excerpt") or row.get("gold_answer"),
            "must_include": row.get("must_include") or expected_final.get("must_include") or row.get("required_conditions"),
            "must_not_include": row.get("must_not_include") or expected_final.get("must_not_include"),
            "required_claims": row.get("required_claims"),
            "forbidden_claims": row.get("forbidden_claims"),
            "format_requirements": format_requirements,
            "expected_tool_calls": expected_tool_calls,
            "forbidden_tool_calls": row.get("forbidden_tool_calls") if isinstance(row.get("forbidden_tool_calls"), list) else [],
            "expected_observation": expected_observation or {"observations": observations} if observations else expected_observation,
            "tool_outputs": tool_outputs or observations,
            "expected_final_answer": expected_final,
        }

    def iter_jsonl(self, path: Path):
        with path.open(encoding="utf-8-sig") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    yield row

    def bump(self, counts: dict, value):
        key = str(value or "unknown").strip() or "unknown"
        counts[key] = counts.get(key, 0) + 1

    def load_eval_dataset_catalog_file(self):
        if not EVAL_DATASET_CATALOG_PATH.exists():
            return {"default_seed": 42, "pools": {}, "profiles": {}}
        try:
            return load_eval_catalog_config(EVAL_DATASET_CATALOG_PATH)
        except (RuntimeError, ValueError, json.JSONDecodeError):
            return {"default_seed": 42, "pools": {}, "profiles": {}}

    def load_eval_dataset_catalog(self):
        return self.augment_eval_dataset_catalog(self.load_eval_dataset_catalog_file())

    def augment_eval_dataset_catalog(self, catalog: dict):
        return build_runtime_eval_dataset_catalog(
            catalog if isinstance(catalog, dict) else {},
            settings_path=QUESTION_DATASET_SETTINGS_PATH,
        )

    def question_dataset_pool_specs(self, catalog: dict):
        return runtime_question_dataset_pool_specs(catalog if isinstance(catalog, dict) else {})

    def question_dataset_pool_quota(self, pool: dict):
        return runtime_question_dataset_pool_quota(pool if isinstance(pool, dict) else {})

    def question_dataset_defaults(self, pools: dict | None = None):
        pool_specs = pools if isinstance(pools, dict) else self.question_dataset_pool_specs(self.load_eval_dataset_catalog_file())
        return runtime_question_dataset_defaults(pool_specs, settings_path=QUESTION_DATASET_SETTINGS_PATH)

    def dataset_id_matches_role(self, dataset_id: str, role: str, pools: dict):
        return runtime_dataset_id_matches_role(dataset_id, role, pools if isinstance(pools, dict) else {})

    def load_question_dataset_settings(self):
        return runtime_load_question_dataset_settings(QUESTION_DATASET_SETTINGS_PATH)

    def write_question_dataset_settings(self, settings: dict):
        runtime_write_question_dataset_settings(settings, QUESTION_DATASET_SETTINGS_PATH)

    def catalog_pool(self, pool_id: str):
        pools = self.load_eval_dataset_catalog().get("pools")
        if isinstance(pools, dict) and isinstance(pools.get(pool_id), dict):
            return pools[pool_id]
        return None

    def catalog_item_visible(self, item: dict):
        value = optional_bool(item.get("ui_visible"))
        return True if value is None else value

    def catalog_dataset_visible(self, item: dict, path: Path):
        if not isinstance(item, dict) or not self.catalog_item_visible(item):
            return False
        return path.exists() and not self.path_has_excluded_dataset_marker(path)

    def path_has_excluded_dataset_marker(self, path: Path):
        normalized_parts = [str(part).lower() for part in path.parts]
        if any(
            marker in part
            for part in normalized_parts
            for marker in EXCLUDED_DATASET_PATH_MARKERS
        ):
            return True
        tokens = []
        for part in normalized_parts:
            tokens.extend(token for token in re.split(r"[^a-z0-9]+", part) if token)
        return any(token in EXCLUDED_DATASET_NAME_TOKENS for token in tokens)

    def case_value(self, row: dict, key: str):
        current = row
        for part in str(key).split("."):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                current = None
                break
        if current is not None and current != "":
            return current
        metadata = case_metadata(row)
        return metadata.get(key)

    def case_values(self, row: dict, key: str):
        value = self.case_value(row, key)
        if value is None or value == "":
            return set()
        if isinstance(value, list):
            return {str(item) for item in value}
        return {str(value)}

    def case_matches_filters(self, row: dict, filters):
        if not isinstance(filters, dict) or not filters:
            return True
        include = filters.get("include") if isinstance(filters.get("include"), dict) else filters
        exclude = filters.get("exclude") if isinstance(filters.get("exclude"), dict) else {}
        for key, accepted in include.items():
            if key == "exclude":
                continue
            accepted_values = {str(item) for item in (accepted if isinstance(accepted, list) else [accepted])}
            if self.case_values(row, key).isdisjoint(accepted_values):
                return False
        for key, rejected in exclude.items():
            rejected_values = {str(item) for item in (rejected if isinstance(rejected, list) else [rejected])}
            if not self.case_values(row, key).isdisjoint(rejected_values):
                return False
        return True

    def pool_overrides_from_payload(self, value):
        if not isinstance(value, dict):
            return {}
        overrides = {}
        for pool_id, quota in value.items():
            try:
                number = int(quota)
            except (TypeError, ValueError):
                raise ValueError(f"pool quota must be an integer: {pool_id}={quota}")
            if number < 0:
                raise ValueError(f"pool quota must be zero or greater: {pool_id}={quota}")
            if number > 0:
                overrides[str(pool_id)] = number
        return overrides

    def prepare_judge_config(
        self,
        *,
        registry: dict,
        judge_payload: dict,
        scoring_mode: str,
        job_id: str,
        log_dir: Path,
        dry_run: bool,
        subprocess_env: dict,
    ):
        selected_config_ids = self.judge_config_ids_from_payload(judge_payload)
        raw_api_key = str(judge_payload.get("api_key") or "").strip()
        provider = str(judge_payload.get("provider") or "").strip()
        if provider == "registered":
            provider = ""
        temp_configs = []
        result_config_ids = []
        option_overrides = self.judge_option_overrides(judge_payload)

        if selected_config_ids:
            missing = [config_id for config_id in selected_config_ids if config_id not in registry]
            if missing:
                return {"error": f"unknown judge config: {', '.join(missing)}"}
            for index, selected_config_id in enumerate(selected_config_ids, 1):
                base_config = dict(registry[selected_config_id])
                if raw_api_key or option_overrides:
                    temp_config = dict(base_config)
                    suffix = "" if len(selected_config_ids) == 1 else f"_{index}"
                    temp_config["config_id"] = f"web_judge_{job_id}{suffix}"
                    temp_options = dict(base_config.get("options") or {})
                    temp_options.update(option_overrides)
                    temp_config["options"] = temp_options
                    if raw_api_key:
                        temp_config["api_key_env"] = f"WEB_EVAL_JUDGE_API_KEY_{job_id.upper()}{suffix.upper()}"
                        subprocess_env[temp_config["api_key_env"]] = raw_api_key
                    else:
                        token, api_key_env = self.provider_api_key_value(base_config)
                        if api_key_env and api_key_env != str(base_config.get("api_key_env") or "").strip():
                            temp_config["api_key_env"] = api_key_env
                        if token and api_key_env:
                            subprocess_env[api_key_env] = token
                        if base_config.get("provider") != "ollama" and api_key_env and not dry_run and not subprocess_env.get(api_key_env):
                            return {"error": f"API key is required for judge config {selected_config_id}."}
                    temp_configs.append(temp_config)
                    result_config_ids.append(temp_config["config_id"])
                else:
                    token, api_key_env = self.provider_api_key_value(base_config)
                    if token and api_key_env:
                        subprocess_env[api_key_env] = token
                    if base_config.get("provider") != "ollama" and api_key_env and not dry_run and not subprocess_env.get(api_key_env):
                        return {"error": f"API key is required for judge config {selected_config_id}."}
                    result_config_ids.append(selected_config_id)
            if not temp_configs:
                return {
                    "judge_config_id": ", ".join(result_config_ids),
                    "judge_config_ids": result_config_ids,
                    "runner_config_path": "",
                }
        else:
            if provider not in {"ollama", "openai_native", "openai_compatible", "generic_api", "clova_studio", "anthropic", "gemini"}:
                return {"error": "Choose a judge provider or an existing judge config."}
            model = str(judge_payload.get("model") or "").strip()
            if not model:
                return {"error": "Judge model is required."}
            api_key_env = ""
            if provider != "ollama":
                if raw_api_key:
                    api_key_env = f"WEB_EVAL_JUDGE_API_KEY_{job_id.upper()}"
                    subprocess_env[api_key_env] = raw_api_key
                else:
                    token, detected_api_key_env = self.provider_api_key_value({"provider": provider})
                    api_key_env = detected_api_key_env
                    if token and api_key_env:
                        subprocess_env[api_key_env] = token
                    if not subprocess_env.get(api_key_env):
                        return {"error": f"API key is required for {provider} judge runs."}
            base_url = str(judge_payload.get("base_url") or "").strip()
            if not base_url:
                base_url, _ = provider_env_value({"provider": provider}, "base_url")
            if not base_url:
                base_url = self.default_judge_base_url(provider)
            judge_options = self.default_judge_options(provider)
            judge_options.update(option_overrides)
            temp_config = {
                "config_id": f"web_judge_{job_id}",
                "display_name": str(judge_payload.get("display_name") or f"{provider} judge"),
                "provider": provider,
                "model": model,
                "base_url": base_url,
                "chat_url": str(judge_payload.get("chat_url") or "").strip(),
                "api_key_env": api_key_env,
                "prompt_version": str(judge_payload.get("prompt_version") or "omnieval_metrics_config_v2").strip(),
                "system_prompt_preset": str(judge_payload.get("system_prompt_preset") or "judge_default_v1").strip(),
                "system_prompt": str(judge_payload.get("system_prompt") or "").strip(),
                "rag_config": "none",
                "safety_policy": "llm_judge_prompt_preset",
                "evaluation_role": "llm_judge",
                "judge_role": "judge",
                "eval_target": False,
                "options": judge_options,
            }
            temp_configs.append(temp_config)
            result_config_ids.append(temp_config["config_id"])

        temp_config_ids = {config["config_id"] for config in temp_configs}
        configs = [self.eval_runner_model_config(spec) for spec in registry.values()]
        configs = [config for config in configs if config.get("config_id") not in temp_config_ids]
        configs.extend(self.eval_runner_model_config(config) for config in temp_configs)
        runner_config_path = log_dir / f"{job_id}_runner_model_configs.json"
        runner_config_path.write_text(
            json.dumps({"configs": configs}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return {
            "judge_config_id": ", ".join(result_config_ids),
            "judge_config_ids": result_config_ids,
            "runner_config_path": str(runner_config_path),
        }

    def eval_runner_model_config(self, config: dict) -> dict:
        runner_config = dict(config)
        chat_url = self.external_http_url(runner_config.get("chat_url"))
        upstream_chat_url = self.external_http_url(runner_config.get("upstream_chat_url"))
        if upstream_chat_url and not chat_url:
            runner_config["chat_url"] = upstream_chat_url

        for key in ("api_url", "health_url", "chat_url", "upstream_chat_url", "upstream_health_url", "responses_url", "response_url"):
            value = str(runner_config.get(key) or "").strip()
            if value and not self.external_http_url(value):
                runner_config.pop(key, None)

        for key in ("registry_source", "deletable"):
            runner_config.pop(key, None)
        return runner_config

    def write_runner_model_configs(self, *, registry: dict, job_id: str, log_dir: Path) -> str:
        runner_config_path = log_dir / f"{job_id}_runner_model_configs.json"
        runner_config_path.write_text(
            json.dumps(
                {"configs": [self.eval_runner_model_config(config) for config in registry.values()]},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return str(runner_config_path)

    def default_judge_options(self, provider: str):
        if provider == "openai_native":
            return {"max_output_tokens": 1024, "reasoning_effort": "low", "store": False}
        if provider == "anthropic":
            return {"temperature": 0, "top_p": 0.1, "max_tokens": 1024}
        if provider == "gemini":
            return {"temperature": 0, "top_p": 0.1, "max_output_tokens": 1024}
        if provider == "clova_studio":
            return {"temperature": 0, "top_p": 0.1, "max_completion_tokens": 1024, "include_ai_filters": False}
        return {"temperature": 0, "top_p": 0.1, "num_predict": 1024}

    def judge_option_overrides(self, judge_payload: dict):
        options = {}
        if self.has_payload_value(judge_payload, "temperature"):
            options["temperature"] = self.safe_float(judge_payload.get("temperature"), default=0.0, minimum=0.0, maximum=2.0)
        if self.has_payload_value(judge_payload, "top_p"):
            options["top_p"] = self.safe_float(judge_payload.get("top_p"), default=0.1, minimum=0.0, maximum=1.0)
        return options

    def has_payload_value(self, payload: dict, key: str):
        return key in payload and payload.get(key) is not None and str(payload.get(key)).strip() != ""

    def default_judge_base_url(self, provider: str):
        return {
            "openai_native": "https://api.openai.com",
            "openai_compatible": "https://api.openai.com",
            "clova_studio": "https://clovastudio.stream.ntruss.com",
            "anthropic": "https://api.anthropic.com",
            "gemini": "https://generativelanguage.googleapis.com",
        }.get(provider, "")

    def safe_int(self, value, default: int, minimum: int, maximum: int):
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = default
        return max(minimum, min(number, maximum))

    def optional_limit(self, value, default: int | None):
        if value is None or value == "":
            return default
        text = str(value).strip()
        if not text:
            return default
        return self.safe_int(text, default=default or 10, minimum=1, maximum=100000)

    def safe_float(self, value, default: float, minimum: float, maximum: float):
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = default
        return max(minimum, min(number, maximum))

    def safe_run_id(self, value):
        text = str(value or "").strip()
        safe = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in text)
        safe = "_".join(part for part in safe.split("_") if part)
        return safe[:120] or f"WEB_EVAL_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def display_path(self, path: Path):
        try:
            return str(path.relative_to(PROJECT_ROOT))
        except ValueError:
            return str(path)

    def resolve_project_path(self, value: str) -> Path:
        raw = str(value or "").strip()
        if not raw:
            raise ValueError("path is required")
        path = Path(raw)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        resolved = path.resolve(strict=False)
        project_root = PROJECT_ROOT.resolve(strict=False)
        try:
            resolved.relative_to(project_root)
        except ValueError as exc:
            raise ValueError(f"path must stay under project root: {self.display_path(path)}") from exc
        return resolved

    def summarize_questionlist_source(self, path: Path):
        if not path.exists():
            return {"total": 0, "source_type": {}, "question_type": {}, "severity": {}, "expected_behavior": {}}
        summary = {"total": 0, "source_type": {}, "question_type": {}, "severity": {}, "expected_behavior": {}}
        with path.open(encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                summary["total"] += 1
                for field in ("source_type", "question_type", "severity", "expected_behavior"):
                    value = str((row.get("severity") or row.get("difficulty")) if field == "severity" else (row.get(field) or ""))
                    summary[field][value] = summary[field].get(value, 0) + 1
        for field in ("source_type", "question_type", "severity", "expected_behavior"):
            summary[field] = dict(sorted(summary[field].items(), key=lambda item: item[1], reverse=True))
        return summary

    def send_json(self, payload, status=200, headers: dict[str, str] | None = None):
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_cors_headers()
        self.end_headers()
        self.write_response_body(body)

    def send_text(self, payload: str, content_type: str, status=200):
        body = payload.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_cors_headers()
        self.end_headers()
        self.write_response_body(body)

    def send_no_content(self):
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.send_cors_headers()
        self.end_headers()

    def send_download(self, payload: str, *, filename: str, content_type: str, status=200):
        body = ("\ufeff" + payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.send_cors_headers()
        self.end_headers()
        self.write_response_body(body)

    def serve_path(self, path: Path, content_type: str):
        if not path.exists():
            self.send_json({"error": "not found", "path": str(path)}, status=404)
            return
        served_path = path
        content_encoding = ""
        vary_header = ""
        if self.client_accepts_gzip() and self.path_is_precompressed_candidate(path, content_type):
            gzip_path = self.gzip_sidecar_path(path)
            if self.gzip_sidecar_is_current(path, gzip_path):
                served_path = gzip_path
                content_encoding = "gzip"
                vary_header = "Accept-Encoding"
        try:
            stat = served_path.stat()
        except OSError:
            self.send_json({"error": "not found", "path": str(path)}, status=404)
            return
        etag = f'W/"{stat.st_mtime_ns:x}-{stat.st_size:x}"'
        last_modified = formatdate(stat.st_mtime, usegmt=True)
        if etag in {value.strip() for value in str(self.headers.get("If-None-Match") or "").split(",")}:
            self.send_response(304)
            self.send_header("ETag", etag)
            self.send_header("Last-Modified", last_modified)
            self.send_header("Cache-Control", "private, max-age=0")
            if content_encoding:
                self.send_header("Content-Encoding", content_encoding)
            if vary_header:
                self.send_header("Vary", vary_header)
            self.send_cors_headers()
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(stat.st_size))
        self.send_header("ETag", etag)
        self.send_header("Last-Modified", last_modified)
        self.send_header("Cache-Control", "private, max-age=0")
        if content_encoding:
            self.send_header("Content-Encoding", content_encoding)
        if vary_header:
            self.send_header("Vary", vary_header)
        self.send_cors_headers()
        self.end_headers()
        self.write_file_response_body(served_path)

    def client_accepts_gzip(self) -> bool:
        return "gzip" in str(self.headers.get("Accept-Encoding") or "").lower()

    def path_is_precompressed_candidate(self, path: Path, content_type: str) -> bool:
        return path.suffix.lower() == ".json" and content_type.startswith("application/json")

    def write_response_body(self, body: bytes):
        if not getattr(self, "_head_only", False):
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                self.close_connection = True

    def write_file_response_body(self, path: Path):
        if getattr(self, "_head_only", False):
            return
        try:
            with path.open("rb") as file:
                while True:
                    chunk = file.read(1024 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            self.close_connection = True
        except OSError:
            self.close_connection = True


def start_ui_case_summary_cache_prewarm():
    disabled = str(os.environ.get("FINAL_UI_PREWARM_CASE_SUMMARY", "1")).strip().lower()
    if disabled in {"0", "false", "no", "off"}:
        return

    def worker():
        handler = object.__new__(FinalUiHandler)
        run_ids: list[str] = []
        for run_id in (CURRENT_UI_DATA_RUN_ID, handler.default_selected_run_id()):
            if run_id and run_id not in run_ids:
                run_ids.append(run_id)
        latest = handler.latest_run_dir()
        if latest and latest.name not in run_ids:
            run_ids.append(latest.name)

        for run_id in run_ids:
            try:
                cache_path = handler.ensure_eval_case_summary_cache_path(run_id)
                print(f"Prewarmed UI case summary cache for {run_id}: {cache_path.name}", flush=True)
            except Exception as exc:
                print(f"UI case summary cache prewarm skipped for {run_id}: {exc}", flush=True)

    thread = threading.Thread(target=worker, name="final-ui-case-summary-prewarm", daemon=True)
    thread.start()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8512
    host = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("FINAL_UI_HOST", "localhost")
    requires_public_auth = host.strip().lower() in PUBLIC_BIND_HOSTS and not FINAL_UI_AUTH_DISABLED
    if requires_public_auth and not FINAL_UI_AUTH_USERS and not FINAL_UI_AUTH_TOKEN:
        raise SystemExit("Public bind requires FINAL_UI_AUTH_USERS, FINAL_UI_AUTH_TOKEN, or FINAL_UI_AUTH_DISABLED=1.")
    server = ThreadingHTTPServer((host, port), FinalUiHandler)
    display_host = "127.0.0.1" if host in {"", "0.0.0.0", "::"} else host
    print(f"UI server running at http://{display_host}:{port} (bind={host})", flush=True)
    if FINAL_UI_AUTH_DISABLED:
        print("Authentication disabled by FINAL_UI_AUTH_DISABLED=1.", flush=True)
    elif FINAL_UI_AUTH_USERS:
        print("User ID auth enabled. Admin can write; user is read-only.", flush=True)
        if FINAL_UI_AUTH_USERS_SOURCE == "default":
            print("Using default credentials: admin/admin and user/user.", flush=True)
        else:
            print("Using FINAL_UI_AUTH_USERS credentials.", flush=True)
    elif FINAL_UI_AUTH_TOKEN:
        print("Write API token enabled. Pass it in X-Final-UI-Token or Authorization: Bearer headers.", flush=True)
    start_ui_case_summary_cache_prewarm()
    server.serve_forever()


if __name__ == "__main__":
    main()
