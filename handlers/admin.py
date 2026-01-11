# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
import asyncio
from aiogram import Router, types, F, Bot
from aiogram.filters import Command, Filter, CommandObject
from database.models import db_manager
from services.matcher import matcher

router = Router()

# Твой ID
ADMIN_ID = 7842274559 

# Исправленный класс фильтра
class IsAdmin(Filter):
    async def __call__(self, message: types.Message) -> bool:
        return message.from_user.id == ADMIN_ID
# 1. ГЛАВНАЯ ПАНЕЛЬ
@router.message(Command("admin"), IsAdmin())
async def admin_panel(message: types.Message):
    total = await db_manager.get_total_users()
    in_queue = len(matcher.queue)
    
    text = (
        "🛠 <b>Админ-панель</b>\n\n"
        f"👥 Всего пользователей: <code>{total}</code>\n"
        f"⏳ Сейчас в очереди: <code>{in_queue}</code>\n\n"
        "<b>Команды:</b>\n"
        "📢 <code>/broadcast текст</code> — рассылка\n"
        "💎 <code>/giveprem ID</code> — выдать VIP\n"
        "🚫 <code>/takeprem ID</code> — забрать VIP"
    )
    await message.answer(text, parse_mode="HTML")

# 2. РАССЫЛКА (BROADCAST)
@router.message(Command("broadcast"), IsAdmin())
async def cmd_broadcast(message: types.Message, bot: Bot):
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        return await message.answer("Введите текст: <code>/broadcast привет</code>")

    users = await db_manager.get_all_user_ids()
    count = 0
    
    await message.answer(f"🚀 Начинаю рассылку на {len(users)} пользователей...")
    
    for user_id in users:
        try:
            await bot.send_message(user_id, text)
            count += 1
            await asyncio.sleep(0.05) # Защита от спам-фильтра Telegram
        except Exception:
            pass
            
    await message.answer(f"✅ Рассылка завершена. Получили: {count}")

# 3. ВЫДАЧА/СНЯТИЕ PREMIUM
@router.message(Command("giveprem"), IsAdmin())
async def cmd_give_prem(message: types.Message):
    try:
        user_id = int(message.text.split()[1])
        await db_manager.set_premium_status(user_id, True)
        await message.answer(f"💎 Пользователю <code>{user_id}</code> выдан PREMIUM!")
    except:
        await message.answer("Ошибка. Формат: <code>/giveprem 12345678</code>")

@router.message(Command("takeprem"))
async def admin_take_premium(message: types.Message, command: CommandObject):
    # Проверка, что команду вызвал админ (замени на свой ID или проверку из БД)
    # if message.from_user.id != ADMIN_ID: return

    if not command.args:
        return await message.answer("Ошибка. Формат: <code>/takeprem 12345678</code>", parse_mode="HTML")

    try:
        user_id = int(command.args.strip()) # strip() уберет лишние пробелы
        user = await db_manager.get_user(user_id)
        
        if not user:
            return await message.answer("Пользователь не найден в базе данных.")

        # Устанавливаем статус премиума в 0 (False)
        await db_manager.update_user_status(user_id, is_premium=False)
        
        await message.answer(f"✅ У пользователя <code>{user_id}</code> успешно отозван PREMIUM статус.", parse_mode="HTML")
        
        # Опционально: уведомляем пользователя
        try:
            await message.bot.send_message(user_id, "ℹ️ Ваш PREMIUM статус был отозван администратором.")
        except:
            pass

    except ValueError:
        await message.answer("Ошибка: ID должен состоять только из цифр.")
# # 4. БАН / РАЗБАН
@router.message(Command("ban"), IsAdmin())
async def cmd_ban(message: types.Message, bot: Bot):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            return await message.answer("Введите ID: <code>/ban 12345678</code>", parse_mode="HTML")
            
        user_id = int(parts[1])
        await db_manager.set_ban_status(user_id, True)
        
        # Разрываем чат, если он активен
        user = await db_manager.get_user(user_id)
        if user and user.partner_id:
            p_id = user.partner_id
            await db_manager.set_partner(user_id, None)
            await db_manager.set_partner(p_id, None)
            try:
                await bot.send_message(p_id, "🛑 Собеседник был заблокирован за нарушение правил. Чат завершен.", reply_markup=main_menu)
            except: pass

        await message.answer(f"🚫 Пользователь <code>{user_id}</code> заблокирован.", parse_mode="HTML")
        try:
            await bot.send_message(user_id, "❌ Вы были заблокированы администрацией за нарушение правил.")
        except: pass
    except ValueError:
        await message.answer("Ошибка! ID должен состоять только из цифр.", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"Ошибка при бане: {e}")

@router.message(Command("unban"), IsAdmin())
async def cmd_unban(message: types.Message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            return await message.answer("Введите ID: <code>/unban 12345678</code>", parse_mode="HTML")

        user_id = int(parts[1])
        await db_manager.set_ban_status(user_id, False)
        await message.answer(f"✅ Пользователь <code>{user_id}</code> разблокирован.", parse_mode="HTML")
    except:
        await message.answer("Ошибка формата. Используйте: <code>/unban ID</code>", parse_mode="HTML")