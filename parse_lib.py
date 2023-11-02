import pathlib

def create_inst_dict2(file_filter:str, include_pseudo:bool = False, include_pseudo_ops: list[str] | None = None):
    # Can do one pass. Create queue of all filenames to parse
    # When encounter import/pseudo, add onto the queue and dict of import/pseudo to parse
    # When processing file, first check if it has been processed yet
    #   If not read file and cache
    #   If it has, process all remaining import/pseudo instructions and remove them from list

    filenames_queue: list[str] = []
    parsed_filenames: set[str] = set()
    instructions_to_parse: dict[str, str] = {}

    # filename:
    #   instruction_name:
    #       instruction_field: value
    inst_dict: dict[str, dict[str, dict[str, str]]] = {}

    if not include_pseudo_ops:
        include_pseudo_ops = []

    pathlib.Path(__file__).parent
    opcodes_dir: str = os.path.dirname(os.path.realpath(__file__))
    for fil in file_filter:
        filenames_queue += glob.glob(f'{opcodes_dir}/{fil}')
    filenames_queue.sort(reverse=True)
