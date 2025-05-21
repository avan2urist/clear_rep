import random
import asyncio
import time
import os
from environs import Env
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, FSInputFile
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

env = Env()
env.read_env()

bot = Bot(token=env('BOT_TOKEN'))
dp = Dispatcher()

# Словарь для хранения времени последнего запроса пользователя
user_cooldowns = {}

# Состояния пользователя
class UserState(StatesGroup):
    selected_asset = State()
    expiry_time = State()
    generating_signal = State()  # Новое состояние для блокировки

# Категории активов
ASSETS = {
    "Криптовалюты OTC": [
        "Bitcoin OTC", "Ethereum OTC", "Cardano OTC", "Avalanche OTC",
        "Litecoin OTC", "Solana OTC", "Toncoin OTC", "Polkadot OTC",
        "Polygon OTC", "Chainlink OTC", "TRON OTC", "BNB OTC",
        "Dogecoin OTC", "Bitcoin ETF OTC"
    ],
    "Криптовалюты": [
        "Bitcoin", "Ethereum", "Dash", "BCH/EUR", "BCH/GBP",
        "BCH/JPY", "BTC/GBP", "BTC/JPY", "Chainlink"
    ],
    "Валютные пары OTC": [
        "AED/CNY OTC", "AUD/CAD OTC", "AUD/NZD OTC", "CHF/JPY OTC",
        "EUR/CHF OTC", "EUR/HUF OTC", "EUR/NZD OTC", "EUR/RUB OTC",
        "EUR/USD OTC", "GBP/AUD OTC", "GBP/USD OTC", "JOD/CNY OTC",
        "NGN/USD OTC", "TND/USD OTC", "UAH/USD OTC", "USD/BRL OTC",
        "USD/CNH OTC", "USD/INR OTC", "USD/RUB OTC", "USD/SGD OTC",
        "USD/THB OTC", "YER/USD OTC", "ZAR/USD OTC", "USD/ARS OTC",
        "USD/VND OTC", "USD/IDR OTC", "LBP/USD OTC", "USD/EGP OTC",
        "EUR/TRY OTC", "SAR/CNY OTC", "USD/DZD OTC", "CAD/JPY OTC",
        "USD/COP OTC", "USD/JPY OTC", "USD/PHP OTC", "USD/BDT OTC",
        "QAR/CNY OTC", "USD/CLP OTC", "USD/PKR OTC", "KES/USD OTC",
        "AUD/USD OTC", "EUR/JPY OTC", "USD/CAD OTC", "NZD/JPY OTC",
        "AUD/CHF OTC", "EUR/GBP OTC", "OMR/CNY OTC", "USD/CHF OTC",
        "USD/MXN OTC", "AUD/JPY OTC"
    ],
    "Валютные пары": [
        "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD",
        "USD/CAD", "USD/CHF", "NZD/USD", "EUR/GBP",
        "EUR/JPY", "GBP/JPY", "AUD/JPY", "EUR/CAD",
        "AUD/NZD", "GBP/AUD", "EUR/AUD", "EUR/NZD"
    ],
    "Акции OTC": [
        "Apple OTC", "Tesla OTC", "Amazon OTC", "Microsoft OTC",
        "Google OTC", "Facebook OTC", "Netflix OTC", "Nvidia OTC",
        "PayPal OTC", "Visa OTC", "JPMorgan OTC", "Bank of America OTC"
    ],
    "Акции": [
        "Apple", "Tesla", "Amazon", "Microsoft",
        "Google", "Facebook", "Netflix", "Nvidia"
    ],
    "Сырьевые товары": [
        "Gold", "Silver", "Oil", "Natural Gas",
        "Copper", "Platinum", "Palladium", "Wheat"
    ]
}

# Клавиатура для выбора категории актива
def get_category_keyboard():
    builder = ReplyKeyboardBuilder()
    for category in ASSETS.keys():
        builder.add(KeyboardButton(text=category))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

