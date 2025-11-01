import os
import logging
import pandas as pd
import random as rnd
from typing import Callable, Iterable
from engine.musicnotesequence import MusicNoteSequence
from config import Config
from singleton import SingletonMeta
from myconstants import *
from abspath import abs_path

class MainDB(metaclass=SingletonMeta):
    def __init__(self):
        self.__data = list[MusicNoteSequence]()
        self.__tts = dict[str, str]()
        self.__used_noteseqs = set[MusicNoteSequence]()
        self.__file = None

    @property
    def file(self) -> str: return self.__file

    def __iter__(self):
        return iter(self.__data)
    
    def __getitem__(self, index):
        return self.__data[index]

    def __len__(self):
        return len(self.__data)

    def clear_used(self):
        self.__used_noteseqs.clear()

    def iterate(self, predicate: Callable[[MusicNoteSequence], bool] = None) -> Iterable[MusicNoteSequence]:
        for noteseq in self.__data:
            if predicate is None or predicate(noteseq) == True:
                yield noteseq

    def shuffle(self, predicate: Callable[[MusicNoteSequence], bool] = None) -> Iterable[MusicNoteSequence]:
        filtered = 0
        dblen = len(self.__data)

        if dblen == 0: return

        for _ in range(2):
            for i in rnd.sample(range(0, dblen), dblen):
                noteseq = self.__data[i]
                if predicate is None or predicate(noteseq) == True:
                    if noteseq not in self.__used_noteseqs:
                        self.__used_noteseqs.add(noteseq)
                        filtered += 1
                        yield noteseq

            if filtered == 0 and len(self.__used_noteseqs) > 0:
                self.__used_noteseqs.clear()
                continue
            break

    def rnd(self, predicate: Callable[[MusicNoteSequence], bool] = None) -> MusicNoteSequence:
        for noteseq in self.shuffle(predicate):
            return noteseq

    @classmethod
    def load(self):
        config = Config()
        instance = self()
        instance.__load_tts(config)
        instance.__load_main_db(config)
        return instance

    def __load_tts(self, config: Config):
        tts_db = abs_path(config.data.tts_db)

        try:
            if not os.path.isfile(tts_db):
                return

            logging.info("Загрузка файла TTS")
            df = pd.read_csv(tts_db, sep=SEP, encoding=UTF8, index_col="text")
            df.index = df.index.str.lower()
            self.__tts = df.tts.dropna().to_dict()

            logging.info(f"Файл TTS загружен")
        except Exception as e:
            logging.error(f"Ошибка загрузки файла TTS \"{tts_db}\"")
            raise e

    def __load_main_db(self, config: Config):
        main_db = abs_path(config.data.main_db)

        try:
            if not os.path.isfile(main_db):
                return None

            logging.info(f"Загрузка базы трезвучий")
            df = pd.read_csv(main_db, sep=SEP, encoding=UTF8, index_col="id")
            data = list[MusicNoteSequence]()

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

                if noteseq.is_interval:
                    distance = abs(noteseq[0].midi_code - noteseq[1].midi_code)
                    if distance > 9: # 9 полутонов == 4,5 тона - секста (максимум)
                        logging.warning(f"Странный интервал {distance / 2:.1f} тонов:\n{row}")
            
            self.__data = data
            self.__file = main_db
            self.clear_used()

            logging.info(f"База трезвучий загружена")
        except Exception as e:
            logging.error(f"Ошибка загрузки базы трезвучий \"{main_db}\"")
            raise e