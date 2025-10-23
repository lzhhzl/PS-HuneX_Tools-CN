#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# Base deepLuna(Hakanaou, https://github.com/Hakanaou/deepLuna)
import sys
import os
import json
import struct

from lib.mrgd import ArchiveInfo


def main():
    print("---Script_Text_MRG Exportor---")
    if len(sys.argv) != 2:
        print("\nUsage: python export_script_text.py <Input script_text.mrg>")
        return
    
    input_mrg_path = sys.argv[1]
    assert os.path.exists(input_mrg_path), f"Input script_text.mrg does not exist! path: {input_mrg_path}"
    output_dir = f"{os.path.splitext(input_mrg_path)[0]}_export"
    os.makedirs(output_dir, exist_ok=True)

    mrg_file = open(input_mrg_path, 'rb')
    mrg_header = mrg_file.read(6)  # magic
    if mrg_header != b'mrgd00':
        print(f'Unknown header: {mrg_header}. This file might not mrgd00 format!')
        sys.exit(1)
    entries_num, = struct.unpack('<H', mrg_file.read(2))
    data_start_offset = (6 + 2 + entries_num * 8)
    
    entries_desc = []
    for i in range(entries_num):
        data_block = mrg_file.read(8)
        offset1, offset2, sector_size_upper_boundary, size_low = struct.unpack('<HHHH', data_block)
        entry_info = ArchiveInfo(offset1, offset2, sector_size_upper_boundary,
                                 size_low, data_start_offset, False)
        entries_desc.append(entry_info)

    assert entries_num%2==0, "Strings Entries cannot split evenly."
    for i in range(0, entries_num, 2):
        mrg_file.seek(entries_desc[i].real_offset, 0)
        strings_offset_data = mrg_file.read(entries_desc[i].real_size)
        mrg_file.seek(entries_desc[i+1].real_offset, 0)
        strings_data = mrg_file.read(entries_desc[i+1].real_size)

        index_strings_tbl = {}
        offset_count = len(strings_offset_data) // 4
        for n in range(offset_count):
            data_start, = struct.unpack('>I', strings_offset_data[n*4:n*4+4])
            data_end, = struct.unpack('>I', strings_offset_data[(n+1)*4:(n+1)*4+4])

            # Zero-len marks end of offset table
            if data_start == data_end:
                break

            # extract the associated string data
            str_data = strings_data[data_start:data_end]
            index_strings_tbl[f"${n:06}"] = str_data.decode('utf-8')
        
        # save strings in json and csv
        output_json_path = os.path.join(output_dir, f"script_text-{i//2}.json")
        json_f = open(output_json_path, 'w', encoding='utf-8')
        json.dump(index_strings_tbl, json_f, ensure_ascii=False)
        json_f.close()
        output_csv_path = os.path.join(output_dir, f"script_text-{i//2}.csv")
        with open(output_csv_path, 'w', encoding='utf-8') as csv_f:
            for index, string_data in index_strings_tbl.items():
                csv_f.write(f"{index},{string_data}\n")
    print(f"Export {entries_num//2} type script-text done.")
    

if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    main()
