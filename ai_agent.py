import logging
import concurrent.futures
from typing import Dict, Any, Optional
from pydantic import BaseModel
from google import genai
import config

logger = logging.getLogger(__name__)

# Gemini AI modellari (asosiy va zaxira)
MODELS_PRIORITY = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest"
]

# Gemini mijozini yaratish
client: Optional[genai.Client] = None
if config.GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=config.GEMINI_API_KEY)
        logger.info("Gemini AI mijozi muvaffaqiyatli ishga tushdi.")
    except Exception as e:
        logger.error(f"Gemini mijozini ishga tushirishda xatolik: {e}")
        client = None

class ExtractedInfo(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_year: Optional[str] = None
    phone: Optional[str] = None
    study_place: Optional[str] = None

class AgentDialogResponse(BaseModel):
    reply_to_user: str
    extracted_info: ExtractedInfo
    is_completed: bool

def _generate_with_fallback(**kwargs) -> Any:
    """Modellar orasida avtomatik zaxiraga o'tish bilan so'rov yuboradi."""
    last_error: Optional[Exception] = None
    for model_name in MODELS_PRIORITY:
        try:
            return client.models.generate_content(model=model_name, **kwargs)
        except Exception as e:
            last_error = e
            logger.warning(f"{model_name} xatolik berdi ({e}), keyingi modelga o'tilmoqda...")
    if last_error is not None:
        raise last_error
    raise RuntimeError("Barcha Gemini modellariga murojaat qilishda xatolik yuz berdi.")

def process_incoming_dialog(user_data: Dict[str, Any], incoming_message: str, is_first_message: bool = False) -> AgentDialogResponse:
    """
    Sun'iy Intellekt yordamida foydalanuvchi bilan tabiiy muloqot qiladi:
    - Ism va familiyani alohida ajratib oladi.
    - Tug'ilgan yilini so'raydi.
    - Telefon raqamini to'g'ri formatda oladi.
    - O'qish joyini (agar o'qimasa 'O'qishni tugatgan' deb) tahlil qilib oladi.
    """
    known_first = user_data.get("first_name") or None
    known_last = user_data.get("last_name") or None
    known_birth = user_data.get("birth_year") or None
    known_phone = user_data.get("phone") or None
    known_study = user_data.get("study_place") or None

    # Eski full_name mavjud bo'lsa uni ajratib olish
    if not known_first and user_data.get("full_name"):
        parts = str(user_data["full_name"]).strip().split(maxsplit=1)
        known_first = parts[0]
        if len(parts) > 1:
            known_last = parts[1]

    # Agar tashqaridan belgilanmagan bo'lsa, mavjud ma'lumotlarga qarab birinchi xabarligini aniqlash
    if not is_first_message:
        is_first_message = not (known_first or known_last or known_birth or known_phone or known_study)

    # Agar Gemini ulanmagan bo'lsa, zaxira javob
    default_fallback = AgentDialogResponse(
        reply_to_user=(
            "Assalomu alaykum! Profilimga xush kelibsiz. "
            "Siz bilan bog'lana olishimiz uchun ism-familiyangiz, tug'ilgan yilingiz, telefon raqamingiz va faoliyat joyingizni yozib qoldiring:"
            if is_first_message else
            "Iltimos, ma'lumotlaringizni to'liq qoldiring:"
        ),
        extracted_info=ExtractedInfo(
            first_name=known_first,
            last_name=known_last,
            birth_year=known_birth,
            phone=known_phone,
            study_place=known_study
        ),
        is_completed=False
    )

    if not client:
        return default_fallback

    user_state = user_data.get("state") or "NEW"

    system_instruction = f"""
Sen Sanjarning (@mustang_2002) shaxsiy aqlli Telegram assistentisan.
Foydalanuvchi profili:
- Holati: {user_state} ('COMPLETED' = allaqachon ro'yxatdan o'tgan, 'IN_PROGRESS' = ro'yxatdan o'tish jarayonida)
- Ism: {known_first or 'Hali noma\'lum'}
- Familiya: {known_last or 'Hali noma\'lum'}
- Tug'ilgan yili: {known_birth or 'Hali noma\'lum'}
- Telefon raqami: {known_phone or 'Hali noma\'lum'}
- Ta'lim / faoliyat joyi: {known_study or 'Hali noma\'lum'}

QAT'IY QOIDALAR VA VAZIFALAR:

1. MA'LUMOTLARNI AJRATIB OLISH TALABLARI:
   Foydalanuvchidan quyidagi ma'lumotlar to'planishi kerak:
   a) Ism va Familiya: 'first_name' va 'last_name' ga ALOHIDA ajratib olinadi!
      - Agar faqat ismini aytsa (masalan: 'Jasur'): 'first_name' ni saqlab, familiyasini muloyim so'ra.
      - Agar to'liq aytsa (masalan: 'Jasur Karimov' yoki 'Karimov Jasur'): ismni 'first_name', familiyani 'last_name' ga ajrat.
   b) Tug'ilgan yili: 'birth_year' (masalan: 2002, 1999, 2005).
      - Agar aytilmagan bo'lsa, tug'ilgan yilini so'ra.
   c) Telefon raqami: 'phone' (+998... formatida).
      - Chala yoki xato bo'lsa, to'g'ri formatda so'ra.
   d) Ta'lim / faoliyat joyi: 'study_place'
      - MUHIM QOIDA: Agar foydalanuvchi 'hech qayerda o'qimayman', 'o'qishni bitirganman', 'tamomlaganman', 'o'qimayman', 'maktabni bitirganman' desa -> 'study_place' ga aniq "O'qishni tugatgan" deb yoz!
      - Agar biror joyda ishlasa yoki kasbini aytsa (masalan: 'dasturchiman', 'magazinda ishlayman') -> o'sha ish/kasbini yoz!
      - Agar o'qisa -> ta'lim muassasasini (universitet, maktab, litsey) yoz!

2. MA'LUMOTLARNI YANGILASH, O'ZGARTIRISH YOKI TO'G'RILASH (UPDATE / RE-REGISTER):
   Agar foydalanuvchi ma'lumotlarini yangilamoqchi, o'zgartirmoqchi, to'g'rilamoqchi bo'lsa (masalan: "telefonim xato ketibdi", "yangi raqamim +9989...", "ismim Ali emas Vali", "tug'ilgan yilim 2003", "yangilamoqchiman"):
   - Yangi qiymatni 'extracted_info' ga yoz, o'zgarmagan eski ma'lumotlarni ham to'liq saqlab qol.
   - Yangilanganini tasdiqla va barcha 5 ta ma'lumot (ism, familiya, tug'ilgan yil, telefon, faoliyat joyi) mavjud bo'lsa 'is_completed=true' qil!
   - Agar shunchaki "yangilamoqchiman" deb yozgan bo'lsa: qaysi ma'lumotni yangilamoqchiligini so'ra.

3. RO'YXATDAN O'TGAN FOYDALANUVCHILAR BILAN MULOQOT ('COMPLETED'):
   Agar ma'lumotlarini yangilashni so'ramayotgan bo'lsa:
   - Ro'yxatdan o'tganlik haqida so'rasa -> "Siz allaqachon muvaffaqiyatli ro'yxatdan o'tgansiz, barcha ma'lumotlaringiz saqlangan. Tez orada Sanjar siz bilan bog'lanadi." deb tasdiqla.
   - Rahmat desa -> "Arzimaydi!" deb javob ber.
   - Begona savollar bersa -> "Men bu haqida bilmayman, mening vazifam sizni ro'yxatdan o'tkazish edi. Barcha savollaringizni Sanjarga yetkazaman, u o'zi siz bilan bog'lanadi." deb javob ber.

4. YAKUNLASH MEZONI:
   Qachonki barcha 5 ta maydon ('first_name', 'last_name', 'birth_year', 'phone', 'study_place') to'liq olingan bo'lsa:
   - 'is_completed' qiymatini true qil!
   - Samimiy minnatdorchilik bildir: "Katta rahmat! Barcha ma'lumotlaringiz muvaffaqiyatli qabul qilindi. Tez orada siz bilan bog'lanamiz!" deb yoz.

5. SALOMLASHISH QOIDASI:
   - Faqat eng birinchi xabardagina salom ber ('is_first_message' True bo'lsa).
   - Agar bu birinchi xabar bo'lmasa, qayta salom berish QAT'IYAN TAQIQLANADI. To'g'ridan-to'g'ri mavzuga o't.
"""

    prompt = f"""
Bu foydalanuvchi bilan birinchi xabarmi: {'Ha' if is_first_message else 'Yo\'q'}.
Foydalanuvchining yangi xabari:
"{incoming_message}"

Vazifa: Qoidalarga asosan insoniy javob ('reply_to_user') tayyorla, yangi/yangilangan ma'lumotlarni ('extracted_info') ajratib ol va agar 5 ta ma'lumot ham to'liq bo'lsa 'is_completed=true' qil.
"""

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _generate_with_fallback,
                contents=prompt,
                config=dict(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=AgentDialogResponse
                )
            )
            response = future.result(timeout=20.0)

        data = AgentDialogResponse.model_validate_json(response.text)

        # Agar oldin to'plangan ma'lumot bo'lsa va yangisida null bo'lsa, eskisini saqlab qolish
        if known_first and not data.extracted_info.first_name:
            data.extracted_info.first_name = known_first
        if known_last and not data.extracted_info.last_name:
            data.extracted_info.last_name = known_last
        if known_birth and not data.extracted_info.birth_year:
            data.extracted_info.birth_year = known_birth
        if known_phone and not data.extracted_info.phone:
            data.extracted_info.phone = known_phone
        if known_study and not data.extracted_info.study_place:
            data.extracted_info.study_place = known_study

        if (data.extracted_info.first_name and 
            data.extracted_info.last_name and 
            data.extracted_info.birth_year and 
            data.extracted_info.phone and 
            data.extracted_info.study_place):
            data.is_completed = True

        # Agar birinchi xabar bo'lmasa, tasodifiy salomlashishlarni tozalash
        if not is_first_message:
            for greeting in ["Assalomu alaykum!", "Assalomu alaykum,", "Assalomu alaykum.", "Salom!", "Salom,"]:
                if data.reply_to_user.startswith(greeting):
                    data.reply_to_user = data.reply_to_user[len(greeting):].strip()

        return data

    except Exception as e:
        logger.warning(f"AI dialog tahlilida xatolik: {e}, fallback ishlatilmoqda.")
        return default_fallback

