from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

async def set_commands(bot: Bot, admin_ids: list):
    # 1. Команды для ВСЕХ пользователей
    user_commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="search", description="Найти собеседника"),
        BotCommand(command="next", description="Следующий собеседник"),
        BotCommand(command="stop", description="Остановить диалог"),
        BotCommand(command="profile", description="Мой профиль"),
        BotCommand(command="vip", description="PREMIUM статус"),
    ]
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    # 2. Команды специально для АДМИНИСТРАТОРОВ
    admin_commands = user_commands + [
        BotCommand(command="admin", description="Админ-панель (только для админа)")
    ]
    
    for admin_id in admin_ids:
        try:
            await bot.set_my_commands(
                admin_commands, 
                scope=BotCommandScopeChat(chat_id=admin_id)
            )
        except Exception as e:
            print(f"Не удалось установить команды для админа {admin_id}: {e}")