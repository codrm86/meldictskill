import random as rnd
from aliceio.types import Message
from abc import ABC, abstractmethod

from config import Config
from musicnotesequence import *
from musicnote import *
from meldictenginebase import MelDictEngineBase
from myfilters import *
from myconstants import *

class MelDictTaskBase(ABC):
    RepeatFilter = CmdFilter("повтор", exclude="не",)

    def __init__(self, engine: MelDictEngineBase, first_run: bool = True):
        assert engine
        self.__engine = engine
        self.__show_right = False
        self.__correct_score = 0
        self.__incorrect_score = 0
        self._first_run = first_run == True

    @property
    def engine(self): return self.__engine

    @property
    def show_right(self): return self.__show_right
    @show_right.setter
    def show_right(self, value: bool): self.__show_right = value

    @property
    def correct_score(self): return self.__correct_score
    @correct_score.setter
    def correct_score(self, value: int): self.__correct_score = max(0, value)

    @property
    def incorrect_score(self): return self.__incorrect_score
    @incorrect_score.setter
    def incorrect_score(self, value: int): self.__incorrect_score = max(0, value)

    def _get_numbers(self, string: str) -> Iterable[int]:
        for n in re.findall(r'[0-9]+', string):
            try:
                yield int(n)
            except ValueError:
                continue

    def _get_last_number(self, string: str) -> int:
        result = None
        for n in self._get_numbers(string):
            result = n
        return result

    def reset(self):
        self.correct_score = self.incorrect_score = 0

    @abstractmethod
    def get_reply(self, repeat: bool = False) -> tuple[str, str]:
        pass

    @abstractmethod
    def process_user_reply(self, message: Message) -> tuple[str, str]:
        pass

    def _format_correct(self, reply: str = "") -> str:
        """
            "Правильно! {reply}"
        """
        return f"Правильно! {reply}"

    def _format_incorrect(self, reply: str = "") -> str:
        """
            "Неправильно! {reply}Попробуй ещё! "
        """
        return f"Неправильно! {reply}Попробуй ещё! "

class DemoTask(MelDictTaskBase):
    __first_run_reply: str = \
        "Поиграем в диктант? Я буду диктовать по две ноты, а ты называй номер той, которая выше или ниже.\n" \
        "Если захочешь прослушать задание ещё раз, просто скажи:\n" \
        "[ПОВТОРИ]\n" \
        "\n" \
        "Начинаем! Прослушай эти две ноты. "
    
    __next_replies = ["Теперь послушай эти. ",
                      "Следующий интервал. ",
                      "Идём дальше. "]

    def __init__(self, engine: MelDictEngineBase):
        super().__init__(engine)
        self.__current_noteseq = None
        self.__current_comparator = False

    def reset(self):
        super().reset()
        self.__current_noteseq = None
        self.__current_comparator = False

    def _format_incorrect(self, reply: str = "") -> str:
        noteseq = self.__current_noteseq
        comparator = self.__current_comparator

        if noteseq and self.show_right:
            note_pos = "Первая" if not comparator and noteseq.is_ascending else "Вторая"
            note_cmp = "выше" if comparator else "ниже"
            answ = f"{note_pos} нота {note_cmp}."
            reply = f"{answ}. {reply}. " if len(reply) > 0 else answ

        return super()._format_incorrect(reply)

    def get_reply(self, repeat: bool = False)-> tuple[str, str]:
        noteseq = None
        comparator = 0
        text = tts = ""
        first_run, self._first_run = (self._first_run, False)

        if first_run:
            text = tts = DemoTask.__first_run_reply

        if repeat:
            noteseq = self.__current_noteseq
            comparator = self.__current_comparator
            text = tts = ""

        if noteseq is None:
            if not first_run:
                reply = rnd.sample(DemoTask.__next_replies, 1)[0]
                text += reply
                tts += reply

            noteseq = self.__current_noteseq = \
                self.engine.get_rnd_note_sequence(
                    lambda ns:
                        ns != self.__current_noteseq and \
                        ns.is_interval and not ns.is_vertical)
            
            comparator = self.__current_comparator = rnd.randint(0, 1) == 1

        if noteseq:
            reply = f"Какая {rnd.sample(["нота", "из них", ""], 1)[0]} {"выше" if comparator else "ниже"}? "
            text += reply
            tts += reply + self.engine.get_audio_tag(noteseq)

            # debug
            if Config().debug.enabled == True:
                text += f"\n#DEBUG\n{noteseq.name}: {noteseq[0]}, {noteseq[1]}"

            return (text, tts.lower())

        raise ValueError()

    def process_user_reply(self, message: Message)-> tuple[str, str]:
        if MelDictTaskBase.RepeatFilter.is_passed(message.command):
            return self.get_reply(True)

        nn = None
        reply = None
        noteseq = self.__current_noteseq
        comparator = self.__current_comparator

        nn = self._get_last_number(message.command)
        if nn is None:
            text = tts = AliceReplies.DONT_UNDERSTAND
            return (text, tts)

        what = f"Это была «{noteseq.title.lower()}». " if len(noteseq.title) > 0 else ""

        if nn >= 1 and nn <= 2 and noteseq:
            n1 = noteseq[nn-1]
            n2 = noteseq[nn-2]
            if (comparator and n1 > n2) or (not comparator and n1 < n2):
                reply = self._format_correct(what)
                self.correct_score += 1

        if reply is None:
            self.incorrect_score += 1
            reply = self._format_incorrect(what)

        text, tts = self.get_reply() # next note sequence
        
        # debug
        if Config().debug.enabled == True:
            text = f"\n#DEBUG\nОтвет: {nn}, сравн.: {'>' if comparator else '<'}" + text

        return (reply + text, reply + tts)


