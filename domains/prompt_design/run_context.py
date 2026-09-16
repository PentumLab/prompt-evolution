"""Resolve run-specific paths without moving the shared project code."""

import json
import os
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_config(path=None):
    raw_path = path or os.getenv("PROMPT_EVOLUTION_CONFIG")
    if not raw_path:
        return {}
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = (REPO_ROOT / candidate).resolve()
    with candidate.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    if not isinstance(config, dict):
        raise ValueError(f"Run config must contain an object: {candidate}")
    return config


def configure(config_path=None):
    if config_path:
        raw = Path(config_path).expanduser()
        if not raw.is_absolute():
            raw = (REPO_ROOT / raw).resolve()
        os.environ["PROMPT_EVOLUTION_CONFIG"] = str(raw)
        # The shared agent configuration loader reads this variable. Keep it
        # aligned with the run config so evaluator and agents use the models
        # selected for this run instead of the repository default config.
        os.environ["HYPERAGENT_CONFIG"] = str(raw)
    config = load_config(config_path)
    run_dir = config.get("run_dir")
    if run_dir:
        run_path = Path(run_dir).expanduser()
        if not run_path.is_absolute():
            run_path = (REPO_ROOT / run_path).resolve()
        os.environ["PROMPT_EVOLUTION_RUN_DIR"] = str(run_path)
        usage_path = config.get("usage_log_path") or config.get("usage", {}).get("usage_log_path")
        if usage_path:
            usage = Path(usage_path).expanduser()
            if not usage.is_absolute():
                usage = (run_path / usage).resolve()
            os.environ["HYPERAGENT_USAGE_LOG"] = str(usage)
    return config


def run_root():
    value = os.getenv("PROMPT_EVOLUTION_RUN_DIR")
    return Path(value).expanduser().resolve() if value else REPO_ROOT


def output_root():
    return run_root() / "outputs" / "prompt_design"


def resolve_config_path(config, key, default):
    value = config.get(key, default)
    path = Path(value).expanduser()
    return path if path.is_absolute() else (REPO_ROOT / path).resolve()


def initialize_run(config):
    root = run_root()
    root.mkdir(parents=True, exist_ok=True)
    agent_target = root / "prompt_design_agent.py"
    baseline = resolve_config_path(config, "agent_baseline", "prompt_design_agent.py")
    if not agent_target.exists():
        agent_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(baseline, agent_target)
    output_root().mkdir(parents=True, exist_ok=True)
    return root
