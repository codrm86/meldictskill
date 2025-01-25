from typing import Callable
from aliceio.types import Message, TextButton
from musicnotesequence import *
from musicnote import *
from myfilters import *
from myconstants import *
from abc import ABC, abstractmethod

class MelDictEngineBase(ABC):
    def __init__(self, skill_id: str):
        assert skill_id and skill_id != ""
        self.__skill_id = skill_id
        self._mode = GameMode.UNKNOWN

    @property
    def skill_id(self) -> str: return self.__skill_id

    @property
    def mode(self) -> int: return self._mode

    @mode.setter
    def mode(self, value: int):
        self._mode = max(GameMode.UNKNOWN, value)

    def _assert_mode(self):
        assert self.mode >= GameMode.INIT, "Режим не задан" # should not be unknown

    @abstractmethod
    def get_stats_reply(self) -> tuple[str, str]:
        pass

    @abstractmethod
    def get_reply(self) -> tuple[str, str]:
        pass

    @abstractmethod
    def process_user_reply(self, message: Message = None, button: TextButton = None) -> tuple[str, str]:
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

    def format_text(self, *args: Iterable[str], sep = " ") -> str:
        return self.__format_text(False, *args, sep=sep)

    def __format_text(self, new_line: bool, *args: Iterable[str], sep = " ") -> str:
        text = ""

        for value in args:
            if value is None:
                continue
            if isinstance(value, str):
                pass # pass required
            elif isinstance(value, Iterable):
                value = self.__format_text(new_line, *value)
            else:
                value = str(value)

            if len(value) == 0:
                continue

            if not new_line and len(sep) > 0 and len(text) > 0 and value[0].isalnum():
                text += sep

            text += value
            new_line = value[-1] == "\n"

        return text

    def format_tts(self, *args: Iterable[str] | Iterable[MusicNoteSequence], sep = " ") -> str:
        return self.__format_tts(False, False, *args, sep=sep)[0]

    def __format_tts(self, new_line: bool, prev_tag: bool, *args: Iterable[str] | Iterable[MusicNoteSequence], sep = " ") \
        -> tuple[str, bool]:
        tts = ""
        for value in args:
            tag = False

            if value is None:
                continue
            if isinstance(value, str):
                pass # pass required
            elif isinstance(value, MusicNoteSequence):
                value = self.get_audio_tag(value.file_name)
                tag = True
            elif isinstance(value, Iterable):
                value, tag = self.__format_tts(new_line, prev_tag, "", *value)
            else:
                value = str(value)

            if len(value) == 0:
                continue

            if not new_line and not tag and len(sep) > 0 and len(tts) > 0 and value[0].isalnum():
                tts += sep

            tts += value
            new_line = new_line if tag else value[-1] == "\n"
            prev_tag = tag

        return tts, prev_tag