# Универсальный Dockerfile для Python сервисов (бот и админ-панель)
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл с зависимостями
COPY requirements.txt ./

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Переменная для выбора запускаемого сервиса
ENV SERVICE=bot

# Создаем необходимые директории
RUN mkdir -p data db/chroma

# Устанавливаем переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Открываем порт (если потребуется в будущем)
EXPOSE 8000

# Команда для запуска приложения
CMD ["sh", "-c", "if [ $SERVICE = 'admin' ]; then python admin_panel.py; else python main.py; fi"] 