#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# Rewrite base MZP Extractor(_extract_mzp.py)
# comes with ABSOLUTELY NO WARRANTY.
#
# Author:
# Portions Copyright (C) 2016 Hintay <hintay@me.com>
# Portions Copyright (C) 2016 Quibi
# Rewrite by ddn_y(denyu), root-none
#
# MZP image files extraction utility
# For more information, see Specifications/mzp_format.md

import os
import json
import struct
import logging
import argparse
import sys
from pathlib import Path
from filename_utils import file_or_folder
from lib.mrgd import ArchiveInfo
from _extract_mzp_tiles import MzpFile, get_dbg_hep_infos


def logging_init(debug_flag):
    if debug_flag:
        logging_level = logging.DEBUG
    else:
        logging_level = logging.INFO
    logging.basicConfig(level=logging_level, format='[%(levelname)s] %(message)s')


def extract(args):
    file_path = Path(args.input)
    assert file_path.exists(), f'Error: This file or folder does not exist: {args.input}'

    output_path = Path(args.output) if args.output else (file_path.parent if file_path.is_file() else file_path)
    files_path_list = file_or_folder(file_path, '**/*.[Mm][Zz][Pp]')
    tiles_summary = {}
    for file in files_path_list:
        mzp_name = file.stem
        mzp_file = file.open('rb')
        logging.info(f'Extracting from {file.name}')
        # check magic
        header = mzp_file.read(6)
        assert header == b'mrgd00', f'Error: This file is not MZP(mrgd00) format. Header:{header}'
        
        # get entries num
        entries_num, = struct.unpack('<H', mzp_file.read(2))
        if entries_num == 0:
            # it did have some mzp like this, strangely
            continue
        # get entries desc
        entries_desc = []
        file_data_start_offset = (6 + 2 + entries_num * 8)
        for i in range(entries_num):
            sector_offset, byte_offset, sector_size_upper_boundary, size_low = struct.unpack('<HHHH', mzp_file.read(8))
            entries_desc.append(
                ArchiveInfo(sector_offset, byte_offset, sector_size_upper_boundary,
                            size_low, file_data_start_offset, False))
        
        # read mzp and extract
        mzp_obj = MzpFile(file, mzp_file, entries_desc,
                          args.palette_convert, args.extend)
        mzp_obj.extract_tiles()
        mzp_obj.save_image(output_path)
        tiles_summary[mzp_name] = mzp_obj.get_tile_info()
        mzp_file.close()
    logging.info(f"Extract all mzp images to {output_path.absolute()}")
    # save all tiles_summary as json
    with open(output_path.joinpath('tiles_summary.json'),'w',encoding='utf-8') as f:
        json.dump(tiles_summary, f, ensure_ascii=False, indent=4, sort_keys=True)
        logging.info('Save all tiles_summary.')


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('input', metavar='input_path', help='Input .mzp file or folder path.')
    parser.add_argument('--output', '-o', metavar="output_path", help='(Optional)Output folder path.')
    parser.add_argument('--palette_convert', '-ptc', action="store_true", default=False, help='If set, 4/8bpp palette(index) image will output tga(palette-index) and png(RGBA).')
    parser.add_argument('--extend','-ext', action="store_true", default=False, help='Few mzp files might have tile X*Y count > entries-num. This test arg can solve.')
    parser.add_argument('--verbose', '-v', action="store_true", default=False, help='If set, output logging.DEBUG messages.')
    return parser, parser.parse_args()


if __name__ == '__main__':
    # os.chdir(os.path.dirname(os.path.abspath(__file__)))
    parser, args = parse_args()
    if args.input is not None:
        logging_init(args.verbose)
        extract(args)
    else:
        parser.print_usage()
        sys.exit(20)
    sys.exit(0)
