from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    REG_AGE = State()
    REG_GENDER = State()
    REG_SEARCH_GENDER = State()
    IDLE = State()
    SEARCH = State()
    CHATTING = State()  # Оставляем для совместимости
    IN_CHAT = State()   # Добавляем, чтобы chat.py не выдавал ошибку
    EDIT_AGE = State()
    EDIT_GENDER = State()
    EDIT_REGION = State()