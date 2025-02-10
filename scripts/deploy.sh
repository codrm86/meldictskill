#!/bin/bash

chmod +x ./*.sh

./create_cert.sh
if [ $? -ne 0 ]; then
  echo "Ошибка при создании сертификатов."
  exit 1
fi

./run.sh --create_venv
if [ $? -ne 0 ]; then
  echo "Ошибка при создании виртуального окружения."
  exit 1
fi

./service.sh --create
if [ $? -ne 0 ]; then
  echo "Ошибка при создании службы."
  exit 1
fi

./service.sh --start
if [ $? -ne 0 ]; then
  echo "Ошибка при запуске службы."
  exit 1
fi

echo "Развертывание завершено успешно."
