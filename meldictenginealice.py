import os
import logging
import random as rnd
from types import SimpleNamespace as dynamic
from typing import Callable
import pandas as pd
from aliceio.types import Message

from musicnotesequence import *
from musicnote import *
from meldictenginebase import *
from meldictlevels import *
from myfilters import *
from myconstants import *

class MelDictEngineAlice(MelDictEngineBase):
    def __init__(self, skill_id):
        super().__init__(skill_id)
        self.__main_db = list[MusicNoteSequence]()
        self.__websounds = dict[str, str]()
        self.__tts = dict()
        self.__first_run = True
        self.__demo_level = DemoLevel(self)
        self.__missed_note_level = MissedNoteLevel(self)
        self.__cadence_level = CadenceLevel(self)
        self.__prima_loc_level = PrimaLocationLevel(self)
        self.__exam = ExamLevel(self, self.__missed_note_level, self.__prima_loc_level, self.__cadence_level)
        self.__current_level = None
        self.__hamster = False

    @property
    def hamster(self): return self.__hamster
    @hamster.setter
    def hamster(self, value: bool): self.__hamster = value

    @MelDictEngineBase.mode.setter
    def mode(self, value: int):
        self._mode = max(GameMode.UNKNOWN, value)
        match value:
            case GameMode.DEMO:
                self.__current_level = None
                self.__demo_level.reset()

            case GameMode.EXAM:
                self.__current_level = None
                self.__exam.reset()

    def get_stats_reply(self) -> tuple[str, str]:
        match self.mode:
            case GameMode.DEMO | GameMode.TRAIN:
                text, tts = VoiceMenu().root.level_not_scored()
            case _:
                text, tts = self.__exam.get_stats_reply() if self.__exam.started \
                    else VoiceMenu().root.no_score()

        return text, tts

    def get_rules_reply(self) -> tuple[str, str]:
        text, tts = VoiceMenu().main_menu.rules
        return text, tts

    def get_reply(self) -> tuple[str, str]:
        self._assert_mode()

        level: MelDictLevelBase = None

        match self.mode:
            case GameMode.INIT:
                self.mode = GameMode.MENU
                noteseq = self.get_rnd_note_sequence(
                    lambda ns:
                        ns.is_vertical and (ns.is_chord_maj or ns.is_tonality_maj))

                greet = VoiceMenu().main_menu.greetings(first_run=True)
                text, tts = greet(noteseq=self.get_audio_tag(noteseq))
                return text, tts

            case GameMode.MENU: # основное меню
                text, tts = VoiceMenu().main_menu.greetings()
                return text, tts

            case GameMode.DEMO:
                level = self.__demo_level

            case GameMode.TRAIN:
                level = self.__current_level

            case GameMode.TRAIN_MENU:
                vm = VoiceMenu()
                train_menu = vm.main_menu.train_menu(
                    missed_note=vm.levels.missed_note.name,
                    prima_location=vm.levels.prima_location.name,
                    cadence=vm.levels.cadence.name)
                return train_menu

            case GameMode.EXAM:
                level = self.__exam

        if level:
            text, tts = level.get_reply()
            return text, tts

        text, tts = VoiceMenu().root.dont_understand()
        return text, self.format_tts(tts)

    def process_user_reply(self, message: Message) -> tuple[str, str]:
        self._assert_mode()
        level: MelDictLevelBase = None
        vm = VoiceMenu()

        match self.mode:
            case GameMode.MENU: # основное меню
                pass
            case GameMode.DEMO: level = self.__demo_level
            case GameMode.TRAIN: level = self.__current_level
            case GameMode.EXAM: level = self.__exam

            case GameMode.TRAIN_MENU:
                if CmdFilter.passed(message.command, ("пропущенн", "1"), exclude=("нет", "не", )):
                    level = self.__missed_note_level
                elif CmdFilter.passed(message.command, ("тоник", "2"), exclude=("нет", "не", "тонир", "тонал")):
                    level = self.__prima_loc_level
                elif CmdFilter.passed(message.command, ("каденци", "3"), exclude=("нет", "не", )):
                    level = self.__cadence_level

                if level:
                    level.reset()
                    level.show_right = True

                    self.mode = GameMode.TRAIN
                    self.__current_level = level
                    text, tts = level.get_reply()
                    return text, tts

        if level:
            text, tts = level.process_user_reply(message)

            if level.finished:
                complete_text, complete_tts = vm.root.level_complete()
                stat_text = stat_tts = None

                match self.mode:
                    case GameMode.DEMO:
                        pass
                    case GameMode.EXAM:
                        complete_text, complete_tts = vm.root.exam_complete()
                        stat_text, stat_tts = level.get_stats_reply()
                    case GameMode.TRAIN:
                        stat_text, stat_tts = level.get_stats_reply()
                    case _:
                        complete_text = complete_tts = None

                self.mode = GameMode.MENU
                menu_text, menu_tts = self.get_reply()

                text = self.format_text(text, "\n\n", complete_text, stat_text, menu_text, sep="\n")
                tts = self.format_tts(tts, complete_tts, stat_tts, menu_tts, sep="\n")
            return text, tts

        text, tts = vm.root.dont_understand()
        return text, self.format_tts(tts)

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

    async def load_data(self, main_csv: str, websounds_csv: str, tts_csv: str = None):
        assert isinstance(main_csv, str) and main_csv != ""
        assert isinstance(websounds_csv, str) and websounds_csv != ""

        await self.__load_websounds(websounds_csv)
        self.__load_tts(tts_csv)
        self.__main_db = self.__load_main_db(main_csv)
        self.mode = GameMode.INIT

    async def __load_websounds(self, websounds_csv: str):
        if not os.path.isfile(websounds_csv): return

        csv = pd.read_csv(websounds_csv, sep=SEP, encoding=UTF8, index_col=False)
        self.__websounds = pd.Series(csv.cloud_id.values, csv.file_name).to_dict()

    def __load_tts(self, tts_csv: str):
        try:
            if not os.path.isfile(tts_csv):
                return

            df = pd.read_csv(tts_csv, sep=SEP, encoding=UTF8)
            df.text = df.text.str.lower()
            self.__tts = df.set_index("text").tts.to_dict()
        except Exception as e:
            logging.error(f"Ошибка загрузки файла TTS \"{tts_csv}\"", exc_info=e)
            pass

    def __load_main_db(self, main_csv: str) -> list[MusicNoteSequence]:
        if not os.path.isfile(main_csv):
            return

        df = pd.read_csv(main_csv, sep=SEP, encoding=UTF8, index_col="name")
        data = list()

        for index, row in df.iterrows():
            noteseq = MusicNoteSequence(row.vertical,
                                        row.note_1, row.note_2, row.note_3,
                                        id=index,
                                        base_chord=row.base_chord,
                                        chord_str=row.chord_type,
                                        interval_str=row.interval,
                                        tonality_maj=row.tonality_maj,
                                        chord_maj=row.chord_maj,
                                        prima_location=row.prima_location,
                                        inversion=row.inversion)

            noteseq.tts_name = self.__tts.get(noteseq.name.lower(), None)
            data.append(noteseq)
        return data