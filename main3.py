import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
import sqlite3
import random
import asyncio
from datetime import datetime

# Настройка логирования для отладки работы бота
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота с API-токеном
API_TOKEN = '7847695839:AAHrzM3d4YkPre-y1-eNfBXDWuMqY08RWTg'  # Замените на ваш токен
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Подключение к базе данных SQLite
conn = sqlite3.connect('construction.db')
cursor = conn.cursor()

# Создание таблицы объектов
cursor.execute('''
CREATE TABLE IF NOT EXISTS objects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    location TEXT NOT NULL  -- Координаты объекта (широта, долгота)
)
''')

# Таблица для отчетов пользователей
cursor.execute('''
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    object_id INTEGER NOT NULL,
    arrival_time DATETIME,  -- Время прибытия на объект
    completion_time DATETIME,  -- Время завершения работы
    report_text TEXT,  -- Отчет пользователя
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

# Таблица пользователей, которые взаимодействуют с ботом
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_name TEXT,
    last_name TEXT
)
''')

# Таблица с разрешёнными именами (чтобы не все могли отправлять отчёты)
cursor.execute('''
CREATE TABLE IF NOT EXISTS allowed_names (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
)
''')
conn.commit()

# Клавиатура с кнопкой для отправки геолокации
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Отправить геолокацию", request_location=True)]
    ],
    resize_keyboard=True
)

# Обработчик команды /start
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "null"
    last_name = message.from_user.last_name or "null"

    # Проверка, есть ли имя в списке разрешённых
    cursor.execute("SELECT name FROM allowed_names WHERE name = ?", (first_name,))
    if not cursor.fetchone():
        await message.reply("Ваше имя не в списке для отчетов.")
        return

    # Запись или обновление данных пользователя в базе
    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, first_name, last_name)
        VALUES (?, ?, ?)
    """, (user_id, first_name, last_name))
    conn.commit()

    # Выбор случайного объекта из базы
    cursor.execute("SELECT id, name, address, location FROM objects")
    objects = cursor.fetchall()

    if not objects:
        await message.reply("Нет доступных объектов.")
        return

    # Выбираем случайный объект и создаем отчет
    object_id, object_name, object_address, object_location = random.choice(objects)
    cursor.execute("INSERT INTO reports (user_id, object_id) VALUES (?, ?)", (user_id, object_id))
    conn.commit()

    # Сообщаем пользователю информацию об объекте
    await message.reply(
        f"Ваш объект: {object_name}, адрес: {object_address}. Отправьте свою геолокацию, чтобы подтвердить прибытие.",
        reply_markup=keyboard)

# Обработка геолокации пользователя
@dp.message(lambda message: message.location is not None)
async def handle_location(message: types.Message):
    user_id = message.from_user.id
    user_location = f"{message.location.latitude}, {message.location.longitude}"

    # Получение последнего отчета пользователя, у которого ещё нет времени прибытия
    cursor.execute("""
        SELECT reports.id, objects.location 
        FROM reports 
        JOIN objects ON reports.object_id = objects.id
        WHERE reports.user_id = ? AND reports.arrival_time IS NULL
        ORDER BY reports.timestamp DESC 
        LIMIT 1
    """, (user_id,))
    last_report = cursor.fetchone()

    if last_report:
        report_id, object_location = last_report

        # Проверяем, соответствует ли геолокация объекта
        if is_user_at_object(user_location, object_location):
            arrival_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE reports SET arrival_time = ? WHERE id = ?", (arrival_time, report_id))
            conn.commit()
            await message.reply(
                f"Вы на объекте! Время прибытия: {arrival_time}. Когда закончите работу, введите команду /end, чтобы отправить отчет.",
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            await message.reply("Вы не на объекте. Пожалуйста, отправьте геолокацию снова.")
    else:
        await message.reply("Ошибка: не удалось найти активный отчёт.")

# Функция для проверки, находится ли сотрудник на объекте
def is_user_at_object(user_location, object_location):
    user_lat, user_lon = map(float, user_location.split(", "))
    obj_lat, obj_lon = map(float, object_location.split(", "))

    # Логирование координат
    logger.info(f"Координаты сотрудника: {user_lat}, {user_lon}")
    logger.info(f"Координаты объекта: {obj_lat}, {obj_lon}")

    # Проверяем, находится ли пользователь в радиусе 10 метров (~0.0001 градуса)
    return abs(user_lat - obj_lat) < 0.001 and abs(user_lon - obj_lon) < 0.001

# Обработчик команды /end (завершение работы)
@dp.message(Command("end"))
async def end_work(message: types.Message):
    user_id = message.from_user.id

    # Поиск активного отчета (куда еще не добавлен текст отчета)
    cursor.execute("""
        SELECT id FROM reports 
        WHERE user_id = ? AND arrival_time IS NOT NULL AND report_text IS NULL
        ORDER BY timestamp DESC 
        LIMIT 1
    """, (user_id,))
    last_report = cursor.fetchone()

    if last_report:
        completion_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE reports SET completion_time = ? WHERE id = ?", (completion_time, last_report[0]))
        conn.commit()
        await message.reply("Пожалуйста, отправьте отчет о выполненной работе.")
    else:
        await message.reply("Ошибка: не удалось найти активный отчёт.")

# Обработка текстового отчета пользователя
# Обработка текстового отчета пользователя
@dp.message(lambda message: message.text and not message.location)
async def handle_report(message: types.Message):
    user_id = message.from_user.id
    report_text = message.text

    # Поиск последнего отчета, который ожидает текст отчета
    cursor.execute("""
        SELECT id FROM reports 
        WHERE user_id = ? AND arrival_time IS NOT NULL AND report_text IS NULL
        ORDER BY timestamp DESC 
        LIMIT 1
    """, (user_id,))
    last_report = cursor.fetchone()

    if last_report:
        report_id = last_report[0]
        cursor.execute("UPDATE reports SET report_text = ? WHERE id = ?", (report_text, report_id))
        conn.commit()

        # Получаем все отчеты пользователя с сортировкой по времени (новые сверху)
        cursor.execute("""
            SELECT * FROM reports 
            WHERE user_id = ? 
            ORDER BY timestamp DESC
        """, (user_id,))
        reports = cursor.fetchall()

        # Формируем сообщение с отчетами
        report_message = "Ваши отчеты:\n"
        for report in reports:
            report_message += f"Объект: {report[2]}, Время прибытия: {report[3]}, Отчет: {report[5]}\n"

        await message.reply(report_message)
    else:
        await message.reply("Ошибка: не удалось найти активный отчёт.")
# Основная функция запуска бота
async def main():
    await dp.start_polling(bot)

# Запуск бота
if __name__ == '__main__':
    asyncio.run(main())