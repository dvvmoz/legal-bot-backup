#!/usr/bin/env python3
"""
Модуль для отключения телеметрии ChromaDB.
Импортируйте этот модуль в начале других модулей для предотвращения ошибок телеметрии.
"""
import os

# Отключаем телеметрию ChromaDB
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

# Дополнительные настройки для подавления предупреждений
os.environ["CHROMA_DISABLE_TELEMETRY"] = "True" 