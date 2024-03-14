from dataclasses import dataclass
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
class InstructionTuple:
    extension: str
    name: str


@dataclass(frozen=True)
class IntermediateInstruction:
    extension: str
    name: str
    encoding: str
    mask: str
    match: str
    args: tuple[str, ...]

    def instruction_tuple(self) -> InstructionTuple:
        return InstructionTuple(self.extension, self.name)


InstructionType = PseudoInstruction | ImportInstruction | IntermediateInstruction

@dataclass(frozen=True)
class ArgList:
    named_args: tuple[str, ...]
    insn_encoding: str
    insn_mask: str
    insn_match: str


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


def get_encoding_size(name: str):
    if name.startswith("c."):
        return 16
    else:
        return 32


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


def parse_extension(
    filename: pathlib.Path,
) -> Generator[
    InstructionType, None, None
]:
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
                    yield IntermediateInstruction(
                        extension,
                        instruction_name,
                        parsed_arg_list.insn_encoding,
                        parsed_arg_list.insn_mask,
                        parsed_arg_list.insn_match,
                        parsed_arg_list.named_args,
                    )
