# 🤖 Termux AI Assistant (MiniMax M2 + GitHub Actions Backend)

یک دستیار هوش مصنوعی agentic که:
- کلاینت سبک تو **Termux** اجرا میشه (فقط سوال می‌پرسه، UI قشنگ، فارسی درست)
- مغز اصلی (**MiniMax M2 + Search + Sandbox**) روی **GitHub Actions** اجرا میشه
- حافظه چت، تفکر تطبیقی، اجازه گرفتن قبل از ساخت فایل تو Termux

## 📂 ساختار پروژه

```
aiproject/
├── .github/workflows/
│   └── agent.yml              # ← GitHub Action که وقتی سوال میاد اجرا میشه
├── agent/
│   ├── main.py                # ← نقطه ورود Action - مدیر کل
│   ├── llm.py                 # ← ارتباط با MiniMax M2
│   ├── tools.py               # ← سرچ DuckDuckGo + Sandbox اجرای کد
│   ├── memory.py              # ← حافظه چت (JSON + خلاصه‌سازی)
│   ├── thinking.py            # ← تصمیم‌گیر سطح تفکر (adaptive)
│   └── prompts.py             # ← system prompt دو زبانه
├── memory/
│   └── chat_history.json      # ← حافظه persistent (خودکار آپدیت میشه)
├── termux_client/
│   ├── ask.py                 # ← اسکریپت اصلی Termux (UI فارسی)
│   └── setup_termux.sh        # ← نصب خودکار روی Termux
├── requirements.txt
└── README.md
```

## 🚀 نصب و راه‌اندازی — قدم به قدم

### قدم ۱: ساخت ریپو خصوصی روی GitHub

1. برو به https://github.com/new
2. نام: `my-ai-assistant` (یا هرچی دوست داری)
3. **Private** بذارش
4. Create repository

### قدم ۲: آپلود این فایل‌ها

```bash
cd aiproject
git init
git add .
git commit -m "initial"
git remote add origin https://github.com/USERNAME/my-ai-assistant.git
git push -u origin main
```

### قدم ۳: تنظیم Secrets در GitHub

برو به: `Settings → Secrets and variables → Actions → New repository secret`

سه تا secret اضافه کن:

| Name | Value |
|------|-------|
| `MINIMAX_API_KEY` | توکن MiniMax تو (`dahl_...` یا هر توکن دیگه) |
| `MINIMAX_BASE_URL` | `https://api.minimax.io/v1` (یا هر endpointای که توکنت مال اونه) |
| `MINIMAX_MODEL` | `MiniMax-M2` (یا `MiniMax-M2.7`) |

> ⚠️ توکنی که دادی (`dahl_...`) روی endpointهای معروف کار نکرد. وقتی provider درستشو پیدا کردی، فقط این ۳ تا secret رو عوض کن، **هیچ تغییری تو کد لازم نیست**.

### قدم ۴: ساخت Personal Access Token (PAT)

Termux نیاز داره Actionرو trigger کنه:

1. برو به: https://github.com/settings/tokens/new
2. Note: `termux-ai-client`
3. Expiration: `No expiration` (یا هرچی)
4. Scope: فقط `repo` رو تیک بزن
5. Generate → توکن رو کپی کن (`ghp_...`)

### قدم ۵: نصب روی Termux

```bash
pkg update -y && pkg install -y python git
pip install requests rich

git clone https://github.com/USERNAME/my-ai-assistant.git
cd my-ai-assistant/termux_client
bash setup_termux.sh
```

اسکریپت `setup_termux.sh` ازت این چیزها رو می‌پرسه و ذخیره می‌کنه:
- GitHub username
- Repo name
- PAT (`ghp_...`)

### قدم ۶: اجرا 🎉

```bash
python ask.py
```

## 🎯 نحوه کار

```
[تو تو Termux] سوال میپرسی
        ↓
[Termux client] از طریق repository_dispatch API میفرسته به GitHub
        ↓
[GitHub Actions] MiniMax M2 فکر میکنه
        ├─ اگه سرچ لازمه → DuckDuckGo
        ├─ اگه کد اجرا لازمه → Sandbox runner
        └─ اگه ساخت فایل تو Termux → اجازه میخواد
        ↓
[GitHub] جواب رو تو memory/chat_history.json کامیت میکنه
        ↓
[Termux client] فایل رو pull میکنه و با UI قشنگ نشون میده
```

## 🧠 قابلیت‌های Agentic

- **تفکر تطبیقی**: هر سوال رو ابتدا analyze می‌کنه و تصمیم می‌گیره چقدر عمیق فکر کنه
- **Tool use**: خودش تصمیم می‌گیره کی سرچ کنه، کی کد اجرا کنه، کی فایل بسازه
- **اجازه‌گیری**: قبل از ساخت فایل تو Termux، از تو تایید می‌گیره
- **حافظه**: تمام مکالمات با خلاصه‌سازی خودکار وقتی طولانی شد

## 🌐 پشتیبانی از فارسی

- کلاینت Termux از `python-bidi` و `arabic-reshaper` استفاده می‌کنه که فارسی برعکس چاپ نشه
- UI با `rich` طراحی شده — پنل، جدول، رنگ، spinner
- دو زبانه: می‌تونی فارسی یا انگلیسی بپرسی
