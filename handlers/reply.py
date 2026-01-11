# -*- coding: utf-8 -*-
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Главное меню
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Найти собеседника")],
        [KeyboardButton(text="👫 Поиск по полу"), KeyboardButton(text="👤 Мой профиль")]
    ], 
    resize_keyboard=True
)

# Кнопки во время чата
stop_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/next"), KeyboardButton(text="/stop")]
    ], 
    resize_keyboard=True
)