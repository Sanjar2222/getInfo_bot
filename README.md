# AI Telegram Userbot Lead Collector & Google Sheets Agent

An autonomous, intelligent Telegram Userbot agent powered by **Google Gemini AI** and **Telethon**. It converses naturally with incoming private chats, collects structured registration leads, intelligently corrects errors, handles data updates, and synchronizes records directly to **Google Sheets** in real time.

---

## 🌟 Key Features

- 🧠 **100% AI-Driven Dialog (Google Gemini):**
  - Engages in human-like, polite conversation in Uzbek (or any language).
  - Welcomes users on their first message only (prevents repeated greeting spam).
  - Automatically extracts:
    1. **First Name & Last Name** (stored in separate columns)
    2. **Birth Year**
    3. **Phone Number** (with format validation)
    4. **Study or Workplace** (intelligently infers *"O'qishni tugatgan"* if the user states they no longer study).
- 🔄 **Autonomous Self-Correction & In-Place Updates:**
  - If a user sends a typo or says *"I changed my phone number"* or *"I want to update my info"*, Gemini dynamically understands the intent, updates their record, and updates the exact existing row in Google Sheets.
- 🚫 **Strict Boundary Rules:**
  - For off-topic or unknown queries, the agent politely informs the user that its role is registration and notes that Sanjar will reach out directly.
- 📊 **Real-Time Google Sheets Synchronization:**
  - Automatically manages an 8-column spreadsheet (`Timestamp`, `Telegram ID`, `Username`, `First Name`, `Last Name`, `Birth Year`, `Phone Number`, `Study / Activity Place`).
- 🛡️ **Anti-Ban & Humanized Behavior:**
  - Sends read receipts (`send_read_acknowledge`) and displays typing indicators (`typing...`) with natural delays before responding.
- 💾 **Pure JSON Local Storage:**
  - Simple, robust atomic storage in `data/leads.json` (no SQLite or complex DBMS required).
- 🔌 **Offline Resilience:**
  - Tracks synchronization status (`sheet_synced`). Any unsynced records due to network interruptions can be synced anytime via `sync_sheets.py`.

---

## 📂 Project Structure

```
get_info_agent/
├── .env.example          # Environment variables template
├── .gitignore            # Git exclusion rules (protects credentials & private data)
├── requirements.txt      # Python dependencies
├── config.py             # Configuration & environment variable loader
├── database.py           # Pure JSON database layer (data/leads.json)
├── sheets_service.py     # Google Sheets API client (gspread & google-auth)
├── ai_agent.py           # Gemini AI extraction & conversational agent
├── bot.py                # Main Telethon userbot runner
├── sync_sheets.py        # Offline/pending lead synchronization utility
└── data/
    └── leads.json        # Local storage file (auto-created)
```

---

## ⚙️ Installation & Setup

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/USERNAME/REPO_NAME.git
cd get_info_agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables (`.env`)

Copy the template:
```bash
cp .env.example .env
```

Open `.env` and fill in your credentials:
```env
# Telegram API Credentials (obtain from https://my.telegram.org)
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+998901234567

# Google Sheets Configuration
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_SHEET_NAME=
GOOGLE_SHEET_ID=your_spreadsheet_id_here

# Userbot Behavior
IGNORE_CONTACTS=False
SIMULATE_TYPING=True

# Google Gemini AI API Key (obtain from https://aistudio.google.com)
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Connect Google Sheets (Service Account)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project and enable both **Google Drive API** and **Google Sheets API**.
3. Navigate to **Credentials** $\rightarrow$ **Create Credentials** $\rightarrow$ **Service Account**.
4. Inside the Service Account, go to **Keys** $\rightarrow$ **Add Key** $\rightarrow$ **Create new key (JSON)** and download the file.
5. Rename the downloaded file to `credentials.json` and place it in the root folder of this project (`get_info_agent/`).
6. Create a Google Spreadsheet and share it with your Service Account email (e.g., `account@project.iam.gserviceaccount.com`) as an **Editor**.
7. Copy the Spreadsheet ID from the URL and paste it into `GOOGLE_SHEET_ID` in `.env`.

---

## 🚀 Running the Userbot

### Start the Bot:
```bash
python bot.py
```
*On the first run, Telegram will ask for your login confirmation code in the terminal. Once logged in, your session is saved locally in `lead_collector_session.session`.*

### Manual Google Sheets Sync (Optional):
If any entries were saved while offline or when the Google Sheets API was temporarily unreachable:
```bash
python sync_sheets.py
```

---

## 🔒 Security & Privacy

- Sensitive files such as `.env`, `credentials.json`, `*.session`, and `data/leads.json` are strictly ignored by `.gitignore` and are never pushed to GitHub.
- Works as a personal client; sensitive tokens never leave your local environment.
