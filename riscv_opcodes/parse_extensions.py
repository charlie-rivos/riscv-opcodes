from dataclasses import dataclass
from enum import IntFlag, auto
import pathlib
import re
from typing import Generator


numeric_arg_regex = re.compile(
    r"(?P<msb>\d+)(?:\.\.(?P<lsb>\d+))?\s*=\s*(?P<val>(?:(0x[a-zA-Z0-9]+)|(\d+)))"
)
import_line_regex = re.compile(
    r"\$import\s+(?P<import_extension>[^::]+)::(?P<import_instruction>[^\s]+)"
)
pseudo_line_regex = re.compile(
    r"\$import\s+(?P<import_extension>[^::]+)::(?P<import_instruction>[^\s]+)\s+(?P<name>[^\s]+)\s+(?P<arg_list>.*)"
)
instruction_line_regex = re.compile(r"(?P<name>[^\s]+)\s+(?P<arg_list>.*)")


def get_encoding_size(name: str):
    if name.startswith("c."):
        return 16
    else:
        return 32


class ArchSize(IntFlag):
    RV32 = auto()
    RV64 = auto()
    RV128 = auto()


@dataclass(frozen=True)
class NumericArg:
    msb: int
    lsb: int
    value: int

    def assert_valid(self):
        if self.lsb > self.msb:
            raise Exception("Invalid range")

        num_bits: int = self.lsb - self.msb + 1
        if self.value.bit_length() >= num_bits:
            raise Exception(
                f"Value of {self.value} too large to fit in specified number of bits ({num_bits})"
            )

    @classmethod
    def from_string(cls, string: str) -> "NumericArg | None":
        numeric_arg_match = numeric_arg_regex.match(string)
        if numeric_arg_match:
            msb, lsb, value = numeric_arg_match.groups()
            if lsb == None:
                msb = int(msb) + 1
            return NumericArg(int(msb), int(msb), int(value))
        return None


@dataclass(frozen=True)
class IntermediateInstruction:
    extension: str
    import_extension: str
    import_name: str


@dataclass(frozen=True)
class PseudoInstruction(IntermediateInstruction):
    name: str
    encoding: str
    mask: str
    match: str
    args: tuple[str, ...]


@dataclass(frozen=True)
class ImportInstruction(IntermediateInstruction):
    pass


@dataclass(frozen=True)
class Instruction:
    name: str
    encoding: str
    extensions: tuple[str]
    mask: str
    match: str
    args: tuple[str, ...]
    arch_size: ArchSize


@dataclass(frozen=True)
class ArgList:
    named_args: tuple[str, ...]
    insn_encoding: str
    insn_mask: str
    insn_match: str


def parse_arg_list(encoding_size: int, arg_list: str) -> ArgList:
    """
    Parse a string of instruction arguments from the instruction format.
    Each argument is space delimited and can either be the name of one of the
    variable args, or the hex value a bit range should contain.
    """
    named_args: list[str] = []

    encoding_bits: int = (1 << encoding_size) - 1

    # Intialize encoding to "don't care" values represented by dashes
    insn_encoding: str = "-" * encoding_size
    insn_mask: int = 0
    insn_match: int = 0

    for arg in arg_list.split():
        numeric_arg = NumericArg.from_string(arg)
        if numeric_arg:
            numeric_arg.assert_valid()
            arg_mask = (encoding_bits >> numeric_arg.lsb) << numeric_arg.lsb
            if arg_mask & insn_mask:
                print("Overlapping bits in instruction")
                exit(1)
            insn_mask = insn_mask | arg_mask
            arg_match = numeric_arg.value << numeric_arg.lsb
            insn_match = insn_match | arg_match

            # Replace relevant "don't care" values from arg values
            insn_encoding = (
                insn_encoding[: numeric_arg.msb]
                + bin(numeric_arg.value)
                + insn_encoding[numeric_arg.lsb + 1 :]
            )
        else:
            named_args.append(arg)

    insn_mask_str: str = hex(insn_mask)
    insn_match_str: str = hex(insn_match)

    return ArgList(tuple(named_args), insn_encoding, insn_mask_str, insn_match_str)


def get_arch_size(extension: str) -> ArchSize:
    if extension.startswith("rv32"):
        return ArchSize.RV32
    elif extension.startswith("rv64"):
        return ArchSize.RV64
    elif extension.startswith("rv128"):
        return ArchSize.RV128
    else:
        return ArchSize.RV32 | ArchSize.RV64 | ArchSize.RV128


