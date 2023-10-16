from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton

button_start = KeyboardButton('/start')
quest_start = KeyboardButton('/quest')

start_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
start_kb.add(button_start)

continue_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
continue_kb.row(button_start, quest_start)

button_register = InlineKeyboardButton("Хочу зарегестрировать команду", callback_data="register")
button_help = InlineKeyboardButton("Кто ты?", callback_data="help")

first_dialog = InlineKeyboardMarkup()\
    .add(button_register)\
    .add(button_help)

button_ans1 = KeyboardButton('1')
button_ans2 = KeyboardButton('2')
button_ans3 = KeyboardButton('3')
button_ans4 = KeyboardButton('4')

ans_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
ans_kb.row(
    button_ans1, button_ans2
).row(
    button_ans3, button_ans4
)
