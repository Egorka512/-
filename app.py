from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

# Подключение к базе данных
def get_db_connection():
    conn = sqlite3.connect('construction.db')
    conn.row_factory = sqlite3.Row
    return conn

# Главная страница
@app.route('/')
def index():
    return render_template('index.html')

# Страница управления именами
@app.route('/manage_names', methods=['GET', 'POST'])
def manage_names():
    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form['name']
        if 'add' in request.form:
            # Добавление имени
            try:
                conn.execute("INSERT INTO allowed_names (name) VALUES (?)", (name,))
                conn.commit()
            except sqlite3.IntegrityError:
                pass  # Имя уже существует
        elif 'delete' in request.form:
            # Удаление имени
            conn.execute("DELETE FROM allowed_names WHERE name = ?", (name,))
            conn.commit()
    # Получаем список имен
    names = conn.execute("SELECT name FROM allowed_names").fetchall()
    conn.close()
    return render_template('manage_names.html', names=names)

# Страница просмотра отчетов
@app.route('/reports')
def show_reports():
    conn = get_db_connection()
    # Получаем отчеты из базы данных с именами и фамилиями пользователей
    reports = conn.execute("""
        SELECT reports.id, reports.user_id, reports.arrival_time, reports.completion_time, reports.report_text, 
               objects.name AS object_name, objects.address, users.first_name, users.last_name
        FROM reports
        JOIN objects ON reports.object_id = objects.id
        JOIN users ON reports.user_id = users.user_id
        ORDER BY users.first_name, users.last_name  -- Сортируем по именам
    """).fetchall()
    conn.close()
    return render_template('reports.html', reports=reports)
# Удаление отчета

@app.route('/delete_report/<int:report_id>')
def delete_report(report_id):
    conn = get_db_connection()
    print(f"Попытка удалить отчет с ID: {report_id}")  # Отладочное сообщение
    try:
        conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        conn.commit()
        print("Отчет успешно удален")  # Отладочное сообщение
    except Exception as e:
        print(f"Ошибка при удалении отчета: {e}")  # Отладочное сообщение
    finally:
        conn.close()
    return redirect(url_for('show_reports'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001)