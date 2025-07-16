"""
Модуль для взаимодействия с языковыми моделями (LLM).
"""
import logging
from typing import List, Dict, Any
from datetime import datetime
from openai import OpenAI
from config import OPENAI_API_KEY, DEFAULT_MODEL, MAX_TOKENS
from .scraping_tracker import get_scraping_summary

logger = logging.getLogger(__name__)

# Глобальная переменная для клиента OpenAI (инициализируется при первом использовании)
client = None

def get_system_prompt() -> str:
    """Возвращает системный промпт с информацией о последнем парсинге."""
    current_date = datetime.now().strftime("%d.%m.%Y")
    scraping_info = get_scraping_summary()
    
    return f"""Вы — ведущий юрист-консультант с 15+ годами практики в правовой системе Республики Беларусь. Отвечайте на юридические вопросы, руководствуясь следующей методологией:

1. Системный анализ запроса:
   - Определите:
     • Отрасль права (с обоснованием выбора)
     • Юридическую значимость вопроса
     • Уровень подготовки спрашивающего (новичок/студент/профессионал)
   - Проверьте актуальность на {current_date} с учетом:
     ✓ Последних изменений законодательства
     ✓ Текущей правоприменительной практики

2. Многоуровневая экспертиза:
   • Обязательные элементы:
     1) Ссылки на конкретные нормы (Кодексы/Законы/Подзаконные акты)
     2) Судебная практика за последние 3 года
     3) Альтернативные точки зрения (при наличии)
   • Шкала достоверности:
     100% - прямая норма закона
     80% - устойчивая судебная практика
     60% - доктринальное толкование

3. Адаптивный ответ:
   [Для граждан]
   - Итоговый вывод (до 10 слов)
   - Объяснение "на пальцах" (3-5 предложений)
   - Чек-лист действий

   [Для специалистов]
   - Глубокий анализ с:
     • Разбором коллизий
     • Сравнением с международным опытом
     • Прогнозом развития регулирования

4. Превентивная безопасность:
   ! Важно: автоматически проверять:
   - Соответствие Конституции РБ
   - Отсутствие конфликта интересов
   - Возможные риски применения советов

⚖️ Гарантии качества:
• Ежедневная сверка с Национальным правовым порталом
• Маркировка спорных вопросов (⚡️Требует уточнения)
• Механизм обратной связи для коррекции

 Дисклеймер:
Ответы соответствуют законодательству РБ на дату: {scraping_info}
Не заменяют персональную консультацию (ст. 1014 ГК РБ)
"""

