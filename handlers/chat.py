# -*- coding: utf-8 -*-
import random
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.filters import Command 
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from database.models import db_manager
from states import UserStates
# Импортируем меню
from keyboards.reply import main_menu, stop_search_menu, chat_menu, game_menu
from services.matcher import matcher

router = Router()

# --- РАСШИРЕННАЯ И ПИКАНТНАЯ БАЗА ИГРЫ ---
GAMES_DB = {
    "common": {
        "truth": [
            "Какое твоё самое странное хобби?",
            "О чем ты больше всего жалеешь?",
            "Если бы ты мог стать невидимым на час, что бы ты сделал?",
            "Какой самый неловкий поступок ты совершал в школе?",
            "Веришь ли ты в привидений или инопланетян?",
            "Какую самую большую ложь ты когда-либо говорил родителям?",
            "Что бы ты купил первым, если бы выиграл миллион долларов?",
            "Кто твой тайный кумир, о котором никто не знает?",
            "Какая песня у тебя на повторе, но тебе стыдно в этом признаться?",
            "Если бы ты мог поменять одну вещь в своем прошлом, что бы это было?",
            "Твой самый большой страх в жизни?",
            "Какое самое странное блюдо ты когда-либо пробовал?",
            "Был ли у тебя когда-нибудь воображаемый друг?",
            "Какую кличку тебе давали в детстве и за что?"
        ],
        "dare": [
            "Пришли свое самое смешное селфи.",
            "Напиши сообщение любому контакту: 'Я знаю твой секрет...'",
            "Расскажи анекдот прямо сейчас.",
            "Сделай скриншот своего последнего прослушанного трека.",
            "Отправь голосовое сообщение с имитацией звуков животного.",
            "Поставь в описание профиля фразу 'Я люблю пылесосить' на 10 минут.",
            "Пришли фото своих носков (или босых ног).",
            "Опиши собеседника пятью прилагательными.",
            "Пришли скриншот своих последних пяти вызовов в телефоне.",
            "Напиши в чат текст песни, которую ты сейчас вспомнишь первой.",
            "Попробуй написать предложение носом и отправь результат.",
            "Скинь ссылку на свое любимое видео в YouTube."
        ]
    },
    "flirt": {
        "truth": [
            "Твое самое смелое эротическое желание, которое ты еще не воплотил(а)?",
            "В каком самом необычном месте у тебя был секс или поцелуй?",
            "Что в противоположном поле заводит тебя с первых секунд?",
            "Твое отношение к сексу на первом свидании?",
            "Ты когда-нибудь фантазировал(а) о ком-то, кого мы оба знаем?",
            "Какая часть твоего тела самая чувствительная?",
            "Любишь ли ты доминировать или предпочитаешь подчиняться?",
            "Опиши свое самое горячее свидание в жизни.",
            "Твое самое запретное удовольствие (guilty pleasure) в постели?",
            "Снимал(а) ли ты когда-нибудь видео или фото интимного характера?",
            "Какое нижнее белье на партнере кажется тебе самым сексуальным?",
            "Веришь ли ты, что секс без любви может быть крутым?",
            "Что бы ты сделал(а) со мной, если бы мы сейчас оказались в одной комнате?",
            "Твой самый безумный поступок ради любви или секса?"
        ],
        "dare": [
            "Сфотографируй свои губы максимально близко и соблазнительно.",
            "Опиши словами, как бы ты меня сейчас поцеловал(а).",
            "Пришли фото своего домашнего образа (домашняя одежда).",
            "Напиши самое пошлое сообщение, которое тебе когда-либо присылали.",
            "Запиши короткое голосовое сообщение с томным шепотом.",
            "Сфотографируй свою шею или ключицы и пришли в чат.",
            "Пришли эмодзи, которое лучше всего описывает твой уровень возбуждения сейчас.",
            "Опиши в деталях, в чем ты сейчас одет(а), включая нижнее белье.",
            "Сделай фото своего отражения в зеркале (без лица, только силуэт).",
            "Назови три вещи, которые я должен(на) сделать, чтобы ты потерял(а) голову.",
            "Пришли фото своей руки на бедре.",
            "Напиши, какую именно часть моего тела ты бы хотел(а) коснуться первой.",
            "Расскажи о своей самой дикой фантазии, связанной с незнакомцем."
        ]
    }
}

def get_rating_kb(target_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍 Лайк", callback_data=f"rate_plus_{target_id}"),
            InlineKeyboardButton(text="👎 Дизлайк", callback_data=f"rate_minus_{target_id}")
        ]
    ])

