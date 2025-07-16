"""
Модуль интеграции аналитики ML-фильтра с существующей системой.
"""
import time
import logging
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

from .user_analytics import log_user_question

logger = logging.getLogger(__name__)

class MLAnalyticsIntegrator:
    """Класс для интеграции аналитики в существующий workflow."""
    
    def __init__(self):
        """Инициализирует интегратор аналитики."""
        self.session_cache = {}  # Кеш сессий пользователей
        logger.info("✅ Интегратор ML-аналитики инициализирован")
    
    def track_question_processing(self, user_id: int, question_text: str, 
                                ml_result: Tuple[bool, float, str]) -> Dict[str, Any]:
        """
        Отслеживает начало обработки вопроса.
        
        Args:
            user_id: ID пользователя
            question_text: Текст вопроса
            ml_result: Результат ML-фильтра
            
        Returns:
            Контекст обработки для последующего использования
        """
        start_time = time.time()
        session_id = self._get_or_create_session(user_id)
        
        context = {
            'user_id': user_id,
            'question_text': question_text,
            'ml_result': ml_result,
            'session_id': session_id,
            'start_time': start_time,
            'timestamp': datetime.now().isoformat()
        }
        
        is_legal, confidence, explanation = ml_result
        logger.info(f"📊 АНАЛИТИКА: Начало обработки вопроса пользователя {user_id}, ML: {is_legal} ({confidence:.3f})")
        
        return context
    
    def track_search_results(self, context: Dict[str, Any], relevant_docs: list, 
                           best_distance: float = None, source_type: str = "knowledge_base") -> Dict[str, Any]:
        """
        Отслеживает результаты поиска в базе знаний.
        
        Args:
            context: Контекст обработки вопроса
            relevant_docs: Найденные документы
            best_distance: Лучшая дистанция поиска
            source_type: Тип источника ('knowledge_base', 'dynamic_search')
            
        Returns:
            Обновленный контекст
        """
        docs_count = len(relevant_docs) if relevant_docs else 0
        
        # Определяем качество результатов
        quality = "unknown"
        if best_distance is not None:
            if best_distance < 0.3:
                quality = "excellent"
            elif best_distance < 0.5:
                quality = "good"
            elif best_distance < 0.8:
                quality = "satisfactory"
            else:
                quality = "poor"
        
        search_results = {
            'docs_count': docs_count,
            'best_distance': best_distance,
            'quality': quality,
            'source_type': source_type
        }
        
        context['search_results'] = search_results
        
        logger.info(f"📊 АНАЛИТИКА: Поиск завершен для пользователя {context['user_id']}: "
                   f"{docs_count} документов, качество: {quality}")
        
        return context
    
    def track_response_completion(self, context: Dict[str, Any], response_text: str = None,
                                error: str = None) -> int:
        """
        Отслеживает завершение обработки вопроса и сохраняет в аналитику.
        
        Args:
            context: Контекст обработки вопроса
            response_text: Текст ответа (если есть)
            error: Текст ошибки (если произошла)
            
        Returns:
            ID записи в базе аналитики
        """
        end_time = time.time()
        processing_time = int((end_time - context['start_time']) * 1000)  # в миллисекундах
        
        response_info = {
            'response_length': len(response_text) if response_text else 0,
            'processing_time_ms': processing_time,
            'has_error': error is not None,
            'error_message': error
        }
        
        context['response_info'] = response_info
        
        # Сохраняем в базу аналитики
        try:
            analytics_id = log_user_question(
                user_id=context['user_id'],
                question_text=context['question_text'],
                ml_result=context['ml_result'],
                search_results=context.get('search_results'),
                response_info=response_info,
                session_id=context['session_id']
            )
            
            is_legal, confidence, _ = context['ml_result']
            logger.info(f"📊 АНАЛИТИКА: Сохранен вопрос пользователя {context['user_id']} "
                       f"(ID: {analytics_id}, время: {processing_time}мс)")
            
            return analytics_id
            
        except Exception as e:
            logger.error(f"Ошибка сохранения аналитики: {e}")
            return -1
    
    def _get_or_create_session(self, user_id: int) -> str:
        """Получает или создает ID сессии для пользователя."""
        current_hour = datetime.now().strftime('%Y%m%d_%H')
        session_key = f"{user_id}_{current_hour}"
        
        if session_key not in self.session_cache:
            self.session_cache[session_key] = f"session_{session_key}"
            
            # Очищаем старые сессии (старше 24 часов)
            self._cleanup_old_sessions()
        
        return self.session_cache[session_key]
    
    def _cleanup_old_sessions(self):
        """Очищает старые сессии из кеша."""
        current_time = datetime.now()
        to_remove = []
        
        for session_key in self.session_cache:
            try:
                # Извлекаем время из ключа сессии
                time_part = session_key.split('_')[-2] + '_' + session_key.split('_')[-1]
                session_time = datetime.strptime(time_part, '%Y%m%d_%H')
                
                # Удаляем сессии старше 24 часов
                if (current_time - session_time).total_seconds() > 86400:  # 24 часа
                    to_remove.append(session_key)
            except:
                # Если не можем распарсить время, удаляем
                to_remove.append(session_key)
        
        for key in to_remove:
            del self.session_cache[key]
    
    def get_session_stats(self, user_id: int) -> Dict[str, Any]:
        """Возвращает статистику текущей сессии пользователя."""
        from .user_analytics import get_analytics
        
        try:
            session_id = self._get_or_create_session(user_id)
            analytics = get_analytics()
            
            import sqlite3
            with sqlite3.connect(analytics.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        COUNT(*) as questions_count,
                        AVG(ml_confidence) as avg_confidence,
                        COUNT(CASE WHEN source_type = 'dynamic_search' THEN 1 END) as dynamic_searches
                    FROM user_questions 
                    WHERE session_id = ? AND user_id = ?
                """, [session_id, user_id])
                
                stats = cursor.fetchone()
                
                return {
                    'session_id': session_id,
                    'questions_count': stats[0] or 0,
                    'avg_confidence': round(stats[1] or 0, 3),
                    'dynamic_searches': stats[2] or 0
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения статистики сессии: {e}")
            return {'error': str(e)}

# Глобальный экземпляр интегратора
_integrator_instance = None

def get_ml_analytics_integrator() -> MLAnalyticsIntegrator:
    """Возвращает глобальный экземпляр интегратора аналитики."""
    global _integrator_instance
    if _integrator_instance is None:
        _integrator_instance = MLAnalyticsIntegrator()
    return _integrator_instance

def create_question_context(user_id: int, question_text: str, ml_result: Tuple[bool, float, str]) -> Dict[str, Any]:
    """Создает контекст для отслеживания обработки вопроса."""
    return get_ml_analytics_integrator().track_question_processing(user_id, question_text, ml_result)

def update_search_context(context: Dict[str, Any], relevant_docs: list, 
                         best_distance: float = None, source_type: str = "knowledge_base") -> Dict[str, Any]:
    """Обновляет контекст информацией о поиске."""
    return get_ml_analytics_integrator().track_search_results(context, relevant_docs, best_distance, source_type)

def finalize_question_context(context: Dict[str, Any], response_text: str = None, 
                             error: str = None) -> int:
    """Завершает обработку вопроса и сохраняет аналитику."""
    return get_ml_analytics_integrator().track_response_completion(context, response_text, error)

# Упрощенные функции для интеграции с bot_handler.py
def create_question_context(question_text: str, user_id: int) -> str:
    """
    Создает контекст для отслеживания обработки вопроса.
    Упрощенная версия для bot_handler.py.
    
    Args:
        question_text: Текст вопроса
        user_id: ID пользователя
        
    Returns:
        ID контекста
    """
    import uuid
    context_id = str(uuid.uuid4())
    
    # Сохраняем контекст в глобальном кеше
    integrator = get_ml_analytics_integrator()
    integrator.session_cache[context_id] = {
        'user_id': user_id,
        'question_text': question_text,
        'start_time': time.time(),
        'timestamp': datetime.now().isoformat()
    }
    
    return context_id

def finalize_question_context(context_id: str, accepted: bool, ml_confidence: float = None, 
                             ml_explanation: str = None, search_quality: str = None, 
                             answer_source: str = None) -> None:
    """
    Завершает контекст обработки вопроса.
    Упрощенная версия для bot_handler.py.
    
    Args:
        context_id: ID контекста
        accepted: Был ли принят вопрос
        ml_confidence: Уверенность ML-фильтра
        ml_explanation: Объяснение ML-фильтра
        search_quality: Качество поиска
        answer_source: Источник ответа
    """
    try:
        from .user_analytics import get_analytics
        
        # Получаем контекст из кеша
        integrator = get_ml_analytics_integrator()
        context = integrator.session_cache.get(context_id)
        
        if not context:
            logger.error(f"Контекст {context_id} не найден")
            return
            
        analytics = get_analytics()
        
        # Подготавливаем данные для логирования
        user_id = context['user_id']
        question_text = context['question_text']
        ml_result = (accepted, ml_confidence or 0.0, ml_explanation or "")
        
        # Подготавливаем результаты поиска
        search_results = None
        if search_quality:
            search_results = {
                'quality': search_quality,
                'source_type': answer_source or 'unknown'
            }
        
        # Логируем вопрос
        analytics.log_question(
            user_id=user_id,
            question_text=question_text,
            ml_result=ml_result,
            search_results=search_results,
            session_id=context_id
        )
            
        # Очищаем контекст из кеша
        del integrator.session_cache[context_id]
        
    except Exception as e:
        logger.error(f"Ошибка при финализации контекста: {e}")

def get_analytics_summary() -> str:
    """
    Получает сводку аналитики ML-фильтра.
    
    Returns:
        Форматированная сводка статистики
    """
    try:
        from .user_analytics import get_analytics
        
        analytics = get_analytics()
        stats = analytics.get_analytics_summary(days=30)
        
        # Проверяем на ошибки
        if 'error' in stats:
            return f"❌ Ошибка при получении статистики: {stats['error']}"
        
        # Вычисляем производные показатели
        total_all = stats['total_questions'] + stats['rejected_questions']
        acceptance_rate = (stats['total_questions'] / total_all * 100) if total_all > 0 else 0
        rejection_rate = (stats['rejected_questions'] / total_all * 100) if total_all > 0 else 0
        
        # Форматируем ответ
        summary = f"""📊 **Аналитика ML-фильтра за последние 30 дней**

**📈 Общая статистика:**
• Всего вопросов: {total_all}
• Принято: {stats['total_questions']} ({acceptance_rate:.1f}%)
• Отклонено: {stats['rejected_questions']} ({rejection_rate:.1f}%)

**🎯 Точность ML-фильтра:**
• Средняя уверенность принятых: {stats['avg_confidence']:.3f}
• Средняя уверенность отклоненных: {stats['avg_rejected_confidence']:.3f}
• Высокая уверенность (>0.9): {stats['high_confidence_count']}
• Низкая уверенность (<0.7): {stats['low_confidence_count']}

**🔍 Качество поиска:**
• Динамических поисков: {stats['dynamic_searches']}

**📊 Популярные категории:**"""
        
        # Добавляем категории
        for category_data in stats['top_categories']:
            summary += f"\n• {category_data['category']}: {category_data['count']}"
        
        # Добавляем информацию о точности если есть
        if 'ml_accuracy_estimate' in stats and stats['ml_accuracy_estimate']:
            accuracy = stats['ml_accuracy_estimate']
            summary += f"""

**⚠️ Оценка точности:**
• Предполагаемая точность: {accuracy.get('accuracy_estimate', 0):.1f}%
• Потенциальных ошибок: {accuracy.get('potential_errors', 0)}"""
        
        return summary.strip()
        
    except Exception as e:
        logger.error(f"Ошибка при получении сводки аналитики: {e}")
        return "❌ Ошибка при получении статистики аналитики" 