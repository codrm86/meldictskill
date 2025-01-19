from aiohttp import web
from types import SimpleNamespace as dynamic
from aliceio.webhook.aiohttp_server import OneSkillAiohttpRequestHandler, setup_application
from aliceio.types import FSInputFile
from aliceio import Skill
from myconstants import *
from config import Config, start_config_watcher
from watchdog.observers.api import BaseObserver
import os
import pandas as pd
import asyncio
import ssl
import logging
import meldicthandlers as md
from myconstants import *

def configure_logger() -> logging.Logger:
    # Создаем объект логгера
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Создаем обработчик для записи лога в файл
    file_handler = logging.FileHandler("meldict_skill.log", encoding=UTF8)
    file_handler.setLevel(logging.INFO)

    # Форматирование логов
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%d.%m.%Y %H:%M:%S")
    file_handler.setFormatter(formatter)

    # Добавляем обработчик к логгеру
    logger.addHandler(file_handler)
    return logger


async def upload_websounds(skill: Skill):
    config = Config()

    if config.data.upload_websounds != True:
        # logger.info(f"Пропуск удаления и загрузки звуков в навык.")
        return

    count = 0

    # удаляем все ранее загруженные звуки
    logging.info("Получение списка ранее загруженных в навык звуков и их удаление")
    pre_sounds = await skill.get_sounds()
    for web_sound in pre_sounds.sounds:
        try:
            await skill.delete_sound(web_sound.id)
            count += 1
            logging.info(f"Звук удалён {web_sound.id}")
        except Exception as e:
            logging.error(f"Ошибка удаления звука {web_sound.id}.", exc_info=e)
            continue

    logging.info(f"Всего звуков удалено: {count}")

    websounds = pd.DataFrame(columns=["file_name", "cloud_id"])
    count = 0

    # загружаем все звуки из папки sounds
    logging.info(f"Загрузка звуков в облачное хранилище навыка")
    websounds_folder = config.data.websounds_folder
    for f in os.listdir(websounds_folder):
        try:
            sound_file = os.path.join(websounds_folder, f)
            logging.info(f"Загрузка звука {sound_file}")

            fsfile = FSInputFile(sound_file)
            result = await skill.upload_sound(fsfile)
            count += 1
            websounds.loc[len(websounds)] = [f.split(".")[0], result.sound.id]
            logging.info(f"Звук загружен {result}")
        except Exception as e:
            logging.warning(f"Ошибка загрузки звука {f}.", exc_info=e)
            continue

    logging.info(f"Всего звуков загружено: {count}")

    websounds_csv = config.data.websounds_csv
    logging.info(f"Сохранение загруженных звуков в {websounds_csv}")
    websounds.to_csv(websounds_csv, sep=SEP, encoding=UTF8, index=False)
    logging.info(f"Файл {websounds_csv} записан")

def main() -> None:
    observer: BaseObserver = None
    try:
        configure_logger()
        logging.info("*** Запуск навыка ***")

        config = Config.load(CONFIG_FILE)
        observer = start_config_watcher(CONFIG_FILE)

        logging.info(f"Skill-ID: {config.skill.id}, OAuth-Token: {config.skill.oauth_token}")

        skill = Skill(skill_id=config.skill.id, oauth_token=config.skill.oauth_token)
        asyncio.run(upload_websounds(skill))

        ssl_context = None
        if config.network.ssl.enabled:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(certfile=config.network.ssl.certfile, keyfile=config.network.ssl.keyfile)

        logging.info(f"Запуск HTTP-сервера: IP {config.network.ip}:{config.network.port}, URL \"{config.network.path}\"")
        app = web.Application()
        requests_handler = OneSkillAiohttpRequestHandler(dispatcher=md.dispatcher, skill=skill)
        requests_handler.register(app, path=f"/{config.network.path}")
        setup_application(app, md.dispatcher, skill=skill)
        web.run_app(app, host=config.network.ip, port=config.network.port, ssl_context=ssl_context)
    except Exception as e:
        logging.fatal("Необработанное исключение", exc_info=e)
    finally:
        if observer:
            observer.stop()
            observer.join()
        logging.info("*** Остановка навыка ***")

if __name__ == "__main__":
    main()
