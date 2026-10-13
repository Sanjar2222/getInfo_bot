import logging
from datetime import datetime
from typing import Dict, Any, Optional
import gspread
from google.oauth2.service_account import Credentials
from config import BASE_DIR, GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEET_NAME, GOOGLE_SHEET_ID

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

class GoogleSheetsService:
    def __init__(self):
        self.client: Optional[gspread.Client] = None
        self.sheet: Optional[gspread.Worksheet] = None
        self._init_client()

    def _init_client(self) -> None:
        """Google Sheets bilan ulanishni o'rnatadi."""
        creds_path = BASE_DIR / GOOGLE_CREDENTIALS_FILE
        if not creds_path.exists():
            logger.warning(
                f"Google Sheets credentials fayli topilmadi: {creds_path}. "
                "Ma'lumotlar faqat lokal JSON faylda (data/leads.json) saqlanadi."
            )

            return

        try:
            creds = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
            self.client = gspread.authorize(creds)

            # Jadvalni ID yoki nomi bo'yicha ochish
            if GOOGLE_SHEET_ID:
                spreadsheet = self.client.open_by_key(GOOGLE_SHEET_ID)
            else:
                spreadsheet = self.client.open(GOOGLE_SHEET_NAME)

            self.sheet = spreadsheet.sheet1
            self._ensure_headers()
            logger.info("Google Sheets ga muvaffaqiyatli ulandi.")
        except Exception as e:
            logger.error(f"Google Sheets ga ulanishda xatolik: {e}")
            self.client = None
            self.sheet = None

    def _ensure_headers(self) -> None:
        """Jadvalda sarlavha (header) qatori borligini ta'minlaydi."""
        if not self.sheet:
            return
        try:
            first_row = self.sheet.row_values(1)
            headers = [
                "Vaqt",
                "Telegram ID",
                "Username",
                "Ism",
                "Familiya",
                "Tug'ilgan Yili",
                "Telefon Raqam",
                "Ta'lim / Faoliyat Joyi"
            ]
            if not first_row:
                self.sheet.append_row(headers)
                logger.info("Google Sheet uchun yangi sarlavhalar (headers) qo'shildi.")
            elif len(first_row) < len(headers):
                # Sarlavhalarni yangilash (agar eski 6 ta ustunli bo'lsa)
                self.sheet.update(range_name=f"A1:H1", values=[headers])
                logger.info("Google Sheet sarlavhalari yangi 8 ta ustunga yangilandi.")
        except Exception as e:
            logger.warning(f"Sarlavhani tekshirishda xatolik: {e}")

    def append_lead(self, lead_data: Dict[str, Any]) -> bool:
        """Yangi lead ma'lumotlarini jadvalga qator sifatida qo'shadi yoki yangilaydi."""
        if not self.sheet:
            # Qayta ulanishga harakat qilib ko'rish
            self._init_client()
            if not self.sheet:
                logger.warning("Google Sheet ulanmagan. Ma'lumot jadvalga yozilmadi.")
                return False

        try:
            user_id_str = str(lead_data.get("user_id", ""))
            reg_time = (
                lead_data.get("registered_at")
                or lead_data.get("updated_at")
                or lead_data.get("created_at")
                or lead_data.get("collected_at")
                or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            first_name = lead_data.get("first_name", "")
            last_name = lead_data.get("last_name", "")
            if not first_name and lead_data.get("full_name"):
                parts = str(lead_data["full_name"]).strip().split(maxsplit=1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ""

            row = [
                reg_time,
                user_id_str,
                f"@{lead_data.get('username')}" if lead_data.get("username") else "",
                first_name,
                last_name,
                str(lead_data.get("birth_year", "")),
                lead_data.get("phone", ""),
                lead_data.get("study_place", "")
            ]

            # Agar foydalanuvchi allaqachon jadvalda bo'lsa (2-ustun: Telegram ID), uning qatorini yangilaymiz
            col_ids = self.sheet.col_values(2)
            if user_id_str in col_ids:
                row_idx = col_ids.index(user_id_str) + 1
                self.sheet.update(range_name=f"A{row_idx}:H{row_idx}", values=[row])
                logger.info(f"Foydalanuvchi {user_id_str} ma'lumotlari Google Sheetda yangilandi (qator {row_idx}).")
            else:
                self.sheet.append_row(row)
                logger.info(f"Foydalanuvchi {user_id_str} Google Sheetga yangi qator sifatida qo'shildi.")
            return True
        except Exception as e:
            logger.error(f"Google Sheetga yozish yoki yangilashda xatolik yuz berdi: {e}")
            return False