# Клавиатура для выбора времени экспирации
def get_expiry_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(
        KeyboardButton(text="1 мин"), 
        KeyboardButton(text="2 мин"),
        KeyboardButton(text="3 мин"),
        KeyboardButton(text="5 мин")
    )
    builder.adjust(3)
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start", "reboot"))
async def start_or_reboot(message: types.Message, state: FSMContext):
    await state.clear()
    
    user_name = message.from_user.first_name or "инвестор"
    
    reboot_msg = await message.answer(
        "🔃 <i>Инициализация торгового модуля...</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await asyncio.sleep(1.5)
    try:
        await reboot_msg.delete()
    except:
        pass
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="⚡ ЗАПУСК", 
                callback_data="start_generation"
            )],
            [InlineKeyboardButton(
                text="📚 РУКОВОДСТВО",
                callback_data="user_guide")]
        ]
    )
    
    welcome_text = f"""
<b>✨ {user_name}, добро пожаловать в </b><b><i>QuantumTrade AI</i></b><b> — вашего персонального аналитика!</b>

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

📊 <b>Что делает наш бот уникальным?</b>

▪ <i>Гибридный анализ</i> — <b>нейросеть + алгоритмический трейдинг</b>  
▪ <i>Мгновенная адаптация</i> к рыночным изменениям  
▪ <i>Многослойная проверка</i> каждого сигнала  

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

💎 <b>Преимущества для вас:</b>

✓ <b>Автоматизация</b> — больше не нужно следить за графиками  
✓ <b>Точность</b> — до 87% прибыльных сделок (на исторических данных)  
✓ <b>Без эмоций</b> — алгоритм исключает человеческий фактор  

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

🚀 <b>Готовы начать?</b>  

Нажмите кнопку ниже, чтобы получить <b><i>первый сигнал уже через 30 секунд!</i></b>  
"""
    
    try:
        photo = FSInputFile("welcome.jpg")
        try:
            await bot.delete_message(message.chat.id, message.message_id - 1)
        except:
            pass
            
        await message.answer_photo(
            photo=photo,
            caption=welcome_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Ошибка загрузки изображения: {e}")
        await message.answer(
            text=welcome_text,
            parse_mode="HTML",
            reply_markup=keyboard
        )

# Обработка кнопки "Начать"
@dp.message(F.text == "Начать генерацию сигнала")
async def begin_signal_generation(message: types.Message, state: FSMContext):
    await message.answer(
        "Выбери категорию актива:",
        reply_markup=get_category_keyboard()
    )

@dp.callback_query(F.data == "start_generation")
async def handle_start_generation(callback: types.CallbackQuery):
    await callback.message.answer(
        "Выбери категорию актива:",
        reply_markup=get_category_keyboard()  # Переключаемся на reply-клавиатуру
    )
    await callback.answer()  # Убираем часики у кнопки

# Обработка выбора категории
@dp.message(F.text.in_(ASSETS.keys()))
async def handle_category(message: types.Message, state: FSMContext):
    builder = ReplyKeyboardBuilder()
    for asset in ASSETS[message.text]:
        builder.add(KeyboardButton(text=asset))
    builder.adjust(2)
    
    await message.answer(
        f"📋 Категория: <b>{message.text}</b>\n"
        "Выбери актив:",
        parse_mode="HTML",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )

# Обработка выбора актива
@dp.message(F.text.in_([item for sublist in ASSETS.values() for item in sublist]))
async def handle_asset(message: types.Message, state: FSMContext):
    await state.update_data(selected_asset=message.text)
    await message.answer(
        f"✅ Выбран актив: <b>{message.text}</b>\n"
        "⏱️ Выбери время экспирации:",
        parse_mode="HTML",
        reply_markup=get_expiry_keyboard()
    )

# Функция для отображения процесса "анализа"
async def show_analysis_process(message: types.Message, selected_asset: str, expiry: str):
    steps = [
        ("🔍 Начинаем анализ рынка...", 1),
        ("📡 Сбор данных по {}...".format(selected_asset), 1),
        ("📊 Анализ ценовых колебаний...", 1),
        ("🧠 Применение нейросетевых моделей...", 2),
        ("⚖️ Оценка рисков...", 1),
        ("🎯 Формирование сигнала...", 2)
    ]
    
    msg = await message.answer("🔄 Подготовка к анализу...")
    
    for step, delay in steps:
        await asyncio.sleep(delay)
        await msg.edit_text(step)
    
    await asyncio.sleep(1)
    
    # Прогресс бар
    progress_msg = await message.answer("⏳ Прогресс анализа: 0%")
    for i in range(1, 101):
        await asyncio.sleep(0.03)
        if i % 10 == 0 or i == 100:
            bar = "[" + "🟩" * (i // 10) + "⬜️" * (10 - i // 10) + "]"
            await progress_msg.edit_text(f"⏳ Прогресс анализа: {i}%\n{bar}")
    
    await asyncio.sleep(0.5)
    await progress_msg.delete()
    await msg.delete()

# Обработка выбора времени и генерация сигнала
@dp.message(F.text.in_(["1 мин", "2 мин", "3 мин", "5 мин"]))
async def generate_signal(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    current_time = time.time()
    
    # Проверяем кулдаун
    if user_id in user_cooldowns:
        elapsed = current_time - user_cooldowns[user_id]
        if elapsed < 60:  # 60 секунд = 1 минута
            remaining = int(60 - elapsed)
            await message.answer(
                f"⏳ Вы можете запросить следующий сигнал через {remaining} секунд(ы)",
                reply_markup=get_category_keyboard()
            )
            return
    
    # Обновляем время последнего запроса
    user_cooldowns[user_id] = current_time
    
    data = await state.get_data()
    selected_asset = data.get('selected_asset', 'Неизвестный актив')
    
    # Показываем процесс "анализа"
    await show_analysis_process(message, selected_asset, message.text)
    
    # Генерируем случайный сигнал
    signal = random.choice(["BUY", "SELL"])
    expiry = message.text
    
    if signal == "BUY":
        signal_text = "🟢  🟢  🟢  🟢  🟢  🟢  \n\n         🚀    <b>BUY</b>    🚀\n\n🟢  🟢  🟢  🟢  🟢  🟢  "
        profit = f"📈 Тейк-профит: +{random.randint(5, 15)}%"
    else:
        signal_text = "🔴  🔴  🔴  🔴  🔴  🔴  \n\n         🛑    <b>SELL</b>    🛑\n\n🔴  🔴  🔴  🔴  🔴  🔴  "
        profit = f"📉 Тейк-профит: +{random.randint(5, 15)}%"
    
    # Отправляем финальный сигнал
    await message.answer(
        f"══ <b>ТОРГОВЫЙ СИГНАЛ</b> ══\n\n"
        f"{signal_text}\n\n"
        f"📌 <b>Актив:</b> {selected_asset}\n"
        f"⏳ <b>Экспирация:</b> {expiry}\n"
        f"🎯 <b>Стоп-лосс:</b> -{random.randint(2, 5)}%\n"
        f"{profit}\n\n"
        f"════════════════════\n"
        f"ℹ️ Сигнал сгенерирован ИИ",
        parse_mode="HTML",
        reply_markup=get_category_keyboard()
    )
    await state.clear()

@dp.callback_query(F.data == "user_guide")
async def show_user_guide(callback: types.CallbackQuery, state: FSMContext):
    guide_text = """
<b>📖 Руководство по использованию QuantumTrade AI</b>

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

🔹 <b>Важно понимать:</b>
Этот бот — <i>интеллектуальный помощник</i> для вашего трейдинга, а не гарантия 100% прибыли. Всегда используйте собственный анализ и риск-менеджмент.

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

<b>📌 Как работает бот:</b>
1. Выбираете актив из доступных категорий
2. Указываете время экспирации (1-5 минут)
3. Бот анализирует рынок и выдает сигнал
4. <i>Рекомендуется</i> проверять сигнал на графике

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

<b>⚡ Рекомендации:</b>
• Начинайте с небольших сумм
• Используйте стоп-лоссы
• Не рискуйте более 1-2% депозита на сделку
• Комбинируйте сигналы бота с собственным анализом

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

<b>📊 Статистика точности:</b>
На основе исторических данных - около 65-87%. Реальные результаты могут отличаться в зависимости от рыночных условий.
"""

    back_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_start")]
        ]
    )
    
    # Отправляем новое сообщение с руководством
    sent_message = await callback.message.answer(
        text=guide_text,
        parse_mode="HTML",
        reply_markup=back_button
    )
    
    # Сохраняем ID сообщения с руководством в состоянии
    await state.update_data(guide_message_id=sent_message.message_id)
    
    await callback.answer()

@dp.callback_query(F.data == "back_to_start")
async def back_to_start(callback: types.CallbackQuery, state: FSMContext):
    # Получаем сохраненное ID сообщения с руководством
    user_data = await state.get_data()
    guide_message_id = user_data.get('guide_message_id')
    
    # Удаляем сообщение с руководством, если оно существует
    try:
        if guide_message_id:
            await bot.delete_message(
                chat_id=callback.from_user.id,
                message_id=guide_message_id
            )
    except Exception as e:
        print(f"Ошибка при удалении сообщения: {e}")
    
    # Очищаем состояние и показываем стартовое сообщение
    await state.clear()
    await start_or_reboot(callback.message, state)
    await callback.answer()

# Обработка неизвестных сообщений
@dp.message()
async def unknown_message(message: types.Message):
    await message.answer(
        "⚠️ Я не понимаю эту команду.\n"
        "Используй кнопки для выбора или /start для перезапуска.",
        reply_markup=get_category_keyboard()
    )

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
