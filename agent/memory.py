"""Chat memory: persistent JSON + auto-summarization when it gets long."""
import json
import os
from pathlib import Path
from typing import List, Dict

MEMORY_FILE = Path(__file__).parent.parent / "memory" / "chat_history.json"
MAX_TURNS_BEFORE_SUMMARY = 20  # every 20 messages, summarize the oldest half


def _ensure_file():
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not MEMORY_FILE.exists():
        MEMORY_FILE.write_text(json.dumps({"messages": [], "summary": ""}, ensure_ascii=False, indent=2))


def load_history() -> Dict:
    _ensure_file()
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"messages": [], "summary": ""}


def save_history(data: Dict):
    _ensure_file()
    MEMORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def add_message(role: str, content: str):
    data = load_history()
    data["messages"].append({"role": role, "content": content})
    save_history(data)


def build_context_messages(system_prompt: str) -> List[Dict[str, str]]:
    """Build messages list for LLM call, including summary if any."""
    data = load_history()
    msgs = [{"role": "system", "content": system_prompt}]
    if data.get("summary"):
        msgs.append({
            "role": "system",
            "content": f"[Previous conversation summary]\n{data['summary']}"
        })
    msgs.extend(data["messages"])
    return msgs


def maybe_summarize(llm_client):
    """If history is too long, summarize the older half."""
    data = load_history()
    if len(data["messages"]) <= MAX_TURNS_BEFORE_SUMMARY:
        return
    half = len(data["messages"]) // 2
    old = data["messages"][:half]
    keep = data["messages"][half:]

    convo_text = "\n".join(f"{m['role']}: {m['content']}" for m in old)
    prompt = [
        {"role": "system", "content": "You are a summarizer. Compress the following conversation into a short factual summary (5-10 lines) preserving key facts, decisions, and user preferences. Reply in the same language as the conversation."},
        {"role": "user", "content": convo_text}
    ]
    try:
        summary = llm_client.chat(prompt, temperature=0.3, max_tokens=800)
    except Exception as e:
        print(f"[memory] Summarization failed, keeping full history: {e}")
        return

    existing = data.get("summary", "")
    new_summary = (existing + "\n" + summary).strip() if existing else summary
    data["summary"] = new_summary
    data["messages"] = keep
    save_history(data)
    print(f"[memory] Summarized {len(old)} old messages.")
