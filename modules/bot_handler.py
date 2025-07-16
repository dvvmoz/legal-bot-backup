"""
Модуль для обработки сообщений Telegram бота.
"""
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, BotCommand
from aiogram.filters import Command
from aiogram.exceptions import TelegramAPIError
import config
import os
from .knowledge_base import search_relevant_docs, get_knowledge_base, should_use_dynamic_search
from .llm_service import get_answer
from .web_scraper import create_scraper_from_config
from .scraping_tracker import get_scraping_tracker
from .incremental_scraper import create_incremental_scraper
from .dynamic_search import create_dynamic_searcher
from .text_processing import TextProcessor
from .ml_question_filter import is_legal_question_ml as is_legal_question, get_ml_rejection_message as get_rejection_message
from .ml_analytics_integration import create_question_context, finalize_question_context, get_analytics_summary

logger = logging.getLogger(__name__)

# Получаем адрес админ-панели из переменной окружения (по умолчанию http://localhost:8080)
ADMIN_PANEL_URL = os.environ.get('ADMIN_PANEL_URL', 'http://localhost:8080')

class LegalBot:
    """Класс для управления юридическим ботом."""
    
    def __init__(self):
        """Инициализирует бота."""
        self.bot = Bot(token=config.TELEGRAM_TOKEN)
        self.dp = Dispatcher()
        self._setup_handlers()
        logger.info("Бот инициализирован")
    
    def _setup_handlers(self):
        """Настраивает обработчики сообщений."""
        # Обработчик команды /start
        self.dp.message.register(self.handle_start, Command("start"))
        
        # Обработчик команды /help
        self.dp.message.register(self.handle_help, Command("help"))
        
        # Обработчик команды /stats
        self.dp.message.register(self.handle_stats, Command("stats"))
        
        # Обработчик команды /scrape
        self.dp.message.register(self.handle_scrape, Command("scrape"))
        
        # Обработчик команды /update для инкрементального парсинга
        self.dp.message.register(self.handle_update, Command("update"))
        
        # Обработчик команды /dynamic для статистики динамического поиска
        self.dp.message.register(self.handle_dynamic, Command("dynamic"))
        
        # Обработчик команды /admin для доступа к админ-панели
        self.dp.message.register(self.handle_admin, Command("admin"))
        
        # Обработчик команды /analytics для статистики ML-фильтра
        self.dp.message.register(self.handle_analytics, Command("analytics"))
        
        # Обработчик команды /startadmin для запуска админ-панели
        self.dp.message.register(self.handle_start_admin, Command("startadmin"))
        
        # Обработчик команды /stopadmin для остановки админ-панели
        self.dp.message.register(self.handle_stop_admin, Command("stopadmin"))
        
        # Обработчики для новых команд с подчеркиванием (для совместимости)
        self.dp.message.register(self.handle_deprecated_start_admin, Command("start_admin"))
        self.dp.message.register(self.handle_deprecated_stop_admin, Command("stop_admin"))
        
        # Обработчик всех текстовых сообщений
        self.dp.message.register(self.handle_question, F.text)
    
    async def _setup_bot_commands(self):
        """Настраивает команды бота в Telegram."""
        commands = [
            BotCommand(command="start", description="Начать работу с ботом"),
            BotCommand(command="help", description="Справка по использованию"),
            BotCommand(command="stats", description="Статистика базы знаний"),
            BotCommand(command="admin", description="Веб-панель администратора"),
            BotCommand(command="analytics", description="Аналитика ML-фильтра"),
            BotCommand(command="startadmin", description="Запуск админ-панели"),
            BotCommand(command="stopadmin", description="Остановка админ-панели"),
            BotCommand(command="scrape", description="Скрапинг сайтов"),
            BotCommand(command="update", description="Инкрементальное обновление"),
            BotCommand(command="dynamic", description="Статистика динамического поиска"),
        ]
        
        try:
            # Принудительно обновляем команды
            await self.bot.set_my_commands(commands)
            logger.info("✅ Команды бота успешно установлены:")
            for cmd in commands:
                logger.info(f"   /{cmd.command} - {cmd.description}")
        except TelegramAPIError as e:
            logger.error(f"❌ Ошибка установки команд бота: {e}")
            # Не прерываем запуск бота из-за ошибки команд
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при установке команд: {e}")
    
    async def handle_start(self, message: Message):
        """
        Обрабатывает команду /start.
        
        Args:
            message: Сообщение от пользователя
        """
        welcome_text = """
🤖 **Добро пожаловать в ЮрПомощник РБ!**

Я ваш персональный юридический ассистент по законодательству Республики Беларусь.

🇧🇾 **Специализация:**
📋 Белорусское законодательство и правоприменение
📚 Кодексы, законы и подзаконные акты РБ
📝 Пошаговые рекомендации по белорусскому праву
⚖️ Процедуры в государственных органах РБ
🔍 **Динамический поиск:** Если нет ответа в базе, ищу на pravo.by!

**Что я знаю:**
• Гражданское право РБ
• Трудовое законодательство
• Хозяйственное право
• Административные процедуры
• Семейное право
• Жилищное законодательство

**Как пользоваться:**
Просто напишите ваш вопрос обычным языком.

**Доступные команды:**
/help - справка по использованию
/stats - статистика базы знаний
/admin - веб-панель администратора (только для администраторов)
/startadmin - запуск админ-панели (только для администраторов)
/stopadmin - остановка админ-панели (только для администраторов)
/scrape - скрапинг сайтов (только для администраторов)
/update - инкрементальное обновление (только для администраторов)
/dynamic - статистика динамического поиска (только для администраторов)

⚠️ **Важно:** Консультации основаны на законодательстве РБ. Не заменяют персональную юридическую помощь.

Задайте свой первый вопрос! 👇
"""
        try:
            await message.answer(welcome_text, parse_mode="Markdown")
            logger.info(f"Пользователь {message.from_user.id} запустил бота")
        except TelegramAPIError as e:
            logger.error(f"Ошибка отправки приветствия: {e}")
    
    async def handle_help(self, message: Message):
        """
        Обрабатывает команду /help.
        
        Args:
            message: Сообщение от пользователя
        """
        help_text = """
📖 **Справка по использованию ЮрПомощника РБ**

🇧🇾 **Примеры вопросов по белорусскому праву:**
• "Как зарегистрировать ИП в Беларуси?"
• "Какие документы нужны для развода в РБ?"
• "Как оформить трудовой договор по ТК РБ?"
• "Какие права у потребителя в Беларуси?"
• "Как получить разрешение на строительство?"
• "Что делать при увольнении в РБ?"

**Советы для лучших результатов:**
✅ Формулируйте вопросы конкретно
✅ Указывайте контекст (для ИП, организации, гражданина)
✅ Уточняйте регион (Минск, области РБ)
✅ Задавайте по одному вопросу за раз

**Что я НЕ делаю:**
❌ Не заменяю профессиональную юридическую консультацию
❌ Не составляю документы
❌ Не даю советы по незаконным действиям
❌ Не консультирую по российскому праву

**Специализация:**
• Гражданское право РБ (ГК РБ)
• Трудовое право (ТК РБ)
• Хозяйственное право (ХК РБ)
• Административное право (КоАП РБ)
• Семейное право (КоБС РБ)

**Команды:**
/start - главное меню
/help - эта справка
/stats - информация о базе знаний
/admin - веб-панель администратора (только для администраторов)
/startadmin - запуск админ-панели (только для администраторов)
/stopadmin - остановка админ-панели (только для администраторов)
/scrape - скрапинг сайтов (только для администраторов)
/update - инкрементальное обновление (только для администраторов)
/dynamic - статистика динамического поиска (только для администраторов)

❓ Если у вас есть вопросы, просто спросите!
"""
        try:
            await message.answer(help_text, parse_mode="Markdown")
            logger.info(f"Пользователь {message.from_user.id} запросил справку")
        except TelegramAPIError as e:
            logger.error(f"Ошибка отправки справки: {e}")
    
    async def handle_stats(self, message: Message):
        """
        Обрабатывает команду /stats.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            kb = get_knowledge_base()
            stats = kb.get_collection_stats()
            
            stats_text = f"""📊 Статистика базы знаний

