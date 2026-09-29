import json

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.ticket import Analysis, Category, Priority

SYSTEM_PROMPT = f"""You are a support desk assistant. Analyze the customer's message and reply with a single JSON object with exactly these keys:
- "category": one of {[c.value for c in Category]}
- "priority": one of {[p.value for p in Priority]}. Use "urgent" for outages or security issues, "high" for money problems or blocked users, "medium" for normal issues, "low" for questions and suggestions.
- "summary": one short sentence describing the issue.
- "reply_draft": a polite, concise reply to the customer from the support team, addressing them by name.
Write "summary" and "reply_draft" in the same language as the customer's message. Output only JSON."""


class LLMError(Exception):
    pass


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise LLMError("LLM response contains no JSON object")
    return json.loads(text[start : end + 1])


def _post(customer_name: str, message: str) -> httpx.Response:
    payload = {
        "model": settings.llm_model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Customer name: {customer_name}\n\nMessage:\n{message}"},
        ],
    }
    headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
    url = f"{settings.llm_base_url.rstrip('/')}/chat/completions"
    return httpx.post(url, json=payload, headers=headers, timeout=settings.llm_timeout_seconds)


def _parse(resp: httpx.Response) -> tuple[str, Analysis]:
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    data = _extract_json(content)
    data = {k: v.strip().lower() if k in ("category", "priority") and isinstance(v, str) else v
            for k, v in data.items()}
    return content, Analysis.model_validate(data)


_PARSE_ERRORS = (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError, LLMError)


def analyze_ticket(customer_name: str, message: str) -> Analysis:
    last_error: Exception | None = None
    for _ in range(2):
        try:
            return _parse(_post(customer_name, message))[1]
        except _PARSE_ERRORS as exc:
            last_error = exc
    raise LLMError(f"LLM analysis failed: {last_error}")


def check_llm() -> dict:
    """Single attempt with a sample ticket; always returns the raw provider output."""
    result: dict = {
        "ok": False,
        "base_url": settings.llm_base_url,
        "model": settings.llm_model,
        "http_status": None,
        "error": None,
        "raw_response": None,
        "content": None,
        "parsed": None,
    }
    try:
        resp = _post("Test User", "I was charged twice for my order #123 but received nothing.")
    except httpx.HTTPError as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    result["http_status"] = resp.status_code
    result["raw_response"] = resp.text
    try:
        content, analysis = _parse(resp)
        result["content"] = content
        result["parsed"] = analysis.model_dump(mode="json")
        result["ok"] = True
    except _PARSE_ERRORS as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        try:
            result["content"] = resp.json()["choices"][0]["message"]["content"]
        except Exception:
            pass
    return result
