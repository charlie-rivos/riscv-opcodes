import parse_extensions
import yaml


count = 0
inst_dict = {}
instruction_collector = parse_extensions.InstructionCollector()

for instruction in instruction_collector.collect(
    ["rv*"], set()
):
    inst_dict[instruction.name.replace(".", "_")] = {
        "encoding": instruction.encoding,
        "extension": sorted(instruction.extensions, reverse=True),
        "mask": instruction.mask,
        "match": instruction.match,
        "variable_fields": list(instruction.args),
    }

with open("instr_dict2.yaml", "w") as outfile:
    yaml.dump(inst_dict, outfile, default_flow_style=False)
