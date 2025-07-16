"""
Модуль для инкрементального парсинга сайтов - парсит только новую/измененную информацию
"""
import json
import os
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Tuple
import logging
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

from .web_scraper import WebScraper
from .scraping_tracker import ScrapingTracker

logger = logging.getLogger(__name__)

# Файл для хранения информации о страницах
PAGES_INFO_FILE = "pages_info.json"

class IncrementalScraper:
    """Класс для инкрементального парсинга сайтов"""
    
    def __init__(self, web_scraper: WebScraper, scraping_tracker: ScrapingTracker):
        self.web_scraper = web_scraper
        self.scraping_tracker = scraping_tracker
        self.pages_info_file = PAGES_INFO_FILE
        self.pages_info = self._load_pages_info()
        
        # Настройки для определения изменений
        self.check_interval_hours = 24  # Проверять изменения каждые 24 часа
        self.content_hash_threshold = 0.1  # Минимальный процент изменений для обновления
        
    def _load_pages_info(self) -> Dict:
        """Загружает информацию о страницах из файла"""
        try:
            if os.path.exists(self.pages_info_file):
                with open(self.pages_info_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    "pages": {},  # URL -> {hash, last_check, last_modified, title, chunks_count}
                    "site_maps": {},  # domain -> {urls, last_scan}
                    "last_full_scan": None
                }
        except Exception as e:
            logger.error(f"Ошибка загрузки информации о страницах: {e}")
            return {"pages": {}, "site_maps": {}, "last_full_scan": None}
    
    def _save_pages_info(self):
        """Сохраняет информацию о страницах в файл"""
        try:
            with open(self.pages_info_file, 'w', encoding='utf-8') as f:
                json.dump(self.pages_info, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения информации о страницах: {e}")
    
    def _get_content_hash(self, content: str) -> str:
        """Вычисляет хэш контента страницы"""
        # Нормализуем контент перед хэшированием
        normalized = content.lower().strip()
        normalized = ' '.join(normalized.split())  # Убираем лишние пробелы
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()
    
    def _get_page_info(self, url: str) -> Optional[Dict]:
        """Получает информацию о странице без полного парсинга"""
        try:
            response = self.web_scraper.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Получаем заголовок
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "Без заголовка"
            
            # Получаем дату последнего изменения из мета-тегов или headers
            last_modified = None
            
            # Пробуем получить из HTTP заголовков
            if 'last-modified' in response.headers:
                last_modified = response.headers['last-modified']
            
            # Пробуем получить из мета-тегов
            if not last_modified:
                meta_modified = soup.find('meta', {'name': 'last-modified'}) or \
                              soup.find('meta', {'property': 'article:modified_time'})
                if meta_modified:
                    last_modified = meta_modified.get('content')
            
            # Получаем основной контент для хэширования
            content = self._extract_main_content(soup)
            content_hash = self._get_content_hash(content)
            
            return {
                'title': title_text,
                'content_hash': content_hash,
                'last_modified': last_modified,
                'content_length': len(content),
                'check_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о странице {url}: {e}")
            return None
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Извлекает основной контент страницы"""
        # Удаляем ненужные элементы
        for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()
        
        # Ищем основной контент
        main_content_selectors = [
            'main', 'article', '.content', '.main-content', 
            '.post-content', '.entry-content', '#content', '#main'
        ]
        
        content = ""
        for selector in main_content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content = content_elem.get_text(separator=' ', strip=True)
                break
        
        # Если не нашли основной контент, берем весь body
        if not content:
            body = soup.find('body')
            if body:
                content = body.get_text(separator=' ', strip=True)
        
        return content
    
    def _discover_site_urls(self, start_url: str, max_pages: int = 100) -> List[str]:
        """Обнаруживает все URL сайта для парсинга"""
        try:
            domain = urlparse(start_url).netloc
            
            # Проверяем, есть ли уже карта сайта
            if domain in self.pages_info["site_maps"]:
                site_map = self.pages_info["site_maps"][domain]
                # Если карта свежая (менее 7 дней), используем её
                if site_map.get("last_scan"):
                    last_scan = datetime.fromisoformat(site_map["last_scan"])
                    if datetime.now() - last_scan < timedelta(days=7):
                        logger.info(f"Используем существующую карту сайта для {domain}")
                        return site_map.get("urls", [])
            
            logger.info(f"Сканируем сайт {domain} для обнаружения страниц...")
            
            urls_found = set()
            urls_to_check = [start_url]
            checked_urls = set()
            
            while urls_to_check and len(urls_found) < max_pages:
                current_url = urls_to_check.pop(0)
                
                if current_url in checked_urls:
                    continue
                
                checked_urls.add(current_url)
                
                try:
                    response = self.web_scraper.session.get(current_url, timeout=10)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Добавляем текущий URL
                    urls_found.add(current_url)
                    
                    # Ищем новые ссылки
                    new_links = self.web_scraper.get_legal_links(soup, current_url)
                    for link in new_links:
                        if link not in checked_urls and len(urls_found) < max_pages:
                            urls_to_check.append(link)
                    
                    time.sleep(self.web_scraper.delay)
                    
                except Exception as e:
                    logger.error(f"Ошибка при сканировании {current_url}: {e}")
                    continue
            
            urls_list = list(urls_found)
            
            # Сохраняем карту сайта
            self.pages_info["site_maps"][domain] = {
                "urls": urls_list,
                "last_scan": datetime.now().isoformat(),
                "total_urls": len(urls_list)
            }
            self._save_pages_info()
            
            logger.info(f"Обнаружено {len(urls_list)} URL для {domain}")
            return urls_list
            
        except Exception as e:
            logger.error(f"Ошибка обнаружения URL сайта: {e}")
            return [start_url]
    
    def check_for_changes(self, urls: List[str]) -> Tuple[List[str], List[str], List[str]]:
        """
        Проверяет изменения на страницах
        
        Args:
            urls: Список URL для проверки
            
        Returns:
            Tuple[новые_страницы, измененные_страницы, удаленные_страницы]
        """
        new_pages = []
        changed_pages = []
        deleted_pages = []
        
        logger.info(f"Проверяем изменения на {len(urls)} страницах...")
        
        # Проверяем существующие страницы
        for url in urls:
            if url not in self.pages_info["pages"]:
                new_pages.append(url)
                continue
            
            page_info = self.pages_info["pages"][url]
            
            # Проверяем, нужно ли проверять страницу
            if page_info.get("last_check"):
                last_check = datetime.fromisoformat(page_info["last_check"])
                if datetime.now() - last_check < timedelta(hours=self.check_interval_hours):
                    continue
            
            # Получаем текущую информацию о странице
            current_info = self._get_page_info(url)
            if not current_info:
                deleted_pages.append(url)
                continue
            
            # Сравниваем хэши
            old_hash = page_info.get("content_hash")
            new_hash = current_info["content_hash"]
            
            if old_hash != new_hash:
                changed_pages.append(url)
                logger.info(f"Обнаружены изменения на странице: {url}")
            
            # Обновляем информацию о проверке
            self.pages_info["pages"][url].update({
                "last_check": current_info["check_time"],
                "content_hash": new_hash,
                "title": current_info["title"]
            })
        
        # Проверяем удаленные страницы
        existing_urls = set(urls)
        for url in list(self.pages_info["pages"].keys()):
            if url not in existing_urls:
                deleted_pages.append(url)
        
        self._save_pages_info()
        
        logger.info(f"Найдено: {len(new_pages)} новых, {len(changed_pages)} измененных, {len(deleted_pages)} удаленных страниц")
        
        return new_pages, changed_pages, deleted_pages
    
    def incremental_scrape(self, start_url: str, max_pages: int = 100) -> Dict:
        """
        Выполняет инкрементальный парсинг сайта
        
        Args:
            start_url: Начальный URL
            max_pages: Максимальное количество страниц для обнаружения
            
        Returns:
            Словарь с результатами парсинга
        """
        logger.info(f"Начинаем инкрементальный парсинг: {start_url}")
        
        # Обнаруживаем все URL сайта
        all_urls = self._discover_site_urls(start_url, max_pages)
        
        # Проверяем изменения
        new_pages, changed_pages, deleted_pages = self.check_for_changes(all_urls)
        
        # Парсим новые и измененные страницы
        pages_to_scrape = new_pages + changed_pages
        
        if not pages_to_scrape:
            logger.info("Новых или измененных страниц не найдено")
            return {
                "total_urls_checked": len(all_urls),
                "new_pages": 0,
                "changed_pages": 0,
                "deleted_pages": len(deleted_pages),
                "pages_scraped": 0,
                "chunks_added": 0
            }
        
        logger.info(f"Парсим {len(pages_to_scrape)} страниц...")
        
        # Парсим страницы
        scraped_data = []
        for url in pages_to_scrape:
            page_data = self.web_scraper.scrape_single_page(url)
            if page_data:
                scraped_data.append(page_data)
                
                # Обновляем информацию о странице
                content_hash = self._get_content_hash(page_data["content"])
                self.pages_info["pages"][url] = {
                    "content_hash": content_hash,
                    "title": page_data["title"],
                    "last_check": datetime.now().isoformat(),
                    "last_scraped": datetime.now().isoformat(),
                    "content_length": len(page_data["content"])
                }
            
            time.sleep(self.web_scraper.delay)
        
        # Удаляем информацию об удаленных страницах
        for url in deleted_pages:
            if url in self.pages_info["pages"]:
                del self.pages_info["pages"][url]
        
        # Добавляем в базу знаний
        chunks_added = 0
        if scraped_data:
            chunks_added = self.web_scraper.add_to_knowledge_base(scraped_data)
        
        # Обновляем информацию о парсинге
        self.scraping_tracker.update_scraping_info(
            start_url, 
            len(scraped_data), 
            chunks_added
        )
        
        # Сохраняем информацию о страницах
        self._save_pages_info()
        
        result = {
            "total_urls_checked": len(all_urls),
            "new_pages": len(new_pages),
            "changed_pages": len(changed_pages),
            "deleted_pages": len(deleted_pages),
            "pages_scraped": len(scraped_data),
            "chunks_added": chunks_added,
            "scraped_urls": [data["url"] for data in scraped_data]
        }
        
        logger.info(f"Инкрементальный парсинг завершен: {result}")
        return result
    
    def force_full_rescan(self, start_url: str, max_pages: int = 100) -> Dict:
        """
        Принудительно выполняет полный пересканирование сайта
        
        Args:
            start_url: Начальный URL
            max_pages: Максимальное количество страниц
            
        Returns:
            Словарь с результатами парсинга
        """
        logger.info(f"Выполняем полное пересканирование: {start_url}")
        
        # Очищаем информацию о сайте
        domain = urlparse(start_url).netloc
        if domain in self.pages_info["site_maps"]:
            del self.pages_info["site_maps"][domain]
        
        # Очищаем информацию о страницах этого домена
        urls_to_remove = [url for url in self.pages_info["pages"].keys() 
                         if urlparse(url).netloc == domain]
        for url in urls_to_remove:
            del self.pages_info["pages"][url]
        
        # Выполняем полный парсинг
        return self.incremental_scrape(start_url, max_pages)
    
    def get_scraping_statistics(self) -> Dict:
        """Возвращает статистику парсинга"""
        total_pages = len(self.pages_info["pages"])
        
        # Группируем по доменам
        domains = {}
        for url in self.pages_info["pages"].keys():
            domain = urlparse(url).netloc
            if domain not in domains:
                domains[domain] = 0
            domains[domain] += 1
        
        return {
            "total_pages_tracked": total_pages,
            "domains": domains,
            "site_maps": {domain: info["total_urls"] 
                         for domain, info in self.pages_info["site_maps"].items()},
            "last_full_scan": self.pages_info.get("last_full_scan")
        }


def create_incremental_scraper(web_scraper: WebScraper, scraping_tracker: ScrapingTracker) -> IncrementalScraper:
    """Создает экземпляр инкрементального скрапера"""
    return IncrementalScraper(web_scraper, scraping_tracker) 