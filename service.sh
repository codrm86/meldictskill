#!/bin/bash

SERVICE_NAME="meldict"
DEFAULT_SCRIPT_PATH="$PWD/run.sh"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

# Функция отображения справочной информации
show_help() {
  echo "Использование: $0 [опции]"
  echo "Опции:"
  echo "  --script <path>   Указать путь к файлу запуска сервера (по умолчанию: $DEFAULT_SCRIPT_PATH)"
  echo "  --create          Создать службу systemd для сервера"
  echo "  --start           Запустить службу"
  echo "  --stop            Остановить службу"
  echo "  --restart         Перезапустить службу"
  echo "  --remove          Удалить службу"
  echo "  --help            Показать эту справочную информацию"
}

# Функция создания службы
create_service() {
  if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Ошибка: Файл $SCRIPT_PATH не найден. Убедитесь, что путь указан правильно."
    exit 1
  fi
  echo "Создание службы..."
  sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=MelDict Server Service
After=network.target

[Service]
ExecStart=/bin/bash $SCRIPT_PATH
Restart=always
User=$(whoami)
WorkingDirectory=$(dirname "$SCRIPT_PATH")
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOL

  sudo chmod 644 $SERVICE_FILE
  sudo chmod +x $SCRIPT_PATH
  sudo systemctl daemon-reload
  sudo systemctl enable $SERVICE_NAME
  echo "Служба создана."
}

# Функция запуска службы
start_service() {
  echo "Запуск службы..."
  sudo systemctl start $SERVICE_NAME
  echo "Служба запущена."
}

# Функция остановки службы
stop_service() {
  echo "Остановка службы..."
  sudo systemctl stop $SERVICE_NAME
  echo "Служба остановлена."
}

# Функция перезапуска службы
restart_service() {
  echo "Перезапуск службы..."
  sudo systemctl restart $SERVICE_NAME
  echo "Служба перезапущена."
}

# Функция удаления службы
remove_service() {
  echo "Удаление службы..."
  sudo systemctl stop $SERVICE_NAME
  sudo systemctl disable $SERVICE_NAME
  sudo rm -f $SERVICE_FILE
  sudo systemctl daemon-reload
  echo "Служба удалена."
}

# если скрипт запущен без аргументов, показываем справку и выходим
if [ $# -eq 0 ]; then
  show_help
  exit 0
fi

# Разбор аргументов
SCRIPT_PATH="$DEFAULT_SCRIPT_PATH"
while [[ $# -gt 0 ]]; do
  case $1 in
    # --script)
    #   SCRIPT_PATH="$2"
    #   shift 2
    #   ;;
    --create)
      create_service
      shift
      ;;
    --start)
      start_service
      shift
      ;;
    --stop)
      stop_service
      shift
      ;;
    --restart)
      restart_service
      shift
      ;;
    --remove)
      remove_service
      shift
      ;;
    --help)
      show_help
      exit 0
      ;;
    *)
      echo "Неизвестный аргумент: $1"
      show_help
      exit 1
      ;;
  esac
done
