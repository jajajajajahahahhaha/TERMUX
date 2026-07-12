"""Adaptive thinking: decide how deep the agent should reason about a task."""
import re

# Keywords that indicate complexity
COMPLEX_HINTS = [
    "analyze", "compare", "design", "build", "implement", "debug", "fix",
    "بررسی", "طراحی", "بساز", "دیباگ", "پیاده", "تحلیل", "مقایسه",
    "چرا", "چطور", "explain", "why", "how",
]
SEARCH_HINTS = [
    "latest", "news", "today", "current", "قیمت", "الان", "امروز", "خبر",
    "اخبار", "current", "recent",
]
CODE_HINTS = [
    "code", "script", "function", "کد", "اسکریپت", "برنامه", "python", "bash",
    "run", "execute", "اجرا",
]


def analyze_question(question: str) -> dict:
    """Return a hint bundle for the LLM's system prompt."""
    q = question.lower()
    complexity = 1  # 1=simple, 2=medium, 3=deep

    hits_complex = sum(1 for kw in COMPLEX_HINTS if kw in q)
    hits_search = any(kw in q for kw in SEARCH_HINTS)
    hits_code = any(kw in q for kw in CODE_HINTS)

    if hits_complex >= 2 or len(question) > 300:
        complexity = 3
    elif hits_complex >= 1 or hits_code or len(question) > 100:
        complexity = 2

    max_tool_steps = {1: 3, 2: 6, 3: 10}[complexity]
    return {
        "complexity": complexity,
        "likely_needs_search": hits_search,
        "likely_needs_code": hits_code,
        "max_tool_steps": max_tool_steps,
    }


def thinking_hint(analysis: dict) -> str:
    """Text to inject as a system message describing depth budget."""
    c = analysis["complexity"]
    label = {1: "SIMPLE", 2: "MEDIUM", 3: "DEEP"}[c]
    return (
        f"[Adaptive Thinking] Estimated complexity: {label}. "
        f"You have a budget of up to {analysis['max_tool_steps']} tool calls. "
        f"For SIMPLE questions, answer directly. For DEEP questions, plan step by step."
    )
