import logging
from typing import Any
from pythonjsonlogger import jsonlogger
from aliceio import Skill
from aliceio.webhook.yandex_functions import OneSkillYandexFunctionsRequestHandler, RuntimeContext
import meldicthandlers as md
from config import Config, start_config_watcher
from myconstants import *

class YcLoggingFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(YcLoggingFormatter, self).add_fields(log_record, record, message_dict)
        log_record["logger"] = record.name
        log_record["level"] = str.replace(str.replace(record.levelname, "WARNING", "WARN"), "CRITICAL", "FATAL")


def configure_logger() -> logging.Logger:
    logHandler = logging.StreamHandler()
    logHandler.setFormatter(YcLoggingFormatter('[%(asctime)s] %(levelname)s: %(message)s'))

    logger = logging.getLogger()
    logger.propagate = False
    logger.addHandler(logHandler)
    logger.setLevel(logging.INFO)
    return logger

configure_logger().info("*** Запуск навыка из Яндекс-функции ***")
config = Config.load(CONFIG_FILE)
start_config_watcher(CONFIG_FILE)

skill = Skill(skill_id=config.skill.id, oauth_token=config.skill.oauth_token)
requests_handler = OneSkillYandexFunctionsRequestHandler(md.dispatcher, skill)

async def handler(event: dict[str, Any], context: RuntimeContext) -> Any:
    return await requests_handler(event, context)
