"""
Модуль для динамического поиска информации на pravo.by
когда нет ответа в базе знаний
"""
import requests
from bs4 import BeautifulSoup
import re
import logging
from urllib.parse import urljoin, quote
from typing import List, Dict, Optional, Tuple
import time
from datetime import datetime

from .web_scraper import WebScraper
from .knowledge_base import KnowledgeBase
from .text_processing import TextProcessor
from .scraping_tracker import ScrapingTracker
from .legal_content_filter import create_legal_content_filter

logger = logging.getLogger(__name__)

class DynamicSearcher:
    """Класс для динамического поиска информации на pravo.by"""
    
    def __init__(self, web_scraper: WebScraper, knowledge_base: KnowledgeBase, 
                 text_processor: TextProcessor, scraping_tracker: ScrapingTracker):
        self.web_scraper = web_scraper
        self.knowledge_base = knowledge_base
        self.text_processor = text_processor
        self.scraping_tracker = scraping_tracker
        self.legal_filter = create_legal_content_filter()
        
        # Настройки поиска
        self.search_base_url = "https://pravo.by"
        self.search_endpoints = [
            "/search/",  # Основной поиск
            "/pravovaya-informatsiya/",  # Правовая информация
            "/natsionalnyy-reestr/",  # Национальный реестр
        ]
        
        # Максимальное количество результатов для обработки
        self.max_search_results = 5
        self.max_pages_per_result = 3
        
    def _generate_search_queries(self, user_question: str) -> List[str]:
        """
        Генерирует поисковые запросы на основе вопроса пользователя
        
        Args:
            user_question: Вопрос пользователя
            
        Returns:
            Список поисковых запросов
        """
        queries = []
        
        # Основной запрос
        queries.append(user_question)
        
        # Извлекаем ключевые слова
        keywords = self._extract_keywords(user_question)
        
        # Создаем запросы из ключевых слов
        if len(keywords) > 1:
            queries.append(" ".join(keywords[:3]))  # Первые 3 ключевых слова
            
        # Добавляем специфичные для РБ термины
        rb_specific_terms = [
            "республика беларусь", "беларусь", "рб", "белорусский",
            "закон", "кодекс", "постановление", "указ", "декрет"
        ]
        
        for term in rb_specific_terms:
            if term in user_question.lower():
                # Создаем запрос с этим термином
                term_query = f"{term} {' '.join(keywords[:2])}"
                if term_query not in queries:
                    queries.append(term_query)
                break
        
        return queries[:3]  # Ограничиваем количество запросов
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Извлекает ключевые слова из текста
        
        Args:
            text: Текст для анализа
            
        Returns:
            Список ключевых слов
        """
        # Удаляем стоп-слова
        stop_words = {
            'как', 'что', 'где', 'когда', 'почему', 'зачем', 'кто', 'какой', 'какая', 'какие',
            'в', 'на', 'с', 'по', 'для', 'от', 'до', 'при', 'за', 'под', 'над', 'между',
            'и', 'или', 'но', 'а', 'да', 'нет', 'не', 'ни', 'же', 'ли', 'бы', 'то',
            'это', 'этот', 'эта', 'эти', 'тот', 'та', 'те', 'мой', 'моя', 'мои',
            'его', 'её', 'их', 'наш', 'наша', 'наши', 'ваш', 'ваша', 'ваши'
        }
        
        # Разбиваем на слова и очищаем
        words = re.findall(r'\b[а-яё]+\b', text.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return keywords[:10]  # Ограничиваем количество ключевых слов
    
    def _search_pravo_by(self, query: str) -> List[str]:
        """
        Выполняет поиск на pravo.by
        
        Args:
            query: Поисковый запрос
            
        Returns:
            Список URL найденных страниц
        """
        found_urls = []
        
        try:
            # Кодируем запрос для URL
            encoded_query = quote(query)
            
            # Пробуем разные способы поиска
            search_urls = [
                f"{self.search_base_url}/search/?q={encoded_query}",
                f"{self.search_base_url}/pravovaya-informatsiya/?search={encoded_query}",
            ]
            
            for search_url in search_urls:
                try:
                    logger.info(f"Поиск по URL: {search_url}")
                    
                    response = self.web_scraper.session.get(search_url, timeout=10)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Ищем ссылки на результаты поиска
                    result_links = self._extract_search_results(soup, query)
                    
                    for link in result_links:
                        full_url = urljoin(self.search_base_url, link)
                        if full_url not in found_urls:
                            found_urls.append(full_url)
                    
                    time.sleep(1)  # Задержка между запросами
                    
                except Exception as e:
                    logger.error(f"Ошибка поиска по {search_url}: {e}")
                    continue
            
            # Если не нашли через поиск, пробуем найти релевантные страницы
            if not found_urls:
                found_urls = self._find_relevant_pages(query)
            
            return found_urls[:self.max_search_results]
            
        except Exception as e:
            logger.error(f"Ошибка при поиске на pravo.by: {e}")
            return []
    
    def _extract_search_results(self, soup: BeautifulSoup, query: str) -> List[str]:
        """
        Извлекает ссылки из результатов поиска
        
        Args:
            soup: BeautifulSoup объект страницы
            query: Поисковый запрос
            
        Returns:
            Список URL
        """
        links = []
        
        # Различные селекторы для результатов поиска
        search_selectors = [
            'a[href*="/novosti/"]',
            'a[href*="/pravovaya-informatsiya/"]',
            'a[href*="/natsionalnyy-reestr/"]',
            'a[href*="/gosudarstvo-i-pravo/"]',
            '.search-result a',
            '.result-item a',
            '.content-item a'
        ]
        
        query_words = query.lower().split()
        
        for selector in search_selectors:
            elements = soup.select(selector)
            for element in elements:
                href = element.get('href')
                text = element.get_text().lower()
                
                # Проверяем релевантность по ключевым словам
                if href and any(word in text for word in query_words):
                    links.append(href)
        
        return list(set(links))  # Убираем дубликаты
    
    def _find_relevant_pages(self, query: str) -> List[str]:
        """
        Находит релевантные страницы на основе ключевых слов
        
        Args:
            query: Поисковый запрос
            
        Returns:
            Список URL
        """
        relevant_urls = []
        
        try:
            # Определяем тематические разделы на основе ключевых слов
            topic_mappings = {
                'трудовой': '/pravovaya-informatsiya/trudovoe-pravo/',
                'гражданский': '/pravovaya-informatsiya/grazhdanskoe-pravo/',
                'семейный': '/pravovaya-informatsiya/semeynoe-pravo/',
                'административный': '/pravovaya-informatsiya/administrativnoe-pravo/',
                'уголовный': '/pravovaya-informatsiya/ugolovnoe-pravo/',
                'хозяйственный': '/pravovaya-informatsiya/khozyaystvennoe-pravo/',
                'налоговый': '/pravovaya-informatsiya/nalogovoe-pravo/',
                'земельный': '/pravovaya-informatsiya/zemelnoe-pravo/',
                'жилищный': '/pravovaya-informatsiya/zhilishchnoe-pravo/',
                'ип': '/pravovaya-informatsiya/individualnoe-predprinimatelstvo/',
                'ооо': '/pravovaya-informatsiya/obshchestva-ogranichennoj-otvetstvennostyu/',
                'регистрация': '/pravovaya-informatsiya/registratsiya/',
                'развод': '/pravovaya-informatsiya/semeynoe-pravo/',
                'увольнение': '/pravovaya-informatsiya/trudovoe-pravo/',
                'договор': '/pravovaya-informatsiya/dogovornoe-pravo/',
                'наследство': '/pravovaya-informatsiya/nasledstvennoe-pravo/',
                'алименты': '/pravovaya-informatsiya/semeynoe-pravo/',
                'штраф': '/pravovaya-informatsiya/administrativnoe-pravo/',
                'суд': '/pravovaya-informatsiya/sudebnaya-sistema/',
                'права': '/pravovaya-informatsiya/prava-grazhdan/',
                'обязанности': '/pravovaya-informatsiya/obyazannosti-grazhdan/'
            }
            
            query_lower = query.lower()
            
            # Ищем подходящие разделы
            for keyword, url_path in topic_mappings.items():
                if keyword in query_lower:
                    full_url = urljoin(self.search_base_url, url_path)
                    relevant_urls.append(full_url)
            
            # Если не нашли специфичные разделы, добавляем общие
            if not relevant_urls:
                general_urls = [
                    f"{self.search_base_url}/pravovaya-informatsiya/",
                    f"{self.search_base_url}/natsionalnyy-reestr/novye-postupleniya/",
                    f"{self.search_base_url}/novosti/analitika/"
                ]
                relevant_urls.extend(general_urls)
            
            return relevant_urls[:self.max_search_results]
            
        except Exception as e:
            logger.error(f"Ошибка поиска релевантных страниц: {e}")
            return []
    
    def _check_if_info_already_exists(self, user_question: str) -> bool:
        """
        Проверяет, есть ли уже информация по похожему запросу в базе знаний.
        
        Args:
            user_question: Вопрос пользователя
            
        Returns:
            True если информация уже есть, False если нужен динамический поиск
        """
        try:
            from .knowledge_base import search_relevant_docs
            
            # Ищем документы, добавленные через динамический поиск
            relevant_docs = search_relevant_docs(user_question, n_results=5)
            
            # Проверяем, есть ли среди них документы с pravo.by
            dynamic_docs = [
                doc for doc in relevant_docs 
                if doc.get('metadata', {}).get('source_type') == 'pravo.by_dynamic'
            ]
            
            if dynamic_docs:
                # Проверяем качество найденных динамических документов
                best_distance = min(doc['distance'] for doc in dynamic_docs)
                
                if best_distance < 0.6:  # Увеличили порог с 0.4 до 0.6 для более гибкого кеширования
                    logger.info(f"🔄 ДИНАМИЧЕСКИЙ ПОИСК: Найдена релевантная информация (дистанция: {best_distance:.3f}) - используем кеш")
                    return True
                else:
                    logger.info(f"🔄 ДИНАМИЧЕСКИЙ ПОИСК: Найдена информация, но качество недостаточное (дистанция: {best_distance:.3f}) - ищем заново")
                    return False
            
            logger.info(f"🔄 ДИНАМИЧЕСКИЙ ПОИСК: Информация по запросу не найдена в кеше - требуется поиск на pravo.by")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка проверки кеша динамического поиска: {e}")
            return False
    
    def search_and_add_to_knowledge_base(self, user_question: str) -> Tuple[Optional[str], bool]:
        """
        Ищет информацию на pravo.by и добавляет в базу знаний
        
        Args:
            user_question: Вопрос пользователя
            
        Returns:
            Tuple[найденная_информация, успешность_операции]
        """
        logger.info(f"🔍 ДИНАМИЧЕСКИЙ ПОИСК: Запрос - {user_question}")
        
        try:
            # Примечание: проверка кеша теперь происходит в bot_handler.py
            # Сразу ищем новую информацию на pravo.by
            logger.info(f"🌐 ДИНАМИЧЕСКИЙ ПОИСК: Ищем новую информацию на pravo.by")
            
            # Генерируем поисковые запросы
            search_queries = self._generate_search_queries(user_question)
            logger.info(f"🔍 ДИНАМИЧЕСКИЙ ПОИСК: Сгенерированы запросы: {search_queries}")
            
            all_found_urls = []
            
            # Выполняем поиск по каждому запросу
            for query in search_queries:
                found_urls = self._search_pravo_by(query)
                all_found_urls.extend(found_urls)
            
            # Убираем дубликаты
            unique_urls = list(set(all_found_urls))
            
            if not unique_urls:
                logger.info("🚫 ДИНАМИЧЕСКИЙ ПОИСК: Релевантные страницы не найдены на pravo.by")
                return None, False
            
            logger.info(f"🎯 ДИНАМИЧЕСКИЙ ПОИСК: Найдено {len(unique_urls)} релевантных страниц для парсинга")
            
            # Парсим найденные страницы
            scraped_data = []
            for url in unique_urls[:self.max_search_results]:
                try:
                    page_data = self.web_scraper.scrape_single_page(url)
                    if page_data and len(page_data['content']) > 200:  # Минимальная длина контента
                        scraped_data.append(page_data)
                        logger.info(f"📄 ДИНАМИЧЕСКИЙ ПОИСК: Успешно спарсена страница: {url}")
                    
                    time.sleep(1)  # Задержка между запросами
                    
                except Exception as e:
                    logger.error(f"Ошибка парсинга {url}: {e}")
                    continue
            
            if not scraped_data:
                logger.info("🚫 ДИНАМИЧЕСКИЙ ПОИСК: Не удалось спарсить релевантные страницы")
                return None, False
            
            # Фильтруем контент на юридическую релевантность
            logger.info(f"🔍 ДИНАМИЧЕСКИЙ ПОИСК: Фильтрация {len(scraped_data)} страниц на юридическую релевантность")
            filtered_data = self.legal_filter.filter_scraped_content(scraped_data)
            
            if not filtered_data:
                logger.info("🚫 ДИНАМИЧЕСКИЙ ПОИСК: Ни одна страница не прошла фильтр юридической релевантности")
                return None, False
            
            logger.info(f"✅ ДИНАМИЧЕСКИЙ ПОИСК: {len(filtered_data)} из {len(scraped_data)} страниц прошли фильтр")
            
            # Добавляем в базу знаний только отфильтрованный контент
            logger.info(f"💾 ДИНАМИЧЕСКИЙ ПОИСК: Добавляем {len(filtered_data)} отфильтрованных страниц в базу знаний")
            chunks_added = self.web_scraper.add_to_knowledge_base(filtered_data)
            
            if chunks_added > 0:
                # Обновляем информацию о парсинге
                self.scraping_tracker.update_scraping_info(
                    "https://pravo.by/", 
                    len(scraped_data), 
                    chunks_added
                )
                
                logger.info(f"✅ ДИНАМИЧЕСКИЙ ПОИСК: Добавлено {chunks_added} чанков в базу знаний")
                
                # Теперь пытаемся найти ответ в обновленной базе знаний
                from .knowledge_base import search_relevant_docs
                from .llm_service import get_answer
                
                relevant_docs = search_relevant_docs(user_question, n_results=5)
                
                if relevant_docs:
                    logger.info(f"🤖 ДИНАМИЧЕСКИЙ ПОИСК: Генерация ответа через OpenAI на основе новых данных из {len(scraped_data)} страниц")
                    answer = get_answer(user_question, relevant_docs)
                    
                    # Добавляем информацию об источнике
                    source_info = f"\n\n📍 Информация найдена и добавлена из {len(scraped_data)} страниц pravo.by"
                    answer += source_info
                    
                    logger.info(f"✅ ДИНАМИЧЕСКИЙ ПОИСК: Ответ успешно сгенерирован на основе новых данных")
                    return answer, True
                else:
                    logger.info(f"🚫 ДИНАМИЧЕСКИЙ ПОИСК: Не удалось найти релевантные документы даже после добавления новых данных")
                    return None, False
            else:
                logger.info("Не удалось добавить информацию в базу знаний")
                return None, False
                
        except Exception as e:
            logger.error(f"Ошибка динамического поиска: {e}")
            return None, False
    
    def get_search_statistics(self) -> Dict:
        """Возвращает статистику динамического поиска"""
        return {
            "search_base_url": self.search_base_url,
            "max_search_results": self.max_search_results,
            "max_pages_per_result": self.max_pages_per_result,
            "available_endpoints": self.search_endpoints
        }


def create_dynamic_searcher(web_scraper: WebScraper, knowledge_base: KnowledgeBase, 
                          text_processor: TextProcessor, scraping_tracker: ScrapingTracker) -> DynamicSearcher:
    """Создает экземпляр динамического поисковика"""
    return DynamicSearcher(web_scraper, knowledge_base, text_processor, scraping_tracker) 