class LLMService:
    """Сервис для работы с языковыми моделями."""
    
    def __init__(self, model: str = DEFAULT_MODEL):
        """
        Инициализирует сервис.
        
        Args:
            model: Название модели OpenAI
        """
        self.model = model
        self.client = None
        logger.info(f"Инициализирован LLM сервис с моделью: {model}")
    
    def _get_client(self):
        """Получает клиент OpenAI, инициализируя его при необходимости."""
        if self.client is None:
            if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("ВАШ_") or OPENAI_API_KEY.startswith("sk-test"):
                raise ValueError(
                    "Необходимо настроить валидный OPENAI_API_KEY в файле .env. "
                    "Получите ключ на https://platform.openai.com/api-keys"
                )
            self.client = OpenAI(api_key=OPENAI_API_KEY)
        return self.client
    
    def get_answer(self, user_question: str, context_docs: List[Dict[str, Any]]) -> str:
        """
        Генерирует ответ на основе вопроса пользователя и контекста.
        
        Args:
            user_question: Вопрос пользователя
            context_docs: Список релевантных документов из базы знаний
            
        Returns:
            Сгенерированный ответ
        """
        try:
            # Формируем контекст из найденных документов
            context = self._format_context(context_docs)
            
            # Формируем полный промпт для пользователя
            user_prompt = self._create_user_prompt(user_question, context, context_docs)
            
            # Отправляем запрос к OpenAI
            response = self._get_client().chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=MAX_TOKENS,
                temperature=0.3,  # Низкая температура для более точных ответов
                top_p=0.9
            )
            
            answer = response.choices[0].message.content.strip()
            
            # Логируем статистику использования токенов
            usage = response.usage
            logger.info(f"🤖 OPENAI: Использовано токенов: {usage.total_tokens} "
                       f"(промпт: {usage.prompt_tokens}, ответ: {usage.completion_tokens})")
            logger.info(f"📝 OPENAI: Длина ответа: {len(answer)} символов")
            
            return answer
            
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа: {e}")
            return self._get_error_response()
    
    def _format_context(self, docs: List[Dict[str, Any]]) -> str:
        """
        Форматирует документы в контекст для промпта.
        
        Args:
            docs: Список документов с метаданными
            
        Returns:
            Отформатированный контекст
        """
        if not docs:
            return "Релевантная информация в базе знаний не найдена."
        
        formatted_docs = []
        for i, doc in enumerate(docs, 1):
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            title = metadata.get('title', f'Документ {i}')
            formatted_docs.append(f"Документ {i} ({title}):\n{content}")
        
        return "\n\n".join(formatted_docs)
    
    def _analyze_document_dates(self, context_docs: List[Dict[str, Any]]) -> str:
        """
        Анализирует даты документов и возвращает информацию об актуальности.
        
        Args:
            context_docs: Список документов с метаданными
            
        Returns:
            Строка с информацией об актуальности данных
        """
        if not context_docs:
            return get_scraping_summary()
        
        from datetime import datetime, timezone, timedelta
        
        dates_with_time = []
        source_types = set()
        
        # Часовой пояс МСК (UTC+3)
        msk_tz = timezone(timedelta(hours=3))
        
        for doc in context_docs:
            metadata = doc.get('metadata', {})
            source_types.add(metadata.get('source_type', 'unknown'))
            
            # Проверяем различные типы дат
            scraped_at = metadata.get('scraped_at')
            added_date = metadata.get('added_date')
            
            if scraped_at:
                try:
                    # Формат: 20250712_170540
                    if len(scraped_at) >= 15:  # Есть время
                        date_obj = datetime.strptime(scraped_at, "%Y%m%d_%H%M%S")
                    else:  # Только дата
                        date_str = scraped_at[:8]
                        date_obj = datetime.strptime(date_str, "%Y%m%d")
                    
                    # Предполагаем, что время уже в МСК (pravo.by - белорусский сайт)
                    date_obj = date_obj.replace(tzinfo=msk_tz)
                    dates_with_time.append(date_obj)
                except:
                    pass
            elif added_date:
                try:
                    # Формат: 2025-07-12T17:05:40.373643
                    date_obj = datetime.fromisoformat(added_date.replace('Z', '+00:00'))
                    # Конвертируем в МСК
                    date_obj = date_obj.astimezone(msk_tz)
                    dates_with_time.append(date_obj)
                except:
                    pass
        
        if not dates_with_time:
            return get_scraping_summary()
        
        # Находим самую старую и самую новую дату
        min_date = min(dates_with_time)
        max_date = max(dates_with_time)
        
        # Форматируем даты для вывода с временем МСК
        min_date_str = min_date.strftime("%d.%m.%Y %H:%M МСК")
        max_date_str = max_date.strftime("%d.%m.%Y %H:%M МСК")
        
        # Определяем тип источников
        if 'pravo.by_dynamic' in source_types:
            source_info = "источник: pravo.by"
        elif len(source_types) == 1 and 'unknown' not in source_types:
            source_info = f"источник: {list(source_types)[0]}"
        else:
            source_info = "смешанные источники"
        
        # Формируем итоговую строку
        if min_date.date() == max_date.date():
            # Если та же дата, показываем диапазон времени
            if min_date == max_date:
                return f"{min_date_str} ({source_info})"
            else:
                date_str = min_date.strftime("%d.%m.%Y")
                # Показываем диапазон времени только если времена разные
                if min_date.time() == max_date.time():
                    return f"{date_str} {min_date.strftime('%H:%M')} МСК ({source_info})"
                else:
                    time_range = f"{min_date.strftime('%H:%M')}-{max_date.strftime('%H:%M')} МСК"
                    return f"{date_str} {time_range} ({source_info})"
        else:
            return f"{min_date_str} - {max_date_str} ({source_info})"

    def _create_user_prompt(self, question: str, context: str, context_docs: List[Dict[str, Any]] = None) -> str:
        """
        Создает промпт для пользователя.
        
        Args:
            question: Вопрос пользователя
            context: Контекст из базы знаний
            context_docs: Документы для анализа дат (опционально)
            
        Returns:
            Сформированный промпт
        """
        # Получаем информацию об актуальности на основе реальных документов
        if context_docs:
            date_info = self._analyze_document_dates(context_docs)
        else:
            date_info = get_scraping_summary()
        
        return f"""
Вопрос пользователя: "{question}"

Информация из базы знаний:
{context}

ЗАДАЧА: Ответьте на вопрос пользователя, строго следуя методологии из системного промпта:

1. СИСТЕМНЫЙ АНАЛИЗ:
   - Определите отрасль права и обоснуйте выбор
   - Оцените юридическую значимость вопроса
   - Определите уровень подготовки пользователя (новичок/студент/профессионал)

2. МНОГОУРОВНЕВАЯ ЭКСПЕРТИЗА:
   - Приведите ссылки на конкретные нормы (статьи, кодексы, законы)
   - Укажите шкалу достоверности (100%/80%/60%)
   - Отметьте альтернативные точки зрения, если есть

3. АДАПТИВНЫЙ ОТВЕТ:
   - Для граждан: итоговый вывод + объяснение + чек-лист действий
   - Для специалистов: глубокий анализ с разбором коллизий

4. ПРЕВЕНТИВНАЯ БЕЗОПАСНОСТЬ:
   - Проверьте соответствие Конституции РБ
   - Укажите возможные риски применения советов

ВАЖНО: Обязательно завершите свой ответ следующим дисклеймером:
"⚖️ Ответ соответствует законодательству РБ на дату: {date_info}. Не заменяет персональную консультацию (ст. 1014 ГК РБ)."
"""
    
    def _get_error_response(self) -> str:
        """
        Возвращает сообщение об ошибке для пользователя.
        
        Returns:
            Сообщение об ошибке
        """
        return """
😔 Извините, произошла техническая ошибка при обработке вашего запроса.

Пожалуйста, попробуйте:
1. Переформулировать вопрос
2. Задать более конкретный вопрос
3. Обратиться позже

Если проблема повторяется, свяжитесь с технической поддержкой.
"""
    
    def get_model_info(self) -> dict:
        """
        Возвращает информацию о текущей модели.
        
        Returns:
            Информация о модели
        """
        return {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "temperature": 0.3
        }

# Глобальный экземпляр LLM сервиса
_llm_service = None

def get_llm_service() -> LLMService:
    """Получает глобальный экземпляр LLM сервиса."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

def get_answer(user_question: str, context_docs: List[Dict[str, Any]]) -> str:
    """
    Функция-обертка для получения ответа от LLM.
    
    Args:
        user_question: Вопрос пользователя
        context_docs: Список релевантных документов из базы знаний
        
    Returns:
        Сгенерированный ответ
    """
    llm_service = get_llm_service()
    return llm_service.get_answer(user_question, context_docs) 