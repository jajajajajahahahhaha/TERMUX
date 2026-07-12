"""
Main agent entry point. Runs inside GitHub Actions.
Reads the user's question from event payload, runs the agent loop,
writes the answer back to memory/chat_history.json (which gets committed).
"""
import os
import sys
import json
import re
import time
from pathlib import Path

# Make agent package importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.llm import LLMClient
from agent.tools import execute_tool
from agent.memory import add_message, build_context_messages, maybe_summarize, load_history, save_history
from agent.prompts import build_system_prompt
from agent.thinking import analyze_question, thinking_hint


MAX_STEPS_HARD_CAP = 12
LATEST_REPLY_FILE = Path(__file__).parent.parent / "memory" / "latest_reply.json"


def extract_tool_call(text: str):
    """Find the last ```json ... ``` block and parse it."""
    # Try fenced blocks first
    fences = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    candidate = None
    if fences:
        candidate = fences[-1]
    else:
        # fallback: try to find a top-level {...} that contains "tool"
        m = re.search(r'(\{[^{}]*"tool"[^{}]*\})', text, flags=re.DOTALL)
        if m:
            candidate = m.group(1)

    if not candidate:
        return None
    try:
        obj = json.loads(candidate)
        if isinstance(obj, dict) and "tool" in obj:
            return obj
    except json.JSONDecodeError:
        # try to fix common issues (trailing commas etc.)
        try:
            cleaned = re.sub(r",\s*}", "}", candidate)
            cleaned = re.sub(r",\s*]", "]", cleaned)
            obj = json.loads(cleaned)
            if isinstance(obj, dict) and "tool" in obj:
                return obj
        except Exception:
            return None
    return None


def write_latest_reply(payload: dict):
    """Write the final reply that Termux will read."""
    LATEST_REPLY_FILE.parent.mkdir(parents=True, exist_ok=True)
    LATEST_REPLY_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_agent(user_question: str, request_id: str = ""):
    print(f"\n{'='*60}\n[agent] Question: {user_question[:200]}\n{'='*60}")

    llm = LLMClient()

    # 1) Log user's message
    add_message("user", user_question)

    # 2) Adaptive thinking analysis
    analysis = analyze_question(user_question)
    print(f"[agent] Complexity analysis: {analysis}")

    # 3) Build context
    system = build_system_prompt()
    messages = build_context_messages(system)
    messages.insert(1, {"role": "system", "content": thinking_hint(analysis)})

    max_steps = min(analysis["max_tool_steps"], MAX_STEPS_HARD_CAP)
    step = 0
    final_answer = None
    file_requests = []  # buffer of termux_file_request objects

    while step < max_steps:
        step += 1
        print(f"\n[agent] --- Step {step}/{max_steps} ---")

        try:
            reply = llm.chat(messages, temperature=0.6, max_tokens=3000)
        except Exception as e:
            print(f"[agent] LLM error: {e}")
            final_answer = f"❌ خطا در فراخوانی مدل / LLM error:\n{e}"
            break

        print(f"[agent] LLM reply (first 400 chars):\n{reply[:400]}")
        messages.append({"role": "assistant", "content": reply})

        call = extract_tool_call(reply)
        if not call:
            # No tool call found → treat entire reply as final answer
            final_answer = reply.strip()
            break

        tool_name = call.get("tool")
        if tool_name == "finish":
            final_answer = call.get("answer", "").strip() or reply.strip()
            break

        # Execute tool
        print(f"[agent] Executing tool: {tool_name}")
        result = execute_tool(tool_name, call)

        # Special handling: termux file requests are queued, not executed here
        if result.get("type") == "termux_file_request":
            file_requests.append({
                "path": result["path"],
                "content": result["content"],
                "reason": result["reason"],
            })
            tool_output_for_llm = {
                "ok": True,
                "note": "File request queued. It will be presented to the user in Termux for approval.",
                "path": result["path"],
            }
        else:
            tool_output_for_llm = result

        # Truncate large outputs
        summary_str = json.dumps(tool_output_for_llm, ensure_ascii=False)
        if len(summary_str) > 6000:
            summary_str = summary_str[:6000] + "\n...[truncated]..."
        messages.append({
            "role": "user",
            "content": f"[TOOL_RESULT for {tool_name}]\n{summary_str}"
        })

    if final_answer is None:
        final_answer = "❗ به بودجه فکر کردنم رسیدم بدون نتیجه نهایی. لطفاً سوالت رو ساده‌تر بپرس."

    # Save assistant final message to history
    add_message("assistant", final_answer)

    # Maybe summarize if history grew
    try:
        maybe_summarize(llm)
    except Exception as e:
        print(f"[agent] summarize failed (non-fatal): {e}")

    # Write latest reply for Termux client
    payload = {
        "request_id": request_id,
        "question": user_question,
        "answer": final_answer,
        "file_requests": file_requests,
        "steps_used": step,
        "complexity": analysis["complexity"],
        "timestamp": int(time.time()),
    }
    write_latest_reply(payload)
    print(f"\n[agent] ✅ Done in {step} steps.")


if __name__ == "__main__":
    # Read the question from GitHub event payload
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    question = ""
    request_id = ""

    if event_path and Path(event_path).exists():
        try:
            event = json.loads(Path(event_path).read_text(encoding="utf-8"))
            client_payload = event.get("client_payload", {}) or {}
            question = client_payload.get("question", "").strip()
            request_id = client_payload.get("request_id", "").strip()
        except Exception as e:
            print(f"[agent] Failed to parse event: {e}")

    # Fallback: env vars (for manual test runs)
    if not question:
        question = os.environ.get("AI_QUESTION", "").strip()
    if not request_id:
        request_id = os.environ.get("AI_REQUEST_ID", str(int(time.time())))

    if not question:
        print("[agent] ❌ No question found in payload or AI_QUESTION env.")
        sys.exit(1)

    run_agent(question, request_id)
