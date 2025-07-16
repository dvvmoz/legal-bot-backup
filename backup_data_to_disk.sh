#!/bin/bash

# === Настройки ===
SRC_DIR="/opt/legal-bot"
BACKUP_DIR="$SRC_DIR/backups"
DATE=$(date +%Y%m%d-%H%M)
ARCHIVE_NAME="legal-bot-backup-$DATE.tar.gz"

# === Создать папку для бэкапов, если нет ===
mkdir -p "$BACKUP_DIR"

# === Перейти в папку проекта ===
cd "$SRC_DIR" || { echo "Нет папки $SRC_DIR"; exit 1; }

# === Создать архив с нужными папками и файлами ===
tar -czvf "$BACKUP_DIR/$ARCHIVE_NAME" data db models logs .env

echo "Бэкап данных сохранён: $BACKUP_DIR/$ARCHIVE_NAME"