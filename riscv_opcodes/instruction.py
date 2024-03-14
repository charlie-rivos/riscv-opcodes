from dataclasses import dataclass
from enum import IntFlag, auto


class BaseExtension(IntFlag):
    RV32 = auto()
    RV64 = auto()
    RV128 = auto()


def get_base_extension(extension: str) -> BaseExtension:
    if extension.startswith("rv32"):
        return BaseExtension.RV32
    elif extension.startswith("rv64"):
        return BaseExtension.RV64
    elif extension.startswith("rv128"):
        return BaseExtension.RV128
    else:
        return BaseExtension.RV32 | BaseExtension.RV64 | BaseExtension.RV128


def get_base_extension_from_list(extensions: list[str]) -> BaseExtension:
    base_extension: BaseExtension = get_base_extension(extensions[0])

    for extension in extensions[1:]:
        base_extension |= get_base_extension(extension)

    return base_extension


@dataclass(frozen=True)
class Instruction:
    extensions: list[str]
    name: str
    encoding: str
    mask: str
    match: str
    args: tuple[str, ...]

    def get_base_extension(self) -> BaseExtension:
        return get_base_extension_from_list(self.extensions)
