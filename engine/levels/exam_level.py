from aliceio.types import Message, TextButton
from .base_level import MelDictLevelBase
from .missed_note_level import MissedNoteLevel
from .prima_location_level import PrimaLocationLevel
from .cadence_level import CadenceLevel
from ..meldictenginebase import MelDictEngineBase
from ...voicemenu import VoiceMenu, GameLevel
from ...myconstants import *

class ExamLevel(MelDictLevelBase):
    def __init__(self,
                 engine: MelDictEngineBase,
                 missed_note_level: MissedNoteLevel,
                 prima_location_level: PrimaLocationLevel,
                 cadence_level: CadenceLevel,
                 first_run = True):
        super().__init__(engine, first_run)
        self.__levels = missed_note_level, prima_location_level, cadence_level

    @property
    def id(self) -> int: return 100

    @property
    def game_level(self) -> GameLevel: return VoiceMenu().levels.exam

    @property
    def correct_score(self): return sum(level.correct_score for level in self.__levels)
    @correct_score.setter
    def correct_score(self, _): raise NotImplementedError()

    @property
    def incorrect_score(self): return sum(level.incorrect_score for level in self.__levels)
    @incorrect_score.setter
    def incorrect_score(self, _): raise NotImplementedError()

    @property
    def finished(self):
        return all(level.finished for level in self.__levels)

    def get_buttons(self):
        for level in self.__levels:
            if not level.finished:
                return level.get_buttons()

    def reset(self):
        super().reset()
        for level in self.__levels:
            level.reset()
            level._first_run = self._first_run

    def _reset_secrets(self):
        pass

    def get_stats_reply(self):
        correct = self.correct_score
        reply = f"Всего отвечено на {correct} {MelDictLevelBase._decline_question(correct)} правильно."

        stats = tuple(level.get_stats_reply()
                      for level in self.__levels if level.total_score > 0)

        text = self.engine.format_text(reply,
                                       *(stat[0] for stat in stats), sep="\n")

        tts = self.engine.format_text(reply,
                                      *(stat[1] for stat in stats), sep=".")
        return text, tts

    def _get_reply(self):
        start_text, start_tts = self._select_start_reply()

        for level in self.__levels:
            if not level.finished:
                text, tts = level.get_reply() # next task
                return self.engine.format_text(start_text, text), self.engine.format_tts(start_tts, tts)

        return None, None

    def _process_user_reply(self, message: Message, button: TextButton):
        texts = []
        ttss = []

        for level in self.__levels:
            if not level.finished:
                text, tts = level.process_user_reply(message, button)
                texts.append(text)
                ttss.append(tts)

                if level.finished:
                    text, tts = self.get_reply() # next level or end
                    if text is not None:
                        texts.append(text)
                        ttss.append(tts)
                break

        return (self.engine.format_text(texts, sep="\n"), self.engine.format_tts(ttss, sep=".")) \
            if len(texts) > 0 else (None, None)