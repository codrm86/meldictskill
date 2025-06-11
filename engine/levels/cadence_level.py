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

class CadenceLevel(MelDictLevelBase):
    def __init__(self, engine: MelDictEngineBase, first_run: bool = True):
        super().__init__(engine, first_run)
        self.__cadence = None
        self.__guessed_index = 0

    @property
    def id(self) -> int: return 3

    @property
    def game_level(self) -> GameLevel: return VoiceMenu().levels.cadence

    def _reset_secrets(self):
        self.__cadence = None
        self.__guessed_index = 0

    def get_buttons(self) -> Iterable[TextButton]:
        if not self.finished:
            answer = self.game_level.answers()
            if answer:
                title = answer.btn(item_number = 1, chord_pos = 0)
                yield self._create_button(title, 1)
                title = answer.btn(item_number = 2, chord_pos = 1)
                yield self._create_button(title, 2)
                title = answer.btn(item_number = 3, chord_pos = 2)
                yield self._create_button(title, 3)

    def __format_what(self, noteseq: MusicNoteSequence) -> tuple[str, str]:
        text = tts = None
        if self.show_right:
            what = self.game_level.whats()
            text, tts = what(
                neuter=noteseq.name.endswith('е'),
                chord_name=lambda s: (noteseq.tts_name if s else noteseq.name).lower())
        return text, tts

    def __format_correct(self, noteseq: MusicNoteSequence) -> tuple[str, str]:
        what = self.__format_what(noteseq)
        return super()._format_correct(*what)

    def __format_incorrect(self, cadence: list[MusicNoteSequence], guessed_index: int) -> tuple[str, str]:        
        text = tts = None
        if self.show_right:
            what_text, what_tts = self.__format_what(cadence[guessed_index])
            answer = self.game_level.answers()
            text, tts = answer(chord_pos=guessed_index)
            text = self.engine.format_text(text, what_text)
            tts = self.engine.format_tts(tts, what_tts)
        return super()._format_incorrect(text, tts)

    def __debug(self, cadence: Iterable[MusicNoteSequence], guessed_index: int, answer: int = None) -> list[str]:
        noteseq = cadence[guessed_index]
        return None if not Config().debug.enabled \
            else ["\n#DEBUG\n",
                  f"Ответ: {answer}\n" if answer \
                    else (f"{i + 1}. {ns.file_name}, {ns.id}, {ns}, {ns.name}\n" for i, ns in enumerate(cadence)),
                  f"Загадан: {guessed_index + 1}. {noteseq.file_name}, {noteseq.id}, {noteseq}, {noteseq.name}\n"]

    def reset(self):
        super().reset()
        self.__cadence = None
        self.__guessed_index = 0

    def _get_reply(self)-> tuple[str, str]:
        cadence = self.__cadence
        guessed_index = self.__guessed_index

        if cadence is None:
            maj = bool(rnd.getrandbits(1))
            main_db = MainDB()

            tns = main_db.rnd(
                lambda ns: ns.is_tonic and ns.is_tonality_maj == maj and ns.is_vertical)
            if tns is None: raise NoReplyError(f"Не удалось выбрать тонику: {'maj' if maj else 'min'}, arp")

            sdns = main_db.rnd(
                lambda ns: ns.is_subdominant and ns.is_tonality_maj == maj and ns.is_vertical)
            if sdns is None: raise NoReplyError(f"Не удалось найти субдоминанту: {'maj' if maj else 'min'}, arp")

            dns = main_db.rnd(
                lambda ns: ns.is_dominant and ns.is_tonality_maj == maj and ns.is_vertical)
            if dns is None: raise NoReplyError(f"Не удалось найти доминанту: {'maj' if maj else 'min'}, arp")

            cadence = self.__cadence = rnd.sample([tns, sdns, dns], 3) # shuffle cadence
            guessed_index = self.__guessed_index = rnd.randint(0, 2) # guess chord number

        if cadence:
            gamelevel = self.game_level
            start_text, start_tts = self._select_start_reply(gamelevel)
            question_text, question_tts = gamelevel.questions()
            
            task_text, task_tts = gamelevel.tasks()(
                    chord_arp = self.engine.get_audio_tag(MusicNoteSequence.get_file_name(False, cadence[guessed_index])),
                    chord_vert = self.engine.get_audio_tag(cadence[guessed_index]),
                    cadence = self.engine.format_tts(cadence))

            debug = self.__debug(cadence, guessed_index)

            text = self.engine.format_text(
                start_text,
                task_text,
                question_text,
                debug)

            tts = self.engine.format_tts(
                start_tts,
                task_tts,
                question_tts)
            return text, tts

        raise NoReplyError()


    def _process_user_reply(self, message: Message, button: TextButton)-> tuple[str, str]:
        cadence = self.__cadence
        guessed_index = self.__guessed_index

        if cadence is None:
            raise NoReplyError("Каденция не создана")

        answer = self._get_last_number(message, button)
        if answer is None:
            text, tts = VoiceMenu().root.dont_understand()
            return text, self.engine.format_tts(tts)

        reply_text = reply_tts = None

        if answer >= 1 and answer <= 3 and answer - 1 == guessed_index:
            self.correct_score += 1
            reply_text, reply_tts = self.__format_correct(cadence[guessed_index])
        else:
            self.incorrect_score += 1
            reply_text, reply_tts = self.__format_incorrect(cadence, guessed_index)

        self._reset_secrets() # reset secrets
        next_text, next_tts = self.get_reply() # next cadence
        debug = self.__debug(cadence, guessed_index, answer)

        # continue_reply = "" if self.finished else rnd.choice(CadenceLevel.__continue_replies)
        continue_text, continue_tts = (None, None) if self.finished \
            else self.game_level.continues()

        text = self.engine.format_text(
            reply_text, continue_text, debug, "\n", next_text)

        tts = self.engine.format_tts(
            reply_tts, continue_tts, next_tts)

        return text, tts