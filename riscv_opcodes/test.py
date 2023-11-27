import parse_extensions
import yaml


count = 0
inst_dict = {}
for instruction in parse_extensions.collect_instructions(
    ["rv_zks"], parse_extensions.IncludePseudoOps.ALL
):
    inst_dict[instruction.name] = {
        "args": list(instruction.args),
        "encoding": instruction.encoding,
        "extension": instruction.extension,
        "mask": instruction.mask,
        "match": instruction.match,
    }

print(yaml.dump(inst_dict))
