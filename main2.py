from http.server import BaseHTTPRequestHandler
from socketserver import TCPServer
import os

# Папка для загрузки файлов
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

class FileUploadHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Обработка GET-запроса для отображения HTML-страницы
        if self.path == '/':
            try:
                with open('index.html', 'rb') as file:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(file.read())
            except FileNotFoundError:
                self.send_error(404, "File not found")
        # Обработка GET-запроса для отображения отчёта
        elif self.path == '/reports':
            try:
                with open('uploads/reports.txt', 'r', encoding='utf-8') as file:
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    # Читаем содержимое файла
                    report_content = file.read()
                    # Форматируем отчёт в HTML
                    html_content = f"""
                    <!DOCTYPE html>
                    <html lang="ru">
                    <head>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <title>Отчёт</title>
                        <style>
                            body {{
                                font-family: Arial, sans-serif;
                                margin: 20px;
                            }}
                            h1 {{
                                color: #333;
                            }}
                            pre {{
                                background-color: #f4f4f4;
                                padding: 10px;
                                border-radius: 5px;
                                white-space: pre-wrap;
                            }}
                        </style>
                    </head>
                    <body>
                        <h1>Отчёт</h1>
                        <pre>{report_content}</pre>
                    </body>
                    </html>
                    """
                    self.wfile.write(html_content.encode('utf-8'))
            except FileNotFoundError:
                self.send_error(404, "File not found")
        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        # Обработка POST-запроса для загрузки файла
        if self.path == '/upload':
            content_length = int(self.headers['Content-Length'])
            file_data = self.rfile.read(content_length)

            # Сохраняем файл
            file_path = os.path.join(UPLOAD_FOLDER, 'reports.txt')
            with open(file_path, 'wb') as file:
                file.write(file_data)

            # Отправляем ответ
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'File uploaded successfully')
        else:
            self.send_error(404, "Not Found")

# Запуск сервера
if __name__ == '__main__':
    server_address = ('127.0.0.1', 5001)  # Используйте порт 5001 или другой
    with TCPServer(server_address, FileUploadHandler) as httpd:
        print(f"Сервер запущен на http://127.0.0.1:5001")
        httpd.serve_forever()