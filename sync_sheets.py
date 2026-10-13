import logging
from sheets_service import GoogleSheetsService
from database import get_unsynced_leads, update_user_field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SheetsSync")

def sync_pending_leads():
    """Hali Google Sheets ga yozilmagan barcha leadlarni JSON fayldan olib sinxronizatsiya qiladi."""
    sheets = GoogleSheetsService()
    if not sheets.sheet:
        logger.error("Google Sheets ga ulanib bo'lmadi! credentials.json faylini tekshiring.")
        return

    leads = get_unsynced_leads()

    if not leads:
        logger.info("Sinxronlashtirilmagan yangi leadlar yo'q.")
        return

    logger.info(f"{len(leads)} ta saqlanmagan lead topildi. Google Sheets ga yuklanmoqda...")
    for lead_data in leads:
        success = sheets.append_lead(lead_data)
        if success:
            update_user_field(lead_data["user_id"], "sheet_synced", 1)
            logger.info(f"User {lead_data['user_id']} Google Sheets ga sinxronlandi.")

    logger.info("Barcha leadlar muvaffaqiyatli sinxronlandi!")

if __name__ == "__main__":
    sync_pending_leads()
