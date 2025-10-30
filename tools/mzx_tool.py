#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# Author: Hintay, root-none
"""
Decompress one or several MZX files
or Compress one or several files as MZX

mzx_tool comes with ABSOLUTELY NO WARRANTY.
"""

import os
import sys
import argparse
import struct
import shutil
from pathlib import Path
from lib.mzx import mzx0_decompress, mzx0_compress
import filename_utils


def decompress(args):
    input_path = Path(args.input)
    xor_flag = args.is_xor if args.is_xor is not None else 1
    folder_path = filename_utils.file_or_folder(input_path, '*.[Mm][Zz][Xx]')
    output_path = None

    for file_path in folder_path:
        if not output_path:
            output_path = file_path.parent
            output_dir = f'{output_path.stem.replace("_compress","")}_decompress'
            output_path = output_path.with_name(output_dir)
            os.makedirs(output_path, exist_ok=True)
        mzx_name = file_path.stem
        with file_path.open('rb') as data:
            head_part = data.read(7)
            offset = 7 if(head_part == b'LV\x03\x00\x00\t\x00') else 0
            mzx_name += '.scr' if(head_part != b'LV\x03\x00\x00\t\x00') else ''
            data.seek(offset)
            _magic, dec_size = struct.unpack('<LL', data.read(0x8))
            datablock_size = file_path.stat().st_size - offset - 8
            status, dec_buf = mzx0_decompress(data, datablock_size, dec_size, xor_flag)
            if status != "OK":
                raise Exception("[{0}] {1}".format(file_path, status))
            out_name = filename_utils.add_suffix(mzx_name,dec_buf.read())
            dec_buf.seek(0)
            with output_path.joinpath(out_name).open('wb') as dbf:
                shutil.copyfileobj(dec_buf, dbf)
        print(f"decompress {file_path.name} to {out_name}")
    print(f"Output directory \'{output_path.absolute()}\'")


def compress(args):
    input_path = Path(args.input)
    xor_flag = args.is_xor
    folder_path = filename_utils.file_or_folder(input_path, '*')
    output_path = None

    for file_path in folder_path:
        if not output_path:
            output_path = file_path.parent
            output_dir = f'{output_path.stem.replace("_decompress","")}_compress'
            output_path = output_path.with_name(output_dir)
            os.makedirs(output_path, exist_ok=True)
        out_name = file_path.stem + '.mzx'
        with file_path.open('rb') as data:
            com_buf = mzx0_compress(data, file_path.stat().st_size, xor_flag)
            with output_path.joinpath(out_name).open('wb') as cbf:
                # add special prefix data for atrac file
                if com_buf[:4] == b"\x52\x49\x46\x46" and\
                    com_buf[0x8:0x10] == b"\x57\x41\x56\x45\x66\x6D\x74\x20":
                    cbf.write(b'LV\x03\x00\x00\t\x00')
                cbf.write(com_buf)
        print(f"compress {file_path.name} to {out_name}")
    print(f"Output directory \'{output_path.absolute()}\'")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    subparsers = parser.add_subparsers(title='subcommands', dest='subcommand')

    # decompress
    parser_decompress = subparsers.add_parser('decompress', help='decompress mzx with/without xor')
    parser_decompress.add_argument('-x', '--xor',
                                   dest='is_xor', type=int,
                                   help='Decompress with(1) or without(0) xorff')
    parser_decompress.add_argument('input', metavar='input_path', help='Input mzx file or folder.')

    # compress
    parser_compress = subparsers.add_parser('compress', help='compress file with/without xor')
    parser_compress.add_argument('-x', '--xor',
                                 dest='is_xor', type=int,
                                 help='Compress with(1) or without(0) xorff')
    parser_compress.add_argument('input', metavar='input_path', help='Input file or folder.')

    return parser, parser.parse_args()


if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    parser, args = parse_args()
    if args.subcommand == "decompress":
        decompress(args)
    elif args.subcommand == "compress":
        compress(args)
    else:
        parser.print_usage()
        sys.exit(20)
    sys.exit(0)
