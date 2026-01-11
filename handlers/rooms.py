from aiogram import Router, types, F
from database.models import db_manager
from keyboards.reply import main_menu

router = Router()

@router.message(F.text == "❤️ Флирт-чат")
async def enter_flirt_room(message: types.Message):
    await db_manager.set_user_room(message.from_user.id, "flirt")
    
    # Можно добавить красивую картинку или стикер
    await message.answer(
        "🔥 **Вы вошли в Флирт-чат!**\n\n"
        "Здесь общение более смелое. Нажмите «Поиск», чтобы найти пару для флирта.",
        parse_mode="Markdown"
    )

@router.message(F.text == "💬 Общение")
async def enter_common_room(message: types.Message):
    await db_manager.set_user_room(message.from_user.id, "common")
    await message.answer("✅ Вы вернулись в обычный чат для дружеского общения.")
