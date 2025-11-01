import threading
from aliceio.types import Message, TextButton
from aliceio.types.number_entity import NumberEntity
from abc import ABC, abstractmethod
from typing import Iterable
from engine.meldictenginebase import MelDictEngineBase
from voicemenu import VoiceMenu, GameLevel
from myconstants import *

class NoReplyError(ValueError):
    def __init__(self, msg: str = "Нет реплики"):
        super().__init__(msg)

class MelDictLevelBase(ABC):
    MAX_TASK_COUNT = 9
    _rlock: threading.RLock

    def __init__(self, engine: MelDictEngineBase, first_run: bool = True):
        super().__init__()
        assert engine
        self.__engine = engine
        self.__show_right = True
        self.__correct_score = 0
        self.__incorrect_score = 0
        self._first_run = first_run
        self._rlock = threading.RLock()

    @property
    @abstractmethod
    def id(self) -> int: pass

    @property
    def name(self) -> str: return self.game_level.name.text

    @property
    def tts_name(self) -> str: return self.game_level.name.tts

    @property
    @abstractmethod
    def game_level(self) -> GameLevel: pass

    @property
    def engine(self): return self.__engine

    @property
    def show_right(self): return self.__show_right
    @show_right.setter
    def show_right(self, value: bool): self.__show_right = value

    @property
    def correct_score(self): return self.__correct_score
    @correct_score.setter
    def correct_score(self, value: int):
        with self._rlock:
            self.__correct_score = max(0, value)

    @property
    def incorrect_score(self): return self.__incorrect_score
    @incorrect_score.setter
    def incorrect_score(self, value: int):
        with self._rlock:
            self.__incorrect_score = max(0, value)

    @property
    def total_score(self) -> int: return self.correct_score + self.incorrect_score

    @property
    def started(self): return self.total_score > 0

    @property
    def finished(self): return self.total_score >= MelDictLevelBase.MAX_TASK_COUNT

    def reset(self):
        with self._rlock:
            self.__correct_score = self.__incorrect_score = 0
            self._reset_secrets()

    def get_stats_reply(self, format_name: bool = True) -> tuple[str, str]:
        mode_reply = "На уровне «{0}» отвечено" if format_name else ""
        correct_reply = "на {0} {1} правильно".format(self.correct_score, MelDictLevelBase._decline_question(self.correct_score))
        incorrect_reply = "и на {0} неправильно".format(self.incorrect_score) \
            if self.incorrect_score > 0 else ""

        text = self.engine.format_text(
            mode_reply.format(self.name),
            correct_reply, incorrect_reply)

        tts = self.engine.format_tts(
            mode_reply.format(self.tts_name),
            correct_reply, incorrect_reply)

        return text, tts

    def get_reply(self) -> tuple[str, str]:
        with self._rlock:
            return self._get_reply() if not self.finished else (None, None)

    @abstractmethod
    def _get_reply(self) -> tuple[str, str]:
        pass

    def process_user_reply(self, message: Message = None, button: TextButton = None) -> tuple[str, str]:
        assert message or button
        with self._rlock:
            return self._process_user_reply(message, button) if not self.finished else (None, None)

    @abstractmethod
    def _process_user_reply(self, message: Message, button: TextButton) -> tuple[str, str]:
        pass

    def _select_start_reply(self, self_game_level: GameLevel = None) -> tuple[str, str]:
        self_game_level = self_game_level if self_game_level else self.game_level

        first_run = self._reset_first_run()
        greet = self_game_level.greetings(first_run=first_run)

        return greet() if first_run or not self.started else (None, None)

    def _reset_first_run(self) -> bool:
        first_run, self._first_run = self._first_run, False
        return first_run

    @abstractmethod
    def _reset_secrets(self):
        pass

    def get_buttons(self) -> Iterable[TextButton]:
        pass

    def _create_button(self, title: str, value: str | int) -> TextButton:
        if not isinstance(value, str) and not isinstance(value, int):
            return None

        return TextButton(title=title if isinstance(title, str) and title != "" \
                          else str(value), payload={ "value": value })

    def _get_last_number(self, message: Message, button: TextButton) -> int:
        if message:
            for en in reversed(message.nlu.entities):
                if isinstance(en.value, NumberEntity):
                    return int(en.value)
        elif button and button.payload:
            value = button.payload.get("value")
            if value: return int(value)

        return None
    
    def _get_value(self, message: Message, button: TextButton) -> str | int:
        if message: return message.command
        if button and button.payload: return button.payload.get("value")
        return None

    def _format_correct(self, text: str = "", tts: str = "") -> tuple[str, str]: # text, tts
        right_text, right_tts = VoiceMenu().root.rights()
        return self.engine.format_text(right_text, text), self.engine.format_tts(right_tts, tts)

    def _format_incorrect(self, text: str = "", tts: str = "") -> tuple[str, str]: # text, tts
        wrong_text, wrong_tts = VoiceMenu().root.wrongs()
        return self.engine.format_text(wrong_text, text), self.engine.format_tts(wrong_tts, tts)

    @staticmethod
    def _decline_number(count: int, singular: str, plural: str, number_234: str = None) -> str:
        mod100 = abs(count) % 100
        if mod100 < 10 or mod100 > 20:
            mod10 = abs(count) % 10
            match mod10: # last digit from int
                case 1: return singular
                case 2 | 3 | 4: return number_234
        return plural

    @staticmethod
    def _decline_question(count: int) -> str:
        return MelDictLevelBase._decline_number(count, "вопрос", "вопросов", "вопроса")