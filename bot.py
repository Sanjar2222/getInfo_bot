import asyncio
import logging
from datetime import datetime
from typing import Any, cast
from telethon import TelegramClient, events
from telethon.tl.types import User

import config
from database import (
    init_db,
    get_user,
    set_user_state,
    update_user_field
)
from sheets_service import GoogleSheetsService
from ai_agent import process_incoming_dialog


# Logging sozlamalari
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("UserbotAgent")

# Google Sheets xizmati
sheets = GoogleSheetsService()

# Telethon mijozini yaratish
if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
    print("\n" + "="*60)
    print("XATOLIK: .env faylida TELEGRAM_API_ID yoki TELEGRAM_API_HASH topilmadi!")
    print("Iltimos, .env faylini to'ldiring.")
    print("="*60 + "\n")
    raise SystemExit(1)

client = TelegramClient(
    session=str(config.BASE_DIR / config.SESSION_NAME),
    api_id=int(str(config.TELEGRAM_API_ID).strip()),
    api_hash=str(config.TELEGRAM_API_HASH).strip()
)

async def send_response(event, message_text: str):
    """Xabarni o'qilgan deb belgilab, odamdek yozish effekti bilan yuboradi."""
    try:
        await event.client.send_read_acknowledge(event.chat_id)
        if config.SIMULATE_TYPING:
            async with event.client.action(event.chat_id, "typing"):
                await asyncio.sleep(1.5)
        await event.respond(message_text)
    except Exception as e:
        logger.error(f"Xabar yuborishda xatolik: {e}")

@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def handle_private_message(event):
    sender = await event.get_sender()

    # O'zimizga, botlarga yoki kanal/guruhlarga javob bermaslik
    if not isinstance(sender, User) or sender.is_self or sender.bot:
        return

    user_id = sender.id
    username = sender.username or ""
    incoming_text = (event.raw_text or "").strip()

    logger.info(f"Yangi xabar keldi: {user_id} (@{username}) | contact={sender.contact} | '{incoming_text}'")

    # Ma'lumotlar bazasidan foydalanuvchi holatini tekshirish
    user = get_user(user_id)

    # Faqat bazada umuman bo'lmagan shaxsiy kontaktlarni e'tiborsiz qoldirish
    if config.IGNORE_CONTACTS and sender.contact and not user:
        logger.info(f"Foydalanuvchi shaxsiy kontaktlaringizda bor (yangi lead emas), o'tkazib yuborildi: {user_id}")
        return

    # 1. YANGI FOYDALANUVCHI BO'LSA - JSON GA QO'SHISH
    is_first = False
    if not user:
        set_user_state(user_id, "IN_PROGRESS", username=username)
        user = get_user(user_id)
        is_first = True

    # 2. BARCHA VAZIFANI 100% SUN'IY INTELLEKT (GEMINI) HAL QILADI:
    # (Yangi ro'yxat, savol-javob, xatoni to'g'rilash va ma'lumotlarni yangilash)
    dialog_res = await asyncio.to_thread(process_incoming_dialog, user, incoming_text, is_first)

    # Sun'iy intellekt ajratib olgan yoki yangilagan ma'lumotlarni JSON ga saqlash
    extracted = dialog_res.extracted_info
    has_changes = False
    if extracted.first_name and extracted.first_name != user.get("first_name"):
        update_user_field(user_id, "first_name", extracted.first_name)
        has_changes = True
    if extracted.last_name and extracted.last_name != user.get("last_name"):
        update_user_field(user_id, "last_name", extracted.last_name)
        has_changes = True
    if extracted.birth_year and str(extracted.birth_year) != str(user.get("birth_year", "")):
        update_user_field(user_id, "birth_year", str(extracted.birth_year))
        has_changes = True
    if extracted.phone and extracted.phone != user.get("phone"):
        update_user_field(user_id, "phone", extracted.phone)
        has_changes = True
    if extracted.study_place and extracted.study_place != user.get("study_place"):
        update_user_field(user_id, "study_place", extracted.study_place)
        has_changes = True

    # Foydalanuvchiga AI tayyorlagan insoniy javobni yuborish
    await send_response(event, dialog_res.reply_to_user)

    # 3. AGAR MA'LUMOTLAR TO'LIQ BO'LSA (YANGI LEADD YOKI YANGILANGAN MA'LUMOT)
    if dialog_res.is_completed:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_user_field(user_id, "registered_at", now_str)
        update_user_field(user_id, "state", "COMPLETED")
        complete_data = get_user(user_id)
        # Faqat yangi bo'lsa yoki ma'lumotlari o'zgargan bo'lsa jadvalga yangilaymiz
        if complete_data and (has_changes or not complete_data.get("sheet_synced")):
            logger.info(f"Lead ma'lumotlari saqlandi/yangilandi: {user_id} (@{username})")
            sheet_success = sheets.append_lead(complete_data)
            if sheet_success:
                update_user_field(user_id, "sheet_synced", 1)
        return



async def main():
    """Botni ishga tushiruvchi asosiy funksiya."""
    init_db()
    
    if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
        print("\n" + "="*60)
        print("XATOLIK: .env faylida TELEGRAM_API_ID va TELEGRAM_API_HASH topilmadi!")
        print("Iltimos, .env faylini to'ldiring. (Qarang: .env.example)")
        print("="*60 + "\n")
        return

    print("Telethon mijoziga ulanmoqda...")
    # Telethon kutubxonasida start() asinxron rejimda Coroutine qaytarsa ham,
    # uning type hint'i noto'g'ri 'TelegramClient' bo'lgani sababli Pyrefly uchun cast(Any, ...) ishlatiladi
    await cast(Any, client.start(phone=config.TELEGRAM_PHONE))
    
    me = await client.get_me()
    print(f"\nUserbot muvaffaqiyatli ishga tushdi!")
    print(f"Akkaunt egasi: {me.first_name} {me.last_name or ''} (@{me.username or 'username_yoq'})")
    print("Yangi foydalanuvchilardan xabarlar kutilmoqda...\n")
    
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\nUserbot to'xtatildi.")
