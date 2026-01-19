# -*- coding: utf-8 -*-
import aiosqlite
from datetime import datetime, timedelta # ДОБАВИЛИ ИМПОРТ ДЛЯ ВРЕМЕНИ
from aiogram import Router, types, F, Bot
from aiogram.filters import Command, CommandObject # Добавили CommandObject для аргументов
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from states import UserStates
from database.models import db_manager
from keyboards.reply import main_menu, stop_search_menu
from services.matcher import matcher
from config import DB_NAME

router = Router()

# --- 1. ПОИСК СОБЕСЕДНИКА ---
@router.message(Command("search"))
@router.message(F.text == "🔍 Найти собеседника")
async def start_search(message: types.Message, state: FSMContext):
    user = await db_manager.get_user(message.from_user.id)
    
    if user and user.is_banned:
        return await message.answer("❌ Доступ к боту ограничен администрацией.")
    
    if not user or not user.age or not user.gender:
        await message.answer("Сначала заполни анкету! 👋\nСколько тебе лет?")
        return await state.set_state(UserStates.REG_AGE)

    await state.set_state(UserStates.SEARCH)
    await matcher.add_to_queue(message.from_user.id)
    await message.answer("🔍 Начинаю поиск... Чтобы отменить, нажми кнопку ниже.", reply_markup=stop_search_menu)

@router.message(F.text == "❌ Остановить поиск", UserStates.SEARCH)
async def stop_search(message: types.Message, state: FSMContext):
    await matcher.remove_from_queue(message.from_user.id)
    await state.set_state(UserStates.IDLE)
    await message.answer("🛑 Поиск остановлен.", reply_markup=main_menu)

# --- 2. ПОМОЩЬ И ПРАВИЛА (/HELP) ---
@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = (
        "<b>Анонимный чат-бот найдет собеседника для общения по интересам и полу!</b>\n\n"
        "<b>Доступные команды:</b>\n\n"
        "/vip - Подробней о 💎 <b>PREMIUM</b> статусе\n"
        "/profile - Посмотреть или изменить свой профиль\n"
        "/referals - 👥 Реферальная система\n"
        "/rules - ℹ️ Правила общения\n\n"
        "/next - ⏩ Следующий собеседник\n"
        "/search - 🔍 Поиск собеседника\n"
        "/stop - 🚫 Закончить диалог\n\n"
        "<i>Все команды всегда доступны по кнопке «Меню» в левой нижней части экрана</i>\n\n"
        "В чате ты можешь отправлять мне текст, ссылки, гифки, стикеры, фотографии, "
        "видео или голосовые сообщения, и я их анонимно перешлю Вашему собеседнику."
    )
    await message.answer(text, parse_mode="HTML")

@router.message(Command("rules"))
async def cmd_rules(message: types.Message):
    rules_url = "https://telegra.ph/Pravila-anonimnogo-chata-05-22"
    text = (
        f"<a href='{rules_url}'>&#8203;</a>"
        "Любой пользователь автоматически будет заблокирован, "
        "если он нарушит правила общения в нашем чате.\n\n"
        "<b>Правила анонимного чата</b>\n"
        "Анонимный чат — это платформа для общения с людьми "
        "разного происхождения и убеждений..."
    )
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="⚡️ ПОСМОТРЕТЬ", url=rules_url))
    await message.answer(
        text, parse_mode="HTML", reply_markup=builder.as_markup(),
        link_preview_options=types.LinkPreviewOptions(is_disabled=False, url=rules_url, prefer_large_media=True)
    )

# --- 3. РЕФЕРАЛЬНАЯ СИСТЕМА ---
@router.message(Command("referals"))
@router.message(F.text == "👥 Рефералы")
@router.callback_query(F.data == "invite_friend")
async def show_referals(event: types.Message | types.CallbackQuery):
    user_id = event.from_user.id
    bot_info = await event.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    count = await db_manager.get_referrals_count(user_id)
    
    text = (
        "👥 <b>РЕФЕРАЛЬНАЯ ПРОГРАММА</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "Приглашай друзей и получай PREMIUM статус!\n\n"
        f"🔗 <b>Твоя ссылка:</b>\n<code>{ref_link}</code>\n\n"
        f"📊 <b>Статистика:</b> Вы пригласили <b>{count}</b> чел.\n\n"
        "🎁 <b>Что получит друг?</b>\n"
        "— 1 день <b>PREMIUM</b> статуса сразу при регистрации.\n\n"
        "🚀 <b>Твоя выгода:</b>\n"
        "— <b>+1 день PREMIUM</b> за каждого приглашенного друга!\n" # ИЗМЕНИЛИ ТЕКСТ ТУТ
        "━━━━━━━━━━━━━━━━━━\n"
        "<i>Просто отправь ссылку другу и жди, пока он заполнит анкету!</i>"
    )

    if isinstance(event, types.Message):
        await event.answer(text, parse_mode="HTML")
    else:
        await event.message.answer(text, parse_mode="HTML")
        await event.answer()

