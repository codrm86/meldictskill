import random as rnd
import threading
from aliceio.types import Message
from aliceio.types.number_entity import NumberEntity
from abc import ABC, abstractmethod

from config import Config
from musicnotesequence import *
from musicnote import *
from meldictenginebase import MelDictEngineBase
from myfilters import *
from myconstants import *

class NoReplyError(ValueError):
    def __init__(self, msg: str = "Нет реплики"):
        super().__init__(msg)

class StopGameException(BaseException):
    def __init__(self, *args):
        super().__init__(*args)


class MelDictTaskBase(ABC):
    RepeatFilter = CmdFilter("повтор", exclude="не",)

    _rlock: threading.RLock

    def __init__(self, engine: MelDictEngineBase, first_run: bool = True):
        assert engine
        self.__engine = engine
        self.__show_right = False
        self.__correct_score = 0
        self.__incorrect_score = 0
        self.__first_run = first_run
        self._rlock = threading.RLock()

    @property
    @abstractmethod
    def display_name(self) -> str: pass

    @property
    def tts_name(self) -> str: return self.display_name

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
    def started(self): return self.correct_score + self.incorrect_score > 0

    def reset(self):
        with self._rlock:
            self.__correct_score = self.__incorrect_score = 0
            self._reset_secrets()

    @abstractmethod
    def _reset_secrets(self):
        pass

    def get_reply(self, repeat: bool = False) -> tuple[str, str]:
        with self._rlock:
            return self._get_reply(repeat)

    @abstractmethod
    def _get_reply(self, repeat: bool = False) -> tuple[str, str]:
        pass

    def process_user_reply(self, message: Message) -> tuple[str, str]:
        with self._rlock:
            if MelDictTaskBase.RepeatFilter.is_passed(message.command):
                return self._get_reply(True)

            return self._process_user_reply(message)

    @abstractmethod
    def _process_user_reply(self, message: Message) -> tuple[str, str]:
        pass

    def _reset_first_run(self) -> bool:
        first_run, self.__first_run = self.__first_run, False
        return first_run

    def _get_last_number(self, message: Message) -> int:
        for en in reversed(message.nlu.entities):
            if isinstance(en.value, NumberEntity):
                return int(en.value)

    def _format_correct(self, reply: str = "") -> tuple[str, str]: # text, tts
        """
            "Правильно! {reply}"
        """
        reply = f"Правильно! {reply}"
        return reply, reply

    def _format_incorrect(self, reply: str = "") -> tuple[str, str]: # text, tts
        """
            "Неправильно! {reply}"
        """
        reply = f"Неправильно! {reply}"
        return reply, reply


