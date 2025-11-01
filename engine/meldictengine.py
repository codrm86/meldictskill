from engine.levels.base_level import MelDictLevelBase
from engine.levels.demo_level import DemoLevel
from engine.levels.missed_note_level import MissedNoteLevel
from engine.levels.prima_location_level import PrimaLocationLevel
from engine.levels.cadence_level import CadenceLevel
from engine.levels.exam_level import ExamLevel
from engine.meldictenginebase import MelDictEngineBase
from engine.maindb import MainDB
from myconstants import *
from voicemenu import VoiceMenu

class MelDictEngine(MelDictEngineBase):
    def __init__(self, skill_id):
        super().__init__(skill_id)
        self._demo_level = DemoLevel(self)
        self._missed_note_level = MissedNoteLevel(self)
        self._prima_loc_level = PrimaLocationLevel(self)
        self._cadence_level = CadenceLevel(self)
        self._exam = ExamLevel(self, self._missed_note_level, self._prima_loc_level, self._cadence_level)
        self._current_level = None

    @MelDictEngineBase.mode.setter
    def mode(self, value: int):
        self._mode = max(GameMode.UNKNOWN, value)
        MainDB().clear_used()

        match self._mode:
            case GameMode.DEMO:
                self._current_level = None
                self._demo_level.reset()

            case GameMode.EXAM:
                self._current_level = None
                self._exam.reset()

    def get_rules_reply(self) -> tuple[str, str]:
        text, tts = VoiceMenu().main_menu.rules
        return text, tts

    def get_stats_reply(self) -> tuple[str, str]:
        match self.mode:
            case GameMode.DEMO | GameMode.TRAIN:
                text, tts = VoiceMenu().root.level_not_scored()
            case _:
                text, tts = self._exam.get_stats_reply() if self._exam.started \
                    else VoiceMenu().root.no_score()

        return text, tts

    def get_reply(self) -> tuple[str, str]:
        self._assert_mode()
        level: MelDictLevelBase = None

        match self.mode:
            case GameMode.INIT:
                noteseq = MainDB().rnd(
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
                text, tts = vm.main_menu.train_menu(
                    missed_note = vm.levels.missed_note.name,
                    prima_location = vm.levels.prima_location.name,
                    cadence = vm.levels.cadence.name)
                return text, tts

            case GameMode.DEMO:
                level = self._demo_level

            case GameMode.TRAIN:
                level = self._current_level

            case GameMode.EXAM:
                level = self._exam

        if level:
            text, tts = level.get_reply()
            return text, tts

        return VoiceMenu().root.dont_understand()
    
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