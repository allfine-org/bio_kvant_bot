from random import randint
import asyncio
import logging
from useful import use_database
from aiogram import F, Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

#####################
# Базовая настройка #
#####################

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.DEBUG, filename="bot.log",filemode="a")
# Объект бота
bot = Bot(token="...")
# Диспетчер
dp = Dispatcher()
score = 0
current = 1 # Переменная, отвечающая за вид мусора в задании 
info = {"num_of_pics": {1: 403, 2: 501, 3: 410, 4: 594, 5: 482, 6: 137},
        "dir_name": {1: "cardboard", 2: "glass", 3: "metal", 4: "paper", 5: "plastic", 6: "trash"},
        "categories": {"Картон": 1, "Стекло": 2, "Металл": 3, "Бумага": 4, "Пластик": 5, "Не перерабатывается": 6}}
file_ids = {} # Структура: "Х_Y: file_id", Х - номер категории^, Y - номер фото, file_id - id файла на сервере тг 
mistakes = 0
level = 100 # Отвечает за количество очков, которое надо набрать до нового уровня

# Создание базы данных
use_database("users.db", '''CREATE TABLE IF NOT EXISTS users
                    (id INTEGER PRIMARY KEY,
                    score INTEGER,
                    mistakes INTEGER,
                    level INTEGER);''')

######################
# Создание клавиатур #
######################

def get_keyboards():
            nachat = InlineKeyboardBuilder()
            nachat.row(types.InlineKeyboardButton(text="Начать!", callback_data="start"))
            nachat.row(types.InlineKeyboardButton(text="Добавить уровень сложности", callback_data="add_level"),
                       types.InlineKeyboardButton(text="Убавить уровень сложности", callback_data="sub_level"))
            
            retry = InlineKeyboardBuilder()
            retry.add(types.InlineKeyboardButton(text="Начать!", callback_data="start")) 
            
            containers = ReplyKeyboardBuilder()
            containers.row(
                types.KeyboardButton(text="Картон"),
                types.KeyboardButton(text="Стекло"))
            containers.row(
                types.KeyboardButton(text="Металл"),
                types.KeyboardButton(text="Бумага"),
                types.KeyboardButton(text="Пластик")
            )
            containers.row(
                types.KeyboardButton(text="Не перерабатывается")
            )
            return {"начало": nachat.as_markup(), "повторить попытку": retry.as_markup(), "контейнеры": containers.as_markup()}
        
####################################################
# Кусок игрового цикла, который часто используется #
####################################################
            
async def gameloop(message: types.Message, state: str = ""):
    global current
    current = randint(1, 6)
    pic_num = randint(1, info["num_of_pics"][current])
        
    if f"{current}_{pic_num}" not in file_ids:
        logging.debug("Загрузка {} на сервер ТГ".format("data/{}/".format(info["dir_name"][current])+info["dir_name"][current] + str(pic_num) + ".jpg"))
        # Загрузка файла на сервер ТГ
        pic = info["dir_name"][current] + str(pic_num) + ".jpg"
        file_ids["{}_{}".format(current, pic_num)] = types.FSInputFile("data/{}/{}".format(info["dir_name"][current], pic))
          
    await bot.delete_message(message.chat.id, message.message_id-1)
    await bot.delete_message(message.chat.id, message.message_id)
    await message.answer_photo(photo=file_ids["{}_{}".format(current, pic_num)],
            caption="{}*Очки: {}, Ошибки: {}, Уровень: {}*\nЕсли очки будут меньше нуля, то вы проиграете\!\n\nНажмите /restart, чтобы начать сначала".format(state, score, mistakes, str(level/100).replace(".", "\.")),
            parse_mode=ParseMode.MARKDOWN_V2, 
            reply_markup=get_keyboards()["контейнеры"])
    
#################################
# DEV штучки. НЕ ДЛЯ СМЕРТНЫХ!! #
#################################
    
# Для просмотра базы данных. Не использовать простым смертным!
@dp.message(Command("database", prefix="!"))
async def show_db(message: types.Message):
    data = use_database("users.db", "SELECT * FROM users", fetchone=False)
    text = ""
    for i in range(len(data)):
        if i % 2 == 0: text += str(data[i])+": "
        else: text += str(data[i])+"\n"
    await message.reply(text)
    
# Для просмотра файла логов. Не использовать простым смертным!
@dp.message(Command("logs", prefix="!"))
async def send_logs(message: types.Message):
    log_id = types.FSInputFile("bot.log")
    await message.reply_document(log_id)
    
###################
# Хендлеры команд #
###################

