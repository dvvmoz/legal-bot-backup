#!/usr/bin/env python3
"""
Скрипт для обновления существующих документов в базе знаний.
"""
import os
import sys
import logging
from pathlib import Path

# Добавляем корневую папку проекта в sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import load_config
from modules.text_processing import get_supported_extensions, is_supported_document
from modules.knowledge_base import get_knowledge_base
from scripts.populate_db import update_document_file, show_statistics

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/rebuild_knowledge_base.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def update_specific_document(file_path: str) -> bool:
    """
    Обновляет конкретный документ.
    
    Args:
        file_path: Путь к файлу документа
        
    Returns:
        True если документ обновлен успешно
    """
    if not os.path.exists(file_path):
        logger.error(f"❌ Файл не найден: {file_path}")
        return False
    
    if not is_supported_document(file_path):
        logger.error(f"❌ Неподдерживаемый формат файла: {file_path}")
        return False
    
    filename = os.path.basename(file_path)
    base_name = os.path.splitext(filename)[0]
    
    # Проверяем, существует ли документ в базе знаний
    kb = get_knowledge_base()
    doc_exists = False
    block_index = 0
    
    while True:
        doc_id = f"{base_name}_block_{block_index:03d}"
        if kb.document_exists(doc_id):
            doc_exists = True
            break
        block_index += 1
        if block_index > 10:  # Проверяем первые 10 блоков
            break
    
    if not doc_exists:
        logger.warning(f"⚠️ Документ {filename} не найден в базе знаний")
        choice = input("Добавить как новый документ? (y/n): ").lower()
        if choice == 'y':
            from scripts.populate_db import process_document_file
            added = process_document_file(file_path)
            if added > 0:
                logger.info(f"✅ Документ {filename} добавлен как новый ({added} блоков)")
                return True
        return False
    
    # Обновляем документ
    updated_blocks = update_document_file(file_path)
    
    if updated_blocks > 0:
        logger.info(f"✅ Документ {filename} успешно обновлен")
        return True
    else:
        logger.error(f"❌ Не удалось обновить документ {filename}")
        return False

def update_all_documents(data_dir: str = "data/documents") -> dict:
    """
    Обновляет все документы в указанной директории.
    
    Args:
        data_dir: Путь к директории с файлами документов
        
    Returns:
        Статистика обновления
    """
    stats = {
        "total_files": 0,
        "updated_files": 0,
        "new_files": 0,
        "failed_files": [],
        "total_blocks": 0,
        "file_types": {}
    }
    
    # Проверяем существование директории
    if not os.path.exists(data_dir):
        logger.error(f"❌ Директория {data_dir} не найдена")
        return stats
    
    # Получаем список поддерживаемых файлов
    supported_extensions = get_supported_extensions()
    document_files = []
    
    for filename in os.listdir(data_dir):
        file_path = os.path.join(data_dir, filename)
        if os.path.isfile(file_path) and is_supported_document(file_path):
            document_files.append(filename)
            
            # Подсчитываем типы файлов
            file_ext = Path(filename).suffix.lower()
            stats["file_types"][file_ext] = stats["file_types"].get(file_ext, 0) + 1
    
    if not document_files:
        logger.warning(f"❌ Поддерживаемые файлы в директории {data_dir} не найдены")
        logger.info(f"📋 Поддерживаемые форматы: {', '.join(supported_extensions)}")
        return stats
    
    stats["total_files"] = len(document_files)
    logger.info(f"📚 Найдено {len(document_files)} файлов для обновления")
    logger.info(f"📊 Типы файлов: {dict(stats['file_types'])}")
    
    kb = get_knowledge_base()
    
    # Обрабатываем каждый файл
    for filename in document_files:
        file_path = os.path.join(data_dir, filename)
        base_name = os.path.splitext(filename)[0]
        
        # Проверяем, существует ли документ в базе знаний
        doc_exists = kb.document_exists(f"{base_name}_block_000")
        
        if doc_exists:
            # Обновляем существующий документ
            blocks_added = update_document_file(file_path, data_dir)
            if blocks_added > 0:
                stats["updated_files"] += 1
                stats["total_blocks"] += blocks_added
            else:
                stats["failed_files"].append(filename)
        else:
            # Добавляем новый документ
            from scripts.populate_db import process_document_file
            blocks_added = process_document_file(file_path, data_dir)
            if blocks_added > 0:
                stats["new_files"] += 1
                stats["total_blocks"] += blocks_added
            else:
                stats["failed_files"].append(filename)
    
    return stats

def show_update_statistics(stats: dict):
    """
    Отображает статистику обновления файлов.
    
    Args:
        stats: Словарь со статистикой
    """
    print("\n" + "="*60)
    print("🔄 СТАТИСТИКА ОБНОВЛЕНИЯ ДОКУМЕНТОВ")
    print("="*60)
    
    print(f"📁 Всего файлов найдено: {stats['total_files']}")
    print(f"🔄 Обновлено существующих: {stats['updated_files']}")
    print(f"➕ Добавлено новых: {stats['new_files']}")
    print(f"❌ Не удалось обработать: {len(stats['failed_files'])}")
    print(f"📝 Всего блоков обработано: {stats['total_blocks']}")
    
    if stats.get('file_types'):
        print(f"\n📋 Типы обработанных файлов:")
        for file_type, count in stats['file_types'].items():
            print(f"  {file_type}: {count} файлов")
    
    if stats['failed_files']:
        print(f"\n❌ Файлы с ошибками:")
        for filename in stats['failed_files']:
            print(f"  • {filename}")
    
    print("\n" + "="*60)

def main():
    """Основная функция скрипта."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Обновление документов в базе знаний")
    parser.add_argument("--file", "-f", help="Обновить конкретный файл")
    parser.add_argument("--all", "-a", action="store_true", help="Обновить все файлы в папке")
    parser.add_argument("--dir", "-d", default="data/documents", help="Папка с документами")
    
    args = parser.parse_args()
    
    logger.info("🔄 Запуск скрипта обновления документов")
    
    try:
        # Загружаем конфигурацию
        load_config()
        
        if args.file:
            # Обновляем конкретный файл
            if update_specific_document(args.file):
                print("✅ Файл успешно обновлен!")
            else:
                print("❌ Не удалось обновить файл")
        
        elif args.all:
            # Обновляем все файлы
            stats = update_all_documents(args.dir)
            show_update_statistics(stats)
            
            if stats["updated_files"] > 0 or stats["new_files"] > 0:
                logger.info("✅ Обновление документов завершено успешно!")
            else:
                logger.warning("❌ Не удалось обновить ни одного документа")
        
        else:
            # Показываем справку
            print("🔄 Скрипт обновления документов в базе знаний")
            print("\nИспользование:")
            print("  python scripts/update_documents.py --file путь/к/файлу.pdf")
            print("  python scripts/update_documents.py --all")
            print("  python scripts/update_documents.py --all --dir data/documents")
            print("\nОпции:")
            print("  --file, -f    Обновить конкретный файл")
            print("  --all, -a     Обновить все файлы в папке")
            print("  --dir, -d     Папка с документами (по умолчанию: data/documents)")
            
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 