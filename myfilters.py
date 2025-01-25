from typing import Sequence
from aliceio.filters import BaseFilter
from aliceio.types import Message

class CmdFilter(BaseFilter):
    def __init__(self, include: str | Sequence[str], exclude: str | Sequence[str] = None, all_words: bool = False) -> None:
        assert include
        include = include.split(sep=" ") if isinstance(include, str) else include
        exclude = exclude.split(sep=" ") if isinstance(exclude, str) else exclude if exclude else []
        self.__include = tuple(word.lower() for word in include)
        self.__exclude = tuple(word.lower() for word in exclude)
        self.__all_words = all_words
        super().__init__()

    async def __call__(self, message: Message) -> bool:
        if message.command == "": return False
        return CmdFilter.passed(message.command, self.__include, self.__exclude, self.__all_words)

    def is_passed(self, command: str | Sequence[str]) -> bool:
        return CmdFilter.passed(command, self.__include, self.__exclude, self.__all_words)

    @staticmethod
    def passed(command: str | Sequence[str], include: Sequence[str], exclude: Sequence[str] = None, all_words = False) -> bool:
        assert command
        assert include
        command_words: Sequence[str] = command.lower().split(sep=" ") if isinstance(command, str) else command

        func = all if all_words else any
        return (exclude is None or not any(any(filter(lambda cmd: cmd.startswith(word), command_words)) for word in exclude)) \
                and func(any(cmd.startswith(word) for cmd in command_words) for word in include)
