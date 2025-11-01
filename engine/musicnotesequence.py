from collections.abc import Sequence
from typing import Iterable
from engine.musicnote import MusicNote

class MusicNoteSequence(Sequence):
    PRIMALOC_UNKNOWN = -1
    PRIMALOC_BOTTOM = 0
    PRIMALOC_MIDDLE = 1
    PRIMALOC_TOP = 2

    INVERSION_UNKNOWN = -1
    INVERSION_MAIN = 0
    INVERSION_FIRST = 1
    INVERSION_SECOND = 2

    def __init__(self, vertical: bool, *notes: Iterable[MusicNote] | Iterable[str],
                 id: str = None,
                 base_chord: str = None,
                 chord_str: str = None,
                 interval_str: str = None,
                 tts_name: str = None,
                 tonality_maj: bool = False,
                 chord_maj: bool = False,
                 prima_location: str | int = None,
                 inversion: str | int = None):
        super().__init__()
        assert notes

        self.__is_ascending, self.__missed_note, self.__notes = self.__parse_notes(notes)
        assert len(self) > 0

        self.__id = id if isinstance(id, str) else ""
        self.__base_chord = base_chord if isinstance(base_chord, str) else ""
        self.__prima_location = MusicNoteSequence.PRIMALOC_UNKNOWN
        self.__inversion = MusicNoteSequence.INVERSION_UNKNOWN
        self.__is_tonic = self.__is_dominant = self.__is_subdominant = False
        self.__is_vertical = vertical == True
        self.__is_tonality_maj = tonality_maj == True
        self.__is_chord_maj = chord_maj == True
        self.__tts_name = tts_name if isinstance(tts_name, str) and tts_name != "" else None

        # parse prima location
        if isinstance(prima_location, str):
            self.__prima_location = MusicNoteSequence.prima_location_str_to_int(prima_location)
        elif isinstance(prima_location, int):
            assert prima_location >= MusicNoteSequence.PRIMALOC_UNKNOWN and prima_location <= MusicNoteSequence.PRIMALOC_TOP
            self.__prima_location = prima_location

        # parse inversion
        if isinstance(inversion, str):
            self.__inversion = MusicNoteSequence.inversion_str_to_int(inversion)
        elif isinstance(inversion, int):
            assert inversion >= MusicNoteSequence.INVERSION_UNKNOWN and inversion <= MusicNoteSequence.INVERSION_SECOND
            self.__inversion = inversion

        # parse triad or interval characteristics and set title
        if self.is_triad and isinstance(chord_str, str):
            self.__name = chord_str
            self.__is_tonic, self.__is_dominant, self.__is_subdominant = \
                MusicNoteSequence.__parse_chord_str(chord_str)
        elif self.is_interval and isinstance(interval_str, str):
            self.__name = interval_str
        else:
            self.__name = ""

    @property
    def is_ascending(self) -> bool: return self.__is_ascending
    @property
    def is_interval(self) -> bool: return len(self) == 2
    @property
    def is_triad(self) -> bool: return len(self) == 3
    @property
    def is_tonic(self) -> bool: return self.__is_tonic
    @property
    def is_dominant(self) -> bool: return self.__is_dominant
    @property
    def is_subdominant(self) -> bool: return self.__is_subdominant
    @property
    def missed_note(self) -> int: return self.__missed_note
    @property
    def id(self) -> str: return self.__id
    @property
    def base_chord(self) -> str: return self.__base_chord
    @property
    def is_vertical(self) -> bool: return self.__is_vertical
    @property
    def is_tonality_maj(self) -> bool: return self.__is_tonality_maj
    @property
    def is_chord_maj(self) -> bool: return self.__is_chord_maj
    @property
    def name(self) -> str: return self.__name
    @property
    def tts_name(self) -> str: return self.__tts_name if isinstance(self.__tts_name, str) and self.__tts_name != "" else self.name
    @tts_name.setter
    def tts_name(self, value: str): self.__tts_name = value
    @property
    def prima_location(self) -> int: return self.__prima_location
    @property
    def prima_location_str(self) -> str: return MusicNoteSequence.prima_location_int_to_str(self.prima_location)
    @property
    def inversion(self) -> int: return self.__inversion
    @property
    def inversion_str(self) -> str: return MusicNoteSequence.inversion_int_to_str(self.__inversion)
    @property
    def file_name(self) -> str: return MusicNoteSequence.get_file_name(self.__is_vertical, self)

    def __iter__(self):
        self.__note_index = 0
        return self

    def __next__(self):
        if self.__note_index >= len(self):
            raise StopIteration()

        note = self.__notes[self.__note_index]
        self.__note_index += 1
        return note

    def __getitem__(self, i):
        return self.__notes[i]

    def __len__(self):
        return len(self.__notes)
    
    def __str__(self):
        return " ".join(str(note) for note in self.__notes)

    @staticmethod
    def get_file_name(vertical: bool, notes: Iterable[MusicNote]) -> str:
        file_name = ""

        for i, n in enumerate(notes):
            file_name += f"{'_' if i > 0 else ''}{n.note}{'s' if n.diez else ''}{n.octave}"

        return file_name + ("_ver" if vertical else "")

    @staticmethod
    def prima_location_str_to_int(prima_location: str) -> int:
        if prima_location and len(prima_location) > 0:
            prima_location = prima_location.lower()
            if "низ" in prima_location: return MusicNoteSequence.PRIMALOC_BOTTOM
            if "серед" in prima_location: return MusicNoteSequence.PRIMALOC_MIDDLE
            if "верх" in prima_location: return MusicNoteSequence.PRIMALOC_TOP

        return MusicNoteSequence.PRIMALOC_UNKNOWN

    @staticmethod
    def prima_location_int_to_str(prima_location: int) -> str:
        match prima_location:
            case MusicNoteSequence.PRIMALOC_BOTTOM: return "Внизу"
            case MusicNoteSequence.PRIMALOC_MIDDLE: return "В середине"
            case MusicNoteSequence.PRIMALOC_TOP: return "Наверху"
        return ""

    @staticmethod
    def inversion_str_to_int(inversion: str) -> int:
        if isinstance(inversion, str) and len(inversion) > 0:
            match inversion[0].lower():
                case "о": return MusicNoteSequence.INVERSION_MAIN
                case "п": return MusicNoteSequence.INVERSION_FIRST
                case "в": return MusicNoteSequence.INVERSION_SECOND

        return MusicNoteSequence.INVERSION_UNKNOWN

    @staticmethod
    def inversion_int_to_str(inversion: int) -> str:
        match inversion:
            case MusicNoteSequence.INVERSION_MAIN: return "Основной вид"
            case MusicNoteSequence.INVERSION_FIRST: return "Первое обращение"
            case MusicNoteSequence.INVERSION_SECOND: return "Второе обращение"
        return ""

    @staticmethod
    def __parse_chord_str(chord_str: str) -> tuple[bool, bool, bool]:
        is_tonic = is_dominant = is_subdominant = False

        if isinstance(chord_str, str) and len(chord_str) > 0:
            s = chord_str[0].lower()
            is_tonic = s == "т" or s == "t"
            is_dominant = s == "д" or s == "d"
            is_subdominant = s == "с" or s == "s"

        return (is_tonic, is_dominant, is_subdominant)

    @staticmethod
    def __parse_notes(notes: Iterable[MusicNote] | Iterable[str]) -> tuple[bool, int | None, tuple[MusicNote, ...]]:
        notes_list = list[MusicNote]()
        ascending = True
        missed = None
        prev_note = None

        for i, note in enumerate(notes):
            if isinstance(note, str) and len(note) > 0: # note is str
                note = MusicNote(note)
                notes_list.append(note)
            elif isinstance(note, MusicNote): # note is MusicNote
                notes_list.append(note)
            else:
                missed = i
                continue

            ascending = ascending and (prev_note is None or prev_note < note)
            prev_note = note

        return ascending, missed, tuple(notes_list)
