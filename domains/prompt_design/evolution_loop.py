"""Run meta-agent, harness and independent evaluator for several generations."""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from domains.prompt_design.run_context import configure, initialize_run, output_root, resolve_config_path, run_root

ROOT_DIR = Path(__file__).resolve().parents[2]
def next_generation(output_dir):
    ids = []
    for path in output_dir.glob("gen_[0-9][0-9][0-9]"):
        try:
            ids.append(int(path.name[4:]))
        except ValueError:
            pass
    return max(ids, default=-1) + 1


def run_step(arguments, log_file=None):
    started = datetime.now(timezone.utc).isoformat()
    command = " ".join(str(item) for item in arguments)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"[{started}] START {command}\n")
    result = subprocess.run([sys.executable, *arguments], cwd=ROOT_DIR, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    if log_file:
        finished = datetime.now(timezone.utc).isoformat()
        with log_file.open("a", encoding="utf-8", newline="\n") as handle:
            if result.stdout:
                handle.write(result.stdout.rstrip() + "\n")
            if result.stderr:
                handle.write(result.stderr.rstrip() + "\n")
            handle.write(f"[{finished}] EXIT {result.returncode}\n")
    return result


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def decide(output_dir, generation, parent_score, min_score=None, max_regression=None):
    directory = output_dir / f"gen_{generation:03d}"
    metadata = read_json(directory / "metadata.json") or {}
    report = read_json(directory / "report.json") or {}
    checks = {
        "candidate_exists": (directory / "candidate_prompt.txt").exists(),
        "patch_exists": bool((directory / "model_patch.diff").exists() and (directory / "model_patch.diff").read_text(encoding="utf-8").strip()),
        "report_exists": bool(report),
        "evaluation_status": metadata.get("status") == "evaluated",
    }
    reasons = [name for name, passed in checks.items() if not passed]
    score = report.get("score")
    if not isinstance(score, (int, float)):
        reasons.append("missing_score")
    if min_score is not None and isinstance(score, (int, float)) and score < min_score:
        reasons.append(f"score_below_{min_score:g}")
    if max_regression is not None and isinstance(parent_score, (int, float)) and isinstance(score, (int, float)) and parent_score - score > max_regression:
        reasons.append(f"regression_over_{max_regression:g}")
    return {"generation": generation, "parent_score": parent_score, "score": score, "continue": not reasons, "reasons": reasons, "checks": checks, "timestamp": datetime.now(timezone.utc).isoformat()}


def detect_stagnation(decisions, threshold, window, min_gain):
    """Detect a high-scoring plateau over the last ``window`` generations."""
    scores = [item.get("score") for item in decisions if isinstance(item.get("score"), (int, float))]
    if threshold is None or window < 2 or len(scores) < window:
        return False
    recent = scores[-window:]
    return recent[0] >= threshold and max(recent) - recent[0] < min_gain


def incomplete_generation(output_dir):
    """Return the newest generation that can be resumed, if any."""
    paths = sorted(output_dir.glob("gen_[0-9][0-9][0-9]"), reverse=True)
    for path in paths:
        metadata = read_json(path / "metadata.json") or {}
        status = metadata.get("status")
        if status in {"interrupted", "pending_evaluation"}:
            try:
                return int(path.name[4:]), status, metadata
            except ValueError:
                continue
    return None


def evaluate_generation(output_dir, generation, original, run_harness=True, log_file=None):
    """Create and evaluate a candidate, returning a failure reason or None."""
    directory = output_dir / f"gen_{generation:03d}"
    candidate = directory / "candidate_prompt.txt"
    if run_harness:
        harness = run_step(["domains/prompt_design/harness.py", "--generation", str(generation)], log_file)
        if harness.returncode != 0:
            return "harness_failed"
    if not candidate.exists():
        return "candidate_missing"
    evaluator = run_step([
        "domains/prompt_design/evaluator/evaluator_runner.py",
        "--generation", str(generation),
        "--original-prompt", str(original),
        "--candidate-prompt", str(candidate),
    ], log_file)
    return None if evaluator.returncode == 0 else "evaluator_failed"


def write_website(config, output_dir, original, log_file):
    website = config.get("website", {}) or {}
    if not website.get("enabled", False):
        return None
    output = Path(website.get("output", "website/prompt_evolution.html")).expanduser()
    if not output.is_absolute():
        output = (run_root() / output).resolve()
    usage = output_dir.parent / "llm_usage.jsonl"
    configured_builder = website.get("script")
    if not configured_builder:
        return None
    candidate = Path(configured_builder).expanduser()
    builder = candidate if candidate.is_absolute() else (ROOT_DIR / candidate).resolve()
    return run_step([
        str(builder),
        "--root", str(output_dir),
        "--source-prompt", str(original),
        "--usage-log", str(usage),
        "--output", str(output),
    ], log_file)


def run_post_step(config, output_dir, generation, original, decision_file, log_file):
    """Run an optional, domain-independent hook after a generation."""
    hook = config.get("post_step", {}) or {}
    if not hook.get("enabled", False) or not hook.get("script"):
        return None
    candidate = Path(hook["script"]).expanduser()
    script = candidate if candidate.is_absolute() else (ROOT_DIR / candidate).resolve()
    arguments = [str(script), "--generation", str(generation), "--run-dir", str(run_root()),
                 "--output-dir", str(output_dir), "--source-prompt", str(original),
                 "--usage-log", str(output_dir.parent / "llm_usage.jsonl"),
                 "--decision-file", str(decision_file)]
    for key, value in (hook.get("params", {}) or {}).items():
        option = "--" + str(key).replace("_", "-")
        if isinstance(value, bool):
            if value:
                arguments.append(option)
        elif value is not None:
            arguments.extend([option, str(value)])
    config_path = os.getenv("PROMPT_EVOLUTION_CONFIG")
    if config_path:
        arguments.extend(["--config", config_path])
    return run_step(arguments, log_file)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=None)
    parser.add_argument("--start-generation", type=int, default=None)
    parser.add_argument("--parent-selection", choices=["best", "latest", "random", "score_prop", "score_child_prop"], default=None)
    parser.add_argument("--min-score", type=float, default=None)
    parser.add_argument("--max-regression", type=float, default=None)
    parser.add_argument("--stagnation-threshold", type=float, default=None, help="Only detect stagnation at or above this score")
    parser.add_argument("--stagnation-window", type=int, default=None, help="Number of evaluated generations in the plateau window")
    parser.add_argument("--stagnation-min-gain", type=float, default=None, help="Required score gain within the window")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--config", default=None, help="External run configuration")
    args = parser.parse_args()
    config = configure(args.config)
    initialize_run(config)
    output_dir = output_root()
    loop_log = output_dir / "loop.log"
    if not args.resume:
        loop_log.parent.mkdir(parents=True, exist_ok=True)
        loop_log.write_text("", encoding="utf-8", newline="\n")
    loop_config = config.get("loop", {}) or {}
    count = args.count if args.count is not None else int(loop_config.get("count", 3))
    parent_selection = args.parent_selection or loop_config.get("parent_selection", "score_child_prop")
    min_score = args.min_score if args.min_score is not None else loop_config.get("min_score")
    max_regression = args.max_regression if args.max_regression is not None else loop_config.get("max_regression")
    stagnation_threshold = args.stagnation_threshold if args.stagnation_threshold is not None else loop_config.get("stagnation_threshold", 80)
    stagnation_window = args.stagnation_window if args.stagnation_window is not None else int(loop_config.get("stagnation_window", 3))
    stagnation_min_gain = args.stagnation_min_gain if args.stagnation_min_gain is not None else float(loop_config.get("stagnation_min_gain", 1))
    if count < 1:
        parser.error("--count must be at least 1")
    if stagnation_window < 2 or stagnation_min_gain < 0:
        parser.error("stagnation window must be >= 2 and minimum gain must be >= 0")
    target = args.start_generation if args.start_generation is not None else next_generation(output_dir)
    decisions_file = output_dir / "loop_decisions.jsonl"
    previous_decisions = []
    if decisions_file.exists():
        for line in decisions_file.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                previous_decisions.append(item)
    original = resolve_config_path(config, "source_prompt", ROOT_DIR / "domains" / "prompt_design" / "prompt.md")

    # A fresh run starts with a task-agent candidate in gen_000. This is kept
    # outside the requested generation count and is also retried on resume if
    # the first evaluation was interrupted.
    gen0 = output_dir / "gen_000"
    gen0_metadata = read_json(gen0 / "metadata.json") or {}
    gen0_report = read_json(gen0 / "report.json") or {}
    if args.start_generation in (None, 0) and gen0_metadata.get("status") != "evaluated":
        failure = evaluate_generation(output_dir, 0, original, run_harness=not (gen0 / "candidate_prompt.txt").exists(), log_file=loop_log)
        if failure:
            print(f"Generation 000 bootstrap failed: {failure}")
            return 1
        website_result = write_website(config, output_dir, original, loop_log)
        if website_result is not None and website_result.returncode != 0:
            print("Website generation failed after gen_000 bootstrap.", file=sys.stderr)
        post_result = run_post_step(config, output_dir, 0, original, decisions_file, loop_log)
        if post_result is not None and post_result.returncode != 0:
            print("Post-step failed after gen_000 bootstrap.", file=sys.stderr)
        print("Generation 000 bootstrap evaluated.")
        target = max(target, 1)

    resume_info = incomplete_generation(output_dir) if args.resume else None
    resume_meta = False
    resume_pending = False
    if resume_info and (args.start_generation is None or args.start_generation == resume_info[0]):
        target, resume_status, resume_metadata = resume_info
        resume_file = output_dir / f"gen_{target:03d}" / "meta_agent_resume_state.json"
        # An interrupted marker alone is insufficient: older failures could
        # write the marker without producing a resumable state file.
        resume_meta = resume_status == "interrupted" and resume_file.exists()
        resume_pending = resume_status == "pending_evaluation"

    for _ in range(count):
        if resume_meta:
            parent_id = (read_json(output_dir / f"gen_{target:03d}" / "metadata.json") or {}).get("parent_genid")
            meta_args = ["domains/prompt_design/meta_step.py", "--target-generation", str(target)]
            if isinstance(parent_id, int):
                meta_args.extend(["--generation", str(parent_id)])
            else:
                meta_args.extend(["--parent-selection", parent_selection])
            meta_args.append("--resume")
            meta = run_step(meta_args, loop_log)
        elif resume_pending and resume_info and target == resume_info[0]:
            meta = subprocess.CompletedProcess([], 0)
        else:
            meta_args = ["domains/prompt_design/meta_step.py", "--parent-selection", parent_selection, "--target-generation", str(target)]
            if resume_info and target == resume_info[0] and not resume_pending:
                # Retry an interrupted generation whose resume state is absent.
                meta_args.append("--force")
            meta = run_step(meta_args, loop_log)
        if meta.returncode != 0:
            decision = {"generation": target, "continue": False, "reasons": ["meta_step_failed"]}
        else:
            target_candidate = output_dir / f"gen_{target:03d}" / "candidate_prompt.txt"
            failure = evaluate_generation(output_dir, target, original, run_harness=not target_candidate.exists(), log_file=loop_log)
            if failure:
                decision = {"generation": target, "continue": False, "reasons": [failure]}
            else:
                metadata = read_json(output_dir / f"gen_{target:03d}" / "metadata.json") or {}
                parent_id = metadata.get("parent_genid")
                parent = read_json(output_dir / f"gen_{parent_id:03d}" / "report.json") if isinstance(parent_id, int) else None
                decision = decide(output_dir, target, parent.get("score") if parent else None, min_score, max_regression)
        resume_meta = False
        resume_info = None
        decision.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        previous_decisions.append(decision)
        if decision.get("continue") and detect_stagnation(previous_decisions, stagnation_threshold, stagnation_window, stagnation_min_gain):
            decision["continue"] = False
            decision["reasons"] = [*decision.get("reasons", []), "stagnation_requires_detailed_evaluation"]
            decision["action"] = "run_detailed_evaluator_for_new_guidance"
        decisions_file.parent.mkdir(parents=True, exist_ok=True)
        with decisions_file.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(decision, ensure_ascii=False) + "\n")
        website_result = write_website(config, output_dir, original, loop_log)
        if website_result is not None and website_result.returncode != 0:
            print("Website generation failed; loop decision remains unchanged.", file=sys.stderr)
        post_result = run_post_step(config, output_dir, target, original, decisions_file, loop_log)
        if post_result is not None and post_result.returncode != 0:
            print("Post-step failed; loop decision remains unchanged.", file=sys.stderr)
        print(f"Generation {target}: {'continue' if decision['continue'] else 'stop'} ({', '.join(decision.get('reasons', [])) or 'checks passed'})")
        if not decision["continue"]:
            return 1
        target += 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