📚 Всего документов: {stats.get('total_documents', 0)}
🗂️ Коллекция: {stats.get('collection_name', 'N/A')}
💾 Путь к БД: {stats.get('db_path', 'N/A')}

✅ Бот готов отвечать на ваши вопросы!"""
            
            await message.answer(stats_text)
            logger.info(f"Пользователь {message.from_user.id} запросил статистику")
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            await message.answer("Извините, не удалось получить статистику.")
    
    async def handle_scrape(self, message: Message):
        """
        Обрабатывает команду /scrape для веб-скрапинга.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Проверяем права администратора
            admin_ids = config.ADMIN_IDS if config.ADMIN_IDS else [123456789]
            
            if message.from_user.id not in admin_ids:
                await message.answer("⛔ У вас нет прав для выполнения этой команды.")
                return
            
            # Парсим аргументы команды
            args = message.text.split()[1:]  # Убираем /scrape
            
            if not args:
                help_text = """
🔍 **Команда скрапинга сайтов**

**Использование:**
`/scrape <URL> [количество_страниц]`

**Примеры:**
• `/scrape https://www.garant.ru/ 10`
• `/scrape https://www.consultant.ru/ 5`

**Параметры:**
• URL - адрес сайта для скрапинга
• количество_страниц - максимум страниц (по умолчанию 20)

⚠️ **Внимание:** Скрапинг может занять время!
"""
                await message.answer(help_text, parse_mode="Markdown")
                return
            
            url = args[0]
            max_pages = int(args[1]) if len(args) > 1 else 20
            
            # Проверяем валидность URL
            if not url.startswith(('http://', 'https://')):
                await message.answer("❌ Неверный формат URL. Используйте полный адрес с http:// или https://")
                return
            
            # Отправляем сообщение о начале скрапинга
            status_msg = await message.answer(f"🚀 Начинаю скрапинг сайта: {url}\n⏳ Это может занять несколько минут...")
            
            # Выполняем скрапинг
            scraper = create_scraper_from_config()
            result = scraper.scrape_and_add(url, max_pages)
            
            if result['success']:
                success_text = f"""
✅ **Скрапинг завершен успешно!**

📄 Обработано страниц: {result['pages_scraped']}
📝 Добавлено чанков: {result['chunks_added']}
🌐 Сайт: {result['start_url']}

База знаний пополнена! Теперь бот знает больше.
"""
                await status_msg.edit_text(success_text, parse_mode="Markdown")
            else:
                error_text = f"""
❌ **Ошибка скрапинга**

🔍 Сайт: {url}
⚠️ Причина: {result['message']}

Попробуйте:
• Проверить доступность сайта
• Уменьшить количество страниц
• Использовать другой URL
"""
                await status_msg.edit_text(error_text, parse_mode="Markdown")
            
            logger.info(f"Пользователь {message.from_user.id} выполнил скрапинг {url}")
            
        except ValueError:
            await message.answer("❌ Неверный формат количества страниц. Используйте число.")
        except Exception as e:
            logger.error(f"Ошибка при скрапинге: {e}")
            await message.answer("😔 Произошла ошибка при скрапинге. Попробуйте позже.")
    
    async def handle_update(self, message: Message):
        """
        Обрабатывает команду /update для инкрементального парсинга.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Проверяем права администратора
            admin_ids = config.ADMIN_IDS if config.ADMIN_IDS else [123456789]
            
            if message.from_user.id not in admin_ids:
                await message.answer("⛔ У вас нет прав для выполнения этой команды.")
                return
            
            # Парсим аргументы команды
            args = message.text.split()[1:]  # Убираем /update
            
            if not args:
                help_text = """
