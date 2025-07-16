#!/bin/bash

# === Настройки ===
REPO_DIR="/opt/legal-bot"           # Путь к вашему проекту
GIT_REMOTE="origin"                 # Имя remote (обычно origin)
BRANCH="main"                       # Ветка для кода
COMMIT_MSG="Бэкап кода $(date '+%Y-%m-%d %H:%M')"

# === Перейти в папку проекта ===
cd "$REPO_DIR" || { echo "Нет папки $REPO_DIR"; exit 1; }

# === Добавить только код и инфраструктуру ===
git add *.py *.md requirements.txt docker-compose* Dockerfile* scripts/ modules/ templates/ static/ examples/ .gitignore env.example

# === Коммитим изменения (только если есть что коммитить) ===
if ! git diff --cached --quiet; then
    git commit -m "$COMMIT_MSG"
    git push $GIT_REMOTE $BRANCH
    echo "Код успешно отправлен в ветку $BRANCH репозитория $GIT_REMOTE"
else
    echo "Нет изменений для коммита."
fi