# -*- coding: utf-8 -*-
import aiosqlite
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime  # ВАЖНО: добавили для работы методов с датой

@dataclass
class User:
    telegram_id: int
    age: Optional[int] = None
    gender: Optional[str] = None
    search_gender: str = "both"
    room: str = "common"
    partner_id: Optional[int] = None
    total_dialogs: int = 0
    today_dialogs: int = 0
    rating: int = 0
    is_premium: bool = False
    is_banned: bool = False
    region: str = "Не указан"
    likes: int = 0
    dislikes: int = 0
    first_name: Optional[str] = "Аноним"
    referred_by: Optional[int] = None
    premium_until: Optional[str] = None # Добавили поле в датакласс

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    first_name TEXT DEFAULT 'Аноним',
                    age INTEGER,
                    gender TEXT,
                    search_gender TEXT DEFAULT 'both',
                    room TEXT DEFAULT 'common',
                    partner_id INTEGER,
                    total_dialogs INTEGER DEFAULT 0,
                    today_dialogs INTEGER DEFAULT 0,
                    rating INTEGER DEFAULT 0,
                    is_premium BOOLEAN DEFAULT 0,
                    is_banned BOOLEAN DEFAULT 0,
                    region TEXT DEFAULT 'Не указан',
                    likes INTEGER DEFAULT 0,
                    dislikes INTEGER DEFAULT 0,
                    referred_by INTEGER,
                    premium_until DATETIME  -- Добавили колонку при создании
                )
            """)
            
            # Список колонок для проверки (если база уже создана)
            cols = {
                "first_name": "TEXT DEFAULT 'Аноним'",
                "room": "TEXT DEFAULT 'common'",
                "total_dialogs": "INTEGER DEFAULT 0",
                "today_dialogs": "INTEGER DEFAULT 0",
                "rating": "INTEGER DEFAULT 0",
                "is_premium": "BOOLEAN DEFAULT 0",
                "is_banned": "BOOLEAN DEFAULT 0",
                "region": "TEXT DEFAULT 'Не указан'",
                "likes": "INTEGER DEFAULT 0",
                "dislikes": "INTEGER DEFAULT 0",
                "referred_by": "INTEGER",
                "premium_until": "DATETIME" # Добавили проверку наличия колонки даты
            }
            
            for col_name, col_type in cols.items():
                try:
                    await db.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                except:
                    pass
            await db.commit()

    # --- ТВОИ НОВЫЕ МЕТОДЫ ДЛЯ ВРЕМЕНИ ПРЕМИУМА ---

    async def get_premium_finish_date(self, user_id: int):
        """Получает объект datetime окончания премиума"""
        async with aiosqlite.connect(self.db_path) as db:
            res = await db.execute("SELECT premium_until FROM users WHERE telegram_id = ?", (user_id,))
            row = await res.fetchone()
            if row and row[0]:
                try:
                    return datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    return None
            return None

    async def set_premium_finish_date(self, user_id: int, date: datetime):
        """Устанавливает дату окончания премиума в БД"""
        async with aiosqlite.connect(self.db_path) as db:
            date_str = date.strftime('%Y-%m-%d %H:%M:%S')
            await db.execute(
                "UPDATE users SET premium_until = ? WHERE telegram_id = ?", 
                (date_str, user_id)
            )
            await db.commit()

    # --- МЕТОДЫ ДЛЯ АДМИН ПАНЕЛИ ---

    async def get_all_user_ids(self) -> List[int]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT telegram_id FROM users") as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    async def update_user_status(self, user_id: int, is_premium: bool):
        async with aiosqlite.connect(self.db_path) as db:
            status = 1 if is_premium else 0
            await db.execute(
                "UPDATE users SET is_premium = ? WHERE telegram_id = ?",
                (status, user_id)
            )
            await db.commit()

    # --- МЕТОДЫ ДЛЯ РЕФЕРАЛОВ ---

    async def add_referral(self, user_id: int, referrer_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            user = await self.get_user(user_id)
            if not user:
                # При регистрации по рефке сразу даем премиум-флаг
                await db.execute(
                    "INSERT INTO users (telegram_id, is_premium, referred_by) VALUES (?, ?, ?)",
                    (user_id, 1, referrer_id)
                )
                await db.commit()
                return True
            return False

    async def get_referrals_count(self, user_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,)) as cursor:
                res = await cursor.fetchone()
                return res[0] if res else 0

    # --- ОСТАЛЬНЫЕ МЕТОДЫ ---

    async def get_user(self, telegram_id: int) -> Optional[User]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    data = dict(row)
                    data['is_premium'] = bool(data.get('is_premium', 0))
                    data['is_banned'] = bool(data.get('is_banned', 0))
                    return User(**data)
                return None

    async def register_user(self, telegram_id: int, age: int, gender: str, first_name: str = "Аноним"):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO users (telegram_id, age, gender, first_name) VALUES (?, ?, ?, ?)",
                (telegram_id, age, gender, first_name)
            )
            await db.execute(
                "UPDATE users SET age = ?, gender = ?, first_name = ? WHERE telegram_id = ?",
                (age, gender, first_name, telegram_id)
            )
            await db.commit()

    async def set_partner(self, telegram_id: int, partner_id: Optional[int]):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET partner_id = ? WHERE telegram_id = ?", (partner_id, telegram_id))
            if partner_id:
                await db.execute("""
                    UPDATE users 
                    SET total_dialogs = total_dialogs + 1, 
                        today_dialogs = today_dialogs + 1 
                    WHERE telegram_id = ?
                """, (telegram_id,))
            await db.commit()

    async def update_search_gender(self, telegram_id: int, search_gender: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET search_gender = ? WHERE telegram_id = ?", (search_gender, telegram_id))
            await db.commit()

    async def set_ban_status(self, user_id: int, status: bool):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET is_banned = ? WHERE telegram_id = ?", (1 if status else 0, user_id))
            await db.commit()

    async def get_total_users(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                res = await cursor.fetchone()
                return res[0] if res else 0

from config import DB_NAME
db_manager = Database(DB_NAME)