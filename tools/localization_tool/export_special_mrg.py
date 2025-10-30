#!/usr/bin/env python
# -*- coding:utf-8 -*-
# 
# Author: root-none
# Script_Text_MRG Export Base deepLuna(Hakanaou, https://github.com/Hakanaou/deepLuna)
"""
Export special mrg content tool to help localization work.
For now, it support:
  script_text.mrg
  scr_adr.mrg
"""
import sys
import os
import json
import argparse
import struct

from lib.mrgd import ArchiveInfo


def script_text_export(mrg_file, entries_desc, output_dir):
    entries_num = len(entries_desc)
    assert entries_num%2==0, "script_text Entries cannot split evenly.(One language text per two entry data)"
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
    print(f"Export {entries_num//2} language type script-text done.")


def scr_adr_export(mrg_file, entries_desc, output_dir, scr_names_path):
    entries_num = len(entries_desc)
    if scr_names_path and os.path.exists(scr_names_path):
        with open(scr_names_path, 'r', encoding='utf-8') as f:
            scr_names = [line.rstrip('\n') for line in f.readlines()]
        assert entries_num==len(scr_names), "Usually won't happend this error, please check."
    else:
        scr_names = [f'{index}' for index in range(1,entries_num+1)]

    for i, entry in enumerate(entries_desc):
        mrg_file.seek(entry.real_offset, 0)
        adr_data = mrg_file.read(entry.real_size)
        with open(os.path.join(output_dir, scr_names[i]), 'wb') as f:
            f.write(adr_data)
    print(f"Export {entries_num} scr address data done.")


def main(args):    
    input_mrg_path = args.input_mrg
    mrg_type = args.mode
    assert mrg_type and os.path.exists(input_mrg_path), f"Input {mrg_type}.mrg does not exist! path: {input_mrg_path}"
    print(f"---{mrg_type.upper()}_MRG Exportor---")
    
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
    
    if mrg_type == "script_text":
        script_text_export(mrg_file, entries_desc, output_dir)
    elif mrg_type == "scr_adr":
        scr_adr_export(mrg_file, entries_desc, output_dir, args.extra)
    else:
        print(f"Unknown mrg {mrg_type}. Exit...")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('input_mrg', metavar='input_mrg', help='Input *.mrg.')
    parser.add_argument('-m', '--mode', required=True, metavar='mrg-name', help='Different solution for different mrg.')
    parser.add_argument('-e', '--extra', metavar='extra_file', help='Extra file arguments.')
    return parser, parser.parse_args()


if __name__ == "__main__":
    parser, args = parse_args()
    main(args)