class DemoTask(MelDictTaskBase):
    __main_question = "Прослушай эти две ноты..."
    __first_run_reply = \
        "Поиграем в диктант? Я буду диктовать по две ноты, а ты называй номер той, которая выше или ниже.\n" \
        "Если захочешь прослушать задание ещё раз, просто скажи:\n" \
        "[ПОВТОРИ]\n" + __main_question
    
    __continue_replies = ["Теперь послушай эти.",
                          "Следующий интервал.",
                          "Идём дальше."]

    @property
    def display_name(self) -> str: return "Демо"

    @property
    def tts_name(self) -> str: return "Д+эмо"

    def __init__(self, engine: MelDictEngineBase, first_run: bool = True):
        super().__init__(engine, first_run)
        self.__current_noteseq = None
        self.__current_comparator = False

    def _reset_secrets(self):
        self.__current_noteseq = None
        self.__current_comparator = False

    def __format_what(self, noteseq: MusicNoteSequence) -> str:
        return f"Это была «{noteseq.title.lower()}»." \
            if len(noteseq.title) > 0 else ""

    def __format_correct(self, noteseq) -> tuple[str, str]:
        return super()._format_correct(self.__format_what(noteseq) if self.show_right else "")

    def __format_incorrect(self, noteseq: MusicNoteSequence, comparator: bool) -> tuple[str, str]:
        reply = ""
        if noteseq and self.show_right:
            note_pos = "Первая" if not comparator and noteseq.is_ascending else "Вторая"
            note_cmp = "выше" if comparator else "ниже"
            answ = f"{note_pos} нота {note_cmp}"
            what = self.__format_what(noteseq)
            reply = f"{answ}. {what}" if len(what) > 0 else answ
        return super()._format_incorrect(reply)

    def __debug(self, noteseq: MusicNoteSequence, comparator: bool, answer: int = None) -> list[str]:
        return None if not Config().debug.enabled \
             else [f"\n#DEBUG\n",
                   f"Ответ: {answer}\n" if answer else None,
                   f"Интервал: {noteseq.name}, {noteseq}\n",
                   f"Сравн.: {'>' if comparator else '<'}\n\n"]

    def _get_reply(self, repeat: bool = False)-> tuple[str, str]:
        noteseq = self.__current_noteseq
        comparator = self.__current_comparator

        if noteseq is None:
            noteseq = self.__current_noteseq = \
                self.engine.get_rnd_note_sequence(
                    lambda ns:
                        ns != self.__current_noteseq and
                        ns.is_interval and
                        not ns.is_vertical)

            comparator = self.__current_comparator = rnd.randint(0, 1) == 1

        if noteseq:
            continue_reply = DemoTask.__first_run_reply if self._reset_first_run() \
                else DemoTask.__main_question if repeat \
                else rnd.choice(DemoTask.__continue_replies)

            question_reply = f"Какая {rnd.choice(["нота", "из них", ""])} {"выше" if comparator else "ниже"}?"
            debug = self.__debug(noteseq, comparator)

            text = self.engine.format_text(
                continue_reply, question_reply, debug)

            tts = self.engine.format_tts(
                continue_reply, question_reply, noteseq)

            return text, tts

        raise NoReplyError()

    def _process_user_reply(self, message: Message)-> tuple[str, str]:
        noteseq = self.__current_noteseq
        comparator = self.__current_comparator
        if noteseq is None: NoReplyError("Интервал не выбран")

        answer = self._get_last_number(message)
        if answer is None:
            text = tts = AliceReplies.DONT_UNDERSTAND
            return text, tts

        reply_text = reply_tts = None

        if answer >= 1 and answer <= 2 and noteseq:
            n1 = noteseq[answer-1]
            n2 = noteseq[answer-2]
            if (comparator and n1 > n2) or (not comparator and n1 < n2):
                self.correct_score += 1
                reply_text, reply_tts = self.__format_correct(noteseq)

        if reply_text is None:
            self.incorrect_score += 1
            reply_text, reply_tts = self.__format_incorrect(noteseq, comparator)

        self._reset_secrets()
        next_text, next_tts = self.get_reply() # next note sequence
        debug = self.__debug(noteseq, comparator, answer)

        text = self.engine.format_text(
            reply_text, debug, next_text)
        
        tts = self.engine.format_tts(
            reply_tts, next_tts)

        return text, tts


