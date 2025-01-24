from pydantic import BaseModel, Field
import threading

# Потокобезопасный синглтон
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