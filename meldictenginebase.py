from typing import Callable
from musicnotesequence import *
from musicnote import *
from myfilters import *
from myconstants import *
from abc import ABC, abstractmethod

class MelDictEngineBase(ABC):
    def __init__(self, skill_id: str):
        assert skill_id and skill_id != ""
        self.__skill_id = skill_id
        self.__mode = GameMode.UNKNOWN

    @property
    def skill_id(self) -> str: return self.__skill_id

    @property
    def mode(self) -> int: return self.__mode

    @mode.setter
    def mode(self, value: int):
        assert self.mode >= GameMode.UNKNOWN and self.mode <= GameMode.TASK # allowed to set unknown
        self.__mode = value

    def _assert_mode(self):
        assert self.mode > GameMode.UNKNOWN and self.mode <= GameMode.TASK, "Режим не задан" # should not be unknown

    def reset(self):
        self.mode = GameMode.MENU

    @abstractmethod
    def get_reply(self) -> tuple[str, str]:
        pass

    @abstractmethod
    def process_user_reply(self, message: Message) -> tuple[str, str]:
        pass

    @abstractmethod
    def iter_note_sequences(self, predicate: Callable[[MusicNoteSequence], bool] = None) -> Iterable[MusicNoteSequence]:
        pass

    @abstractmethod
    def shuffle_note_sequences(self, predicate: Callable[[MusicNoteSequence], bool] = None) -> Iterable[MusicNoteSequence]:
        pass

    @abstractmethod
    def get_rnd_note_sequence(self, predicate: Callable[[MusicNoteSequence], bool] = None) -> MusicNoteSequence:
        pass

    @abstractmethod
    def get_audio_tag(self, nsf: str | MusicNoteSequence) -> str:
        pass
