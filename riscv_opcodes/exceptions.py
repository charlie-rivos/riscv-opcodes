from riscv_opcodes.parse_extension import IntermediateInstruction
from riscv_opcodes.parse_extensions import Instruction, get_base_extension


class DuplicateInstructionException(Exception):
    def __init__(self, instruction: IntermediateInstruction):
        super().__init__(
            f'Instruction "{instruction.name}" already defined in extension'
            f'"{instruction.extension}".'
        )


class DuplicateEncodingException(Exception):
    def __init__(self, instruction: IntermediateInstruction, duplicate: Instruction):
        super().__init__(
            f'Instruction "{instruction.name}" in extensions'
            f'"{instruction.extension}" has same encoding as instruction'
            f"{duplicate.name} which is included in extensions"
            f'"{duplicate.extensions}". The overlapping base extension(s):'
            f"{get_base_extension(instruction.extension) & duplicate.get_base_extension()}"
        )
