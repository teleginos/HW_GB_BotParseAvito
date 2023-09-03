import logging
import aiogram
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.utils.exceptions import BotBlocked
from selenium.webdriver.common.by import By
from selenium.webdriver import ChromeOptions, Chrome
import asyncio
from API_TOKEN import API_TOKEN

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

active_users = {}


async def send_ads(chat_id, ads):
    for ad in ads:
        try:
            await bot.send_message(chat_id, ad)
        except aiogram.utils.exceptions.BotBlocked:
            logging.warning(f"Bot is blocked by the user with chat ID {chat_id}")
            return


@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    active_users[message.chat.id] = True
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    search_button = types.KeyboardButton("Поиск")
    keyboard.add(search_button)
    if message.chat.id not in active_users:
        await bot.send_message(chat_id=message.chat.id, text="Привет! Я бот для поиска новых объявлений на Авито.\n"
                                                             "Нажмите кнопку Поиск для начала поиска или выберите "
                                                             "команду /search из меню слева.",
                               reply_markup=keyboard)
    else:
        await bot.send_message(chat_id=message.chat.id, text="С возвращением! Рад снова работать с Вами\n"
                                                             "Нажмите кнопку Поиск ли выберите "
                                                             "команду /search из меню слева и я найду самые свежие "
                                                             "объявления "
                                                             "по вашему запросу", reply_markup=keyboard)


@dp.message_handler(commands=['cancel'])
async def cmd_cancel(message: types.Message):
    active_users[message.chat.id] = False
    await bot.send_message(chat_id=message.chat.id, text="Надеюсь, я смог Вам помочь с вашими поисками. Если Вам "
                                                         "потребуется моя помощь снова, просто введите в чат /start.")


@dp.message_handler(commands=['search'])
@dp.message_handler(lambda message: message.text.lower() == 'поиск')
async def ask_for_keywords(message: types.Message):
    keyboard = types.ReplyKeyboardRemove()
    await bot.send_message(chat_id=message.chat.id, text="Введите ключевые слова для поиска, разделяя их запятыми:",
                           reply_markup=keyboard)


@dp.message_handler(lambda message: message.text and message.text.lower() != "поиск")
async def search_ads(message: types.Message):
    await bot.send_message(chat_id=message.chat.id, text=f"Начинаю отслеживать собщения по вашему запросу "
                                                         f"({message.text})"
                                                         f"\nОжидайте, как только на сайте появятся новые объявления я "
                                                         f"Вам сразу же пришлю ссылки на них")
    keywords = message.text.split(',')
    tasks = []
    for i, keyword in enumerate(keywords):
        await asyncio.sleep(i * 15)  # Задержка в 15 секунд между каждым запуском
        task = asyncio.create_task(parse_data(message.chat.id, keyword.strip()))
        tasks.append(task)
    # await asyncio.gather(*(parse_data(message.chat.id, keyword.strip()) for keyword in keywords))


async def parse_data(chat_id, keyword):
    chrome_options = ChromeOptions()
    chrome_options.add_argument('--headless')

    driver = None
    try:
        driver = Chrome(options=chrome_options)

        driver.get(f'https://www.avito.ru/moskva_i_mo?q={keyword}&s=104')

        button_1 = driver.find_element(By.CSS_SELECTOR, "[data-marker='sort-select/input']")
        button_1.click()
        button_2 = driver.find_element(By.CSS_SELECTOR, "[data-marker='sort-select/option(104)']")
        button_2.click()

        while True:
            if not active_users.get(chat_id, True):
                break
            driver.refresh()

            new_elements = driver.find_elements(By.CSS_SELECTOR, "[data-marker='item']")

            new_ads = []
            for element in new_elements:
                data_time = element.find_element(By.CSS_SELECTOR, "[data-marker='item-date']")

                if data_time.text in ["1 минуту назад", "Несколько секунд назад"]:
                    url = element.find_element(By.CSS_SELECTOR, "[itemprop='url']").get_attribute("href")
                    new_ads.append(url)

            if new_ads:
                await send_ads(chat_id=chat_id, ads=new_ads)

            await asyncio.sleep(60)
    except Exception as e:
        logging.error(f"Failed to start ChromeDriver: {e}")
    finally:
        if driver is not None:
            driver.quit()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
