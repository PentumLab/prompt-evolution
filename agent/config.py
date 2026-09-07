import json
import os
from functools import lru_cache
from pathlib import Path


CONFIG_FILENAME = "hyperagent_config.json"
UNLIMITED_VALUES = {"-1", "unlimited", "none", "off", "false", "no"}
DEFAULT_VALUES = {"default", "inherit"}
USE_DEFAULT_LIMIT = object()


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


def parse_output_token_limit(value, name="limit", allow_default=False):
    if value in (None, ""):
        if allow_default:
            return USE_DEFAULT_LIMIT
        raise ValueError(f"{name} must be configured")

    text = str(value).strip()
    if not text:
        if allow_default:
            return USE_DEFAULT_LIMIT
        raise ValueError(f"{name} must be configured")

    lowered = text.lower()
    if lowered in DEFAULT_VALUES:
        if allow_default:
            return USE_DEFAULT_LIMIT
        raise ValueError(f"{name} cannot use DEFAULT here")
    if lowered in UNLIMITED_VALUES:
        return None

    try:
        limit = int(text)
    except ValueError:
        raise ValueError(
            f"{name} must be an integer, DEFAULT, or UNLIMITED, got {value!r}"
        )
    if limit < 0:
        return None
    return limit


def parse_tool_call_limit(value, name="limit", allow_default=False):
    if value in (None, ""):
        if allow_default:
            return USE_DEFAULT_LIMIT
        raise ValueError(f"{name} must be configured")

    text = str(value).strip()
    if not text:
        if allow_default:
            return USE_DEFAULT_LIMIT
        raise ValueError(f"{name} must be configured")

    lowered = text.lower()
    if lowered in DEFAULT_VALUES:
        if allow_default:
            return USE_DEFAULT_LIMIT
        raise ValueError(f"{name} cannot use DEFAULT here")
    if lowered in UNLIMITED_VALUES:
        return -1

    try:
        limit = int(text)
    except ValueError:
        raise ValueError(
            f"{name} must be an integer, DEFAULT, or UNLIMITED, got {value!r}"
        )
    if limit < 0:
        return -1
    return limit


def _normalize_model(model):
    return str(model or "").strip().lower()


def _model_matches(model, pattern):
    model = _normalize_model(model)
    pattern = _normalize_model(pattern)
    if not pattern:
        return False
    if pattern.endswith("*"):
        return model.startswith(pattern[:-1])
    return model == pattern or pattern in model


def get_configured_model(key, default):
    models = load_hyperagent_config().get("models", {})
    if not isinstance(models, dict):
        return default
    return models.get(key, default)


def get_max_output_tokens():
    config = load_hyperagent_config()
    defaults = config.get("defaults", {})
    value = None
    if isinstance(defaults, dict):
        value = defaults.get("max_output_tokens")
    if value is None:
        value = config.get("max_output_tokens")
    return parse_output_token_limit(value, "defaults.max_output_tokens")


def get_max_tool_calls():
    config = load_hyperagent_config()
    defaults = config.get("defaults", {})
    value = None
    if isinstance(defaults, dict):
        value = defaults.get("max_tool_calls")
    if value is None:
        value = config.get("max_tool_calls")
    return parse_tool_call_limit(value, "defaults.max_tool_calls")


def get_agent_max_output_tokens(agent_key):
    config = load_hyperagent_config()
    agent_limits = config.get("agent_max_output_tokens", {})
    if isinstance(agent_limits, dict) and agent_key in agent_limits:
        limit = parse_output_token_limit(
            agent_limits.get(agent_key),
            f"agent_max_output_tokens[{agent_key}]",
            allow_default=True,
        )
        return get_max_output_tokens() if limit is USE_DEFAULT_LIMIT else limit
    return get_max_output_tokens()


def get_agent_max_tool_calls(agent_key):
    config = load_hyperagent_config()
    agent_limits = config.get("agent_max_tool_calls", {})
    if isinstance(agent_limits, dict) and agent_key in agent_limits:
        limit = parse_tool_call_limit(
            agent_limits.get(agent_key),
            f"agent_max_tool_calls[{agent_key}]",
            allow_default=True,
        )
        return get_max_tool_calls() if limit is USE_DEFAULT_LIMIT else limit
    return get_max_tool_calls()


def get_model_max_output_tokens(model):
    limits = load_hyperagent_config().get("model_max_output_tokens", {})
    if not isinstance(limits, dict):
        return None

    for pattern, raw_limit in limits.items():
        if _model_matches(model, pattern):
            limit = parse_output_token_limit(
                raw_limit,
                f"model_max_output_tokens[{pattern}]",
                allow_default=True,
            )
            return get_max_output_tokens() if limit is USE_DEFAULT_LIMIT else limit
    return None


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
