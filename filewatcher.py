import os
import logging
from collections.abc import Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


# Обработчик событий для Watchdog
class ModifiedHandler(FileSystemEventHandler):
    def __init__(self, config_path: str, callback: Callable[[str], None]):
        assert config_path
        assert callback
        self.config_path = os.path.abspath(config_path)
        self.__callback = callback

    def on_modified(self, event):
        if os.path.abspath(event.src_path) == self.config_path:
            try:
                logging.info(f"Обнаружено изменение {self.config_path}")
                self.__callback(self.config_path)
            except:
                pass

def start_file_watcher(config_path: str, callback: Callable[[str], None]):
    """Запускает наблюдателя для отслеживания изменений файла."""
    event_handler = ModifiedHandler(config_path, callback)
    observer = Observer()
    folder_path = os.path.dirname(event_handler.config_path)
    observer.schedule(event_handler, path=folder_path, recursive=False)
    observer.start()
    logging.info(f"Запущено наблюдение за изменениями {event_handler.config_path}")
    return observer