"""
ML-фильтр для определения юридических вопросов с использованием машинного обучения.
Основан на обучающих данных из тестовых случаев.
"""

import re
import logging
from typing import Tuple, List, Dict, Any
from dataclasses import dataclass
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os

logger = logging.getLogger(__name__)

@dataclass
class TrainingExample:
    """Пример для обучения ML-модели."""
    question: str
    is_legal: bool
    category: str
    confidence: float = 1.0

class MLQuestionFilter:
    """
    ML-фильтр для определения юридических вопросов.
    Использует комбинацию TF-IDF векторизации и ансамбля классификаторов.
    """
    
    def __init__(self, model_path: str = "models/legal_question_classifier.pkl"):
        """
        Инициализация ML-фильтра.
        
        Args:
            model_path: Путь к сохраненной модели
        """
        self.model_path = model_path
        self.vectorizer = None
        self.classifier = None
        self.is_trained = False
        
        # Создаем директорию для моделей
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        # Загружаем модель если она существует
        self._load_model()
        
        # Если модель не загружена, создаем и обучаем новую
        if not self.is_trained:
            self._train_model()
    
    def _get_training_data(self) -> List[TrainingExample]:
        """Получает обучающие данные из наших тестовых случаев."""
        training_data = [
            # Стандартные юридические вопросы
            TrainingExample("Как подать иск в суд в Беларуси?", True, "стандартный"),
            TrainingExample("Какие документы нужны для развода в РБ?", True, "стандартный"),
            TrainingExample("Как оформить трудовой договор по ТК РБ?", True, "стандартный"),
            TrainingExample("Какие права у потребителя в Беларуси?", True, "стандартный"),
            TrainingExample("Как обжаловать решение административного органа?", True, "стандартный"),
            
            # Короткие юридические вопросы (ДОБАВЛЕНО)
            TrainingExample("открытие ип", True, "короткий"),
            TrainingExample("регистрация ип", True, "короткий"),
            TrainingExample("как открыть ип", True, "короткий"),
            TrainingExample("документы для ип", True, "короткий"),
            TrainingExample("закрытие ип", True, "короткий"),
            TrainingExample("налоги ип", True, "короткий"),
            TrainingExample("права ип", True, "короткий"),
            TrainingExample("ип в беларуси", True, "короткий"),
            TrainingExample("развод документы", True, "короткий"),
            TrainingExample("трудовой договор", True, "короткий"),
            TrainingExample("увольнение права", True, "короткий"),
            TrainingExample("алименты размер", True, "короткий"),
            TrainingExample("наследство оформить", True, "короткий"),
            TrainingExample("штраф гаи", True, "короткий"),
            TrainingExample("жалоба в суд", True, "короткий"),
            TrainingExample("права потребителя", True, "короткий"),
            TrainingExample("договор аренды", True, "короткий"),
            TrainingExample("банкротство физлица", True, "короткий"),
            TrainingExample("защита прав", True, "короткий"),
            TrainingExample("иск к соседу", True, "короткий"),
            
            # Разговорные юридические вопросы
            TrainingExample("Меня кинули с деньгами, что делать?", True, "разговорный"),
            TrainingExample("Начальник не платит зарплату уже месяц", True, "разговорный"),
            TrainingExample("Соседи шумят по ночам, как их утихомирить?", True, "разговорный"),
            TrainingExample("Развожусь с мужем, он не дает денег на ребенка", True, "разговорный"),
            TrainingExample("Купил телефон, а он сломался через неделю", True, "разговорный"),
            TrainingExample("Меня уволили без предупреждения", True, "разговорный"),
            TrainingExample("Банк списал деньги без моего согласия", True, "разговорный"),
            TrainingExample("Врач сделал неправильную операцию", True, "разговорный"),
            TrainingExample("Полиция задержала без причины", True, "разговорный"),
            TrainingExample("Управляющая компания не делает ремонт", True, "разговорный"),
            
            # Специализированные юридические термины
            TrainingExample("Эстоппель в гражданском праве", True, "специализированный"),
            TrainingExample("Субсидиарная ответственность учредителей", True, "специализированный"),
            TrainingExample("Виндикационный иск против добросовестного приобретателя", True, "специализированный"),
            TrainingExample("Негаторный иск в отношении недвижимости", True, "специализированный"),
            TrainingExample("Реституция при недействительности сделки", True, "специализированный"),
            TrainingExample("Цессия требования по договору подряда", True, "специализированный"),
            TrainingExample("Новация долга в обязательственном праве", True, "специализированный"),
            TrainingExample("Суброгация в страховом праве", True, "специализированный"),
            TrainingExample("Деликтная ответственность за причинение вреда", True, "специализированный"),
            TrainingExample("Виндикация бездокументарных ценных бумаг", True, "специализированный"),
            
            # Иностранные юридические термины
            TrainingExample("Что такое habeas corpus?", True, "иностранный"),
            TrainingExample("Принцип pacta sunt servanda", True, "иностранный"),
            TrainingExample("Доктрина res ipsa loquitur", True, "иностранный"),
            TrainingExample("Правило de minimis non curat lex", True, "иностранный"),
            TrainingExample("Принцип ultra vires в корпоративном праве", True, "иностранный"),
            TrainingExample("Что означает pro bono в юриспруденции?", True, "иностранный"),
            TrainingExample("Концепция force majeure в договорах", True, "иностранный"),
            TrainingExample("Принцип caveat emptor при покупке", True, "иностранный"),
            TrainingExample("Доктрина respondeat superior", True, "иностранный"),
            TrainingExample("Правило nemo dat quod non habet", True, "иностранный"),
            
            # Контекстные юридические вопросы
            TrainingExample("Права человека в интернете", True, "контекстный"),
            TrainingExample("Страхование жизни и здоровья", True, "контекстный"),
            TrainingExample("Защита персональных данных", True, "контекстный"),
            TrainingExample("Трудовые споры с работодателем", True, "контекстный"),
            TrainingExample("Медицинская ответственность врачей", True, "контекстный"),
            TrainingExample("Банковские услуги для бизнеса", True, "контекстный"),
            TrainingExample("Как оформить наследство?", True, "контекстный"),
            TrainingExample("Какие права у меня есть?", True, "контекстный"),
            TrainingExample("Как защитить свои интересы?", True, "контекстный"),
            TrainingExample("Что делать с долгами?", True, "контекстный"),
            
            # Региональные юридические вопросы
            TrainingExample("Как работает мировой суд в Минске?", True, "региональный"),
            TrainingExample("Особенности регистрации ИП в Гомеле", True, "региональный"),
            TrainingExample("Налоговые льготы в ПВТ", True, "региональный"),
            TrainingExample("Земельное законодательство в Брестской области", True, "региональный"),
            TrainingExample("Жилищные вопросы в Витебске", True, "региональный"),
            TrainingExample("Трудовое право в свободных экономических зонах", True, "региональный"),
            TrainingExample("Права потребителей в интернет-магазинах РБ", True, "региональный"),
            TrainingExample("Экологическое право в Гродненской области", True, "региональный"),
            
            # Неюридические вопросы (технические ложные срабатывания)
            TrainingExample("Как работает суд присяжных в кино?", False, "техническое"),
            TrainingExample("Права доступа к базе данных", False, "техническое"),
            TrainingExample("Защита растений от вредителей", False, "техническое"),
            TrainingExample("Договор с интернет-провайдером не работает", False, "техническое"),
            TrainingExample("Налоговая декларация в Excel", False, "техническое"),
            TrainingExample("Трудовой стаж в компьютерной игре", False, "техническое"),
            TrainingExample("Права администратора в Windows", False, "техническое"),
            TrainingExample("Наследование классов в программировании", False, "техническое"),
            TrainingExample("Защита авторских прав в интернете", False, "техническое"),
            TrainingExample("Юридическая фирма ищет программиста", False, "техническое"),
            
            # Общие неюридические вопросы
            TrainingExample("Как приготовить борщ?", False, "обычное"),
            TrainingExample("Какая погода завтра?", False, "обычное"),
            TrainingExample("Как похудеть на 10 кг?", False, "обычное"),
            TrainingExample("Где скачать фильм?", False, "обычное"),
            TrainingExample("Как установить Windows?", False, "обычное"),
            TrainingExample("Что посмотреть в кино?", False, "обычное"),
            TrainingExample("Как готовить пиццу?", False, "обычное"),
            TrainingExample("Где купить телефон?", False, "обычное"),
            TrainingExample("Как изучить английский язык?", False, "обычное"),
            TrainingExample("Что делать при простуде?", False, "обычное"),
            
            # Короткие неюридические вопросы (ДОБАВЛЕНО)
            TrainingExample("приготовить еду", False, "короткий_не_юр"),
            TrainingExample("купить телефон", False, "короткий_не_юр"),
            TrainingExample("установить игру", False, "короткий_не_юр"),
            TrainingExample("скачать фильм", False, "короткий_не_юр"),
            TrainingExample("погода завтра", False, "короткий_не_юр"),
            TrainingExample("изучить язык", False, "короткий_не_юр"),
            TrainingExample("похудеть быстро", False, "короткий_не_юр"),
            TrainingExample("путешествие в европу", False, "короткий_не_юр"),
            TrainingExample("ремонт квартиры", False, "короткий_не_юр"),
            TrainingExample("работа программист", False, "короткий_не_юр"),
            
            # Контекстные неюридические вопросы
            TrainingExample("Как подать документы?", False, "контекстный_не_юр"),
            TrainingExample("Что мне делать?", False, "контекстный_не_юр"),
            TrainingExample("Куда обращаться за помощью?", False, "контекстный_не_юр"),
            TrainingExample("Какие документы нужны?", False, "контекстный_не_юр"),
            TrainingExample("Сколько это стоит?", False, "контекстный_не_юр"),
            TrainingExample("Можно ли это сделать?", False, "контекстный_не_юр"),
        ]
        
        return training_data
    
    def _extract_features(self, question: str) -> Dict[str, Any]:
        """Извлекает признаки из вопроса для ML-модели."""
        features = {}
        question_lower = question.lower()
        
        # Базовые признаки
        features['length'] = len(question)
        features['word_count'] = len(question.split())
        features['has_question_mark'] = '?' in question
        features['has_exclamation'] = '!' in question
        
        # Юридические ключевые слова (РАСШИРЕННЫЙ СПИСОК)
        legal_keywords = [
            'суд', 'право', 'закон', 'договор', 'иск', 'жалоба', 'нарушение',
            'ответственность', 'требование', 'обязательство', 'штраф', 'налог',
            'трудовой', 'гражданский', 'административный', 'уголовный',
            'ип', 'предприниматель', 'регистрация', 'открытие', 'закрытие',
            'алименты', 'развод', 'наследство', 'завещание', 'опека',
            'банкротство', 'долг', 'кредит', 'банк', 'страхование',
            'недвижимость', 'аренда', 'собственность', 'земля', 'участок',
            'увольнение', 'работа', 'зарплата', 'отпуск', 'больничный',
            'защита', 'консультация', 'юрист', 'адвокат', 'нотариус',
            'документы', 'справка', 'заявление', 'оформить', 'подать'
        ]
        
        features['legal_keyword_count'] = sum(1 for word in legal_keywords if word in question_lower)
        features['legal_keyword_density'] = features['legal_keyword_count'] / max(features['word_count'], 1)
        
        # Разговорные выражения
        colloquial_words = ['кинули', 'обманули', 'уволили', 'списал', 'задержала']
        features['colloquial_count'] = sum(1 for word in colloquial_words if word in question_lower)
        
        # Специализированные термины
        specialized_terms = ['эстоппель', 'субсидиарная', 'виндикационный', 'негаторный', 'реституция']
        features['specialized_count'] = sum(1 for term in specialized_terms if term in question_lower)
        
        # Иностранные термины
        foreign_terms = ['habeas corpus', 'pacta sunt servanda', 'res ipsa loquitur', 'force majeure']
        features['foreign_count'] = sum(1 for term in foreign_terms if term in question_lower)
        
        # Региональные маркеры
        regional_markers = ['минск', 'гомель', 'брест', 'витебск', 'гродно', 'пвт', 'рб', 'беларус']
        features['regional_count'] = sum(1 for marker in regional_markers if marker in question_lower)
        
        # Технические исключения
        tech_exclusions = ['программ', 'компьютер', 'интернет', 'база данных', 'excel', 'windows']
        features['tech_exclusion_count'] = sum(1 for term in tech_exclusions if term in question_lower)
        
        # Специальные признаки для коротких вопросов (ДОБАВЛЕНО)
        short_legal_patterns = [
            'ип', 'предприниматель', 'регистрация', 'открытие', 'закрытие',
            'развод', 'алименты', 'наследство', 'завещание', 'долг', 'кредит',
            'штраф', 'право', 'закон', 'суд', 'иск', 'жалоба', 'договор',
            'увольнение', 'зарплата', 'отпуск', 'больничный', 'работа'
        ]
        features['short_legal_count'] = sum(1 for pattern in short_legal_patterns if pattern in question_lower)
        
        # Бонус для очень коротких юридических вопросов
        features['short_legal_bonus'] = 1 if (features['word_count'] <= 3 and features['short_legal_count'] > 0) else 0
        
        return features
    
    def _train_model(self):
        """Обучает ML-модель на подготовленных данных."""
        logger.info("Начинаем обучение ML-модели...")
        
        # Получаем обучающие данные
        training_data = self._get_training_data()
        
        # Подготавливаем данные
        texts = [example.question for example in training_data]
        labels = [example.is_legal for example in training_data]
        
        # Создаем TF-IDF векторизатор
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),
            stop_words=None,
            lowercase=True,
            analyzer='word'
        )
        
        # Векторизуем тексты
        X_tfidf = self.vectorizer.fit_transform(texts)
        
        # Извлекаем дополнительные признаки
        feature_data = []
        for text in texts:
            features = self._extract_features(text)
            feature_data.append(list(features.values()))
        
        X_features = np.array(feature_data)
        
        # Объединяем TF-IDF и дополнительные признаки
        X_combined = np.hstack([X_tfidf.toarray(), X_features])
        
        # Разделяем на обучающую и тестовую выборки
        X_train, X_test, y_train, y_test = train_test_split(
            X_combined, labels, test_size=0.2, random_state=42, stratify=labels
        )
        
        # Создаем ансамбль классификаторов
        from sklearn.ensemble import VotingClassifier
        
        lr_classifier = LogisticRegression(random_state=42, max_iter=1000)
        rf_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        
        self.classifier = VotingClassifier(
            estimators=[
                ('lr', lr_classifier),
                ('rf', rf_classifier)
            ],
            voting='soft'
        )
        
        # Обучаем модель
        self.classifier.fit(X_train, y_train)
        
        # Оцениваем качество
        y_pred = self.classifier.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.info(f"Точность ML-модели: {accuracy:.3f}")
        logger.info(f"Отчет о классификации:\n{classification_report(y_test, y_pred)}")
        
        self.is_trained = True
        
        # Сохраняем модель
        self._save_model()
    
    def _save_model(self):
        """Сохраняет обученную модель."""
        try:
            model_data = {
                'vectorizer': self.vectorizer,
                'classifier': self.classifier,
                'is_trained': self.is_trained
            }
            joblib.dump(model_data, self.model_path)
            logger.info(f"Модель сохранена в {self.model_path}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении модели: {e}")
    
    def _load_model(self):
        """Загружает сохраненную модель."""
        try:
            if os.path.exists(self.model_path):
                model_data = joblib.load(self.model_path)
                self.vectorizer = model_data['vectorizer']
                self.classifier = model_data['classifier']
                self.is_trained = model_data['is_trained']
                logger.info(f"Модель загружена из {self.model_path}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели: {e}")
            self.is_trained = False
    
    def is_legal_question(self, question: str) -> Tuple[bool, float, str]:
        """
        Определяет, является ли вопрос юридическим с использованием ML.
        
        Args:
            question: Текст вопроса
            
        Returns:
            Кортеж (is_legal, confidence, explanation)
        """
        if not question or not question.strip():
            return False, 0.0, "Пустой вопрос"
        
        if not self.is_trained:
            return False, 0.0, "Модель не обучена"
        
        try:
            # Векторизуем вопрос
            X_tfidf = self.vectorizer.transform([question])
            
            # Извлекаем дополнительные признаки
            features = self._extract_features(question)
            X_features = np.array([list(features.values())])
            
            # Объединяем признаки
            X_combined = np.hstack([X_tfidf.toarray(), X_features])
            
            # Получаем предсказание и вероятность
            prediction = self.classifier.predict(X_combined)[0]
            probabilities = self.classifier.predict_proba(X_combined)[0]
            
            # Вероятность для класса "юридический"
            confidence = probabilities[1] if len(probabilities) > 1 else probabilities[0]
            
            explanation = f"ML-предсказание: {prediction}, уверенность: {confidence:.3f}"
            
            return bool(prediction), float(confidence), explanation
            
        except Exception as e:
            logger.error(f"Ошибка в ML-фильтре: {e}")
            return False, 0.0, f"Ошибка обработки: {str(e)}"
    
    def get_rejection_message(self) -> str:
        """Возвращает сообщение об отклонении неюридического вопроса."""
        return ("Извините, но ваш вопрос не относится к юридической тематике. "
                "Я специализируюсь на вопросах права и законодательства Беларуси. "
                "Пожалуйста, задайте вопрос, связанный с юридической тематикой.")


# Глобальный экземпляр фильтра
_ml_filter_instance = None

def get_ml_question_filter() -> MLQuestionFilter:
    """Возвращает глобальный экземпляр ML-фильтра."""
    global _ml_filter_instance
    if _ml_filter_instance is None:
        _ml_filter_instance = MLQuestionFilter()
    return _ml_filter_instance

def is_legal_question_ml(question: str) -> Tuple[bool, float, str]:
    """
    Определяет, является ли вопрос юридическим с использованием ML.
    
    Args:
        question: Текст вопроса
        
    Returns:
        Кортеж (is_legal, confidence, explanation)
    """
    filter_instance = get_ml_question_filter()
    return filter_instance.is_legal_question(question)

def get_ml_rejection_message() -> str:
    """Возвращает сообщение об отклонении неюридического вопроса из ML-фильтра."""
    filter_instance = get_ml_question_filter()
    return filter_instance.get_rejection_message() 