🔄 **Команда инкрементального обновления**

**Использование:**
`/update <URL> [количество_страниц]`

**Примеры:**
• `/update https://pravo.by/ 50`
• `/update https://www.consultant.ru/ 30`

**Параметры:**
• URL - адрес сайта для обновления
• количество_страниц - максимум страниц для сканирования (по умолчанию 100)

**Возможности:**
✅ Парсит только новые и измененные страницы
✅ Отслеживает изменения по хэшам контента
✅ Экономит время и ресурсы
✅ Ведет статистику изменений

⚠️ **Внимание:** Первое сканирование может занять больше времени!
"""
                await message.answer(help_text, parse_mode="Markdown")
                return
            
            url = args[0]
            max_pages = int(args[1]) if len(args) > 1 else 100
            
            # Проверяем валидность URL
            if not url.startswith(('http://', 'https://')):
                await message.answer("❌ Неверный формат URL. Используйте полный адрес с http:// или https://")
                return
            
            # Отправляем сообщение о начале обновления
            status_msg = await message.answer(f"🔄 Начинаю инкрементальное обновление: {url}\n⏳ Проверяю изменения...")
            
            # Создаем инкрементальный скрапер
            web_scraper = create_scraper_from_config()
            scraping_tracker = get_scraping_tracker()
            incremental_scraper = create_incremental_scraper(web_scraper, scraping_tracker)
            
            # Выполняем инкрементальное обновление
            result = incremental_scraper.incremental_scrape(url, max_pages)
            
            # Формируем отчет
            if result['pages_scraped'] > 0:
                success_text = f"""
✅ **Обновление завершено успешно!**

📊 **Статистика:**
• Проверено URL: {result['total_urls_checked']}
• Новых страниц: {result['new_pages']}
• Измененных страниц: {result['changed_pages']}
• Удаленных страниц: {result['deleted_pages']}
• Обработано страниц: {result['pages_scraped']}
• Добавлено чанков: {result['chunks_added']}

🌐 **Сайт:** {url}

База знаний обновлена! 🎉
"""
                await status_msg.edit_text(success_text, parse_mode="Markdown")
            else:
                no_changes_text = f"""
ℹ️ **Изменений не найдено**

📊 **Статистика:**
• Проверено URL: {result['total_urls_checked']}
• Новых страниц: {result['new_pages']}
• Измененных страниц: {result['changed_pages']}
• Удаленных страниц: {result['deleted_pages']}

🌐 **Сайт:** {url}

