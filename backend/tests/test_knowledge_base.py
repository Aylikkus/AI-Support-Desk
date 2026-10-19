from app.services.knowledge_base import (
    KnowledgeBase,
    init_knowledge_base,
    search_knowledge_base,
)

KB = """## Возврат денежных средств
Деньги возвращаются на карту в течение 3–10 рабочих дней после отмены заказа.

---

## Доставка по Москве
Курьерская доставка по Москве занимает 1–2 рабочих дня, стоимость 299 руб.
"""


def test_load_splits_sections():
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "kb.md"
        path.write_text(KB, encoding="utf-8")
        kb = KnowledgeBase.load(str(path))

    assert [e.title for e in kb.entries] == ["Возврат денежных средств", "Доставка по Москве"]
    assert kb.entries[0].body.startswith("Деньги возвращаются")


def test_search_ranks_relevant_entry_first():
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "kb.md"
        path.write_text(KB, encoding="utf-8")
        kb = KnowledgeBase.load(str(path))

    hits = kb.search("как вернуть деньги за заказ")
    assert hits
    assert hits[0].title == "Возврат денежных средств"
    assert kb.search("абракадабра") == []


def test_tool_uses_initialized_base(tmp_path):
    path = tmp_path / "kb.md"
    path.write_text(KB, encoding="utf-8")
    init_knowledge_base(str(path))

    result = search_knowledge_base.invoke({"query": "возврат денег"})
    assert "Возврат денежных средств" in result


def test_tool_reports_no_hits(tmp_path):
    path = tmp_path / "kb.md"
    path.write_text(KB, encoding="utf-8")
    init_knowledge_base(str(path))

    assert "ничего не найдено" in search_knowledge_base.invoke({"query": "абракадабра"})
