import json

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.services import graph as graph_module
from app.services import llm as llm_module
from app.services.graph import resume_support_graph, run_support_graph
from app.services.knowledge_base import init_knowledge_base

KB = """## Возврат денежных средств
Деньги возвращаются на карту в течение 3–10 рабочих дней.

---

## Доставка
Срок доставки по Москве — 1–2 дня.
"""


def _analysis_json(reply: str = "Здравствуйте!") -> str:
    return json.dumps(
        {
            "category": "payment",
            "priority": "high",
            "summary": "Двойное списание",
            "reply_draft": reply,
        },
        ensure_ascii=False,
    )


def _decision_json(**overrides) -> str:
    data = {
        "escalate": False,
        "operator_question": None,
        "category": "payment",
        "priority": "high",
    }
    data.update(overrides)
    return json.dumps(data, ensure_ascii=False)


@pytest.fixture()
def kb_file(tmp_path):
    path = tmp_path / "kb.md"
    path.write_text(KB, encoding="utf-8")
    return str(path)


def _patch_models(monkeypatch, messages):
    fake = GenericFakeChatModel(messages=iter(messages))
    monkeypatch.setattr(graph_module, "_triage_model", lambda: fake)
    monkeypatch.setattr(llm_module, "get_chat_model", lambda *args, **kwargs: fake)
    return fake


def test_graph_resolves_with_knowledge_base(monkeypatch, kb_file):
    init_knowledge_base(kb_file)
    _patch_models(
        monkeypatch,
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_knowledge_base",
                        "args": {"query": "возврат денег"},
                        "id": "call_1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="Нашёл раздел о возврате средств."),
            AIMessage(content=_decision_json()),
            AIMessage(content=_analysis_json()),
        ],
    )

    run = run_support_graph("Иван", "Хочу вернуть деньги за заказ")

    assert run.escalation is None
    assert run.analysis is not None
    assert run.analysis.category == "payment"
    assert run.analysis.reply_draft == "Здравствуйте!"


def test_graph_escalates_and_resumes(monkeypatch, kb_file):
    init_knowledge_base(kb_file)
    fake = _patch_models(
        monkeypatch,
        [
            AIMessage(content="В базе знаний нет ответа на этот вопрос."),
            AIMessage(
                content=_decision_json(
                    escalate=True,
                    operator_question="Какой заказ имеется в виду?",
                )
            ),
            AIMessage(content=_analysis_json("Здравствуйте, Иван! Заказ отменён.")),
        ],
    )

    run = run_support_graph("Иван", "Мой заказ пропал, и никто не отвечает")

    assert run.analysis is None
    assert run.escalation is not None
    assert run.escalation.question == "Какой заказ имеется в виду?"
    assert run.escalation.category == "payment"
    assert run.escalation.priority == "high"

    analysis = resume_support_graph(run.thread_id, "Заказ №123")
    assert analysis.reply_draft == "Здравствуйте, Иван! Заказ отменён."


def test_graph_invalid_decision_json_raises(monkeypatch, kb_file):
    init_knowledge_base(kb_file)
    _patch_models(
        monkeypatch,
        [
            AIMessage(content="Готово."),
            AIMessage(content="не JSON"),
            AIMessage(content="опять не JSON"),
        ],
    )

    with pytest.raises(llm_module.LLMError):
        run_support_graph("Иван", "Тест")
