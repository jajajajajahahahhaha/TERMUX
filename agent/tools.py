"""Tools available to the agent: web search + code sandbox + termux-file-request."""
import subprocess
import tempfile
import os
import json
from typing import Dict, Any


def web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """DuckDuckGo search — no API key needed. Supports both old and new package names."""
    DDGS = None
    try:
        from ddgs import DDGS  # new package name
    except ImportError:
        try:
            from duckduckgo_search import DDGS  # legacy fallback
        except ImportError:
            return {"ok": False, "error": "ddgs not installed"}

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        cleaned = [
            {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
            for r in results
        ]
        return {"ok": True, "results": cleaned}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_code(language: str, code: str, timeout: int = 60) -> Dict[str, Any]:
    """Run Python/Bash code in the GitHub runner. Isolated per-call temp dir."""
    language = language.lower().strip()
    if language not in ("python", "bash", "sh"):
        return {"ok": False, "error": f"Unsupported language: {language}"}

    with tempfile.TemporaryDirectory() as tmp:
        if language == "python":
            script = os.path.join(tmp, "s.py")
            with open(script, "w", encoding="utf-8") as f:
                f.write(code)
            cmd = ["python3", script]
        else:
            script = os.path.join(tmp, "s.sh")
            with open(script, "w", encoding="utf-8") as f:
                f.write(code)
            cmd = ["bash", script]

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tmp,
            )
            return {
                "ok": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": (proc.stdout or "")[:4000],
                "stderr": (proc.stderr or "")[:2000],
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"Timeout after {timeout}s"}
        except Exception as e:
            return {"ok": False, "error": str(e)}


def create_termux_file_request(path: str, content: str, reason: str) -> Dict[str, Any]:
    """
    This DOESN'T actually create the file — GitHub runner can't touch Termux.
    It returns a structured request that the Termux client will handle: ask
    the user for permission, then create the file locally on the phone.
    """
    return {
        "ok": True,
        "type": "termux_file_request",
        "path": path,
        "content": content,
        "reason": reason,
        "note": "The user's Termux client will ask permission and create the file locally.",
    }


TOOL_REGISTRY = {
    "web_search": lambda args: web_search(args.get("query", ""), int(args.get("max_results", 5))),
    "run_code": lambda args: run_code(args.get("language", "python"), args.get("code", "")),
    "create_termux_file": lambda args: create_termux_file_request(
        args.get("path", ""), args.get("content", ""), args.get("reason", "")
    ),
}


def execute_tool(name: str, args: dict) -> Dict[str, Any]:
    if name not in TOOL_REGISTRY:
        return {"ok": False, "error": f"Unknown tool: {name}"}
    try:
        return TOOL_REGISTRY[name](args)
    except Exception as e:
        return {"ok": False, "error": f"Tool crashed: {e}"}
