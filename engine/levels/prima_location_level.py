from aliceio.types import Message, TextButton
from typing import Iterable
from .base_level import MelDictLevelBase, NoReplyError
from ..musicnotesequence import MusicNoteSequence
from ..meldictenginebase import MelDictEngineBase
from ..maindb import MainDB
from ...config import Config
from ...voicemenu import VoiceMenu, GameLevel
from ...myfilters import CmdFilter
from ...myconstants import *

class PrimaLocationLevel(MelDictLevelBase):
    def __init__(self, engine: MelDictEngineBase, first_run: bool = True):
        super().__init__(engine, first_run)
        self.__current_noteseq = None

    @property
    def id(self) -> int: return 2

    @property
    def game_level(self) -> GameLevel: return VoiceMenu().levels.prima_location

    def _reset_secrets(self):
        self.__current_noteseq = None

    def get_buttons(self) -> Iterable[TextButton]:
        if not self.finished:
            answer = self.game_level.answers()
            if answer:
                title = answer.btn(prima_loc = MusicNoteSequence.PRIMALOC_BOTTOM)
                yield self._create_button(title, MusicNoteSequence.PRIMALOC_BOTTOM)
                title = answer.btn(prima_loc = MusicNoteSequence.PRIMALOC_MIDDLE)
                yield self._create_button(title, MusicNoteSequence.PRIMALOC_MIDDLE)
                title = answer.btn(prima_loc = MusicNoteSequence.PRIMALOC_TOP)
                yield self._create_button(title, MusicNoteSequence.PRIMALOC_TOP)

    def __format_incorrect(self, noteseq: MusicNoteSequence) -> tuple[str, str]:
        text = tts = None
        if self.show_right:
            answer = self.game_level.answers()
            text, tts = answer(prima_loc=noteseq.prima_location)
        return super()._format_incorrect(text, tts)

    def __debug(self, noteseq: MusicNoteSequence, answer: int = None) -> list[str]:
        return None if not Config().debug.enabled \
             else [f"\n#DEBUG\n",
                   f"Код ответа: {answer}\n" if answer else None,
                   f"Загадан: {noteseq.file_name}, {noteseq.id}, {noteseq}, {noteseq.prima_location_str}\n"]

    def _get_reply(self)-> tuple[str, str]:
        main_db = MainDB()
        noteseq = self.__current_noteseq
        
        if noteseq is None:
            noteseq = self.__current_noteseq = main_db.rnd(
                lambda ns:
                    ns != self.__current_noteseq and \
                    ns.is_triad and not ns.is_vertical and \
                    ns.prima_location != MusicNoteSequence.PRIMALOC_UNKNOWN)

        if noteseq:
            gamelevel = self.game_level
            start_text, start_tts = self._select_start_reply(gamelevel)
            task_text, task_tts = gamelevel.tasks()
            question_text, question_tts = gamelevel.questions()
            debug = self.__debug(noteseq)

            text = self.engine.format_text(
                start_text,
                task_text,
                question_text,
                debug)

            tts = self.engine.format_tts(
                start_tts,
                task_tts, noteseq,
                question_tts)

            return text, tts

        raise NoReplyError()

    def _process_user_reply(self, message: Message, button: TextButton)-> tuple[str, str]:
        noteseq = self.__current_noteseq
        answer = MusicNoteSequence.PRIMALOC_UNKNOWN

        if noteseq is None:
            raise NoReplyError("Трезвучие не выбрано")

        answer = self._get_value(message, button)

        if isinstance(answer, str):
            if answer and CmdFilter.passed(answer, ("внизу", "снизу"), ("не", "нет")):
                answer = MusicNoteSequence.PRIMALOC_BOTTOM
            elif answer and CmdFilter.passed(answer, ("середин", "посреди", "посередин"), ("не", "нет")):
                answer = MusicNoteSequence.PRIMALOC_MIDDLE
            elif answer and CmdFilter.passed(answer, ("сверху", "наверху", "вверху"), ("не", "нет")):
                answer = MusicNoteSequence.PRIMALOC_TOP
            else:
                text, tts = VoiceMenu().root.dont_understand()
                return text, self.engine.format_tts(tts)

        reply_text = reply_tts = None
        if answer == noteseq.prima_location:
            self.correct_score += 1
            reply_text, reply_tts = self._format_correct()
        else:
            self.incorrect_score += 1
            reply_text, reply_tts = self.__format_incorrect(noteseq)

        self._reset_secrets()

        continue_text, continue_tts = (None, None) if self.finished \
            else self.game_level.continues()

        next_text, next_tts = self.get_reply() # next chord
        debug = self.__debug(noteseq, answer)

        text = self.engine.format_text(
            reply_text, continue_text, debug, "\n", next_text)

        tts = self.engine.format_tts(
            reply_tts, continue_tts, next_tts)

        return text, tts