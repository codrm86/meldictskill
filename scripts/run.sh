#!/bin/bash

# Убедитесь, что имя виртуального окружения указано правильно
SKILL_DIR=$(dirname $(dirname $(realpath "$0")))
VENV_DIR="$SKILL_DIR/venv"  # Путь к директории виртуального окружения
SCRIPT_NAME="main"  # Имя Python-скрипта для запуска
REQUIREMENTS_FILE="$SKILL_DIR/requirements.txt"  # Файл с зависимостями
CREATE_VENV=false  # Флаг создания виртуального окружения

echo "Запуск скрипта: $0"
echo "Папка навыка:   $SKILL_DIR"

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
  echo "Удаление предыдущего виртуального окружения: $VENV_DIR"
  rm -rf "$VENV_DIR"
  echo "Создание виртуального окружения: $VENV_DIR"
  python3.12 -m venv "$VENV_DIR"

  if [ $? -ne 0 ]; then
    echo "Ошибка ($?): не удалось создать виртуальное окружение."
    exit 1
  fi

  # Проверяем наличие файла requirements.txt
  if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "Ошибка: файл $REQUIREMENTS_FILE не найден."
    exit 1
  fi

  # Устанавливаем зависимости из requirements.txt
  echo "Установка зависимостей из $REQUIREMENTS_FILE..."
  $VENV_DIR/bin/pip3.12 install -r "$REQUIREMENTS_FILE"

  # Проверяем, успешно ли установлены зависимости
  if [ $? -ne 0 ]; then
    echo "Ошибка  ($?): не удалось установить зависимости из $REQUIREMENTS_FILE."
    exit 1
  fi
else
  # Проверьте, существует ли виртуальное окружение
  if [ ! -d "$VENV_DIR" ]; then
    echo "Ошибка ($?): виртуальное окружение не найдено в директории $VENV_DIR"
    exit 1
  fi

  # Активируем виртуальное окружение
  echo "Активация виртуального окружения: $VENV_DIR/bin/activate"
  source "$VENV_DIR/bin/activate"

  # Проверяем, успешно ли активировалось окружение
  if [ $? -ne 0 ]; then
    echo "Ошибка ($?): не удалось активировать виртуальное окружение."
    exit 1
  fi

  # Запускаем Python-скрипт
  echo "Запуск Python-скрипта: $SCRIPT_NAME"
  cd $SKILL_DIR
  $VENV_DIR/bin/python3.12 -m $SCRIPT_NAME

  if [ $? -eq 0 ]; then
    echo "Python-скрипт успешно выполнен."
  else
    echo "Ошибка при выполнении Python-скрипта ($?)."
  fi

  # Деактивируем виртуальное окружение
  echo "Деактивация виртуального окружения: $VENV_DIR"
  deactivate
fi