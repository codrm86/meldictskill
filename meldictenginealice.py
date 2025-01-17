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
        self.__current_task = None
        self.__first_run = True
        self.__demo_task = DemoTask(self)
        self.__prima_loc_task = PrimaLocationTask(self)
        self.__cadence_task = CadenceTask(self)

    def reset(self):
        super().reset()
        task, self.__current_task = (self.__current_task, None)
        if task: task.reset()

    def get_reply(self) -> tuple[str, str]:
        self._assert_mode()

        reply = ""
        text = ""
        tts = ""

        match self.mode:
            case GameMode.INIT:
                reply = "Рада приветствовать тебя на музыкальном диктанте. "
                noteseq = self.get_rnd_note_sequence()
                ts = reply + self.get_audio_tag(noteseq.file_name) if noteseq else reply
                self.mode = GameMode.MENU
                text, tts = self.get_reply()

                return (reply + text, ts + tts)

            case GameMode.MENU: # основное меню
                first_run, self.__first_run = (self.__first_run, False)
                if first_run:
                    text = tts = "Доступно три режима игры.\n" \
                                "1. [ДЕМО] - Демонстрационный режим.\n" \
                                "2. [ТОНИКА] - Определение основного тона аккорда.\n"\
                                "3. [КАДЕНЦИЯ] - Угадывание аккорда в каденции.\n" \
                                "\n" \
                                "Чтобы выйти в это меню, в любое время скажи:\n" \
                                "[МЕНЮ] или [ПЕРЕЗАПУСК].\n" \
                                "Для выхода из музыкального диктанта скажи:\n" \
                                "[ХВАТИТ] "
                else:
                    text = tts = "Скажи [ДЕМО], чтобы запустить демонстрационный режим.\n" \
                                 "Скажи [ТОНИКА], чтобы определять основной тон аккорда.\n" \
                                 "Скажи [КАДЕНЦИЯ], чтобы угадывать аккорд в каденции.\n" \
                                 "Скажи [МЕНЮ] или [ПЕРЕЗАПУСК] чтобы выйти в это меню. "

                tts = tts.replace("1", "первый") \
                         .replace("2", "второй") \
                         .replace("3", "третий") \
                         .replace("4", "четвёртый")
                return (text, tts.lower())

            case GameMode.TASK: # демо-режим
                task = self.__current_task
                result = task.get_reply() if task else None
                if result: return result

        text = tts = AliceReplies.DONT_UNDERSTAND
        return (text, tts.lower())


    def process_user_reply(self, message: Message) -> tuple[str, str]:
        self._assert_mode()

        match self.mode:
            case GameMode.MENU: # основное меню
                new_task = None

                if CmdFilter.passed(message.command, ("демо", "1"), exclude=("нет", "не", "демон", "демотив")):
                    new_task = self.__demo_task
                elif CmdFilter.passed(message.command, ("тоника", "2"), exclude=("нет", "не", "тонир", "тонал")):
                    new_task = self.__prima_loc_task
                elif CmdFilter.passed(message.command, ("каденция", "3"), exclude=("нет", "не", "тонир", "тонал")):
                    new_task = self.__cadence_task

                if new_task:
                    self.mode = GameMode.TASK
                    new_task.show_right = True
                    self.__current_task = new_task
                    return self.get_reply()

            case GameMode.TASK: # демо-режим
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
                                        major=row.tonality_maj,
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