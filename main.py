import logging
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
import sqlite3
import random
import asyncio
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
#API_TOKEN = '7847695839:AAHrzM3d4YkPre-y1-eNfBXDWuMqY08RWTg'  # Замените на ваш токен
#bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Подключение к базе данных
conn = sqlite3.connect('construction.db')
cursor = conn.cursor()

# Создание таблиц, если они не существуют
cursor.execute('''
CREATE TABLE IF NOT EXISTS objects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    location TEXT NOT NULL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    object_id INTEGER NOT NULL,
    arrival_time DATETIME,
    completion_time DATETIME,
    report_text TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_name TEXT,
    last_name TEXT
)
''')

# Таблица для хранения имен, добавленных администратором
cursor.execute('''
CREATE TABLE IF NOT EXISTS allowed_names (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
)
''')
conn.commit()

# Клавиатура для удобства
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Отправить геолокацию", request_location=True)]
    ],
    resize_keyboard=True
)

# Функция для создания файла с отчетами
def generate_report_file():
    # Получаем данные из базы данных
    cursor.execute("""
        SELECT reports.user_id, reports.arrival_time, reports.completion_time, reports.report_text, objects.name, objects.address
        FROM reports
        JOIN objects ON reports.object_id = objects.id
    """)
    reports = cursor.fetchall()

    # Получаем список имен, добавленных администратором
    cursor.execute("SELECT name FROM allowed_names")
    allowed_names = [row[0] for row in cursor.fetchall()]

    with open("reports.txt", mode="w", encoding="utf-8") as file:
        # Создаем плашки для отчетов
        for name in allowed_names:
            file.write(f"=== Отчет для {name} ===\n")
            for report in reports:
                user_id, arrival_time, completion_time, report_text, object_name, object_address = report
                cursor.execute("SELECT first_name FROM users WHERE user_id = ?", (user_id,))
                user_data = cursor.fetchone()
                if user_data and user_data[0] == name:
                    file.write(f"ID пользователя - {user_id}\n")
                    file.write(f"Адрес объекта - {object_address}\n")
                    file.write(f"Попал на объект - {'Да' if arrival_time else 'Нет'}\n")
                    file.write(f"Время прибытия - {arrival_time}\n")
                    file.write(f"Время завершения работ - {completion_time}\n")
                    file.write(f"Отчет - {report_text if report_text else 'null'}\n")
                    file.write("\n")
            file.write("\n")  # Разделитель между плашками
    logger.info("Файл reports.txt успешно создан.")

# Функция для отправки файла на локальный сервер
def upload_report_to_site(file_path):
    try:
        with open(file_path, 'rb') as file:
            files = {'file': file}
            response = requests.post('http://127.0.0.1:5001/upload', files=files)
            logger.info(f"Ответ сервера: {response.status_code}, {response.text}")
            return response
    except Exception as e:
        logger.error(f"Ошибка при отправке файла на сервер: {e}")
        return None

# Команда /start
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "null"
    last_name = message.from_user.last_name or "null"

    # Проверяем, есть ли имя пользователя в списке allowed_names
    cursor.execute("SELECT name FROM allowed_names WHERE name = ?", (first_name,))
    if not cursor.fetchone():
        await message.reply("Ваше имя не в списке для отчетов.")
        return

    # Сохраняем или обновляем данные пользователя
    cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, first_name, last_name)
        VALUES (?, ?, ?)
    """, (user_id, first_name, last_name))
    conn.commit()

    # Выбираем случайный объект из базы данных
    cursor.execute("SELECT id, name, address, location FROM objects")
    objects = cursor.fetchall()

    if not objects:
        await message.reply("Нет доступных объектов.")
        return

    object_id, object_name, object_address, object_location = random.choice(objects)
    cursor.execute("INSERT INTO reports (user_id, object_id) VALUES (?, ?)", (user_id, object_id))
    conn.commit()

    await message.reply(f"Ваш объект: {object_name}, адрес: {object_address}. Отправьте свою геолокацию, чтобы подтвердить прибытие.", reply_markup=keyboard)

# Команда /add_name (только для администратора)
@dp.message(Command("add_name"))
async def add_name(message: types.Message):
    # Проверяем, является ли пользователь администратором
    if message.from_user.id != ADMIN_USER_ID:  # Замените ADMIN_USER_ID на ID администратора
        await message.reply("У вас нет прав для выполнения этой команды.")
        return

    # Получаем имя из сообщения
    name = message.text.split(maxsplit=1)[1].strip() if len(message.text.split()) > 1 else None
    if not name:
        await message.reply("Используйте команду так: /add_name Имя")
        return

    # Добавляем имя в таблицу allowed_names
    try:
        cursor.execute("INSERT INTO allowed_names (name) VALUES (?)", (name,))
        conn.commit()
        await message.reply(f"Имя '{name}' успешно добавлено.")
    except sqlite3.IntegrityError:
        await message.reply(f"Имя '{name}' уже существует в списке.")

# Обработка геолокации
@dp.message(lambda message: message.location is not None)
async def handle_location(message: types.Message):
    user_id = message.from_user.id
    user_location = f"{message.location.latitude}, {message.location.longitude}"

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
    logger.info(f"Координаты сотрудника: {user_lat}, {user_lon}")
    logger.info(f"Координаты объекта: {obj_lat}, {obj_lon}")
    return abs(user_lat - obj_lat) < 1000 and abs(user_lon - obj_lon) < 1000

# Команда /end
@dp.message(Command("end"))
async def end_work(message: types.Message):
    user_id = message.from_user.id

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

# Обработка текстового отчета
@dp.message(lambda message: message.text and not message.location)
async def handle_report(message: types.Message):
    user_id = message.from_user.id
    report_text = message.text

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
        await message.reply("Отчет успешно сохранен!")

        generate_report_file()
        response = upload_report_to_site("reports.txt")

        if response and response.status_code == 200:
            await message.reply("Отчет успешно отправлен на сервер! Вы можете просмотреть его по ссылке: http://127.0.0.1:5001/reports")
        else:
            await message.reply("Ошибка при отправке отчета на сервер.")
    else:
        await message.reply("Ошибка: не удалось найти активный отчёт.")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())