@dp.message(Command("restart"))
async def cmd_restart(message: types.Message):
    global score
    score = 0
    mistakes = 0
    use_database("users.db", "UPDATE users SET mistakes = ?, score = ? WHERE id = ?", (mistakes, score, message.chat.id))
    await gameloop(message)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if use_database("users.db", "SELECT id FROM users WHERE id = ?", (message.chat.id,)) != None:
        use_database("users.db", "DELETE FROM users WHERE id = ?", (message.chat.id,))
    use_database("users.db", "INSERT INTO users(id, score, mistakes, level) VALUES (?,?,?,?)", (message.chat.id, 0, 0, 100))
    logging.info("Пользователь {} ({}) запустил бота".format(message.chat.id, message.from_user.username))
    await message.answer("Добро пожаловать в игру от БиоКвантума, в которой вам нужно будет сортировать мусор по ящикам!\nНажмите 'Начать!'\n\nУровень сложности: {}".format(str(level/100)), 
                         reply_markup=get_keyboards()["начало"])
    
########################
# Главный игровой цикл #
########################
    
@dp.message(F.text)
async def main_gameloop(message: types.Message):
    global score
    global current
    global mistakes
    global level
    score, mistakes, level = use_database("users.db", "SELECT score, mistakes, level FROM users WHERE id = ?", (message.chat.id,))
    logging.debug("Получен score = {}, mistakes = {}, level = {} от пользователя {} ({})".format(score, mistakes, level, message.chat.id, message.from_user.username))
    text = message.text
    if text in ("Картон", "Стекло", "Металл", "Бумага", "Пластик", "Не перерабатывается") and score >= 0:
        keyboards = get_keyboards()
        if info["categories"][text] == current: 
            score += 5 # Если угадал, то +5 очков
            state = "*Верно\!*\n"
        else: 
            score -= int(score/2) if score not in (0, 1) else 1 # Если не угадал, то минус половина очков
            mistakes += 1
            use_database("users.db", "UPDATE users SET mistakes = ? WHERE id = ?", (mistakes, message.chat.id))
            state = "*Неверно\!* Правильный ответ: *{}*\n".format(tuple(info["categories"].keys())[current-1])
        logging.debug("Пользователь {} ({}) играет со счётом {}".format(message.chat.id, message.from_user.username, score))
        use_database("users.db", "UPDATE users SET score = ? WHERE id = ?", (score, message.chat.id))
        
        if score < 0: # Если счёт меньше 0, то пользователь проиграл
            logging.info("Пользователь {} ({}) проиграл".format(message.chat.id, message.from_user.username))
            await bot.delete_message(message.chat.id, message.message_id-1)
            await message.answer("*Вы проиграли\!* Верный ответ: *{}*\n Начать снова?".format(tuple(info["categories"].keys())[current-1]), parse_mode=ParseMode.MARKDOWN_V2, reply_markup=keyboards["повторить попытку"])
            return
        
        if score >= level:
            state = "Поздравляю, вы перешли на новый уровень!"
            level += 50
            use_database("users.db", "UPDATE users SET level = ? WHERE id = ?", (level, message.chat.id))
            
        await gameloop(message, state)
        
#########################
# Обработка callback-ов #
#########################
        
@dp.callback_query(F.data == "start")
async def start(callback: types.CallbackQuery):
    global score
    global mistakes
    score = 0
    mistakes = 0
    use_database("users.db", "UPDATE users SET score = ?, mistakes = ? WHERE id = ?", (score, mistakes, callback.message.chat.id))
    logging.info("Пользователь {} ({}) начал игру".format(callback.message.chat.id, callback.message.chat.username))
    await gameloop(callback.message)
    
@dp.callback_query(F.data == "add_level")
async def add_level(callback: types.CallbackQuery):
    global level
    level+=50
    use_database("users.db", "UPDATE users SET level = ? WHERE id = ?", (level, callback.message.chat.id))
    await callback.message.edit_text("Добро пожаловать в игру от БиоКвантума, в которой вам нужно будет сортировать мусор по ящикам!\nНажмите 'Начать!'\n\nУровень сложности: {}".format(str(level/100)), 
                         reply_markup=get_keyboards()["начало"])
    
@dp.callback_query(F.data == "sub_level")
async def add_level(callback: types.CallbackQuery):
    global level
    if level >= 100: level-=50
    use_database("users.db", "UPDATE users SET level = ? WHERE id = ?", (level, callback.message.chat.id))
    await callback.message.edit_text("Добро пожаловать в игру от БиоКвантума, в которой вам нужно будет сортировать мусор по ящикам!\nНажмите 'Начать!'\n\nУровень сложности: {}".format(str(level/100)), 
                         reply_markup=get_keyboards()["начало"])
        

# Запуск процесса поллинга новых апдейтов
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
