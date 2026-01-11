# -*- coding: utf-8 -*-
import aiosqlite
from dataclasses import dataclass
from typing import Optional, List

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
                    referred_by INTEGER
                )
            """)
            
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
                "referred_by": "INTEGER"
            }
            
            for col_name, col_type in cols.items():
                try:
                    await db.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                except:
                    pass
            await db.commit()

    # --- МЕТОДЫ ДЛЯ АДМИН ПАНЕЛИ ---

    async def get_all_user_ids(self) -> List[int]:
        """Возвращает список ID всех зарегистрированных пользователей для рассылки"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT telegram_id FROM users") as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    async def update_user_status(self, user_id: int, is_premium: bool):
        """Обновляет статус премиума для пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            # В БД 1 — это True, 0 — это False
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
                await db.execute(
                    "INSERT INTO users (telegram_id, is_premium, referred_by) VALUES (?, ?, ?)",
                    (user_id, 1, referrer_id)
                )
                await db.execute(
                    "UPDATE users SET rating = rating + 50 WHERE telegram_id = ?",
                    (referrer_id,)
                )
                await db.commit()
                return True
            return False

    async def get_referrals_count(self, user_id: int) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,)) as cursor:
                res = await cursor.fetchone()
                return res[0] if res else 0

    # --- МЕТОДЫ ДЛЯ ТОПА ---

    async def get_top_users(self, limit: int = 10) -> List[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT telegram_id, first_name, rating FROM users "
                "WHERE rating > 0 AND is_banned = 0 "
                "ORDER BY rating DESC LIMIT ?", (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_all_active_users(self) -> List[int]:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT telegram_id FROM users WHERE is_banned = 0") as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

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

    async def update_rating(self, telegram_id: int, is_like: bool):
        async with aiosqlite.connect(self.db_path) as db:
            if is_like:
                await db.execute("UPDATE users SET likes = likes + 1, rating = rating + 1 WHERE telegram_id = ?", (telegram_id,))
            else:
                await db.execute("UPDATE users SET dislikes = dislikes + 1, rating = rating - 1 WHERE telegram_id = ?", (telegram_id,))
            await db.commit()

    async def set_premium(self, user_id: int, status: bool):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET is_premium = ? WHERE telegram_id = ?", (1 if status else 0, user_id))
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