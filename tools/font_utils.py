#!/usr/bin/env python
# -*- coding:utf-8 -*-
'''Some font/scr file utils'''

import json
from dataclasses import dataclass

ASCII_RANGE = [code for code in range(0x20,0x80)]

HALFWIDTH_RANGE = [0xf8f0] + [code for code in range(0xff61,0xffa0)]

@dataclass
class tbl_t:
    tcode : bytes = b""
    tchar : str = ""


def load_font_code_table(tbl_str, tbl_type='tbl', split_char='='):
    char_map_tbl = []
    if tbl_type == 'tbl':
        for map_line in tbl_str.split('\n'):
            if not map_line: continue
            map_code_hex, map_char = map_line.split(split_char)
            char_map_tbl.append(tbl_t(bytes.fromhex(map_code_hex), map_char))
    elif tbl_type == 'json':
        for map_code_hex, map_char in json.loads(tbl_str).items():
            char_map_tbl.append(tbl_t(bytes.fromhex(map_code_hex), map_char))
    return char_map_tbl


def build_code_map_char(char_map_tbl):
    return {char_set.tcode: char_set.tchar for char_set in char_map_tbl}


def build_char_map_code(char_map_tbl):
    return {char_set.tchar: char_set.tcode for char_set in char_map_tbl}


def encode_with_mapping(text_string, mapping_dict):
    encode_buf = b""
    if mapping_dict:
        for char in text_string:
            if ord(char) in ASCII_RANGE\
                or ord(char) in HALFWIDTH_RANGE\
                    or 0xDC80<=ord(char)<=0xDCFF:
                encode_buf += char.encode("cp932", errors='surrogateescape')
            else:
                char_code = mapping_dict[char]
                assert type(char_code)==bytes
                encode_buf += char_code
    else:
        encode_buf = text_string.encode("cp932", errors='surrogateescape')

    return encode_buf