def get_registered_user_reply(user_data: Dict[str, Any], user_message: str) -> str:
    """
    Ro'yxatdan o'tgan foydalanuvchilar savol berganda:
    - Qayta salom bermaydi.
    - Informationdan tashqari savollarga: 'Men bu haqida bilmayman,
      vazifam register qilish edi. Sanjarga yetkazaman' deb javob beradi.
    """
    full_name = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip() or user_data.get("full_name") or "do'stim"
    study_place = user_data.get("study_place") or ""

    default_fallback = (
        f"{full_name}, men bu haqida bilmayman. Mening vazifam sizni ro'yxatdan o'tkazish (register qilish) edi. "
        "Savolingizni Sanjarga yetkazib qo'yaman, tez orada siz bilan shaxsan bog'lanadi!"
    )

    if not client:
        return default_fallback

    system_instruction = f"""
Sen Sanjarning (@mustang_2002) shaxsiy yordamchisisan.
Suhbatdoshing: {full_name} (Faoliyat joyi: {study_place or 'belgilanmagan'}).
Bu foydalanuvchi BIZNING RO'YXATIMIZDAN ALLAQACHON TO'LIQ VA MUVAFFAQIYATLI O'TGAN.
Foydalanuvchi senga yangi xabar yozdi: "{user_message}".

QAT'IY QOIDALAR:
1. HAR SAFAR SALOM BERMA! ("Assalomu alaykum" yoki "Salom" deb boshlash QAT'IYAN TAQIQLANADI). To'g'ridan-to'g'ri mavzuga o't.
2. RO'YXATDAN O'TGANLIK YOKI MA'LUMOTLAR SAQLANGANLIGI HAQIDA SO'RASA:
   "Siz allaqachon muvaffaqiyatli ro'yxatdan o'tgansiz, barcha ma'lumotlaringiz qabul qilingan. Tez orada Sanjar siz bilan bog'lanadi." deb tasdiqla.
3. MINNATDORCHILIK BILDIRSA (Rahmat, salomat bo'ling, tashakkur va h.k.):
   Xushmuomalalik bilan "Arzimaydi!", "Sizga ham katta rahmat!" deb javob ber.
4. BOSHQA BARCHA SAVOLLAR VA MAVZULARGA (darslar qachon, narxlar, shartlar va h.k.):
   Hech narsa to'qima. Aniq qilib:
   "Men bu haqida bilmayman, mening vazifam sizni ro'yxatdan o'tkazish edi. Barcha savollaringizni Sanjarga yetkazaman, u o'zi siz bilan bog'lanadi." deb javob ber.
5. Javobing o'zbek tilida, do'stona, samimiy va ixcham (1-2 gap) bo'lsin.
"""

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _generate_with_fallback,
                contents=system_instruction
            )
            response = future.result(timeout=15.0)

        reply = response.text.strip()
        for greeting in ["Assalomu alaykum!", "Assalomu alaykum,", "Assalomu alaykum.", "Salom!", "Salom,"]:
            if reply.startswith(greeting):
                reply = reply[len(greeting):].strip()
        return reply if reply else default_fallback
    except Exception as e:
        logger.warning(f"Gemini javobida xatolik: {e}")
        return default_fallback