class PrimaLocationTask(MelDictTaskBase):
    __main_question = "Где основной тон в этом аккорде?"
    __first_run_reply = "Я буду диктовать арпеджированные аккорды, а ты называй, на каком месте стоит тоника - сверху, в середине или внизу.\n" \
                        "Если захочешь прослушать задание ещё раз, просто скажи:\n\n" \
                        "[ПОВТОРИ]\n" + __main_question
    
    __continue_replies = ["Теперь послушай этот аккорд.",
                          "Следующий аккорд.",
                          "Продолжаем.",
                          "Продолжаем диктант.",
                          "Идём дальше."]
    
    __questions = ["Где тоника?",
                   "Где основной тон?",
                   __main_question]

    @property
    def display_name(self) -> str: return "Тоника"

    def __init__(self, engine: MelDictEngineBase, first_run: bool = True):
        super().__init__(engine, first_run)
        self.__current_noteseq = None

    def _reset_secrets(self):
        self.__current_noteseq = None

    def __format_incorrect(self, noteseq: MusicNoteSequence) -> tuple[str, str]:
        reply = f"Правильный ответ - {noteseq.prima_location_str.lower()}. " if noteseq and self.show_right else ""
        return super()._format_incorrect(reply)

    def __debug(self, noteseq: MusicNoteSequence, answer: int = None) -> list[str]:
        return None if not Config().debug.enabled \
             else [f"\n#DEBUG\n",
                   f"Код ответа: {answer}\n" if answer else None,
                   f"Загадан: {noteseq.name} - {noteseq.prima_location_str}, {noteseq}\n\n"]

    def _get_reply(self, repeat: bool = False)-> tuple[str, str]:
        noteseq = self.__current_noteseq
        if noteseq is None:
            noteseq = self.__current_noteseq = self.engine.get_rnd_note_sequence(
                lambda ns:
                    ns != self.__current_noteseq and \
                    ns.is_triad and not ns.is_vertical and \
                    ns.prima_location != MusicNoteSequence.PRIMALOC_UNKNOWN)

        if noteseq:
            first_run = self._reset_first_run()

            continue_reply = "" if first_run or repeat \
                else rnd.choice(PrimaLocationTask.__continue_replies)

            task_reply = PrimaLocationTask.__first_run_reply if first_run \
                else rnd.choice(PrimaLocationTask.__questions)

            debug = self.__debug(noteseq)

            text = self.engine.format_text(
                continue_reply,
                task_reply,
                debug)

            tts = self.engine.format_tts(
                continue_reply,
                task_reply, noteseq)

            return text, tts

        raise NoReplyError()

    def _process_user_reply(self, message: Message)-> tuple[str, str]:
        noteseq = self.__current_noteseq
        answer = MusicNoteSequence.PRIMALOC_UNKNOWN

        if noteseq is None:
            raise NoReplyError("Трезвучие не выбрано")

        if CmdFilter.passed(message.command, ("внизу", "снизу"), ("не", "нет")):
            answer = MusicNoteSequence.PRIMALOC_BOTTOM
        elif CmdFilter.passed(message.command, ("середин", "посреди", "посередин"), ("не", "нет")):
            answer = MusicNoteSequence.PRIMALOC_MIDDLE
        elif CmdFilter.passed(message.command, ("сверху", "наверху", "вверху"), ("не", "нет")):
            answer = MusicNoteSequence.PRIMALOC_TOP
        else:
            text = tts = AliceReplies.DONT_UNDERSTAND
            return text, tts

        reply_text = reply_tts = None
        if answer == noteseq.prima_location:
            self.correct_score += 1
            reply_text, reply_tts = self._format_correct()
        else:
            self.incorrect_score += 1
            reply_text, reply_tts = self.__format_incorrect(noteseq)

        self._reset_secrets()
        next_text, next_tts = self.get_reply() # next note sequence
        debug = self.__debug(noteseq, answer)

        text = self.engine.format_text(
            reply_text, debug, next_text)

        tts = self.engine.format_tts(
            reply_tts, next_tts)

        return text, tts


