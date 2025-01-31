import random as rnd
import threading
from aliceio.types import Message, TextButton
from aliceio.types.number_entity import NumberEntity
from abc import ABC, abstractmethod

from config import Config
from voicemenu import *
from musicnotesequence import *
from musicnote import *
from meldictenginebase import MelDictEngineBase
from myfilters import *
from myconstants import *

class NoReplyError(ValueError):
    def __init__(self, msg: str = "Нет реплики"):
        super().__init__(msg)

class MelDictLevelBase(ABC):
    MaxTasksCount = 9
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
    def finished(self): return self.total_score >= MissedNoteLevel.MaxTasksCount

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
                title = answer.btn(note_pos = 0, note_cmp = self.__current_comparator)
                yield self._create_button(title, 1)
                title = answer.btn(note_pos = 1, note_cmp = self.__current_comparator)
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
                   f"Сравн.: {'>' if comparator else '<'}\n\n"]

    def get_stats_reply(self, format_name: bool = True) -> tuple[str, str]:
        return None, None

    def _get_reply(self)-> tuple[str, str]:
        noteseq = self.__current_noteseq
        comparator = self.__current_comparator

        if noteseq is None:
            noteseq = self.__current_noteseq = \
                self.engine.get_rnd_note_sequence(
                    lambda ns:
                        ns != self.__current_noteseq and
                        ns.is_interval and
                        not ns.is_vertical)

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
                   f"Загадан: {noteseq.file_name}, {noteseq.id}, {noteseq}, {noteseq.prima_location_str}\n\n"]

    def _get_reply(self)-> tuple[str, str]:
        noteseq = self.__current_noteseq
        
        if noteseq is None:
            noteseq = self.__current_noteseq = self.engine.get_rnd_note_sequence(
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


class CadenceLevel(MelDictLevelBase):
    def __init__(self, engine, first_run: bool = True):
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
                title = answer.btn(chord_pos = 0)
                yield self._create_button(title, 1)
                title = answer.btn(chord_pos = 1)
                yield self._create_button(title, 2)
                title = answer.btn(chord_pos = 2)
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
                  f"Загадан: {guessed_index + 1}. {noteseq.file_name}, {noteseq.id}, {noteseq}, {noteseq.name}\n\n"]

    def reset(self):
        super().reset()
        self.__cadence = None
        self.__guessed_index = 0

    def _get_reply(self)-> tuple[str, str]:
        cadence = self.__cadence
        guessed_index = self.__guessed_index

        if cadence is None:
            maj = bool(rnd.getrandbits(1))

            tns = self.engine.get_rnd_note_sequence(
                lambda ns: ns.is_tonic and ns.is_tonality_maj == maj and ns.is_vertical)
            if tns is None: raise NoReplyError(f"Не удалось выбрать тонику: {'maj' if maj else 'min'}, arp")

            sdns = self.engine.get_rnd_note_sequence(
                lambda ns: ns.is_subdominant and ns.is_tonality_maj == maj and ns.is_vertical)
            if sdns is None: raise NoReplyError(f"Не удалось найти субдоминанту: {'maj' if maj else 'min'}, arp")

            dns = self.engine.get_rnd_note_sequence(
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


class MissedNoteLevel(MelDictLevelBase):
    def __init__(self, engine, first_run = True):
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
                title = answer.btn(note_pos = 0)
                yield self._create_button(title, 1)
                title = answer.btn(note_pos = 1)
                yield self._create_button(title, 2)
                title = answer.btn(note_pos = 2)
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
                  f"Аккорд: {chord.file_name}, {chord.id}, {'maj' if chord.is_chord_maj else 'min'}, {chord}\n\n",
                  f"Интервал: {chord.file_name}, {interval.id}, {interval.base_chord}, {interval}, пропуск: {interval.missed_note + 1}\n\n"]

    def _get_reply(self):
        interval = self.__interval
        chord = self.__chord

        if interval is None:
            interval = self.engine.get_rnd_note_sequence(
                lambda ns:
                    ns.is_interval and ns.is_ascending and not ns.is_vertical and len(ns.name) > 0)

            if interval is None:
                raise NoReplyError(f"Не удалось выбрать интервал")

            chord = self.engine.get_rnd_note_sequence(
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