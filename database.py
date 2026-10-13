import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from config import LEADS_JSON_PATH

def _read_data() -> Dict[str, Any]:
    """JSON fayldan barcha foydalanuvchilar ma'lumotlarini o'qiydi."""
    if not LEADS_JSON_PATH.exists():
        return {}
    try:
        with open(LEADS_JSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _write_data(data: Dict[str, Any]) -> None:
    """Ma'lumotlarni JSON faylga xavfsiz (atomik) yozadi."""
    temp_file = LEADS_JSON_PATH.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    temp_file.replace(LEADS_JSON_PATH)

def init_db() -> None:
    """Oddiy JSON faylini tayyorlaydi (baza shart emas)."""
    if not LEADS_JSON_PATH.exists():
        _write_data({})

def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Foydalanuvchi ma'lumotlarini JSON fayldan oladi."""
    data = _read_data()
    return data.get(str(user_id))

def set_user_state(user_id: int, state: str, username: Optional[str] = None) -> None:
    """Foydalanuvchi holatini (state) yangilaydi yoki yangi foydalanuvchi qo'shadi."""
    data = _read_data()
    key = str(user_id)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if key not in data:
        data[key] = {
            "user_id": user_id,
            "username": username or "",
            "state": state,
            "first_name": "",
            "last_name": "",
            "birth_year": "",
            "full_name": "",
            "phone": "",
            "study_place": "",
            "created_at": now,
            "updated_at": now,
            "registered_at": now if state == "COMPLETED" else "",
            "sheet_synced": 0
        }
    else:
        data[key]["state"] = state
        if username:
            data[key]["username"] = username
        data[key]["updated_at"] = now
        if state == "COMPLETED" and not data[key].get("registered_at"):
            data[key]["registered_at"] = now

    _write_data(data)

def update_user_field(user_id: int, field: str, value: Any) -> None:
    """Foydalanuvchining aniq bitta maydonini yangilaydi."""
    data = _read_data()
    key = str(user_id)
    if key in data:
        data[key][field] = value
        if field in ("first_name", "last_name"):
            fn = data[key].get("first_name", "")
            ln = data[key].get("last_name", "")
            data[key]["full_name"] = f"{fn} {ln}".strip()
        data[key]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _write_data(data)


def get_unsynced_leads() -> List[Dict[str, Any]]:
    """Google Sheets ga hali yozilmagan COMPLETED leadlarni qaytaradi."""
    data = _read_data()
    return [
        lead for lead in data.values()
        if lead.get("state") == "COMPLETED" and not lead.get("sheet_synced")
    ]
