import re

class MusicNote:
    __note_pattern = re.compile(r"(?P<note>[a-h]{1}){1}(?P<pitch>\#)?(?P<octave>[0-8]{1}){1}", re.IGNORECASE)

    def __init__(self, note_string: str = None, note: str = None, octave: int = None, diez: bool = False):
        if note_string:
            self.__note, self.__diez, self.__octave, self.__midi_code = \
                MusicNote.parse_notation(note_string)
            return

        assert note
        assert octave
        self.__note = note
        self.__diez = diez == True
        self.__octave = octave
        self.__midi_code = MusicNote.get_midi_code(note, octave, diez)


    @property
    def note(self) -> str: return self.__note
    @property
    def diez(self) -> bool: return self.__diez
    @property
    def octave(self) -> int: return self.__octave
    @property
    def midi_code(self) -> int: return self.__midi_code

    def __str__(self): return f"{self.__note}{'#' if self.__diez else ''}{self.__octave}"
    def __eq__(self, value): return self.__midi_code == value.__midi_code
    def __ne__(self, value): return self.__midi_code != value.__midi_code
    def __lt__(self, value): return self.__midi_code < value.__midi_code
    def __le__(self, value): return self.__midi_code <= value.__midi_code
    def __gt__(self, value): return self.__midi_code > value.__midi_code
    def __ge__(self, value): return self.__midi_code >= value.__midi_code

    @staticmethod
    def parse_notation(note_string: str) -> tuple[str, bool, int, int]:
        """
        Разбирает запись музыкальной ноты в формате научной нотации и извлекает её составляющие.

        #### Параметры:
        - `note_string` (str): Строка, содержащая нотную запись в научной нотации (ноты A-G; нота H тоже обработается корректно) либо в русской нотации (До, Ре, Ми и т.д.).

        #### Возвращает:
        - `tuple`: Кортеж, содержащий ноту (str), диез (bool), октаву (int) и MIDI код (int).

        #### Исключения:
        - `ValueError`: Если строка ноты неизвестна или не распознана.
        """
        m = MusicNote.__note_pattern.match(note_string)
        if m is None: raise ValueError(f"Неизвестная нотная запись {note_string}")

        note = m.group("note")
        octave = int(m.group("octave"))
        diez = m.group("pitch") == "#"
        midi_code = MusicNote.get_midi_code(note, octave, diez) #(octave + 1) * 12 + MusicNote.map_note(note, diez)[1]
        return (note, diez, octave, midi_code)

    @staticmethod
    def get_midi_code(note: str, octave: int, diez: bool = False) -> int:
        """
        Рассчитать MIDI код для заданной ноты и октавы.

        #### Параметры:
        - `note` (str): Музыкальная нота (например, 'C', 'D', 'E' и т.д.).
        - `octave` (int): Номер октавы в диапазоне научной нотации (0-8).
        - `diez` (bool): Указывает, является ли нота диезом (#). По умолчанию False.

        #### Возвращает:
        - `int`: MIDI код, соответствующий ноте и октаве.

        #### Исключения:
        - `ValueError`: Если нота неизвестна или не распознана, или октава выходит за пределы диапазона.
        """
        if octave < 0 or octave > 8:
            raise ValueError("Октава должна быть в пределах от 0 до 8 включительно")

        return (octave + 1) * 12 + MusicNote.map_note(note, diez)[1]

    @staticmethod
    def map_note(note: str, diez: bool = False) -> tuple[str, int]:
        """
        Преобразует музыкальную ноту в соответствующее имя и MIDI код.

        #### Аргументы:
        - `note` (str): Музыкальная нота для преобразования. Может быть на английском (например, "C", "D", "E") или русском (например, "до", "ре", "ми").
        - `diez` (bool, optional): Если True, нота является диезом (#). По умолчанию False.

        #### Возвращает:
        - `tuple[str, int]`: Кортеж, содержащий преобразованное имя ноты в другой нотации (рус/англ) и соответствующий MIDI код без октавы (0-11).

        #### Исключения:
        - `ValueError`: Если нота неизвестна или не распознана.
        """
        assert note
        midi_code = -1

        match note.lower():
            case "c": note = "До"; midi_code = 0
            case "d": note = "Ре"; midi_code = 2
            case "e": return ("Ми", 4)
            case "f": note = "Фа"; midi_code = 5
            case "g": note = "Соль"; midi_code = 7
            case "a": note = "Ля"; midi_code = 9
            case "b" | "h": return ("Си", 11)

            case "до": note = "C"; midi_code = 0
            case "ре": note = "D"; midi_code = 2
            case "ми": return ("E", 4)
            case "фа": note = "F"; midi_code = 5
            case "соль": note = "G"; midi_code = 7
            case "ля": note = "A"; midi_code = 9
            case "си": return ("B", 11)

        if midi_code < 0:
            raise ValueError("Неизвестная нота")

        return (note, midi_code + (1 if diez == True else 0))