def get_instructions(
    filename: pathlib.Path,
) -> Generator[Instruction | IntermediateInstruction, None, None]:
    """
    Given a path to a file, parse all of the instructions in the file. This only
    returns IntermediateInstructions because this function does not follow the
    import or pseudo instructions to the original definitions.
    """
    extension = filename.name
    with open(filename) as file:
        for line in file:
            stripped_line = line.lstrip()

            # Only parse lines that have content and are not comments
            if stripped_line and not stripped_line.startswith("#"):
                if stripped_line.startswith("$import"):
                    parsed_import_instruction = import_line_regex.match(stripped_line)
                    if not parsed_import_instruction:
                        raise Exception(
                            f"Malformed import instruction ({line}) in file ({filename})"
                        )
                    import_instruction_dict = parsed_import_instruction.groupdict()
                    import_extension = import_instruction_dict["import_extension"]
                    import_instruction = import_instruction_dict["import_instruction"]
                    yield ImportInstruction(
                        extension, import_extension, import_instruction
                    )
                elif stripped_line.startswith("$pseudo_op"):
                    parsed_pseudo_instruction = pseudo_line_regex.match(stripped_line)
                    if not parsed_pseudo_instruction:
                        raise Exception(
                            f"Malformed pseudo instruction ({line}) in file ({filename})"
                        )
                    pseudo_instruction_dict = parsed_pseudo_instruction.groupdict()
                    pseudo_extension = pseudo_instruction_dict["import_extension"]
                    pseudo_instruction = pseudo_instruction_dict["import_instruction"]
                    pseudo_instruction_name = pseudo_instruction_dict["name"]
                    pseudo_instruction_encoding_size = get_encoding_size(
                        pseudo_instruction_name
                    )
                    pseudo_arg_list = pseudo_instruction_dict["arg_list"]
                    parsed_pseudo_arg_list = parse_arg_list(
                        pseudo_instruction_encoding_size, pseudo_arg_list
                    )
                    yield PseudoInstruction(
                        extension,
                        pseudo_extension,
                        pseudo_instruction,
                        pseudo_instruction_name,
                        parsed_pseudo_arg_list.insn_encoding,
                        parsed_pseudo_arg_list.insn_mask,
                        parsed_pseudo_arg_list.insn_match,
                        parsed_pseudo_arg_list.named_args,
                    )
                else:
                    # Default case where there is no directive
                    parsed_instruction = instruction_line_regex.match(stripped_line)
                    if not parsed_instruction:
                        raise Exception(
                            f"Malformed instruction ({line}) in file ({filename})"
                        )
                    instruction_dict = parsed_instruction.groupdict()
                    instruction_name = instruction_dict["name"]
                    instruction_encoding_size = get_encoding_size(instruction_name)
                    arg_list = instruction_dict["arg_list"]
                    parsed_arg_list = parse_arg_list(
                        instruction_encoding_size, arg_list
                    )
                    arch_size = get_arch_size(extension)
                    yield Instruction(
                        instruction_name,
                        parsed_arg_list.insn_encoding,
                        (extension,),
                        parsed_arg_list.insn_mask,
                        parsed_arg_list.insn_match,
                        parsed_arg_list.named_args,
                        arch_size,
                    )


def get_file_list(file_filter: list[str]) -> list[pathlib.Path]:
    file_list: list[pathlib.Path] = []
    extensions_path = (pathlib.Path(__file__).parent / "extensions").resolve()
    for pattern in file_filter:
        for extension in extensions_path.glob(pattern):
            file_list.append(extension)
    file_list.sort(reverse=True)
    return file_list


def create_inst_dict(
    file_filter: list[str],
    include_pseudo: bool = False,
    include_pseudo_ops: list[str] | None = None,
) -> list[Instruction]:
    # Can do one pass. Create queue of all filenames to parse
    # When encounter import/pseudo, add onto the queue and dict of import/pseudo to parse
    # When processing file, first check if it has been processed yet
    #   If not read file and cache
    #   If it has, process all remaining import/pseudo instructions and remove them from list

    filenames_queue: list[pathlib.Path] = []
    parsed_filenames: set[str] = set()
    instructions_to_parse: dict[str, str] = {}

    # Dict of instruction_name: (IntermediateInstruction, list[extension_names])
    # Used to check if instructions with the same name are overlapping
    # It is possible for an instruction to be defined in two different extensions
    encountered_instructions: dict[str, tuple[IntermediateInstruction, list[str]]] = {}

    # Following dict is used to find an instruction that is known to be in an
    # extension
    # filename (also is the extension):
    # 	instruction_name:
    # 		instruction
    inst_dict: dict[str, dict[str, Instruction]] = {}

    if not include_pseudo_ops:
        include_pseudo_ops = []

    filenames_queue = get_file_list(file_filter)

    while filenames_queue:
        current_filename = filenames_queue.pop(0)
        for instruction in get_instructions(current_filename):
            print(instruction)
