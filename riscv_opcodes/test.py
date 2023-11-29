import parse_extensions
import yaml


count = 0
inst_dict = {}
for instruction in parse_extensions.collect_instructions(
    ["rv_zksed"], parse_extensions.AnyPseudoOp()
):
    inst_dict[instruction.name] = {
        "encoding": instruction.encoding,
        "extension": instruction.extensions,
        "mask": instruction.mask,
        "match": instruction.match,
        "variable_fields": list(instruction.args),
    }

with open("instr_dict2.yaml", "w") as outfile:
    yaml.dump(inst_dict, outfile, default_flow_style=False)
