import sqlite3

# Подключение к базе данных
conn = sqlite3.connect("construction.db")
cursor = conn.cursor()

# Очистим старую таблицу
cursor.execute("DROP TABLE IF EXISTS objects")

# Создадим новую таблицу с нужными объектами
cursor.execute("""
CREATE TABLE IF NOT EXISTS objects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    location TEXT NOT NULL
);
""")

# Вставляем нужные объекты в таблицу
cursor.execute("""
INSERT INTO objects (name, address, location) VALUES
    ('Объект 1', 'ул. Ленина, 1', '56.010569, 92.852572'),
    ('Объект 2', 'пр. Мира, 53', '56.012345, 92.856789'),
    ('Объект 3', 'ул. Карла Маркса, 123', '56.015678, 92.860000'),
    ('Объект 4', 'ул. Дубровинского, 72', '56.018901, 92.865432');
""")
# Сохраняем изменения
conn.commit()

# Закрываем соединение
conn.close()

print("База данных успешно обновлена!")