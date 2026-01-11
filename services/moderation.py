import logging
from database.models import db_manager
from config import ADMIN_IDS
from aiogram import Bot

# Порог жалоб, после которого наступает автоматический бан
BAN_THRESHOLD = 3

class ModerationService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def handle_report(self, reporter_id: int, reported_id: int):
        """
        Обрабатывает жалобу, проверяет порог и банит при необходимости.
        Возвращает: (is_banned: bool, reports_count: int)
        """
        # 1. Добавляем жалобу в БД через наш db_manager
        count = await db_manager.add_report(reporter_id, reported_id)
        
        is_newly_banned = False

        # 2. Проверяем, не пора ли банить
        if count >= BAN_THRESHOLD:
            user = await db_manager.get_user(reported_id)
            if not user.is_banned:
                await db_manager.update_user(reported_id, is_banned=1)
                is_newly_banned = True
                
                # Уведомляем админов о бане
                await self.notify_admins(reported_id, count)
                
                # Уведомляем самого нарушителя
                try:
                    await self.bot.send_message(
                        reported_id, 
                        "?? Вы были автоматически заблокированы за многочисленные жалобы пользователей."
                    )
                except Exception:
                    pass

        return is_newly_banned, count

    async def notify_admins(self, user_id: int, reports_count: int):
        """Отправка уведомления администраторам о новом бане."""
        for admin_id in ADMIN_IDS:
            try:
                await self.bot.send_message(
                    admin_id,
                    f"? **Авто-бан**\n\n"
                    f"Пользователь ID: `{user_id}`\n"
                    f"Количество жалоб: `{reports_count}`\n"
                    f"Статус: Заблокирован системой.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logging.error(f"Ошибка уведомления админа {admin_id}: {e}")

    async def check_ban(self, user_id: int) -> bool:
        """Быстрая проверка, забанен ли пользователь."""
        user = await db_manager.get_user(user_id)
        return user.is_banned if user else False

# Инициализируем в main.py и прокидываем в хендлеры