# --- 4. КОМАНДА /START (ИСПРАВЛЕННАЯ ЛОГИКА) ---
@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    user = await db_manager.get_user(user_id)
    
    args = message.text.split()
    # Если пользователь новый и пришел по реф-ссылке
    if not user and len(args) > 1:
        referrer_id = args[1]
        if referrer_id.isdigit() and int(referrer_id) != user_id:
            ref_id = int(referrer_id)
            
            # 1. Даем прем новому пользователю (приглашенному)
            now = datetime.now()
            welcome_prem = now + timedelta(days=1)
            # В базу данных нового пользователя мы добавим чуть позже в блоке регистрации, 
            # но здесь помечаем успех в add_referral
            await db_manager.add_referral(user_id, ref_id)
            
            # 2. Начисляем +1 день тому, кто пригласил
            current_ref_finish = await db_manager.get_premium_finish_date(ref_id)
            if current_ref_finish and current_ref_finish > now:
                new_finish_date = current_ref_finish + timedelta(days=1)
            else:
                new_finish_date = now + timedelta(days=1)
            
            await db_manager.update_user_status(ref_id, is_premium=True)
            await db_manager.set_premium_finish_date(ref_id, new_finish_date)
            
            # Уведомляем пригласившего
            try:
                await bot.send_message(ref_id, "🎁 Друг присоединился! Вам начислен <b>+1 день PREMIUM</b>.", parse_mode="HTML")
            except:
                pass
            
            await message.answer("🎁 Добро пожаловать! Тебе начислен <b>1 день PREMIUM</b> по приглашению!", parse_mode="HTML")

    if user and user.is_banned:
        return await message.answer("❌ Доступ к боту ограничен администрацией.")

    if not user or not user.age or not user.gender:
        await message.answer("Привет! Давай заполним анкету. 👋\nСколько тебе лет?")
        await state.set_state(UserStates.REG_AGE)
        return

    await state.set_state(UserStates.IDLE)
    await message.answer("Нажмите /search, чтобы искать собеседника", reply_markup=main_menu)

# --- ОСТАЛЬНЫЕ ХЕНДЛЕРЫ БЕЗ ИЗМЕНЕНИЙ ---
# ... (process_age, process_gender, process_search_pref и т.д.)
# --- 5. КНОПКИ МЕНЮ И КОМНАТЫ ---

@router.message(F.text == "👫 Поиск по полу")
async def menu_search_gender(message: types.Message, state: FSMContext):
    user = await db_manager.get_user(message.from_user.id)
    
    if user and not user.is_premium:
        return await message.answer(
            "💎 Функция выбора пола доступна только <b>PREMIUM</b> пользователям!\n"
            "Используйте /referals чтобы получить его за друзей.", 
            parse_mode="HTML"
        )
    
    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Парней"), types.KeyboardButton(text="Девушек")],
            [types.KeyboardButton(text="Всех")]
        ],
        resize_keyboard=True
    )
    await message.answer("Кого ты хочешь найти? 👇", reply_markup=kb)
    await state.set_state(UserStates.REG_SEARCH_GENDER)

@router.message(F.text.in_(["❤️ Флирт-чат", "💬 Общение"]))
async def change_room(message: types.Message):
    room_name = "flirt" if "Флирт" in message.text else "common"
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET room = ? WHERE telegram_id = ?", (room_name, message.from_user.id))
        await db.commit()
    await message.answer(f"✅ Ты перешел в комнату: <b>{message.text}</b>", parse_mode="HTML")

# --- 6. ПРОЦЕСС РЕГИСТРАЦИИ ---

@router.message(UserStates.REG_AGE)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or not (12 <= int(message.text) <= 99):
        return await message.answer("Пожалуйста, введи возраст числом (12-99).")
    await state.update_data(age=int(message.text))
    kb = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="Мужской"), types.KeyboardButton(text="Женский")]], resize_keyboard=True)
    await message.answer("Выбери свой пол:", reply_markup=kb)
    await state.set_state(UserStates.REG_GENDER)

@router.message(UserStates.REG_GENDER, F.text.in_(["Мужской", "Женский"]))
async def process_gender(message: types.Message, state: FSMContext):
    await state.update_data(gender=message.text)
    kb = types.ReplyKeyboardMarkup(keyboard=[[types.KeyboardButton(text="Парней"), types.KeyboardButton(text="Девушек")], [types.KeyboardButton(text="Всех")]], resize_keyboard=True)
    await message.answer("Кого ты хочешь найти в чате? 👇", reply_markup=kb)
    await state.set_state(UserStates.REG_SEARCH_GENDER)

@router.message(UserStates.REG_SEARCH_GENDER, F.text.in_(["Парней", "Девушек", "Всех"]))
async def process_search_pref(message: types.Message, state: FSMContext):
    user = await db_manager.get_user(message.from_user.id)
    data = await state.get_data()
    pref_map = {"Парней": "Мужской", "Девушек": "Женский", "Всех": "both"}
    
    if message.text in ["Парней", "Девушек"] and not (user and user.is_premium):
        search_pref = "both"
        await message.answer("💎 Поиск по полу доступен только <b>PREMIUM</b>. Установлен поиск: <b>Всех</b>.", parse_mode="HTML")
    else:
        search_pref = pref_map[message.text]

    if 'age' in data and 'gender' in data:
        await db_manager.register_user(message.from_user.id, data['age'], data['gender'], message.from_user.first_name)
    
    await db_manager.update_search_gender(message.from_user.id, search_pref)
    await state.set_state(UserStates.IDLE)
    await message.answer(f"Настройки сохранены! ✅", reply_markup=main_menu)