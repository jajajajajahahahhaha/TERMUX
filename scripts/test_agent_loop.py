"""End-to-end test of the agent loop using a MOCK LLM (no real API call).
Simulates: user asks something → LLM decides to search → LLM decides to run code → finish.
"""
import sys, os, json
from pathlib import Path

# Set fake env so LLMClient init doesn't complain
os.environ["MINIMAX_API_KEY"] = "test_key"
os.environ["MINIMAX_BASE_URL"] = "https://fake"
os.environ["MINIMAX_MODEL"] = "MiniMax-M2"

sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------- Mock LLM ----------------
from agent import llm as llm_module

class MockLLM:
    def __init__(self):
        self.step = 0
        self.responses = [
            # 1st: decide to search
            'برای پیدا کردن جواب سرچ می‌کنم.\n```json\n{"tool":"web_search","query":"Python programming","max_results":2}\n```',
            # 2nd: decide to run code
            'حالا یه کد پایتون تست می‌کنم.\n```json\n{"tool":"run_code","language":"python","code":"print(sum(range(10)))"}\n```',
            # 3rd: ask permission to create file
            'می‌خوام یه فایل بسازم.\n```json\n{"tool":"create_termux_file","path":"~/test.py","content":"print(\\"hi from AI\\")","reason":"تست ساخت فایل"}\n```',
            # 4th: finish
            'کارم تموم شد.\n```json\n{"tool":"finish","answer":"سلام! این یک جواب تست است. سرچ شد، کد اجرا شد، درخواست فایل هم داده شد. ✅"}\n```',
        ]

    def chat(self, messages, temperature=0.7, max_tokens=4000):
        r = self.responses[self.step]
        self.step += 1
        return r

# Monkey-patch
llm_module.LLMClient = MockLLM

# Now import and run the agent
from agent import main as agent_main

# Reset memory
mem = Path(__file__).parent.parent / "memory"
for f in mem.glob("*.json"):
    f.unlink()

# Run
agent_main.run_agent("یه سوال پیچیده که سرچ و کد هم بخواد", request_id="test-123")

# Verify output
reply_file = mem / "latest_reply.json"
assert reply_file.exists(), "latest_reply.json not written!"
reply = json.loads(reply_file.read_text(encoding="utf-8"))
print("\n" + "="*50)
print("FINAL REPLY:")
print(json.dumps(reply, ensure_ascii=False, indent=2))

# Assertions
assert reply["request_id"] == "test-123"
assert "✅" in reply["answer"]
assert len(reply["file_requests"]) == 1
assert reply["file_requests"][0]["path"] == "~/test.py"
assert reply["steps_used"] == 4
print("\n✅ ALL ASSERTIONS PASSED!")

# Check history
hist = json.loads((mem / "chat_history.json").read_text(encoding="utf-8"))
print(f"\nHistory has {len(hist['messages'])} messages")
