from __future__ import annotations

import copy
import csv
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / "config" / "eval_dataset_catalog.yaml"
DEFAULT_SETTINGS = ROOT / "final_UI" / "data" / "question_dataset_settings.json"

BENCHMARK_CSV_ROOT = ROOT / "questionlist" / "benchmark"
REGRESSION_CSV_ROOT = ROOT / "questionlist" / "regression"
USER_UPLOAD_CSV_ROOT = ROOT / "questionlist" / "user_uploads"
QUESTIONLIST_CSV_DIRS = (
    BENCHMARK_CSV_ROOT,
    REGRESSION_CSV_ROOT,
    USER_UPLOAD_CSV_ROOT / "benchmark",
    USER_UPLOAD_CSV_ROOT / "regression",
)

QUESTION_DATASET_ROLES = ("benchmark", "regression")
FALLBACK_DEFAULT_DATASET_BY_ROLE = {
    "benchmark": "benchmark_final_full",
    "regression": "regression_golden_full",
}
DEFAULT_PROFILE_BY_ROLE = {
    "benchmark": "benchmark_default_full",
    "regression": "regression_default_full",
}
REGISTERED_ALL_PROFILE_BY_ROLE = {
    "benchmark": "benchmark_registered_all",
    "regression": "regression_registered_all",
}

EXCLUDED_DATASET_PATH_MARKERS = (
    "_unused_files",
    "archive",
    "backup",
    "tmp",
    "draft",
    "cleanup",
)
EXCLUDED_DATASET_NAME_TOKENS = ("old",)

CSV_QUESTION_FIELD_ALIASES = (
    "instruction",
    "question",
    "input",
    "prompt",
    "query",
    "user_question",
    "문제",
    "주관식 문제",
    "질문",
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
    "hallucination_trap(모델이 꾸미기 쉬운 오답)",
    "오답_유형",
)
CSV_CASE_ID_FIELD_ALIASES = ("case_id", "id", "question_id", "qid")
CSV_ORDINAL_FIELD_ALIASES = ("no", "row_no", "번호")


