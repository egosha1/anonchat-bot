# -*- coding: utf-8 -*-
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command 
from database.models import db_manager
from states import UserStates
from keyboards.reply import main_menu
import aiosqlite
from config import DB_NAME

# Импортируем функцию показа рефералов из start.py (или дублируем логику, если файлы разделены)
# Если функция в другом файле, убедись, что она доступна.
from handlers.start import show_referals 

# 1. СОЗДАЕМ РОУТЕР
router = Router()

## 2. ОБРАБОТЧИК ПРОФИЛЯ
@router.message(Command("profile"))
@router.message(F.text == "👤 Мой профиль")
async def show_profile(message: types.Message):
    user = await db_manager.get_user(message.from_user.id)
    
    if not user:
        return await message.answer("Сначала нажми /start")

    # Иконки и текст (оставляем без изменений)
    gender_icon = "👦 Парень" if user.gender == "Мужской" else "👧 Девушка"
    search_map = {"Мужской": "Парней 👦", "Женский": "Девушек 👧", "both": "Всех 🌍"}
    prem_status = "💎 PREMIUM" if user.is_premium else "Обычный"
    
    text = (
        f"🆔 — <code>{user.telegram_id}</code> [{prem_status}]\n\n"
        f"🎈 Пол — {gender_icon}\n"
        f"🗓 Возраст — {user.age}\n"
        f"📍 Регион — {user.region if user.region else 'Не указан'}\n"
        f"🔍 Ищешь — {search_map.get(user.search_gender, 'Всех 🌍')}\n\n"
        f"⚡️ <b>Диалоги</b>\n"
        f"├ Всего: {user.total_dialogs}\n"
        f"└ За сегодня: {user.today_dialogs}\n\n"
        f"🌟 Оценки: {user.likes} 👍 {user.dislikes} 👎\n\n"
        f"👇 Доступ к эксклюзивным функциям\n"
        f"/vip - стать 💎 <b>PREMIUM</b> пользователем"
    )

    builder = InlineKeyboardBuilder()

    # 1. Изменение пола и возраста (теперь это верхний ряд)
    builder.row(
        types.InlineKeyboardButton(text="⚧️ Изменить пол", callback_data="edit_gender"),
        types.InlineKeyboardButton(text="🔞 Изменить возраст", callback_data="edit_age")
    )
    
    # 2. Изменение региона
    builder.row(
        types.InlineKeyboardButton(text="📍 Изменить регион", callback_data="edit_region")
    )
    
    # 3. Кнопка покупки VIP (если еще нет премиума)
    if not user.is_premium:
        builder.row(types.InlineKeyboardButton(text="💎 Купить VIP", callback_data="buy_premium"))

    # 4. Кнопка рефералов — ТЕПЕРЬ В САМОМ НИЗУ
    builder.row(
        types.InlineKeyboardButton(text="👥 Пригласить друга (+50💎)", callback_data="invite_friend")
    )

    await message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())

# --- ОБРАБОТЧИК КНОПКИ ПРИГЛАШЕНИЯ ---

@router.callback_query(F.data == "invite_friend")
async def invite_callback(callback: types.CallbackQuery):
    # Вызываем функцию показа рефералов, которую мы написали в start.py
    # Она отправит сообщение с реф. ссылкой
    await show_referals(callback)
    await callback.answer()

# --- ЛОГИКА VIP СТАТУСА ---

@router.message(Command("vip"))
async def show_vip_info(message: types.Message):
    text = (
        "💎 <b>PREMIUM СТАТУС</b>\n\n"
        "Стань особенным пользователем и получи доступ к эксклюзивным функциям:\n\n"
        "✅ <b>Поиск по полу</b> — выбирай, с кем хочешь общаться.\n"
        "✅ <b>Просмотр анкет</b> — видь данные собеседника сразу.\n"
        "✅ <b>Установка региона</b> — укажи свой город.\n"
        "✅ <b>Значок PREMIUM</b> — выделись в чате.\n"
        "✅ <b>Приоритет</b> — быстрый поиск собеседника.\n\n"
        "💰 Стоимость: <b>199₽ / месяц</b>\n"
        "🎁 <i>Или пригласи друга и получи бесплатно!</i>"
    )

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="💳 Купить Premium", callback_data="buy_premium"))
    builder.row(types.InlineKeyboardButton(text="👥 Получить за друзей", callback_data="invite_friend"))

    await message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())

@router.callback_query(F.data == "buy_premium")
async def process_buy_premium(callback: types.CallbackQuery):
    await callback.message.answer(
        "🛠 <b>Система оплаты в разработке.</b>\nПока что Premium можно получить через /referals.", 
        parse_mode="HTML"
    )
    await callback.answer()

# --- ИЗМЕНЕНИЕ ДАННЫХ ---

@router.callback_query(F.data == "edit_age")
async def start_edit_age(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.EDIT_AGE)
    await callback.message.answer("🗓 Введите ваш новый возраст:")
    await callback.answer()

@router.callback_query(F.data == "edit_region")
async def start_edit_region(callback: types.CallbackQuery, state: FSMContext):
    user = await db_manager.get_user(callback.from_user.id)
    if not user.is_premium:
        return await callback.answer("💎 Функция доступна только PREMIUM пользователям!", show_alert=True)
    
    await callback.message.answer("📍 Введите ваш город или регион:")
    await state.set_state(UserStates.EDIT_REGION)
    await callback.answer()

@router.message(UserStates.EDIT_REGION)
async def process_edit_region(message: types.Message, state: FSMContext):
    # Здесь предполагается наличие метода update_region в твоем db_manager
    # Если его нет, добавь в models.py
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET region = ? WHERE telegram_id = ?", (message.text[:30], message.from_user.id))
        await db.commit()
    await state.set_state(UserStates.IDLE)
    await message.answer(f"✅ Регион изменен на: {message.text}", reply_markup=main_menu)

@router.callback_query(F.data == "edit_gender")
async def start_edit_gender(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.EDIT_GENDER)
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="👦 Парень", callback_data="set_new_g_Мужской"),
        types.InlineKeyboardButton(text="👧 Девушка", callback_data="set_new_g_Женский")
    )
    await callback.message.answer("🎈 Выберите ваш пол:", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("set_new_g_"))
async def process_edit_gender(callback: types.CallbackQuery, state: FSMContext):
    new_gender = callback.data.split("_")[3]
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET gender = ? WHERE telegram_id = ?", (new_gender, callback.from_user.id))
        await db.commit()
    await state.set_state(UserStates.IDLE)
    await callback.message.edit_text(f"✅ Ваш пол изменен на: {new_gender}")
    await callback.message.answer("Профиль обновлен!", reply_markup=main_menu)

# --- АДМИН-КОМАНДА ---
@router.message(Command("give_prem"))
async def admin_give_prem(message: types.Message):
    ADMIN_ID = 7842274559 
    if message.from_user.id == ADMIN_ID:
        await db_manager.set_premium(message.from_user.id, True)
        await message.answer("✅ Тебе выдан <b>PREMIUM статус</b>!", parse_mode="HTML")
    else:
        await message.answer("❌ Нет прав.")