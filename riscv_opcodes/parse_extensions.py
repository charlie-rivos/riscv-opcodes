import dataclasses
from dataclasses import dataclass
from enum import IntFlag, auto
import pathlib
import re
from typing import Generator


numeric_arg_regex = re.compile(r"(?P<msb>\d+)(?:\.\.(?P<lsb>\d+))?\s*=\s*(?P<val>.*)")
import_line_regex = re.compile(
    r"\$import\s+(?P<import_extension>[^::]+)::(?P<import_instruction>[^\s]+)"
)
pseudo_line_regex = re.compile(
    r"\$pseudo_op\s+(?P<import_extension>[^::]+)::(?P<import_instruction>[^\s]+)\s+(?P<name>[^\s]+)\s+(?P<arg_list>.*)"
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

    def bit_value(self) -> str:
        ret_val = f"{self.value:0{(self.msb - self.lsb) + 1}b}"
        return ret_val

    def assert_valid(self):
        if self.lsb > self.msb:
            raise Exception("Invalid range")

        num_bits: int = self.msb - self.lsb + 1
        if self.value.bit_length() > num_bits:
            raise Exception(
                f"Value of {self.value} too large to fit in specified number of bits ({num_bits})"
            )

    @classmethod
    def from_string(cls, string: str) -> "NumericArg | None":
        numeric_arg_match = numeric_arg_regex.match(string)
        if numeric_arg_match:
            msb, lsb, value = numeric_arg_match.groups()
            if lsb == None:
                lsb = int(msb)
            return NumericArg(int(msb), int(lsb), int(value, 0))
        return None


@dataclass(frozen=True)
class PseudoInstruction:
    extension: str
    import_extension: str
    import_name: str
    name: str
    encoding: str
    mask: str
    match: str
    args: tuple[str, ...]


@dataclass(frozen=True)
class ImportInstruction:
    extension: str
    import_extension: str
    import_name: str


@dataclass(frozen=True)
class Instruction:
    extensions: list[str]
    name: str
    encoding: str
    mask: str
    match: str
    args: tuple[str, ...]

    @staticmethod
    def get_extension_arch_size(extension: str) -> ArchSize:
        if extension.startswith("rv32"):
            return ArchSize.RV32
        elif extension.startswith("rv64"):
            return ArchSize.RV64
        elif extension.startswith("rv128"):
            return ArchSize.RV128
        else:
            return ArchSize.RV32 | ArchSize.RV64 | ArchSize.RV128

    def get_arch_size(self) -> ArchSize:
        arch_size: ArchSize = Instruction.get_extension_arch_size(self.extensions[0])

        for extension in self.extensions[1:]:
            extension_arch_size = Instruction.get_extension_arch_size(extension)
            if arch_size:
                arch_size |= extension_arch_size
            else:
                arch_size = extension_arch_size

        return arch_size


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
            # Generate bit mask in range of msb:lsb
            arg_mask = (encoding_bits - (1 << numeric_arg.lsb) + 1) & (
                encoding_bits >> (encoding_size - 1 - numeric_arg.msb)
            )
            if arg_mask & insn_mask:
                print("Overlapping bits in instruction")
                exit(1)
            insn_mask = insn_mask | arg_mask
            arg_match = numeric_arg.value << numeric_arg.lsb
            insn_match = insn_match | arg_match

            # Replace relevant "don't care" values from arg values.
            # Index from the back since instructions are little-endian but
            # indexing is big-endian
            insn_encoding = (
                insn_encoding[: encoding_size - (numeric_arg.msb + 1)]
                + numeric_arg.bit_value()
                + insn_encoding[encoding_size - (numeric_arg.lsb) :]
            )
            print(insn_encoding, numeric_arg.value, numeric_arg.bit_value())
        else:
            named_args.append(arg)

    insn_mask_str: str = hex(insn_mask)
    insn_match_str: str = hex(insn_match)

    return ArgList(tuple(named_args), insn_encoding, insn_mask_str, insn_match_str)


def get_instructions(
    filename: pathlib.Path,
) -> Generator[Instruction | PseudoInstruction | ImportInstruction, None, None]:
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
                    yield ImportInstruction(
                        extension,
                        import_instruction_dict["import_extension"],
                        import_instruction_dict["import_instruction"],
                    )
                elif stripped_line.startswith("$pseudo_op"):
                    parsed_pseudo_instruction = pseudo_line_regex.match(stripped_line)
                    if not parsed_pseudo_instruction:
                        raise Exception(
                            f"Malformed pseudo instruction ({line}) in file ({filename})"
                        )
                    pseudo_instruction_dict = parsed_pseudo_instruction.groupdict()
                    pseudo_instruction_name = pseudo_instruction_dict["name"]
                    parsed_pseudo_arg_list = parse_arg_list(
                        get_encoding_size(pseudo_instruction_name),
                        pseudo_instruction_dict["arg_list"],
                    )
                    yield PseudoInstruction(
                        extension,
                        pseudo_instruction_dict["import_extension"],
                        pseudo_instruction_dict["import_instruction"],
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
                    parsed_arg_list = parse_arg_list(
                        get_encoding_size(instruction_name),
                        instruction_dict["arg_list"],
                    )
                    yield Instruction(
                        [extension],
                        instruction_name,
                        parsed_arg_list.insn_encoding,
                        parsed_arg_list.insn_mask,
                        parsed_arg_list.insn_match,
                        parsed_arg_list.named_args,
                    )


extensions_path = (pathlib.Path(__file__).parent / "extensions").resolve()


def get_file_list(file_filter: list[str]) -> list[tuple[pathlib.Path, bool]]:
    file_list: list[tuple[pathlib.Path, bool]] = []
    for pattern in file_filter:
        for extension in extensions_path.glob(pattern):
            file_list.append((extension, True))
    return sorted(file_list, reverse=True)


def get_filename(extension: str) -> pathlib.Path:
    ratified_extension = extensions_path / extension
    unratified_extension = extensions_path / "unratified" / extension
    if ratified_extension.exists():
        return ratified_extension
    elif unratified_extension.exists():
        return unratified_extension
    print(f"Extension {extension} does not exist!")
    exit(1)


class AnyPseudoOp:
    def __contains__(self, o: str) -> bool:
        return True


def collect_instructions(
    file_filter: list[str],
    include_pseudo_ops: set[str] | AnyPseudoOp = set(),
) -> list[Instruction]:
    included_instructions: set[tuple[str, str]] = set()
    encoding_dict: dict[str, Instruction] = dict()
    pseudo_instructions_to_add: dict[tuple[str, str], list[Instruction]] = {}
    inst_list: list[Instruction] = []

    visited_extensions: set[pathlib.Path] = set()
    filenames_queue: list[tuple[pathlib.Path, bool]] = []

    # These dicts have a tuple as key that is (extension, instruction_name)
    instructions_to_import: dict[tuple[str, str], list[ImportInstruction]] = dict()
    pseudo_instructions: dict[tuple[str, str], list[PseudoInstruction]] = dict()
    inst_dict: dict[tuple[str, str], Instruction] = {}

    filenames_queue = get_file_list(file_filter)
    while filenames_queue:
        current_filename, include_all_insts = filenames_queue.pop(0)
        if current_filename in visited_extensions:
            continue
        else:
            visited_extensions.add(current_filename)

        extension: str = current_filename.name
        for instruction in get_instructions(current_filename):
            match instruction:
                case Instruction():
                    instruction_tuple = (extension, instruction.name)

                    if instruction_tuple in inst_dict:
                        print(
                            f'Instruction "{instruction.name}" already defined in extension "{extension}".'
                        )
                        exit(1)
                    elif instruction.encoding in encoding_dict:
                        print(
                            f'Instruction "{instruction.name}" in extension "{extension}" has same encoding ("{instruction.encoding}") as instruction "{encoding_dict[instruction.encoding].name}" from extensions {encoding_dict[instruction.encoding].extensions}.'
                        )
                        exit(1)
                    else:
                        # Add instruction to instruction cache
                        inst_dict[instruction_tuple] = instruction
                        encoding_dict[instruction.encoding] = instruction

                    should_import = instruction_tuple in instructions_to_import
                    should_import_pseudo = instruction_tuple in pseudo_instructions

                    extension_list: list[str] = []
                    if include_all_insts:
                        extension_list.append(extension)

                    # When importing instruction, do simple bookkeeping of
                    # logging which extension imported the instruction
                    if should_import:
                        for import_instruction in instructions_to_import[
                            instruction_tuple
                        ]:
                            extension_list.append(import_instruction.extension)
                        del instructions_to_import[instruction_tuple]

                    # Each pseudo instruction is treated as a real instruction,
                    # except they are only added if explicitly listed in
                    # @include_pseudo_ops or the original instruction is not
                    # included.
                    if should_import_pseudo:
                        pseudo_instruction_list: list[Instruction] = []
                        for pseudo_instruction in pseudo_instructions[
                            instruction_tuple
                        ]:
                            # Only include pseudo ops explicitly mentioned
                            if pseudo_instruction.name in include_pseudo_ops:
                                pseudo_instruction_list.append(
                                    Instruction(
                                        name=pseudo_instruction.name,
                                        encoding=pseudo_instruction.encoding,
                                        extensions=[pseudo_instruction.extension],
                                        mask=pseudo_instruction.mask,
                                        match=pseudo_instruction.match,
                                        args=pseudo_instruction.args,
                                    )
                                )
                        del pseudo_instructions[instruction_tuple]

                        pseudo_instructions_to_add[
                            instruction_tuple
                        ] = pseudo_instruction_list

                case PseudoInstruction():
                    instruction_tuple = (
                        instruction.import_extension,
                        instruction.import_name,
                    )

                    # Check if instruction has been processed
                    if instruction_tuple in inst_dict:
                        inst_dict[instruction_tuple].extensions.append(
                            instruction.extension
                        )
                    elif include_all_insts:
                        if instruction_tuple not in pseudo_instructions:
                            pseudo_instructions[instruction_tuple] = []
                        # Add to list of pseudo instructions to be processed
                        pseudo_instructions[instruction_tuple].append(instruction)
                        filenames_queue.append(
                            (get_filename(instruction.import_extension), False)
                        )
                    # Otherwise already queued to be processed
                case ImportInstruction():
                    instruction_tuple = (
                        instruction.import_extension,
                        instruction.import_name,
                    )
                    # Check if instruction has been processed
                    if instruction_tuple in inst_dict:
                        inst_dict[instruction_tuple].extensions.append(
                            instruction.extension
                        )
                    elif include_all_insts and (
                        instruction_tuple not in instructions_to_import
                    ):
                        # Add to list of import instructions to be processed
                        if instruction_tuple not in instructions_to_import:
                            instructions_to_import[instruction_tuple] = []
                        instructions_to_import[instruction_tuple].append(instruction)
                        filenames_queue.append(
                            (get_filename(instruction.import_extension), False)
                        )
                    # Otherwise already queued to be processed
    return inst_list
