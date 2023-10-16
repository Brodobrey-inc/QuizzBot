import os

import buttons
import db_bot
from db_bot import AdminFilter, TeamHead, TeamFinish

import logging
import asyncio
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram import Dispatcher, executor, types
from aiogram.types import ReplyKeyboardRemove

MAIN_RULES = """Здесь могла быть ваша реклама"""

API_TOKEN = '5597934808:AAF1t1UMfXpqLFEhJOV5GNrIm-xSogK8h9g'

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = db_bot.DBBot({618552862: "Ilya"}, 2, token=API_TOKEN, use_backup=False)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.filters_factory.bind(AdminFilter)


@dp.message_handler(AdminFilter(), commands=['add_admin'])
async def add_admin(message: types.Message):
    # TODO add validating parameters
    args = message.get_args()
    _id, name = args.strip().split()
    message.bot.admins[int(_id)] = name
    await message.answer(f'Админимстратор {name} успешно добавлен')


@dp.message_handler(AdminFilter(), commands=['delete_admin'])
async def delete_admin(message: types.Message):
    # TODO add validating parameters
    args = message.get_args()
    name = args.strip()
    _id = -1
    for key, val in message.bot.admins.items():
        if name == val:
            _id = key
    if _id != -1:
        message.bot.admins.pop(_id)
        await message.answer(f'Администратор {name} успешно удален')
    else:
        await message.answer(f'Администратор {name} не найден')


@dp.message_handler(AdminFilter(), commands=['add_teams'])
async def add_teams(message: types.Message):
    args = message.get_args()
    if args is None:
        return await message.answer("Specify number of teams to add.")
    try:
        team_num = int(args)
    except Exception as e:
        return await message.answer("Error " + str(e))
    tokens = []
    for _ in range(team_num):
        tokens.append(message.bot.add_new_team())
    mes = "Successfully added new teams with tokens:\n"
    for ind, token in enumerate(tokens):
        mes += str(ind+1) + ". " + token + "\n"
    await message.answer(mes)


@dp.message_handler(AdminFilter(), commands=['delete_team'])
async def delete_team(message: types.Message):
    args = message.get_args().strip()
    _id = int(args) if args.isdigit() else args
    message.bot.df.drop(inplace=True, columns=[_id])
    await message.answer(f'Команда {_id} успешно удалена')


@dp.message_handler(AdminFilter(), commands=['get_tokens'])
async def get_tokens(message: types.Message):
    tokens = message.bot.get_tokens()
    mes = "List of tokens:\n"
    for ind, token in enumerate(tokens):
        mes += str(ind + 1) + ". " + token + "\n"
    await message.answer(mes)


@dp.message_handler(AdminFilter(), commands=['get_teams'])
async def get_teams(message: types.Message):
    tokens = message.bot.get_teams()
    mes = "List of teams:\n"
    for team_name, captain in tokens.items():
        mes += str(team_name) + " - " + captain + "\n"
    await message.answer(mes)


@dp.message_handler(AdminFilter(), commands=['start_backup'])
async def start_backup(message: types.Message):
    message.bot.continue_backup = True
    await message.answer("Start backup data.")
    while message.bot.continue_backup:
        message.bot.backup()
        await asyncio.sleep(30)
    await message.answer("Stop backup data.")


@dp.message_handler(AdminFilter(), commands=['end_backup'])
async def end_backup(message: types.Message):
    message.bot.continue_backup = False
    await message.answer("Finishing backup process...")


@dp.message_handler(AdminFilter(), commands=['get_results'])
async def get_results(message: types.Message):
    message.bot.backup(True)
    await message.answer_document(open("results.xlsx", 'rb'))


@dp.message_handler(TeamFinish(), commands=['quest'])
async def finish_quest(message: types.Message, state: FSMContext):
    await message.answer("Ты уже закончил квест, так что можешь отдохнуть)")


@dp.message_handler(TeamHead(), commands=['quest'], state=db_bot.Session.restore)
async def start_rest_quest(message: types.Message, state: FSMContext):
    await db_bot.Quiz.start.set()
    await state.finish()
    await message.answer(message.bot.get_curr_quiestion())


@dp.message_handler(TeamHead(), commands=['quest'])
async def start_quest(message: types.Message):
    await db_bot.Quiz.start.set()
    await message.answer(MAIN_RULES)
    await message.answer("Чтобы начать квест, просто напиши готов")


@dp.message_handler(TeamHead(), state=db_bot.Quiz.start)
async def ask_question(message: types.Message, state: FSMContext):
    answer = message.text.strip().lower()
    if answer != 'готов' and message.bot.first_question(message.from_user.id):
        return await state.finish()
    question = message.bot.get_next_question(message.from_user.id, answer)
    if question is None:
        await message.answer("Вы молодцы! Теперь вам осталось дождаться только результатов)")
        return await state.finish()
    await message.answer(question, reply_markup=buttons.ans_kb)


@dp.message_handler(commands=['start'], state=db_bot.Greeting.done)
async def send_welcome(message: types.Message, state: FSMContext):
    """
    This handler will be called when user sends `/start` or `/help` command
    """
    await state.finish()
    await message.answer("Чем я могу тебе помочь?", reply_markup=buttons.first_dialog)


@dp.callback_query_handler(lambda c: c.data == 'register', state='*')
async def register(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await bot.answer_callback_query(callback_query.id)
    await db_bot.Register.token.set()
    await bot.send_message(callback_query.from_user.id,
                           'Введите полученый токен для регистрации',
                           reply_markup=ReplyKeyboardRemove())


@dp.callback_query_handler(lambda c: c.data == 'help', state='*')
async def help_message(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, 'Я бот)')


@dp.message_handler(state=db_bot.Register.token)
async def validate_token(message: types.Message, state: FSMContext):
    await state.finish()
    token = message.text.strip()
    if not message.bot.has_token(token):
        return await message.answer('Неверный токен!')
    message.bot.df[token]['captain'] = message.from_user.full_name
    message.bot.df = message.bot.df.rename({token: message.from_user.id}, axis='columns')
    await db_bot.Register.team_name.set()
    await message.answer('Введите название команды')


@dp.message_handler(state=db_bot.Register.team_name)
async def team_name(message: types.Message, state: FSMContext):
    await state.finish()
    message.bot.df[message.from_user.id]["team"] = message.text.strip().title()
    await message.answer("Круто! Теперь чтобы начать наш квест, просто отправь команду /quest")


@dp.message_handler(commands=['get_id'])
async def get_id(message: types.Message):
    await message.answer("Твой id: " + str(message.from_user.id))


@dp.message_handler(state=db_bot.Greeting.done)
async def whoops_answer(message: types.Message):
    await message.answer("Я всего лишь простой бот( Попробую отправить мне команду /start. " 
                         "Ну или можешь попробовать команду /quest, если мы уже с тобой знакомы)",
                         reply_markup=buttons.continue_kb)


@dp.message_handler(TeamHead())
async def echo(message: types.Message):
    await db_bot.Greeting.done.set()
    await db_bot.Session.restore.set()
    await message.answer("Кажется мы уже с тобой знакомы, поэтому если ты уже здесь все знаешь"
                         ", то можешь отправить мне команду /quest и продолжить."
                         , reply_markup=buttons.continue_kb)


@dp.message_handler()
async def echo(message: types.Message):
    await db_bot.Greeting.done.set()
    await message.answer("Привет, друг! Чтобы начать отправть команду /start", reply_markup=buttons.start_kb)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
