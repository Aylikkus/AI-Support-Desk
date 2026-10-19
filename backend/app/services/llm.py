"""LLM service.

LangChain owns everything provider-related: the chat-model connection
(OpenAI-compatible base URL), tool binding and JSON-mode responses. All of it
stays isolated behind this module; the rest of the app never touches providers.
"""

import json
from typing import TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.schemas.ticket import Analysis

TSchema = TypeVar("TSchema", bound=BaseModel)


class LLMError(Exception):
    pass


def get_chat_model(temperature: float = 0.2) -> BaseChatModel:
    """Chat model bound to the configured OpenAI-compatible provider."""
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key or None,
        base_url=settings.llm_base_url or None,
        temperature=temperature,
        timeout=settings.llm_timeout_seconds,
        max_retries=1,
    )


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


def ask_json(schema: type[TSchema], messages: list, temperature: float = 0.2) -> TSchema:
    """Invoke the chat model in JSON mode and validate the answer with a Pydantic schema (one retry)."""
    model = get_chat_model(temperature).bind(response_format={"type": "json_object"})
    last_error: Exception | None = None
    for _ in range(2):
        try:
            resp = model.invoke(messages)
            content = resp.content if isinstance(resp.content, str) else str(resp.content)
            return schema.model_validate(_extract_json(content))
        except (LLMError, json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
    raise LLMError(f"LLM response failed validation: {last_error}")


CHECK_SYSTEM = """Ты — ассистент службы поддержки. Проанализируй обращение клиента и ответь одним JSON-объектом с ключами:
- "category": одна из [payment, technical, account, delivery, product, other]
- "priority": одна из [low, medium, high, urgent]. urgent — сбой сервиса или проблема безопасности; high — деньги или заблокированный клиент; medium — обычные обращения; low — вопросы и предложения.
- "summary": одно короткое предложение, описывающее суть проблемы.
- "reply_draft": вежливый краткий ответ клиенту от лица службы поддержки.
Выведи только JSON."""

CHECK_SAMPLE = "Меня дважды списали оплату за заказ №123, но товар так и не пришёл."

_PARSE_ERRORS = (json.JSONDecodeError, ValidationError, LLMError)


def check_llm() -> dict:
    """Single attempt with a sample ticket; always returns the raw model output."""
    result: dict = {
        "ok": False,
        "base_url": settings.llm_base_url,
        "model": settings.llm_model,
        "error": None,
        "content": None,
        "parsed": None,
    }
    try:
        resp = get_chat_model().bind(response_format={"type": "json_object"}).invoke(
            [
                SystemMessage(CHECK_SYSTEM),
                HumanMessage(f"Имя клиента: Иван\n\nСообщение:\n{CHECK_SAMPLE}"),
            ]
        )
    except Exception as exc:  # provider/auth/network errors from the LangChain stack
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    content = resp.content if isinstance(resp.content, str) else str(resp.content)
    result["content"] = content
    try:
        data = _extract_json(content)
        data = {
            k: v.strip().lower() if k in ("category", "priority") and isinstance(v, str) else v
            for k, v in data.items()
        }
        result["parsed"] = Analysis.model_validate(data).model_dump(mode="json")
        result["ok"] = True
    except _PARSE_ERRORS as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result
