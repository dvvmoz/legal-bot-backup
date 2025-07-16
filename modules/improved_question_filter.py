"""
Улучшенный модуль для фильтрации вопросов с лучшей обработкой пограничных случаев.
"""
import re
import logging
from typing import List, Dict, Tuple
from modules.question_filter import QuestionFilter

logger = logging.getLogger(__name__)

class ImprovedQuestionFilter(QuestionFilter):
    """Улучшенный класс для фильтрации вопросов с лучшей обработкой сложных случаев."""
    
    def __init__(self):
        """Инициализирует улучшенный фильтр вопросов."""
        super().__init__()
        
        # Дополнительные ключевые слова из анализа
        self.additional_keywords = {
            # Специализированные термины
            'эстоппель': 0.9, 'субсидиарная': 0.9, 'виндикационный': 0.9,
            'негаторный': 0.9, 'реституция': 0.9, 'цессия': 0.9,
            'новация': 0.9, 'суброгация': 0.9, 'деликтная': 0.9,
            'виндикация': 0.9, 'недействительность': 0.8, 'сделки': 0.7,
            'требования': 0.6, 'подряда': 0.6, 'обязательственном': 0.8,
            'причинение': 0.7, 'добросовестного': 0.7, 'приобретателя': 0.7,
            # Дополнительные профессиональные термины
            'преклюзия': 0.9, 'конвалидация': 0.9, 'аффилированный': 0.8,
            'бенефициарный': 0.8, 'индоссамент': 0.9, 'аваль': 0.9,
            'солидарный': 0.8, 'субсидиарный': 0.8, 'акцессорный': 0.8,
            'коллизионный': 0.9, 'диспозитивный': 0.8, 'императивный': 0.8,
            
            # Разговорные юридические термины
            'кинули': 0.8, 'обманули': 0.7, 'развожусь': 0.8, 'уволили': 0.8,
            'задержала': 0.7, 'начальник': 0.5, 'зарплату': 0.6, 'соседи': 0.4,
            'шумят': 0.3, 'утихомирить': 0.6, 'сломался': 0.3, 'купил': 0.3,
            'списал': 0.6, 'согласия': 0.7, 'операцию': 0.4, 'неправильную': 0.5,
            'ремонт': 0.4, 'управляющая': 0.6, 'предупреждения': 0.6,
            
            # Иностранные юридические термины
            'habeas': 0.9, 'corpus': 0.9, 'pacta': 0.9, 'sunt': 0.9, 'servanda': 0.9,
            'ipsa': 0.9, 'loquitur': 0.9, 'minimis': 0.9, 'curat': 0.9,
            'ultra': 0.9, 'vires': 0.9, 'bono': 0.9, 'юриспруденции': 0.9,
            'force': 0.8, 'majeure': 0.9, 'caveat': 0.9, 'emptor': 0.9,
            'respondeat': 0.9, 'superior': 0.9, 'nemo': 0.9, 'quod': 0.9, 'habet': 0.9,
            
            # Контекстные индикаторы
            'персональных': 0.6, 'данных': 0.5, 'человека': 0.4, 'интернете': 0.3,
            'споры': 0.8, 'работодателем': 0.8, 'медицинская': 0.5, 'врачей': 0.4,
            'банковские': 0.6, 'услуги': 0.4, 'бизнеса': 0.5, 'долгами': 0.7,
            'заработать': 0.3, 'недвижимости': 0.6, 'интересы': 0.5,
            
            # Региональная специфика
            'минске': 0.6, 'гомеле': 0.6, 'витебске': 0.6, 'могилеве': 0.6,
            'брестской': 0.6, 'гродненской': 0.6, 'области': 0.5, 'пвт': 0.8,
            'мировой': 0.7, 'особенности': 0.5, 'земельное': 0.8,
            'законодательство': 0.9, 'экономических': 0.6, 'зонах': 0.6,
            'сельской': 0.4, 'местности': 0.4, 'экологическое': 0.8,
        }
        
        # Дополнительные паттерны
        self.additional_patterns = [
            # Разговорные паттерны
            r'меня\s+(\w+\s+)*кинули',
            r'меня\s+(\w+\s+)*обманули',
            r'меня\s+(\w+\s+)*уволили',
            r'не\s+(\w+\s+)*платит\s+(\w+\s+)*зарплату',
            r'не\s+(\w+\s+)*дает\s+(\w+\s+)*денег',
            r'списал\s+(\w+\s+)*деньги\s+(\w+\s+)*без\s+(\w+\s+)*согласия',
            r'задержала\s+(\w+\s+)*без\s+(\w+\s+)*причины',
            r'сделал\s+(\w+\s+)*неправильную\s+(\w+\s+)*операцию',
            r'не\s+(\w+\s+)*делает\s+(\w+\s+)*ремонт',
            r'шумят\s+(\w+\s+)*по\s+(\w+\s+)*ночам',
            r'сломался\s+(\w+\s+)*через\s+(\w+\s+)*неделю',
            
            # Специализированные паттерны
            r'субсидиарная\s+(\w+\s+)*ответственность',
            r'виндикационный\s+(\w+\s+)*иск',
            r'негаторный\s+(\w+\s+)*иск',
            r'реституция\s+(\w+\s+)*при\s+(\w+\s+)*недействительности',
            r'цессия\s+(\w+\s+)*требования',
            r'новация\s+(\w+\s+)*долга',
            r'суброгация\s+(\w+\s+)*в\s+(\w+\s+)*страховом',
            r'деликтная\s+(\w+\s+)*ответственность',
            r'виндикация\s+(\w+\s+)*бездокументарных',
            
            # Иностранные термины
            r'habeas\s+corpus',
            r'pacta\s+sunt\s+servanda',
            r'res\s+ipsa\s+loquitur',
            r'de\s+minimis\s+non\s+curat\s+lex',
            r'ultra\s+vires',
            r'pro\s+bono',
            r'force\s+majeure',
            r'caveat\s+emptor',
            r'respondeat\s+superior',
            r'nemo\s+dat\s+quod\s+non\s+habet',
            
            # Контекстные паттерны
            r'защита\s+(\w+\s+)*персональных\s+(\w+\s+)*данных',
            r'права\s+(\w+\s+)*человека\s+(\w+\s+)*в\s+(\w+\s+)*интернете',
            r'медицинская\s+(\w+\s+)*ответственность\s+(\w+\s+)*врачей',
            r'трудовые\s+(\w+\s+)*споры\s+(\w+\s+)*с\s+(\w+\s+)*работодателем',
            r'банковские\s+(\w+\s+)*услуги\s+(\w+\s+)*для\s+(\w+\s+)*бизнеса',
            r'страхование\s+(\w+\s+)*жизни\s+(\w+\s+)*и\s+(\w+\s+)*здоровья',
        ]
        
        # Улучшенные исключающие паттерны
        self.improved_exclusions = [
            # Технические исключения
            r'в\s+кино',
            r'в\s+игре',
            r'в\s+программировании',
            r'в\s+excel',
            r'в\s+windows',
            r'программист',
            r'база\s+данных',
            r'интернет-провайдер',
            r'компьютерной\s+игре',
            r'права\s+доступа\s+к\s+базе',
            r'права\s+администратора\s+в\s+windows',
            r'наследование\s+классов\s+в\s+программировании',
            r'защита\s+растений\s+от\s+вредителей',
            r'ищет\s+программиста',
            r'не\s+работает',  # для технических проблем
            r'декларация\s+в\s+excel',
            r'стаж\s+в\s+компьютерной\s+игре',
        ]
        
        # Объединяем ключевые слова
        self.legal_keywords.update(self.additional_keywords)
        
        # Объединяем паттерны
        self.legal_patterns.extend(self.additional_patterns)
        
        # Объединяем исключения
        self.non_legal_patterns.extend(self.improved_exclusions)
        
        # Адаптивные пороги
        self.adaptive_threshold = 0.08  # Более низкий порог для лучшего распознавания
        
        logger.info("Инициализирован улучшенный фильтр юридических вопросов")
    
    def _analyze_colloquial_expressions(self, question: str) -> float:
        """Анализирует разговорные выражения с расширенным словарем."""
        colloquial_mappings = {
            'кинули': 0.8,
            'обманули': 0.7,
            'уволили': 0.8,
            'не платит зарплату': 0.9,
            'не дает денег': 0.7,
            'списал деньги': 0.8,
            'задержала полиция': 0.9,
            'неправильная операция': 0.6,
            'не делает ремонт': 0.6,
            'шумят соседи': 0.5,
            'сломался товар': 0.5,
            # Новые разговорные выражения
            'телефон сломался': 0.6,
            'товар бракованный': 0.6,
            'не возвращают деньги': 0.8,
            'полиция задержала': 0.9,
            'задержали без причины': 0.9,
            'врач ошибся': 0.7,
            'неправильно лечил': 0.7,
            'купил а он не работает': 0.6,
            'продали брак': 0.6,
            'не дают больничный': 0.8,
            'заставляют работать': 0.8,
            'не отпускают с работы': 0.8,
        }
        
        question_lower = question.lower()
        colloquial_score = 0.0
        
        for expression, weight in colloquial_mappings.items():
            if expression in question_lower:
                colloquial_score += weight
        
        return min(colloquial_score, 1.0)
    
    def _analyze_foreign_terms(self, question: str) -> float:
        """Анализирует иностранные юридические термины."""
        foreign_terms = {
            'habeas', 'corpus', 'pacta', 'sunt', 'servanda', 'res', 'ipsa', 'loquitur',
            'de', 'minimis', 'non', 'curat', 'lex', 'ultra', 'vires', 'pro', 'bono',
            'force', 'majeure', 'caveat', 'emptor', 'respondeat', 'superior',
            'nemo', 'dat', 'quod', 'habet'
        }
        
        words = question.lower().split()
        foreign_score = 0.0
        
        for word in words:
            if word in foreign_terms:
                foreign_score += 0.3
        
        return min(foreign_score, 1.0)
    
    def _analyze_context_indicators(self, question: str) -> float:
        """Анализирует контекстные индикаторы с улучшенным алгоритмом."""
        context_indicators = {
            'legal_action': ['подать', 'обжаловать', 'защитить', 'взыскать', 'оформить', 'зарегистрировать', 'получить'],
            'legal_subject': ['права', 'обязанности', 'ответственность', 'нарушение', 'требования'],
            'legal_process': ['суд', 'заявление', 'иск', 'жалоба', 'документы', 'процедура'],
            'legal_consequence': ['штраф', 'наказание', 'взыскание', 'возмещение', 'санкции'],
            'legal_entities': ['организация', 'учреждение', 'предприятие', 'ип', 'юрлицо'],
            'legal_domains': ['гражданский', 'трудовой', 'административный', 'семейный', 'жилищный']
        }
        
        # Специальные паттерны для повышения точности
        specific_patterns = {
            'inheritance_patterns': [
                r'наследство', r'наследование', r'завещание', r'наследник', r'наследодатель',
                r'принятие\s+наследства', r'отказ\s+от\s+наследства', r'наследственная\s+масса'
            ],
            'insurance_patterns': [
                r'страхование\s+(\w+\s+)*ответственности', r'страховка\s+(\w+\s+)*от\s+несчастных\s+случаев',
                r'обязательное\s+страхование', r'добровольное\s+страхование', r'страховой\s+случай'
            ],
            'rights_patterns': [
                r'права\s+(\w+\s+)*собственности', r'права\s+(\w+\s+)*потребителя',
                r'трудовые\s+права', r'конституционные\s+права', r'авторские\s+права'
            ]
        }
        
        question_lower = question.lower()
        context_score = 0.0
        
        # Базовый анализ контекстных индикаторов
        for category, indicators in context_indicators.items():
            for indicator in indicators:
                if indicator in question_lower:
                    context_score += 0.15
        
        # Анализ специальных паттернов
        for pattern_type, patterns in specific_patterns.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    context_score += 0.3
                    break  # Засчитываем только один паттерн из категории
        
        # Дополнительные бонусы для конкретных случаев
        if re.search(r'как\s+(\w+\s+)*оформить\s+(\w+\s+)*наследство', question_lower):
            context_score += 0.4  # Конкретный вопрос о наследстве
        
        if re.search(r'страхование\s+(\w+\s+)*жизни\s+(\w+\s+)*и\s+(\w+\s+)*здоровья', question_lower):
            context_score += 0.3  # Конкретный вид страхования
        
        if re.search(r'какие\s+(\w+\s+)*права\s+(\w+\s+)*у\s+(\w+\s+)*меня', question_lower):
            # Слишком общий вопрос - снижаем балл
            context_score -= 0.2
        
        return min(context_score, 1.0)
    
    def _calculate_base_legal_score(self, question_lower: str) -> float:
        """Вычисляет базовый юридический балл используя логику родительского класса."""
        total_score = 0.0
        
        # 1. Проверка ключевых слов
        keyword_score = 0.0
        for keyword, weight in self.legal_keywords.items():
            if keyword in question_lower:
                keyword_score += weight
        
        # 2. Проверка юридических паттернов
        pattern_score = 0.0
        for pattern in self.legal_patterns:
            if re.search(pattern, question_lower):
                pattern_score += 0.5
        
        # 3. Проверка юридических тем
        topic_score = 0.0
        for topic in self.legal_topics:
            if topic in question_lower:
                topic_score += 0.3
        
        # 4. Проверка юридических действий
        action_score = 0.0
        for action in self.legal_actions:
            if action in question_lower:
                action_score += 0.4
        
        # 5. Проверка юридических субъектов
        entity_score = 0.0
        for entity in self.legal_entities:
            if entity in question_lower:
                entity_score += 0.2
        
        # Суммируем все баллы
        total_score = keyword_score + pattern_score + topic_score + action_score + entity_score
        
        # Добавляем бонусы за специальные комбинации
        bonus_score = 0.0
        
        # Бонус за упоминание Беларуси + юридические термины
        if any(word in question_lower for word in ['беларусь', 'беларуси', 'рб', 'республика беларусь']):
            if any(word in question_lower for word in ['закон', 'право', 'суд', 'договор', 'кодекс']):
                bonus_score += 0.2
        
        # Бонус за вопросительные слова + юридические термины
        question_words = ['как', 'что', 'где', 'когда', 'какой', 'какая', 'какие', 'кто', 'почему']
        legal_terms = ['подать', 'оформить', 'получить', 'зарегистрировать', 'обжаловать', 'взыскать', 'защитить']
        
        if any(qw in question_lower for qw in question_words):
            if any(lt in question_lower for lt in legal_terms):
                bonus_score += 0.15
        
        # Бонус за упоминание документов + процедур
        if 'документ' in question_lower:
            if any(word in question_lower for word in ['нужны', 'требуются', 'оформить', 'подать', 'получить']):
                bonus_score += 0.1
        
        # Бонус за права + обязанности
        if any(word in question_lower for word in ['права', 'право', 'обязанности', 'обязанность']):
            if any(word in question_lower for word in ['имею', 'должен', 'обязан', 'могу', 'можно']):
                bonus_score += 0.1
        
        # Бонус за ответственность + нарушения
        if 'ответственность' in question_lower:
            if any(word in question_lower for word in ['какая', 'какую', 'несет', 'предусмотрена', 'за']):
                bonus_score += 0.1
        
        total_score += bonus_score
        
        # Нормализуем счет (максимум примерно 10-15 баллов)
        normalized_score = min(total_score / 8.0, 1.0)  # Уменьшаем делитель для повышения чувствительности
        
        return normalized_score

    def _get_adaptive_threshold(self, question: str, base_score: float, colloquial_score: float, 
                               foreign_score: float, context_score: float) -> float:
        """Определяет адаптивный порог в зависимости от типа вопроса."""
        question_lower = question.lower()
        
        # Для специализированных терминов - более низкий порог
        if foreign_score > 0.3 or any(term in question_lower for term in 
                                     ['эстоппель', 'субсидиарная', 'виндикационный', 'негаторный', 'реституция']):
            return 0.06
        
        # Для разговорных выражений - средний порог
        if colloquial_score > 0.5:
            return 0.07
        
        # Для контекстных вопросов - стандартный порог
        if context_score > 0.3:
            return 0.08
        
        # Для базовых юридических вопросов - обычный порог
        if base_score > 0.3:
            return 0.08
        
        # Для неоднозначных случаев - более высокий порог
        return 0.09

    def is_legal_question(self, question: str) -> Tuple[bool, float, str]:
        """
        Определяет, является ли вопрос юридическим с улучшенным анализом.
        
        Args:
            question: Текст вопроса
            
        Returns:
            Кортеж (is_legal, score, explanation)
        """
        if not question or not question.strip():
            return False, 0.0, "Пустой вопрос"
        
        question_lower = question.lower().strip()
        
        # Проверяем на явно неюридические паттерны
        for pattern in self.non_legal_patterns:
            if re.search(pattern, question_lower):
                return False, 0.0, f"Найден неюридический паттерн"
        
        # Базовый анализ
        base_score = self._calculate_base_legal_score(question_lower)
        
        # Дополнительные анализы
        colloquial_score = self._analyze_colloquial_expressions(question)
        foreign_score = self._analyze_foreign_terms(question)
        context_score = self._analyze_context_indicators(question)
        
        # Вычисляем итоговый балл
        total_score = (
            base_score * 0.5 +           # Базовый анализ
            colloquial_score * 0.25 +    # Разговорные выражения
            foreign_score * 0.15 +       # Иностранные термины
            context_score * 0.1          # Контекстные индикаторы
        )
        
        # Используем адаптивный порог
        adaptive_threshold = self._get_adaptive_threshold(question, base_score, colloquial_score, 
                                                         foreign_score, context_score)
        is_legal = total_score >= adaptive_threshold
        
        # Генерируем объяснение
        explanation_parts = []
        if base_score > 0.1:
            explanation_parts.append(f"базовый анализ ({base_score:.3f})")
        if colloquial_score > 0.1:
            explanation_parts.append(f"разговорные выражения ({colloquial_score:.3f})")
        if foreign_score > 0.1:
            explanation_parts.append(f"иностранные термины ({foreign_score:.3f})")
        if context_score > 0.1:
            explanation_parts.append(f"контекстные индикаторы ({context_score:.3f})")
        
        if explanation_parts:
            explanation = f"Обнаружены: {', '.join(explanation_parts)}"
        else:
            explanation = "Юридические признаки не найдены"
        
        logger.debug(f"Улучшенный анализ: '{question[:50]}...' - "
                    f"Балл: {total_score:.3f}, Порог: {adaptive_threshold:.3f}, "
                    f"Юридический: {is_legal}")
        
        return is_legal, total_score, explanation

# Глобальный экземпляр улучшенного фильтра
_improved_question_filter = None

def get_improved_question_filter() -> ImprovedQuestionFilter:
    """Возвращает глобальный экземпляр улучшенного фильтра вопросов."""
    global _improved_question_filter
    if _improved_question_filter is None:
        _improved_question_filter = ImprovedQuestionFilter()
    return _improved_question_filter

def is_legal_question_improved(question: str) -> Tuple[bool, float, str]:
    """
    Определяет, является ли вопрос юридическим с использованием улучшенного анализа.
    
    Args:
        question: Текст вопроса
        
    Returns:
        Кортеж (is_legal, score, explanation)
    """
    filter_instance = get_improved_question_filter()
    return filter_instance.is_legal_question(question) 

def get_rejection_message_improved() -> str:
    """Возвращает сообщение об отклонении неюридического вопроса из улучшенного фильтра."""
    filter_instance = get_improved_question_filter()
    return filter_instance.get_rejection_message() 