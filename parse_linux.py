#!/usr/bin/env python3

from typing import Any, Callable
import argparse
from dataclasses import dataclass
from parse import create_inst_dict  # type: ignore
from variable_field_data import (
    VariableField,
    ImmVariableField,
    ImmType,
    field_types,
)


@dataclass(frozen=True)
class Instruction:
    encoding: str
    name: str
    extension: list[str]
    mask: int
    match: int
    variable_fields: list[str]


@dataclass(frozen=True)
class GenerationOptions:
    generate_extract_code: bool
    generate_insert_code: bool
    generate_update_code: bool
    generate_check_code: bool
    generate_create_code: bool


ImmVariableFieldsFunctionType = Callable[
    [
        str,
        ImmVariableField,
        ImmVariableField,
    ],
    str,
]


NonImmVariableFieldsFunctionType = Callable[
    [
        str,
        VariableField,
    ],
    str,
]

InstructionFunctionType = Callable[[Instruction], str]


def construct_hi_lo_name(hi_name: str) -> str:
    return f"{hi_name}lo"


def extract_part(position: tuple[int, int], opoffset: int, offset: int) -> str:
    return f"RV_X(insn, {opoffset}, GENMASK({position[0] - position[1]}, 0)) << {offset}"


def generate_variable_field_extract_code(
    name: str, variable_field: VariableField
) -> str:
    extract_string: str = (
        f"static inline u32 riscv_extract_{name}(u32 insn) {{\n"
    )
    # Generate non-imm extract
    extract_string += (
        "\treturn "
        + extract_part(variable_field.position, variable_field.position[1], 0)
        + "\n}\n"
    )

    return extract_string


def generate_extract_interior(variable_field_imm: ImmVariableField) -> str:
    interior_string: str = ""
    opoffset: int = variable_field_imm.position[0]
    for imm_field in variable_field_imm.imm_configuration:
        opoffset -= imm_field[0] - imm_field[1]
        interior_string += (
            extract_part(imm_field, opoffset, imm_field[1])
        ) + " |\n\t       "
        opoffset -= 1
    return interior_string


def generate_hi_lo_field_extract_code(
    name: str,
    hi_variable_field: ImmVariableField,
    lo_variable_field: ImmVariableField,
) -> str:
    extract_string: str = (
        f"static inline u32 riscv_extract_{name}(u32 insn) {{\n\treturn "
    )
    extract_string += generate_extract_interior(hi_variable_field)
    extract_string += generate_extract_interior(lo_variable_field)
    if hi_variable_field.type.is_signed():
        extract_string += f"(-(((insn) >> {hi_variable_field.position[0]}) & 1)) << {hi_variable_field.imm_configuration[0][0]}"
    extract_string += ";\n}\n"
    return extract_string


def insert_part(position: tuple[int, int], opoffset: int, offset: int):
    return f"*insn |= RV_X(value, {offset}, GENMASK({position[0] - position[1]}, 0)) << {opoffset};"


def generate_variable_field_insert_code(
    name: str, variable_field: VariableField
) -> str:
    insert_string: str = (
        f"static inline void riscv_insert_{name}(u32 *insn, u32 value) {{ \n"
    )
    # Generate non-imm insert
    insert_string += (
        "\t"
        + insert_part(variable_field.position, variable_field.position[1], 0)
        + "\n}\n"
    )

    return insert_string


def generate_insert_interior(variable_field_imm: ImmVariableField) -> str:
    interior_string: str = ""
    opoffset: int = variable_field_imm.position[0]
    for imm_field in variable_field_imm.imm_configuration:
        opoffset -= imm_field[0] - imm_field[1]
        interior_string += (
            "\t" + insert_part(imm_field, opoffset, imm_field[1]) + "\n"
        )
        opoffset -= 1
    return interior_string


def generate_hi_lo_field_insert_code(
    name: str,
    hi_variable_field: ImmVariableField,
    lo_variable_field: ImmVariableField,
) -> str:
    insert_string: str = (
        f"static inline void riscv_insert_{name}(u32 *insn, u32 value) {{ \n"
    )
    insert_string += generate_insert_interior(hi_variable_field)
    insert_string += generate_insert_interior(lo_variable_field)
    insert_string += "}\n"

    return insert_string


def generate_variable_field_update_code(
    name: str, variable_field: VariableField
) -> str:
    insert_string: str = (
        f"static inline void riscv_update_{name}(u32 *insn, u32 value) {{ \n"
    )
    insert_string += f"\t*insn &= ~(GENMASK({variable_field.position[0], variable_field.position[1]}));\n"
    insert_string += f"\triscv_insert_{name}(insn, value);\n"
    insert_string += "}\n"

    return insert_string


def generate_hi_lo_field_update_code(
    name: str,
    hi_variable_field: ImmVariableField,
    lo_variable_field: ImmVariableField,
) -> str:
    insert_string: str = (
        f"static inline void riscv_update_{name}(u32 *insn, u32 value) {{ \n"
    )
    insert_string += f"\t*insn &= ~(GENMASK({hi_variable_field.position[0]}, {hi_variable_field.position[1]}));\n"
    insert_string += f"\t*insn &= ~(GENMASK({lo_variable_field.position[0]}, {lo_variable_field.position[1]}));\n"
    insert_string += f"\triscv_insert_{name}(insn, value);\n"
    insert_string += "}\n"

    return insert_string


