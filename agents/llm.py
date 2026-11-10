"""Provider-agnostic LLM layer.

Chain: Gemini (primary) -> OpenRouter free model (fallback) -> Mock (last resort).
Every response is cached to disk so demo rehearsals never burn rate limits.
"""
import hashlib, json, os, re
import config


def _cache_key(system: str, user: str, provider: str) -> str:
    raw = f"{provider}|{system}|{user}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _cache_get(key):
    path = os.path.join(config.DATA_DIR, "llm_cache.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f).get(key)


def _cache_put(key, value):
    os.makedirs(config.DATA_DIR, exist_ok=True)
    path = os.path.join(config.DATA_DIR, "llm_cache.json")
    db = {}
    if os.path.exists(path):
        with open(path) as f:
            db = json.load(f)
    db[key] = value
    with open(path, "w") as f:
        json.dump(db, f)


def _extract_json(text: str) -> dict:
    """Robust JSON extraction: handles markdown fences + surrounding prose."""
    text = text.strip().removeprefix("```json").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


def _call_gemini(system: str, user: str) -> str:
    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(model=config.GEMINI_MODEL,
                                 google_api_key=config.GEMINI_API_KEY,
                                 temperature=0)
    return llm.invoke([{"role": "system", "content": system},
                       {"role": "user", "content": user}]).content


def _call_openrouter(system: str, user: str, model: str) -> str:
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model=model,
                     api_key=config.OPENROUTER_API_KEY,
                     base_url="https://openrouter.ai/api/v1",
                     temperature=0)
    return llm.invoke([{"role": "system", "content": system},
                       {"role": "user", "content": user}]).content


def chat_json(system_prompt: str, user_msg: str, agent_tag: str, ticker: str = "") -> dict:
    """Try providers in order with disk cache. Never raises: falls back to mock."""
    from orchestrator.graph import _mock_payload  # single source of mock truth

    user_full = user_msg + "\n\nRespond with STRICT JSON only."
    providers = []
    if config.LLM_PROVIDER in ("gemini", "auto") and config.GEMINI_API_KEY:
        providers.append(("gemini", config.GEMINI_MODEL))
    if config.LLM_PROVIDER in ("openrouter", "auto") and config.OPENROUTER_API_KEY:
        providers += [("openrouter", m) for m in config.OPENROUTER_FALLBACK_MODELS]

    for provider, model in providers:
        key = _cache_key(system_prompt, user_full, f"{provider}:{model}")
        cached = _cache_get(key)
        if cached is not None:
            return cached
        try:
            raw = _call_gemini(system_prompt, user_full) if provider == "gemini" \
                else _call_openrouter(system_prompt, user_full, model)
            data = _extract_json(raw)
            _cache_put(key, data)
            return data
        except Exception as e:
            print(f"[llm] {provider}:{model} failed -> next fallback. ({type(e).__name__})")
    return _mock_payload(agent_tag, ticker)
