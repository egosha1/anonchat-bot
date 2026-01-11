# services/matcher.py
import asyncio
from aiogram import Bot
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.models import db_manager
from states import UserStates
from keyboards.reply import chat_menu

class Matcher:
    def __init__(self):
        self.queue = []

    async def add_to_queue(self, user_id: int):
        if user_id not in self.queue:
            self.queue.append(user_id)
            print(f"DEBUG: {user_id} добавлен в очередь.")

    async def remove_from_queue(self, user_id: int):
        if user_id in self.queue:
            self.queue.remove(user_id)
            print(f"DEBUG: {user_id} удален из очереди.")

    def _check_gender_match(self, u1, u2):
        s1 = getattr(u1, 'search_gender', 'both') or 'both'
        s2 = getattr(u2, 'search_gender', 'both') or 'both'
        u1_ok = (s1 == 'both' or s1 == u2.gender)
        u2_ok = (s2 == 'both' or s2 == u1.gender)
        return u1_ok and u2_ok

    async def worker(self, bot: Bot, storage):
        print("🚀 ВОРКЕР ЗАПУЩЕН!")
        while True:
            await asyncio.sleep(1)
            if len(self.queue) < 2:
                continue

            u_list = self.queue[:] 
            for i, u1_id in enumerate(u_list):
                if u1_id not in self.queue: continue
                u1 = await db_manager.get_user(u1_id)
                if not u1 or u1.partner_id:
                    if u1_id in self.queue: self.queue.remove(u1_id)
                    continue

                for u2_id in u_list[i+1:]:
                    if u2_id not in self.queue: continue
                    u2 = await db_manager.get_user(u2_id)
                    if not u2 or u2.partner_id:
                        if u2_id in self.queue: self.queue.remove(u2_id)
                        continue

                    if (u1.room or "common") != (u2.room or "common"): continue 
                    if not self._check_gender_match(u1, u2): continue 

                    try:
                        await db_manager.set_partner(u1_id, u2_id)
                        await db_manager.set_partner(u2_id, u1_id)

                        if u1_id in self.queue: self.queue.remove(u1_id)
                        if u2_id in self.queue: self.queue.remove(u2_id)

                        for uid in [u1_id, u2_id]:
                            await storage.set_state(
                                StorageKey(bot_id=bot.id, chat_id=uid, user_id=uid), 
                                UserStates.IN_CHAT
                            )

                        # ИСПРАВЛЕННАЯ ФУНКЦИЯ: viewer_is_premium определяет видимость
                        def get_profile_text(target_user, viewer_is_premium):
                            # Метка премиума (показываем, если у ЦЕЛИ есть премиум)
                            is_target_prem = getattr(target_user, 'is_premium', False)
                            prem_label = " 💎 PREM" if is_target_prem else ""
                            
                            g_map = {"Мужской": "Мужской 👱", "Женский": "Женский 👩", "male": "Мужской 👱", "female": "Женский 👩"}

                            # ГЛАВНОЕ УСЛОВИЕ: Инфо видит только тот, у кого САМОГО есть премиум
                            if viewer_is_premium:
                                gender = g_map.get(target_user.gender, "Не указан 😶")
                                age = getattr(target_user, 'age', 'Не указан')
                                reg = getattr(target_user, 'region', 'Не указан 🌍')
                            else:
                                gender = "Скрыто 🔒"
                                age = "Скрыто 🔒"
                                reg = "Скрыто 🔒"

                            rating = getattr(target_user, 'rating', 0)
                            d = getattr(target_user, 'dislikes', 0)
                            
                            return (
                                f"🤝 <b>Собеседник найден!</b>{prem_label}\n"
                                f"━━━━━━━━━━━━━━\n"
                                f"👤 <b>Пол:</b> {gender}\n"
                                f"🗓 <b>Возраст:</b> {age}\n"
                                f"📍 <b>Регион:</b> {reg}\n"
                                f"🌟 <b>Оценки:</b> {rating} 👍 / {d} 👎\n"
                                f"━━━━━━━━━━━━━━\n"
                                f"Приятного общения!"
                            )

                        game_kb = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🎲 Предложить игру", callback_data="propose_game")]
                        ])

                        # Отправляем u1 инфу про u2 (проверяем премиум у u1)
                        u1_prem = getattr(u1, 'is_premium', False)
                        await bot.send_message(u1_id, get_profile_text(u2, u1_prem), reply_markup=chat_menu, parse_mode="HTML")
                        await bot.send_message(u1_id, "Хотите сыграть в 'Правда или Действие'?", reply_markup=game_kb)
                        
                        # Отправляем u2 инфу про u1 (проверяем премиум у u2)
                        u2_prem = getattr(u2, 'is_premium', False)
                        await bot.send_message(u2_id, get_profile_text(u1, u2_prem), reply_markup=chat_menu, parse_mode="HTML")
                        await bot.send_message(u2_id, "Хотите сыграть в 'Правда или Действие'?", reply_markup=game_kb)

                        break 

                    except Exception as e:
                        print(f"❌ ОШИБКА: {e}")
                        continue

matcher = Matcher()