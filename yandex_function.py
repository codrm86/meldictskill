import logging
from typing import Any
from pythonjsonlogger import jsonlogger
from aliceio import Skill
from aliceio.webhook.yandex_functions import OneSkillYandexFunctionsRequestHandler, RuntimeContext
from engine.alice.alice_handlers import dispatcher
from config import Config
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

configure_logger().info("*** Запуск навыка ***")
config = Config.load_default()

skill = Skill(skill_id=config.skill.id, oauth_token=config.skill.oauth_token)
requests_handler = OneSkillYandexFunctionsRequestHandler(dispatcher, skill)

async def handler(event: dict[str, Any], context: RuntimeContext) -> Any:
    return await requests_handler(event, context)
