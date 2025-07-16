"""
Гибридный фильтр для определения юридических вопросов.
Комбинирует улучшенный фильтр с ML-фильтром для максимальной точности.
"""

import logging
from typing import Tuple, Optional
from .improved_question_filter import ImprovedQuestionFilter
from .ml_question_filter import MLQuestionFilter

logger = logging.getLogger(__name__)

class HybridQuestionFilter:
    """
    Гибридный фильтр, комбинирующий улучшенный фильтр с ML-фильтром.
    Использует голосование и взвешенное усреднение для принятия решения.
    """
    
    def __init__(self):
        """Инициализация гибридного фильтра."""
        self.improved_filter = ImprovedQuestionFilter()
        try:
            self.ml_filter = MLQuestionFilter()
            self.ml_available = True
        except Exception as e:
            logger.warning(f"ML-фильтр недоступен: {e}")
            self.ml_available = False
    
    def is_legal_question(self, question: str) -> Tuple[bool, float, str]:
        """
        Определяет, является ли вопрос юридическим с использованием гибридного подхода.
        
        Args:
            question: Текст вопроса
            
        Returns:
            Кортеж (is_legal, confidence, explanation)
        """
        if not question or not question.strip():
            return False, 0.0, "Пустой вопрос"
        
        # Получаем результат от улучшенного фильтра
        improved_result, improved_score, improved_explanation = self.improved_filter.is_legal_question(question)
        
        # Если ML-фильтр недоступен, используем только улучшенный фильтр
        if not self.ml_available:
            return improved_result, improved_score, f"Улучшенный фильтр: {improved_explanation}"
        
        try:
            # Получаем результат от ML-фильтра
            ml_result, ml_score, ml_explanation = self.ml_filter.is_legal_question(question)
            
            # Комбинируем результаты с весами
            # Улучшенный фильтр имеет больший вес (0.7) из-за лучшей производительности
            combined_score = improved_score * 0.7 + ml_score * 0.3
            
            # Определяем финальный результат
            # Если оба фильтра согласны, используем их решение
            if improved_result == ml_result:
                final_result = improved_result
                confidence = combined_score
                explanation = f"Согласие фильтров: улучшенный={improved_score:.3f}, ML={ml_score:.3f}"
            else:
                # Если фильтры не согласны, используем более консервативный подход
                # Приоритет отдается улучшенному фильтру
                if improved_score > 0.15:  # Высокая уверенность улучшенного фильтра
                    final_result = improved_result
                    confidence = improved_score
                    explanation = f"Приоритет улучшенного: {improved_score:.3f} vs ML: {ml_score:.3f}"
                elif ml_score > 0.8:  # Очень высокая уверенность ML-фильтра
                    final_result = ml_result
                    confidence = ml_score
                    explanation = f"Приоритет ML (высокая уверенность): {ml_score:.3f} vs улучшенный: {improved_score:.3f}"
                else:
                    # В случае неопределенности, используем комбинированный балл
                    final_result = combined_score > 0.5
                    confidence = combined_score
                    explanation = f"Комбинированное решение: {combined_score:.3f} (улучшенный={improved_score:.3f}, ML={ml_score:.3f})"
            
            return final_result, confidence, explanation
            
        except Exception as e:
            logger.error(f"Ошибка в ML-фильтре: {e}")
            # Возвращаем результат улучшенного фильтра в случае ошибки
            return improved_result, improved_score, f"Ошибка ML, используем улучшенный: {improved_explanation}"
    
    def get_rejection_message(self) -> str:
        """Возвращает сообщение об отклонении неюридического вопроса."""
        return self.improved_filter.get_rejection_message()


# Глобальный экземпляр фильтра
_hybrid_filter_instance = None

def get_hybrid_question_filter() -> HybridQuestionFilter:
    """Возвращает глобальный экземпляр гибридного фильтра."""
    global _hybrid_filter_instance
    if _hybrid_filter_instance is None:
        _hybrid_filter_instance = HybridQuestionFilter()
    return _hybrid_filter_instance

def is_legal_question_hybrid(question: str) -> Tuple[bool, float, str]:
    """
    Определяет, является ли вопрос юридическим с использованием гибридного подхода.
    
    Args:
        question: Текст вопроса
        
    Returns:
        Кортеж (is_legal, confidence, explanation)
    """
    filter_instance = get_hybrid_question_filter()
    return filter_instance.is_legal_question(question)

def get_hybrid_rejection_message() -> str:
    """Возвращает сообщение об отклонении неюридического вопроса из гибридного фильтра."""
    filter_instance = get_hybrid_question_filter()
    return filter_instance.get_rejection_message() 