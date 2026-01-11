# -*- coding: utf-8 -*-
from aiogram import types
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- ГЛАВНОЕ МЕНЮ ---
def get_main_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    
    # Первый ряд: Кнопка поиска на всю ширину
    builder.row(KeyboardButton(text="🔍 Найти собеседника"))
    
    # Второй ряд: Профиль и Поиск по полу
    builder.row(
        KeyboardButton(text="👤 Мой профиль"),
        KeyboardButton(text="👫 Поиск по полу")
    )
    
    # Третий ряд: Кнопки выбора режима чата
    builder.row(
        KeyboardButton(text="❤️ Флирт-чат"),
        KeyboardButton(text="💬 Общение")
    )
    
    return builder.as_markup(resize_keyboard=True)

main_menu = get_main_menu()

# --- КЛАВИАТУРА ОТМЕНЫ ПОИСКА ---
def get_stop_search_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="❌ Остановить поиск"))
    return builder.as_markup(resize_keyboard=True)

stop_search_menu = get_stop_search_menu()

# --- МЕНЮ ВНУТРИ ЧАТА (БЕЗ ИГРЫ) ---
chat_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="⏭ Следующий собеседник"), 
            KeyboardButton(text="❌ Остановить диалог")
        ]
    ],
    resize_keyboard=True
)

# --- МЕНЮ, КОГДА ИГРА АКТИВИРОВАНА ---
game_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🎲 Правда"), 
            KeyboardButton(text="🔥 Действие")
        ],
        [
            KeyboardButton(text="⏭ Следующий собеседник"), 
            KeyboardButton(text="❌ Остановить диалог")
        ],
        [
            KeyboardButton(text="📥 Закончить игру")
        ]
    ],
    resize_keyboard=True
)