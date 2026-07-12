#!/usr/bin/env python3
"""
Termux client for the AI assistant.
- Beautiful UI with rich
- Persian text rendered correctly (right-to-left)
- Triggers the GitHub Action via repository_dispatch
- Polls the repo for the latest reply
- Handles file-creation permission requests
"""
import json
import os
import sys
import time
import uuid
import base64
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ 'requests' نصب نیست. اجرا کن: pip install requests rich")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.markdown import Markdown
    from rich.spinner import Spinner
    from rich.live import Live
    from rich.text import Text
    from rich.align import Align
except ImportError:
    print("❌ 'rich' نصب نیست. اجرا کن: pip install rich")
    sys.exit(1)

# Optional: proper Persian shaping
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_BIDI = True
except ImportError:
    HAS_BIDI = False


CONFIG_FILE = Path(__file__).parent / ".config.json"
console = Console()


# ─────────────────────────────────────────────────────────────
# Persian text helper
# ─────────────────────────────────────────────────────────────
def fa(text: str) -> str:
    """Reshape and reorder Persian/Arabic text for correct terminal display.
    If arabic_reshaper + python-bidi are not installed, returns as-is
    (most modern terminals including Termux handle it OK, but shaping is nicer).
    """
    if not HAS_BIDI or not text:
        return text
    try:
        # Only reshape if contains Arabic/Persian
        if any('\u0600' <= ch <= '\u06FF' for ch in text):
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        return text
    except Exception:
        return text


# ─────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────
def load_config():
    if not CONFIG_FILE.exists():
        return None
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_config(cfg):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except Exception:
        pass


def setup_wizard():
    console.print(Panel.fit(
        "[bold cyan]🚀 راه‌اندازی اولیه / First-time setup[/bold cyan]\n"
        "لطفاً اطلاعات GitHub رو وارد کن.",
        border_style="cyan"
    ))
    owner = Prompt.ask("GitHub username").strip()
    repo = Prompt.ask("Repo name").strip()
    token = Prompt.ask("Personal Access Token (ghp_...)", password=True).strip()
    cfg = {"owner": owner, "repo": repo, "token": token}
    save_config(cfg)
    console.print("[green]✅ ذخیره شد.[/green]")
    return cfg


