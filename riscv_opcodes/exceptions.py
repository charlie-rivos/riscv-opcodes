from parse_extension import IntermediateInstruction
from instruction import Instruction


class DuplicateInstructionException(BaseException):
    def __init__(self, instruction: IntermediateInstruction):
        super().__init__(
            f'Instruction "{instruction.name}" already defined in extension '
            f'"{instruction.extension}".'
        )


class DuplicateEncodingException(BaseException):
    def __init__(self, instruction: Instruction, duplicate: Instruction):
        super().__init__(
            f'Instruction "{instruction.name}" has the same encoding as '
            f'"{duplicate.name}" in base extension(s): '
            f"{str(instruction.get_base_extension() & duplicate.get_base_extension())}"
        )


class DuplicateNameException(BaseException):
    def __init__(self, instruction: Instruction, duplicate: Instruction):
        super().__init__(
            f'Instruction "{instruction.name}" in extension(s) '
            f'"{instruction.extensions}" has same encoding as instruction '
            f"{duplicate.name} which is included in extension(s) "
            f'"{duplicate.extensions}". The overlapping base extension(s): '
            f"{str(instruction.get_base_extension() & duplicate.get_base_extension())}"
        )


class IllegalInstructionImport(BaseException):
    pass
