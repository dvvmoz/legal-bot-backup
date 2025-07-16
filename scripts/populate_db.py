#!/usr/bin/env python3
"""
Скрипт для наполнения базы знаний из PDF и Word файлов.
"""
import os
import sys
import logging
from pathlib import Path

# Добавляем корневую папку проекта в sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import load_config
from modules.text_processing import (
    extract_text_from_document, 
    split_text_into_structure, 
    get_supported_extensions,
    is_supported_document
)
from modules.knowledge_base import add_document, get_knowledge_base

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/add_scraped_to_knowledge_base.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def update_document_file(file_path: str, source_folder: str = "data/documents") -> int:
    """
    Обновляет документ в базе знаний, удаляя старые блоки и добавляя новые.
    
    Args:
        file_path: Путь к файлу документа
        source_folder: Папка-источник для метаданных
        
    Returns:
        Количество добавленных блоков
    """
    try:
        filename = os.path.basename(file_path)
        file_extension = Path(file_path).suffix.lower()
        base_name = os.path.splitext(filename)[0]
        
        logger.info(f"🔄 Обновляю файл: {filename} (формат: {file_extension})")
        
        # Проверяем поддерживаемый формат
        if not is_supported_document(file_path):
            logger.warning(f"❌ Неподдерживаемый формат файла: {file_extension}")
            return 0
        
        # Получаем базу знаний
        kb = get_knowledge_base()
        
        # Удаляем все существующие блоки этого документа
        deleted_count = 0
        block_index = 0
        while True:
            doc_id = f"{base_name}_block_{block_index:03d}"
            if kb.document_exists(doc_id):
                if kb.delete_document(doc_id):
                    deleted_count += 1
                block_index += 1
            else:
                break
        
        if deleted_count > 0:
            logger.info(f"🗑️ Удалено {deleted_count} старых блоков документа {filename}")
        
        # Теперь добавляем новую версию документа
        added_count = process_document_file(file_path, source_folder)
        
        if added_count > 0:
            logger.info(f"✅ Документ {filename} обновлен: удалено {deleted_count}, добавлено {added_count} блоков")
        
        return added_count
        
    except Exception as e:
        logger.error(f"💥 Критическая ошибка при обновлении файла {file_path}: {e}")
        return 0

def process_document_file(file_path: str, source_folder: str = "data/documents") -> int:
    """
    Обрабатывает один файл документа (PDF, DOCX, DOC) и добавляет его содержимое в базу знаний.
    
    Args:
        file_path: Путь к файлу документа
        source_folder: Папка-источник для метаданных
        
    Returns:
        Количество добавленных документов
    """
    try:
        filename = os.path.basename(file_path)
        file_extension = Path(file_path).suffix.lower()
        
        logger.info(f"📄 Обрабатываю файл: {filename} (формат: {file_extension})")
        
        # Проверяем поддерживаемый формат
        if not is_supported_document(file_path):
            logger.warning(f"❌ Неподдерживаемый формат файла: {file_extension}")
            return 0
        
        # Извлекаем текст из документа
        try:
            full_text = extract_text_from_document(file_path)
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения текста из {filename}: {e}")
            return 0
        
        if not full_text.strip():
            logger.warning(f"❌ Файл {filename} пуст или не содержит текста")
            return 0
        
        # Разделяем текст на структурированные блоки
        text_blocks = split_text_into_structure(full_text)
        
        if not text_blocks:
            logger.warning(f"❌ Не удалось разделить текст из файла {filename}")
            return 0
        
        # Добавляем каждый блок в базу знаний
        added_count = 0
        base_name = os.path.splitext(filename)[0]
        
        for i, block in enumerate(text_blocks):
            # Создаем уникальный ID для каждого блока
            doc_id = f"{base_name}_block_{i:03d}"
            
            # Метаданные для блока
            metadata = {
                "source_file": filename,
                "source_folder": source_folder,
                "file_type": file_extension,
                "block_index": i,
                "total_blocks": len(text_blocks),
                "block_length": len(block)
            }
            
            # Добавляем блок в базу знаний
            if add_document(doc_id, block, metadata):
                added_count += 1
            else:
                logger.warning(f"❌ Не удалось добавить блок {i} из файла {filename}")
        
        logger.info(f"✅ Добавлено {added_count} блоков из файла {filename}")
        return added_count
        
    except Exception as e:
        logger.error(f"💥 Критическая ошибка при обработке файла {file_path}: {e}")
        return 0

def populate_from_directory(data_dir: str = "data/documents") -> dict:
    """
    Наполняет базу знаний из всех поддерживаемых файлов в указанной директории.
    
    Args:
        data_dir: Путь к директории с файлами документов
        
    Returns:
        Статистика обработки
    """
    stats = {
        "total_files": 0,
        "processed_files": 0,
        "total_blocks": 0,
        "failed_files": [],
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
    logger.info(f"📚 Найдено {len(document_files)} файлов для обработки")
    logger.info(f"📊 Типы файлов: {dict(stats['file_types'])}")
    
    # Обрабатываем каждый файл
    for filename in document_files:
        file_path = os.path.join(data_dir, filename)
        
        blocks_added = process_document_file(file_path, data_dir)
        
        if blocks_added > 0:
            stats["processed_files"] += 1
            stats["total_blocks"] += blocks_added
        else:
            stats["failed_files"].append(filename)
    
    return stats

def show_statistics(stats: dict):
    """
    Отображает статистику обработки файлов.
    
    Args:
        stats: Словарь со статистикой
    """
    print("\n" + "="*60)
    print("📊 СТАТИСТИКА ОБРАБОТКИ ФАЙЛОВ")
    print("="*60)
    
    print(f"📁 Всего файлов найдено: {stats['total_files']}")
    print(f"✅ Успешно обработано: {stats['processed_files']}")
    print(f"❌ Не удалось обработать: {len(stats['failed_files'])}")
    print(f"📝 Всего добавлено блоков: {stats['total_blocks']}")
    
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
    logger.info("🚀 Запуск скрипта наполнения базы знаний")
    
    try:
        # Загружаем конфигурацию
        load_config()
        
        # Проверяем наличие папки data/documents
        data_dir = "data/documents"
        if not os.path.exists(data_dir):
            logger.info(f"📁 Создаю директорию {data_dir}")
            os.makedirs(data_dir, exist_ok=True)
            
            supported_formats = get_supported_extensions()
            logger.info(f"📁 Директория {data_dir} создана.")
            logger.info(f"📋 Поддерживаемые форматы: {', '.join(supported_formats)}")
            logger.info(f"📄 Добавьте файлы документов в папку {data_dir} и запустите скрипт снова.")
            return
        
        # Показываем информацию о поддерживаемых форматах
        supported_formats = get_supported_extensions()
        logger.info(f"📋 Поддерживаемые форматы документов: {', '.join(supported_formats)}")
        
        # Наполняем базу знаний
        stats = populate_from_directory(data_dir)
        
        # Показываем статистику
        show_statistics(stats)
        
        if stats["processed_files"] > 0:
            logger.info("✅ Наполнение базы знаний завершено успешно!")
            logger.info(f"📊 Обработано {stats['processed_files']} файлов, добавлено {stats['total_blocks']} блоков")
        else:
            logger.warning("❌ Не удалось обработать ни одного файла")
            
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 