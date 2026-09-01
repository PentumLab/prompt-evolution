import backoff
import os
from typing import Tuple
import requests
import litellm
from dotenv import load_dotenv
import json
from agent.config import (
    get_configured_model,
    get_hosted_vllm_api_base,
    get_max_output_tokens,
)
from agent.usage import check_token_budget, log_usage

load_dotenv()

MAX_TOKENS = 16384
MAX_META_TOKENS = 4000

CLAUDE_MODEL = "anthropic/claude-sonnet-4-5-20250929"
CLAUDE_HAIKU_MODEL = "anthropic/claude-3-haiku-20240307"
CLAUDE_35NEW_MODEL = "anthropic/claude-3-5-sonnet-20241022"
OPENAI_MODEL = "openai/gpt-4o"
OPENAI_MINI_MODEL = "openai/gpt-4o-mini"
OPENAI_O3_MODEL = "openai/o3"
OPENAI_O3MINI_MODEL = "openai/o3-mini"
OPENAI_O4MINI_MODEL = "openai/o4-mini"
OPENAI_GPT52_MODEL = "openai/gpt-5.2"
OPENAI_GPT5_MODEL = "openai/gpt-5"
OPENAI_GPT5MINI_MODEL = "openai/gpt-5-mini"
GEMINI_3_MODEL = "gemini/gemini-3-pro-preview"
GEMINI_MODEL = "gemini/gemini-2.5-pro"
GEMINI_FLASH_MODEL = "gemini/gemini-2.5-flash"
GEMMA_MODEL = get_configured_model("prompt_design_task_agent", "hosted_vllm/gemma-4")
CLAUDE_HAIKU_45_MODEL = get_configured_model("meta_agent", "anthropic/claude-haiku-4-5-20251001")


litellm.drop_params=True

@backoff.on_exception(
    backoff.expo,
    (requests.exceptions.RequestException, json.JSONDecodeError, KeyError),
    max_time=600,
    max_value=60,
)
def get_response_from_llm(
    msg: str,
    model: str = OPENAI_MODEL,
    temperature: float = 0.0,
    max_tokens: int = None,
    msg_history=None,
    system_prompt: str = None,
) -> Tuple[str, list, dict]:
    if msg_history is None:
        msg_history = []
    if max_tokens is None:
        max_tokens = get_max_output_tokens(MAX_TOKENS)

    # Convert text to content, compatible with LITELLM API
    msg_history = [
        {**msg, "content": msg.pop("text")} if "text" in msg else msg
        for msg in msg_history
    ]

    #new_msg_history = msg_history + [{"role": "user", "content": msg}]
    new_msg_history = []

    if system_prompt:
        new_msg_history.append(
            {"role": "system", "content": system_prompt}
        )

    new_msg_history += msg_history
    new_msg_history.append(
        {"role": "user", "content": msg}
    )

    # Build kwargs - handle model-specific requirements
    completion_kwargs = {
        "model": model,
        "messages": new_msg_history,
    }

    if model.startswith("hosted_vllm/"):
        api_base = get_hosted_vllm_api_base()
        if api_base:
            completion_kwargs["api_base"] = api_base

    # GPT-5 and GPT-5-mini only support default temperature (1), skip it
    # GPT-5.2 supports temperature
    if model in ["openai/gpt-5", "openai/gpt-5-mini"]:
        pass  # Don't set temperature
    else:
        completion_kwargs["temperature"] = temperature

    # GPT-5 models require max_completion_tokens instead of max_tokens
    if "gpt-5" in model:
        completion_kwargs["max_completion_tokens"] = max_tokens
    else:
        # Claude Haiku has a 4096 token limit
        if "claude-3-haiku" in model:
            completion_kwargs["max_tokens"] = min(max_tokens, 4096)
        else:
            completion_kwargs["max_tokens"] = max_tokens

    check_token_budget(model)
    response = litellm.completion(**completion_kwargs)
    response_text = response['choices'][0]['message']['content']  # pyright: ignore
    usage_info = log_usage(
        response,
        model=model,
        input_messages=completion_kwargs["messages"],
        output_text=response_text,
    )
    new_msg_history.append({"role": "assistant", "content": response['choices'][0]['message']['content']})

    # Convert content to text, compatible with MetaGen API
    new_msg_history = [
        {**msg, "text": msg.pop("content")} if "content" in msg else msg
        for msg in new_msg_history
    ]

    return response_text, new_msg_history, {"usage": usage_info}


if __name__ == "__main__":
    msg = 'Hello there!'
    models = [
        ("CLAUDE_MODEL", CLAUDE_MODEL),
        ("CLAUDE_HAIKU_MODEL", CLAUDE_HAIKU_MODEL),
        ("CLAUDE_35NEW_MODEL", CLAUDE_35NEW_MODEL),
        ("OPENAI_MODEL", OPENAI_MODEL),
        ("OPENAI_MINI_MODEL", OPENAI_MINI_MODEL),
        ("OPENAI_O3_MODEL", OPENAI_O3_MODEL),
        ("OPENAI_O3MINI_MODEL", OPENAI_O3MINI_MODEL),
        ("OPENAI_O4MINI_MODEL", OPENAI_O4MINI_MODEL),
        ("OPENAI_GPT52_MODEL", OPENAI_GPT52_MODEL),
        ("OPENAI_GPT5_MODEL", OPENAI_GPT5_MODEL),
        ("OPENAI_GPT5MINI_MODEL", OPENAI_GPT5MINI_MODEL),
        ("GEMINI_3_MODEL", GEMINI_3_MODEL),
        ("GEMINI_MODEL", GEMINI_MODEL),
        ("GEMINI_FLASH_MODEL", GEMINI_FLASH_MODEL),
    ]
    for name, model in models:
        print(f"\n{'='*50}")
        print(f"Testing {name}: {model}")
        print('='*50)
        try:
            output_msg, msg_history, info = get_response_from_llm(msg, model=model)
            print(f"OK: {output_msg[:100]}...")
        except Exception as e:
            print(f"FAIL: {str(e)[:200]}")