# ─────────────────────────────────────────────────────────────
# GitHub API
# ─────────────────────────────────────────────────────────────
class GitHubClient:
    def __init__(self, cfg):
        self.owner = cfg["owner"]
        self.repo = cfg["repo"]
        self.token = cfg["token"]
        self.base = f"https://api.github.com/repos/{self.owner}/{self.repo}"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def check_access(self):
        r = requests.get(self.base, headers=self.headers, timeout=15)
        return r.status_code == 200, r.status_code, r.text[:200]

    def dispatch(self, question: str, request_id: str):
        url = f"{self.base}/dispatches"
        payload = {
            "event_type": "ask_ai",
            "client_payload": {"question": question, "request_id": request_id},
        }
        r = requests.post(url, headers=self.headers, json=payload, timeout=20)
        return r.status_code, r.text[:300]

    def get_latest_reply(self):
        """Fetch memory/latest_reply.json from default branch."""
        url = f"{self.base}/contents/memory/latest_reply.json"
        r = requests.get(url, headers=self.headers, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        try:
            content = base64.b64decode(data["content"]).decode("utf-8")
            return json.loads(content)
        except Exception:
            return None


# ─────────────────────────────────────────────────────────────
# Wait for reply
# ─────────────────────────────────────────────────────────────
def wait_for_reply(gh: GitHubClient, request_id: str, timeout: int = 300):
    """Poll every 4 seconds for a new reply with matching request_id."""
    start = time.time()
    last_seen_ts = 0
    with console.status("[cyan]🧠 در حال فکر کردن... (ممکنه ۳۰-۹۰ ثانیه طول بکشه)[/cyan]", spinner="dots") as status:
        while time.time() - start < timeout:
            time.sleep(4)
            reply = gh.get_latest_reply()
            if reply and reply.get("request_id") == request_id:
                return reply
            if reply and reply.get("timestamp", 0) > last_seen_ts:
                last_seen_ts = reply.get("timestamp", 0)
    return None


# ─────────────────────────────────────────────────────────────
# Handle file requests
# ─────────────────────────────────────────────────────────────
def handle_file_requests(file_requests):
    if not file_requests:
        return
    for req in file_requests:
        path = os.path.expanduser(req.get("path", ""))
        content = req.get("content", "")
        reason = req.get("reason", "")

        console.print()
        console.print(Panel(
            f"[bold yellow]📝 دستیار می‌خواد یک فایل بسازه[/bold yellow]\n\n"
            f"[cyan]مسیر:[/cyan] {path}\n"
            f"[cyan]دلیل:[/cyan] {reason}\n\n"
            f"[dim]--- محتوا ({len(content)} کاراکتر) ---[/dim]\n"
            f"{content[:600]}{'...' if len(content) > 600 else ''}",
            border_style="yellow"
        ))
        if Confirm.ask("[bold]اجازه ساخت این فایل رو میدی؟[/bold]", default=False):
            try:
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                Path(path).write_text(content, encoding="utf-8")
                console.print(f"[green]✅ ساخته شد: {path}[/green]")
            except Exception as e:
                console.print(f"[red]❌ خطا: {e}[/red]")
        else:
            console.print("[dim]رد شد.[/dim]")


# ─────────────────────────────────────────────────────────────
# Main UI
# ─────────────────────────────────────────────────────────────
BANNER = r"""
  ████████╗ █████╗ ██╗
  ╚══██╔══╝██╔══██╗██║
     ██║   ███████║██║
     ██║   ██╔══██║██║
     ██║   ██║  ██║██║
     ╚═╝   ╚═╝  ╚═╝╚═╝
   Termux AI Assistant
"""


def show_banner():
    console.print(Align.center(Text(BANNER, style="bold cyan")))
    console.print(Align.center(Text("MiniMax M2 · GitHub Actions Backend · Agentic",
                                     style="dim italic")))
    console.print()


def _has_persian(text: str) -> bool:
    return any('\u0600' <= ch <= '\u06FF' for ch in text or "")


def print_answer(reply: dict):
    answer = reply.get("answer", "(no answer)")
    steps = reply.get("steps_used", "?")
    complexity = reply.get("complexity", "?")
    comp_label = {1: "ساده", 2: "متوسط", 3: "پیچیده"}.get(complexity, "?")

    console.print()
    # Modern Termux terminals render Persian correctly natively; rich's Markdown
    # preserves logical order. Using bidi + reshaping INSIDE a rich panel double-flips
    # the text, so only apply fa() when the terminal is known-bad (fallback).
    # Default: pass the answer as Markdown → looks great, Persian stays readable.
    if _has_persian(answer):
        body = Text(answer, justify="right")
    else:
        body = Markdown(answer)

    console.print(Panel(
        body,
        title=f"[bold green]🤖 پاسخ[/bold green]  [dim](پیچیدگی: {comp_label} · مراحل: {steps})[/dim]",
        border_style="green",
        padding=(1, 2),
    ))


def main():
    show_banner()

    cfg = load_config()
    if not cfg:
        cfg = setup_wizard()

    gh = GitHubClient(cfg)
    ok, code, msg = gh.check_access()
    if not ok:
        console.print(f"[red]❌ دسترسی به ریپو ندارم (HTTP {code}).[/red] {msg}")
        if Confirm.ask("می‌خوای دوباره تنظیم کنی؟"):
            cfg = setup_wizard()
            gh = GitHubClient(cfg)
        else:
            sys.exit(1)

    console.print("[green]✅ اتصال به GitHub برقراره.[/green]")
    console.print("[dim]برای خروج: exit یا Ctrl+C[/dim]\n")

    while True:
        try:
            console.print()
            question = Prompt.ask("[bold cyan]شما[/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]خداحافظ 👋[/dim]")
            break

        if not question:
            continue
        if question.lower() in ("exit", "quit", "خروج", ":q"):
            console.print("[dim]خداحافظ 👋[/dim]")
            break

        request_id = uuid.uuid4().hex[:12]
        console.print(f"[dim]→ ارسال به GitHub Actions... (id={request_id})[/dim]")

        status_code, resp = gh.dispatch(question, request_id)
        if status_code not in (200, 201, 204):
            console.print(f"[red]❌ ارسال شکست خورد (HTTP {status_code}):[/red] {resp}")
            continue

        reply = wait_for_reply(gh, request_id, timeout=300)
        if not reply:
            console.print("[red]⏱ timeout: جوابی نیومد. تب Actions تو GitHub رو چک کن.[/red]")
            continue

        print_answer(reply)
        handle_file_requests(reply.get("file_requests", []))


if __name__ == "__main__":
    main()
