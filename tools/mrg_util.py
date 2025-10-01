#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# Author: ddn_y(denyu), root-none, Lisen(SpriteLisen)
# Base on Hintay <hintay@me.com>, Nanashi3 and Quibi etc. work
#
# MRG(header mrgd00) files extraction & creation utility
# For more information, see Specifications/hed_format.md
"""
mrg_util —— rewrite base on hedutil and unpack_allsrc.

Script to unpack or repack a .hed/.nam/.mrg triple

mrg_util comes with ABSOLUTELY NO WARRANTY.
"""

import argparse
import struct
import os
import sys
import io
from pathlib import Path

from lib.mrgd import ArchiveInfo, VoiceInfo
from lib.mrgd import calculate_entry_desc, add_entry_padding
import filename_utils

MODE = ''  # specific game mode for diffrent processing

"""MRG struct{
    (optional) char magic[6];  // mrgd00
    (optional) uint16 entries_num;  // number of archive entry descriptors
    hed struct{
        entries_num times uint64 Entry Descriptor data
    }
    { File Data }
}
"""


class CustHelpAction(argparse._HelpAction):  # show subcommand help
    def __call__(self, parser, namespace, values, option_string=None):
        parser.print_help()
        for subparser_action in parser._actions:
            if isinstance(subparser_action, argparse._SubParsersAction):
                for choice, subparser in subparser_action.choices.items():
                    print("\n\n== {} ==".format(choice))
                    print(subparser.format_help())
        parser.exit()


def get_nam_pattern(nam_file_name):
    if nam_file_name.find('voice') >= 0:
        if MODE == 'fateSN':
            # Fate Stay Night Realta Nua
            return 0x8
        elif MODE == 'aiyokuEus':
            # Aiyoku no Eustia
            return 0x10
    return 0x20


# Author: root-none, rewrite base hedutil.NamUtil
def extract_filenames(nam_filename, nam_data, fix=False):
    namelist = []
    if nam_data[:0x7] == b'MRG.NAM':
        # TODO: haven't test this part yet
        names_count, = struct.unpack('<I', nam_data[0x10:0x14])
        nam_index = {}
        for i in range(names_count):
            nam_index[i], = struct.unpack("<I", nam_data[(0x20+i*4): (0x20+i*4+4)])
        nam_index[names_count] = len(nam_data)  # make sure have the end
        for i in range(names_count):
            start_offset, next_offset = nam_index[i], nam_index[i + 1]
            length = next_offset - start_offset - 4
            in_count, = struct.unpack("<I", nam_data[start_offset: (start_offset+4)])
            if in_count != i:
                raise Exception(f"[DEBUG]Error: can't get name from index {i}, the in-header index is {in_count}")
            name_bytes = nam_data[(start_offset+4): (start_offset+4+length)]
            if name_bytes.find(b'\x00')>=0:
                name_bytes = name_bytes[:name_bytes.index(b'\x00')]
            file_name = name_bytes.decode('cp932')
            namelist.append(file_name)
    else:
        nam_length = get_nam_pattern(nam_filename)
        names_count = len(nam_data) // nam_length
        for i in range(names_count):
            file_name = filename_utils.fix_file_name(i, MODE) if fix else ""
            name_bytes = nam_data[(i*nam_length): (i*nam_length+nam_length)]
            name_bytes = name_bytes.replace(b'\x01', b'')
            if name_bytes.find(b'\x00')>=0:
                name_bytes = name_bytes[:name_bytes.index(b'\x00')]
            if i+1!=names_count and name_bytes==b"":
                print(f"Debug: have empty name bytes(index:{i}) in nam file")
            try:
                file_name += name_bytes.decode('cp932')
            except UnicodeDecodeError:
                file_name += f"error_name_{name_bytes.hex()}"
            namelist.append(file_name)
    return namelist


