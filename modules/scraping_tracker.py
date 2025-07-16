"""
Модуль для отслеживания информации о парсинге сайтов
"""
import json
import os
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Путь к файлу с информацией о парсинге
SCRAPING_INFO_FILE = "scraping_info.json"

class ScrapingTracker:
    """Класс для отслеживания информации о парсинге"""
    
    def __init__(self, info_file: str = SCRAPING_INFO_FILE):
        self.info_file = info_file
        self.info = self._load_info()
    
    def _load_info(self) -> Dict:
        """Загружает информацию о парсинге из файла"""
        try:
            if os.path.exists(self.info_file):
                with open(self.info_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    "last_scraping_date": None,
                    "last_scraped_sites": [],
                    "total_pages_scraped": 0,
                    "total_chunks_added": 0,
                    "scraping_history": []
                }
        except Exception as e:
            logger.error(f"Ошибка загрузки информации о парсинге: {e}")
            return {
                "last_scraping_date": None,
                "last_scraped_sites": [],
                "total_pages_scraped": 0,
                "total_chunks_added": 0,
                "scraping_history": []
            }
    
    def _save_info(self):
        """Сохраняет информацию о парсинге в файл"""
        try:
            with open(self.info_file, 'w', encoding='utf-8') as f:
                json.dump(self.info, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения информации о парсинге: {e}")
    
    def update_scraping_info(self, site_url: str, pages_scraped: int, chunks_added: int):
        """
        Обновляет информацию о парсинге
        
        Args:
            site_url: URL сайта, который парсился
            pages_scraped: Количество спарсенных страниц
            chunks_added: Количество добавленных чанков
        """
        try:
            current_date = datetime.now().strftime("%d.%m.%Y")
            current_time = datetime.now().strftime("%H:%M")
            
            # Извлекаем домен из URL
            from urllib.parse import urlparse
            domain = urlparse(site_url).netloc
            
            # Обновляем основную информацию
            self.info["last_scraping_date"] = current_date
            self.info["last_scraping_time"] = current_time
            
            # Добавляем сайт в список, если его там нет
            if domain not in self.info["last_scraped_sites"]:
                self.info["last_scraped_sites"].append(domain)
            
            # Обновляем статистику
            self.info["total_pages_scraped"] = self.info.get("total_pages_scraped", 0) + pages_scraped
            self.info["total_chunks_added"] = self.info.get("total_chunks_added", 0) + chunks_added
            
            # Добавляем в историю
            history_entry = {
                "date": current_date,
                "time": current_time,
                "site": domain,
                "pages_scraped": pages_scraped,
                "chunks_added": chunks_added
            }
            
            if "scraping_history" not in self.info:
                self.info["scraping_history"] = []
            
            self.info["scraping_history"].append(history_entry)
            
            # Оставляем только последние 10 записей в истории
            if len(self.info["scraping_history"]) > 10:
                self.info["scraping_history"] = self.info["scraping_history"][-10:]
            
            # Сохраняем
            self._save_info()
            
            logger.info(f"Обновлена информация о парсинге: {domain} ({pages_scraped} страниц, {chunks_added} чанков)")
            
        except Exception as e:
            logger.error(f"Ошибка обновления информации о парсинге: {e}")
    
    def get_last_scraping_info(self) -> Dict:
        """
        Возвращает информацию о последнем парсинге
        
        Returns:
            Словарь с информацией о последнем парсинге
        """
        return {
            "date": self.info.get("last_scraping_date"),
            "time": self.info.get("last_scraping_time"),
            "sites": self.info.get("last_scraped_sites", []),
            "total_pages": self.info.get("total_pages_scraped", 0),
            "total_chunks": self.info.get("total_chunks_added", 0)
        }
    
    def get_scraping_summary(self) -> str:
        """
        Возвращает краткую сводку о парсинге для системного промпта
        
        Returns:
            Строка с информацией о парсинге
        """
        info = self.get_last_scraping_info()
        
        if not info["date"]:
            return "дата не определена (парсинг не выполнялся)"
        
        # Формируем список сайтов
        sites = info["sites"]
        if not sites:
            site_info = "источник не определён"
        elif len(sites) == 1:
            site_info = f"источник: {sites[0]}"
        else:
            site_info = f"источники: {', '.join(sites[:3])}"
            if len(sites) > 3:
                site_info += f" и ещё {len(sites) - 3}"
        
        return f"{info['date']} ({site_info})"

# Глобальный экземпляр трекера
_tracker = None

def get_scraping_tracker() -> ScrapingTracker:
    """Возвращает глобальный экземпляр трекера парсинга"""
    global _tracker
    if _tracker is None:
        _tracker = ScrapingTracker()
    return _tracker

def update_scraping_info(site_url: str, pages_scraped: int, chunks_added: int):
    """Обновляет информацию о парсинге"""
    tracker = get_scraping_tracker()
    tracker.update_scraping_info(site_url, pages_scraped, chunks_added)

def get_scraping_summary() -> str:
    """Возвращает краткую сводку о парсинге"""
    tracker = get_scraping_tracker()
    return tracker.get_scraping_summary() 