from pydantic import BaseModel
import threading

# Потокобезопасный синглтон
class SingletonMeta(type):
    _instance = None
    _rlock = threading.RLock()

    def __call__(self, *args, new: bool = False, **kwargs):
        """Возвращает существующий экземпляр или создаёт новый."""
        with self._rlock:
            if self._instance is None or new or args or kwargs:
                # Если экземпляр ещё не создан, создаём с использованием аргументов
                self._instance = super().__call__(*args, **kwargs)
            return self._instance

class BaseModelSingletonMeta(type(BaseModel), SingletonMeta):
    pass