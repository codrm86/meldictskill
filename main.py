import sys
import logging.config
import logging.handlers
import os
import ssl
import logging
from aiohttp import web
from aliceio.webhook.aiohttp_server import OneSkillAiohttpRequestHandler, setup_application
from aliceio import Skill
from watchdog.observers.api import BaseObserver
from filewatcher import start_file_watcher
from config import Config
from voicemenu import VoiceMenu
from engine.maindb import MainDB
from chordgen import generate_audio
from engine.alice.alice_handlers import dispatcher
from myconstants import *
from abspath import abs_path

def configure_logger() -> logging.Logger:
    # Создаем объект логгера
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Форматирование логов
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%d.%m.%Y %H:%M:%S")

    # Создаем обработчик для записи лога в файл
    os.makedirs(abs_path("logs"), exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(abs_path("logs/skill.log"), maxBytes=1024 * 1024, backupCount=5, encoding=UTF8)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Создаем обработчик для записи лога в консоль
    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(formatter)
    logger.addHandler(consoleHandler)

    return logger


def generate_sounds():
    config = Config()

    # генерируем отсутствующие звуки
    os.makedirs(abs_path(config.data.websounds_folder), exist_ok=True)
    count = 0

    for noteseq in MainDB():
        try:
            logging.info(f"Генерация аудио для {noteseq}")
            if generate_audio(noteseq, replace_existing=False):
                count += 1
                logging.info(f"Аудио для {noteseq} сгенерировано")
        except Exception as e:
            logging.error(f"Ошибка во время генерации аудио для {noteseq}", exc_info=e)
            continue

    if count > 0:
        logging.info(f"Всего аудиофайлов сгенерировано: {count}")


def main() -> None:
    cfg_watcher: BaseObserver = None
    vm_watcher: BaseObserver = None
    main_watcher: BaseObserver = None

    try:
        # Настройка логгера
        configure_logger()

        logging.info("*** Запуск сервера Музыкального Диктанта ***")

        # Загрузка конфига (должна выполняться следующей после логгера)
        config = Config.load_default()
        cfg_watcher = start_file_watcher(config.file, Config.load)

        # Загрузка голосового меню
        vm = VoiceMenu.load(abs_path(config.data.voice_menu))
        vm_watcher = start_file_watcher(vm.file, VoiceMenu.load)

        # Загрузка базы данных трезвучий
        maindb = MainDB.load()
        main_watcher = start_file_watcher(maindb.file, lambda _: MainDB.load())

        # Генерация звуков
        if config.data.upload_websounds:
            generate_sounds()

        # Создание экземпляра навыка Алисы
        # oauth-token resolve information: https://yandex.ru/dev/dialogs/alice/doc/ru/resource-upload#auth
        logging.info(f"Alice Skill-ID: {config.skill.id}, OAuth-Token: {config.skill.oauth_token}")
        skill = Skill(skill_id=config.skill.id, oauth_token=config.skill.oauth_token)

        logging.info(f"Запуск HTTP-сервера: http{'s' if config.network.ssl.enabled else ''}://{config.network.ip}:{config.network.port}/{config.network.path}")

        # Настраиваем SSL на сервере
        ssl_context = None
        if config.network.ssl.enabled:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(certfile=config.network.ssl.certfile, keyfile=config.network.ssl.keyfile)

        app = web.Application()
        requests_handler = OneSkillAiohttpRequestHandler(dispatcher=dispatcher, skill=skill)
        requests_handler.register(app, path=f"/{config.network.path}")
        setup_application(app, dispatcher, skill=skill)

        # запускаем прослушивание порта по указанному ip
        web.run_app(app, host=config.network.ip, port=config.network.port, ssl_context=ssl_context)
    except Exception as e:
        logging.fatal("Необработанное исключение", exc_info=e)
        raise e
    finally:
        if cfg_watcher:
            cfg_watcher.stop()
            cfg_watcher.join()
        if main_watcher:
            main_watcher.stop()
            main_watcher.join()
        if vm_watcher:
            vm_watcher.stop()
            vm_watcher.join()
        logging.info("*** Остановка сервера ***")

if __name__ == "__main__":
    main()