Все страницы актуальны! ✅
"""
                await status_msg.edit_text(no_changes_text, parse_mode="Markdown")
            
            logger.info(f"Пользователь {message.from_user.id} выполнил инкрементальное обновление {url}")
            
        except ValueError:
            await message.answer("❌ Неверный формат количества страниц. Используйте число.")
        except Exception as e:
            logger.error(f"Ошибка при инкрементальном обновлении: {e}")
            await message.answer("😔 Произошла ошибка при обновлении. Попробуйте позже.")
    
    async def handle_dynamic(self, message: Message):
        """
        Обрабатывает команду /dynamic для статистики динамического поиска.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Проверяем права администратора
            admin_ids = config.ADMIN_IDS if config.ADMIN_IDS else [123456789]
            
            if message.from_user.id not in admin_ids:
                await message.answer("⛔ У вас нет прав для выполнения этой команды.")
                return
            
            # Создаем динамический поисковик для получения статистики
            web_scraper = create_scraper_from_config()
            knowledge_base = get_knowledge_base()
            text_processor = TextProcessor()
            scraping_tracker = get_scraping_tracker()
            
            dynamic_searcher = create_dynamic_searcher(
                web_scraper, knowledge_base, text_processor, scraping_tracker
            )
            
            stats = dynamic_searcher.get_search_statistics()
            
            stats_text = f"""
🔍 **Статистика динамического поиска**

🌐 **Базовый URL:** {stats['search_base_url']}
📊 **Максимум результатов:** {stats['max_search_results']}
📄 **Максимум страниц на результат:** {stats['max_pages_per_result']}

🔗 **Доступные эндпоинты:**
{chr(10).join(f"• {endpoint}" for endpoint in stats['available_endpoints'])}

**Как это работает:**
✅ Если нет ответа в базе знаний, бот автоматически ищет на pravo.by
✅ Найденная информация добавляется в базу знаний
✅ Пользователь получает актуальный ответ
✅ Следующие похожие вопросы будут решены мгновенно

**Поддерживаемые темы:**
• Трудовое право • Гражданское право • Семейное право
• Административное право • Хозяйственное право • Налоговое право
• Регистрация ИП/ООО • Договоры • Наследство • Алименты
• Суды • Штрафы • Права и обязанности граждан
"""
            
            await message.answer(stats_text, parse_mode="Markdown")
            logger.info(f"Пользователь {message.from_user.id} запросил статистику динамического поиска")
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики динамического поиска: {e}")
            await message.answer("😔 Произошла ошибка при получении статистики.")
    
    async def handle_admin(self, message: Message):
        """
        Обрабатывает команду /admin для доступа к веб-панели администратора.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Проверяем права администратора
            admin_ids = config.ADMIN_IDS if config.ADMIN_IDS else [123456789]
            
            # Временное логирование для получения ID пользователя
            logger.info(f"Пользователь {message.from_user.id} (@{message.from_user.username}) запросил /admin")
            
            if message.from_user.id not in admin_ids:
                await message.answer(f"⛔ У вас нет прав для выполнения этой команды.\n\n📝 **Ваш ID:** `{message.from_user.id}`\n\nДля получения доступа добавьте свой ID в файл .env:\n```\nADMIN_IDS={message.from_user.id}\n```", parse_mode="Markdown")
                return
            
            admin_text = """
🛠️ **Веб-панель администратора ЮрПомощника**

🌐 <a href="{ADMIN_PANEL_URL}">Адрес админ-панели</a>

🔑 **Данные для входа:**
• Логин: `admin`
• Пароль: `admin123`

⚠️ **Важно:** Панель доступна только при запущенном сервере админ-панели!

**Возможности панели:**
🎛️ **Дашборд** - системная статистика в реальном времени
📊 **Статистика** - детальная информация о системе
📋 **Логи** - просмотр файлов логов (bot.log, scraping.log и др.)
🔧 **Команды** - выполнение административных команд
⚙️ **Процессы** - мониторинг запущенных процессов
📁 **Документы** - управление базой знаний

**Как запустить панель:**
1. Откройте терминал в папке проекта
2. Выполните: `python admin_panel.py`
3. Откройте в браузере: <a href="{ADMIN_PANEL_URL}">Адрес админ-панели</a>
4. Войдите с указанными данными

**Или используйте быстрый запуск:**
• Windows: `start_admin_panel.bat`
• Linux/macOS: `./start_admin_panel.sh`

🔒 **Безопасность:** Смените пароль по умолчанию в файле .env
"""
            
            await message.answer(admin_text.format(ADMIN_PANEL_URL=ADMIN_PANEL_URL), parse_mode="HTML")
            logger.info(f"Пользователь {message.from_user.id} запросил доступ к админ-панели")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке команды /admin: {e}")
            await message.answer("😔 Произошла ошибка при обработке команды.")
    
    async def handle_analytics(self, message: Message):
        """
        Обрабатывает команду /analytics для получения статистики ML-фильтра.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Проверяем права администратора
            admin_ids = config.ADMIN_IDS if config.ADMIN_IDS else [123456789]
            
            if message.from_user.id not in admin_ids:
                await message.answer(f"⛔ У вас нет прав для выполнения этой команды.\n\n📝 **Ваш ID:** `{message.from_user.id}`", parse_mode="Markdown")
                return
            
            # Получаем статистику аналитики
            analytics_summary = get_analytics_summary()
            
            await message.answer(analytics_summary, parse_mode="Markdown")
            logger.info(f"Пользователь {message.from_user.id} запросил аналитику ML-фильтра")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке команды /analytics: {e}")
            await message.answer("😔 Произошла ошибка при получении статистики.")
    
    async def handle_start_admin(self, message: Message):
        """
        Обрабатывает команду /start_admin для запуска админ-панели.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Проверяем права администратора
            admin_ids = config.ADMIN_IDS if config.ADMIN_IDS else [123456789]
            
            # Логирование
            logger.info(f"Пользователь {message.from_user.id} (@{message.from_user.username}) запросил /start_admin")
            
            if message.from_user.id not in admin_ids:
                await message.answer(f"⛔ У вас нет прав для выполнения этой команды.\n\n📝 **Ваш ID:** `{message.from_user.id}`\n\nДля получения доступа добавьте свой ID в файл .env:\n```\nADMIN_IDS={message.from_user.id}\n```", parse_mode="Markdown")
                return
            
            # Отправляем сообщение о запуске
            status_msg = await message.answer("🚀 Запускаю админ-панель...\n⏳ Это может занять несколько секунд...")
            
            try:
                import subprocess
                import sys
                import os
                
                # Определяем команду для запуска
                python_cmd = sys.executable
                admin_panel_script = "admin_panel.py"
                
                # Проверяем существование скрипта
                if not os.path.exists(admin_panel_script):
                    await status_msg.edit_text("❌ Файл admin_panel.py не найден в текущей директории!")
                    return
                
                # Запускаем админ-панель в фоновом режиме
                if os.name == 'nt':  # Windows
                    # Для Windows используем CREATE_NEW_CONSOLE чтобы открыть в новом окне
                    process = subprocess.Popen(
                        [python_cmd, admin_panel_script],
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                        cwd=os.getcwd()
                    )
                else:  # Linux/macOS
                    # Для Unix-систем запускаем в фоне
                    process = subprocess.Popen(
                        [python_cmd, admin_panel_script],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True
                    )
                
                # Ждем немного чтобы процесс успел запуститься
                import asyncio
                await asyncio.sleep(3)
                
                # Проверяем что процесс запустился
                if process.poll() is None:  # Процесс еще работает
                    success_text = f"""
