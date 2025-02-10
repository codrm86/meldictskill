from typing import Iterable
from aliceio.types import AliceResponse, Response, Message, TextButton
from musicnotesequence import MusicNoteSequence
from musicnote import MusicNote
from meldictenginebase import MelDictEngineBase
from meldictlevels import MelDictLevelBase, DemoLevel, MissedNoteLevel, PrimaLocationLevel, CadenceLevel, ExamLevel
from myfilters import CmdFilter
from myconstants import *
from maindb import MainDB
from yandex_websounds import YandexWebSounds
from voicemenu import VoiceMenu

class MelDictEngineAlice(MelDictEngineBase):
    def __init__(self, skill_id):
        super().__init__(skill_id)
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
        MainDB().clear_used()

        match self._mode:
            case GameMode.DEMO:
                self.__current_level = None
                self.__demo_level.reset()

            case GameMode.EXAM:
                self.__current_level = None
                self.__exam.reset()

    def _is_help_button(self, button: TextButton) -> bool:
        return button and button.payload and button.payload.get("help", False) == True

    def _is_repeat_button(self, button: TextButton) -> bool:
        return button and button.payload and button.payload.get("repeat", False) == True

    def _get_button_mode(self, button: TextButton) -> int:
        if button and button.payload:
            value = button.payload.get("set_mode")
            if isinstance(value, int) and value >= GameMode.MENU: return value
        return None

    def _get_button_level(self, button: TextButton) -> int:
        if button and button.payload:
            value = button.payload.get("set_level")
            if isinstance(value, int): return value
        return None

    def get_buttons(self) -> Iterable[TextButton]:
        level = None
        vm = VoiceMenu()
        back_mode = GameMode.MENU
        set_mode_key = "set_mode"

        match self.mode:
            case GameMode.DEMO:
                level = self.__demo_level
            case GameMode.TRAIN:
                level = self.__current_level
                back_mode = GameMode.TRAIN_MENU
            case GameMode.EXAM:
                level = self.__exam

            case GameMode.MENU | GameMode.INIT:
                back_mode = None
                yield TextButton(title=vm.levels.demo.name.text, payload={ set_mode_key: GameMode.DEMO })
                yield TextButton(title=vm.main_menu.train_menu.button, payload={ set_mode_key: GameMode.TRAIN_MENU })
                yield TextButton(title=vm.levels.exam.name.text, payload={ set_mode_key: GameMode.EXAM })

            case GameMode.TRAIN_MENU:
                set_level_key = "set_level"
                yield TextButton(title=vm.levels.missed_note.name.text, payload={ set_level_key: self.__missed_note_level.id })
                yield TextButton(title=vm.levels.prima_location.name.text, payload={ set_level_key: self.__prima_loc_level.id })
                yield TextButton(title=vm.levels.cadence.name.text, payload={ set_level_key: self.__cadence_level.id })

        if level and not level.finished:
            for btn in level.get_buttons():
                yield btn
            yield TextButton(title=VoiceMenu().levels.repeat_buttons().text, payload={ "repeat": True })
        elif not level:
            yield TextButton(title=vm.main_menu.rules.button, payload={ "help": True })

        if back_mode is not None:
            yield TextButton(title=vm.main_menu.back.button, payload={ set_mode_key: back_mode })

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

    def process_back_action(self) -> tuple[str, str]:
        match self.mode:
            case GameMode.MENU:
                text, tts = VoiceMenu().root.no_way_back()
                return text, tts
            case GameMode.DEMO | GameMode.TRAIN_MENU | GameMode.EXAM:
                self.mode = GameMode.MENU
            case GameMode.TRAIN:
                self.mode = GameMode.TRAIN_MENU
            case _:
                text, tts = VoiceMenu().root.dont_understand()
                return text, tts

        text, tts = self.get_reply()
        return text, tts

    def get_reply(self) -> tuple[str, str]:
        self._assert_mode()
        level: MelDictLevelBase = None
        main_db = MainDB()

        match self.mode:
            case GameMode.INIT:
                noteseq = main_db.rnd(
                    lambda ns:
                        ns.is_vertical and (ns.is_chord_maj or ns.is_tonality_maj))

                self.mode = GameMode.MENU
                greet = VoiceMenu().main_menu.greetings(first_run=True)
                text, tts = greet(noteseq = self.get_audio_tag(noteseq))
                return text, tts

            case GameMode.MENU: # основное меню
                text, tts = VoiceMenu().main_menu.greetings()
                return text, tts

            case GameMode.TRAIN_MENU:
                vm = VoiceMenu()
                train_menu = vm.main_menu.train_menu(
                    missed_note = vm.levels.missed_note.name,
                    prima_location = vm.levels.prima_location.name,
                    cadence = vm.levels.cadence.name)
                return train_menu

            case GameMode.DEMO:
                level = self.__demo_level

            case GameMode.TRAIN:
                level = self.__current_level

            case GameMode.EXAM:
                level = self.__exam

        if level:
            text, tts = level.get_reply()
            return text, tts

        text, tts = VoiceMenu().root.dont_understand()
        return text, tts

    def process_user_reply(self, message: Message = None, mode_str: str = None) -> tuple[str, str]:
        self._assert_mode()
        new_mode = None
        new_level_id = None

        match self.mode:
            case GameMode.MENU:
                if mode_str:
                    if CmdFilter.passed(mode_str, ("демо", "продемонстрир")):
                        new_mode = GameMode.DEMO
                    elif CmdFilter.passed(mode_str, ("трениро", "потренир")):
                        new_mode = GameMode.TRAIN_MENU
                    elif CmdFilter.passed(mode_str, "экзамен"):
                        new_mode = GameMode.EXAM

            case GameMode.TRAIN_MENU:
                if CmdFilter.passed(message.command, ("пропущенн", "1"), exclude=("нет", "не", )):
                    new_level_id = self.__missed_note_level.id
                elif CmdFilter.passed(message.command, ("тоник", "2"), exclude=("нет", "не", "тонир", "тонал")):
                    new_level_id = self.__prima_loc_level.id
                elif message and CmdFilter.passed(message.command, ("каденци", "3"), exclude=("нет", "не", )):
                    new_level_id = self.__cadence_level.id

        return self.__process_action(
            new_mode=new_mode,
            new_level_id=new_level_id,
            message=message)

    def process_button_pressed(self, button: TextButton):
        self._assert_mode()

        return self.__process_action(
            self._is_repeat_button(button),
            self._is_help_button(button),
            self._get_button_mode(button),
            self._get_button_level(button),
            button = button)

    def __process_action(
            self,
            repeat: bool = None,
            help: bool = None,
            new_mode: int = None,
            new_level_id: int = None,
            message: Message = None,
            button: TextButton = None,
            ) -> tuple[str, str]:
        if repeat:
            return self.get_reply()

        if help:
            return self.get_rules_reply()

        if new_mode and new_mode >= GameMode.MENU:
            self.mode = new_mode

        level: MelDictLevelBase = None

        match self.mode:
            case GameMode.MENU:
                if new_mode: # нажата кнопка назад из меню тренировки
                    return self.get_reply()

            case GameMode.DEMO: level = self.__demo_level
            case GameMode.TRAIN: level = self.__current_level
            case GameMode.EXAM: level = self.__exam

            case GameMode.TRAIN_MENU:
                if new_level_id == self.__missed_note_level.id:
                    level = self.__missed_note_level
                elif new_level_id == self.__prima_loc_level.id:
                    level = self.__prima_loc_level
                elif new_level_id == self.__cadence_level.id:
                    level = self.__cadence_level
                elif new_mode: # нажата кнопка назад из уровня
                    return self.get_reply()

                if level:
                    self.mode = GameMode.TRAIN
                    self.__current_level = level

        if level is None:
            text, tts = VoiceMenu().root.dont_understand()
            return text, tts

        if new_level_id or new_mode: # уровень только что выбран
            level.reset()

        text, tts = level.get_reply() if new_level_id or new_mode \
            else  level.process_user_reply(message, button)

        if level.finished:
            vm = VoiceMenu()
            complete_text = complete_tts = None
            stat_text = stat_tts = None

            match self.mode:
                case GameMode.DEMO | GameMode.TRAIN:
                    complete_text, complete_tts = vm.root.level_complete()
                case GameMode.EXAM:
                    complete_text, complete_tts = vm.root.exam_complete()
                    stat_text, stat_tts = level.get_stats_reply()

            self.mode = GameMode.MENU
            menu_text, menu_tts = self.get_reply()

            text = self.format_text(text, complete_text, stat_text, menu_text, sep="\n\n")
            tts = self.format_tts(tts, complete_tts, stat_tts, menu_tts, sep=".")
        return text, tts

    def get_audio_tag(self, nsf: str | MusicNoteSequence) -> str:
        cloud_id = YandexWebSounds().get_cloud_id(nsf)
        return f'<speaker audio="dialogs-upload/{self.skill_id}/{cloud_id}.opus">' if cloud_id else ""

    def get_hamster_tag(self) -> str:
        return "<speaker effect=\"hamster\">" if self.hamster else None

    def create_response(self, text: str, tts: str, end_session: bool = False):
        buttons = None if end_session else list(self.get_buttons())

        return AliceResponse(
            response=Response(text=text,
                              tts=self.format_tts(self.get_hamster_tag(), tts, sep=""),
                              end_session=end_session,
                              buttons=buttons))