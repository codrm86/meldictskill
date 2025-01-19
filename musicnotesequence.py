from collections.abc import Sequence
from typing import Iterable
from musicnote import MusicNote

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
                 name: str = None,
                 base_chord: str = None,
                 chord_str: str = None,
                 interval_str: str = None,
                 tonality_maj: bool = False,
                 chord_maj: bool = False,
                 prima_location: str | int = None,
                 inversion: str | int = None):
        super().__init__()
        assert notes

        self.__is_ascending, self.__missed_note, self.__notes = self.__parse_notes(notes)
        assert len(self) > 0

        self.__name = name if name else ""
        self.__base_chord = base_chord if base_chord else ""
        self.__prima_location = MusicNoteSequence.PRIMALOC_UNKNOWN
        self.__inversion = MusicNoteSequence.INVERSION_UNKNOWN
        self.__is_tonic = self.__is_dominant = self.__is_subdominant = False
        self.__is_vertical = vertical == True
        self.__is_tonality_maj = tonality_maj == True
        self.__is_chord_maj = chord_maj == True

        # parse prima location
        if isinstance(prima_location, str):
            self.__prima_location = MusicNoteSequence.__prima_location_str_to_int(prima_location)
        elif isinstance(prima_location, int):
            assert prima_location >= MusicNoteSequence.PRIMALOC_UNKNOWN and prima_location <= MusicNoteSequence.PRIMALOC_TOP
            self.__prima_location = prima_location

        # parse inversion
        if isinstance(inversion, str):
            self.__inversion = MusicNoteSequence.__inversion_str_to_int(inversion)
        elif isinstance(inversion, int):
            assert inversion >= MusicNoteSequence.INVERSION_UNKNOWN and inversion <= MusicNoteSequence.INVERSION_SECOND
            self.__inversion = inversion

        # parse triad or interval characteristics and set title
        if self.is_triad and isinstance(chord_str, str):
            self.__title = chord_str
            self.__is_tonic, self.__is_dominant, self.__is_subdominant = \
                MusicNoteSequence.__parse_chord_str(chord_str)
        elif self.is_interval and isinstance(interval_str, str):
            self.__title = interval_str
        else:
            self.__title = ""

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
    def name(self) -> str: return self.__name
    @property
    def base_chord(self) -> str: return self.__base_chord
    @property
    def is_vertical(self) -> bool: return self.__is_vertical
    @property
    def is_tonality_maj(self) -> bool: return self.__is_tonality_maj
    @property
    def is_chord_maj(self) -> bool: return self.__is_chord_maj
    @property
    def title(self) -> str: return self.__title
    @property
    def prima_location(self) -> int: return self.__prima_location
    @property
    def prima_location_str(self) -> str: return MusicNoteSequence.__prima_location_int_to_str(self.prima_location)
    @property
    def inversion(self) -> int: return self.__inversion
    @property
    def inversion_str(self) -> str: return MusicNoteSequence.__inversion_int_to_str(self.__inversion)
    @property
    def file_name(self) -> str: return MusicNoteSequence.__get_file_name(self.__is_vertical, self)

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
        return "".join(str(note) for note in self.__notes)

    @staticmethod
    def __get_file_name(vertical: bool, notes: Iterable[MusicNote]) -> str:
        suffix = ""
        file_name = ""
        count = 0

        for i, n in enumerate(notes):
            file_name += f"{'_' if i > 0 else ''}{n.note}{'s' if n.diez else ''}{n.octave}"
            count += 1

        if count > 1:
            if vertical: suffix = "_vert"
            elif count == 2: suffix = "_mel"
            elif count > 2: suffix = "_arp"

        return file_name + suffix

    @staticmethod
    def __prima_location_str_to_int(prima_location: str) -> int:
        if prima_location and len(prima_location) > 0:
            prima_location = prima_location.lower()
            if "низ" in prima_location: return MusicNoteSequence.PRIMALOC_BOTTOM
            if "серед" in prima_location: return MusicNoteSequence.PRIMALOC_MIDDLE
            if "верх" in prima_location: return MusicNoteSequence.PRIMALOC_TOP

        return MusicNoteSequence.PRIMALOC_UNKNOWN

    @staticmethod
    def __prima_location_int_to_str(prima_location: int) -> str:
        match prima_location:
            case MusicNoteSequence.PRIMALOC_BOTTOM: return "Внизу"
            case MusicNoteSequence.PRIMALOC_MIDDLE: return "В середине"
            case MusicNoteSequence.PRIMALOC_TOP: return "Наверху"
        return ""
    
    @staticmethod
    def __inversion_str_to_int(inversion: str) -> int:
        invrs = MusicNoteSequence.INVERSION_UNKNOWN

        if inversion and len(inversion) > 0:
            s = inversion[0].lower()
            if s == "о": invrs = MusicNoteSequence.INVERSION_MAIN
            elif s == "п": invrs = MusicNoteSequence.INVERSION_FIRST
            elif s == "в": invrs = MusicNoteSequence.INVERSION_SECOND

        return invrs
    
    @staticmethod
    def __inversion_int_to_str(inversion: int) -> str:
        match inversion:
            case MusicNoteSequence.INVERSION_MAIN: return "Основной вид"
            case MusicNoteSequence.INVERSION_FIRST: return "Первое обращение"
            case MusicNoteSequence.INVERSION_SECOND: return "Второе обращение"
        return ""

    @staticmethod
    def __parse_chord_str(chord_str: str) -> tuple[bool, bool, bool]:
        is_tonic = is_dominant = is_subdominant = False

        if chord_str and len(chord_str) > 0:
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
            if isinstance(note, str):
                if len(note) == 0: # note is str
                    missed = i
                    continue
                note = MusicNote(note)
                notes_list.append(note)
            elif isinstance(note, MusicNote):
                notes_list.append(note) # note is MusicNote
            else:
                missed = i
                continue

            ascending = ascending and (prev_note is None or prev_note < note)
            prev_note = note

        return ascending, missed, tuple(notes_list)
