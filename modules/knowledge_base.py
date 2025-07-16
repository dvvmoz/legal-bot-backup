#!/usr/bin/env python3
"""
Модуль для работы с базой знаний на основе ChromaDB.
"""
# Отключаем телеметрию ChromaDB в первую очередь
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import disable_telemetry

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

# Отключаем телеметрию ChromaDB для предотвращения ошибок
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from config import CHROMA_DB_PATH

# Отключаем логирование телеметрии ChromaDB
telemetry_logger = logging.getLogger('chromadb.telemetry')
telemetry_logger.setLevel(logging.CRITICAL)
telemetry_logger.addHandler(logging.NullHandler())

# Отключаем логирование posthog
posthog_logger = logging.getLogger('chromadb.telemetry.product.posthog')
posthog_logger.setLevel(logging.CRITICAL)
posthog_logger.addHandler(logging.NullHandler())

# Настройка логирования для этого модуля
logger = logging.getLogger(__name__)

class KnowledgeBase:
    """Класс для управления базой знаний."""
    
    def __init__(self, collection_name: str = "legal_docs"):
        """
        Инициализирует базу знаний.
        
        Args:
            collection_name: Имя коллекции в ChromaDB
        """
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self._initialize_db()
    
    def _initialize_db(self):
        """Инициализирует подключение к ChromaDB."""
        try:
            # Создаем директорию для базы данных, если она не существует
            os.makedirs(CHROMA_DB_PATH, exist_ok=True)
            
            # Инициализируем клиент ChromaDB
            self.client = chromadb.PersistentClient(
                path=CHROMA_DB_PATH,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                    is_persistent=True
                )
            )
            
            # Получаем или создаем коллекцию
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}  # Используем косинусное сходство
            )
            
            logger.info(f"✅ База знаний инициализирована: {self.collection_name}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации базы знаний: {e}")
            raise
    
    def add_document(self, doc_id: str, document_text: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Добавляет документ в базу знаний.
        
        Args:
            doc_id: Уникальный идентификатор документа
            document_text: Текст документа
            metadata: Метаданные документа
            
        Returns:
            True если документ добавлен успешно, False в противном случае
        """
        try:
            if not document_text or not document_text.strip():
                logger.warning(f"Пустой текст для документа {doc_id}")
                return False
            
            # Проверяем, существует ли уже документ с таким ID
            if self.document_exists(doc_id):
                logger.debug(f"Документ {doc_id} уже существует в базе знаний - пропускаем")
                return False
            
            if metadata is None:
                metadata = {}
            
            # Добавляем текущее время и размер документа в метаданные
            metadata.update({
                "length": len(document_text),
                "doc_id": doc_id,
                "added_date": datetime.now().isoformat()
            })
            
            self.collection.add(
                documents=[document_text],
                metadatas=[metadata],
                ids=[doc_id]
            )
            
            logger.debug(f"Документ {doc_id} добавлен в базу знаний")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка добавления документа {doc_id}: {e}")
            return False
    
    def search_relevant_docs(self, query_text: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Ищет релевантные документы по запросу.
        
        Args:
            query_text: Текст запроса для поиска
            n_results: Максимальное количество результатов
            
        Returns:
            Список найденных документов с метаданными
        """
        try:
            if not query_text or not query_text.strip():
                logger.warning("Пустой запрос для поиска")
                return []
            
            # Получаем количество документов в коллекции
            collection_count = self.collection.count()
            if collection_count == 0:
                logger.warning("База знаний пуста")
                return []
            
            # Ограничиваем количество результатов доступным количеством документов
            n_results = min(n_results, collection_count)
            
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            
            documents = results.get('documents', [[]])[0]
            distances = results.get('distances', [[]])[0]
            metadatas = results.get('metadatas', [[]])[0]
            
            # Фильтруем результаты по релевантности
            # Для косинусного расстояния: 0.0-0.3 отлично, 0.3-0.5 хорошо, 0.5-0.8 удовлетворительно, >0.8 плохо
            relevant_docs = []
            for i, (doc, distance) in enumerate(zip(documents, distances)):
                if distance < 0.9:  # Порог релевантности (слегка увеличен для максимального покрытия)
                    metadata = metadatas[i] if i < len(metadatas) and metadatas[i] else {}
                    relevant_docs.append({
                        'content': doc,
                        'metadata': metadata,
                        'distance': distance
                    })
            
            logger.info(f"📊 БАЗА ЗНАНИЙ: Найдено {len(relevant_docs)} релевантных документов для запроса: '{query_text[:50]}...'")
            if distances:
                avg_distance = sum(distances) / len(distances)
                min_distance = min(distances)
                
                # Определяем качество результатов (обновлена шкала для более агрессивного поиска на pravo.by)
                if min_distance < 0.3:
                    quality = "отличное"
                elif min_distance < 0.5:
                    quality = "хорошее"
                elif min_distance < 0.8:
                    quality = "удовлетворительное"
                else:
                    quality = "слабое"
                
                logger.info(f"📈 БАЗА ЗНАНИЙ: Средняя дистанция: {avg_distance:.3f}, лучший результат: {min_distance:.3f} ({quality} качество)")
            return relevant_docs
            
        except Exception as e:
            logger.error(f"Ошибка поиска документов: {e}")
            return []
    
    def should_use_dynamic_search(self, query_text: str, n_results: int = 3) -> tuple[bool, List[Dict[str, Any]]]:
        """
        Определяет, нужно ли использовать динамический поиск на основе качества результатов.
        
        Args:
            query_text: Текст запроса для поиска
            n_results: Максимальное количество результатов
            
        Returns:
            Кортеж (нужен_динамический_поиск, найденные_документы)
        """
        try:
            # Сначала ищем в базе знаний
            relevant_docs = self.search_relevant_docs(query_text, n_results)
            
            # Если документов нет совсем
            if not relevant_docs:
                logger.info(f"🔍 РЕШЕНИЕ: Документы не найдены - требуется динамический поиск")
                return True, []
            
            # Проверяем качество лучшего результата
            best_distance = min(doc['distance'] for doc in relevant_docs)
            
            # Проверяем семантическое соответствие запроса
            query_lower = query_text.lower()
            
            # Ключевые слова, которые указывают на процедурные вопросы
            procedural_keywords = [
                'как получить', 'как оформить', 'как подать', 'как зарегистрировать',
                'какие документы', 'какие справки', 'где получить', 'куда обратиться',
                'процедура', 'порядок', 'инструкция', 'пошагово', 'алгоритм',
                'лицензия', 'разрешение', 'справка', 'регистрация', 'оформление'
            ]
            
            # Ключевые слова, которые указывают на технические вопросы о боте
            bot_keywords = [
                'бот', 'не работает', 'не отвечает', 'не обращается', 'ошибка',
                'pravo.by', 'сайт', 'поиск', 'динамический'
            ]
            
            # Проверяем, является ли запрос процедурным или техническим
            is_procedural = any(keyword in query_lower for keyword in procedural_keywords)
            is_bot_related = any(keyword in query_lower for keyword in bot_keywords)
            
            # Если это вопрос о боте, всегда используем базу знаний
            if is_bot_related:
                logger.info(f"🔍 РЕШЕНИЕ: Технический вопрос о боте - используем базу знаний")
                return False, relevant_docs
            
            # Для процедурных вопросов проверяем релевантность содержимого
            if is_procedural:
                # Проверяем, содержат ли найденные документы процедурную информацию
                best_doc_content = relevant_docs[0]['content'].lower()
                procedural_content_keywords = [
                    'процедура', 'порядок', 'инструкция', 'алгоритм', 'пошагово',
                    'документы', 'справка', 'заявление', 'подача', 'получение',
                    'регистрация', 'оформление', 'лицензия', 'разрешение'
                ]
                
                has_procedural_content = any(keyword in best_doc_content for keyword in procedural_content_keywords)
                
                if not has_procedural_content or best_distance > 0.35:
                    logger.info(f"🔍 РЕШЕНИЕ: Процедурный вопрос без релевантного содержимого (дистанция: {best_distance:.3f}) - требуется динамический поиск")
                    return True, relevant_docs
                else:
                    logger.info(f"🔍 РЕШЕНИЕ: Процедурный вопрос с релевантным содержимым (дистанция: {best_distance:.3f}) - используем базу знаний")
                    return False, relevant_docs
            
            # Для общих вопросов используем стандартный порог
            if best_distance > 0.6:
                logger.info(f"🔍 РЕШЕНИЕ: Низкое качество результатов (дистанция: {best_distance:.3f}) - требуется динамический поиск")
                return True, relevant_docs
            
            # Если качество хорошее, используем найденные документы
            logger.info(f"🔍 РЕШЕНИЕ: Хорошее качество результатов (дистанция: {best_distance:.3f}) - используем базу знаний")
            return False, relevant_docs
            
        except Exception as e:
            logger.error(f"Ошибка при определении необходимости динамического поиска: {e}")
            # В случае ошибки возвращаем пустой результат и флаг для динамического поиска
            return True, []
    
    def document_exists(self, doc_id: str) -> bool:
        """
        Проверяет, существует ли документ в базе знаний.
        
        Args:
            doc_id: Идентификатор документа
            
        Returns:
            True если документ существует, False в противном случае
        """
        try:
            # Пытаемся получить документ по ID
            result = self.collection.get(ids=[doc_id])
            return len(result.get('ids', [])) > 0
        except Exception as e:
            logger.error(f"Ошибка проверки существования документа {doc_id}: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику коллекции.
        
        Returns:
            Словарь со статистикой
        """
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "db_path": CHROMA_DB_PATH
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return {"error": str(e)}
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Удаляет документ из базы знаний.
        
        Args:
            doc_id: Идентификатор документа для удаления
            
        Returns:
            True если документ удален успешно
        """
        try:
            self.collection.delete(ids=[doc_id])
            logger.info(f"Документ {doc_id} удален из базы знаний")
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления документа {doc_id}: {e}")
            return False
    
    def clear_collection(self) -> bool:
        """
        Очищает всю коллекцию.
        
        Returns:
            True если коллекция очищена успешно
        """
        try:
            # Удаляем коллекцию и создаем новую
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("База знаний очищена")
            return True
        except Exception as e:
            logger.error(f"Ошибка очистки базы знаний: {e}")
            return False

# Глобальный экземпляр для использования в других модулях
_knowledge_base = None

def get_knowledge_base() -> KnowledgeBase:
    """Возвращает глобальный экземпляр базы знаний."""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base

# Удобные функции для использования в других модулях
def add_document(doc_id: str, document_text: str, metadata: Dict[str, Any] = None) -> bool:
    """Добавляет документ в базу знаний."""
    return get_knowledge_base().add_document(doc_id, document_text, metadata)

def search_relevant_docs(query_text: str, n_results: int = 3) -> List[Dict[str, Any]]:
    """Ищет релевантные документы."""
    return get_knowledge_base().search_relevant_docs(query_text, n_results) 

def should_use_dynamic_search(query_text: str, n_results: int = 3) -> tuple[bool, List[Dict[str, Any]]]:
    """Определяет, нужно ли использовать динамический поиск."""
    return get_knowledge_base().should_use_dynamic_search(query_text, n_results) 

def document_exists(doc_id: str) -> bool:
    """Проверяет, существует ли документ в базе знаний."""
    return get_knowledge_base().document_exists(doc_id) 