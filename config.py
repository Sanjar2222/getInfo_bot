import os
from pathlib import Path
from dotenv import load_dotenv

# Loyiha ildiz katalogi
BASE_DIR = Path(__file__).resolve().parent

# .env faylini yuklash
load_dotenv(BASE_DIR / ".env")

# Telegram sozlamalari
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_HASH") or os.getenv("TELEGRAM_API_HASH")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE")
SESSION_NAME = os.getenv("SESSION_NAME", "lead_collector_session")

# Google Sheets sozlamalari
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Leadlar (Userbot)")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")

# Userbot xulq-atvori
IGNORE_CONTACTS = os.getenv("IGNORE_CONTACTS", "False").lower() in ("true", "1", "yes")
SIMULATE_TYPING = os.getenv("SIMULATE_TYPING", "True").lower() in ("true", "1", "yes")

# Gemini AI sozlamalari
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Ma'lumotlar papkalari
DATA_DIR = BASE_DIR / "data"
LEADS_JSON_PATH = DATA_DIR / "leads.json"

# Kerakli papkalarni yaratish
DATA_DIR.mkdir(parents=True, exist_ok=True)

