from typing import Iterable
from aliceio.types import AliceResponse, Response, Message, TextButton
from engine.alice.alice_websounds import AliceWebSounds
from engine.musicnotesequence import MusicNoteSequence
from engine.meldictengine import MelDictEngine
from engine.levels.base_level import MelDictLevelBase
from myfilters import CmdFilter
from myconstants import *
from voicemenu import VoiceMenu

class AliceEngine(MelDictEngine):
    def __init__(self, skill_id):
        super().__init__(skill_id)

        self.__hamster = False

    @property
    def hamster(self): return self.__hamster
    @hamster.setter
    def hamster(self, value: bool): self.__hamster = value

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
                level = self._demo_level
            case GameMode.TRAIN:
                level = self._current_level
                back_mode = GameMode.TRAIN_MENU
            case GameMode.EXAM:
                level = self._exam

            case GameMode.MENU | GameMode.INIT:
                back_mode = None
                yield TextButton(title=vm.levels.demo.name.text, payload={ set_mode_key: GameMode.DEMO })
                yield TextButton(title=vm.main_menu.train_menu.button, payload={ set_mode_key: GameMode.TRAIN_MENU })
                yield TextButton(title=vm.levels.exam.name.text, payload={ set_mode_key: GameMode.EXAM })

            case GameMode.TRAIN_MENU:
                set_level_key = "set_level"
                yield TextButton(title=vm.levels.missed_note.name.text, payload={ set_level_key: self._missed_note_level.id })
                yield TextButton(title=vm.levels.prima_location.name.text, payload={ set_level_key: self._prima_loc_level.id })
                yield TextButton(title=vm.levels.cadence.name.text, payload={ set_level_key: self._cadence_level.id })

        if level and not level.finished:
            for btn in level.get_buttons():
                yield btn
            yield TextButton(title=vm.root.repeat_buttons().text, payload={ "repeat": True })
        elif not level:
            yield TextButton(title=vm.main_menu.rules.button, payload={ "help": True })

        if back_mode is not None:
            yield TextButton(title=vm.root.back_buttons().text, payload={ set_mode_key: back_mode })

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
                    new_level_id = self._missed_note_level.id
                elif CmdFilter.passed(message.command, ("тоник", "2"), exclude=("нет", "не", "тонир", "тонал")):
                    new_level_id = self._prima_loc_level.id
                elif message and CmdFilter.passed(message.command, ("каденци", "3"), exclude=("нет", "не", )):
                    new_level_id = self._cadence_level.id

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

            case GameMode.DEMO: level = self._demo_level
            case GameMode.TRAIN: level = self._current_level
            case GameMode.EXAM: level = self._exam

            case GameMode.TRAIN_MENU:
                if new_level_id == self._missed_note_level.id:
                    level = self._missed_note_level
                elif new_level_id == self._prima_loc_level.id:
                    level = self._prima_loc_level
                elif new_level_id == self._cadence_level.id:
                    level = self._cadence_level
                elif new_mode: # нажата кнопка назад из уровня
                    return self.get_reply()

                if level:
                    self.mode = GameMode.TRAIN
                    self._current_level = level

        text = tts = None

        if level is None:
            text, tts = VoiceMenu().root.dont_understand()
            return text, tts

        if new_level_id or new_mode: # уровень только что выбран
            level.reset()
            text, tts = level.get_reply()
        else:
            text, tts = level.process_user_reply(message, button)

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

            text = self.format_text(text, complete_text, stat_text, menu_text, sep="\n")
            tts = self.format_tts(tts, complete_tts, stat_tts, menu_tts, sep=".")
        return text, tts

    def get_audio_tag(self, nsf: str | MusicNoteSequence) -> str:
        cloud_id = AliceWebSounds().get_cloud_id(nsf)
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