class CadenceTask(MelDictTaskBase):
    __first_run_reply = "Я продиктую аккорд, а потом каденцию, а ты угадай каким он был по счёту.\n" \
                        "Если захочешь прослушать задание ещё раз, просто скажи:\n" \
                        "[ПОВТОРИ]\n"

    __continue_replies = ["Продолжаем.",
                          "Продолжаем диктант.",
                          "Идём дальше.",
                          ""]

    @property
    def display_name(self) -> str: return "Каденция"

    @property
    def tts_name(self) -> str: return "Кад+энция"

    def __init__(self, engine, first_run: bool = True):
        super().__init__(engine, first_run)
        self.__cadence = None
        self.__guessed_index = 0

    def _reset_secrets(self):
        self.__cadence = None
        self.__guessed_index = 0

    def __format_what(self, noteseq: MusicNoteSequence) -> str:
        return f"Это был{'о' if noteseq.title.endswith('е') else ''} «{noteseq.title.lower()}». " \
            if len(noteseq.title) > 0 else ""

    def __format_correct(self, noteseq: MusicNoteSequence) -> tuple[str, str]:
        return super()._format_correct(self.__format_what(noteseq) if self.show_right else "")

    def __format_incorrect(self, cadence: list[MusicNoteSequence], guessed_index: int) -> tuple[str, str]:        
        reply = ""
        if self.show_right:
            num_str = "первым" if guessed_index == 0 else \
                      "вторым" if guessed_index == 1 else \
                      "третьим"
            what = self.__format_what(cadence[guessed_index])
            reply = f"Он был {num_str} по счёту. {what}"

        return super()._format_incorrect(reply)

    def __debug(self, cadence: Iterable[MusicNoteSequence], guessed_index: int, answer: int = None) -> list[str]:
        noteseq = cadence[guessed_index]
        return None if not Config().debug.enabled \
            else ["\n#DEBUG\n",
                  f"Ответ: {answer}\n" if answer \
                    else (f"{i + 1}. {ns.name} - {ns.title}, {ns}\n" for i, ns in enumerate(cadence)),
                  f"Загадан: {guessed_index + 1}. {noteseq.name} - {noteseq.title}, {noteseq}\n\n"]

    def reset(self):
        super().reset()
        self.__cadence = None
        self.__guessed_index = 0

    def _get_reply(self, repeat: bool = False)-> tuple[str, str]:
        cadence = self.__cadence
        guessed_index = self.__guessed_index

        if cadence is None:
            maj = rnd.randint(0, 1) == 1

            tns = self.engine.get_rnd_note_sequence(
                lambda ns: ns.is_tonic and ns.is_tonality_maj == maj and not ns.is_vertical)
            if tns is None: raise NoReplyError(f"Не удалось выбрать тонику: {'maj' if maj else 'min'}, arp")

            sdns = self.engine.get_rnd_note_sequence(
                lambda ns: ns.is_subdominant and ns.is_tonality_maj == maj and not ns.is_vertical)
            if sdns is None: raise NoReplyError(f"Не удалось найти субдоминанту: {'maj' if maj else 'min'}, arp")

            dns = self.engine.get_rnd_note_sequence(
                lambda ns: ns.is_dominant and ns.is_tonality_maj == maj and not ns.is_vertical)
            if dns is None: raise NoReplyError(f"Не удалось найти доминанту: {'maj' if maj else 'min'}, arp")

            cadence = self.__cadence = rnd.sample([tns, sdns, dns], 3) # shuffle cadence
            guessed_index = self.__guessed_index = rnd.randint(0, 2) # guess chord number

        if cadence:
            start_reply = CadenceTask.__first_run_reply if self._reset_first_run() \
                else "" if repeat \
                else rnd.choice(CadenceTask.__continue_replies)
            task_reply1 = f"Прослушай аккорд."
            task_reply2 = "Теперь каденцию."
            question_reply = "Каким по счету был этот аккорд?"

            debug = self.__debug(cadence, guessed_index)

            text = self.engine.format_text(
                start_reply,
                task_reply1,
                task_reply2,
                question_reply,
                debug)

            tts = self.engine.format_tts(
                start_reply.replace("де", "д+э"),
                task_reply1, cadence[guessed_index],
                task_reply2.replace("де", "д+э"), cadence,
                question_reply)

            return text, tts

        raise NoReplyError()


    def _process_user_reply(self, message: Message)-> tuple[str, str]:
        cadence = self.__cadence
        guessed_index = self.__guessed_index

        if cadence is None:
            raise NoReplyError("Каденция не создана")

        answer = self._get_last_number(message)
        if answer is None:
            text = tts = AliceReplies.DONT_UNDERSTAND
            return (text, tts)

        reply_text = reply_tts = None

        if answer >= 1 and answer <= 3 and answer - 1 == guessed_index:
            self.correct_score += 1
            reply_text, reply_tts = self.__format_correct(cadence[guessed_index])
        else:
            self.incorrect_score += 1
            reply_text, reply_tts = self.__format_incorrect(cadence, guessed_index)

        self._reset_secrets() # reset secrets
        text, tts = self.get_reply() # next cadence
        debug = self.__debug(cadence, guessed_index, answer)

        text = self.engine.format_text(
            reply_text, debug, text)

        tts = self.engine.format_tts(
            reply_tts, tts)

        return text, tts
    

