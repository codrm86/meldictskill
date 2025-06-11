import random as rnd
from aliceio.types import Message, TextButton
from typing import Iterable
from .base_level import MelDictLevelBase, NoReplyError
from ..musicnotesequence import MusicNoteSequence
from ..meldictenginebase import MelDictEngineBase
from ..maindb import MainDB
from ...config import Config
from ...voicemenu import VoiceMenu, GameLevel
from ...myconstants import *

class DemoLevel(MelDictLevelBase):
    def __init__(self, engine: MelDictEngineBase, first_run: bool = True):
        super().__init__(engine, first_run)
        self.__current_noteseq = None
        self.__current_comparator = False

    @property
    def id(self) -> int: return 0

    @property
    def game_level(self) -> GameLevel: return VoiceMenu().levels.demo

    def _reset_secrets(self):
        self.__current_noteseq = None
        self.__current_comparator = False

    def get_buttons(self) -> Iterable[TextButton]:
        if not self.finished:
            answer = self.game_level.answers()
            if answer:
                title = answer.btn(item_number = 1, note_pos = 0, note_cmp = self.__current_comparator)
                yield self._create_button(title, 1)
                title = answer.btn(item_number = 2, note_pos = 1, note_cmp = self.__current_comparator)
                yield self._create_button(title, 2)

    def __format_what(self, noteseq: MusicNoteSequence, vm: VoiceMenu = None) -> tuple[str, str]:
        text = tts = None
        if len(noteseq.name) > 0:
            vm = vm if vm else VoiceMenu()
            what = vm.levels.demo.whats()
            text, tts = what(asc=noteseq.is_ascending, value=lambda s: (noteseq.tts_name if s else noteseq.name).lower())
        return text, tts

    def __format_correct(self, noteseq, vm: VoiceMenu = None) -> tuple[str, str]:
        what = self.__format_what(noteseq, vm) if self.show_right else (None, None)
        return super()._format_correct(*what)

    def __format_incorrect(self, noteseq: MusicNoteSequence, note_cmp: bool, vm: VoiceMenu = None) -> tuple[str, str]:
        text = tts = None
        vm = vm if vm else VoiceMenu()

        if noteseq and self.show_right:
            note_pos = int(noteseq.is_ascending) if note_cmp \
                else int(not noteseq.is_ascending)

            answer = vm.levels.demo.answers()
            answer_text, answer_tts = answer(
                note_pos=note_pos, note_cmp=note_cmp)
            what_text, what_tts = self.__format_what(noteseq, vm)
            text = self.engine.format_text(answer_text, what_text)
            tts = self.engine.format_tts(answer_tts, what_tts)

        wrong = vm.root.wrongs()
        text = self.engine.format_text(wrong.text, text)
        tts = self.engine.format_tts(wrong.tts, tts)
        return text, tts

    def __debug(self, noteseq: MusicNoteSequence, comparator: bool, answer: int = None) -> list[str]:
        return None if not Config().debug.enabled \
             else [f"\n#DEBUG\n",
                   f"Ответ: {answer}\n" if answer else None,
                   f"Интервал: {noteseq.file_name}, {noteseq.id}, {noteseq}\n",
                   f"Сравн.: {'>' if comparator else '<'}\n"]

    def get_stats_reply(self, format_name: bool = True) -> tuple[str, str]:
        return None, None

    def _get_reply(self)-> tuple[str, str]:
        main_db = MainDB()
        noteseq = self.__current_noteseq
        comparator = self.__current_comparator

        if noteseq is None:
            noteseq = self.__current_noteseq = \
                main_db.rnd(
                    lambda ns:
                        ns.is_interval and not ns.is_vertical)

            comparator = self.__current_comparator = bool(rnd.getrandbits(1))

        if noteseq:
            gamelevel = self.game_level
            start_text, start_tts = self._select_start_reply(gamelevel)
            task_text, task_tts = gamelevel.tasks()
            question_text, question_tts = gamelevel.questions()(note_cmp=comparator)
            debug = self.__debug(noteseq, comparator)

            text = self.engine.format_text(
                start_text, task_text, question_text, debug)

            tts = self.engine.format_tts(
                start_tts, task_tts, question_tts, noteseq)

            return text, tts
        raise NoReplyError()

    def _process_user_reply(self, message: Message, button: TextButton)-> tuple[str, str]:
        noteseq = self.__current_noteseq
        comparator = self.__current_comparator
        if noteseq is None: NoReplyError("Интервал не выбран")

        answer = self._get_last_number(message, button)
        if answer is None:
            text, tts = VoiceMenu().root.dont_understand()
            return text, self.engine.format_tts(tts)

        reply_text = reply_tts = None
        vm = VoiceMenu()

        if answer >= 1 and answer <= 2:
            n1 = noteseq[answer-1]
            n2 = noteseq[answer-2]
            if (comparator and n1 > n2) or (not comparator and n1 < n2):
                self.correct_score += 1
                reply_text, reply_tts = self.__format_correct(noteseq, vm)

        if reply_text is None:
            self.incorrect_score += 1
            reply_text, reply_tts = self.__format_incorrect(noteseq, comparator, vm)

        self._reset_secrets()

        continue_text, continue_tts = (None, None) if self.finished \
            else vm.levels.demo.continues()

        next_text, next_tts = self.get_reply() # next interval
        debug = self.__debug(noteseq, comparator, answer)

        text = self.engine.format_text(
            reply_text, continue_text, debug, "\n", next_text)

        tts = self.engine.format_tts(
            reply_tts, continue_tts, next_tts)

        return text, tts