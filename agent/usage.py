import json
import os
import threading
import time
from contextlib import contextmanager
from math import ceil
from pathlib import Path

from agent.config import (
    get_model_token_limits,
    get_usage_log_filename,
    get_usage_log_path,
    parse_optional_limit,
)


_local = threading.local()
_lock = threading.Lock()


class TokenBudgetExceeded(RuntimeError):
    pass


def _truthy(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _split_patterns(value):
    return [x.strip() for x in str(value or "").split(",") if x.strip()]


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


def set_usage_context(log_path=None, agent_role=None, metadata=None):
    _local.log_path = str(log_path) if log_path else None
    _local.agent_role = agent_role
    _local.metadata = metadata or {}


@contextmanager
def usage_context(log_path=None, agent_role=None, metadata=None):
    old = (
        getattr(_local, "log_path", None),
        getattr(_local, "agent_role", None),
        getattr(_local, "metadata", {}),
    )
    set_usage_context(log_path=log_path, agent_role=agent_role, metadata=metadata)
    try:
        yield
    finally:
        _local.log_path, _local.agent_role, _local.metadata = old


def default_usage_log_path():
    explicit = os.getenv("HYPERAGENT_USAGE_LOG") or get_usage_log_path()
    if explicit:
        return Path(explicit).expanduser()

    context_path = getattr(_local, "log_path", None)
    if context_path:
        return Path(context_path).expanduser()

    return Path("./outputs") / get_usage_log_filename()


def usage_log_path_for_chat_history(chat_history_file):
    explicit = os.getenv("HYPERAGENT_USAGE_LOG") or get_usage_log_path()
    if explicit:
        return Path(explicit).expanduser()
    chat_path = Path(chat_history_file).expanduser()
    return chat_path.parent / get_usage_log_filename()


def _get_value(obj, *names):
    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj.get(name)
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def extract_usage(response):
    usage = _get_value(response, "usage")
    if usage is None:
        return {
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "raw_usage": None,
        }

    input_tokens = _get_value(usage, "input_tokens", "prompt_tokens")
    output_tokens = _get_value(usage, "output_tokens", "completion_tokens")
    total_tokens = _get_value(usage, "total_tokens")

    try:
        input_tokens = int(input_tokens) if input_tokens is not None else None
    except Exception:
        input_tokens = None
    try:
        output_tokens = int(output_tokens) if output_tokens is not None else None
    except Exception:
        output_tokens = None
    try:
        total_tokens = int(total_tokens) if total_tokens is not None else None
    except Exception:
        total_tokens = None

    if total_tokens is None and input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens

    if hasattr(usage, "model_dump"):
        raw_usage = usage.model_dump()
    elif hasattr(usage, "dict"):
        raw_usage = usage.dict()
    elif isinstance(usage, dict):
        raw_usage = dict(usage)
    else:
        raw_usage = {
            k: _get_value(usage, k)
            for k in ("prompt_tokens", "completion_tokens", "total_tokens", "input_tokens", "output_tokens")
            if _get_value(usage, k) is not None
        }

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "raw_usage": raw_usage,
    }


def _messages_char_length(messages):
    total = 0
    for message in messages or []:
        if isinstance(message, dict):
            content = message.get("content") or message.get("text") or ""
        else:
            content = str(message)
        total += len(str(content))
    return total


def _rough_token_estimate_from_chars(char_count):
    if char_count <= 0:
        return None
    return max(1, int(ceil(char_count / 4)))


def estimate_tokens(model, input_messages=None, output_text=None):
    input_tokens = None
    output_tokens = None

    try:
        import litellm

        if input_messages:
            input_tokens = int(litellm.token_counter(model=model, messages=input_messages))
        if output_text:
            output_tokens = int(litellm.token_counter(model=model, text=output_text))
    except Exception:
        input_tokens = None
        output_tokens = None

    if input_tokens is None:
        input_tokens = _rough_token_estimate_from_chars(_messages_char_length(input_messages))
    if output_tokens is None:
        output_tokens = _rough_token_estimate_from_chars(len(str(output_text or "")))

    total_tokens = None
    if input_tokens is not None and output_tokens is not None:
        total_tokens = input_tokens + output_tokens

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def _parse_pattern_limits(name):
    value = os.getenv(name, "").strip()
    if not value:
        return {}
    if value.startswith("{"):
        data = json.loads(value)
        limits = {}
        for key, raw_limit in data.items():
            limit = parse_optional_limit(raw_limit, f"{name}[{key}]")
            if limit is not None:
                limits[str(key)] = limit
        return limits

    limits = {}
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(
                f"{name} must use 'pattern=limit' entries"
            )
        key, raw_limit = part.split("=", 1)
        limit = parse_optional_limit(raw_limit.strip(), f"{name}[{key.strip()}]")
        if limit is not None:
            limits[key.strip()] = limit
    return limits


def _parse_model_limits():
    limits = get_model_token_limits()
    env_limits = _parse_pattern_limits("HYPERAGENT_MODEL_TOKEN_LIMITS")
    return {**limits, **env_limits}


def _read_usage_records(path):
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _token_total(record):
    value = record.get("total_tokens")
    if value is None:
        input_tokens = record.get("input_tokens")
        output_tokens = record.get("output_tokens")
        if input_tokens is not None and output_tokens is not None:
            value = int(input_tokens) + int(output_tokens)
    try:
        return int(value or 0)
    except Exception:
        return 0


def summarize_usage(path=None):
    path = Path(path).expanduser() if path else default_usage_log_path()
    records = _read_usage_records(path)
    summary = {
        "all_tokens": 0,
        "by_model": {},
        "by_role": {},
    }
    for record in records:
        tokens = _token_total(record)
        model = record.get("model") or "unknown"
        role = record.get("agent_role") or "unknown"
        summary["all_tokens"] += tokens
        summary["by_model"][model] = summary["by_model"].get(model, 0) + tokens
        summary["by_role"][role] = summary["by_role"].get(role, 0) + tokens
    return summary


def current_agent_role():
    return getattr(_local, "agent_role", None) or os.getenv("HYPERAGENT_AGENT_ROLE") or "llm_call"


def _check_budget_for_model(model, path):
    if _truthy(os.getenv("HYPERAGENT_DISABLE_TOKEN_BUDGETS")):
        return

    summary = summarize_usage(path)

    model_limits = _parse_model_limits()
    for pattern, limit in model_limits.items():
        if _model_matches(model, pattern):
            used = sum(
                tokens
                for logged_model, tokens in summary["by_model"].items()
                if _model_matches(logged_model, pattern)
            )
            if used >= limit:
                raise TokenBudgetExceeded(
                    f"Token budget exceeded for {pattern}: {used} >= {limit}"
                )


def check_token_budget(model):
    path = default_usage_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        _check_budget_for_model(model, path)


def log_usage(response, model, call_kind="completion", input_messages=None, output_text=None, extra=None):
    path = default_usage_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    usage = extract_usage(response)
    estimated = False
    if usage["total_tokens"] is None:
        estimate = estimate_tokens(
            model,
            input_messages=input_messages,
            output_text=output_text,
        )
        usage.update(estimate)
        estimated = True
    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pid": os.getpid(),
        "thread_id": threading.get_ident(),
        "agent_role": current_agent_role(),
        "call_kind": call_kind,
        "model": model,
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "total_tokens": usage["total_tokens"],
        "raw_usage": usage["raw_usage"],
        "estimated": estimated,
    }
    context_metadata = getattr(_local, "metadata", {}) or {}
    if context_metadata:
        record["context"] = context_metadata
    if extra:
        record.update(extra)

    with _lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record
