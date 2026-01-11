# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from database.models import db_manager
from states import UserStates
from keyboards.reply import chat_menu, main_menu
from services.matcher import matcher

router = Router()

# --- 1. ГЛОБАЛЬНАЯ ОСТАНОВКА ПОИСКА ---
# Ставим ПЕРВЫМ в файле. 
# Реагирует и на точный текст, и на текст без эмодзи через лямбду.
@router.message(F.text == "❌ Остановить поиск")
@router.message(lambda m: m.text and "остановить поиск" in m.text.lower())
async def stop_search_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Полная очистка
    await matcher.remove_from_queue(user_id)
    await db_manager.set_partner(user_id, None)
    await state.clear()
    
    print(f"✅ ХЕНДЛЕР СРАБОТАЛ: {user_id} принудительно вышел из поиска")
    
    await message.answer(
        "🛑 <b>Поиск остановлен.</b>", 
        reply_markup=main_menu, 
        parse_mode="HTML"
    )

# --- 2. НАЧАЛО ПОИСКА ---
@router.message(F.text == "🔍 Найти собеседника")
async def start_search(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await db_manager.get_user(user_id)
    
    # Проверка на активный чат
    if user and user.partner_id:
        return await message.answer("❌ У тебя уже есть активный чат! Используй /stop чтобы выйти.")

    await matcher.add_to_queue(user_id)
    # Ставим стейт поиска
    await state.set_state(UserStates.SEARCH) 
    
    room_name = "Флирт" if user.room == "flirt" else "Общение"
    await message.answer(
        f"🔍 Ищу собеседника (Режим: {room_name})...\nНажми кнопку ниже для отмены.", 
        reply_markup=chat_menu
    )

# --- 3. ВЫБОР КОМНАТ ---
@router.message(F.text.in_(["❤️ Флирт-чат", "💬 Общение"]))
async def rooms_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    # Если юзер меняет комнату, убираем его из старой очереди
    await matcher.remove_from_queue(user_id)
    
    room = "flirt" if "Флирт" in message.text else "common"
    await db_manager.set_user_room(user_id, room)
    
    text = "🔥 Режим <b>ФЛИРТ</b>" if room == "flirt" else "✅ Режим <b>ОБЩЕНИЕ</b>"
    await message.answer(f"{text} включен!\nНажми «Найти собеседника».", parse_mode="HTML")