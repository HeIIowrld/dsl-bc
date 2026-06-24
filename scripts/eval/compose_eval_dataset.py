from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / "config" / "eval_dataset_catalog.yaml"


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


def normalize_csv_case(row: dict[str, Any], *, path: Path, index: int, pool_id: str, pool: dict[str, Any]) -> dict[str, Any] | None:
    role = str(pool.get("role") or "benchmark")
    question = csv_text(row, "instruction", "question", "input", "prompt", "query", "user_question", "문제", "주관식 문제", "질문")
    answer = csv_text(row, "output", "ground_truth", "answer", "gold_answer", "expected_answer", "expected_output", "reference_answer", "target_answer", "정답", "모범답안", "기준답변")
    if not question and not answer:
        return None
    stable_id = csv_text(row, "case_id", "id", "question_id", "qid")
    ordinal_id = csv_text(row, "no", "row_no", "번호")
    case_id = stable_id or (f"{pool_id}-{ordinal_id}" if ordinal_id else f"{pool_id}-{index:05d}")
    qa_category = csv_text(row, "qa_category", "category", "source_type", "topic", "대분류", "카테고리") or role
    qa_topic = csv_text(row, "qa_topic", "qa_matrix_topic", "topic", "intent", "source_term", "금융토픽", "출처_용어") or qa_category
    question_type = csv_text(row, "question_type", "qtype", "type", "task_type", "문제유형", "질문유형") or "grounded_qa"
    suite = csv_text(row, "suite", "split_type", "regression_suite") or role
    regression_suite = csv_text(row, "regression_suite", "split_type", "suite")
    trap = csv_text(row, "forbidden_claims", "must_not_include", "hallucination_trap", "오답_유형", "hallucination_trap(모델이 틀리기 쉬운 오답)")
    metadata = {
        "qa_category": qa_category,
        "qa_topic": qa_topic,
        "qa_matrix_topic": qa_topic,
        "question_type": question_type,
        "source_type": qa_category,
        "source_title": path.stem,
        "case_source": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "expected_behavior": "answer_from_source",
        "selection_mode": "question_source_csv",
        "dataset_pool_id": pool_id,
        "dataset_role": role,
    }
    if role == "regression" and regression_suite:
        metadata["regression_suite"] = regression_suite
    normalized: dict[str, Any] = {
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
    return normalized


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def stable_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:16]


def resolve_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path


def metadata_for(row: dict[str, Any]) -> dict[str, Any]:
    return row.get("metadata") if isinstance(row.get("metadata"), dict) else {}


def first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def compact_topic_path(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    parts = [part.strip() for part in text.split(">") if part.strip()]
    if len(parts) >= 2:
        return " > ".join(parts[-2:])
    return text


def benchmark_topic_for_case(row: dict[str, Any], metadata: dict[str, Any], pool_id: str) -> str:
    existing = first_text(metadata.get("qa_matrix_topic"))
    if existing and existing not in {"faq", "finance_info"}:
        return existing
    path_topic = compact_topic_path(first_text(row.get("source_path"), metadata.get("source_path")))
    return first_text(
        path_topic,
        row.get("intent"),
        metadata.get("intent"),
        row.get("source_type"),
        metadata.get("source_type"),
        existing,
        pool_id,
    )


def benchmark_question_type_for_case(row: dict[str, Any], metadata: dict[str, Any]) -> str:
    return first_text(
        metadata.get("question_type"),
        row.get("category"),
        row.get("intent"),
        metadata.get("expected_behavior"),
        row.get("expected_behavior"),
    )


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


def case_id_for(row: dict[str, Any]) -> str:
    case_id = str(row.get("case_id") or row.get("scenario_id") or row.get("id") or "").strip()
    if case_id:
        return case_id
    text = json.dumps(row, ensure_ascii=False, sort_keys=True)
    return "COMPOSED-" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:12].upper()