def get_enabled_variable_fields_generation(
    generation_options: GenerationOptions,
) -> tuple[
    list[ImmVariableFieldsFunctionType], list[NonImmVariableFieldsFunctionType]
]:
    imm_generation_functions: list[ImmVariableFieldsFunctionType] = []
    non_imm_generation_functions: list[NonImmVariableFieldsFunctionType] = []

    if generation_options.generate_extract_code:
        imm_generation_functions.append(generate_hi_lo_field_extract_code)
        non_imm_generation_functions.append(
            generate_variable_field_extract_code
        )

    if generation_options.generate_insert_code:
        imm_generation_functions.append(generate_hi_lo_field_insert_code)
        non_imm_generation_functions.append(generate_variable_field_insert_code)

    if generation_options.generate_update_code:
        imm_generation_functions.append(generate_hi_lo_field_update_code)
        non_imm_generation_functions.append(generate_variable_field_update_code)

    return imm_generation_functions, non_imm_generation_functions


def generate_variable_fields_code(
    variable_fields: list[tuple[str, VariableField]],
    generation_options: GenerationOptions,
) -> str:
    imm_generation_functions: list[ImmVariableFieldsFunctionType]
    non_imm_generation_functions: list[NonImmVariableFieldsFunctionType]
    variable_fields_code_string: str = ""

    (
        imm_generation_functions,
        non_imm_generation_functions,
    ) = get_enabled_variable_fields_generation(generation_options)

    for name, variable_field in variable_fields:
        if (
            isinstance(variable_field, ImmVariableField)
            and variable_field.imm_type == ImmType.HI
        ):
            lo_variable_field: VariableField = field_types[f"{name[:-2]}lo"]
            assert isinstance(lo_variable_field, ImmVariableField)

            for imm_generation_function in imm_generation_functions:
                variable_fields_code_string += (
                    imm_generation_function(
                        construct_hi_lo_name(name),
                        variable_field,
                        lo_variable_field,
                    )
                    + "\n"
                )
        elif (
            isinstance(variable_field, ImmVariableField)
            and variable_field.imm_type == ImmType.UNIFIED
        ) or not isinstance(variable_field, ImmVariableField):
            for non_imm_generation_function in non_imm_generation_functions:
                variable_fields_code_string += (
                    non_imm_generation_function(name, variable_field) + "\n"
                )
    return variable_fields_code_string


def is_rv32_only(instruction: Instruction) -> bool:
    return all([extension[:4] == "rv32" for extension in instruction.extension])


def is_rv64_only(instruction: Instruction) -> bool:
    return all([extension[:4] == "rv64" for extension in instruction.extension])


def generate_instruction_check_code(instruction: Instruction) -> str:
    check_instruction_string: str = ""

    arch_restricted: bool = False

    check_instruction_string += (
        f"bool riscv_is_{instruction.name}(u32 insn) {{\n"
    )

    if is_rv32_only(instruction):
        arch_restricted = True
        check_instruction_string += "#ifdef CONFIG_32BIT\n"
    elif is_rv64_only(instruction):
        arch_restricted = True
        check_instruction_string += "#ifdef CONFIG_64BIT\n"

    check_instruction_string += (
        f"\treturn ((insn & ({instruction.mask})) == ({instruction.match}));\n"
    )

    if arch_restricted:
        check_instruction_string += "#else\n"
        check_instruction_string += "\treturn 0;\n"
        check_instruction_string += "#endif\n"
    check_instruction_string += "}\n"
    return check_instruction_string


def get_params(
    variable_fields: list[str],
) -> list[str]:
    params: list[str] = []
    for field in variable_fields:
        # A hi immediate should always be paired with a lo immediate
        # Have a single parameter for a hi/lo split
        variable_field: VariableField = field_types[field]
        if isinstance(variable_field, ImmVariableField):
            if variable_field.imm_type == ImmType.HI:
                # Skip ImmType.LO because that is covered by this ImmType.HI
                # immediate
                params.append(construct_hi_lo_name(field))
            elif variable_field.imm_type == ImmType.UNIFIED:
                params.append(field)
        else:
            params.append(field)
    return params