GIFT_TEXT = "\n\n<i>Самых залайканных пользователей будут ждать ценные подарки в конце месяца! 🎁</i>"

async def is_banned(user_id: int, message: types.Message) -> bool:
    user = await db_manager.get_user(user_id)
    if user and user.is_banned:
        await message.answer("❌ Доступ к боту ограничен администрацией.")
        return True
    return False

# --- ЗАПРЕТ НА @USERNAME (Ставим выше пересылки!) ---
@router.message(UserStates.IN_CHAT, F.text.contains("@"))
async def block_usernames(message: Message):
    await message.answer("⚠️ В целях безопасности отправка @username запрещена. \nИспользуйте команду /sharelink, чтобы поделиться своим профилем.")

# --- КОМАНДА /sharelink ---
@router.message(Command("sharelink"), UserStates.IN_CHAT)
async def share_link_handler(message: Message, bot: Bot):
    user_id = message.from_user.id
    user = await db_manager.get_user(user_id)
    
    if not user or not user.partner_id:
        return await message.answer("Вы не находитесь в чате.")

    my_username = f"@{message.from_user.username}" if message.from_user.username else "не установлен"
    
    if my_username == "не установлен":
        return await message.answer("У вас не установлен username в настройках Telegram, нечем делиться.")

    try:
        await bot.send_message(
            user.partner_id, 
            f"🔔 Собеседник открыл свой профиль: {my_username}"
        )
        await message.answer("✅ Ваш профиль отправлен собеседнику!")
    except Exception:
        await message.answer("Произошла ошибка при отправке ссылки.")

# --- НОВАЯ ЛОГИКА: ПРЕДЛОЖЕНИЕ И ПРИНЯТИЕ ИГРЫ ---
@router.callback_query(F.data == "propose_game")
async def process_propose_game(callback: CallbackQuery, bot: Bot):
    user = await db_manager.get_user(callback.from_user.id)
    if user and user.partner_id:
        accept_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Давай играть!", callback_data="accept_game")]
        ])
        
        await bot.send_message(
            user.partner_id, 
            f"🔔 Собеседник предлагает сыграть в <b>'Правда или Действие'</b>!",
            reply_markup=accept_kb,
            parse_mode="HTML"
        )
        await callback.answer("Предложение отправлено!")
        await callback.message.edit_text("⏳ Ждем ответа собеседника...")
    else:
        await callback.answer("Вы не в чате!")

@router.callback_query(F.data == "accept_game")
async def process_accept_game(callback: CallbackQuery, bot: Bot):
    user = await db_manager.get_user(callback.from_user.id)
    if user and user.partner_id:
        my_id = callback.from_user.id
        partner_id = user.partner_id

        await bot.send_message(my_id, "🎉 Начинаем игру!", reply_markup=game_menu)
        await bot.send_message(partner_id, "🎉 Собеседник принял вызов! Начинаем игру.", reply_markup=game_menu)
        
        try:
            await callback.message.delete()
        except: pass
    else:
        await callback.answer("Чат уже завершен или партнер ушел.")

# --- ЗАВЕРШЕНИЕ ИГРЫ ---
@router.message(F.text == "📥 Закончить игру", UserStates.IN_CHAT)
async def stop_game_process(message: types.Message, bot: Bot):
    user = await db_manager.get_user(message.from_user.id)
    if user and user.partner_id:
        await message.answer("Вы закончили игру.", reply_markup=chat_menu)
        await bot.send_message(user.partner_id, "🔔 Собеседник закончил игру.", reply_markup=chat_menu)

# --- ЛОГИКА ИГРЫ (КНОПКИ В МЕНЮ) ---
@router.message(F.text.in_(["🎲 Правда", "🔥 Действие"]), UserStates.IN_CHAT)
async def play_game(message: types.Message, bot: Bot):
    if await is_banned(message.from_user.id, message): return
    
    user = await db_manager.get_user(message.from_user.id)
    if not user or not user.partner_id: return

    category = "truth" if "Правда" in message.text else "dare"
    room = user.room if user.room in GAMES_DB else "common"
    task = random.choice(GAMES_DB[room][category])
    
    game_name = "ПРАВДА" if category == "truth" else "ДЕЙСТВИЕ"
    game_msg = (
        f"🎲 <b>ИГРА: {game_name}</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"Задание для: <b>{message.from_user.first_name}</b>\n"
        f"👉 <i>{task}</i>\n"
        f"━━━━━━━━━━━━━━"
    )
    await message.answer(game_msg, parse_mode="HTML")
    await bot.send_message(user.partner_id, game_msg, parse_mode="HTML")

