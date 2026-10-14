# Ott-Bot - Complete Hotstar Downloader with Telegram Integration

## 🎯 Features:
- ✅ Chrome Extension - Auto captures MPD + License URL
- ✅ Auto Key Extraction - pywidevine CDM integration
- ✅ Telegram Bot (Pyrogram) - Optional, CLI fallback
- ✅ Video Selector - Choose which video to download
- ✅ Full Pipeline - URL → Capture → Download → Decrypt → Upload

## 📁 Structure:
```
Ott-Bot/
├── extension/           # Chrome extension
│   ├── manifest.json
│   ├── background.js
│   ├── content.js
│   └── popup.html
├── bot/                 # Python backend
│   ├── main.py          # Entry point
│   ├── browser.py       # Browser automation
│   ├── downloader.py    # Download + decrypt pipeline
│   ├── tg_bot.py        # Telegram bot (Pyrogram)
│   └── config.py        # Configuration
├── requirements.txt
└── README.md
```

## 🚀 Quick Start:
```bash
# 1. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 2. Load extension in Chrome
# chrome://extensions/ → Load unpacked → extension/ folder

# 3. Run bot
python bot/main.py

# 4. Send Hotstar URL via Telegram or CLI
# Bot handles everything automatically!
```
