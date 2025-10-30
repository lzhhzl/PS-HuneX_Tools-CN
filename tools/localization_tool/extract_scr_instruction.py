import re
import json
from pathlib import Path
import os
os.chdir(os.path.dirname(__file__))

scr_path = r""
scr_ext = "*.scr"
text_type = True

other_command = [  # other instruction, not related scr text
]

ignore_command = [  # other instruction contain sjis text but not care
]

match_command = [  # main instruction about scr text display action
]

param_index_pattern = r'`\d{3}'

scr_dir = Path(scr_path)
assert scr_dir.is_dir(), "need the directory path contain scr files"
raw_scr_list = scr_dir.glob(scr_ext)
text_instruction_list = []
other_instruction_list = []
param_index_list = []
for scr_path in raw_scr_list:
    with scr_path.open("rb") as f:
        raw_data = f.read()
    assert raw_data.split(b';')[-1]==b""
    for buf in raw_data.split(b';')[:-1]:
        decode_text = buf.decode('cp932', errors='surrogateescape')
        instruction_text = decode_text[:decode_text.index('(')]
        match_result1 = re.search(rf'{"|".join(match_command)}', instruction_text)
        if match_command and match_result1 is not None:
            continue
        if len(re.sub('[ -~]', '', decode_text))>0:
            # matches containing non-ASCII characters
            match_result2 = re.search(rf'{"|".join(ignore_command)}', instruction_text)
            if not ignore_command or match_result2 is None:
                text_instruction_list.append(instruction_text)
        else:
            # other action instruction
            match_result2 = re.search(rf'{"|".join(other_command)}', instruction_text)
            if not other_command or match_result2 is None:
                other_instruction_list.append(instruction_text)
        match_result3 = re.findall(param_index_pattern, decode_text)
        if match_result3:
            param_index_list += match_result3
    print(f"Read scr: {scr_path.name} instruction.")
text_instruction_set = sorted(set(text_instruction_list))
other_instruction_set = sorted(set(other_instruction_list+ignore_command))+other_command
other_instruction_dict = {}
for oi in other_instruction_set:
    other_instruction_dict[oi] = ""
param_index_set = sorted(set(param_index_list))
param_index_dict = {}
for pi in param_index_set:
    param_index_dict[pi] = ""

save_text_instruction_path = r"scr_text_instruction.json"
save_other_instruction_path = r"scr_other_instruction.json"
save_param_index_path = r"scr_param_index.json"
text_instruction_f = open(save_text_instruction_path, "w", encoding='utf-8')
other_instruction_f = open(save_other_instruction_path, "w", encoding='utf-8')
param_index_f = open(save_param_index_path, "w", encoding='utf-8')
json.dump(text_instruction_set, text_instruction_f, ensure_ascii=False)
json.dump(other_instruction_dict, other_instruction_f, ensure_ascii=False)
json.dump(param_index_dict, param_index_f, ensure_ascii=False)
text_instruction_f.close()
other_instruction_f.close()
param_index_f.close()