def unique_cases(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        by_id.setdefault(case_id_for(row), row)
    return [by_id[key] for key in sorted(by_id)]


def parse_pool_overrides(values: list[str] | None) -> dict[str, int]:
    overrides: dict[str, int] = {}
    for value in values or []:
        if "=" not in value:
            raise ValueError(f"--pool must use pool_id=quota format: {value}")
        pool_id, quota_text = value.split("=", 1)
        pool_id = pool_id.strip()
        try:
            quota = int(quota_text)
        except ValueError as exc:
            raise ValueError(f"quota must be an integer: {value}") from exc
        if not pool_id:
            raise ValueError(f"pool id is empty: {value}")
        if quota < 0:
            raise ValueError(f"quota must be zero or greater: {value}")
        overrides[pool_id] = quota
    return overrides


def pools_for_request(catalog: dict[str, Any], profile_id: str | None, overrides: dict[str, int]) -> tuple[str, dict[str, int]]:
    profiles = catalog.get("profiles") if isinstance(catalog.get("profiles"), dict) else {}
    if profile_id and profile_id != "custom":
        profile = profiles.get(profile_id)
        if not isinstance(profile, dict):
            raise ValueError(f"unknown profile: {profile_id}")
        profile_pools = profile.get("pools") if isinstance(profile.get("pools"), dict) else {}
        quotas = {str(pool_id): int(quota) for pool_id, quota in profile_pools.items()}
    else:
        profile_id = profile_id or "custom"
        quotas = {}
    quotas.update(overrides)
    if not quotas:
        raise ValueError("choose --profile or at least one --pool pool_id=quota")
    if any(int(quota) < 0 for quota in quotas.values()):
        raise ValueError("pool quotas must be zero or greater")
    if all(int(quota) <= 0 for quota in quotas.values()):
        raise ValueError("at least one pool quota must be greater than zero")
    return profile_id, quotas


def optional_bool(value: Any) -> bool | None:
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


def explicit_gold_verified(row: dict[str, Any], pool: dict[str, Any]) -> bool | None:
    metadata = metadata_for(row)
    defaults = pool.get("metadata_defaults") if isinstance(pool.get("metadata_defaults"), dict) else {}
    for value in (
        row.get("gold_verified"),
        metadata.get("gold_verified"),
        pool.get("gold_verified"),
        pool.get("gold_verified_default"),
        defaults.get("gold_verified"),
    ):
        parsed = optional_bool(value)
        if parsed is not None:
            return parsed
    return None


def explicit_release_gate_eligible(row: dict[str, Any], pool: dict[str, Any]) -> bool | None:
    metadata = metadata_for(row)
    defaults = pool.get("metadata_defaults") if isinstance(pool.get("metadata_defaults"), dict) else {}
    for value in (
        row.get("release_gate_eligible"),
        metadata.get("release_gate_eligible"),
        row.get("gate_eligible"),
        metadata.get("gate_eligible"),
        pool.get("release_gate_eligible"),
        pool.get("release_gate_eligible_default"),
    ):
        parsed = optional_bool(value)
        if parsed is not None:
            return parsed
    return None


def normalized_case_status(row: dict[str, Any], pool: dict[str, Any]) -> str:
    metadata = metadata_for(row)
    status = first_text(row.get("case_status"), metadata.get("case_status")).lower()
    if status in {"draft", "shadow", "active", "deprecated"}:
        return status
    source_status = first_text(row.get("status"), metadata.get("status")).lower()
    if source_status in {"shadow", "deprecated", "draft"}:
        return source_status
    if source_status in {"candidate", "generated"}:
        return "draft"
    if source_status == "active" and explicit_gold_verified(row, pool) is True:
        return "active"
    role = str(pool.get("role") or "regression").lower()
    if role == "benchmark":
        return "shadow"
    default_status = first_text(pool.get("case_status_default"), pool.get("case_status")).lower()
    if default_status in {"draft", "shadow", "active", "deprecated"}:
        return default_status
    return "shadow"


def lifecycle_defaults(row: dict[str, Any], pool: dict[str, Any], case_status: str, pool_gate_eligible: bool) -> tuple[bool, bool, bool]:
    gold_verified = explicit_gold_verified(row, pool) is True
    explicit_release = explicit_release_gate_eligible(row, pool)
    release_gate_eligible = (
        explicit_release
        if explicit_release is not None
        else bool(pool_gate_eligible and case_status == "active" and gold_verified)
    )
    release_gate_eligible = bool(release_gate_eligible and case_status == "active" and gold_verified)
    metadata = metadata_for(row)
    explicit_review = optional_bool(row.get("human_review_required"))
    if explicit_review is None:
        explicit_review = optional_bool(metadata.get("human_review_required"))
    human_review_required = (
        explicit_review
        if explicit_review is not None
        else case_status in {"draft", "shadow"} or not gold_verified
    )
    return release_gate_eligible, gold_verified, human_review_required


def annotate_case(
    row: dict[str, Any],
    *,
    pool_id: str,
    pool: dict[str, Any],
    seed: int,
    profile_id: str,
    source_hash: str,
    forced_case_status: str | None = None,
    case_source: str | None = None,
) -> dict[str, Any]:
    case = copy.deepcopy(row)
    case.setdefault("case_id", case_id_for(row))
    metadata = dict(metadata_for(case))
    role = str(pool.get("role") or "regression")
    pool_gate_eligible = bool(pool.get("gate_eligible", role != "benchmark"))
    case_status = forced_case_status or normalized_case_status(case, pool)
    release_gate_eligible, gold_verified, human_review_required = lifecycle_defaults(case, pool, case_status, pool_gate_eligible)
    gate_eligible = bool(pool_gate_eligible and release_gate_eligible)
    defaults = pool.get("metadata_defaults") if isinstance(pool.get("metadata_defaults"), dict) else {}
    for key, value in defaults.items():
        metadata.setdefault(str(key), value)
    if role == "benchmark":
        topic = benchmark_topic_for_case(case, metadata, pool_id)
        question_type = benchmark_question_type_for_case(case, metadata)
        if topic:
            metadata["qa_matrix_topic"] = topic
        if question_type:
            metadata["question_type"] = question_type

    metadata.update(
        {
            "dataset_pool_id": pool_id,
            "dataset_role": role,
            "dataset_version": str(pool.get("dataset_version") or "v0"),
            "source_hash": source_hash,
            "is_public": bool(pool.get("is_public", False)),
            "selection_seed": seed,
            "profile_id": profile_id,
            "gate_eligible": gate_eligible,
            "release_gate_eligible": release_gate_eligible,
            "case_status": case_status,
            "gold_verified": gold_verified,
            "human_review_required": human_review_required,
        }
    )
    if case_source:
        metadata["case_source"] = case_source
    case["metadata"] = metadata
    case["gate_eligible"] = gate_eligible
    case["release_gate_eligible"] = release_gate_eligible
    case["case_status"] = case_status
    case["gold_verified"] = gold_verified
    case["human_review_required"] = human_review_required
    if case_source:
        case["case_source"] = case_source
    case["dataset_pool_id"] = pool_id
    case["dataset_role"] = role
    case["dataset_version"] = metadata["dataset_version"]
    case["source_hash"] = source_hash
    case["is_public"] = metadata["is_public"]
    return case


def compose_dataset(
    *,
    catalog: dict[str, Any],
    profile_id: str | None,
    pool_overrides: dict[str, int] | None = None,
    seed: int | None = None,
    case_status: str = "all",
    allow_shadow_fallback: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    seed = int(catalog.get("default_seed", 42) if seed is None else seed)
    profile_id, quotas = pools_for_request(catalog, profile_id, pool_overrides or {})
    pools = catalog.get("pools") if isinstance(catalog.get("pools"), dict) else {}
    seen: set[str] = set()
    selected: list[dict[str, Any]] = []
    pool_summaries: list[dict[str, Any]] = []

    for pool_id, quota in quotas.items():
        if quota <= 0:
            continue
        pool = pools.get(pool_id)
        if not isinstance(pool, dict):
            raise ValueError(f"unknown pool: {pool_id}")
        path = resolve_path(str(pool.get("path") or ""))
        if not path.exists():
            raise FileNotFoundError(f"dataset pool path is missing for {pool_id}: {path}")
        source_hash = stable_hash(path)
        all_candidates = unique_cases([row for row in read_cases_path(path, pool_id=pool_id, pool=pool) if matches_filter(row, pool.get("filters"))])
        fallback_to_shadow = False
        if case_status == "all":
            candidates = all_candidates
        else:
            candidates = [row for row in all_candidates if normalized_case_status(row, pool) == case_status]
            if (
                case_status == "active"
                and allow_shadow_fallback
                and not candidates
                and all_candidates
            ):
                candidates = all_candidates
                fallback_to_shadow = True
        rng = random.Random(f"{seed}:{pool_id}")
        shuffled = list(candidates)
        rng.shuffle(shuffled)
        chosen: list[dict[str, Any]] = []
        for row in shuffled:
            case_id = case_id_for(row)
            if case_id in seen:
                continue
            chosen.append(row)
            seen.add(case_id)
            if len(chosen) >= quota:
                break
        if len(chosen) < quota:
            raise ValueError(
                f"pool {pool_id} requested {quota} cases but only {len(chosen)} unique cases are available "
                f"after filters and cross-pool de-duplication"
            )
        annotated = [
            annotate_case(
                row,
                pool_id=pool_id,
                pool=pool,
                seed=seed,
                profile_id=profile_id,
                source_hash=source_hash,
                forced_case_status="shadow" if fallback_to_shadow else None,
                case_source="shadow_fallback" if fallback_to_shadow else None,
            )
            for row in chosen
        ]
        selected.extend(annotated)
        pool_summaries.append(
            {
                "pool_id": pool_id,
                "role": pool.get("role", "regression"),
                "path": str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path),
                "requested": quota,
                "selected": len(annotated),
                "available": len(candidates),
                "available_before_case_status_filter": len(all_candidates),
                "case_status_filter": case_status,
                "shadow_fallback": fallback_to_shadow,
                "gate_eligible": bool(pool.get("gate_eligible", pool.get("role") != "benchmark")),
                "dataset_version": pool.get("dataset_version", "v0"),
                "source_hash": source_hash,
            }
        )

    role_counts = Counter(str(row.get("dataset_role") or metadata_for(row).get("dataset_role") or "unknown") for row in selected)
    status_counts = Counter(str(row.get("case_status") or metadata_for(row).get("case_status") or "unknown") for row in selected)
    gate_counts = Counter("eligible" if row.get("gate_eligible") else "not_eligible" for row in selected)
    shadow_fallback_used = any(pool.get("shadow_fallback") for pool in pool_summaries)
    has_gate_eligible = bool(gate_counts.get("eligible"))
    if shadow_fallback_used or (role_counts.get("regression") and not has_gate_eligible):
        run_type = "exploratory_regression"
    elif has_gate_eligible:
        run_type = "release_gate"
    elif role_counts and set(role_counts) <= {"benchmark"}:
        run_type = "benchmark"
    else:
        run_type = profile_id
    summary = {
        "profile_id": profile_id,
        "seed": seed,
        "total": len(selected),
        "pools": pool_summaries,
        "role_counts": dict(sorted(role_counts.items())),
        "case_status_counts": dict(sorted(status_counts.items())),
        "gate_eligible_counts": dict(sorted(gate_counts.items())),
        "run_type": run_type,
        "case_source": "shadow_fallback" if shadow_fallback_used else "catalog",
        "case_ids": [case_id_for(row) for row in selected],
    }
    return selected, summary


def default_output_path(catalog: dict[str, Any], profile_id: str, seed: int) -> Path:
    output_dir = resolve_path(str(catalog.get("resolved_output_dir") or "out/eval_runs/profiles"))
    return output_dir / f"{profile_id}_seed{seed}.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compose deterministic eval case files from dataset pools.")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    parser.add_argument("--profile", default=None)
    parser.add_argument("--pool", action="append", default=None, help="Pool quota override, e.g. faq_50=10")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--summary", default=None)
    parser.add_argument("--case-status", choices=["active", "shadow", "all"], default="all")
    parser.add_argument("--allow-shadow-fallback", action="store_true")
    return parser.parse_args()


def main() -> None:
    try:
        args = parse_args()
        catalog = load_config(resolve_path(args.catalog))
        overrides = parse_pool_overrides(args.pool)
        seed = int(catalog.get("default_seed", 42) if args.seed is None else args.seed)
        cases, summary = compose_dataset(
            catalog=catalog,
            profile_id=args.profile,
            pool_overrides=overrides,
            seed=seed,
            case_status=args.case_status,
            allow_shadow_fallback=args.allow_shadow_fallback,
        )
        profile_id = str(summary["profile_id"])
        output = resolve_path(args.output) if args.output else default_output_path(catalog, profile_id, seed)
        summary_path = resolve_path(args.summary) if args.summary else output.with_suffix(".summary.json")
        write_jsonl(output, cases)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"profile={profile_id}")
        print(f"seed={seed}")
        print(f"cases={len(cases)}")
        print(f"output={output}")
        print(f"summary={summary_path}")
    except (FileNotFoundError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc))


if __name__ == "__main__":
    main()
