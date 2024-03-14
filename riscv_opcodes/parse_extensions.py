from dataclasses import dataclass
import pathlib
from typing import Generator
from exceptions import (
    DuplicateEncodingException,
    DuplicateInstructionException,
    DuplicateNameException,
    IllegalInstructionImport,
)
from instruction import BaseExtension, Instruction, get_base_extension

from parse_extension import (
    ImportInstruction,
    InstructionTuple,
    InstructionType,
    IntermediateInstruction,
    PseudoInstruction,
    parse_extension,
)


extensions_path = (pathlib.Path(__file__).parent / "extensions").resolve()


@dataclass(frozen=True)
class Extension:
    name: str
    instructions: tuple[Instruction]


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


class InstructionCollector:
    encoding_may_overlap_dict: set[InstructionTuple] = set()
    encoding_dict: dict[str, list[InstructionTuple]] = dict()

    collected_instructions: dict[InstructionTuple, Instruction] = {}
    instruction_cache: dict[InstructionTuple, IntermediateInstruction] = {}
    pseudo_dependent_instructions: set[InstructionTuple]
    name_cache: set[str] = set()

    instructions_to_import: dict[InstructionTuple, list[ImportInstruction]] = {}
    pseudo_instructions: dict[InstructionTuple, list[PseudoInstruction]] = {}

    visited_extensions: set[pathlib.Path] = set()
    filenames_queue: list[tuple[pathlib.Path, bool]] = []

    def track_instruction_encoding(
        self,
        instruction: IntermediateInstruction,
        ignore_overlap: set[str] = set(),
    ):
        # An instruction can't overlap with itself
        # Perform a union rather than directly adding to ignore_overlap such
        # that the original ignore_overlap set is not modified
        ignore_overlap = ignore_overlap.union(set((instruction.name,)))

        if instruction.encoding in self.encoding_dict:
            for overlapping_inst_tuple in self.encoding_dict[instruction.encoding]:
                overlapping_inst = self.collected_instructions[overlapping_inst_tuple]
                if (overlapping_inst.name not in ignore_overlap) and (
                    (
                        get_base_extension(instruction.extension)
                        & overlapping_inst.get_base_extension()
                    )
                ):
                    raise DuplicateEncodingException(instruction, overlapping_inst)
            self.encoding_dict[instruction.encoding].append(
                InstructionTuple(instruction.extension, instruction.name)
            )
        else:
            self.encoding_dict[instruction.encoding] = [
                (InstructionTuple(instruction.extension, instruction.name))
            ]

    def file_iterator(
        self, file_filter: list[str]
    ) -> Generator[tuple[pathlib.Path, bool], None, None]:
        for pattern in file_filter:
            for current_filename in extensions_path.glob(pattern):
                if current_filename not in self.visited_extensions:
                    self.visited_extensions.add(current_filename)
                    yield current_filename, True
        # After all files in filter processed, continue onto the file queue
        while self.filenames_queue:
            current_filename, include_all_insts = self.filenames_queue.pop(0)
            if current_filename not in self.visited_extensions:
                self.visited_extensions.add(current_filename)
                yield current_filename, include_all_insts

    def add_instruction(
        self,
        intermediate_inst: IntermediateInstruction,
        in_selected_extension: bool,
        ignore_overlap: set[str] = set(),
        from_pseudo: bool = False,
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
            ignore_overlap (set[InstructionTuple]): Don't error if the instruction
                                                    to add overlaps with an instruction
                                                    in this set.
        """
        inst_tuple: InstructionTuple = intermediate_inst.instruction_tuple()
        if inst_tuple in self.instruction_cache:
            raise DuplicateInstructionException(intermediate_inst)

        self.name_cache.add(intermediate_inst.name)

        if not from_pseudo:
            self.instruction_cache[inst_tuple] = intermediate_inst

        self.track_instruction_encoding(intermediate_inst, ignore_overlap)

        # Construct the extension list, bringing in all of the extensions that
        # have imported this instruction before this point
        extension_list: list[str] = []
        if in_selected_extension:
            extension_list.append(intermediate_inst.extension)

        if inst_tuple in self.instructions_to_import:
            if from_pseudo:
                raise IllegalInstructionImport(
                    f"Attempted to import {inst_tuple} which is a pseudo instruction. This is not supported."
                )
            for import_instruction in self.instructions_to_import[inst_tuple]:
                extension_list.append(import_instruction.extension)
            del self.instructions_to_import[inst_tuple]

        if in_selected_extension:
            # Don't need to check if inst_tuple in collected_instructions
            # because was already checked if the instruction is in the
            # instruction_cache and it's not possible to not be in the cache
            # but be in collected_instructions
            self.collected_instructions[inst_tuple] = Instruction(
                extension_list,
                intermediate_inst.name,  # TODO: It is possible for there to be two instructions with the same name. They should be merged into one.
                intermediate_inst.encoding,
                intermediate_inst.mask,
                intermediate_inst.match,
                intermediate_inst.args,
            )

    def add_pseudo_instruction(
        self, instruction: PseudoInstruction, include_pseudo_ops: set[str] | AnyPseudoOp
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

        if not ignore_pseudo:
            # Add to list of pseudo instructions to be processed
            if dependent_inst_tuple not in self.pseudo_instructions:
                self.pseudo_instructions[dependent_inst_tuple] = []
            self.pseudo_instructions[dependent_inst_tuple].append(instruction)

    def add_import_instruction(self, instruction: ImportInstruction):
        instruction_tuple = InstructionTuple(
            instruction.import_extension,
            instruction.import_name,
        )

        if instruction_tuple in self.instruction_cache:
            if instruction_tuple in self.collected_instructions:
                # Dependent instruction has been cached and used by a selected
                # extension, need to add this extension to the extension list
                self.collected_instructions[instruction_tuple].extensions.append(
                    instruction.extension
                )
                self.track_instruction_encoding(
                    self.instruction_cache[instruction_tuple], set()
                )
            else:
                # Dependent instruction has been cached, but not requested by a
                # selected extension until now
                self.add_instruction(self.instruction_cache[instruction_tuple], True)
        else:
            # Instruction hasn't been parsed yet, add to filenames queue so it can be parsed
            if instruction_tuple not in self.instructions_to_import:
                self.instructions_to_import[instruction_tuple] = []
            self.instructions_to_import[instruction_tuple].append(instruction)
            self.filenames_queue.append(
                (get_filename(instruction.import_extension), False)
            )

    def in_same_base_extension(
        self, instruction: Instruction, instruction2: Instruction
    ) -> BaseExtension:
        return instruction.get_base_extension() & instruction2.get_base_extension()

    def handle_pseudo_instructions(self, include_pseudo_ops: set[str] | AnyPseudoOp):
        for (
            dependent_instruction_tuple,
            instructions,
        ) in self.pseudo_instructions.items():
            # A pseudo instruction should be ignored if the dependent
            # instruction has already been collected and the pseudo
            # instruction was not listed in @include_pseudo_ops
            dependent_inst_collected = (
                dependent_instruction_tuple in self.collected_instructions
            )

            for instruction in instructions:
                force_include_pseudo = instruction.name in include_pseudo_ops
                ignore_pseudo: bool = (
                    dependent_inst_collected and not force_include_pseudo
                )
                if not ignore_pseudo:
                    self.add_instruction(
                        IntermediateInstruction(
                            instruction.extension,
                            instruction.name,
                            instruction.encoding,
                            instruction.mask,
                            instruction.match,
                            instruction.args,
                        ),
                        True,
                        set((dependent_instruction_tuple.name,)),
                    )

    extension_cache: dict[str, Extension] = dict()
    selected_instructions: list[Instruction] = list()
    encoding_dict2: dict[str, Instruction] = dict()
    name_dict2: dict[str, Instruction] = dict()

    def assert_instruction_not_duplicated(self, instruction: Instruction):
        duplicate_encoding: Instruction | None = self.encoding_dict2.get(
            instruction.encoding
        )
        if duplicate_encoding and (duplicate_encoding != instruction):
            raise DuplicateEncodingException(
                instruction, self.encoding_dict2[instruction.encoding]
            )

        duplicate_name: Instruction | None = self.name_dict2.get(instruction.name)
        if (
            duplicate_name
            and (duplicate_name != instruction)
            and self.in_same_base_extension(instruction, duplicate_name)
        ):
            raise DuplicateNameException(
                instruction, self.encoding_dict2[instruction.encoding]
            )

    # def get_instruction(self, intermediate_instruction: IntermediateInstruction) -> Instruction:
    #     return self.collected_instructions[inst_tuple] = Instruction(
    #             extension_list,
    #             intermediate_inst.name, # TODO: It is possible for there to be two instructions with the same name. They should be merged into one.
    #             intermediate_inst.encoding,
    #             intermediate_inst.mask,
    #             intermediate_inst.match,
    #             intermediate_inst.args,
    #         )

    def collect(
        self, file_filter: list[str], include_pseudo_ops: set[str] | AnyPseudoOp = set()
    ) -> list[Instruction]:
        for filename, in_selected_extension in self.file_iterator(file_filter):
            instruction_list: list[Instruction] = []
            for instruction in parse_extension(filename):
                match instruction:
                    case IntermediateInstruction():
                        # self.add_instruction(instruction, in_selected_extension)
                        resolved_instruction = Instruction(
                            [],
                            instruction.name,
                            instruction.encoding,
                            instruction.mask,
                            instruction.match,
                            instruction.args,
                        )
                        self.assert_instruction_not_duplicated(resolved_instruction)
                    case PseudoInstruction():
                        if in_selected_extension:
                            self.add_pseudo_instruction(instruction, include_pseudo_ops)
                    case ImportInstruction():
                        if in_selected_extension:
                            self.add_import_instruction(instruction)

        # All instructions have been parsed, now pseudo instructions can be handled
        self.handle_pseudo_instructions(include_pseudo_ops)

        return list(self.collected_instructions.values())