✅ **Админ-панель успешно запущена!**

🌐 **Адрес:** <a href="{ADMIN_PANEL_URL}">Адрес админ-панели</a>
🔑 **Логин:** admin
🔑 **Пароль:** admin123

📝 **PID процесса:** {process.pid}

🎯 **Что делать дальше:**
1. Откройте браузер
2. Перейдите по адресу: <a href="{ADMIN_PANEL_URL}">Адрес админ-панели</a>
3. Войдите с указанными данными
4. Используйте панель для управления системой

⚠️ **Важно:** Панель запущена в фоновом режиме. Для остановки используйте диспетчер задач или перезагрузите компьютер.

🔒 **Безопасность:** Смените пароль по умолчанию в файле .env
"""
                    await status_msg.edit_text(success_text.format(ADMIN_PANEL_URL=ADMIN_PANEL_URL), parse_mode="HTML")
                    logger.info(f"Админ-панель запущена пользователем {message.from_user.id}, PID: {process.pid}")
                else:
                    # Процесс завершился с ошибкой
                    error_text = f"""
❌ **Ошибка запуска админ-панели**

Код возврата: {process.returncode}

**Возможные причины:**
• Порт 5000 уже занят
• Не установлены зависимости
• Ошибка в конфигурации

**Попробуйте:**
1. Закрыть другие приложения на порту 5000
2. Запустить вручную: `python admin_panel.py`
3. Проверить логи на ошибки

**Или используйте ручной запуск:**
• Windows: `start_admin_panel.bat`
• Linux/macOS: `./start_admin_panel.sh`
"""
                    await status_msg.edit_text(error_text, parse_mode="Markdown")
                    logger.error(f"Ошибка запуска админ-панели пользователем {message.from_user.id}, код: {process.returncode}")
                    
            except Exception as e:
                error_text = f"""
❌ **Ошибка при запуске админ-панели**

Ошибка: {str(e)}

**Попробуйте альтернативные способы:**
1. Ручной запуск: `python admin_panel.py`
2. Windows: `start_admin_panel.bat`
3. Linux/macOS: `./start_admin_panel.sh`

**Или используйте команду /admin для получения инструкций**
"""
                await status_msg.edit_text(error_text, parse_mode="Markdown")
                logger.error(f"Исключение при запуске админ-панели: {e}")
                
        except Exception as e:
            logger.error(f"Ошибка при обработке команды /start_admin: {e}")
            await message.answer("😔 Произошла ошибка при обработке команды.")
    
    async def handle_stop_admin(self, message: Message):
        """
        Обрабатывает команду /stop_admin для остановки админ-панели.
        
        Args:
            message: Сообщение от пользователя
        """
        try:
            # Проверяем права администратора
            admin_ids = config.ADMIN_IDS if config.ADMIN_IDS else [123456789]
            
            # Логирование
            logger.info(f"Пользователь {message.from_user.id} (@{message.from_user.username}) запросил /stop_admin")
            
            if message.from_user.id not in admin_ids:
                await message.answer(f"⛔ У вас нет прав для выполнения этой команды.\n\n📝 **Ваш ID:** `{message.from_user.id}`\n\nДля получения доступа добавьте свой ID в файл .env:\n```\nADMIN_IDS={message.from_user.id}\n```", parse_mode="Markdown")
                return
            
            # Отправляем сообщение о поиске процессов
            status_msg = await message.answer("🔍 Ищу процессы админ-панели...")
            
            try:
                import subprocess
                import sys
                import os
                import psutil
                
                # Ищем процессы админ-панели
                admin_processes = []
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = proc.info['cmdline']
                        if cmdline and 'admin_panel.py' in ' '.join(cmdline):
                            admin_processes.append(proc)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                if not admin_processes:
                    await status_msg.edit_text("ℹ️ Процессы админ-панели не найдены. Возможно, панель уже остановлена.")
                    return
                
                # Останавливаем найденные процессы
                stopped_count = 0
                for proc in admin_processes:
                    try:
                        proc.terminate()  # Мягкая остановка
                        proc.wait(timeout=5)  # Ждем до 5 секунд
                        stopped_count += 1
                        logger.info(f"Процесс админ-панели PID {proc.pid} остановлен")
                    except psutil.TimeoutExpired:
                        # Если процесс не завершился, принудительно убиваем
                        proc.kill()
                        stopped_count += 1
                        logger.info(f"Процесс админ-панели PID {proc.pid} принудительно остановлен")
                    except Exception as e:
                        logger.error(f"Ошибка остановки процесса {proc.pid}: {e}")
                
                if stopped_count > 0:
                    success_text = f"""