class PrimaLocationTask(MelDictTaskBase):
    __main_question = "Где основной тон в этом аккорде?"
    __firs_run_reply = \
            "Я буду диктовать арпеджированные аккорды, а ты называй, на каком месте стоит тоника - сверху, в середине или внизу.\n" \
            "Если захочешь прослушать задание ещё раз, просто скажи:\n\n" \
            "[ПОВТОРИ]\n" \
            "\n" \
            "Начинаем! " + __main_question
    
    __next_replies = ["Теперь послушай этот аккорд. ",
                      "Следующий аккорд.",
                      "Идём дальше. Где тоника?",
                      "А в этом аккорде где? "]

    def __init__(self, engine: MelDictEngineBase):
        super().__init__(engine)
        self.__current_noteseq = None

    def reset(self):
        super().reset()
        self.__current_noteseq = None

    def _format_incorrect(self, reply: str = "") -> str:
        noteseq = self.__current_noteseq
        reply = f"Правильный ответ - {noteseq.prima_location_str.lower()}. " if noteseq and self.show_right else ""
        return super()._format_incorrect(reply)

    def get_reply(self, repeat: bool = False)-> tuple[str, str]:
        noteseq = None
        text = tts = ""
        first_run, self._first_run = (self._first_run, False)

        if first_run:
            text = tts = PrimaLocationTask.__firs_run_reply

        if repeat:
            noteseq = self.__current_noteseq
            text = tts = ""

        if noteseq is None:
            if not first_run:
                reply = rnd.sample(PrimaLocationTask.__next_replies, 1)[0]
                text += reply
                tts += reply

            noteseq = self.__current_noteseq = self.engine.get_rnd_note_sequence(
                lambda ns:
                    ns != self.__current_noteseq and \
                    ns.is_triad and not ns.is_vertical and \
                    ns.prima_location != MusicNoteSequence.PRIMALOC_UNKNOWN)

        if noteseq:
            if repeat: text = tts = PrimaLocationTask.__main_question

            # debug
            if Config().debug.enabled == True:
                text += f"\n#DEBUG\nЗагадан: {noteseq.name} - {noteseq.prima_location_str}. "

            return (text, (tts + self.engine.get_audio_tag(noteseq)).lower())

        raise ValueError()

    def process_user_reply(self, message: Message)-> tuple[str, str]:
        if MelDictTaskBase.RepeatFilter.is_passed(message.command):
            return self.get_reply(True)

        reply = ""
        noteseq = self.__current_noteseq
        answer = MusicNoteSequence.PRIMALOC_UNKNOWN

        if CmdFilter.passed(message.command, ("внизу", "снизу"), ("не", "нет")):
            answer = MusicNoteSequence.PRIMALOC_BOTTOM
        elif CmdFilter.passed(message.command, ("середин", "посреди"), ("не", "нет")):
            answer = MusicNoteSequence.PRIMALOC_MIDDLE
        elif CmdFilter.passed(message.command, ("сверху", "наверху", "вверху"), ("не", "нет")):
            answer = MusicNoteSequence.PRIMALOC_TOP
        else:
            text = tts = AliceReplies.DONT_UNDERSTAND
            return (text, tts)

        if answer > MusicNoteSequence.PRIMALOC_UNKNOWN and noteseq and noteseq.prima_location == answer:
            self.correct_score += 1
            reply = self._format_correct()
        else:
            self.incorrect_score += 1
            reply = self._format_incorrect()

        text, tts = self.get_reply() # next note sequence
        return (reply + text, (reply + tts).lower())