def unpack(args):
    # read input file
    mrg_path = Path(args.input)
    mrg_name = mrg_path.stem.lower()  # mrg name
    hed_path = mrg_path.with_suffix('.hed')
    nam_path = mrg_path.with_suffix('.nam')
    assert mrg_path.exists(), f"{mrg_name}.mrg not found. Please pass the path to the folder it is located in."

    # set output dir
    output_path = mrg_path.with_name(mrg_name + '_unpack')
    try:
        output_path.mkdir(parents=True)
    except FileExistsError:
        print(f"Output directory \'{output_path.resolve()}\' already exists. You should delete it first.")
        return

    # read filenames in .nam file(if exists)
    filename_list = []
    if nam_path.exists():
        print(f"Find \'{mrg_name}.nam\' file.")
        with open(nam_path, 'rb') as f:
            nam_data = f.read()
        filename_list += extract_filenames(nam_path.name,nam_data)

    # read mrg file hed part
    mrg_file = open(mrg_path, 'rb')
    has_hed = hed_path.exists()
    if has_hed:  # if hed file exists, use it first
        print(f"Find \'{mrg_name}.hed\' file.")
        hed_file = open(hed_path, 'rb')
        _low, first_entry_high = struct.unpack('<HH', hed_file.read(0x04))
        entry_length = 8 if (first_entry_high & 0x0FFF)==0 else 4
        entries_num = hed_path.stat().st_size // entry_length
        # if mrg with hed file, it will not contain its magic and entry-num header
        file_data_start_offset = 0
        hed_file.seek(0)
        entry_data_file = hed_file
    else:
        mrg_header = mrg_file.read(6)  # magic
        if mrg_header != b'mrgd00':
            print(f'Unknown header: {mrg_header}. This file might not mrgd00 format!')
            sys.exit(1)
        print('header: {0}'.format(mrg_header.decode('ASCII')))
        entries_num, = struct.unpack('<H', mrg_file.read(2))  # files info count in mrg
        entry_length = 8  # single mrg usually not contain voice
        file_data_start_offset = (6 + 2 + entries_num * entry_length)
        entry_data_file = mrg_file
    print(f"MRG {mrg_name} Archive count: {entries_num} entries")
    
    entries_desc = []
    indexed_fmt = '{0:04d}' if entries_num < 10000 else '{0:06d}'
    # read data in mrg file
    for i in range(entries_num):
        # read entry
        if not has_hed:
            entry_data_file.seek(8+i*entry_length, 0)
        data_block = entry_data_file.read(entry_length)
        first_word, = struct.unpack_from('<L', data_block)
        if first_word == 0xFFFFFFFF:
            continue
        if len(data_block) == 8:
            offset1, offset2, sector_size_upper_boundary, size_low = struct.unpack('<HHHH', data_block)
            entry_info = ArchiveInfo(offset1, offset2, sector_size_upper_boundary,
                                    size_low, file_data_start_offset, has_hed)
        elif len(data_block) == 4:
            offset_low, offset_size_high = struct.unpack('<HH', data_block)
            entry_info = VoiceInfo(offset_low, offset_size_high)
        else:
            raise ValueError(
                'Hed Entry constructor expects either a 4-byte or 8-byte binary block, source file may be incomplete')
        entries_desc.append(entry_info)  # for debug

        # seek data
        mrg_file.seek(entry_info.real_offset, 0)
        file_data = mrg_file.read(entry_info.real_size)

        # debug padding part
        # can also check and verify output file true size in here
        if has_hed:
            sec_data_size = entry_info.real_size if mrg_name.startswith('voice') else entry_info.size_sectors*0x800
            pad_num = sec_data_size - entry_info.real_size
            page_pad_num = pad_num%0x10
            sec_pad_num = pad_num//0x10
            next_bts = mrg_file.read(page_pad_num)
            if next_bts!=b'\x00'*page_pad_num:
                pass # breakpoint
            next_bts = mrg_file.read(sec_pad_num*0x10)
            if next_bts!=(b'\x0c'+b'\x00'*0xF)*sec_pad_num:
                pass # breakpoint
        else:
            dbg_num = 8-entry_info.real_size%8
            next_bts = mrg_file.read(dbg_num)
            if next_bts!=b'\xFF'*dbg_num:
                pass # breakpoint

        # generate file name
        if mrg_name.lower()=='allscr' and i==0:
            # TODO: besides script, other game allscr may have unknown/specific files at the beginning
            if MODE=='fateSN':  # Fate Stay Night Realta Nua
                filename_list = ['allscr.nam', 'unknown_table.mrg', 'unknown1']
                filename_list += extract_filenames('allscr.nam', file_data, True)
            else:
                filename_list = ['unknown_table.mrg']
        if len(filename_list)>i:
            file_name = filename_list[i]
            file_name = filename_utils.add_suffix(file_name, file_data, output_path, indexed_fmt.format(i))
            filename_list[i] = file_name
        else:
            file_name = f'{mrg_name}_file' + indexed_fmt.format(i)
            file_name = filename_utils.add_suffix(file_name, file_data)
            filename_list.append(file_name)
        if '.nam' in file_name: print(f"Find \'{mrg_name}.nam\' file.")

        # save file
        print(f"save file: {file_name}", end='')
        with open(output_path.joinpath(file_name), 'wb') as f:
            f.write(file_data)
        print(' succeed.')

    # export filename.list
    with open(output_path.joinpath(f'filename_{mrg_name}.list'), 'w', encoding="utf-8") as f:
        f.write('\n'.join(filename_list))

    mrg_file.close()
    print(f'Output Directory: {output_path}')


