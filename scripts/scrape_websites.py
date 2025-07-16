#!/usr/bin/env python3
"""
Скрипт для скрапинга юридических сайтов и пополнения базы знаний
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Добавляем корневую директорию проекта в путь
sys.path.append(str(Path(__file__).parent.parent))

from modules.web_scraper import WebScraper, create_scraper_from_config
from modules.knowledge_base import KnowledgeBase
from modules.text_processing import TextProcessor


def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/scraping.log'),
            logging.StreamHandler()
        ]
    )


def scrape_single_site(url: str, max_pages: int = 20):
    """
    Скрапинг одного сайта
    
    Args:
        url: URL сайта для скрапинга
        max_pages: Максимальное количество страниц
    """
    print(f"🚀 Начинаем скрапинг сайта: {url}")
    
    scraper = create_scraper_from_config()
    result = scraper.scrape_and_add(url, max_pages)
    
    if result['success']:
        print(f"✅ Скрапинг завершен успешно!")
        print(f"📄 Обработано страниц: {result['pages_scraped']}")
        print(f"📝 Добавлено чанков: {result['chunks_added']}")
    else:
        print(f"❌ Ошибка скрапинга: {result['message']}")
    
    return result


def scrape_multiple_sites(urls: list, max_pages_per_site: int = 10):
    """
    Скрапинг нескольких сайтов
    
    Args:
        urls: Список URL для скрапинга
        max_pages_per_site: Максимальное количество страниц на сайт
    """
    print(f"🌐 Начинаем скрапинг {len(urls)} сайтов")
    
    scraper = create_scraper_from_config()
    total_pages = 0
    total_chunks = 0
    
    for i, url in enumerate(urls, 1):
        print(f"\n📋 Сайт {i}/{len(urls)}: {url}")
        
        result = scraper.scrape_and_add(url, max_pages_per_site)
        
        if result['success']:
            total_pages += result['pages_scraped']
            total_chunks += result['chunks_added']
            print(f"✅ Успешно: {result['pages_scraped']} страниц, {result['chunks_added']} чанков")
        else:
            print(f"❌ Ошибка: {result['message']}")
    
    print(f"\n🎉 Общий результат:")
    print(f"📄 Всего страниц: {total_pages}")
    print(f"📝 Всего чанков: {total_chunks}")


def get_legal_sites_list():
    """
    Список популярных юридических сайтов для скрапинга (РБ + РФ)
    
    Returns:
        Список URL юридических сайтов
    """
    return [
        # Основные правовые порталы Беларуси
        "https://pravo.by/",
        "https://www.government.by/",
        "https://www.house.gov.by/",
        "https://www.kc.gov.by/",
        "https://www.court.gov.by/",
        "https://www.prokuratura.gov.by/",
        "https://www.minjust.gov.by/",
        "https://www.notariat.by/",
        "https://www.lawbelarus.com/",
        "https://www.jurist.by/",
        
        # Российские правовые порталы (для сравнительного анализа)
        "https://www.garant.ru/",
        "https://www.consultant.ru/",
        "https://www.pravo.gov.ru/",
        "https://www.advgazeta.ru/",
        "https://www.law.ru/"
    ]


def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(
        description="Скрипт для скрапинга юридических сайтов и пополнения базы знаний"
    )
    
    parser.add_argument(
        '--url',
        type=str,
        help='URL сайта для скрапинга'
    )
    
    parser.add_argument(
        '--max-pages',
        type=int,
        default=20,
        help='Максимальное количество страниц для скрапинга (по умолчанию: 20)'
    )
    
    parser.add_argument(
        '--sites-file',
        type=str,
        help='Файл со списком URL для скрапинга (по одному URL на строку)'
    )
    
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Запустить демо-скрапинг популярных юридических сайтов'
    )
    
    parser.add_argument(
        '--list-sites',
        action='store_true',
        help='Показать список доступных юридических сайтов'
    )
    
    args = parser.parse_args()
    
    # Настройка логирования
    setup_logging()
    
    if args.list_sites:
        print("📋 Доступные юридические сайты для скрапинга:")
        sites = get_legal_sites_list()
        for i, site in enumerate(sites, 1):
            print(f"{i:2d}. {site}")
        return
    
    if args.demo:
        print("🎯 Запуск демо-скрапинга популярных юридических сайтов")
        sites = get_legal_sites_list()[:3]  # Берем первые 3 сайта для демо
        scrape_multiple_sites(sites, max_pages_per_site=5)
        return
    
    if args.sites_file:
        if not os.path.exists(args.sites_file):
            print(f"❌ Файл {args.sites_file} не найден")
            return
        
        with open(args.sites_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]
        
        if not urls:
            print("❌ Файл пуст или не содержит валидных URL")
            return
        
        scrape_multiple_sites(urls, args.max_pages)
        return
    
    if args.url:
        scrape_single_site(args.url, args.max_pages)
        return
    
    # Если не указаны аргументы, показываем справку
    print("🔍 Скрипт для скрапинга юридических сайтов")
    print("\n📖 Использование:")
    print("  python scripts/scrape_websites.py --url https://example.com")
    print("  python scripts/scrape_websites.py --demo")
    print("  python scripts/scrape_websites.py --sites-file urls.txt")
    print("  python scripts/scrape_websites.py --list-sites")
    print("\n💡 Примеры:")
    print("  # Скрапинг одного сайта")
    print("  python scripts/scrape_websites.py --url https://www.garant.ru/ --max-pages 10")
    print("\n  # Демо-скрапинг популярных сайтов")
    print("  python scripts/scrape_websites.py --demo")
    print("\n  # Скрапинг из файла")
    print("  python scripts/scrape_websites.py --sites-file legal_sites.txt")


if __name__ == "__main__":
    main() 