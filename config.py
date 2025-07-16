"""
Конфигурация проекта - загрузка переменных окружения и настроек.
"""
import os
from dotenv import load_dotenv

# Немедленно загружаем переменные из .env файла.
# Это гарантирует, что они доступны для всех модулей, импортирующих config.
load_dotenv()

def check_env_vars():
    """Проверяет, что обязательные переменные окружения загружены."""
    required_vars = ['TELEGRAM_TOKEN', 'OPENAI_API_KEY']
    for var in required_vars:
        if not os.getenv(var):
            raise ValueError(f"Переменная окружения {var} не найдена. Проверьте файл .env")
    
    print("OK: Конфигурация загружена успешно")

def load_config():
    """Загружает конфигурацию и проверяет переменные окружения."""
    # Переменные уже загружены в начале модуля
    # Просто проверяем их наличие
    check_env_vars()
    return True

# Переменные окружения
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "db/chroma")

# Настройки администраторов
ADMIN_IDS = []
admin_ids_str = os.getenv("ADMIN_IDS", "")
if admin_ids_str:
    try:
        ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip()]
    except ValueError:
        print("⚠️ Предупреждение: Некорректный формат ADMIN_IDS в .env файле")

# Настройки ИИ
DEFAULT_MODEL = "gpt-4o-mini"
MAX_RESULTS = 10  # Максимальное количество документов для контекста
MAX_TOKENS = 2000  # Максимальное количество токенов в ответе 