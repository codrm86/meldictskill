import random as rnd
from aliceio.types import Message, TextButton
from typing import Iterable
from engine.levels.base_level import MelDictLevelBase, NoReplyError
from engine.musicnotesequence import MusicNoteSequence
from engine.meldictenginebase import MelDictEngineBase
from engine.maindb import MainDB
from config import Config
from voicemenu import VoiceMenu, GameLevel
from myconstants import *

class MissedNoteLevel(MelDictLevelBase):
    def __init__(self, engine: MelDictEngineBase, first_run: bool = True):
        super().__init__(engine, first_run)
        self.__interval = None
        self.__chord = None

    @property
    def id(self) -> int: return 1

    @property
    def game_level(self) -> GameLevel: return VoiceMenu().levels.missed_note

    def _reset_secrets(self):
        self.__interval = None
        self.__chord = None

    def get_buttons(self) -> Iterable[TextButton]:
        if not self.finished:
            answer = self.game_level.answers()
            if answer:
                title = answer.btn(item_number = 1, note_pos = 0)
                yield self._create_button(title, 1)
                title = answer.btn(item_number = 2, note_pos = 1)
                yield self._create_button(title, 2)
                title = answer.btn(item_number = 3, note_pos = 2)
                yield self._create_button(title, 3)

    def __format_what(self, chord: MusicNoteSequence, interval: MusicNoteSequence) -> tuple[str, str]:
        gamelevel = self.game_level
        what = gamelevel.whats()
        text, tts = what(
            inversion=chord.inversion_str.lower(),
            maj=chord.is_chord_maj,
            interval_name=lambda s: (interval.tts_name if s else interval.name).lower())
        return text, tts

    def __format_correct(self, chord: MusicNoteSequence, interval: MusicNoteSequence) -> tuple[str, str]:
        what = self.__format_what(chord, interval) if self.show_right else (None, None)
        return super()._format_correct(*what)

    def __format_incorrect(self, chord: MusicNoteSequence, interval: MusicNoteSequence) -> tuple[str, str]:        
        text = tts = None
        if self.show_right:
            answer = self.game_level.answers()
            answer_text, answer_tts = answer(
                note_pos=interval.missed_note)
            what_text, what_tts = self.__format_what(chord, interval)
            text = self.engine.format_text(answer_text, what_text)
            tts = self.engine.format_tts(answer_tts, what_tts)
        return super()._format_incorrect(text, tts)

    def __debug(self, chord: MusicNoteSequence, interval: MusicNoteSequence, answer: int = None) -> list[str]:
        return None if not Config().debug.enabled \
            else ["\n#DEBUG\n",
                  f"Ответ: {answer}\n" if answer else None,
                  f"Аккорд: {chord.file_name}, {chord.id}, {'maj' if chord.is_chord_maj else 'min'}, {chord}\n",
                  f"Интервал: {chord.file_name}, {interval.id}, {interval.base_chord}, {interval}, пропуск: {interval.missed_note + 1}\n"]

    def _get_reply(self):
        main_db = MainDB()
        interval = self.__interval
        chord = self.__chord

        if interval is None:
            interval = main_db.rnd(
                lambda ns:
                    ns.is_interval and ns.is_ascending and not ns.is_vertical and len(ns.name) > 0)

            if interval is None:
                raise NoReplyError(f"Не удалось выбрать интервал")

            chord = main_db.rnd(
                lambda ns:
                    ns.is_triad and not ns.is_vertical and interval.base_chord == ns.id)

            if chord is None:
                raise NoReplyError(f"Не удалось найти базовый аккорд")

            self.__interval = interval
            self.__chord = chord

        if chord:
            gamelevel = self.game_level
            start_text, start_tts = self._select_start_reply(gamelevel)
            task_text, task_tts = gamelevel.tasks()
            question_text, question_tts = gamelevel.questions()
            debug = self.__debug(chord, interval)

            text = self.engine.format_text(
                start_text,
                task_text,
                question_text,
                debug)

            tts = self.engine.format_tts(
                start_tts,
                task_tts, chord, interval,
                question_tts)

            return text, tts

        raise NoReplyError()

    def _process_user_reply(self, message: Message, button: TextButton):
        interval = self.__interval
        chord = self.__chord

        if interval is None:
            raise NoReplyError("Интервал не выбран")

        answer = self._get_last_number(message, button)
        if answer is None:
            text, tts = VoiceMenu().root.dont_understand()
            return text, self.engine.format_tts(tts)

        reply_text = reply_tts = None

        if answer - 1 == interval.missed_note:
            self.correct_score += 1
            reply_text, reply_tts = self.__format_correct(chord, interval)
        else:
            self.incorrect_score += 1
            reply_text, reply_tts = self.__format_incorrect(chord, interval)

        self._reset_secrets()

        continue_text, continue_tts = (None, None) if self.finished \
            else self.game_level.continues()

        next_text, next_tts = self.get_reply() # next interval and chord
        debug = self.__debug(chord, interval, answer)

        text = self.engine.format_text(
            reply_text, continue_text, debug, "\n", next_text)

        tts = self.engine.format_tts(
            reply_tts, continue_tts, next_tts)

        return text, tts