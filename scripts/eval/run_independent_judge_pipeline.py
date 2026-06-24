from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def resolve_root(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def archive_root_for(out_root: str | Path) -> Path:
    root = resolve_root(out_root)
    if root.name == "archive":
        return root
    if root.parent.name == "archive":
        return root.parent
    return root / "archive"


def judge_job_dir(out_root: str | Path) -> Path:
    override = os.environ.get("EVAL_JUDGE_JOB_DIR", "").strip()
    if override:
        path = Path(override)
        return path if path.is_absolute() else ROOT / path
    return archive_root_for(out_root) / "judge_jobs"


def judge_child_run_root(out_root: str | Path) -> Path:
    override = os.environ.get("EVAL_JUDGE_CHILD_RUN_ROOT", "").strip()
    if override:
        path = Path(override)
        return path if path.is_absolute() else ROOT / path
    return archive_root_for(out_root) / "judge_runs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run each LLM judge independently, then merge completed judge rows."
    )
    parser.add_argument("--source-run-id", default="")
    parser.add_argument("--source-run-dir", default="")
    parser.add_argument("--answers-csv", default="")
    parser.add_argument("--cases-file", default="")
    parser.add_argument("--external-config-id", default="external_model_v1")
    parser.add_argument("--config", action="append", default=[])
    parser.add_argument("--complete-only", action="store_true")
    parser.add_argument("--registry", default="")
    parser.add_argument("--matrix", default="")
    parser.add_argument("--risk-taxonomy", default="")
    parser.add_argument("--out-root", default=str(ROOT / "out" / "eval_runs"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--base-url", default="")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--control-file", default="")
    parser.add_argument("--export-final-ui", action="store_true")
    parser.add_argument("--final-ui-data", default="")
    parser.add_argument("--scoring-mode", choices=["static_llm", "llm_override", "blend"], default="llm_override")
    parser.add_argument("--judge-config", action="append", required=True)
    parser.add_argument("--judge-mode", choices=["audit", "override", "blend"], default="override")
    parser.add_argument("--judge-blend-weight", type=float, default=0.5)
    parser.add_argument("--judge-score-weights", default="")
    parser.add_argument(
        "--judge-aggregation-method",
        choices=["auto", "weighted_mean", "mean", "trimmed_mean", "max", "min"],
        default="auto",
    )
    parser.add_argument("--pass-threshold", type=float, default=None)
    parser.add_argument("--static-embedding-model", default="")
    parser.add_argument("--static-embedding-base-url", default="")
    parser.add_argument("--static-embedding-keep-alive", default="0")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--retry-transient", type=int, default=2)
    parser.add_argument("--retry-sleep-seconds", type=float, default=2.0)
    parser.add_argument("--rate-limit-max-retries", type=int, default=0)
    parser.add_argument("--rate-limit-sleep-seconds", type=float, default=120.0)
    parser.add_argument("--min-ok-judges", type=int, default=1)
    parser.add_argument(
        "--conflict-policy",
        choices=["review", "arbiter_override", "three_judge"],
        default="review",
    )
    parser.add_argument("--arbiter-config", default="")
    return parser.parse_args()


def safe_suffix(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:72] or "judge"


def add_arg(cmd: list[str], name: str, value: object | None) -> None:
    if value is None:
        return
    text = str(value)
    if text:
        cmd.extend([name, text])


def add_repeated(cmd: list[str], name: str, values: list[str]) -> None:
    for value in values:
        text = str(value or "").strip()
        if text:
            cmd.extend([name, text])


def stream_output(process: subprocess.Popen[str], lock: threading.Lock) -> None:
    if process.stdout is None:
        return
    for line in process.stdout:
        with lock:
            print(line.rstrip("\n"), flush=True)


def source_run_dir_for_merge(args: argparse.Namespace, first_child_run_id: str, child_root: Path) -> Path:
    if args.source_run_dir:
        return resolve_root(args.source_run_dir)
    if args.source_run_id:
        return resolve_root(args.out_root) / args.source_run_id
    return child_root / first_child_run_id


def build_child_command(
    args: argparse.Namespace,
    judge_config: str,
    child_run_id: str,
    *,
    key_file: Path | None = None,
) -> list[str]:
    child_root = judge_child_run_root(args.out_root)
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "eval" / "judge_saved_answers.py"),
        "--run-id",
        child_run_id,
        "--out-root",
        str(child_root),
        "--timeout",
        str(args.timeout),
        "--scoring-mode",
        args.scoring_mode,
        "--judge-config",
        judge_config,
        "--judge-mode",
        args.judge_mode,
        "--judge-blend-weight",
        str(args.judge_blend_weight),
        "--workers",
        str(max(1, args.workers)),
        "--retry-transient",
        str(max(0, args.retry_transient)),
        "--retry-sleep-seconds",
        str(max(0.0, args.retry_sleep_seconds)),
        "--rate-limit-max-retries",
        str(max(0, args.rate_limit_max_retries)),
        "--rate-limit-sleep-seconds",
        str(max(0.0, args.rate_limit_sleep_seconds)),
        "--resume",
    ]
    if args.source_run_dir:
        add_arg(cmd, "--source-run-dir", args.source_run_dir)
    elif args.source_run_id:
        add_arg(cmd, "--source-run-dir", str(resolve_root(args.out_root) / args.source_run_id))
    add_arg(cmd, "--answers-csv", args.answers_csv)
    add_arg(cmd, "--cases-file", args.cases_file)
    add_arg(cmd, "--external-config-id", args.external_config_id)
    add_arg(cmd, "--key-file", str(key_file) if key_file else "")
    add_arg(cmd, "--registry", args.registry)
    add_arg(cmd, "--matrix", args.matrix)
    add_arg(cmd, "--risk-taxonomy", args.risk_taxonomy)
    add_arg(cmd, "--base-url", args.base_url)
    add_arg(cmd, "--control-file", args.control_file)
    add_arg(cmd, "--final-ui-data", args.final_ui_data)
    add_arg(cmd, "--static-embedding-model", args.static_embedding_model)
    add_arg(cmd, "--static-embedding-base-url", args.static_embedding_base_url)
    add_arg(cmd, "--static-embedding-keep-alive", args.static_embedding_keep_alive)
    add_arg(cmd, "--judge-aggregation-method", args.judge_aggregation_method)
    if args.pass_threshold is not None:
        add_arg(cmd, "--pass-threshold", args.pass_threshold)
    add_repeated(cmd, "--config", args.config)
    if args.complete_only:
        cmd.append("--complete-only")
    if args.allow_missing:
        cmd.append("--allow-missing")
    if args.export_final_ui:
        cmd.append("--export-final-ui")
    return cmd