class MissedNoteTask(MelDictTaskBase):
    __main_question = "Прослушай аккорд, а потом интервал. Угадай, какой звук пропущен?"
    __first_run_reply = __main_question + "\n" \
                        "Если захочешь прослушать задание ещё раз, просто скажи:\n" \
                        "[ПОВТОРИ]\n"

    __continue_replies = ["Продолжаем.",
                          "Продолжаем диктант.",
                          "Идём дальше.",
                          ""]

    @property
    def display_name(self) -> str: return "Пропущенный звук"

    def __init__(self, engine, first_run = True):
        super().__init__(engine, first_run)
        self.__interval = None
        self.__chord = None

    def __format_what(self, chord: MusicNoteSequence, interval: MusicNoteSequence) -> str:
        return f"Это было «{'мажорное' if chord.is_chord_maj else 'минорное'} трезвучие», " \
               f"осталась «{interval.title.lower()}»."

    def __format_correct(self, chord: MusicNoteSequence, interval: MusicNoteSequence) -> tuple[str, str]:
        what = self.__format_what(chord, interval) if self.show_right else ""
        return super()._format_correct(what)

    def __format_incorrect(self, chord: MusicNoteSequence, interval: MusicNoteSequence) -> tuple[str, str]:        
        reply = ""
        if self.show_right:
            num_str = "первая" if interval.missed_note == 0 else \
                      "вторая" if interval.missed_note == 1 else \
                      "третья"
            what = self.__format_what(chord, interval)
            reply = f"Пропущена {num_str} нота. {what}"
        return super()._format_incorrect(reply)

    def __debug(self, chord: MusicNoteSequence, interval: MusicNoteSequence, answer: int = None) -> list[str]:
        return None if not Config().debug.enabled \
            else ["\n#DEBUG\n",
                  f"Ответ: {answer}\n" if answer else None,
                  f"Аккорд: {chord.name}, {'maj' if chord.is_chord_maj else 'min'}, {chord}\n\n",
                  f"Интервал: {interval.name}, {interval.base_chord}, {interval}, пропуск: {interval.missed_note + 1}\n",]

    def _reset_secrets(self):
        self.__interval = None
        self.__chord = None

    def _get_reply(self, repeat = False):
        interval = self.__interval
        chord = self.__chord

        if interval is None:
            interval = self.engine.get_rnd_note_sequence(
                lambda ns:
                    ns.is_interval and ns.is_ascending and not ns.is_vertical and len(ns.title) > 0)

            if interval is None:
                raise NoReplyError(f"Не удалось выбрать интервал")

            chord = self.engine.get_rnd_note_sequence(
                lambda ns:
                    ns.is_triad and not ns.is_vertical and ns.name == interval.base_chord)

            if chord is None:
                raise NoReplyError(f"Не удалось найти базовый аккорд")

            self.__interval = interval
            self.__chord = chord

        if chord:
            first_run = self._reset_first_run()
            continue_reply = "" if first_run or repeat \
                else rnd.choice(MissedNoteTask.__continue_replies)
            task_reply = MissedNoteTask.__first_run_reply if first_run \
                else MissedNoteTask.__main_question

            question_reply = "Какой звук пропущен?"
            debug = self.__debug(chord, interval)

            text = self.engine.format_text(
                continue_reply,
                task_reply,
                question_reply,
                debug)

            tts = self.engine.format_tts(
                continue_reply,
                task_reply, chord, interval,
                question_reply)

            return text, tts

        raise NoReplyError()

    def _process_user_reply(self, message):
        interval = self.__interval
        chord = self.__chord

        if interval is None: raise NoReplyError("Интервал выбран")

        answer = self._get_last_number(message)
        if answer is None:
            text = tts = AliceReplies.DONT_UNDERSTAND
            return text, tts

        reply_text = reply_tts = None

        if answer - 1 == interval.missed_note:
            self.correct_score += 1
            reply_text, reply_tts = self.__format_correct(chord, interval)
        else:
            self.incorrect_score += 1
            reply_text, reply_tts = self.__format_incorrect(chord, interval)

        self._reset_secrets()
        next_text, next_tts = self.get_reply() # next interval and chord
        debug = self.__debug(chord, interval, answer)

        text = self.engine.format_text(
            reply_text, debug, next_text)

        tts = self.engine.format_tts(
            reply_tts, next_tts)

        return text, tts