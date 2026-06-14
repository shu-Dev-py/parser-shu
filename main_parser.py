import logging
import sqlite3
import httpx
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import os
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    exit("❌ Ошибка: Переменная BOT_TOKEN не найдена! Создайте файл .env")

DB_NAME = "funpay.db"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def search_games_in_db(query: str):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT game_name FROM game_sections WHERE game_name LIKE ?",
            (f"%{query}%",)
        )
        return [row for row in cursor.fetchall()]


def get_options_for_game(game_name: str):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT game_id, category_name FROM game_sections WHERE game_name = ?",
            (game_name,)
        )
        return cursor.fetchall()


def get_url_by_id(game_id: str):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT url, game_name FROM game_sections WHERE game_id = ?", (str(game_id),))
        return cursor.fetchone()


async def parse_funpay_top5(url: str) -> str:
    """Парсит страницу FunPay и возвращает оформленный ТОП-5 со ссылками на каждый товар."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=10.0)
            if response.status_code != 200:
                return f"❌ Ошибка получения данных с FunPay (Код: {response.status_code})"
        except Exception as e:
            return f"❌ Не удалось подключиться к сайту: {e}"

        soup = BeautifulSoup(response.text, "lxml")
        items = soup.find_all("a", class_="tc-item")

        valid_items_count = 0
        total_price = 0
        all_slots = []

        for item in items:
            try:
                name_node = item.find("div", class_="tc-desc-text")
                price_node = item.find("div", class_="tc-price")

                if not name_node or not price_node:
                    continue

                name_text = name_node.text.strip()
                raw_price = price_node.text.strip()

                lot_url = item.get('href')
                if lot_url and lot_url.startswith('/'):
                    lot_url = f"https://funpay.com{lot_url}"


                clean_string = raw_price.replace('₽', '').replace(' ', '').replace('\xa0', '')

                chist_price = clean_string.split('.')[0]

                price_num = int(chist_price)

                total_price += price_num
                valid_items_count += 1

                all_slots.append({
                    "name": name_text,
                    "price": price_num,
                    "url": lot_url
                })
            except (ValueError, IndexError, AttributeError) as err:

                continue

        if valid_items_count == 0:
            return "❌ Сообщение: активных товаров в данной категории сейчас нет!"

        avg_price = total_price // valid_items_count
        sorted_lots = sorted(all_slots, key=lambda x: x['price'])

        message_lines = [
            f"📊 Статистика раздела:",
            f"• Всего товаров: {valid_items_count}",
            f"• Средняя цена: {avg_price}₽",
            f"• Общая сумма: {total_price}₽",
            f"_" * 20,
            f"🔥 5 самых дешевых предложений:"
        ]

        for idx, lot in enumerate(sorted_lots[:5], 1):
            if lot['url']:

                message_lines.append(f"{idx}. [{lot['price']}₽]({lot['url']}) | {lot['name']}")
            else:
                message_lines.append(f"{idx}. {lot['price']}₽ | {lot['name']}")
        return "\n".join(message_lines)


def build_games_keyboard(games, search_query: str):
    """Строит список игр + кнопка сброса/назад к вводу текста."""
    buttons = []
    for game in games:
        buttons.append([InlineKeyboardButton(text=game[0], callback_data=f"g_{game[0][:40]}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад к поиску", callback_data="back_to_search")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_options_keyboard(options, game_name: str):
    """Строит список опций + кнопка возврата к результатам поиска игр."""
    buttons = []
    for game_id, cat_name in options:
        buttons.append([InlineKeyboardButton(text=cat_name, callback_data=f"opt_{game_id}")])

    buttons.append(
        [InlineKeyboardButton(text="⬅️ Назад к списку игр", callback_data=f"back_to_games:{game_name[:40]}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)



@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Введи название игры (или часть названия), чтобы я нашел её в базе данных."
    )


@dp.message(F.text)
async def handle_game_search(message: Message):
    query = message.text.strip()
    games = search_games_in_db(query)

    if not games:
        await message.answer("❌ Игра не найдена. Попробуй ввести другое название.")
        return

    if len(games) > 15:
        await message.answer("⚠️ Найдено слишком много игр. Уточните ваш поисковый запрос.")
        return

    keyboard = build_games_keyboard(games, query)
    await message.answer("🎯 Выберите точное название игры:", reply_markup=keyboard)



@dp.callback_query(F.data == "back_to_search")
async def process_back_to_search(callback: CallbackQuery):
    """Возврат к самому первому шагу (просьба ввести текст)."""
    await callback.message.edit_text("👋 Введите название игры в чат, чтобы начать поиск заново.")
    await callback.answer()


@dp.callback_query(F.data.startswith("back_to_games:"))
async def process_back_to_games(callback: CallbackQuery):
    """Возврат от опций назад к списку найденных игр."""
    game_part_name = callback.data.replace("back_to_games:", "")
    games = search_games_in_db(game_part_name)

    if not games:
        await callback.message.edit_text("❌ Ошибка при возврате: игры не найдены. Введите название заново.")
        await callback.answer()
        return

    keyboard = build_games_keyboard(games, game_part_name)
    await callback.message.edit_text("🎯 Выберите точное название игры:", reply_markup=keyboard)
    await callback.answer()



@dp.callback_query(F.data.startswith("g_"))
async def handle_game_choice(callback: CallbackQuery):
    game_name = callback.data.replace("g_", "")
    options = get_options_for_game(game_name)

    if not options:
        await callback.message.edit_text("❌ У этой игры не найдены доступные категории.")
        await callback.answer()
        return

    keyboard = build_options_keyboard(options, game_name)
    await callback.message.edit_text(
        f"🎮 Выбрана игра: **{game_name}**\nТеперь выберите нужную опцию:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("opt_"))
async def handle_option_choice(callback: CallbackQuery):
    game_id = callback.data.replace("opt_", "")

    await callback.message.edit_text("⏳ Подключаюсь к FunPay, сортирую лоты и считаю среднюю цену...")

    db_data = get_url_by_id(game_id)
    if not db_data:
        await callback.message.edit_text("❌ Ошибка: целевой URL не найден в базе данных.")
        await callback.answer()
        return

    target_url, game_name = db_data
    result_text = await parse_funpay_top5(target_url)

    options = get_options_for_game(game_name)
    keyboard = build_options_keyboard(options, game_name)

    await callback.message.delete()
    await callback.message.answer(result_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


if __name__ == "__main__":
    dp.run_polling(bot)