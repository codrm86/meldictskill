import os
import logging
import pandas as pd
import chordgen
from aliceio.types import FSInputFile
from aliceio import Skill
from singleton import SingletonMeta
from config import Config
from myconstants import *
from musicnotesequence import MusicNoteSequence

class YandexWebSounds(metaclass=SingletonMeta):
    def __init__(self):
        self.__websounds = dict[str, str]()

    def get_cloud_id(self, nsf: str | MusicNoteSequence):
        return self.__websounds.get(nsf.file_name if isinstance(nsf, MusicNoteSequence) else nsf)

    @classmethod
    def load(self):
        try:
            config = Config()
            if not os.path.isfile(config.data.websounds_db):
                return

            logging.info(f"Загрузка базы облачных идентификаторов звуков")

            df = pd.read_csv(config.data.websounds_db, sep=SEP, encoding=UTF8, index_col="file_name")
            self().__websounds = df.cloud_id.dropna().to_dict()

            logging.info(f"База облачных идентификаторов звуков загружена")
        except Exception as e:
            logging.error(f"Ошибка загрузки базы облачных идентификаторов звуков \"{config.data.websounds_db}\"")
            raise e

    @staticmethod
    async def upload_websounds(skill: Skill):
        # удаляем все ранее загруженные звуки
        logging.info("Получение списка ранее загруженных в навык звуков и их удаление")
        pre_sounds = await skill.get_sounds()
        count = 0

        for web_sound in pre_sounds.sounds:
            try:
                await skill.delete_sound(web_sound.id)
                count += 1
                logging.info(f"Звук удалён: id={web_sound.id}")
            except Exception as e:
                logging.error(f"Ошибка удаления звука {web_sound.id}.", exc_info=e)
                continue

        logging.info(f"Всего звуков удалено: {count}")

        websounds = pd.DataFrame(columns=["file_name", "cloud_id"])
        count = 0

        # загружаем все звуки из папки sounds
        logging.info(f"Загрузка звуков в облачное хранилище навыка")
        config = Config()

        for f in filter(lambda f: f.endswith(chordgen.OPUS_EXT), os.listdir(config.data.websounds_folder)):
            try:
                sound_file = os.path.join(config.data.websounds_folder, f)
                # logging.info(f"Загрузка звука: {f}")

                fsfile = FSInputFile(sound_file)
                result = await skill.upload_sound(fsfile)
                count += 1
                websounds.loc[len(websounds)] = [f.split(".")[0], result.sound.id]
                logging.info(f"Звук загружен: {f}, id={result.sound.id}")
            except Exception as e:
                logging.warning(f"Ошибка загрузки звука {f}.", exc_info=e)
                continue

        logging.info(f"Всего звуков загружено: {count}")
        logging.info("Сохранение базы облачных идентификаторов звуков")

        # создаём папку для сохранения базы облачных идентификаторов звуков
        os.makedirs(os.path.dirname(config.data.websounds_db), exist_ok=True)

        # сохраняем файл базы облачных идентификаторов звуков
        websounds.to_csv(config.data.websounds_db, sep=SEP, encoding=UTF8, index=False)

        logging.info(f"База облачных идентификаторов звуков сохранена {config.data.websounds_db}")