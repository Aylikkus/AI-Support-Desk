"""LangGraph support graph.

LangChain owns the model connection, tool binding and JSON-mode parsing
(services.llm); LangGraph owns the graph, the tool loop and the
human-in-the-loop interrupt. Graph:

    START → triage ─(tool calls?)→ tools → triage …
           triage ─→ decide ─(escalate?)→ human (interrupt, waits for the
                                    operator's answer) → finalize → END
                   decide ─→ finalize → END

The graph state is checkpointed per ticket thread (Postgres in production,
MemorySaver for SQLite/tests), so a ticket paused for an operator survives
restarts and can be resumed later with the operator's answer.
"""

import json
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Annotated, Any

from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt
from typing_extensions import TypedDict

from app.core.config import settings
from app.schemas.ticket import Analysis, TriageDecision
from app.services import llm as llm_service
from app.services.knowledge_base import search_knowledge_base

MAX_TRIAGE_STEPS = 4


class SupportGraphError(Exception):
    pass


TRIAGE_SYSTEM = """Ты — автоматический ассистент службы поддержки интернет-магазина.
У тебя есть инструмент search_knowledge_base для поиска по базе знаний службы поддержки.
Алгоритм:
1. Если для ответа нужны факты, вызови search_knowledge_base с запросом по сути обращения клиента.
2. Кратко сформулируй, что удалось выяснить (или что в базе знаний нет ответа).
Отвечай на русском языке. Не придумывай факты, которых нет в базе знаний."""

DECIDE_SYSTEM = """Ты — старший специалист службы поддержки. На основе диалога ассистента
прими решение по обращению клиента и ответь одним JSON-объектом с ключами:
- "escalate": true, если вопрос нельзя решить автоматически (в базе знаний нет ответа, нужна проверка человеком, задета судьба заказа или денег), иначе false.
- "operator_question": конкретный вопрос оператору-человеку; обязателен, если escalate=true.
- "category": одна из [payment, technical, account, delivery, product, other].
- "priority": одна из [low, medium, high, urgent]. urgent — сбой сервиса или проблема безопасности; high — деньги или заблокированный клиент; medium — обычные обращения; low — вопросы и предложения.
Выведи только JSON."""

FINALIZE_SYSTEM = """Ты — сотрудник службы поддержки. Составь итоговое решение по обращению клиента
и ответь одним JSON-объектом с ключами:
- "category": одна из [payment, technical, account, delivery, product, other].
- "priority": одна из [low, medium, high, urgent].
- "summary": одно короткое предложение с сутью проблемы клиента.
- "reply_draft": вежливый и конкретный ответ клиенту на русском языке; обращайся к нему по имени;
  используй только факты из базы знаний (диалог ассистента) и ответ оператора, если он есть.
Выведи только JSON."""


class GraphState(TypedDict):
    customer_name: str
    message: str
    messages: Annotated[list[AnyMessage], add_messages]
    triage_steps: int
    decision: dict[str, Any] | None
    operator_answer: str | None
    analysis: dict[str, Any] | None


@dataclass(frozen=True)
class Escalation:
    question: str
    category: str | None = None
    priority: str | None = None


@dataclass(frozen=True)
class GraphRunResult:
    thread_id: str
    analysis: Analysis | None
    escalation: Escalation | None


def _triage_model():
    return llm_service.get_chat_model().bind_tools([search_knowledge_base])


def triage_node(state: GraphState) -> dict:
    response = _triage_model().invoke(state["messages"])
    return {"messages": [response], "triage_steps": state.get("triage_steps", 0) + 1}


def route_after_triage(state: GraphState) -> str:
    last = state["messages"][-1]
    has_tool_calls = bool(getattr(last, "tool_calls", None))
    if has_tool_calls and state.get("triage_steps", 0) < MAX_TRIAGE_STEPS:
        return "tools"
    return "decide"


def _render_messages(messages: list[AnyMessage]) -> str:
    roles = {"system": "Система", "human": "Клиент", "ai": "Ассистент", "tool": "База знаний"}
    parts: list[str] = []
    for msg in messages:
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            calls = "; ".join(
                f"{call['name']}({json.dumps(call['args'], ensure_ascii=False)})" for call in tool_calls
            )
            content = f"{content} [вызов инструмента: {calls}]".strip()
        parts.append(f"{roles.get(msg.type, msg.type)}: {content}")
    return "\n".join(parts)


def decide_node(state: GraphState) -> dict:
    human = (
        f"Имя клиента: {state['customer_name']}\n\n"
        f"Сообщение клиента:\n{state['message']}\n\n"
        f"Диалог ассистента:\n{_render_messages(state['messages'])}\n\n"
        "Прими решение (только JSON)."
    )
    decision = llm_service.ask_json(TriageDecision, [SystemMessage(DECIDE_SYSTEM), HumanMessage(human)])
    return {"decision": decision.model_dump()}


