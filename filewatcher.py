import os
import logging
from collections.abc import Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


# Обработчик событий для Watchdog
class ModifiedHandler(FileSystemEventHandler):
    def __init__(self, file_name: str, callback: Callable[[str], None]):
        assert file_name
        assert callback
        self.file_name = os.path.abspath(file_name)
        self.__callback = callback

    def on_modified(self, event):
        if os.path.abspath(event.src_path) == self.file_name:
            try:
                logging.info(f"Обнаружено изменение {self.file_name}")
                self.__callback(self.file_name)
            except:
                pass

def start_file_watcher(file_name: str, callback: Callable[[str], None]):
    """Запускает наблюдателя для отслеживания изменений файла."""
    event_handler = ModifiedHandler(file_name, callback)
    observer = Observer()
    folder_path = os.path.dirname(event_handler.file_name)
    observer.schedule(event_handler, path=folder_path, recursive=False)
    observer.start()
    logging.info(f"Запущено наблюдение за изменениями {event_handler.file_name}")
    return observer