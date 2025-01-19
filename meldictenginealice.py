import os
import random as rnd
from types import SimpleNamespace as dynamic
from typing import Callable
import pandas as pd
from aliceio.types import Message

from musicnotesequence import *
from musicnote import *
from meldictenginebase import *
from meldicttask import *
from myfilters import *
from myconstants import *

class MelDictEngineAlice(MelDictEngineBase):
    def __init__(self, skill_id):
        super().__init__(skill_id)
        self.__main_db = list[MusicNoteSequence]()
        self.__websounds = dict[str, str]()
        self.__first_run = True
        self.__demo_task = DemoTask(self)
        self.__missed_note_task = MissedNoteTask(self)
        self.__cadence_task = CadenceTask(self)
        self.__prima_loc_task = PrimaLocationTask(self)
        self.__current_task = None

    def get_stats_reply(self) -> tuple[str, str]:
        def format_reply(task: MelDictTaskBase, tts: bool):
            def format_q(s):
                mod100 = abs(s) % 100
                if mod100 < 10 or mod100 > 20:
                    mod10 = abs(s) % 10
                    match mod10: # last digit from int
                        case 1: return "вопрос"
                        case 2 | 3 | 4: return "вопроса"
                return "вопросов"
            fmt_func = self.format_tts if tts else self.format_text
            return fmt_func(f"В режиме «{task.tts_name if tts else task.display_name}» отвечено",
                            f"на {task.correct_score} {format_q(task.correct_score)} правильно",
                            f"и на {task.incorrect_score} {format_q(task.incorrect_score)} неправильно" if task.incorrect_score > 0 else "", ".")

        # в меню возвращаем статистику по всем задачам, по которым были набранны баллы
        if self.mode == GameMode.MENU:
            def reply_line(task: MelDictTaskBase, ts: bool) -> str:
                return f"{format_reply(task, ts)}\n\n" if task.started else ""

            text = self.format_text(
                reply_line(self.__demo_task, False),
                reply_line(self.__missed_note_task, False),
                reply_line(self.__cadence_task, False),
                reply_line(self.__prima_loc_task, False))

            tts = self.format_tts(
                reply_line(self.__demo_task, True),
                reply_line(self.__missed_note_task, True),
                reply_line(self.__cadence_task, True),
                reply_line(self.__prima_loc_task, True))
            
            if text != "":
                return text, tts

        # во всех остальных режимах, возвращаем статистику по текущей задаче
        task = self.__current_task

        if task is None:
            reply = "Ты ещё не прошёл ни один уровень. Выбери режим игры в меню, и пройди все задания. В любое время при прохождении уровня, ты можешь попросить меня назвать набранные баллы."
            return reply, reply

        if not task.started:
            reply = "Ты не начал проходить уровень. Отвечай на вопросы в заданиях и набирай баллы, у тебя всё получится!"
            return reply, reply

        return format_reply(task, False), format_reply(task, True)

    def get_reply(self) -> tuple[str, str]:
        self._assert_mode()

        match self.mode:
            case GameMode.INIT:
                reply = "Рада приветствовать тебя на музыкальном диктанте!\n"
                noteseq = self.get_rnd_note_sequence(
                    lambda ns:
                        ns.is_vertical and (ns.is_chord_maj or ns.is_tonality_maj))

                self.mode = GameMode.MENU
                text, tts = self.get_reply()

                text = self.format_text(
                    reply, text)

                tts = self.format_tts(
                    reply, noteseq,
                    tts)

                return text, tts

            case GameMode.MENU: # основное меню
                first_run, self.__first_run = self.__first_run, False

                def format_reply(ts):
                    def get_name(task: MelDictTaskBase):
                        return task.tts_name if ts else task.display_name
                    reply = None
                    if first_run:
                        reply = "Доступно четыре режима игры.\n" \
                                f"1. [{get_name(self.__demo_task)}] - Демонстрационный режим.\n" \
                                f"2. [{get_name(self.__missed_note_task)}] - Поиск пропущенного звука в аккорде.\n" \
                                f"3. [{get_name(self.__cadence_task)}] - Угадывание аккорда в последовательности.\n" \
                                f"4. [{get_name(self.__prima_loc_task)}] - Определение основного тона аккорда.\n"\
                                f"\n" \
                                f"Чтобы выйти в это меню, в любое время скажи:\n" \
                                f"[МЕНЮ] или [ПЕРЕЗАПУСК].\n" \
                                f"Для выхода из музыкального диктанта скажи:\n" \
                                f"[ХВАТИТ]"
                    else:
                        reply =  f"Скажи [{get_name(self.__demo_task)}], чтобы запустить демонстрационный режим.\n" \
                                 f"[{get_name(self.__missed_note_task)}] - чтобы искать пропущенный звук в аккорде.\n" \
                                 f"[{get_name(self.__cadence_task)}], чтобы угадывать аккорд в последовательности.\n" \
                                 f"[{get_name(self.__prima_loc_task)}], чтобы определять основной тон аккорда.\n" \
                                  "Скажи [МЕНЮ] или [ПЕРЕЗАПУСК] чтобы выйти в это меню."
                    if ts:
                        reply = reply.replace("1", "первый") \
                                     .replace("2", "второй") \
                                     .replace("3", "третий") \
                                     .replace("4", "четвёртый") \
                                     .replace("[", "").replace("]", "!")
                    return reply
                return format_reply(False), format_reply(True)

            case GameMode.TASK: # демо-режим
                task = self.__current_task
                result = task.get_reply() if task else (None, None)
                if result: return result

        text = tts = AliceReplies.DONT_UNDERSTAND
        return text, tts

    def process_user_reply(self, message: Message) -> tuple[str, str]:
        self._assert_mode()

        match self.mode:
            case GameMode.MENU: # основное меню
                new_task: MelDictTaskBase = None

                if CmdFilter.passed(message.command, ("демо", "1"), exclude=("нет", "не", "демотив")):
                    new_task = self.__demo_task
                elif CmdFilter.passed(message.command, ("пропущенн", "2"), exclude=("нет", "не", )):
                    new_task = self.__missed_note_task
                elif CmdFilter.passed(message.command, ("каденци", "3"), exclude=("нет", "не", )):
                    new_task = self.__cadence_task
                elif CmdFilter.passed(message.command, ("тоник", "4"), exclude=("нет", "не", "тонир", "тонал")):
                    new_task = self.__prima_loc_task

                if new_task:
                    self.mode = GameMode.TASK
                    new_task.show_right = True
                    self.__current_task = new_task
                    new_task.reset()
                    return self.get_reply()

            case GameMode.TASK:
                task = self.__current_task
                result = task.process_user_reply(message) if task else None
                if result: return result

            case _:
                raise ValueError("Неизвестный режим")

        text = tts = AliceReplies.DONT_UNDERSTAND
        return (text, tts.lower())

    def get_audio_tag(self, nsf: str | MusicNoteSequence) -> str:
        cloud_id = self.__websounds.get(nsf.file_name if isinstance(nsf, MusicNoteSequence) else nsf)
        return f'<speaker audio="dialogs-upload/{self.skill_id}/{cloud_id}.opus">' if cloud_id else ""

    def iter_note_sequences(self, predicate: Callable[[MusicNoteSequence], bool] = None) -> Iterable[MusicNoteSequence]:
        for noteseq in self.__main_db:
            if predicate is None or predicate(noteseq) == True:
                yield noteseq

    def shuffle_note_sequences(self, predicate: Callable[[MusicNoteSequence], bool] = None) -> Iterable[MusicNoteSequence]:
        dblen = len(self.__main_db)
        for i in rnd.sample(range(0, dblen), dblen):
            noteseq = self.__main_db[i]
            if predicate is None or predicate(noteseq) == True:
                yield noteseq

    def get_rnd_note_sequence(self, predicate: Callable[[MusicNoteSequence], bool] = None) -> MusicNoteSequence:
        for noteseq in self.shuffle_note_sequences(predicate):
            return noteseq

    async def load_data(self, main_csv: str, websounds_csv: str):
        assert isinstance(main_csv, str) and main_csv != ""
        assert isinstance(websounds_csv, str) and websounds_csv != ""

        await self.__load_websounds(websounds_csv)
        self.__main_db = self.__load_main_db(main_csv)
        self.mode = GameMode.INIT

    async def __load_websounds(self, websounds_csv: str):
        if not os.path.isfile(websounds_csv): return

        csv = pd.read_csv(websounds_csv, sep=SEP, encoding=UTF8, index_col=False)
        self.__websounds = pd.Series(csv.cloud_id.values, csv.file_name).to_dict()

    def __load_main_db(self, main_csv: str) -> list[MusicNoteSequence]:
        if not os.path.isfile(main_csv):
            return

        df = pd.read_csv(main_csv, sep=SEP, encoding=UTF8, index_col="name")
        # unavail_df = pd.DataFrame(columns=["file_name"])
        data: list[MusicNoteSequence] = list()
        # filenames = set()

        for name, row in df.iterrows():
            noteseq = MusicNoteSequence(row.vertical,
                                        row.note_1, row.note_2, row.note_3,
                                        name=name,
                                        base_chord=row.base_chord,
                                        chord_str=row.chord_type,
                                        interval_str=row.interval,
                                        tonality_maj=row.tonality_maj,
                                        chord_maj=row.chord_maj,
                                        prima_location=row.prima_location,
                                        inversion=row.inversion)

            data.append(noteseq)
        #     file_name = noteseq.file_name

        #     if file_name not in filenames:
        #         filenames.add(file_name)
        #         if file_name not in self.__websounds:
        #             unavail_df.loc[len(unavail_df)] = [file_name]

        # if len(unavail_df) > 0:
        #     unavail_df.to_csv("web_sounds_unavailable.csv", sep=SEP, encoding=UTF8, index=False)

        return data