def route_after_decide(state: GraphState) -> str:
    decision = state.get("decision") or {}
    return "human" if decision.get("escalate") else "finalize"


def human_node(state: GraphState) -> dict:
    decision = state.get("decision") or {}
    payload = {
        "question": decision.get("operator_question"),
        "category": decision.get("category"),
        "priority": decision.get("priority"),
    }
    answer = interrupt(payload)
    return {"operator_answer": answer}


def finalize_node(state: GraphState) -> dict:
    parts = [
        f"Имя клиента: {state['customer_name']}",
        f"Сообщение клиента:\n{state['message']}",
        f"Диалог ассистента:\n{_render_messages(state['messages'])}",
    ]
    if state.get("operator_answer"):
        parts.append(f"Ответ оператора-человека:\n{state['operator_answer']}")
    analysis = llm_service.ask_json(
        Analysis, [SystemMessage(FINALIZE_SYSTEM), HumanMessage("\n\n".join(parts))]
    )
    return {"analysis": analysis.model_dump()}


def build_support_graph() -> StateGraph:
    builder = StateGraph(GraphState)
    builder.add_node("triage", triage_node)
    builder.add_node("tools", ToolNode([search_knowledge_base]))
    builder.add_node("decide", decide_node)
    builder.add_node("human", human_node)
    builder.add_node("finalize", finalize_node)
    builder.add_edge(START, "triage")
    builder.add_conditional_edges("triage", route_after_triage, {"tools": "tools", "decide": "decide"})
    builder.add_edge("tools", "triage")
    builder.add_conditional_edges("decide", route_after_decide, {"human": "human", "finalize": "finalize"})
    builder.add_edge("human", "finalize")
    builder.add_edge("finalize", END)
    return builder


def _psycopg_url() -> str:
    return settings.database_url.replace("postgresql+psycopg", "postgresql", 1)


def _using_sqlite() -> bool:
    return settings.database_url.startswith("sqlite")


_memory_checkpointer: MemorySaver | None = None


def init_graph_runtime() -> None:
    """Called once on startup: create the LangGraph checkpoint tables (Postgres only).

    LangGraph provisions its own tables (checkpoints, writes) via checkpointer.setup();
    they are framework-managed and live separately from the Alembic-managed app schema.
    """
    if _using_sqlite():
        return
    with PostgresSaver.from_conn_string(_psycopg_url()) as checkpointer:
        checkpointer.setup()


@contextmanager
def _compiled_graph():
    """A compiled graph with a checkpointer; one fresh Postgres connection per run
    (sync PostgresSaver connections are single-threaded, FastAPI runs sync work in a threadpool)."""
    if _using_sqlite():
        global _memory_checkpointer
        if _memory_checkpointer is None:
            _memory_checkpointer = MemorySaver()
        yield build_support_graph().compile(checkpointer=_memory_checkpointer)
    else:
        with PostgresSaver.from_conn_string(_psycopg_url()) as checkpointer:
            yield build_support_graph().compile(checkpointer=checkpointer)


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _to_run_result(thread_id: str, result: dict) -> GraphRunResult:
    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        return GraphRunResult(
            thread_id=thread_id,
            analysis=None,
            escalation=Escalation(
                question=payload["question"],
                category=payload.get("category"),
                priority=payload.get("priority"),
            ),
        )
    analysis = result.get("analysis")
    if analysis is None:
        raise SupportGraphError("graph finished without a final analysis")
    return GraphRunResult(thread_id=thread_id, analysis=Analysis.model_validate(analysis), escalation=None)


def run_support_graph(customer_name: str, message: str) -> GraphRunResult:
    """Run the support graph for a new ticket. A fresh thread is used for every run,
    so reanalysis never resumes a stale interrupted state."""
    thread_id = f"ticket-{uuid.uuid4().hex}"
    initial: GraphState = {
        "customer_name": customer_name,
        "message": message,
        "messages": [
            SystemMessage(TRIAGE_SYSTEM),
            HumanMessage(f"Имя клиента: {customer_name}\n\nСообщение:\n{message}"),
        ],
        "triage_steps": 0,
    }
    with _compiled_graph() as graph:
        result = graph.invoke(initial, config=_config(thread_id))
    return _to_run_result(thread_id, result)


def resume_support_graph(thread_id: str, answer: str) -> Analysis:
    """Resume a paused (interrupted) graph with the operator's answer."""
    with _compiled_graph() as graph:
        result = graph.invoke(Command(resume=answer), config=_config(thread_id))
    if "__interrupt__" in result:
        raise SupportGraphError("graph is still waiting for an operator answer")
    analysis = result.get("analysis")
    if analysis is None:
        raise SupportGraphError("graph finished without a final analysis")
    return Analysis.model_validate(analysis)
