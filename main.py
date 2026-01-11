# -*- coding: utf-8 -*-
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from config import BOT_TOKEN, ADMIN_IDS 
from database.models import db_manager
from services.matcher import matcher

# Импортируем роутеры
from handlers import admin, start, profile, chat

# --- ФУНКЦИЯ ЕЖЕНЕДЕЛЬНОЙ РАССЫЛКИ ТОПА ---
async def weekly_top_newsletter(bot: Bot):
    print("📢 Запуск еженедельной рассылки ТОПа и выдача наград...")
    top_users = await db_manager.get_top_users(10)
    
    if not top_users:
        print("Отмена рассылки: нет пользователей с рейтингом.")
        return

    # --- ВЫДАЧА ПРЕМИУМА ПОБЕДИТЕЛЮ ---
    winner = top_users[0]  # Самый первый в списке
    winner_id = winner.get('telegram_id')
    winner_name = winner.get('first_name') or "Аноним"
    
    # Выдаем премиум в базе данных
    await db_manager.set_premium(winner_id, True)
    # ----------------------------------

    # Формируем текст
    text = "🏆 <b>ИТОГИ НЕДЕЛИ: ТОП-10 ПОПУЛЯРНОСТИ</b>\n"
    text += "━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, user in enumerate(top_users, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "👤"
        name = user.get('first_name') or "Аноним"
        rating = user.get('rating') or 0
        
        if i == 1:
            text += f"{medal} <b>{name}</b> — {rating} ⭐ (ПОБЕДИТЕЛЬ!)\n"
        else:
            text += f"{medal} {i}. <b>{name}</b> — {rating} ⭐\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━\n"
    text += f"🎉 Поздравляем <b>{winner_name}</b>!\n"
    text += "🎁 Как лидер рейтинга, ты получаешь <b>PREMIUM на 7 дней!</b>\n\n"
    text += "🔥 Хочешь так же? Получай лайки от собеседников и стань лучшим на следующей неделе!"

    all_user_ids = await db_manager.get_all_active_users()
    
    count = 0
    for user_id in all_user_ids:
        try:
            await bot.send_message(user_id, text, parse_mode="HTML")
            # Отдельное уведомление победителю, чтобы он точно заметил
            if user_id == winner_id:
                await bot.send_message(user_id, "🌟 Тебе начислен заслуженный PREMIUM статус за 1-е место в топе!")
            
            count += 1
            await asyncio.sleep(0.05) 
        except Exception:
            continue
    
    print(f"✅ Рассылка завершена. Победитель {winner_name} получил VIP.")

# 1. Функция регистрации команд
async def set_commands(bot: Bot):
    user_commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="search", description="Найти собеседника"),
        BotCommand(command="next", description="Следующий собеседник"),
        BotCommand(command="stop", description="Остановить диалог"),
        BotCommand(command="profile", description="Мой профиль"),
        BotCommand(command="referals", description="👥 Реферальная система"),
        BotCommand(command="help", description="🆘 Помощь и команды"),
        BotCommand(command="rules", description="ℹ️ Правила чата"),
        BotCommand(command="vip", description="PREMIUM статус"),
        BotCommand(command="sharelink", description="Поделиться своим профилем")
    ]
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    admin_commands = user_commands + [
        BotCommand(command="admin", description="Админ-панель (только для админа)")
    ]
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.set_my_commands(
                admin_commands, 
                scope=BotCommandScopeChat(chat_id=admin_id)
            )
        except Exception as e:
            logging.error(f"Не удалось установить команды для админа {admin_id}: {e}")

# 2. Действия при старте
async def on_startup(bot: Bot):
    matcher.queue = [] 
    print("🧹 Очередь поиска очищена после перезапуска")
    await set_commands(bot)

async def main():
    logging.basicConfig(level=logging.INFO)
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Инициализация БД
    await db_manager.init()

    # --- НАСТРОЙКА ПЛАНИРОВЩИКА ---
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    # Запуск каждый понедельник в 00:00
    scheduler.add_job(weekly_top_newsletter, "cron", day_of_week='mon', hour=0, minute=0, args=[bot])
    scheduler.start()
    print("⏰ Планировщик рассылок запущен!")

    # --- РЕГИСТРАЦИЯ РОУТЕРОВ ---
    dp.include_router(chat.router)
    dp.include_router(admin.router) 
    dp.include_router(start.router)
    dp.include_router(profile.router)

    await on_startup(bot)

    # Запуск воркера матчинга
    asyncio.create_task(matcher.worker(bot, dp.storage))
    print("🚀 ВОРКЕР ЗАПУЩЕН И ГОТОВ СОЕДИНЯТЬ!")

    print("🚀 Бот запущен и готов к работе!")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот выключен")