def build_merge_command(
    args: argparse.Namespace,
    child_run_ids: list[str],
    *,
    out_root: Path | None = None,
    run_id: str | None = None,
) -> list[str]:
    child_root = judge_child_run_root(args.out_root)
    merge_out_root = out_root or resolve_root(args.out_root)
    source_run_dir = source_run_dir_for_merge(args, child_run_ids[0], child_root)
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "eval" / "merge_independent_judge_runs.py"),
        "--source-run-dir",
        str(source_run_dir),
        "--out-root",
        str(merge_out_root),
        "--run-id",
        run_id or args.run_id,
        "--scoring-mode",
        args.scoring_mode,
        "--judge-mode",
        args.judge_mode,
        "--judge-blend-weight",
        str(args.judge_blend_weight),
        "--min-ok-judges",
        str(max(1, args.min_ok_judges)),
        "--conflict-policy",
        args.conflict_policy,
    ]
    add_arg(cmd, "--cases-file", args.cases_file)
    add_arg(cmd, "--final-ui-data", args.final_ui_data)
    add_arg(cmd, "--judge-score-weights", args.judge_score_weights)
    add_arg(cmd, "--judge-aggregation-method", args.judge_aggregation_method)
    add_arg(cmd, "--arbiter-config-id", args.arbiter_config)
    if args.pass_threshold is not None:
        add_arg(cmd, "--pass-threshold", args.pass_threshold)
    for child_run_id in child_run_ids:
        cmd.extend(["--judge-run-dir", str(child_root / child_run_id)])
    if args.export_final_ui:
        cmd.append("--export-final-ui")
    return cmd


