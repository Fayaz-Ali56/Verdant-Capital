"""Optional evidence-grounded LLM calls with explicit failure reporting.

If a provider is missing/unavailable, the caller receives None and must use
an openly labeled deterministic fallback. Never silently synthesize ESG facts.
"""

import hashlib
import json
import re
from pathlib import Path

import config
from data.files import write_json


def _parse_json(text):
    if not isinstance(text, str):
        raise ValueError("Model output is not text")
    value = text.strip()
    if value.startswith("```json"):
        value = value[7:].strip()
    if value.startswith("```"):
        value = value[3:].strip()
    if value.endswith("```"):
        value = value[:-3].strip()
    try:
        result = json.loads(value)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", value, re.DOTALL)
        if not match:
            raise
        result = json.loads(match.group(0))
    if not isinstance(result, dict):
        raise ValueError("Expected JSON object")
    return result


def chat_json(system_prompt, user_message, purpose="esg"):
    """Returns (payload | None, provenance), never fabricated substitute content."""
    provider = config.LLM_PROVIDER
    choices = []
    if provider in {"auto", "gemini"} and config.GEMINI_API_KEY:
        choices.append(("gemini", config.GEMINI_MODEL))
    if provider in {"auto", "openrouter"} and config.OPENROUTER_API_KEY:
        choices.append(("openrouter", config.OPENROUTER_MODEL))
    if not choices:
        return None, "not_configured"
    key = hashlib.sha256(
        (purpose + system_prompt + user_message + str(choices)).encode()
    ).hexdigest()
    cache = Path(config.DATA_DIR) / "llm_cache"
    cache_file = cache / f"{key}.json"
    if cache_file.is_file():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8")), "cache"
        except (ValueError, OSError):
            pass
    for backend, model in choices:
        try:
            if backend == "gemini":
                from langchain_google_genai import ChatGoogleGenerativeAI

                llm = ChatGoogleGenerativeAI(
                    model=model,
                    google_api_key=config.GEMINI_API_KEY,
                    temperature=0,
                    timeout=20,
                    max_retries=1,
                )
            else:
                from langchain_openai import ChatOpenAI

                llm = ChatOpenAI(
                    model=model,
                    api_key=config.OPENROUTER_API_KEY,
                    base_url="https://openrouter.ai/api/v1",
                    temperature=0,
                    timeout=20,
                    max_retries=1,
                )
            content = llm.invoke(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ]
            ).content
            result = _parse_json(content)
            write_json(cache_file, result)
            return result, backend
        except Exception as e:
            # Do not print model output, retrieved documents or keys to stderr.
            print(f"[llm] {backend} unavailable: {type(e).__name__}; trying backup")
    return None, "unavailable"
