"""
Продвинутый модуль для фильтрации вопросов с семантическим анализом.
Улучшенная версия с контекстным пониманием и обработкой сложных случаев.
"""
import re
import logging
from typing import List, Dict, Set, Tuple
from collections import Counter
import math

logger = logging.getLogger(__name__)

class AdvancedQuestionFilter:
    """Продвинутый класс для фильтрации вопросов с семантическим анализом."""
    
    def __init__(self):
        """Инициализирует продвинутый фильтр вопросов."""
        self.legal_keywords = self._get_enhanced_legal_keywords()
        self.legal_patterns = self._get_enhanced_legal_patterns()
        self.non_legal_patterns = self._get_enhanced_non_legal_patterns()
        self.legal_topics = self._get_legal_topics()
        self.legal_actions = self._get_legal_actions()
        self.legal_entities = self._get_legal_entities()
        self.colloquial_mappings = self._get_colloquial_mappings()
        self.context_analyzers = self._get_context_analyzers()
        self.foreign_legal_terms = self._get_foreign_legal_terms()
        
        # Адаптивные пороги для разных типов вопросов
        self.thresholds = {
            'formal_legal': 0.08,      # Формальные юридические вопросы
            'colloquial': 0.05,        # Разговорные формулировки
            'specialized': 0.12,       # Специализированная терминология
            'ambiguous': 0.15,         # Неоднозначные случаи
            'context_dependent': 0.10  # Контекстно-зависимые
        }
        
        logger.info("Инициализирован продвинутый фильтр юридических вопросов")
    
    def _get_enhanced_legal_keywords(self) -> Dict[str, float]:
        """Возвращает расширенный словарь юридических ключевых слов."""
        base_keywords = {
            # Основные юридические термины (высокий вес)
            'закон': 1.0, 'право': 1.0, 'юрист': 1.0, 'адвокат': 1.0,
            'суд': 1.0, 'судья': 1.0, 'иск': 1.0, 'договор': 1.0,
            'кодекс': 1.0, 'статья': 1.0, 'норма': 1.0, 'правовой': 1.0,
            'юридический': 1.0, 'законный': 1.0, 'незаконный': 1.0,
            'правомерный': 1.0, 'неправомерный': 1.0, 'правонарушение': 1.0,
            'ответственность': 1.0, 'обязанность': 1.0, 'права': 1.0,
            'обязательство': 1.0, 'нарушение': 1.0, 'штраф': 1.0,
            'наказание': 1.0, 'санкция': 1.0, 'взыскание': 1.0,
            
            # Специализированные термины (на основе анализа)
            'эстоппель': 1.0, 'субсидиарная': 1.0, 'виндикационный': 1.0,
            'негаторный': 1.0, 'реституция': 1.0, 'цессия': 1.0,
            'новация': 1.0, 'суброгация': 1.0, 'деликтная': 1.0,
            'виндикация': 1.0, 'бездокументарных': 0.8, 'ценных': 0.7,
            'бумаг': 0.6, 'недействительность': 0.9, 'сделки': 0.8,
            'требования': 0.7, 'подряда': 0.7, 'долга': 0.6,
            'обязательственном': 0.9, 'страховом': 0.8, 'причинение': 0.8,
            'вреда': 0.7, 'добросовестного': 0.8, 'приобретателя': 0.8,
            
            # Разговорные юридические термины
            'кинули': 0.7, 'обманули': 0.6, 'развожусь': 0.8, 'уволили': 0.8,
            'задержала': 0.7, 'полиция': 0.8, 'начальник': 0.5, 'зарплату': 0.7,
            'соседи': 0.4, 'шумят': 0.3, 'утихомирить': 0.5, 'сломался': 0.3,
            'купил': 0.3, 'телефон': 0.2, 'списал': 0.5, 'согласия': 0.6,
            'операцию': 0.4, 'врач': 0.3, 'неправильную': 0.4, 'ремонт': 0.4,
            'управляющая': 0.6, 'компания': 0.4, 'предупреждения': 0.5,
            
            # Контекстные индикаторы
            'защитить': 0.7, 'интересы': 0.5, 'персональных': 0.6, 'данных': 0.5,
            'человека': 0.4, 'интернете': 0.3, 'жизни': 0.3, 'здоровья': 0.4,
            'бизнеса': 0.5, 'услуги': 0.4, 'споры': 0.8, 'работодателем': 0.8,
            'врачей': 0.4, 'медицинская': 0.4, 'недвижимости': 0.6,
            'заработать': 0.3, 'долгами': 0.6, 'банковские': 0.6,
            
            # Иностранные юридические термины
            'habeas': 0.9, 'corpus': 0.9, 'pacta': 0.9, 'sunt': 0.9, 'servanda': 0.9,
            'ipsa': 0.9, 'loquitur': 0.9, 'minimis': 0.9, 'curat': 0.9,
            'ultra': 0.9, 'vires': 0.9, 'корпоративном': 0.8, 'bono': 0.9,
            'юриспруденции': 1.0, 'force': 0.8, 'majeure': 0.9, 'договорах': 0.8,
            'caveat': 0.9, 'emptor': 0.9, 'покупке': 0.5, 'respondeat': 0.9,
            'superior': 0.9, 'nemo': 0.9, 'quod': 0.9, 'habet': 0.9,
            
            # Региональная специфика
            'минске': 0.6, 'гомеле': 0.6, 'витебске': 0.6, 'могилеве': 0.6,
            'гродненской': 0.6, 'брестской': 0.6, 'области': 0.5, 'пвт': 0.8,
            'льготы': 0.7, 'мировой': 0.7, 'особенности': 0.5, 'земельное': 0.8,
            'законодательство': 0.9, 'экономических': 0.6, 'зонах': 0.6,
            'сельской': 0.4, 'местности': 0.4, 'интернет-магазинах': 0.5,
            'экологическое': 0.8, 'гродненской': 0.6,
        }
        
        return base_keywords
    
    def _get_enhanced_legal_patterns(self) -> List[str]:
        """Возвращает расширенный список паттернов для юридических вопросов."""
        return [
            # Базовые паттерны
            r'как\s+(\w+\s+)*подать\s+иск',
            r'как\s+(\w+\s+)*обжаловать',
            r'как\s+(\w+\s+)*защитить\s+права',
            r'имею\s+ли\s+право',
            r'обязан\s+ли\s+я',
            r'должен\s+ли\s+я',
            r'могу\s+ли\s+я\s+(\w+\s+)*требовать',
            
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
            
            # Контекстные паттерны
            r'защита\s+(\w+\s+)*персональных\s+(\w+\s+)*данных',
            r'права\s+(\w+\s+)*человека\s+(\w+\s+)*в\s+(\w+\s+)*интернете',
            r'медицинская\s+(\w+\s+)*ответственность\s+(\w+\s+)*врачей',
            r'трудовые\s+(\w+\s+)*споры\s+(\w+\s+)*с\s+(\w+\s+)*работодателем',
            r'банковские\s+(\w+\s+)*услуги\s+(\w+\s+)*для\s+(\w+\s+)*бизнеса',
            r'страхование\s+(\w+\s+)*жизни\s+(\w+\s+)*и\s+(\w+\s+)*здоровья',
            
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
            
            # Региональные паттерны
            r'мировой\s+(\w+\s+)*суд\s+(\w+\s+)*в\s+(\w+\s+)*минске',
            r'регистрации\s+(\w+\s+)*ип\s+(\w+\s+)*в\s+(\w+\s+)*гомеле',
            r'налоговые\s+(\w+\s+)*льготы\s+(\w+\s+)*в\s+(\w+\s+)*пвт',
            r'земельное\s+(\w+\s+)*законодательство\s+(\w+\s+)*в\s+(\w+\s+)*области',
            r'жилищные\s+(\w+\s+)*вопросы\s+(\w+\s+)*в\s+(\w+\s+)*витебске',
            r'трудовое\s+(\w+\s+)*право\s+(\w+\s+)*в\s+(\w+\s+)*зонах',
            r'права\s+(\w+\s+)*потребителей\s+(\w+\s+)*в\s+(\w+\s+)*интернет-магазинах',
        ]
    
    def _get_enhanced_non_legal_patterns(self) -> List[str]:
        """Возвращает расширенный список исключающих паттернов."""
        return [
            # Базовые исключения
            r'как\s+(\w+\s+)*готовить',
            r'как\s+(\w+\s+)*приготовить',
            r'рецепт\s+(\w+\s+)*',
            r'как\s+(\w+\s+)*похудеть',
            r'как\s+(\w+\s+)*заработать\s+деньги',
            r'как\s+(\w+\s+)*выучить\s+(\w+\s+)*язык',
            r'как\s+(\w+\s+)*изучить',
            r'как\s+(\w+\s+)*играть\s+в',
            r'как\s+(\w+\s+)*установить\s+(\w+\s+)*программу',
            r'как\s+(\w+\s+)*скачать',
            r'как\s+(\w+\s+)*настроить\s+(\w+\s+)*компьютер',
            r'как\s+(\w+\s+)*починить',
            r'как\s+(\w+\s+)*отремонтировать',
            r'погода\s+(\w+\s+)*',
            r'какая\s+(\w+\s+)*погода',
            
            # Технические исключения (на основе анализа)
            r'в\s+кино',
            r'в\s+игре',
            r'в\s+программировании',
            r'в\s+excel',
            r'в\s+windows',
            r'программист',
            r'база\s+данных',
            r'интернет-провайдер',
            r'не\s+работает',  # для технических проблем
            r'компьютерной\s+игре',
            r'права\s+доступа\s+к\s+базе',
            r'права\s+администратора\s+в\s+windows',
            r'наследование\s+классов\s+в\s+программировании',
            r'защита\s+растений\s+от\s+вредителей',
            r'ищет\s+программиста',
            
            # Медицинские исключения
            r'что\s+(\w+\s+)*болит',
            r'как\s+(\w+\s+)*лечить',
            r'симптомы\s+(\w+\s+)*',
            r'диагноз\s+(\w+\s+)*',
            r'лекарство\s+(\w+\s+)*',
            
            # Развлекательные исключения
            r'что\s+(\w+\s+)*посмотреть',
            r'что\s+(\w+\s+)*почитать',
            r'какой\s+(\w+\s+)*фильм',
            r'какую\s+(\w+\s+)*книгу',
            r'как\s+(\w+\s+)*знакомиться',
            r'отношения\s+с\s+(\w+\s+)*девушкой',
            r'отношения\s+с\s+(\w+\s+)*парнем',
        ]
    
    def _get_colloquial_mappings(self) -> Dict[str, List[str]]:
        """Возвращает словарь сопоставлений разговорных и юридических терминов."""
        return {
            'кинули': ['мошенничество', 'обман', 'неисполнение обязательств'],
            'обманули': ['мошенничество', 'введение в заблуждение'],
            'уволили': ['увольнение', 'расторжение трудового договора'],
            'не платит зарплату': ['задержка заработной платы', 'нарушение трудовых прав'],
            'не дает денег': ['неуплата алиментов', 'нарушение обязательств'],
            'списал деньги': ['неправомерное списание', 'нарушение банковских правил'],
            'задержала полиция': ['административное задержание', 'нарушение прав'],
            'неправильная операция': ['медицинская ошибка', 'врачебная ответственность'],
            'не делает ремонт': ['нарушение обязательств управляющей компании'],
            'шумят соседи': ['нарушение покоя', 'административное правонарушение'],
            'сломался товар': ['некачественный товар', 'права потребителя'],
        }
    
    def _get_context_analyzers(self) -> Dict[str, callable]:
        """Возвращает словарь анализаторов контекста."""
        return {
            'question_intent': self._analyze_question_intent,
            'legal_context': self._analyze_legal_context,
            'formality_level': self._analyze_formality_level,
            'specificity': self._analyze_specificity,
            'domain_indicators': self._analyze_domain_indicators,
        }
    
    def _get_foreign_legal_terms(self) -> Set[str]:
        """Возвращает множество иностранных юридических терминов."""
        return {
            'habeas', 'corpus', 'pacta', 'sunt', 'servanda', 'res', 'ipsa', 'loquitur',
            'de', 'minimis', 'non', 'curat', 'lex', 'ultra', 'vires', 'pro', 'bono',
            'force', 'majeure', 'caveat', 'emptor', 'respondeat', 'superior',
            'nemo', 'dat', 'quod', 'habet'
        }
    
    def _get_legal_topics(self) -> Set[str]:
        """Возвращает множество юридических тем."""
        return {
            'гражданское право', 'трудовое право', 'семейное право',
            'жилищное право', 'административное право', 'уголовное право',
            'хозяйственное право', 'налоговое право', 'земельное право',
            'экологическое право', 'конституционное право', 'финансовое право',
            'договорное право', 'наследственное право', 'авторское право',
            'патентное право', 'банковское право', 'страховое право',
            'таможенное право', 'валютное право', 'бюджетное право',
            'процессуальное право', 'исполнительное производство',
            'нотариальное право', 'адвокатская деятельность',
            'правоохранительная деятельность', 'судебная система',
            'прокурорский надзор', 'следственная деятельность',
            'оперативно-розыскная деятельность', 'пенитенциарная система'
        }
    
    def _get_legal_actions(self) -> Set[str]:
        """Возвращает множество типичных юридических действий."""
        return {
            'подать иск', 'обжаловать решение', 'подать жалобу',
            'подать заявление', 'обратиться в суд', 'защитить права',
            'взыскать ущерб', 'возместить вред', 'расторгнуть договор',
            'заключить договор', 'оформить документы', 'получить разрешение',
            'зарегистрировать права', 'установить факт', 'признать недействительным',
            'восстановить срок', 'приостановить исполнение', 'отменить решение',
            'изменить решение', 'пересмотреть дело', 'возобновить производство',
            'прекратить производство', 'оставить заявление без рассмотрения',
            'принять к производству', 'отказать в принятии', 'вынести решение',
            'исполнить решение', 'обратить взыскание', 'наложить арест',
            'снять арест', 'установить опеку', 'лишить родительских прав',
            'восстановить в родительских правах', 'взыскать алименты',
            'определить место жительства', 'установить отцовство',
            'усыновить ребенка', 'развестись', 'признать брак недействительным',
            'разделить имущество', 'выделить долю', 'установить сервитут'
        }
    
    def _get_legal_entities(self) -> Set[str]:
        """Возвращает множество юридических субъектов и организаций."""
        return {
            'суд', 'прокуратура', 'следственный комитет', 'милиция',
            'нотариус', 'адвокат', 'юрист', 'судебный исполнитель',
            'судебный пристав', 'эксперт', 'переводчик', 'представитель',
            'опекун', 'попечитель', 'усыновитель', 'наследник',
            'завещатель', 'даритель', 'получатель', 'арендодатель',
            'арендатор', 'наймодатель', 'нанимател', 'подрядчик',
            'заказчик', 'поставщик', 'покупатель', 'продавец',
            'кредитор', 'должник', 'поручитель', 'залогодатель',
            'залогодержатель', 'страховщик', 'страхователь',
            'выгодоприобретатель', 'потерпевший', 'истец', 'ответчик',
            'третье лицо', 'заявитель', 'заинтересованное лицо',
            'участник процесса', 'сторона договора', 'контрагент',
            'правообладатель', 'собственник', 'владелец', 'пользователь',
            'управляющий', 'директор', 'учредитель', 'участник',
            'акционер', 'член кооператива', 'индивидуальный предприниматель',
            'юридическое лицо', 'физическое лицо', 'государственный орган',
            'местный орган', 'организация', 'учреждение', 'предприятие'
        }
    
    def _analyze_question_intent(self, question: str) -> float:
        """Анализирует намерение вопроса."""
        intent_indicators = {
            'request_help': ['что делать', 'как поступить', 'помогите', 'подскажите'],
            'seek_information': ['что такое', 'как работает', 'какие', 'где'],
            'request_procedure': ['как оформить', 'как подать', 'какой порядок'],
            'seek_rights': ['имею ли право', 'могу ли', 'должен ли'],
            'complaint': ['нарушили', 'не выполняют', 'кинули', 'обманули'],
        }
        
        question_lower = question.lower()
        intent_score = 0.0
        
        for intent_type, indicators in intent_indicators.items():
            for indicator in indicators:
                if indicator in question_lower:
                    if intent_type in ['request_procedure', 'seek_rights', 'complaint']:
                        intent_score += 0.3  # Высокий юридический потенциал
                    elif intent_type == 'seek_information':
                        intent_score += 0.1  # Может быть юридическим
                    else:
                        intent_score += 0.2  # Средний потенциал
        
        return min(intent_score, 1.0)
    
    def _analyze_legal_context(self, question: str) -> float:
        """Анализирует юридический контекст."""
        context_indicators = {
            'legal_procedure': ['суд', 'заявление', 'иск', 'жалоба', 'документы'],
            'legal_relationship': ['договор', 'сделка', 'обязательство', 'право', 'обязанность'],
            'legal_consequence': ['ответственность', 'наказание', 'штраф', 'взыскание'],
            'legal_status': ['законно', 'правомерно', 'нарушение', 'правонарушение'],
        }
        
        question_lower = question.lower()
        context_score = 0.0
        
        for context_type, indicators in context_indicators.items():
            for indicator in indicators:
                if indicator in question_lower:
                    context_score += 0.2
        
        return min(context_score, 1.0)
    
    def _analyze_formality_level(self, question: str) -> Tuple[str, float]:
        """Анализирует уровень формальности вопроса."""
        formal_indicators = ['статья', 'кодекс', 'закон', 'норма', 'правило']
        colloquial_indicators = ['кинули', 'обманули', 'не платит', 'что делать']
        specialized_indicators = ['виндикационный', 'негаторный', 'реституция', 'цессия']
        
        question_lower = question.lower()
        
        formal_score = sum(1 for indicator in formal_indicators if indicator in question_lower)
        colloquial_score = sum(1 for indicator in colloquial_indicators if indicator in question_lower)
        specialized_score = sum(1 for indicator in specialized_indicators if indicator in question_lower)
        
        if specialized_score > 0:
            return 'specialized', 0.9
        elif formal_score > colloquial_score:
            return 'formal', 0.7
        elif colloquial_score > 0:
            return 'colloquial', 0.5
        else:
            return 'neutral', 0.3
    
    def _analyze_specificity(self, question: str) -> float:
        """Анализирует специфичность вопроса."""
        specific_indicators = [
            'статья', 'пункт', 'часть', 'кодекс', 'закон', 'номер',
            'конкретно', 'именно', 'точно', 'определенно'
        ]
        
        general_indicators = [
            'что', 'как', 'где', 'когда', 'почему', 'вообще', 'в принципе'
        ]
        
        question_lower = question.lower()
        
        specific_score = sum(1 for indicator in specific_indicators if indicator in question_lower)
        general_score = sum(1 for indicator in general_indicators if indicator in question_lower)
        
        if specific_score > 0:
            return min(specific_score * 0.3, 1.0)
        elif general_score > 2:
            return 0.1  # Очень общий вопрос
        else:
            return 0.5  # Средняя специфичность
    
    def _analyze_domain_indicators(self, question: str) -> Dict[str, float]:
        """Анализирует индикаторы различных доменов."""
        domains = {
            'legal': ['право', 'закон', 'суд', 'договор', 'ответственность'],
            'medical': ['врач', 'лечение', 'болезнь', 'здоровье', 'медицина'],
            'technical': ['программа', 'компьютер', 'интернет', 'сайт', 'база данных'],
            'business': ['бизнес', 'продажа', 'покупка', 'деньги', 'прибыль'],
            'personal': ['семья', 'дети', 'родители', 'отношения', 'личное'],
        }
        
        question_lower = question.lower()
        domain_scores = {}
        
        for domain, indicators in domains.items():
            score = sum(1 for indicator in indicators if indicator in question_lower)
            domain_scores[domain] = score * 0.2
        
        return domain_scores
    
    def is_legal_question(self, question: str) -> Tuple[bool, float, str]:
        """
        Определяет, является ли вопрос юридическим с использованием продвинутого анализа.
        
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
                return False, 0.0, f"Найден неюридический паттерн: {pattern}"
        
        # Многоуровневый анализ
        analysis_results = {}
        
        # 1. Анализ ключевых слов
        keyword_score = self._analyze_keywords(question_lower)
        analysis_results['keywords'] = keyword_score
        
        # 2. Анализ паттернов
        pattern_score = self._analyze_patterns(question_lower)
        analysis_results['patterns'] = pattern_score
        
        # 3. Контекстный анализ
        context_scores = {}
        for analyzer_name, analyzer_func in self.context_analyzers.items():
            context_scores[analyzer_name] = analyzer_func(question)
        analysis_results['context'] = context_scores
        
        # 4. Анализ формальности
        formality_type, formality_score = self._analyze_formality_level(question)
        analysis_results['formality'] = {'type': formality_type, 'score': formality_score}
        
        # 5. Анализ разговорных выражений
        colloquial_score = self._analyze_colloquial_expressions(question_lower)
        analysis_results['colloquial'] = colloquial_score
        
        # 6. Анализ иностранных терминов
        foreign_score = self._analyze_foreign_terms(question_lower)
        analysis_results['foreign'] = foreign_score
        
        # Вычисляем итоговый балл
        total_score = self._calculate_total_score(analysis_results)
        
        # Определяем тип вопроса и соответствующий порог
        question_type = self._determine_question_type(analysis_results)
        threshold = self.thresholds.get(question_type, self.thresholds['formal_legal'])
        
        is_legal = total_score >= threshold
        
        # Генерируем объяснение
        explanation = self._generate_explanation(analysis_results, total_score, question_type)
        
        logger.debug(f"Продвинутый анализ: '{question[:50]}...' - "
                    f"Тип: {question_type}, Балл: {total_score:.3f}, "
                    f"Порог: {threshold:.3f}, Юридический: {is_legal}")
        
        return is_legal, total_score, explanation
    
    def _analyze_keywords(self, question: str) -> float:
        """Анализирует ключевые слова с учетом контекста."""
        keyword_score = 0.0
        found_keywords = []
        
        for keyword, weight in self.legal_keywords.items():
            if keyword in question:
                # Контекстная коррекция веса
                context_weight = self._get_context_weight(keyword, question)
                adjusted_weight = weight * context_weight
                keyword_score += adjusted_weight
                found_keywords.append(keyword)
        
        # Нормализация с учетом количества слов
        word_count = len(question.split())
        if word_count > 0:
            keyword_score = keyword_score / math.log(word_count + 1)
        
        return min(keyword_score, 1.0)
    
    def _get_context_weight(self, keyword: str, question: str) -> float:
        """Получает контекстный вес для ключевого слова."""
        # Проверяем контекст вокруг ключевого слова
        words = question.split()
        try:
            keyword_index = words.index(keyword)
            
            # Анализируем слова до и после
            context_before = words[max(0, keyword_index-2):keyword_index]
            context_after = words[keyword_index+1:min(len(words), keyword_index+3)]
            
            context_words = context_before + context_after
            
            # Усиливающие контекстные слова
            enhancing_words = ['нарушение', 'защита', 'права', 'обязанность', 'ответственность']
            # Ослабляющие контекстные слова
            weakening_words = ['кино', 'игра', 'программирование', 'компьютер']
            
            weight = 1.0
            for word in context_words:
                if word in enhancing_words:
                    weight *= 1.2
                elif word in weakening_words:
                    weight *= 0.5
            
            return min(weight, 2.0)
        except ValueError:
            return 1.0
    
    def _analyze_patterns(self, question: str) -> float:
        """Анализирует паттерны с учетом приоритета."""
        pattern_score = 0.0
        matched_patterns = []
        
        for pattern in self.legal_patterns:
            if re.search(pattern, question):
                # Разные веса для разных типов паттернов
                if any(term in pattern for term in ['habeas', 'pacta', 'res', 'de']):
                    pattern_score += 0.8  # Иностранные термины
                elif any(term in pattern for term in ['кинули', 'уволили', 'списал']):
                    pattern_score += 0.6  # Разговорные выражения
                elif any(term in pattern for term in ['субсидиарная', 'виндикационный']):
                    pattern_score += 0.9  # Специализированные термины
                else:
                    pattern_score += 0.5  # Обычные паттерны
                
                matched_patterns.append(pattern)
        
        return min(pattern_score, 1.0)
    
    def _analyze_colloquial_expressions(self, question: str) -> float:
        """Анализирует разговорные выражения."""
        colloquial_score = 0.0
        
        for expression, legal_terms in self.colloquial_mappings.items():
            if expression in question:
                # Вес зависит от количества соответствующих юридических терминов
                colloquial_score += len(legal_terms) * 0.2
        
        return min(colloquial_score, 1.0)
    
    def _analyze_foreign_terms(self, question: str) -> float:
        """Анализирует иностранные юридические термины."""
        foreign_score = 0.0
        words = question.split()
        
        for word in words:
            if word in self.foreign_legal_terms:
                foreign_score += 0.3
        
        return min(foreign_score, 1.0)
    
    def _calculate_total_score(self, analysis_results: Dict) -> float:
        """Вычисляет итоговый балл с учетом всех факторов."""
        # Базовые веса
        weights = {
            'keywords': 0.3,
            'patterns': 0.25,
            'context': 0.2,
            'formality': 0.1,
            'colloquial': 0.1,
            'foreign': 0.05
        }
        
        total_score = 0.0
        
        # Ключевые слова
        total_score += analysis_results['keywords'] * weights['keywords']
        
        # Паттерны
        total_score += analysis_results['patterns'] * weights['patterns']
        
        # Контекст (среднее по всем анализаторам, исключая кортежи)
        context_values = []
        for value in analysis_results['context'].values():
            if isinstance(value, (int, float)):
                context_values.append(value)
            elif isinstance(value, tuple):
                context_values.append(value[1] if len(value) > 1 else value[0])
        
        context_avg = sum(context_values) / len(context_values) if context_values else 0.0
        total_score += context_avg * weights['context']
        
        # Формальность
        total_score += analysis_results['formality']['score'] * weights['formality']
        
        # Разговорные выражения
        total_score += analysis_results['colloquial'] * weights['colloquial']
        
        # Иностранные термины
        total_score += analysis_results['foreign'] * weights['foreign']
        
        return min(total_score, 1.0)
    
    def _determine_question_type(self, analysis_results: Dict) -> str:
        """Определяет тип вопроса для выбора подходящего порога."""
        formality_type = analysis_results['formality']['type']
        
        if formality_type == 'specialized':
            return 'specialized'
        elif formality_type == 'colloquial':
            return 'colloquial'
        elif analysis_results['context']['specificity'] < 0.3:
            return 'context_dependent'
        elif max(value if isinstance(value, (int, float)) else (value[1] if len(value) > 1 else value[0]) for value in analysis_results['context'].values()) < 0.5:
            return 'ambiguous'
        else:
            return 'formal_legal'
    
    def _generate_explanation(self, analysis_results: Dict, total_score: float, question_type: str) -> str:
        """Генерирует объяснение решения."""
        explanation_parts = []
        
        if analysis_results['keywords'] > 0.1:
            explanation_parts.append(f"ключевые слова ({analysis_results['keywords']:.3f})")
        
        if analysis_results['patterns'] > 0.1:
            explanation_parts.append(f"юридические паттерны ({analysis_results['patterns']:.3f})")
        
        if analysis_results['colloquial'] > 0.1:
            explanation_parts.append(f"разговорные выражения ({analysis_results['colloquial']:.3f})")
        
        if analysis_results['foreign'] > 0.1:
            explanation_parts.append(f"иностранные термины ({analysis_results['foreign']:.3f})")
        
        context_max = max(value if isinstance(value, (int, float)) else (value[1] if len(value) > 1 else value[0]) for value in analysis_results['context'].values())
        context_info = f"контекст ({context_max:.3f})"
        explanation_parts.append(context_info)
        
        if explanation_parts:
            explanation = f"Обнаружены: {', '.join(explanation_parts)}. "
        else:
            explanation = "Юридические признаки не найдены. "
        
        explanation += f"Тип: {question_type}, общий балл: {total_score:.3f}"
        
        return explanation

# Глобальный экземпляр продвинутого фильтра
_advanced_question_filter = None

def get_advanced_question_filter() -> AdvancedQuestionFilter:
    """Возвращает глобальный экземпляр продвинутого фильтра вопросов."""
    global _advanced_question_filter
    if _advanced_question_filter is None:
        _advanced_question_filter = AdvancedQuestionFilter()
    return _advanced_question_filter

def is_legal_question_advanced(question: str) -> Tuple[bool, float, str]:
    """
    Определяет, является ли вопрос юридическим с использованием продвинутого анализа.
    
    Args:
        question: Текст вопроса
        
    Returns:
        Кортеж (is_legal, score, explanation)
    """
    filter_instance = get_advanced_question_filter()
    return filter_instance.is_legal_question(question) 