#!/data/data/com.termux/files/usr/bin/bash
# Setup script for Termux side.
set -e

echo "🚀 نصب پیش‌نیاز‌ها روی Termux ..."
pkg update -y
pkg install -y python git

echo "📦 نصب پکیج‌های پایتون ..."
pip install --upgrade pip
pip install requests rich arabic-reshaper python-bidi

# Make sure UTF-8 locale is used
if ! grep -q "LANG=en_US.UTF-8" ~/.bashrc 2>/dev/null; then
  echo 'export LANG=en_US.UTF-8' >> ~/.bashrc
  echo 'export LC_ALL=en_US.UTF-8' >> ~/.bashrc
fi

echo ""
echo "✅ نصب کامل شد."
echo ""
echo "برای اجرا:"
echo "    python ask.py"
echo ""
