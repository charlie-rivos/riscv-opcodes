from dataclasses import dataclass
import dataclasses
from enum import IntFlag, auto
import pathlib
from typing import Generator
from riscv_opcodes.exceptions import (
    DuplicateEncodingException,
    DuplicateInstructionException,
)

from riscv_opcodes.parse_extension import (
    ImportInstruction,
    InstructionTuple,
    IntermediateInstruction,
    PseudoInstruction,
    parse_extension,
)


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


# TODO: Make add instruction function
#       Checks for overlapping encodings in same base extension, duplicate names
#       in same base extension


class InstructionCollector:
    encoding_may_overlap_dict: set[InstructionTuple] = set()
    encoding_dict: dict[str, list[InstructionTuple]] = dict()
    collected_instructions: dict[InstructionTuple, Instruction] = {}
    instruction_cache: dict[InstructionTuple, IntermediateInstruction] = {}

    instructions_to_import: dict[InstructionTuple, list[ImportInstruction]] = {}
    pseudo_instructions: dict[InstructionTuple, list[PseudoInstruction]] = {}

    visited_extensions: set[pathlib.Path] = set()
    filenames_queue: list[tuple[pathlib.Path, bool]] = []

    def file_iterator(
        self, file_filter: list[str]
    ) -> Generator[tuple[pathlib.Path, bool], None, None]:
        for pattern in file_filter:
            for extension in extensions_path.glob(pattern):
                yield extension, True
        # After all files in filter processed, continue onto the file queue
        while self.filenames_queue:
            current_filename, include_all_insts = self.filenames_queue.pop(0)
            if current_filename not in self.visited_extensions:
                self.visited_extensions.add(current_filename)
                yield current_filename, include_all_insts

    def add_instruction(
        self, intermediate_inst: IntermediateInstruction, in_selected_extension: bool
    ):
        """Add an instruction to the collected_instructions dict, along with all
        of the necessary bookkeeping.

        Args:
            instruction (IntermediateInstruction): The instruction to add
            include_extension (bool): Whether the extension that this instruction
                                      is defined in is one of the extensions that
                                      should be included in the results. This should
                                      be False if this extension is only imported
                                      for a subset of its instructions, and not
                                      requested by the original caller.
        """
        inst_tuple: InstructionTuple = intermediate_inst.instruction_tuple()
        if inst_tuple in self.instruction_cache:
            raise DuplicateInstructionException(intermediate_inst)
        else:
            self.instruction_cache[inst_tuple] = intermediate_inst

        # Construct the extension list, bringing in all of the extensions that
        # have imported this instruction before this point
        extension_list: list[str] = []
        if in_selected_extension:
            extension_list.append(intermediate_inst.extension)

        if inst_tuple in self.instructions_to_import:
            for import_instruction in self.instructions_to_import[inst_tuple]:
                extension_list.append(import_instruction.extension)
            del self.instructions_to_import[inst_tuple]

        inst: Instruction = Instruction(
            extension_list,
            intermediate_inst.name,
            intermediate_inst.encoding,
            intermediate_inst.mask,
            intermediate_inst.mask,
            intermediate_inst.args,
        )

        if intermediate_inst.encoding in self.encoding_dict:
            # Check if the instructions that have the same encoding as this
            # instruction share a same base extension
            for overlapping_inst_tuple in self.encoding_dict[
                intermediate_inst.encoding
            ]:
                overlapping_inst = self.collected_instructions[overlapping_inst_tuple]
                if inst.get_base_extension() & overlapping_inst.get_base_extension():
                    raise DuplicateEncodingException(
                        intermediate_inst, overlapping_inst
                    )
                else:
                    # A not-yet-parsed import may cause this instruction encoding
                    # to overlap within a base instruction. Optimize this case by
                    # keeping track of which instructions may overlap
                    self.encoding_may_overlap_dict.add(inst_tuple)
            self.encoding_dict[intermediate_inst.encoding].append(inst_tuple)

        self.encoding_dict[intermediate_inst.encoding] = [inst_tuple]
        self.collected_instructions[inst_tuple] = inst

    def add_pseudo_instruction(
        self,
        instruction: PseudoInstruction,
        include_pseudo_ops: set[str] | AnyPseudoOp,
        in_selected_extension: bool,
    ):
        dependent_inst_tuple = InstructionTuple(
            instruction.import_extension,
            instruction.import_name,
        )

        # A pseudo instruction should be ignored if the dependent
        # instruction has already been collected and the pseudo
        # instruction was not listed in @include_pseudo_ops
        dependent_inst_collected = dependent_inst_tuple in self.collected_instructions
        force_include_pseudo = instruction.name in include_pseudo_ops
        ignore_pseudo: bool = dependent_inst_collected and not force_include_pseudo

        if not ignore_pseudo and in_selected_extension:
            # Add to list of pseudo instructions to be processed
            if dependent_inst_tuple not in self.pseudo_instructions:
                self.pseudo_instructions[dependent_inst_tuple] = []
            self.pseudo_instructions[dependent_inst_tuple].append(instruction)

    def add_import_instruction(
        self, instruction: ImportInstruction, in_selected_extension: bool
    ):
        instruction_tuple = InstructionTuple(
            instruction.import_extension,
            instruction.import_name,
        )

        if instruction_tuple in self.instruction_cache:
            if instruction_tuple in self.collected_instructions:
                # this extension to list of extensions that imported the
                # original instruction
                # TODO: Need to check if adding new extension causes
                #       overlapping names/encoding in base extension
                self.collected_instructions[instruction_tuple].extensions.append(
                    instruction.extension
                )
                self.assert_not_overlapping(
                    self.collected_instructions[instruction_tuple]
                )
            else:
                # Dependent instruction has been cached, but not requested by a
                # selected extension until now
                self.add_instruction(self.instruction_cache[instruction_tuple], True)
        # elif include_all_insts and (instruction_tuple not in instructions_to_import):
        #     if instruction_tuple not in instructions_to_import:
        #         instructions_to_import[instruction_tuple] = []
        #     instructions_to_import[instruction_tuple].append(instruction)
        #     filenames_queue.append((get_filename(instruction.import_extension), False))

    def assert_not_overlapping(self, instruction: Instruction):
        if instruction.encoding in self.encoding_dict:
            for overlapping_inst_tuple in self.encoding_dict[instruction.encoding]:
                overlapping_inst = self.collected_instructions[overlapping_inst_tuple]
                if (
                    instruction.get_base_extension()
                    & overlapping_inst.get_base_extension()
                ):
                    raise DuplicateEncodingException(instruction, overlapping_inst)

    def track_instruction_encoding(self, instruction: IntermediateInstruction):
        if instruction.encoding in self.encoding_dict:
            for overlapping_inst_tuple in self.encoding_dict[instruction.encoding]:
                overlapping_inst = self.collected_instructions[overlapping_inst_tuple]
                if (
                    get_base_extension(instruction.encoding)
                    & overlapping_inst.get_base_extension()
                ):
                    raise DuplicateEncodingException(instruction, overlapping_inst)
            self.encoding_dict[instruction.encoding].append(
                InstructionTuple(instruction.extension, instruction.extension)
            )
        else:
            self.encoding_dict[instruction.encoding] = [
                (InstructionTuple(instruction.extension, instruction.extension))
            ]

    def collect(
        self, file_filter: list[str], include_pseudo_ops: set[str] | AnyPseudoOp = set()
    ):
        for filename, in_selected_extension in self.file_iterator(file_filter):
            for instruction in parse_extension(filename):
                match instruction:
                    case IntermediateInstruction():
                        self.add_instruction(instruction, in_selected_extension)
                    case PseudoInstruction():
                        self.add_pseudo_instruction(
                            instruction, include_pseudo_ops, in_selected_extension
                        )
                    case ImportInstruction():
                        self.add_import_instruction(instruction, in_selected_extension)