def repack(args):
    # repack files path
    files_path = Path(args.source_path)
    has_hed = not args.is_combine
    assert files_path.exists(), f'{files_path} does not found. Please pass the path to the folder contains repack files.'

    # set output path
    mrg_output_path = Path(args.output) if args.output else files_path.parent.joinpath(f"{files_path.stem.replace('_unpack','')}.mrg")
    mrg_name = mrg_output_path.stem

    # read filename list
    file_list_path = files_path.joinpath(f'filename_{mrg_name}.list')
    assert file_list_path.exists(), f'{file_list_path.name} does not found in {files_path}. Please make sure the path to the folder contains filename list.'
    with open(file_list_path, 'r', encoding="utf-8") as f:
        filename_list = [line.rstrip('\n') for line in f.readlines()]
    print('Loaded Filelist')
    
    # pack files
    hed_buf = b''
    temp_buf = io.BytesIO()    
    for file_name in filename_list:
        assert files_path.joinpath(file_name).exists(), f"Cannot find {file_name} in {files_path}."
        with open(files_path.joinpath(file_name), 'rb') as f:
            pack_data = f.read()
        data_offset, data_size = temp_buf.tell(), len(pack_data)
        # add padding
        pad_len, pad_data = add_entry_padding(args.is_combine, len(pack_data))
        if has_hed:
            if mrg_name.startswith('voice'):
                offset_low, offset_size_high = calculate_entry_desc(data_offset, data_size+pad_len,
                                                                    False, True)
                entry_buf = struct.pack('<HH', offset_low, offset_size_high)
            else:
                offset_low, offset_high, size_sectors, size_low = calculate_entry_desc(
                                                                    data_offset, data_size, False)
                entry_buf = struct.pack('<HHHH', offset_low, offset_high, size_sectors, size_low)
            pack_data += pad_data
        else:
            sector_offset, byte_offset, size_sectors, size_low = calculate_entry_desc(
                                                                    data_offset, data_size, True)
            entry_buf = struct.pack('<HHHH', sector_offset, byte_offset, size_sectors, size_low)
            pack_data += pad_data

        temp_buf.write(pack_data)
        hed_buf += entry_buf
        print(f"find and pack file: {file_name}")
    
    pack_buf = temp_buf.getvalue()
    if has_hed:
        # save hed file
        hed_buf += b'\xFF' * 0x10
        hed_output_path = mrg_output_path.with_name(f'new_{mrg_output_path.stem}.hed')
        with hed_output_path.open('wb') as f:
            f.write(hed_buf)
        print(f'save as {hed_output_path.absolute()}')
    else:
        # add magic and entries num for single mrg
        pack_buf = b'\x6D\x72\x67\x64\x30\x30' + struct.pack('<H', len(filename_list)) + hed_buf + pack_buf
    
    # save mrg file
    mrg_output_path = mrg_output_path.with_name(f'new_{mrg_output_path.name}')
    with mrg_output_path.open('wb') as f:
        f.write(pack_buf)
    print(f'save as {mrg_output_path.absolute()}')


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    subparsers = parser.add_subparsers(title='subcommands', dest='subcommand')

    # unpack
    parser_unpack = subparsers.add_parser('unpack', help='unpack mrg and create a filelist')
    parser_unpack.add_argument('input', metavar='input.mrg', help='Input .mrg file')

    # repack
    parser_repack = subparsers.add_parser('repack', help='generate a new .mrg base an existing MRG filelist')
    parser_repack.add_argument('-s', '--source_files',
                               required=True, dest='source_path',
                               help='Files path to repack, that also contain filename_xxx.list [REQUIRED]')
    parser_repack.add_argument('-c', '--combine',
                               dest='is_combine', type=int,
                               help='Decide whether to generate .hed file. Default 0(False)')
    parser_repack.add_argument('output', metavar='output.mrg',
                               help='Output .mrg file. Same basename is used for .hed/.nam when needed')

    # help
    parser.add_argument('-h', '--help',
                        action=CustHelpAction, default=argparse.SUPPRESS,
                        help='show this help message and exit')

    return parser, parser.parse_args()


if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    parser, args = parse_args()
    if args.subcommand == "unpack":
        unpack(args)
    elif args.subcommand == "repack":
        repack(args)
    else:
        parser.print_usage()
        sys.exit(20)
    sys.exit(0)
