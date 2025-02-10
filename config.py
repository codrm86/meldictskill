from pydantic import BaseModel, Field
import json
import os
import logging
from myconstants import *
from singleton import BaseModelSingletonMeta
from filewatcher import *

# Pydantic модели конфигов
class SSLConfig(BaseModel):
    enabled: bool = Field(False, description="Включить или отключить SSL")
    certfile: str = Field("", description="Путь к файлу сертификата SSL")
    keyfile: str = Field("", description="Путь к файлу ключа SSL")

class NetworkConfig(BaseModel):
    ip: str = Field("127.0.0.1", description="IP-адрес для привязки")
    port: int = Field(5000, description="Номер порта")
    path: str = Field("/meldict", description="URL путь")
    ssl: SSLConfig = Field(default_factory=SSLConfig, description="Настройки SSL")

class DataConfig(BaseModel):
    upload_websounds: bool = Field(False, description="Флаг, указывающий на необходимость генерации и загрузки звуков в облачное хранилище навыка при запуске сервера")
    websounds_folder: str = Field("data/sounds", description="Папка со звуковыми файлами")
    websounds_db: str = Field("data/websounds.csv", description="CSV-файл с облачными идентификаторами загруженных звуков")
    sound_font: str = Field("data/default_sound_font.sf2", description="Библиотека MIDI-сэмплов по умолчанию для синтеза звуков")
    main_db: str = Field("data/main.csv", description="Основной CSV-файл с аккордами и интервалами")
    tts_db: str = Field("data/tts.csv", description="CSV-файл со словами в TTS-разметке")
    voice_menu: str = Field("voice_menu.json", description="JSON-файл голосового меню")

class SkillConfig(BaseModel):
    id: str = Field("", description="Идентификатор навыка")
    oauth_token: str = Field("", description="OAuth токен для навыка")

class DebugConfig(BaseModel):
    enabled: bool = Field(False, description="Включить или отключить режим отладки")

class Config(BaseModel, metaclass=BaseModelSingletonMeta):
    """Основной класс конфигурации."""
    network: NetworkConfig = Field(default_factory=NetworkConfig, description="Настройки сети")
    data: DataConfig = Field(default_factory=DataConfig, description="Настройки данных")
    skill: SkillConfig = Field(default_factory=SkillConfig, description="Информация о навыке Алисы")
    debug: DebugConfig = Field(default_factory=DebugConfig, description="Настройки отладки")

    @classmethod
    def load(cls, config_path: str):
        """Загружает и валидирует конфигурацию из JSON-файла."""
        try:
            logging.info("Загрузка конфигурации")
            config_data = None

            with open(config_path, "r", encoding=UTF8) as file:
                config_data = json.load(file)

            config = cls(**config_data)
            logging.info("Конфигурация загружена")

            return config
        except Exception as e:
            logging.error("Конфигурация не загружена", exc_info=e)
            raise e

