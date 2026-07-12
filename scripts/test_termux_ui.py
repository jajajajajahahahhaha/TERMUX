"""Render the Termux UI panels to confirm layout works.
Doesn't actually contact GitHub — just tests print_answer + file-request panel.
"""
import sys, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "termux_client"))

# Mock stdin for Confirm() → auto-reject to skip file creation
os.environ["PYTHONIOENCODING"] = "utf-8"

from ask import print_answer, console, fa, show_banner
from rich.panel import Panel

show_banner()

# Simulate a reply
reply = {
    "answer": "سلام! این یک تست UI است.\n\n- مورد اول\n- مورد دوم با کد `print(1)` داخلش\n\nخب امیدوارم قشنگ نشون داده بشه ✨",
    "steps_used": 3,
    "complexity": 2,
    "file_requests": [],
}
print_answer(reply)

# Simulate a file request panel (without actually asking)
req = {
    "path": "~/my_script.py",
    "content": "#!/usr/bin/env python3\nprint('hello from AI-created file')\n",
    "reason": "برای اینکه یک اسکریپت شروع سریع داشته باشی",
}
console.print()
console.print(Panel(
    f"[bold yellow]📝 دستیار می‌خواد یک فایل بسازه[/bold yellow]\n\n"
    f"[cyan]مسیر:[/cyan] {req['path']}\n"
    f"[cyan]دلیل:[/cyan] {req['reason']}\n\n"
    f"[dim]--- محتوا ---[/dim]\n{req['content']}",
    border_style="yellow"
))

print("\n[UI TEST DONE]")
