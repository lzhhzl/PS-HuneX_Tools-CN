#!/usr/bin/env python
# -*- coding:utf-8 -*-
'''Some import/export file name utils'''

# Author: ddn_y, root-none
def add_suffix(name, data, output_path=None, collision_suffix=None):
    # automatically add the file suffix (not necessarily correct)
    if '.' not in name:
        # MRG,MZP(mrgd00)
        if data[:6] == b'\x6D\x72\x67\x64\x30\x30':
            # TODO: In test, distinguish mrg or mzp, not necessarily correct
            entries_num = int.from_bytes(data[6:8], 'little')
            if data.count(b'\x6D\x72\x67\x64\x30\x30')==1 and\
                data.count(b'\x4D\x5A\x58\x30')>=1 and\
                    data.count(b'\x4D\x5A\x58\x30')==(entries_num-1):
                name += '.mzp'
            else:
                name += '.mrg'
        # MZX(MZX0)
        elif data[:4] == b'\x4D\x5A\x58\x30' or\
                data[:11] == b"\x4C\x56\x03\x00\x00\x09\x00\x4D\x5A\x58\x30":
            name += '.mzx'
        # RIFF....WAVEfmt
        elif data[:4] == b"\x52\x49\x46\x46" and\
                data[0x8:0x10] == b"\x57\x41\x56\x45\x66\x6D\x74\x20":
            # TODO: In test, use GUID part to identify the atrac type, maybe not accurate
            if data[0x2c:0x3C] == b"\xD2\x42\xE1\x47\xBA\x36\x8D\x4D\x88\xFC\x61\x65\x4F\x8C\x83\x6C":
                name += '.at9'
            elif data[0x2c:0x3C] == b"\xBF\xAA\x23\xE9\x58\xCB\x71\x44\xA1\x19\xFF\xFA\x01\xE4\xCE\x62":
                name += '.at3'
            else:
                name += '.atrac_bin'
        else:
            name += '.bin'
    assert ' ' not in name
    # if exist collision name, add unique number suffix to avoid
    if output_path:
        save_path = output_path.joinpath(name)
        name_part, ext = name[:name.rfind('.')], name[name.rfind('.')+1:]
        if save_path.exists():
            name = f"{name_part}-{collision_suffix}.{ext}"
            # save_path = output_path.joinpath(name)
    return name


# Author: Hintay, Quibi
def fix_file_name(index, mode):
    # Some scrpit file name might delete prefix between diff game
    # Those patten can usually be finded in allpac-SCR.NAM
    # You might need to fix some names in case overwriting same file name
    if mode == 'fateSN':
        index -= 3
        if 101 <= index <= 202:
            return 'セイバールート十'
        elif index == 240:
            return 'ラストエピソ'
        elif 338 <= index <= 483:
            return '桜ルート十'
        elif 604 <= index <= 705:
            return '凛ルート十'
    return ""


def file_or_folder(path_arg, glob_fmt):
    if path_arg.is_file():
        return [path_arg]
    elif path_arg.is_dir():
        return path_arg.glob(glob_fmt)
    else:
        assert path_arg.exists(), f"Invalid input path: {path_arg}."
