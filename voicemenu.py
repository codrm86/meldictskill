from typing import Optional, TypeVar, Generic, ClassVar
from pydantic import RootModel, BaseModel, Field
from collections.abc import Callable
from myconstants import *
from singleton import BaseModelSingletonMeta
from extended_formatter import ExtendedFormatter
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
    __formatter: ClassVar[ExtendedFormatter] = ExtendedFormatter()
    arguments: Optional[dict[str, dict[str, TextTTS]]] = Field(default_factory=lambda: dict())

    def _format(self, source: str, tts: bool, **kwargs):
        if not isinstance(source, str) or len(source) == 0:
            return ""

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

        return Format.__formatter.format(source, **kwargs) if len(kwargs) > 0 else source

    def format(self, **kwargs) -> tuple[str, str]:
        text = self._format(self.text, False, **kwargs)
        tts = self._format(self.tts, True, **kwargs)
        return text, tts if tts else text

    def __call__(self, **kwargs) -> tuple[str, str]:
        return self.format(**kwargs)


class FormatButton(Format):
    button: str = Field(default=None)

    def btn(self, **kwargs) -> str:
        text = self._format(self.button, False, **kwargs)
        return text


class TextTTSRndCollection(RandomCollection[TextTTS]):
    DEFAULT: ClassVar[TextTTS] = TextTTS(text="")

    def rnd(self) -> TextTTS:
        return random.choice(self.root) \
            if isinstance(self.root, list) and len(self.root) > 0 else TextTTSRndCollection.DEFAULT

    def __getitem__(self, index) -> TextTTS:
        return self.root[index] if isinstance(self.root, list) else TextTTSRndCollection.DEFAULT
    
    def __call__(self) -> TextTTS:
        return self.rnd()


class FormatRndCollection(RandomCollection[Format]):
    DEFAULT: ClassVar[Format] = Format(text="")

    def rnd(self) -> Format:
        return random.choice(self.root) \
            if isinstance(self.root, list) and len(self.root) > 0 else FormatRndCollection.DEFAULT

    def __getitem__(self, index) -> Format:
        return self.root[index] if isinstance(self.root, list) else FormatRndCollection.DEFAULT
    
    def __call__(self) -> Format:
        return self.rnd()


class FormatButtonRndCollection(RandomCollection[FormatButton]):
    DEFAULT: ClassVar[FormatButton] = FormatButton(text="")

    def rnd(self) -> FormatButton:
        return random.choice(self.root) \
            if isinstance(self.root, list) and len(self.root) > 0 else FormatButtonRndCollection.DEFAULT

    def __getitem__(self, index) -> FormatButton:
        return self.root[index] if isinstance(self.root, list) else FormatButtonRndCollection.DEFAULT
    
    def __call__(self) -> FormatButton:
        return self.rnd()


class Greetings(BaseModel):
    initial_run: Format = Field(default_factory=lambda: Format(text=""))
    first_run: Format = Field()
    second_run: Format = Field()

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
    no_score: TextTTSRndCollection = Field()
    level_not_scored: TextTTSRndCollection = Field()
    level_complete: TextTTSRndCollection = Field()
    exam_complete: TextTTSRndCollection = Field()
    no_way_back: TextTTSRndCollection = Field()
    rights: TextTTSRndCollection = Field()
    wrongs: TextTTSRndCollection= Field()


class MenuLevel(Replies):
    train_menu: FormatButton = Field()
    rules: FormatButton = Field()
    back: FormatButton = Field(default_factory=lambda: FormatButton(text="Назад", button="Назад"))


class GameLevel(Replies):
    name: TextTTS = Field()
    tasks: FormatRndCollection = Field()
    questions: FormatRndCollection = Field()
    answers: FormatButtonRndCollection = Field()
    whats: FormatRndCollection = Field()
    continues: FormatRndCollection = Field()


class GameLevels(BaseModel):
    demo: GameLevel = Field()
    missed_note: GameLevel = Field()
    prima_location: GameLevel = Field()
    cadence: GameLevel = Field()
    exam: GameLevel = Field()
    repeat_buttons: TextTTSRndCollection = Field(default_factory=lambda: TextTTS(text="Повторить"))


class VoiceMenu(BaseModel, metaclass=BaseModelSingletonMeta):
    root: RootLevel = Field()
    main_menu: MenuLevel = Field()
    levels: GameLevels = Field()

    @classmethod
    def load(cls, file_name: str):
        """Загружает и валидирует голосовое меню из JSON-файла."""
        assert file_name

        try:
            logging.info("Загрузка голосового меню")
            json_data = None

            with open(file_name, "r", encoding=UTF8) as file:
                json_data = json.load(file)

            cls(**json_data)
            logging.info("Голосовое меню загружено")
        except Exception as e:
            logging.error("Ошибка загрузки голосового меню", exc_info=e)
            raise e