class CadenceTask(MelDictTaskBase):
    __firs_run_reply = "Я продиктую аккорд, а потом каденцию, а ты угадай каким он был по счету. "

    __next_replies = ["Продолжаем диктант. ",
                      "Идём дальше. ",
                      " "]

    def __init__(self, engine, first_run = True):
        super().__init__(engine, first_run)
        self.__cadence = None
        self.__guessed_index = 0

    def reset(self):
        super().reset()
        self.__cadence = None
        self.__guessed_index = 0

    def get_reply(self, repeat: bool = False)-> tuple[str, str]:
        cadence = None
        guessed_index = 0
        text = tts = ""
        first_run, self._first_run = (self._first_run, False)

        if first_run:
            text = tts = CadenceTask.__firs_run_reply

        if repeat:
            text = tts = ""
            cadence = self.__cadence
            guessed_index = self.__guessed_index

        if cadence is None:
            if not first_run:
                reply = rnd.sample(CadenceTask.__next_replies, 1)[0]
                text += reply
                tts += reply

            maj = rnd.randint(0, 1) == 1

            tns = self.engine.get_rnd_note_sequence(
                lambda ns: ns.is_tonic and ns.is_major == maj and not ns.is_vertical)
            if tns is None: raise ValueError(f"Не удалось найти тонику: {'maj' if maj else 'min'}, arp")

            sdns = self.engine.get_rnd_note_sequence(
                lambda ns: ns.is_subdominant and ns.is_major == maj and not ns.is_vertical)
            if sdns is None: raise ValueError(f"Не удалось найти субдоминанту: {'maj' if maj else 'min'}, arp")

            dns = self.engine.get_rnd_note_sequence(
                lambda ns: ns.is_dominant and ns.is_major == maj and not ns.is_vertical)
            if dns is None: raise ValueError(f"Не удалось найти доминанту: {'maj' if maj else 'min'}, arp")

            cadence = self.__cadence = rnd.sample([tns, sdns, dns], 3) # shuffle cadence
            guessed_index = self.__guessed_index = rnd.randint(0, 2) # guess chord number

        if cadence:
            guessed_noteseq = cadence[guessed_index]

            reply = f"Прослушай этот аккорд в {'мажоре' if guessed_noteseq.is_major else 'миноре'}. "
            guessed_audio = self.engine.get_audio_tag(guessed_noteseq.file_name)
            text += reply
            tts += f"{reply}{guessed_audio}"

            reply = "Теперь я продиктую каденцию. "
            text += reply
            tts += f"{reply}"
            tts += "".join(self.engine.get_audio_tag(ns) if i != guessed_index else guessed_audio \
                           for i, ns in enumerate(cadence))

            reply = "Каким был по счету этот аккорд? "
            text += reply
            tts += reply

            # debug
            if Config().debug.enabled == True:
                text += "\n#DEBUG\n"
                for i, ns in enumerate(cadence):
                    text += f"\n{i + 1}. {ns.name} - {ns.title}. "
                text += f"\nЗагадан: {guessed_index + 1}"

            return (text, tts.lower())

        raise ValueError()


    def process_user_reply(self, message: Message)-> tuple[str, str]:
        if MelDictTaskBase.RepeatFilter.is_passed(message.command):
            return self.get_reply(True)

        nn = None
        reply = None
        cadence = self.__cadence
        guessed_index = self.__guessed_index

        if cadence is None:
            raise "Каденция не создана"

        nn = self._get_last_number(message.command)
        if nn is None:
            text = tts = AliceReplies.DONT_UNDERSTAND
            return (text, tts)

        guessed_noteseq = cadence[guessed_index]
        what = f"Это был{'о' if guessed_noteseq.title.endswith('е') else ''} «{guessed_noteseq.title.lower()}». "

        if nn >= 1 and nn <= 3 and nn - 1 == guessed_index:
            reply = self._format_correct(what)
            self.correct_score += 1
        else:
            num_str = "первым" if guessed_index == 0 else \
                      "вторым" if guessed_index == 1 else \
                      "третьим"

            self.incorrect_score += 1
            reply = self._format_incorrect(f"Он был {num_str} по счёту. {what}")

        text, tts = self.get_reply() # next cadence
        
        # debug
        if Config().debug.enabled == True:
            text = f"\n#DEBUG\nОтвет: {nn}, загадан: {guessed_index + 1}" + text

        return (reply + text, reply + tts)