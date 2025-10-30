#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# Rewrite base prep_tpl and make_mzx
# comes with ABSOLUTELY NO WARRANTY.
#
# Portions Copyright (C) 2014 Nanashi3.
# Rewrite Author: root-none, Lisen
"""
Usage:
prep_scr.py decode [-o output_parent_path] [-u] [-v] <input_path of *.scr file/folder>
prep_scr.py encode [-s source_scripts_path] [-o output_path] [-t font_code_map_tbl] <input_path of *.csv file/folder>
"""

import argparse
import re
import sys
import csv
from pathlib import Path

import filename_utils
import font_utils

text_command = {
    "_LVSV": r'_LVSV\((.*)\)\)',
    "_STTI":"",  # TODO: wait to add
    "_MSAD": r'_MSAD\((.*)$',
    r"_ZM[0-9a-f]{5}": r'_ZM[0-9a-f]{5}\(([^)]*)(?:\)|$)',
    r"SEL[R]": r'_SELR\([^;]*;/([^)]*)\)\)',
    r"_MSA\d": r"_MSA\d\((.*)$",
    "_RTTH": r'_RTTH\([^,]*,([^)]*)\)\)',
    "_MTLK": r'_MTLK\([^,]*,\s*([^)]*)\)'
}

special_bytes = []


def decode_scr_bin(args):
    input_path = Path(args.input)
    assert input_path.exists()
    # two output for decode-text and decode-scr
    if args.output_parent:
        parent_path = Path(args.output_parent)
        assert parent_path.exists() and parent_path.is_dir(), "output_parent path must be a folder."
    else:
        parent_path = (input_path.parent if input_path.is_file() else input_path).parent
    decode_text_path = parent_path.joinpath("decoded_text")
    decode_scr_path = parent_path.joinpath("decoded_script")

    combine_text_patterns = re.compile("|".join(f"({p})" for p in text_command))
    raw_files = filename_utils.file_or_folder(input_path, '*.scr')
    for scr_path in raw_files:
        print(f"Decoding {scr_path.name}")
        with scr_path.open('rb') as f:
            raw_buf = f.read()

        out_line = []
        out_text = []
        for line_i, instr in enumerate(raw_buf.split(b';')):
            instr_text = instr.decode('cp932', errors='surrogateescape')
            # find all surrogate-escape codepoints
            for spe_uni in re.findall(r'[\uDC80-\uDCFF]', instr_text):
                spe = hex(ord(spe_uni)-0xdc00)
                if (spe,spe_uni) not in special_bytes:
                    special_bytes.append((spe,spe_uni))

            instructor_match = combine_text_patterns.search(instr_text)
            if instructor_match is not None:
                instr_text = re.sub(r'[\uDC80-\uDCFF]',
                                    lambda m:  f'_u[{(ord(m.group(0))-0xDC00):02x}]',
                                    instr_text)
                for i, (_, pattern_str) in enumerate(text_command.items()):
                    if instructor_match.group(i+1) is not None:
                        pattern = re.compile(pattern_str)
                        content_match = pattern.search(instr_text)
                        if content_match is None: continue
                        assert len(content_match.groups())==1, f"[Debug] {instructor_match.group(i+1)} match more than one text result!"
                        # In case some part(like ruby<*,*>) wiil use ',' so replace it with ';/'
                        content = content_match.group(1).replace(',',';/')
                        line_offset = line_i
                        out_text.append(f"{line_offset},{content},"+
                                        (f",{instructor_match.group(i+1)}" if args.verbose else ''))

            out_line.append(instr_text)
        
        # save decode content
        if out_text:
            out_csv_name = scr_path.with_suffix('.csv').name
            decode_text_path.mkdir(parents=True, exist_ok=True)
            with decode_text_path.joinpath(out_csv_name).open('w', encoding='utf-8-sig') as f:
                f.write("\n".join(out_text))

        # save decode scr
        if out_line:
            out_txt_name = scr_path.with_suffix('.txt').name
            decode_scr_path.mkdir(parents=True, exist_ok=True)
            text_encode = 'utf-8' if args.unicode else 'cp932'
            with decode_scr_path.joinpath(out_txt_name).open('w', encoding=text_encode) as f:
                f.write("\n".join(out_line))
    if special_bytes:
        # special instruction byte may surrogate-escape
        print(f"Found special byte in all scr: {special_bytes}")
    print(f'Done Decode.\nAll decoded scr save in {decode_scr_path.absolute()}.\nAll decoded text save in {decode_text_path.absolute()}.')


