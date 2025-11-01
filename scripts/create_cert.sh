#!/bin/bash

# Путь к файлу конфигурации
SKILL_DIR=$(dirname $(dirname $(realpath "$0")))  # Путь к директории навыка
CONFIG_FILE="$SKILL_DIR/config.json"

echo "Запуск скрипта:    $0"
echo "Папка навыка:      $SKILL_DIR"
echo "Файл конфигурации: $CONFIG_FILE"

# Проверка существования файла конфигурации
if [ ! -f "$CONFIG_FILE" ]; then
  echo "Ошибка: Файл конфигурации $CONFIG_FILE не найден."
  exit 1
fi

# Проверка, установлен ли jq
if ! command -v jq &> /dev/null; then
  echo "Ошибка: jq не установлен. Установите его с помощью 'sudo apt install jq'."
  exit 1
fi

# Получение внешнего IP, либо чтение из JSON-файла
IP=$(curl -s ifconfig.me || jq -r '.network.ip' "$CONFIG_FILE")
if [ -z "$IP" ]; then
  echo "Ошибка: не удалось получить IP-адрес."
  exit 1
fi
# Запись IP-адреса в конфиг-файл
jq --arg ip "$IP" '.network.ip = $ip' "$CONFIG_FILE" > tmp.$$.json && mv tmp.$$.json "$CONFIG_FILE"
# Запись флага включения SSL в конфиг-файл
jq '.network.ssl.enabled = true' "$CONFIG_FILE" > tmp.$$.json && mv tmp.$$.json "$CONFIG_FILE"


# Получение имён файлов сертификатов сертификатов из конфига
CERTFILE="$SKILL_DIR/$(jq -r '.network.ssl.certfile' "$CONFIG_FILE")"
KEYFILE="$SKILL_DIR/$(jq -r '.network.ssl.keyfile' "$CONFIG_FILE")"

if [ -z "$CERTFILE" ] || [ -z "$KEYFILE" ]; then
  echo "Ошибка: Не указаны пути к сертификату и ключу в конфигурации."
  exit 1
fi

# Генерация SSL-сертификатов
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$KEYFILE" \
  -out "$CERTFILE" \
  -subj "/C=RU/ST=Astrakhan Oblast/L=Astrakhan/O=Team 2/CN=$IP"

if [ $? -eq 0 ]; then
  echo "Сертификаты успешно созданы:"
  echo "Сертификат: $CERTFILE"
  echo "Приватный ключ: $KEYFILE"
else
  echo "Ошибка при создании сертификатов."
  exit 1
fi