✅ **Админ-панель остановлена!**

📊 **Статистика:**
• Остановлено процессов: {stopped_count}

🌐 **Статус:** <a href="{ADMIN_PANEL_URL}">Адрес админ-панели</a> недоступен

**Для повторного запуска используйте:**
• `/start_admin` - автоматический запуск
• `/admin` - инструкции по ручному запуску
"""
                    await status_msg.edit_text(success_text.format(ADMIN_PANEL_URL=ADMIN_PANEL_URL), parse_mode="HTML")
                    logger.info(f"Админ-панель остановлена пользователем {message.from_user.id}, процессов: {stopped_count}")
                else:
                    await status_msg.edit_text("⚠️ Не удалось остановить ни одного процесса. Возможно, недостаточно прав.")
                    
            except ImportError:
                error_text = """
❌ **Ошибка: модуль psutil не найден**

Для работы команды /stop_admin требуется модуль psutil.

**Установите его:**
```
pip install psutil
```

**Альтернативные способы остановки:**
• Диспетчер задач (Windows)
• Activity Monitor (macOS)
• htop/ps (Linux)
• Перезагрузка системы
"""
                await status_msg.edit_text(error_text, parse_mode="Markdown")
                
            except Exception as e:
                error_text = f"""
❌ **Ошибка при остановке админ-панели**

Ошибка: {str(e)}

**Альтернативные способы остановки:**
• Диспетчер задач (Windows)
• Activity Monitor (macOS) 
• htop/ps (Linux)
• Перезагрузка системы
"""
                await status_msg.edit_text(error_text, parse_mode="Markdown")
                logger.error(f"Исключение при остановке админ-панели: {e}")
                
        except Exception as e:
            logger.error(f"Ошибка при обработке команды /stop_admin: {e}")
            await message.answer("😔 Произошла ошибка при обработке команды.")
    
    async def handle_deprecated_start_admin(self, message: Message):
        """
        Обрабатывает команду /start_admin с подчеркиванием.
        
        Args:
            message: Сообщение от пользователя
        """
        deprecated_text = """
ℹ️ **Альтернативная команда**

Вы использовали `/start_admin`, но основная команда:
👉 `/startadmin` (без подчеркивания)

Перенаправляю на запуск админ-панели...
"""
        try:
            await message.answer(deprecated_text, parse_mode="Markdown")
            logger.info(f"Пользователь {message.from_user.id} использовал команду /start_admin, перенаправляем на /startadmin")
            # Вызываем основной обработчик
            await self.handle_start_admin(message)
        except TelegramAPIError as e:
            logger.error(f"Ошибка отправки сообщения о команде: {e}")
    
    async def handle_deprecated_stop_admin(self, message: Message):
        """
        Обрабатывает команду /stop_admin с подчеркиванием.
        
        Args:
            message: Сообщение от пользователя
        """
        deprecated_text = """
ℹ️ **Альтернативная команда**

Вы использовали `/stop_admin`, но основная команда:
👉 `/stopadmin` (без подчеркивания)

