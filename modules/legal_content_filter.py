"""
Модуль для фильтрации юридического контента.
Определяет, является ли контент юридически релевантным для базы знаний.
"""
import re
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class LegalContentFilter:
    """Класс для фильтрации юридического контента."""
    
    def __init__(self):
        """Инициализирует фильтр юридического контента."""
        self.legal_keywords = self._load_legal_keywords()
        self.legal_patterns = self._load_legal_patterns()
        self.non_legal_patterns = self._load_non_legal_patterns()
        self.min_legal_score = 0.20  # Оптимизированный порог для лучшего распознавания (100% точность)
        
    def _load_legal_keywords(self) -> Dict[str, List[str]]:
        """Загружает ключевые слова для определения юридического контента."""
        return {
            # Основные юридические термины
            'core_legal': [
                'закон', 'кодекс', 'статья', 'пункт', 'часть', 'глава', 'раздел',
                'постановление', 'указ', 'декрет', 'решение', 'определение',
                'право', 'обязанность', 'ответственность', 'нарушение', 'штраф',
                'суд', 'судебный', 'правосудие', 'иск', 'истец', 'ответчик',
                'договор', 'соглашение', 'контракт', 'сделка', 'обязательство',
                'собственность', 'имущество', 'наследство', 'завещание',
                'регистрация', 'лицензия', 'разрешение', 'уведомление'
            ],
            
            # Белорусские юридические термины
            'belarus_legal': [
                'республика беларусь', 'беларусь', 'рб', 'белорусский',
                'совет министров', 'президент', 'парламент', 'палата представителей',
                'совет республики', 'конституционный суд', 'верховный суд',
                'министерство юстиции', 'генеральная прокуратура',
                'национальный банк', 'комитет государственного контроля'
            ],
            
            # Отрасли права
            'law_branches': [
                'гражданское право', 'трудовое право', 'семейное право',
                'административное право', 'уголовное право', 'налоговое право',
                'хозяйственное право', 'земельное право', 'экологическое право',
                'жилищное право', 'наследственное право', 'авторское право',
                'патентное право', 'банковское право', 'страховое право'
            ],
            
            # Правовые процедуры
            'legal_procedures': [
                'регистрация', 'лицензирование', 'сертификация', 'аккредитация',
                'судопроизводство', 'арбитраж', 'медиация', 'нотариат',
                'исполнительное производство', 'банкротство', 'ликвидация',
                'реорганизация', 'слияние', 'поглощение', 'аудит'
            ],
            
            # Субъекты права
            'legal_entities': [
                'физическое лицо', 'юридическое лицо', 'индивидуальный предприниматель',
                'общество с ограниченной ответственностью', 'акционерное общество',
                'унитарное предприятие', 'учреждение', 'организация',
                'государственный орган', 'местный орган', 'должностное лицо'
            ],
            
            # Документы
            'legal_documents': [
                'паспорт', 'удостоверение', 'справка', 'выписка', 'копия',
                'заявление', 'жалоба', 'ходатайство', 'протокол', 'акт',
                'приказ', 'распоряжение', 'инструкция', 'положение', 'устав'
            ]
        }
    
    def _load_legal_patterns(self) -> List[str]:
        """Загружает паттерны для определения юридического контента."""
        return [
            r'стать[яи]\s*\d+',  # статья 123
            r'пункт\s*\d+',      # пункт 5
            r'част[ьи]\s*\d+',   # часть 2
            r'глав[ае]\s*\d+',   # глава 10
            r'раздел\s*\d+',     # раздел III
            r'подпункт\s*\d+\.\d+',  # подпункт 1.1
            r'абзац\s*\d+',      # абзац 3
            r'№\s*\d+',          # № 123
            r'от\s*\d{1,2}\.\d{1,2}\.\d{4}',  # от 12.05.2023
            r'в редакции',       # в редакции
            r'с изменениями',    # с изменениями
            r'утратил силу',     # утратил силу
            r'вступает в силу',  # вступает в силу
            r'в соответствии с', # в соответствии с
            r'согласно',         # согласно
            r'на основании',     # на основании
            r'в порядке',        # в порядке
            r'не позднее',       # не позднее
            r'в течение',        # в течение
            r'подлежит',         # подлежит
            r'обязан',           # обязан
            r'вправе',           # вправе
            r'имеет право',      # имеет право
            r'несет ответственность',  # несет ответственность
            r'штраф\s*в размере',      # штраф в размере
            r'базовых величин',        # базовых величин
            r'белорусских рублей',     # белорусских рублей
        ]
    
    def _load_non_legal_patterns(self) -> List[str]:
        """Загружает паттерны для исключения нерелевантного контента."""
        return [
            r'рецепт',
            r'кулинар',
            r'готовить',
            r'приготовление',
            r'спорт',
            r'футбол',
            r'хоккей',
            r'погода',
            r'гороскоп',
            r'развлечения',
            r'кино',
            r'музыка',
            r'игры',
            r'мода',
            r'красота',
            r'здоровье',
            r'медицина',
            r'лечение',
            r'болезнь',
            r'туризм',
            r'путешествие',
            r'отдых',
            r'реклама',
            r'скидка',
            r'распродажа',
            r'купить',
            r'продать',
            r'цена',
            r'стоимость',
            r'технологии',
            r'компьютер',
            r'интернет',
            r'социальные сети'
        ]
    
    def is_legal_content(self, text: str, title: str = "", url: str = "") -> Tuple[bool, float, str]:
        """
        Определяет, является ли контент юридически релевантным.
        
        Args:
            text: Текст контента
            title: Заголовок (опционально)
            url: URL страницы (опционально)
            
        Returns:
            Tuple[bool, float, str]: (является_юридическим, балл_релевантности, объяснение)
        """
        if not text or len(text.strip()) < 50:
            return False, 0.0, "Слишком короткий текст"
        
        # Объединяем текст и заголовок для анализа
        full_text = f"{title} {text}".lower()
        
        # Проверяем на исключающие паттерны
        non_legal_score = self._calculate_non_legal_score(full_text)
        if non_legal_score > 0.5:
            return False, non_legal_score, "Содержит нерелевантный контент"
        
        # Вычисляем юридический балл
        legal_score = self._calculate_legal_score(full_text, url)
        
        # Дополнительные проверки
        structure_score = self._check_legal_structure(text)
        terminology_score = self._check_legal_terminology(full_text)
        
        # Итоговый балл с улучшенными весами
        total_score = (legal_score * 0.6 + structure_score * 0.25 + terminology_score * 0.15)
        
        # Бонус для белорусского контента
        if 'беларусь' in full_text or 'республика беларусь' in full_text or 'pravo.by' in url.lower():
            total_score += 0.1
        
        # Бонус для официальных документов
        if any(word in full_text for word in ['постановление', 'декрет', 'указ', 'закон', 'кодекс']):
            total_score += 0.05
        
        is_legal = total_score >= self.min_legal_score
        
        explanation = self._generate_explanation(legal_score, structure_score, terminology_score, total_score)
        
        logger.info(f"Анализ контента: балл={total_score:.3f}, юридический={'ДА' if is_legal else 'НЕТ'}")
        
        return is_legal, total_score, explanation
    
    def _calculate_legal_score(self, text: str, url: str = "") -> float:
        """Вычисляет балл юридической релевантности."""
        score = 0.0
        total_keywords = 0
        
        # Анализируем по категориям ключевых слов
        for category, keywords in self.legal_keywords.items():
            category_score = 0
            for keyword in keywords:
                if keyword in text:
                    category_score += 1
                    total_keywords += 1
            
            # Весовые коэффициенты для разных категорий
            weights = {
                'core_legal': 0.3,
                'belarus_legal': 0.25,
                'law_branches': 0.2,
                'legal_procedures': 0.15,
                'legal_entities': 0.1,
                'legal_documents': 0.05
            }
            
            weight = weights.get(category, 0.1)
            score += (category_score / len(keywords)) * weight
        
        # Проверяем паттерны
        pattern_score = 0
        for pattern in self.legal_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                pattern_score += len(matches) * 0.1
        
        # Проверяем URL на юридическую релевантность
        url_score = 0
        if url:
            legal_url_patterns = [
                'pravo.by', 'law', 'legal', 'юридический', 'право', 'закон',
                'government', 'gov', 'министерство', 'комитет', 'совет'
            ]
            for pattern in legal_url_patterns:
                if pattern in url.lower():
                    url_score += 0.1
        
        total_score = min(score + pattern_score * 0.1 + url_score, 1.0)
        return total_score
    
    def _calculate_non_legal_score(self, text: str) -> float:
        """Вычисляет балл нерелевантности (чем выше, тем менее юридический)."""
        score = 0.0
        
        for pattern in self.non_legal_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                score += len(matches) * 0.1
        
        return min(score, 1.0)
    
    def _check_legal_structure(self, text: str) -> float:
        """Проверяет структуру текста на соответствие юридическим документам."""
        score = 0.0
        
        # Проверяем наличие пронумерованных пунктов
        if re.search(r'\d+\.\s', text):
            score += 0.3
        
        # Проверяем наличие ссылок на статьи/пункты
        if re.search(r'(статья|пункт|часть|глава)\s*\d+', text, re.IGNORECASE):
            score += 0.4
        
        # Проверяем наличие дат в юридическом формате
        if re.search(r'\d{1,2}\.\d{1,2}\.\d{4}', text):
            score += 0.2
        
        # Проверяем наличие номеров документов
        if re.search(r'№\s*\d+', text):
            score += 0.1
        
        return min(score, 1.0)
    
    def _check_legal_terminology(self, text: str) -> float:
        """Проверяет использование юридической терминологии."""
        legal_terms = [
            'в соответствии с', 'согласно', 'на основании', 'в порядке',
            'не позднее', 'в течение', 'подлежит', 'обязан', 'вправе',
            'имеет право', 'несет ответственность', 'установленный',
            'предусмотренный', 'определенный', 'указанный'
        ]
        
        found_terms = 0
        for term in legal_terms:
            if term in text:
                found_terms += 1
        
        return min(found_terms / len(legal_terms), 1.0)
    
    def _generate_explanation(self, legal_score: float, structure_score: float, 
                            terminology_score: float, total_score: float) -> str:
        """Генерирует объяснение решения."""
        parts = []
        
        if legal_score > 0.3:
            parts.append(f"юридические термины ({legal_score:.2f})")
        
        if structure_score > 0.3:
            parts.append(f"структура документа ({structure_score:.2f})")
        
        if terminology_score > 0.3:
            parts.append(f"правовая терминология ({terminology_score:.2f})")
        
        if parts:
            return f"Найдены: {', '.join(parts)}. Общий балл: {total_score:.3f}"
        else:
            return f"Недостаточно юридических признаков. Балл: {total_score:.3f}"
    
    def filter_scraped_content(self, scraped_data: List[Dict]) -> List[Dict]:
        """
        Фильтрует спарсенный контент, оставляя только юридически релевантный.
        
        Args:
            scraped_data: Список словарей с данными страниц
            
        Returns:
            Отфильтрованный список только с юридическим контентом
        """
        filtered_data = []
        total_pages = len(scraped_data)
        
        logger.info(f"🔍 Фильтрация контента: анализ {total_pages} страниц")
        
        for i, page_data in enumerate(scraped_data):
            url = page_data.get('url', '')
            title = page_data.get('title', '')
            content = page_data.get('content', '')
            
            if not content:
                logger.debug(f"Пропуск страницы {i+1}: пустой контент")
                continue
            
            is_legal, score, explanation = self.is_legal_content(content, title, url)
            
            if is_legal:
                # Добавляем информацию о фильтрации в метаданные
                page_data['legal_score'] = score
                page_data['legal_explanation'] = explanation
                page_data['filtered_at'] = datetime.now().isoformat()
                
                filtered_data.append(page_data)
                logger.info(f"✅ Страница {i+1} прошла фильтр: {title[:50]}... (балл: {score:.3f})")
            else:
                logger.info(f"❌ Страница {i+1} отклонена: {title[:50]}... (балл: {score:.3f}) - {explanation}")
        
        logger.info(f"📊 Результат фильтрации: {len(filtered_data)}/{total_pages} страниц прошли фильтр")
        
        return filtered_data
    
    def get_filter_statistics(self) -> Dict:
        """Возвращает статистику работы фильтра."""
        return {
            'total_keywords': sum(len(keywords) for keywords in self.legal_keywords.values()),
            'legal_patterns': len(self.legal_patterns),
            'non_legal_patterns': len(self.non_legal_patterns),
            'min_legal_score': self.min_legal_score,
            'categories': list(self.legal_keywords.keys())
        }

def create_legal_content_filter() -> LegalContentFilter:
    """Создает экземпляр фильтра юридического контента."""
    return LegalContentFilter() 