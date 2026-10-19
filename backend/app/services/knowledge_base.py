"""Knowledge base: a configurable plain-text file, loaded once on startup.

The file is split into sections by standalone "---" lines; the first line of a
section is its title, the rest is the body. Search is a small keyword index
(ranked by token overlap) — intentionally simple, swappable for a vector store
later behind the same KnowledgeBase interface.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from langchain_core.tools import tool

from app.core.config import settings

_WORD_RE = re.compile(r"\w+", re.UNICODE)
_SECTION_SPLIT_RE = re.compile(r"^\s*---\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Entry:
    title: str
    body: str
    tokens: frozenset[str]


def _tokenize(text: str) -> frozenset[str]:
    return frozenset(match.group(0) for match in _WORD_RE.finditer(text.lower()))


class KnowledgeBase:
    """A tiny keyword-search index over the sections of a text file."""

    def __init__(self, entries: list[Entry]) -> None:
        self.entries = entries

    @classmethod
    def load(cls, path: str) -> "KnowledgeBase":
        raw = Path(path).read_text(encoding="utf-8")
        entries: list[Entry] = []
        for section in _SECTION_SPLIT_RE.split(raw):
            section = section.strip()
            if not section:
                continue
            lines = section.splitlines()
            title = lines[0].lstrip("#").strip()
            body = "\n".join(lines[1:]).strip()
            entries.append(Entry(title=title, body=body, tokens=_tokenize(f"{title} {body}")))
        return cls(entries)

    def search(self, query: str, top_k: int = 3) -> list[Entry]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []
        scored = [(len(entry.tokens & query_tokens), index, entry) for index, entry in enumerate(self.entries)]
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [entry for score, _, entry in scored if score > 0][:top_k]


_kb: KnowledgeBase | None = None


def init_knowledge_base(path: str | None = None) -> KnowledgeBase:
    """Load the knowledge base from the configured file; called on app startup."""
    global _kb
    _kb = KnowledgeBase.load(path or settings.knowledge_base_path)
    return _kb


def get_knowledge_base() -> KnowledgeBase:
    """Current knowledge base; lazily loaded if startup init was skipped."""
    global _kb
    if _kb is None:
        _kb = init_knowledge_base()
    return _kb


@tool
def search_knowledge_base(query: str) -> str:
    """Поиск по базе знаний службы поддержки. Возвращает самые релевантные разделы по запросу клиента."""
    hits = get_knowledge_base().search(query)
    if not hits:
        return "По запросу ничего не найдено в базе знаний."
    return "\n\n".join(f"[{hit.title}]\n{hit.body}" for hit in hits)