def generate_instruction_create_code(instruction: Instruction) -> str:
    create_instruction_string: str = ""
    params = get_params(instruction.variable_fields)
    param_string = ", ".join([f"u32 {param}" for param in params])

    create_instruction_string += (
        f"u32 riscv_insn_{instruction.name}({param_string}) {{\n"
    )

    if is_rv32_only(instruction):
        create_instruction_string += "#ifdef CONFIG_32BIT\n"
    elif is_rv64_only(instruction):
        create_instruction_string += "#ifdef CONFIG_64BIT\n"

    create_instruction_string += (
        f"\tu32 insn = 0b{instruction.encoding.replace('-', '0')};\n"
    )
    for param in params:
        create_instruction_string += f"\triscv_insert_{param}(insn, {param});\n"

    if is_rv32_only(instruction):
        create_instruction_string += "#else\n"
        create_instruction_string += (
            '#error "This instruction is only available on rv32"\n'
        )
        create_instruction_string += "#endif\n"
    elif is_rv64_only(instruction):
        create_instruction_string += "#else\n"
        create_instruction_string += (
            '#error "This instruction is only available on rv64"\n'
        )
        create_instruction_string += "#endif\n"

    create_instruction_string += "\treturn insn;\n}\n"

    return create_instruction_string


def get_enabled_instruction_generation(
    generation_options: GenerationOptions,
) -> list[InstructionFunctionType]:
    generation_functions: list[InstructionFunctionType] = []

    if generation_options.generate_check_code:
        generation_functions.append(generate_instruction_check_code)

    if generation_options.generate_create_code:
        generation_functions.append(generate_instruction_create_code)

    return generation_functions


def generate_instruction_code(
    instruction_data: list[Instruction], generation_options: GenerationOptions
) -> str:
    instruction_code_string = ""
    instruction_functions: list[
        InstructionFunctionType
    ] = get_enabled_instruction_generation(generation_options)

    for instruction in instruction_data:
        for instruction_function in instruction_functions:
            instruction_code_string += instruction_function(instruction) + "\n"
    return instruction_code_string


def get_configured_instructions(
    config_file_path: str, sort_file: bool
) -> set[str]:
    configured_instructions: set[str] = set()

    with open(config_file_path, "r") as config_file:
        for line in config_file:
            configured_instructions.add(line.strip())

    if sort_file:
        sorted_configured_instructions = list(configured_instructions)
        sorted_configured_instructions.sort()
        with open(config_file_path, "w") as config_file:
            config_file.write("\n".join(sorted_configured_instructions))

    return configured_instructions


def get_variable_fields(
    instruction: Instruction,
) -> list[tuple[str, VariableField]]:
    return [
        (variable_field, field_types[variable_field])
        for variable_field in instruction.variable_fields
    ]


def get_instruction_data(
    extensions: list[str],
    configured_instructions: set[str],
) -> tuple[list[Instruction], list[tuple[str, VariableField]]]:
    instr_dict: dict[str, dict[str, Any]] = create_inst_dict(
        extensions,
        include_pseudo=True,
    )

    instructions: list[Instruction] = []
    variable_fields: set[tuple[str, VariableField]] = set()
    for instruction_str in configured_instructions:
        if instruction_str in instr_dict.keys():
            instruction = Instruction(
                name=instruction_str, **instr_dict[instruction_str]
            )
            instructions.append(instruction)
            variable_fields = variable_fields.union(
                get_variable_fields(instruction)
            )
        else:
            print(
                f"Instruction ({instruction_str}) not found in provided extensions: {extensions}"
            )

    return sorted(
        instructions, key=lambda instruction: instruction.name
    ), sorted(list(variable_fields))


def generate_macros() -> str:
    generated_macros_string: str = (
        "#define RV_X(X, s, mask)  (((X) >> (s)) & (mask))\n\n"
    )
    return generated_macros_string


def generate_includes() -> str:
    generated_includes_string: str = "#include <linux/bits.h>\n\n"
    return generated_includes_string


def generate_code(
    variable_fields: list[tuple[str, VariableField]],
    instruction_data: list[Instruction],
    generation_options: GenerationOptions,
) -> str:
    generated_code_string: str = ""
    generated_code_string += generate_includes()
    generated_code_string += generate_macros()
    generated_code_string += generate_variable_fields_code(
        variable_fields, generation_options
    )
    generated_code_string += generate_instruction_code(
        instruction_data, generation_options
    )
    return generated_code_string[:-1]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse an instr_dict.yaml from riscv-opcodes"
    )
    parser.add_argument(
        "output_file_path", type=str, help="Path to output file."
    )
    parser.add_argument(
        "config_file_path",
        type=str,
        help="""Path to config file. Code will be generated for each opcode
        placed in this file. Place one instruction per line.""",
    )
    parser.add_argument("--extensions", nargs="+", default=["rv*"])
    parser.add_argument("--generate_extract_code", action="store_false")
    parser.add_argument("--generate_insert_code", action="store_false")
    parser.add_argument("--generate_update_code", action="store_false")
    parser.add_argument("--generate_check_code", action="store_false")
    parser.add_argument("--generate_create_code", action="store_false")
    args = parser.parse_args()
    instruction_data, variable_fields = get_instruction_data(
        args.extensions,
        get_configured_instructions(args.config_file_path, True),
    )
    generation_options = GenerationOptions(
        args.generate_extract_code,
        args.generate_insert_code,
        args.generate_update_code,
        args.generate_check_code,
        args.generate_create_code,
    )

    with open(args.output_file_path, "w+") as file:
        file.write(
            generate_code(variable_fields, instruction_data, generation_options)
        )
