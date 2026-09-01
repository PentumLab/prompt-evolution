import json
import os
from functools import lru_cache
from pathlib import Path


CONFIG_FILENAME = "hyperagent_config.json"
UNLIMITED_VALUES = {"-1", "unlimited", "none", "off", "false", "no"}


def _unique_paths(paths):
    seen = set()
    result = []
    for path in paths:
        resolved = Path(path).expanduser()
        key = str(resolved).lower()
        if key not in seen:
            seen.add(key)
            result.append(resolved)
    return result


def config_candidates():
    explicit = os.getenv("HYPERAGENT_CONFIG")
    if explicit:
        return [Path(explicit).expanduser()]

    package_root = Path(__file__).resolve().parents[1]
    server_root = Path(__file__).resolve().parents[2]
    return _unique_paths([
        Path.cwd() / CONFIG_FILENAME,
        package_root / CONFIG_FILENAME,
        server_root / CONFIG_FILENAME,
    ])


@lru_cache(maxsize=1)
def load_hyperagent_config():
    candidates = config_candidates()
    explicit = os.getenv("HYPERAGENT_CONFIG")

    for path in candidates:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError(f"{path} must contain a JSON object")
            return data

    if explicit:
        raise FileNotFoundError(f"HYPERAGENT_CONFIG not found: {explicit}")

    return {}


def parse_optional_limit(value, name="limit"):
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text or text.lower() in UNLIMITED_VALUES:
        return None
    try:
        limit = int(text)
    except ValueError:
        raise ValueError(f"{name} must be an integer or UNLIMITED, got {value!r}")
    if limit < 0:
        return None
    return limit


def get_configured_model(key, default):
    models = load_hyperagent_config().get("models", {})
    if not isinstance(models, dict):
        return default
    return models.get(key, default)


def get_max_output_tokens(default):
    config = load_hyperagent_config()
    defaults = config.get("defaults", {})
    value = None
    if isinstance(defaults, dict):
        value = defaults.get("max_output_tokens")
    if value is None:
        value = config.get("max_output_tokens")
    limit = parse_optional_limit(value, "defaults.max_output_tokens")
    return default if limit is None else limit


def get_usage_log_filename(default="llm_usage.jsonl"):
    config = load_hyperagent_config()
    usage = config.get("usage", {})
    if isinstance(usage, dict):
        filename = usage.get("log_filename")
        if filename:
            return str(filename)
    return default


def get_usage_log_path(default=None):
    config = load_hyperagent_config()
    usage = config.get("usage", {})
    value = None
    if isinstance(usage, dict):
        value = usage.get("log_path")
    if value is None:
        value = config.get("usage_log_path")
    return str(value) if value else default


def get_hosted_vllm_api_base(default=None):
    config = load_hyperagent_config()
    providers = config.get("providers", {})
    value = None
    if isinstance(providers, dict):
        value = providers.get("hosted_vllm_api_base")
    if value is None:
        value = config.get("hosted_vllm_api_base")
    return str(value) if value else default


def get_model_token_limits():
    limits = load_hyperagent_config().get("model_token_limits", {})
    if not isinstance(limits, dict):
        return {}

    parsed = {}
    for pattern, raw_limit in limits.items():
        limit = parse_optional_limit(raw_limit, f"model_token_limits[{pattern}]")
        if limit is not None:
            parsed[str(pattern)] = limit
    return parsed