Перенаправляю на остановку админ-панели...
"""
        try:
            await message.answer(deprecated_text, parse_mode="Markdown")
            logger.info(f"Пользователь {message.from_user.id} использовал команду /stop_admin, перенаправляем на /stopadmin")
            # Вызываем основной обработчик
            await self.handle_stop_admin(message)
        except TelegramAPIError as e:
            logger.error(f"Ошибка отправки сообщения о команде: {e}")
    
    async def handle_question(self, message: Message):
        """
        Обрабатывает вопросы пользователя.
        
        Args:
            message: Сообщение от пользователя
        """
        user_question = message.text
        user_id = message.from_user.id
        
        logger.info(f"Получен вопрос от пользователя {user_id}: {user_question[:100]}...")
        
        # Создаем контекст для аналитики
        context_id = create_question_context(user_question, user_id)
        
        try:
            # Проверяем, является ли вопрос юридическим
            is_legal, score, explanation = is_legal_question(user_question)
            
            if not is_legal:
                # Если вопрос не юридический, отклоняем его
                logger.info(f"❌ ФИЛЬТР: Отклонен неюридический вопрос от пользователя {user_id} "
                           f"(оценка: {score:.3f}): {explanation}")
                
                # Финализируем контекст для отклоненного вопроса
                finalize_question_context(context_id, accepted=False, ml_confidence=score, ml_explanation=explanation)
                
                rejection_message = get_rejection_message()
                await message.answer(rejection_message, parse_mode="Markdown")
                return
            
            # Логируем принятие юридического вопроса
            logger.info(f"✅ ФИЛЬТР: Принят юридический вопрос от пользователя {user_id} "
                       f"(оценка: {score:.3f}): {explanation}")
            
            # Отправляем сообщение о том, что обрабатываем запрос
            processing_msg = await message.answer("🔍 Ищу информацию по вашему вопросу...")
            
            # Сначала ищем в базе знаний
            relevant_docs = search_relevant_docs(user_question, n_results=config.MAX_RESULTS)
            
            # Логируем результаты анализа
            if relevant_docs:
                logger.info(f"📚 ИСТОЧНИК: База знаний - найдено {len(relevant_docs)} документов для пользователя {user_id}")
                # Формируем читаемые названия документов
                doc_titles = []
                for doc in relevant_docs[:3]:
                    metadata = doc.get('metadata', {})
                    title = metadata.get('title') or metadata.get('source_file') or 'Без названия'
                    # Убираем расширение .pdf для краткости
                    if title.endswith('.pdf'):
                        title = title[:-4]
                    doc_titles.append(title[:50])
                logger.info(f"📄 Примеры найденных документов: {doc_titles}")
            else:
                logger.info(f"❌ ИСТОЧНИК: База знаний пуста для пользователя {user_id}")
            
            # Проверяем качество результатов из базы знаний
            need_dynamic_search = False
            if not relevant_docs:
                # Если документов не найдено, всегда ищем на pravo.by
                need_dynamic_search = True
                logger.info(f"🔍 РЕШЕНИЕ: Документы не найдены - всегда ищем на pravo.by")
            else:
                # Проверяем качество лучшего результата
                best_distance = min(doc['distance'] for doc in relevant_docs)
                # Используем более агрессивный порог для динамического поиска
                if best_distance > 0.5:  # Снижен порог с 0.6 до 0.5
                    need_dynamic_search = True
                    logger.info(f"🔍 РЕШЕНИЕ: Низкое качество результатов (дистанция: {best_distance:.3f}) - ищем на pravo.by")
                else:
                    logger.info(f"🔍 РЕШЕНИЕ: Хорошее качество результатов (дистанция: {best_distance:.3f}) - используем базу знаний")
            
            if need_dynamic_search:
                # Выполняем динамический поиск на pravo.by
                await processing_msg.edit_text("🌐 Ищу актуальную информацию на pravo.by...")
                
                try:
                    # Создаем динамический поисковик
                    web_scraper = create_scraper_from_config()
                    knowledge_base = get_knowledge_base()
                    text_processor = TextProcessor()
                    scraping_tracker = get_scraping_tracker()
                    
                    dynamic_searcher = create_dynamic_searcher(
                        web_scraper, knowledge_base, text_processor, scraping_tracker
                    )
                    
                    # Выполняем динамический поиск
                    logger.info(f"🔍 ИСТОЧНИК: Запуск динамического поиска на pravo.by для пользователя {user_id}")
                    dynamic_answer, success = dynamic_searcher.search_and_add_to_knowledge_base(user_question)
                    
                    if success and dynamic_answer:
                        await processing_msg.edit_text(dynamic_answer)
                        logger.info(f"✅ ИСТОЧНИК: Динамический поиск успешен - ответ получен с pravo.by для пользователя {user_id}")
                        
                        # Финализируем контекст для успешного динамического поиска
                        finalize_question_context(context_id, accepted=True, ml_confidence=score, ml_explanation=explanation,
                                                search_quality="high", answer_source="dynamic_search")
                        return
                    else:
                        # Если динамический поиск не помог, но в базе есть хоть что-то
                        if relevant_docs:
                            await processing_msg.edit_text("🔍 Информация на pravo.by не найдена. Генерирую ответ на основе базы знаний...")
                            answer = get_answer(user_question, relevant_docs)
                            await processing_msg.edit_text(answer)
                            logger.info(f"✅ ИСТОЧНИК: Ответ получен из базы знаний после неуспешного поиска на pravo.by для пользователя {user_id}")
                            
                            # Финализируем контекст для ответа из базы знаний после неуспешного поиска
                            search_quality = "medium" if min(doc['distance'] for doc in relevant_docs) <= 0.5 else "low"
                            finalize_question_context(context_id, accepted=True, ml_confidence=score, ml_explanation=explanation,
                                                    search_quality=search_quality, answer_source="knowledge_base_fallback")
                            return
                        else:
                            # Если динамический поиск не помог и в базе ничего нет
                            no_info_response = """
😔 К сожалению, я не нашел информации по вашему вопросу ни в базе знаний, ни на pravo.by.

**Попробуйте:**
• Переформулировать вопрос более конкретно
• Задать вопрос по другой теме права
• Уточнить сферу права (трудовое, гражданское, семейное и т.д.)

**Пример:** вместо "Что делать?" спросите "Что делать при увольнении в РБ?"

🔄 **Хорошая новость:** Я попытался найти информацию на pravo.by и пополнил свою базу знаний. Возможно, следующий похожий вопрос я смогу решить!

