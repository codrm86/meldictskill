#!/bin/bash

# Убедитесь, что имя виртуального окружения указано правильно
VENV_DIR=".venv"  # Путь к директории виртуального окружения
SCRIPT_NAME="main.py"  # Имя Python-скрипта для запуска
REQUIREMENTS_FILE="requirements.txt"  # Файл с зависимостями
CREATE_VENV=false  # Флаг создания виртуального окружения

# Разбор аргументов
for arg in "$@"
do
  case $arg in
    --create_venv)
      CREATE_VENV=true
      shift
      ;;
    *)
      echo "Неизвестный аргумент: $1"
      exit 1
      ;;
  esac
done

# Проверка наличия Python 3.12
if ! command -v python3.12 &> /dev/null; then
  echo "Ошибка: Python 3.12 не найден. Установите Python 3.12 перед запуском."
  exit 1
fi

# Проверка и создание/пересоздание виртуального окружения
if [ "$CREATE_VENV" = true ]; then
  echo "Создание виртуального окружения..."
  rm -rf "$VENV_DIR"
  python3.12 -m venv "$VENV_DIR"
  if [ $? -ne 0 ]; then
    echo "Ошибка: не удалось создать виртуальное окружение."
    exit 1
  fi
fi

# Проверьте, существует ли виртуальное окружение
if [ ! -d "$VENV_DIR" ]; then
  echo "Ошибка: виртуальное окружение не найдено в директории $VENV_DIR"
  exit 1
fi

# Активируем виртуальное окружение
source "$VENV_DIR/bin/activate"

# Проверяем, успешно ли активировалось окружение
if [ $? -ne 0 ]; then
  echo "Ошибка: не удалось активировать виртуальное окружение."
  exit 1
fi

# Проверяем наличие файла requirements.txt
if [ ! -f "$REQUIREMENTS_FILE" ]; then
  echo "Ошибка: файл $REQUIREMENTS_FILE не найден."
  deactivate
  exit 1
fi

# Устанавливаем зависимости из requirements.txt
$VENV_DIR/bin/pip3.12 install -r "$REQUIREMENTS_FILE"

# Проверяем, успешно ли установлены зависимости
if [ $? -ne 0 ]; then
  echo "Ошибка: не удалось установить зависимости из $REQUIREMENTS_FILE."
  deactivate
  exit 1
fi

if [ "$CREATE_VENV" = false ]; then
  # Запускаем Python-скрипт
  $VENV_DIR/bin/python3.12 "$SCRIPT_NAME"

  if [ $? -eq 0 ]; then
    echo "Скрипт успешно выполнен."
  else
    echo "Ошибка при выполнении скрипта."
  fi
fi

# Деактивируем виртуальное окружение
deactivate