def run_command(cmd: list[str], env: dict[str, str]) -> int:
    return subprocess.call(cmd, cwd=str(ROOT), env=env)


def write_conflict_key_file(merge_run_id: str, out_root: str | Path) -> Path:
    root = resolve_root(out_root)
    score_path = root / merge_run_id / "judge_scores.jsonl"
    if not score_path.exists():
        raise SystemExit(f"merged score file not found for conflict extraction: {score_path}")
    key_path = judge_job_dir(out_root) / f"{merge_run_id}.conflict_keys.jsonl"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with score_path.open("r", encoding="utf-8") as source, key_path.open("w", encoding="utf-8") as target:
        for line in source:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("llm_judge_conflict"):
                target.write(
                    json.dumps(
                        {
                            "config_id": row.get("config_id"),
                            "case_id": row.get("case_id"),
                            "reason": row.get("llm_judge_conflict_reason", ""),
                            "arbiter_context": arbiter_context_from_merged_row(row),
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )
                count += 1
    print(f"CONFLICT_KEYS_WRITTEN path={key_path} count={count}", flush=True)
    return key_path


def conflict_key_count(key_file: Path) -> int:
    if not key_file.exists():
        return 0
    with key_file.open("r", encoding="utf-8") as file:
        return sum(1 for line in file if line.strip())


def json_field(value, fallback):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback
    return value if value is not None else fallback


def arbiter_context_from_merged_row(row: dict) -> dict:
    individual_scores = json_field(row.get("llm_judge_individual_scores"), [])
    if not isinstance(individual_scores, list):
        individual_scores = []
    base_judges = []
    for score in individual_scores:
        if not isinstance(score, dict):
            continue
        base_judges.append(
            {
                "role": score.get("role") or "judge",
                "config_id": score.get("config_id"),
                "provider": score.get("provider"),
                "model": score.get("model"),
                "overall_score": score.get("overall_score"),
                "pass": score.get("pass"),
                "critical_fail": score.get("critical_fail"),
                "error_type": score.get("error_type"),
                "reason": score.get("reason"),
                "acc": score.get("acc"),
                "com": score.get("com"),
                "utl": score.get("utl"),
                "nac": score.get("nac"),
                "hal": score.get("hal"),
                "utl_applicable": score.get("utl_applicable"),
                "prompt_version": score.get("prompt_version"),
                "prompt_hash": score.get("prompt_hash"),
            }
        )
    return {
        "conflict_reason": row.get("llm_judge_conflict_reason", ""),
        "score_gap": row.get("llm_judge_score_gap", ""),
        "score_min": row.get("llm_judge_score_min", ""),
        "score_max": row.get("llm_judge_score_max", ""),
        "pass_mismatch": row.get("llm_judge_pass_mismatch", ""),
        "base_judges": base_judges,
    }


def run_parallel_judges(
    *,
    args: argparse.Namespace,
    judge_configs: list[str],
    run_id_prefix: str,
    env: dict[str, str],
    key_file: Path | None = None,
) -> tuple[list[str], list[tuple[str, int]], bool]:
    output_lock = threading.Lock()
    children: list[tuple[str, str, subprocess.Popen[str], threading.Thread]] = []
    for judge_config in judge_configs:
        child_run_id = f"{run_id_prefix}__judge_{safe_suffix(judge_config)}"
        cmd = build_child_command(args, judge_config, child_run_id, key_file=key_file)
        print(f"INDEPENDENT_JUDGE_START judge={judge_config} run_id={child_run_id}", flush=True)
        process = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        thread = threading.Thread(target=stream_output, args=(process, output_lock), daemon=True)
        thread.start()
        children.append((judge_config, child_run_id, process, thread))

    child_run_ids: list[str] = []
    failed: list[tuple[str, int]] = []
    cancelled = False
    for judge_config, child_run_id, process, thread in children:
        returncode = process.wait()
        thread.join(timeout=5)
        child_run_ids.append(child_run_id)
        print(
            f"INDEPENDENT_JUDGE_DONE judge={judge_config} run_id={child_run_id} returncode={returncode}",
            flush=True,
        )
        if returncode == 130:
            cancelled = True
        elif returncode != 0:
            failed.append((judge_config, returncode))
    return child_run_ids, failed, cancelled


def main() -> int:
    args = parse_args()
    judge_configs = list(dict.fromkeys(str(item).strip() for item in args.judge_config if str(item).strip()))
    if len(judge_configs) < 2:
        raise SystemExit("run_independent_judge_pipeline requires at least two --judge-config values")
    arbiter_config = str(args.arbiter_config or "").strip()
    base_judge_configs = [judge for judge in judge_configs if judge != arbiter_config]
    if len(base_judge_configs) < 2:
        base_judge_configs = judge_configs
    if args.conflict_policy in {"arbiter_override", "three_judge"} and not arbiter_config:
        raise SystemExit("--arbiter-config is required when conflict-policy uses an arbiter")
    use_conflict_arbiter = bool(arbiter_config) and args.conflict_policy in {"arbiter_override", "three_judge"}

    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUNBUFFERED", "1")
    child_root = judge_child_run_root(args.out_root)
    child_root.mkdir(parents=True, exist_ok=True)
    child_run_ids, failed, cancelled = run_parallel_judges(
        args=args,
        judge_configs=base_judge_configs,
        run_id_prefix=args.run_id,
        env=env,
    )

    if cancelled:
        print("INDEPENDENT_JUDGE_CANCELLED merge skipped", flush=True)
        return 130

    if use_conflict_arbiter:
        base_merge_run_id = f"{args.run_id}__base_conflict_scan"
        print("INDEPENDENT_JUDGE_BASE_MERGE_START " + " ".join(child_run_ids), flush=True)
        original_policy = args.conflict_policy
        args.conflict_policy = "review"
        base_merge_cmd = build_merge_command(args, child_run_ids, out_root=child_root, run_id=base_merge_run_id)
        base_merge_returncode = run_command(base_merge_cmd, env)
        args.conflict_policy = original_policy
        print(f"INDEPENDENT_JUDGE_BASE_MERGE_DONE returncode={base_merge_returncode}", flush=True)
        if base_merge_returncode != 0:
            return base_merge_returncode
        key_file = write_conflict_key_file(base_merge_run_id, child_root)
        if conflict_key_count(key_file):
            arbiter_run_ids, arbiter_failed, arbiter_cancelled = run_parallel_judges(
                args=args,
                judge_configs=[arbiter_config],
                run_id_prefix=f"{args.run_id}__arbiter_conflicts",
                env=env,
                key_file=key_file,
            )
            if arbiter_cancelled:
                print("INDEPENDENT_JUDGE_CANCELLED final merge skipped", flush=True)
                return 130
            failed.extend(arbiter_failed)
            child_run_ids.extend(arbiter_run_ids)
        else:
            print("INDEPENDENT_JUDGE_NO_CONFLICTS arbiter skipped", flush=True)

    print("INDEPENDENT_JUDGE_MERGE_START " + " ".join(child_run_ids), flush=True)
    merge_cmd = build_merge_command(args, child_run_ids)
    merge_returncode = run_command(merge_cmd, env)
    print(f"INDEPENDENT_JUDGE_MERGE_DONE returncode={merge_returncode}", flush=True)
    if merge_returncode != 0:
        return merge_returncode
    if failed:
        failures = ", ".join(f"{judge}={code}" for judge, code in failed)
        print(f"INDEPENDENT_JUDGE_PARTIAL_FAILURE {failures}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