def collect_instructions(
    file_filter: list[str],
    include_pseudo_ops: set[str] | AnyPseudoOp = set(),
) -> list[Instruction]:
    encoding_dict: dict[str, Instruction] = dict()
    # inst_list: list[Instruction] = []
    collected_instructions: dict[tuple[str, str], Instruction] = {}

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
                case IntermediateInstruction():
                    instruction_tuple = (extension, instruction.name)

                    if instruction_tuple in inst_dict:
                        print(
                            f'Instruction "{instruction.name}" already defined in extension "{extension}".'
                        )
                        exit(1)
                    elif instruction.encoding in encoding_dict:
                        # TODO: Only do this check on the same base extension
                        print(
                            f'Instruction "{instruction.name}" in extension "{extension}" has same encoding ("{instruction.encoding}") as instruction "{encoding_dict[instruction.encoding].name}" from extensions {encoding_dict[instruction.encoding].extensions}.'
                        )
                        exit(1)
                    else:
                        # Add instruction to instruction cache
                        inst_dict[instruction_tuple] = instruction
                        encoding_dict[instruction.encoding] = instruction

                    extension_list: list[str] = []
                    if include_all_insts:
                        extension_list.append(extension)

                    # Now that this instruction has been parsed, add all of the
                    # extensions that imported this extension to this
                    # instruction's extension list
                    if instruction_tuple in instructions_to_import:
                        for import_instruction in instructions_to_import[
                            instruction_tuple
                        ]:
                            extension_list.append(import_instruction.extension)
                        del instructions_to_import[instruction_tuple]

                    collected_instructions[instruction_tuple] = dataclasses.replace(
                        instruction, extensions=extension_list
                    )

                case PseudoInstruction():
                    instruction_tuple = (
                        instruction.import_extension,
                        instruction.import_name,
                    )

                    # A pseudo instruction should be skipped if the original
                    # instruction has already been collected and the pseudo
                    # instruction was not listed in @include_pseudo_ops
                    should_skip_pseudo: bool = (
                        instruction_tuple in collected_instructions
                    ) and (instruction.name not in include_pseudo_ops)

                    if (not (should_skip_pseudo)) and include_all_insts:
                        # Add to list of pseudo instructions to be processed
                        if instruction_tuple not in pseudo_instructions:
                            pseudo_instructions[instruction_tuple] = []
                        pseudo_instructions[instruction_tuple].append(instruction)
                case ImportInstruction():
                    instruction_tuple = (
                        instruction.import_extension,
                        instruction.import_name,
                    )
                    if instruction_tuple in inst_dict:
                        if instruction_tuple in collected_instructions:
                            # Original instruction has already been processed, add
                            # this extension to list of extensions that imported the
                            # original instruction
                            # TODO: Need to check if adding new extension causes
                            #       overlapping names/encoding in base extension
                            collected_instructions[instruction_tuple].extensions.append(
                                instruction.extension
                            )
                        else:
                            # Import an instruction that has been cached but not
                            # added.
                            collected_instructions[
                                instruction_tuple
                            ] = dataclasses.replace(
                                inst_dict[instruction_tuple],
                                extensions=[instruction.extension],
                            )
                    elif include_all_insts and (
                        instruction_tuple not in instructions_to_import
                    ):
                        if instruction_tuple not in instructions_to_import:
                            instructions_to_import[instruction_tuple] = []
                        instructions_to_import[instruction_tuple].append(instruction)
                        filenames_queue.append(
                            (get_filename(instruction.import_extension), False)
                        )

    for instruction_tuple, pseudo_instruction_list in pseudo_instructions.items():
        for pseudo_instruction in pseudo_instruction_list:
            if instruction_tuple in collected_instructions:
                collected_instructions[
                    (
                        pseudo_instruction.extension,
                        pseudo_instruction.name,
                    )
                ] = Instruction(
                    [pseudo_instruction.extension],
                    pseudo_instruction.name,
                    pseudo_instruction.encoding,
                    pseudo_instruction.mask,
                    pseudo_instruction.match,
                    pseudo_instruction.args,
                )

    return list(collected_instructions.values())
