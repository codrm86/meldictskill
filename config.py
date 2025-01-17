from pydantic import BaseModel, Field
import json
import threading
import os
import logging
from myconstants import *
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Потокобезопасный синглтон для конфигурации
class SingletonMeta(type(BaseModel)):
    _instance = None
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        """Возвращает существующий экземпляр или создаёт новый."""
        with cls._lock:
            if cls._instance is None or args or kwargs:
                # Если экземпляр ещё не создан, создаём с использованием аргументов
                cls._instance = super().__call__(*args, **kwargs)
            return cls._instance

# Pydantic модели для конфигурации
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
    upload_websounds: bool = Field(False, description="Разрешить загрузку звуков")
    websounds_folder: str = Field("sounds", description="Папка для звуков")
    websounds_csv: str = Field("websounds.csv", description="CSV-файл для звуков")
    main_csv: str = Field("main.csv", description="Основной CSV-файл")

class SkillConfig(BaseModel):
    id: str = Field("", description="Идентификатор навыка")
    oauth_token: str = Field("", description="OAuth токен для навыка")

class DebugConfig(BaseModel):
    enabled: bool = Field(False, description="Включить или отключить режим отладки")

class Config(BaseModel, metaclass=SingletonMeta):
    """Основной класс конфигурации."""
    network: NetworkConfig = Field(default_factory=NetworkConfig, description="Настройки сети")
    data: DataConfig = Field(default_factory=DataConfig, description="Настройки данных")
    skill: SkillConfig = Field(default_factory=SkillConfig, description="Информация о навыке Алисы")
    debug: DebugConfig = Field(default_factory=DebugConfig, description="Настройки отладки")

    @classmethod
    def load(cls, config_path: str):
        """Загружает и валидирует конфигурацию из JSON-файла."""
        logging.info("Загрузка конфигурации")
        config_data = None
        with open(config_path, "r", encoding=UTF8) as file:
            config_data = json.load(file)
        return cls(**config_data)

# Обработчик событий для Watchdog
class ConfigHandler(FileSystemEventHandler):
    def __init__(self, config_path: str):
        self.config_path = os.path.abspath(config_path)

    def on_modified(self, event):
        if os.path.abspath(event.src_path) == self.config_path:
            logging.info(f"Обнаружено изменение {self.config_path}")
            try:
                Config.load(self.config_path)
            except Exception as e:
                logging.error(f"Ошибка при перезагрузке конфигурации", exc_info=e)

# Функция для запуска наблюдателя
def start_config_watcher(config_path: str):
    """Запускает наблюдателя для отслеживания изменений конфигурационного файла."""
    event_handler = ConfigHandler(config_path)
    observer = Observer()
    folder_path = os.path.dirname(event_handler.config_path)
    observer.schedule(event_handler, path=folder_path, recursive=False)
    observer.start()
    logging.info(f"Запущено наблюдение за изменениями {config_path}")
    return observer
