"""
Модуль для сбора и анализа пользовательских данных для дообучения ML-фильтра.
"""
import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

class UserAnalytics:
    """Класс для сбора и анализа пользовательских данных."""
    
    def __init__(self, db_path: str = "db/user_analytics.db"):
        """
        Инициализирует систему аналитики.
        
        Args:
            db_path: Путь к файлу базы данных SQLite
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        logger.info(f"✅ Система аналитики инициализирована: {db_path}")
    
    def _init_database(self):
        """Инициализирует базу данных и создает таблицы."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица для вопросов пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    question_text TEXT NOT NULL,
                    question_length INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ml_prediction BOOLEAN,
                    ml_confidence REAL,
                    ml_explanation TEXT,
                    was_accepted BOOLEAN,
                    search_result_quality TEXT,
                    search_distance REAL,
                    docs_found INTEGER,
                    source_type TEXT,  -- 'knowledge_base', 'dynamic_search', 'error'
                    response_length INTEGER,
                    processing_time_ms INTEGER,
                    keywords TEXT,  -- JSON массив ключевых слов
                    question_category TEXT,  -- автоматически определяемая категория
                    session_id TEXT  -- для группировки вопросов в сессии
                )
            """)
            
            # Таблица для отклоненных вопросов (важно для анализа ложных срабатываний)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rejected_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    question_text TEXT NOT NULL,
                    question_length INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ml_confidence REAL,
                    ml_explanation TEXT,
                    user_feedback TEXT,  -- если пользователь жалуется на неправильное отклонение
                    manual_review BOOLEAN DEFAULT FALSE,
                    should_be_legal BOOLEAN  -- результат ручной проверки
                )
            """)
            
            # Таблица для паттернов и статистики
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ml_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE DEFAULT CURRENT_DATE,
                    total_questions INTEGER,
                    accepted_questions INTEGER,
                    rejected_questions INTEGER,
                    avg_confidence REAL,
                    low_confidence_count INTEGER,  -- < 0.7
                    high_confidence_count INTEGER,  -- > 0.9
                    false_positives INTEGER,  -- оценочно
                    false_negatives INTEGER,  -- оценочно
                    dynamic_search_triggered INTEGER,
                    knowledge_base_hits INTEGER
                )
            """)
            
            # Индексы для быстрого поиска
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_questions_user_id ON user_questions(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_questions_timestamp ON user_questions(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_questions_ml_prediction ON user_questions(ml_prediction)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_rejected_questions_timestamp ON rejected_questions(timestamp)")
            
            conn.commit()
            logger.info("📊 База данных аналитики инициализирована")
    
    def log_question(self, user_id: int, question_text: str, ml_result: Tuple[bool, float, str], 
                    search_results: Dict[str, Any] = None, response_info: Dict[str, Any] = None,
                    session_id: str = None) -> int:
        """
        Логирует вопрос пользователя и результаты обработки.
        
        Args:
            user_id: ID пользователя
            question_text: Текст вопроса
            ml_result: Результат ML-фильтра (предсказание, уверенность, объяснение)
            search_results: Результаты поиска в базе знаний
            response_info: Информация об ответе
            session_id: ID сессии
            
        Returns:
            ID записи в базе данных
        """
        try:
            is_legal, confidence, explanation = ml_result
            
            # Извлекаем ключевые слова
            keywords = self._extract_keywords(question_text)
            
            # Определяем категорию вопроса
            category = self._categorize_question(question_text, keywords)
            
            # Подготавливаем данные для вставки
            question_data = {
                'user_id': user_id,
                'question_text': question_text,
                'question_length': len(question_text),
                'ml_prediction': is_legal,
                'ml_confidence': confidence,
                'ml_explanation': explanation,
                'was_accepted': is_legal,
                'keywords': json.dumps(keywords, ensure_ascii=False),
                'question_category': category,
                'session_id': session_id or f"session_{user_id}_{datetime.now().strftime('%Y%m%d_%H')}"
            }
            
            # Добавляем информацию о поиске, если есть
            if search_results:
                question_data.update({
                    'search_result_quality': search_results.get('quality', 'unknown'),
                    'search_distance': search_results.get('best_distance'),
                    'docs_found': search_results.get('docs_count', 0),
                    'source_type': search_results.get('source_type', 'unknown')
                })
            
            # Добавляем информацию об ответе, если есть
            if response_info:
                question_data.update({
                    'response_length': response_info.get('response_length', 0),
                    'processing_time_ms': response_info.get('processing_time_ms', 0)
                })
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if is_legal:
                    # Вопрос принят - записываем в основную таблицу
                    columns = ', '.join(question_data.keys())
                    placeholders = ', '.join(['?' for _ in question_data])
                    query = f"INSERT INTO user_questions ({columns}) VALUES ({placeholders})"
                    cursor.execute(query, list(question_data.values()))
                else:
                    # Вопрос отклонен - записываем в таблицу отклоненных
                    rejected_data = {
                        'user_id': user_id,
                        'question_text': question_text,
                        'question_length': len(question_text),
                        'ml_confidence': confidence,
                        'ml_explanation': explanation
                    }
                    columns = ', '.join(rejected_data.keys())
                    placeholders = ', '.join(['?' for _ in rejected_data])
                    query = f"INSERT INTO rejected_questions ({columns}) VALUES ({placeholders})"
                    cursor.execute(query, list(rejected_data.values()))
                
                question_id = cursor.lastrowid
                conn.commit()
                
                logger.debug(f"📝 Вопрос пользователя {user_id} сохранен в аналитику (ID: {question_id})")
                return question_id
                
        except Exception as e:
            logger.error(f"Ошибка сохранения вопроса в аналитику: {e}")
            return -1
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Извлекает ключевые слова из текста."""
        import re
        
        # Простое извлечение ключевых слов
        stop_words = {
            'как', 'что', 'где', 'когда', 'почему', 'зачем', 'кто', 'какой', 'какая', 'какие',
            'в', 'на', 'с', 'по', 'для', 'от', 'до', 'при', 'за', 'под', 'над', 'между',
            'и', 'или', 'но', 'а', 'да', 'нет', 'не', 'ни', 'же', 'ли', 'бы', 'то',
            'это', 'этот', 'эта', 'эти', 'тот', 'та', 'те'
        }
        
        words = re.findall(r'\b[а-яёa-z]+\b', text.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        return keywords[:10]  # Ограничиваем количество
    
    def _categorize_question(self, text: str, keywords: List[str]) -> str:
        """Автоматически определяет категорию вопроса."""
        text_lower = text.lower()
        
        # Категории по ключевым словам
        categories = {
            'налоги': ['налог', 'подоходный', 'ндс', 'налогообложение', 'декларация', 'льгота'],
            'трудовые_отношения': ['трудовой', 'договор', 'увольнение', 'зарплата', 'отпуск', 'больничный'],
            'регистрация_бизнеса': ['ип', 'регистрация', 'предприниматель', 'ооо', 'лицензия'],
            'семейное_право': ['развод', 'алименты', 'брак', 'наследство', 'опека'],
            'недвижимость': ['квартира', 'дом', 'аренда', 'покупка', 'продажа', 'недвижимость'],
            'административные_правонарушения': ['штраф', 'нарушение', 'гибдд', 'коап', 'протокол'],
            'гражданские_споры': ['иск', 'суд', 'возмещение', 'ущерб', 'договор'],
            'социальные_вопросы': ['пенсия', 'пособие', 'льготы', 'инвалидность', 'материнский'],
            'документооборот': ['справка', 'документы', 'паспорт', 'виза', 'загранпаспорт']
        }
        
        for category, category_keywords in categories.items():
            if any(keyword in text_lower for keyword in category_keywords):
                return category
        
        return 'общие_вопросы'
    
    def get_analytics_summary(self, days: int = 30) -> Dict[str, Any]:
        """
        Возвращает сводку аналитики за указанный период.
        
        Args:
            days: Количество дней для анализа
            
        Returns:
            Словарь с аналитическими данными
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Общая статистика
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_questions,
                        AVG(ml_confidence) as avg_confidence,
                        COUNT(CASE WHEN ml_confidence < 0.7 THEN 1 END) as low_confidence,
                        COUNT(CASE WHEN ml_confidence > 0.9 THEN 1 END) as high_confidence,
                        COUNT(CASE WHEN source_type = 'dynamic_search' THEN 1 END) as dynamic_searches
                    FROM user_questions 
                    WHERE timestamp >= datetime('now', '-{} days')
                """.format(days))
                
                accepted_stats = cursor.fetchone()
                
                # Статистика отклоненных вопросов
                cursor.execute("""
                    SELECT 
                        COUNT(*) as rejected_count,
                        AVG(ml_confidence) as avg_rejected_confidence
                    FROM rejected_questions 
                    WHERE timestamp >= datetime('now', '-{} days')
                """.format(days))
                
                rejected_stats = cursor.fetchone()
                
                # Топ категорий
                cursor.execute("""
                    SELECT question_category, COUNT(*) as count
                    FROM user_questions 
                    WHERE timestamp >= datetime('now', '-{} days')
                    GROUP BY question_category 
                    ORDER BY count DESC 
                    LIMIT 10
                """.format(days))
                
                top_categories = cursor.fetchall()
                
                return {
                    'period_days': days,
                    'total_questions': accepted_stats[0] or 0,
                    'rejected_questions': rejected_stats[0] or 0,
                    'avg_confidence': round(accepted_stats[1] or 0, 3),
                    'avg_rejected_confidence': round(rejected_stats[1] or 0, 3),
                    'low_confidence_count': accepted_stats[2] or 0,
                    'high_confidence_count': accepted_stats[3] or 0,
                    'dynamic_searches': accepted_stats[4] or 0,
                    'top_categories': [{'category': cat, 'count': count} for cat, count in top_categories],
                    'ml_accuracy_estimate': self._estimate_accuracy(days)
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения аналитики: {e}")
            return {'error': str(e)}
    
    def _estimate_accuracy(self, days: int) -> Dict[str, Any]:
        """Оценивает точность ML-фильтра на основе косвенных признаков."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Предположительные ложные срабатывания (очень низкая уверенность в принятых)
                cursor.execute("""
                    SELECT COUNT(*) FROM user_questions 
                    WHERE ml_confidence < 0.6 AND timestamp >= datetime('now', '-{} days')
                """.format(days))
                likely_false_positives = cursor.fetchone()[0]
                
                # Предположительные пропуски (высокая уверенность в отклоненных)
                cursor.execute("""
                    SELECT COUNT(*) FROM rejected_questions 
                    WHERE ml_confidence > 0.8 AND timestamp >= datetime('now', '-{} days')
                """.format(days))
                likely_false_negatives = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM user_questions 
                    WHERE timestamp >= datetime('now', '-{} days')
                """.format(days))
                total_accepted = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM rejected_questions 
                    WHERE timestamp >= datetime('now', '-{} days')
                """.format(days))
                total_rejected = cursor.fetchone()[0]
                
                total_questions = total_accepted + total_rejected
                
                if total_questions > 0:
                    estimated_accuracy = 1 - (likely_false_positives + likely_false_negatives) / total_questions
                    return {
                        'estimated_accuracy': round(max(0, estimated_accuracy), 3),
                        'likely_false_positives': likely_false_positives,
                        'likely_false_negatives': likely_false_negatives,
                        'total_questions': total_questions
                    }
                
                return {'estimated_accuracy': 0, 'insufficient_data': True}
                
        except Exception as e:
            logger.error(f"Ошибка оценки точности: {e}")
            return {'error': str(e)}
    
    def export_training_data(self, output_file: str = "ml_training_data.csv", 
                           min_confidence: float = 0.8) -> bool:
        """
        Экспортирует данные для дообучения ML-модели.
        
        Args:
            output_file: Путь к выходному файлу
            min_confidence: Минимальная уверенность для включения в датасет
            
        Returns:
            True если экспорт успешен
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Экспортируем принятые вопросы с высокой уверенностью
                accepted_df = pd.read_sql_query("""
                    SELECT 
                        question_text,
                        1 as is_legal,
                        ml_confidence,
                        question_category,
                        keywords
                    FROM user_questions 
                    WHERE ml_confidence >= ?
                    ORDER BY timestamp DESC
                """, conn, params=[min_confidence])
                
                # Экспортируем отклоненные вопросы с высокой уверенностью
                rejected_df = pd.read_sql_query("""
                    SELECT 
                        question_text,
                        0 as is_legal,
                        ml_confidence,
                        'non_legal' as question_category,
                        '[]' as keywords
                    FROM rejected_questions 
                    WHERE ml_confidence >= ?
                    ORDER BY timestamp DESC
                """, conn, params=[min_confidence])
                
                # Объединяем данные
                combined_df = pd.concat([accepted_df, rejected_df], ignore_index=True)
                
                # Сохраняем в CSV
                combined_df.to_csv(output_file, index=False, encoding='utf-8')
                
                logger.info(f"✅ Экспортировано {len(combined_df)} записей для дообучения в {output_file}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка экспорта данных для обучения: {e}")
            return False
    
    def get_low_confidence_questions(self, threshold: float = 0.7, limit: int = 50) -> List[Dict]:
        """Возвращает вопросы с низкой уверенностью для ручной проверки."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        id, question_text, ml_confidence, ml_prediction, ml_explanation, timestamp
                    FROM user_questions 
                    WHERE ml_confidence < ?
                    ORDER BY ml_confidence ASC, timestamp DESC
                    LIMIT ?
                """, [threshold, limit])
                
                columns = ['id', 'question_text', 'ml_confidence', 'ml_prediction', 'ml_explanation', 'timestamp']
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Ошибка получения вопросов с низкой уверенностью: {e}")
            return []

# Глобальный экземпляр аналитики
_analytics_instance = None

def get_analytics() -> UserAnalytics:
    """Возвращает глобальный экземпляр системы аналитики."""
    global _analytics_instance
    if _analytics_instance is None:
        _analytics_instance = UserAnalytics()
    return _analytics_instance

def log_user_question(user_id: int, question_text: str, ml_result: Tuple[bool, float, str], 
                     search_results: Dict[str, Any] = None, response_info: Dict[str, Any] = None,
                     session_id: str = None) -> int:
    """Удобная функция для логирования вопроса пользователя."""
    return get_analytics().log_question(user_id, question_text, ml_result, search_results, response_info, session_id) 