def load_translations(csv_reader, char_map_code_dict, encode_lang='jp'):
    translations_dict = {}
    for row in csv_reader:
        assert len(row)==3, "Debug row length, if row<3 need to check or use other solution."
        line_offset, src, tran = row[0], row[1], row[2]

        # restore special byte
        src = re.sub(r'_u\[([0-9a-f]{2})\]',
                     lambda m: chr(0xDC00 + int(m.group(1),16)),
                     src)
        tran = re.sub(r'_u\[([0-9a-f]{2})\]',
                     lambda m: chr(0xDC00 + int(m.group(1),16)),
                     tran)

        if tran == '': tran = src  # not translated
        # replace some char in non-english lang
        src = src.replace(';/',',')
        if encode_lang!='en':
            # ensure some ascii characters won't use in text
            tran = tran.replace(", ",chr(0xff0c)).replace(",",chr(0xff0c)).replace(';/',',')
        encode_src = src.encode('cp932', errors='surrogateescape')
        encode_tran = font_utils.encode_with_mapping(tran,char_map_code_dict)
        translations_dict[int(line_offset)] = (encode_src, encode_tran)
    return translations_dict


def encode_csv_to_scr(args):
    # csv file(s) contains translations text
    input_path = Path(args.input)
    assert input_path.exists()
    # original scr(s) path
    scrs_path = Path(args.scr_path)
    # output translated scr(s)
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = (input_path.parent if input_path.is_file() else input_path).parent
        output_path = output_path.joinpath("encoded_script")
    output_path.mkdir(parents=True, exist_ok=True)
    # read characters code mapping table
    if args.tbl_path:
        tbl_type = 'json' if args.tbl_path.endswith('.json') else 'tbl'
        with open(args.tbl_path, 'r', encoding='utf-8') as f:
            tbl_content = f.read()
        char_map_tbl = font_utils.load_font_code_table(tbl_content, tbl_type)
        char_code_mapping = font_utils.build_char_map_code(char_map_tbl)
    else:
        char_code_mapping = {}

    translate_files = filename_utils.file_or_folder(input_path, '*.csv')
    for csv_file in translate_files:
        print(f"Encoding {csv_file.stem}")

        # load translations with char-mapping-table
        with csv_file.open('r', encoding='utf-8-sig') as f:
            csv_reader = csv.reader(f)
            translations = load_translations(csv_reader, char_code_mapping, args.lang)

        assert scrs_path.joinpath(csv_file.stem+'.scr').exists(), f"Can't find {csv_file.stem+'.scr'} file in {scrs_path.absolute()} which need to encode."
        with scrs_path.joinpath(csv_file.stem+'.scr').open('rb') as f:
            raw_buf = f.read()
            scr_lines = raw_buf.split(b';')
        for line_i, tran_set in translations.items():
            orig_bytes = scr_lines[line_i]
            assert orig_bytes.index(tran_set[0])>=0
            tran_bytes = orig_bytes.replace(tran_set[0], tran_set[1])
            scr_lines[line_i] = tran_bytes
        
        # save encode scr
        with output_path.joinpath(csv_file.stem+'.scr').open('wb') as f:
            assert scr_lines[-1]==b''
            f.write(b';'.join(scr_lines))
    print(f'Done Encode.\nAll new encode scr files save in {output_path.absolute()}.')


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    subparsers = parser.add_subparsers(title='subcommands', dest='subcommand')

    parser_decode = subparsers.add_parser('decode', help='Decode scr file.')
    parser_decode.add_argument('input', metavar='input_path', help='Input *.scr file or folder.')
    parser_decode.add_argument('-o', '--output_parent', required=False,
                               metavar='output_parent_path', help='Output (two)folder parent path.')
    parser_decode.add_argument('-u', '--unicode', action="store_true",
                               default=False, help='Set to save decode-scr in utf-8 encoding.')
    parser_decode.add_argument('-v', '--verbose', action="store_true",
                               default=False, help='output csv will has some debug parts.')

    parser_encode = subparsers.add_parser('encode', help='Encode translation csv files to scr.')
    parser_encode.add_argument('input', metavar='input_path', help='Input *.csv file or folder.')
    parser_encode.add_argument('-s', '--scr_path', required=True,
                               metavar='source_scripts_path', help='Origin scr files path to encode.')
    parser_encode.add_argument('-o', '--output', required=False, metavar='output_path', help='Output folder.')
    parser_encode.add_argument('-t', '--tbl_path', required=False,
                               metavar='font_code_tbl', help='(Option)Scr font code map table for encoding.')
    parser_encode.add_argument('-l', '--lang', required=False, default='jp', help='(Option)Encoding text language. Default jp.')

    return parser, parser.parse_args()


if __name__ == '__main__':
    parser, args = parse_args()
    if args.subcommand == "decode":
        decode_scr_bin(args)
    elif args.subcommand == "encode":
        encode_csv_to_scr(args)
    else:
        parser.print_usage()
        sys.exit(20)
    sys.exit(0)
    