Или обратитесь к квалифицированному юристу для получения персональной консультации.
"""
                            await processing_msg.edit_text(no_info_response, parse_mode="Markdown")
                            
                            # Финализируем контекст для случая, когда информация не найдена
                            finalize_question_context(context_id, accepted=True, ml_confidence=score, ml_explanation=explanation,
                                                    search_quality="none", answer_source="no_answer")
                            return
                        
                except Exception as e:
                    logger.error(f"Ошибка динамического поиска: {e}")
                    
                    # Если произошла ошибка, но в базе есть документы - используем их
                    if relevant_docs:
                        await processing_msg.edit_text("⚠️ Ошибка поиска на pravo.by. Генерирую ответ на основе базы знаний...")
                        answer = get_answer(user_question, relevant_docs)
                        await processing_msg.edit_text(answer)
                        logger.info(f"✅ ИСТОЧНИК: Ответ получен из базы знаний после ошибки поиска на pravo.by для пользователя {user_id}")
                        
                        # Финализируем контекст для ответа из базы знаний после ошибки поиска
                        search_quality = "medium" if min(doc['distance'] for doc in relevant_docs) <= 0.5 else "low"
                        finalize_question_context(context_id, accepted=True, ml_confidence=score, ml_explanation=explanation,
                                                search_quality=search_quality, answer_source="knowledge_base_error")
                        return
                    else:
                        # Если ошибка и в базе ничего нет
                        no_info_response = """
😔 К сожалению, произошла ошибка при поиске информации.

**Попробуйте:**
• Переформулировать вопрос
• Задать более конкретный вопрос
• Уточнить сферу права

**Пример:** вместо "Что делать?" спросите "Что делать при увольнении?"

Или обратитесь к квалифицированному юристу для получения персональной консультации.
"""
                        await processing_msg.edit_text(no_info_response, parse_mode="Markdown")
                        
                        # Финализируем контекст для случая ошибки без базы знаний
                        finalize_question_context(context_id, accepted=True, ml_confidence=score, ml_explanation=explanation,
                                                search_quality="error", answer_source="error")
                        return
            
            # Генерируем ответ с помощью LLM
            logger.info(f"🤖 ИСТОЧНИК: Генерация ответа через OpenAI на основе базы знаний для пользователя {user_id}")
            answer = get_answer(user_question, relevant_docs)
            
            # Отправляем ответ пользователю (без Markdown чтобы избежать ошибок парсинга)
            await processing_msg.edit_text(answer)
            
            logger.info(f"✅ ИСТОЧНИК: Ответ отправлен пользователю {user_id} - OpenAI + База знаний")
            
            # Финализируем контекст для принятого вопроса
            search_quality = "high" if relevant_docs and min(doc['distance'] for doc in relevant_docs) <= 0.5 else "medium"
            finalize_question_context(context_id, accepted=True, ml_confidence=score, ml_explanation=explanation, 
                                    search_quality=search_quality, answer_source="knowledge_base")
            
        except TelegramAPIError as e:
            logger.error(f"Ошибка Telegram API: {e}")
            # Если ошибка парсинга, отправляем ответ без форматирования
            try:
                answer = get_answer(user_question, relevant_docs)
                await message.answer(answer)
                
                # Финализируем контекст для случая ошибки Telegram API с ответом
                search_quality = "medium" if relevant_docs and min(doc['distance'] for doc in relevant_docs) <= 0.5 else "low"
                finalize_question_context(context_id, accepted=True, ml_confidence=score, ml_explanation=explanation,
                                        search_quality=search_quality, answer_source="telegram_api_error")
            except:
                await message.answer("Извините, произошла ошибка при отправке ответа.")
                
                # Финализируем контекст для критической ошибки
                finalize_question_context(context_id, accepted=True, ml_confidence=score, ml_explanation=explanation,
                                        search_quality="error", answer_source="critical_error")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при обработке вопроса: {e}")
            error_response = """
😔 Произошла техническая ошибка при обработке вашего запроса.

Пожалуйста, попробуйте:
• Переформулировать вопрос
• Задать вопрос позже
• Обратиться в поддержку

Приносим извинения за неудобства!
"""
            await message.answer(error_response)
            
            # Финализируем контекст для неожиданной ошибки
            try:
                finalize_question_context(context_id, accepted=True, ml_confidence=score, ml_explanation=explanation,
                                        search_quality="error", answer_source="unexpected_error")
            except:
                # Если даже финализация не работает, просто логируем
                logger.error("Ошибка при финализации контекста аналитики")
    
    async def start_polling(self):
        """Запускает бота в режиме polling."""
        try:
            logger.info("Запуск бота в режиме polling...")
            # Устанавливаем команды бота
            await self._setup_bot_commands()
            await self.dp.start_polling(self.bot)
        except Exception as e:
            logger.error(f"Ошибка при запуске polling: {e}")
            raise
    
    async def stop(self):
        """Останавливает бота."""
        await self.bot.session.close()
        logger.info("Бот остановлен")

# Глобальный экземпляр бота
_bot_instance = None

def get_bot() -> LegalBot:
    """Возвращает глобальный экземпляр бота."""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = LegalBot()
    return _bot_instance

def start_bot():
    """Запускает бота."""
    import asyncio
    
    bot = get_bot()
    
    try:
        asyncio.run(bot.start_polling())
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise
    finally:
        logger.info("Бот завершает работу") 