def load_config(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise RuntimeError(f"{path} is not JSON and PyYAML is not installed") from exc
        payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def resolve_project_path(value: str, *, root: Path = ROOT) -> Path:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("path is required")
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve(strict=False)
    project_root = root.resolve(strict=False)
    try:
        resolved.relative_to(project_root)
    except ValueError as exc:
        raise ValueError(f"path must stay under project root: {display_path(path, root=root)}") from exc
    return resolved


def display_path(path: Path, *, root: Path = ROOT) -> str:
    try:
        return str(path.resolve(strict=False).relative_to(root.resolve(strict=False)))
    except ValueError:
        return str(path)


def optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return None


def normalize_question_dataset_role(value: Any) -> str:
    role = str(value or "benchmark").strip().lower()
    return role if role in set(QUESTION_DATASET_ROLES) else "benchmark"


def csv_text(row: dict[str, Any], *keys: str) -> str:
    normalized = {str(key or "").strip().lstrip("\ufeff").lower(): value for key, value in row.items()}
    for key in keys:
        direct_key = str(key or "").strip().lstrip("\ufeff")
        value = row.get(direct_key)
        if value in ("", None):
            value = normalized.get(direct_key.lower())
        text = str(value or "").strip()
        if text:
            return text
    return ""


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
    return rows


def normalize_csv_case(row: dict[str, Any], *, path: Path, index: int, pool_id: str, pool: dict[str, Any]) -> dict[str, Any] | None:
    role = normalize_question_dataset_role(pool.get("role"))
    question = csv_text(row, *CSV_QUESTION_FIELD_ALIASES)
    answer = csv_text(row, *CSV_ANSWER_FIELD_ALIASES)
    if not question and not answer:
        return None
    stable_id = csv_text(row, *CSV_CASE_ID_FIELD_ALIASES)
    ordinal_id = csv_text(row, *CSV_ORDINAL_FIELD_ALIASES)
    case_id = stable_id or (f"{pool_id}-{ordinal_id}" if ordinal_id else f"{pool_id}-{index:05d}")
    qa_category = csv_text(row, *CSV_QA_CATEGORY_FIELD_ALIASES) or role
    qa_topic = csv_text(row, *CSV_QA_TOPIC_FIELD_ALIASES) or qa_category
    question_type = csv_text(row, *CSV_QUESTION_TYPE_FIELD_ALIASES) or "grounded_qa"
    suite = csv_text(row, "suite", "split_type", "regression_suite") or role
    regression_suite = csv_text(row, "regression_suite", "split_type", "suite")
    trap = csv_text(row, *CSV_FORBIDDEN_FIELD_ALIASES)
    metadata = {
        "qa_category": qa_category,
        "qa_topic": qa_topic,
        "qa_matrix_topic": qa_topic,
        "question_type": question_type,
        "source_type": qa_category,
        "source_title": path.stem,
        "case_source": display_path(path),
        "expected_behavior": "answer_from_source",
        "selection_mode": "question_source_csv",
        "dataset_pool_id": pool_id,
        "dataset_role": role,
    }
    if role == "regression" and regression_suite:
        metadata["regression_suite"] = regression_suite
    return {
        "case_id": str(case_id),
        "question_id": str(case_id),
        "suite": suite,
        "question": question,
        "instruction": question,
        "output": answer,
        "gold_answer": answer,
        "required_conditions": [answer] if answer else [],
        "forbidden_claims": [trap] if trap else [],
        "intent": qa_topic,
        "task_type": "qa",
        "qa_category": qa_category,
        "source_type": qa_category,
        "question_type": question_type,
        "qa_topic": qa_topic,
        "qa_matrix_topic": qa_topic,
        "expected_behavior": "answer_from_source",
        "selection_mode": "question_source_csv",
        "dataset_pool_id": pool_id,
        "dataset_role": role,
        "metadata": metadata,
    }


def read_cases_path(path: Path, *, pool_id: str, pool: dict[str, Any]) -> list[dict[str, Any]]:
    if path.suffix.lower() != ".csv":
        return read_jsonl(path)
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for index, row in enumerate(reader, 1):
            normalized = normalize_csv_case(row, path=path, index=index, pool_id=pool_id, pool=pool)
            if normalized:
                rows.append(normalized)
    return rows


def metadata_for(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("metadata") if isinstance(row.get("metadata"), dict) else {}


def value_at(row: dict[str, Any], key: str) -> Any:
    current: Any = row
    for part in key.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            current = None
            break
    if current is not None and current != "":
        return current
    return metadata_for(row).get(key)


def values_for(row: dict[str, Any], key: str) -> set[str]:
    value = value_at(row, key)
    if value is None or value == "":
        return set()
    if isinstance(value, list):
        return {str(item) for item in value}
    return {str(value)}


def matches_filter(row: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    if not filters:
        return True
    include = filters.get("include") if isinstance(filters.get("include"), dict) else filters
    exclude = filters.get("exclude") if isinstance(filters.get("exclude"), dict) else {}
    for key, accepted in include.items():
        if key == "exclude":
            continue
        accepted_values = {str(item) for item in (accepted if isinstance(accepted, list) else [accepted])}
        if values_for(row, key).isdisjoint(accepted_values):
            return False
    for key, rejected in exclude.items():
        rejected_values = {str(item) for item in (rejected if isinstance(rejected, list) else [rejected])}
        if not values_for(row, key).isdisjoint(rejected_values):
            return False
    return True


def summarize_case_file(path: Path, *, filters: dict[str, Any] | None = None, dataset_id: str = "", role: str = "") -> dict[str, int]:
    if not path.exists():
        return {"total": 0}
    pool = {"role": normalize_question_dataset_role(role)}
    rows = read_cases_path(path, pool_id=dataset_id or path.stem, pool=pool)
    return {"total": sum(1 for row in rows if matches_filter(row, filters))}


def catalog_item_visible(item: dict[str, Any]) -> bool:
    value = optional_bool(item.get("ui_visible"))
    return True if value is None else value


def path_has_excluded_dataset_marker(path: Path) -> bool:
    normalized_parts = [str(part).lower() for part in path.parts]
    if any(marker in part for part in normalized_parts for marker in EXCLUDED_DATASET_PATH_MARKERS):
        return True
    tokens: list[str] = []
    for part in normalized_parts:
        tokens.extend(token for token in re.split(r"[^a-z0-9]+", part) if token)
    return any(token in EXCLUDED_DATASET_NAME_TOKENS for token in tokens)


def catalog_dataset_visible(item: dict[str, Any], path: Path) -> bool:
    if not isinstance(item, dict) or not catalog_item_visible(item):
        return False
    return path.exists() and not path_has_excluded_dataset_marker(path)


def discover_question_csv_datasets() -> dict[str, dict[str, Any]]:
    datasets: dict[str, dict[str, Any]] = {}
    upload_root = USER_UPLOAD_CSV_ROOT.resolve(strict=False)
    for directory in QUESTIONLIST_CSV_DIRS:
        if not directory.exists():
            continue
        role = normalize_question_dataset_role(directory.name)
        try:
            directory.resolve(strict=False).relative_to(upload_root)
            is_user_upload = True
        except ValueError:
            is_user_upload = False
        for path in sorted(directory.glob("*.csv")):
            if not is_user_upload and path_has_excluded_dataset_marker(path):
                continue
            dataset_id = f"user__{role}__{path.stem}" if is_user_upload else f"{directory.name}__{path.stem}"
            datasets[dataset_id] = {
                "id": dataset_id,
                "name": path.stem,
                "path": path,
                "role": role,
                "format": "csv",
                "directory": display_path(directory),
                "user_uploaded": is_user_upload,
                "version": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y%m%d_%H%M%S"),
            }
    return datasets


def question_dataset_pool_quota(pool: dict[str, Any]) -> int:
    try:
        return max(0, int(pool.get("total") or pool.get("default_quota") or 0))
    except (TypeError, ValueError):
        return 0


def question_dataset_pool_specs(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    pools = catalog.get("pools") if isinstance(catalog.get("pools"), dict) else {}
    specs: dict[str, dict[str, Any]] = {}
    catalog_paths: dict[str, str] = {}

    for pool_id, pool in pools.items():
        if not isinstance(pool, dict) or not pool.get("path"):
            continue
        try:
            path = resolve_project_path(str(pool.get("path") or ""))
        except ValueError:
            continue
        catalog_paths[str(path.resolve(strict=False)).lower()] = str(pool_id)
        if not catalog_dataset_visible(pool, path):
            continue
        role = normalize_question_dataset_role(pool.get("role"))
        summary = summarize_case_file(path, filters=pool.get("filters"), dataset_id=str(pool_id), role=role)
        quota = int(summary.get("total") or pool.get("default_quota") or 0)
        spec = copy.deepcopy(pool)
        spec.update(
            {
                "label": str(pool.get("label") or path.name),
                "path": display_path(path),
                "role": role,
                "default_quota": quota,
                "total": quota,
                "gate_eligible": bool(pool.get("gate_eligible", role != "benchmark")),
                "dataset_version": str(
                    pool.get("dataset_version")
                    or datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y%m%d_%H%M%S")
                ),
                "registered_all_eligible": optional_bool(pool.get("registered_all_eligible")) is not False,
                "case_id_prefix": str(pool.get("case_id_prefix") or pool_id),
            }
        )
        specs[str(pool_id)] = spec

    for dataset in discover_question_csv_datasets().values():
        path = dataset["path"]
        resolved_key = str(path.resolve(strict=False)).lower()
        if resolved_key in catalog_paths:
            continue
        role = normalize_question_dataset_role(dataset["role"])
        summary = summarize_case_file(path, dataset_id=dataset["id"], role=role)
        quota = int(summary.get("total") or 0)
        specs[dataset["id"]] = {
            "label": dataset["name"],
            "path": display_path(path),
            "role": role,
            "default_quota": quota,
            "total": quota,
            "gate_eligible": role != "benchmark",
            "release_gate_eligible_default": role == "regression",
            "case_status_default": "active" if role == "regression" else "shadow",
            "gold_verified_default": role == "regression",
            "dataset_version": dataset["version"],
            "is_public": not bool(dataset.get("user_uploaded")),
            "ui_visible": True,
            "source_format": "csv",
            "source_directory": dataset["directory"],
            "auto_discovered": True,
            "user_uploaded": bool(dataset.get("user_uploaded")),
            "registered_all_eligible": True,
            "case_id_prefix": dataset["id"],
        }
    return specs


def load_question_dataset_settings(path: Path = DEFAULT_SETTINGS) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {"defaults": {}}
    try:
        raw = load_config(path)
    except (OSError, json.JSONDecodeError, RuntimeError, ValueError):
        return {"defaults": {}}
    defaults = raw.get("defaults") if isinstance(raw, dict) and isinstance(raw.get("defaults"), dict) else {}
    return {
        "defaults": {
            role: str(defaults.get(role) or "").strip()
            for role in QUESTION_DATASET_ROLES
            if str(defaults.get(role) or "").strip()
        }
    }


def write_question_dataset_settings(settings: dict[str, Any], path: Path = DEFAULT_SETTINGS) -> None:
    defaults = settings.get("defaults") if isinstance(settings.get("defaults"), dict) else {}
    payload = {
        "defaults": {
            role: str(defaults.get(role) or "").strip()
            for role in QUESTION_DATASET_ROLES
            if str(defaults.get(role) or "").strip()
        }
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


def dataset_id_matches_role(dataset_id: str, role: str, pools: dict[str, dict[str, Any]]) -> bool:
    pool = pools.get(dataset_id) if isinstance(pools, dict) else None
    return isinstance(pool, dict) and str(pool.get("role") or "").lower() == role and question_dataset_pool_quota(pool) > 0


def question_dataset_defaults(
    pools: dict[str, dict[str, Any]] | None = None,
    *,
    settings_path: Path = DEFAULT_SETTINGS,
) -> dict[str, str]:
    pool_specs = pools if isinstance(pools, dict) else question_dataset_pool_specs(load_config(DEFAULT_CATALOG))
    configured = load_question_dataset_settings(settings_path).get("defaults", {})
    defaults: dict[str, str] = {}
    for role in QUESTION_DATASET_ROLES:
        candidate = str(configured.get(role) or "").strip()
        if candidate and dataset_id_matches_role(candidate, role, pool_specs):
            defaults[role] = candidate
            continue
        fallback = FALLBACK_DEFAULT_DATASET_BY_ROLE.get(role, "")
        if fallback and dataset_id_matches_role(fallback, role, pool_specs):
            defaults[role] = fallback
            continue
        defaults[role] = next(
            (
                pool_id
                for pool_id, pool in sorted(pool_specs.items())
                if isinstance(pool, dict)
                and str(pool.get("role") or "").lower() == role
                and question_dataset_pool_quota(pool) > 0
            ),
            "",
        )
    return defaults


def build_runtime_eval_dataset_catalog(
    catalog: dict[str, Any] | None = None,
    *,
    catalog_path: Path = DEFAULT_CATALOG,
    settings_path: Path = DEFAULT_SETTINGS,
) -> dict[str, Any]:
    base_catalog = load_config(catalog_path) if catalog is None else catalog
    runtime_catalog = copy.deepcopy(base_catalog if isinstance(base_catalog, dict) else {})
    runtime_catalog.setdefault("default_seed", 42)
    runtime_catalog["pools"] = question_dataset_pool_specs(runtime_catalog)
    profiles = runtime_catalog.get("profiles") if isinstance(runtime_catalog.get("profiles"), dict) else {}
    profiles = copy.deepcopy(profiles)

    for legacy_profile in ("benchmark_final_full", "regression_golden_full"):
        if isinstance(profiles.get(legacy_profile), dict):
            profiles[legacy_profile]["ui_visible"] = False

    defaults = question_dataset_defaults(runtime_catalog["pools"], settings_path=settings_path)
    for role in QUESTION_DATASET_ROLES:
        default_dataset_id = defaults.get(role, "")
        default_profile_id = DEFAULT_PROFILE_BY_ROLE[role]
        all_profile_id = REGISTERED_ALL_PROFILE_BY_ROLE[role]
        role_label = "벤치마크" if role == "benchmark" else "회귀"
        default_quota = question_dataset_pool_quota(runtime_catalog["pools"].get(default_dataset_id, {}))
        if default_dataset_id and default_quota > 0:
            profiles[default_profile_id] = {
                "label": f"기본 {role_label} 셋",
                "description": f"기본으로 지정된 {role_label} 테스트셋 전체를 실행합니다.",
                "pools": {default_dataset_id: default_quota},
                "ui_visible": True,
                "role": role,
                "default_dataset_id": default_dataset_id,
            }

        all_pools = {
            pool_id: question_dataset_pool_quota(pool)
            for pool_id, pool in sorted(runtime_catalog["pools"].items())
            if isinstance(pool, dict)
            and str(pool.get("role") or "").lower() == role
            and bool(pool.get("registered_all_eligible", True))
            and question_dataset_pool_quota(pool) > 0
        }
        if all_pools:
            profiles[all_profile_id] = {
                "label": f"등록된 {role_label} 전체",
                "description": f"현재 등록되어 있는 {role_label} 테스트셋을 모두 합쳐 실행합니다.",
                "pools": all_pools,
                "ui_visible": True,
                "role": role,
                "all_registered": True,
            }

    profiles.setdefault("custom_seeded_mix", {"label": "직접 구성", "pools": {}, "ui_visible": True})
    runtime_catalog["profiles"] = profiles
    return runtime_catalog
