from typing import Optional, TypeVar, Generic, ClassVar
from pydantic import RootModel, BaseModel, Field
from collections.abc import Callable
from myconstants import *
from singleton import SingletonMeta
import random
import logging
import json

T = TypeVar('T')

class RandomCollection(RootModel[list[T]], Generic[T]):
    root: list[T]

    def rnd(self) -> T:
        return random.choice(self.root) \
            if isinstance(self.root, list) and len(self.root) > 0 else None

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, index):
        return self.root[index] if isinstance(self.root, list) else None
    
    def __call__(self):
        return self.rnd()

class TextTTS(BaseModel):
    text: str = Field()
    original_tts: Optional[str] = Field(default=None, alias="tts")

    @property
    def tts(self) -> str:
        return self.original_tts if isinstance(self.original_tts, str) and len(self.original_tts) > 0 else self.text

    def __getitem__(self, index) -> str:
        if index == 0: return self.text
        if index == 1: return self.tts
        raise IndexError()

    def __iter__(self):
        return iter((self.text, self.tts))

    def __call__(self):
        return self.text, self.tts


class Format(TextTTS):
    arguments: Optional[dict[str, dict[str, TextTTS]]]  = Field(default_factory=lambda: dict())

    def __format(self, tts: bool, **kwargs):
        source = self.tts if tts else self.text

        if not isinstance(source, str): return None
        if len(source) == 0: return ""

        for key, value in kwargs.items():
            arg = self.arguments.get(key)
            arg_value = None

            if arg:
                arg_value = arg.get(str(value), value)
            else:
                if not isinstance(value, TextTTS):
                    if isinstance(value, Callable):
                        value = value(tts)
                        kwargs[key] = value
                    continue
                arg_value = value

            kwargs[key] = arg_value.tts if tts else arg_value.text

        return source.format(**kwargs) if len(kwargs) else source

    def __call__(self, **kwargs) -> tuple[str, str]:
        text = self.__format(False, **kwargs)
        tts = self.__format(True, **kwargs)
        return text, tts if tts else text


class TextTTSRndCollection(RandomCollection[TextTTS]):
    Default: ClassVar[TextTTS] = TextTTS(text="")

    def rnd(self) -> TextTTS:
        return random.choice(self.root) \
            if isinstance(self.root, list) and len(self.root) > 0 else TextTTSRndCollection.Default

    def __getitem__(self, index) -> TextTTS:
        return self.root[index] if isinstance(self.root, list) else TextTTSRndCollection.Default
    
    def __call__(self) -> TextTTS:
        return self.rnd()

class FormatRndCollection(RandomCollection[Format]):
    Default: ClassVar[Format] = Format(text="")

    def rnd(self) -> Format:
        return random.choice(self.root) \
            if isinstance(self.root, list) and len(self.root) > 0 else FormatRndCollection.Default

    def __getitem__(self, index) -> Format:
        return self.root[index] if isinstance(self.root, list) else FormatRndCollection.Default
    
    def __call__(self) -> Format:
        return self.rnd()

class Greetings(BaseModel):
    initial_run: Format = Field(default_factory=lambda: Format(text=""))
    first_run: Format = Field()
    second_run: Optional[Format] = Field(default_factory=lambda: Format(text=""))

    def __call__(self, initial_run: bool = False, first_run: bool = False):
        return self.initial_run if initial_run \
            else self.first_run if first_run \
            else self.second_run


class Replies(BaseModel):
    greetings: Greetings = Field()


class RootLevel(BaseModel):
    dont_understand: TextTTSRndCollection = Field()
    something_went_wrong: TextTTSRndCollection = Field()
    byebye: TextTTSRndCollection = Field()
    hamster_on: TextTTSRndCollection = Field()
    hamster_off: TextTTSRndCollection = Field()
    no_way_back: TextTTSRndCollection = Field()
    rights: TextTTSRndCollection = Field()
    wrongs: TextTTSRndCollection= Field()


class MenuLevel(Replies):
    train_menu: Format = Field()
    rules: TextTTS = Field()


class GameLevel(Replies):
    name: TextTTS = Field()
    tasks: FormatRndCollection = Field()
    questions: FormatRndCollection = Field()
    answers: FormatRndCollection = Field()
    whats: FormatRndCollection = Field()
    continues: FormatRndCollection = Field()


class GameLevels(BaseModel):
    demo: GameLevel = Field()
    missed_note: GameLevel = Field()
    prima_location: GameLevel = Field()
    cadence: GameLevel = Field()
    exam: GameLevel = Field()


class VoiceMenu(BaseModel, metaclass=SingletonMeta):
    root: RootLevel = Field()
    main_menu: MenuLevel = Field()
    levels: GameLevels = Field()

    @classmethod
    def load(cls, config_path: str):
        """Загружает и валидирует голосовое меню из JSON-файла."""
        try:
            logging.info("Загрузка голосового меню")
            config_data = None

            with open(config_path, "r", encoding=UTF8) as file:
                config_data = json.load(file)

            config = cls(**config_data)
            logging.info("Голосовое меню загружено")

            return config
        except Exception as e:
            logging.error("Ошибка загрузки голосового меню", exc_info=e)
            raise