# --- ОСТАНОВКА ДИАЛОГА ---
@router.message(Command("stop"))
@router.message(F.text == "❌ Остановить диалог")
async def stop_chat(message: types.Message, state: FSMContext, bot: Bot):
    if await is_banned(message.from_user.id, message): return
    user = await db_manager.get_user(message.from_user.id)
    current_state = await state.get_state()

    if current_state == UserStates.SEARCH:
        await matcher.remove_from_queue(message.from_user.id)
        await state.set_state(UserStates.IDLE)
        return await message.answer("🔍 Поиск остановлен.", reply_markup=main_menu)

    if user and user.partner_id:
        p_id = user.partner_id
        my_id = message.from_user.id
        try:
            await bot.send_message(p_id, "🛑 Собеседник завершил чат.")
            await bot.send_message(p_id, "🗣️ <b>Можешь оставить отзыв о своем собеседнике?</b>" + GIFT_TEXT,
                               reply_markup=get_rating_kb(my_id), parse_mode="HTML")
            await bot.send_message(p_id, "Вы вернулись в меню.", reply_markup=main_menu)

            await message.answer("👋 Вы завершили диалог.")
            await message.answer("🗣️ <b>Можешь оставить отзыв о своем собеседнике?</b>" + GIFT_TEXT,
                               reply_markup=get_rating_kb(p_id), parse_mode="HTML")
            await message.answer("Вы вернулись в меню.", reply_markup=main_menu)
        except: pass

        await db_manager.set_partner(my_id, None)
        await db_manager.set_partner(p_id, None)
        await state.set_state(UserStates.IDLE)
        await state.storage.set_state(StorageKey(bot_id=bot.id, chat_id=p_id, user_id=p_id), UserStates.IDLE)
    else:
        await state.set_state(UserStates.IDLE)
        await message.answer("У вас нет активного чата.", reply_markup=main_menu)

# --- СЛЕДУЮЩИЙ СОБЕСЕДНИК ---
@router.message(Command("next"))
@router.message(F.text == "⏭ Следующий собеседник")
async def next_partner(message: types.Message, state: FSMContext, bot: Bot):
    if await is_banned(message.from_user.id, message): return
    user = await db_manager.get_user(message.from_user.id)
    my_id = message.from_user.id
    
    if user and user.partner_id:
        p_id = user.partner_id
        try:
            await bot.send_message(p_id, "🛑 Собеседник завершил чат.")
            await bot.send_message(p_id, "🗣️ <b>Можешь оставить отзыв о своем собеседнике?</b>" + GIFT_TEXT,
                               reply_markup=get_rating_kb(my_id), parse_mode="HTML")
            await bot.send_message(p_id, "Вы вернулись в меню.", reply_markup=main_menu)
            
            await message.answer("👋 Диалог завершен.")
            await message.answer("🗣️ <b>Можешь оставить отзыв о предыдущем собеседнике?</b>" + GIFT_TEXT,
                               reply_markup=get_rating_kb(p_id), parse_mode="HTML")
        except: pass
        await db_manager.set_partner(my_id, None)
        await db_manager.set_partner(p_id, None)
        await state.storage.set_state(StorageKey(bot_id=bot.id, chat_id=p_id, user_id=p_id), UserStates.IDLE)

    await state.set_state(UserStates.SEARCH)
    await matcher.add_to_queue(my_id)
    await message.answer("🔄 Ищу нового собеседника...", reply_markup=stop_search_menu)

# --- ОБРАБОТКА РЕЙТИНГА ---
@router.callback_query(F.data.startswith("rate_"))
async def process_rating(callback: CallbackQuery):
    data = callback.data.split("_")
    await db_manager.update_rating(int(data[2]), data[1] == "plus")
    await callback.answer("Спасибо за оценку!")
    await callback.message.edit_text("✅ Рейтинг обновлен! Спасибо за ваш отзыв.")

# --- ПЕРЕСЫЛКА СООБЩЕНИЙ (В самом низу!) ---
@router.message(UserStates.IN_CHAT)
async def echo_chat(message: Message, bot: Bot):
    if await is_banned(message.from_user.id, message): return
    user = await db_manager.get_user(message.from_user.id)
    if user and user.partner_id:
        try:
            await message.send_copy(chat_id=user.partner_id)
        except:
            await message.answer("⚠️ Собеседник недоступен.")