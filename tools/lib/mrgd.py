#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# Author: ddny, root-none
'''mrgd00 lib'''

DEFAULT_SECTOR_SIZE = 0x800

"""Describes one file in the mrg archive
Entry info struct{
    Without .hed: (Same as MZP)
    uint16 sector_offset; (usually one sector 0x800 bytes)
    uint16 byte_offset;  (within sector)
    uint16 size_sectors;  (sector count upper boundary)
    uint16 size_low;

    With .hed:
    uint16 offset_low;
    uint16 offset_high;
    uint16 size_sectors;  (upper boundary)
    uint16 size_low;
}"""
class ArchiveInfo:
    def __init__(self, offset1, offset2,
                 size_sector_upper_boundary, size,
                 data_start_offset, with_hed):
        # set file data real offset
        if with_hed:
            self.offset_low = offset1
            self.offset_high = offset2
            self.real_offset = DEFAULT_SECTOR_SIZE * (((self.offset_high & 0xF000) << 4) | self.offset_low)
        else:
            self.sector_offset = offset1
            self.byte_offset = offset2
            self.real_offset = self.sector_offset * DEFAULT_SECTOR_SIZE + self.byte_offset
        self.real_offset += data_start_offset

        # set file data real size
        self.size_sectors = size_sector_upper_boundary
        self.size_low = size
        if not with_hed and\
            self.size_low<((self.size_sectors-1)*DEFAULT_SECTOR_SIZE)\
                and (self.size_low+self.byte_offset)>((self.size_sectors-1)*DEFAULT_SECTOR_SIZE):
            self.size_sectors -= 1
        if with_hed and self.size_low == 0:
            self.real_size = self.size_sectors * DEFAULT_SECTOR_SIZE
        else:
            self.real_size = ((DEFAULT_SECTOR_SIZE * (self.size_sectors - 1)) & 0xFFFF0000) | self.size_low


"""Voice Entry info struct{
    uint16 offset_low;
    uint16 offset_high and size;
}"""
class VoiceInfo:
    def __init__(self, offset_low, offset_size_high):
        self.offset_low = offset_low
        self.offset_size_high = offset_size_high
        self.real_offset = DEFAULT_SECTOR_SIZE * (((offset_size_high & 0xF000) << 4) | offset_low)
        self.real_size = DEFAULT_SECTOR_SIZE * (offset_size_high & 0x0FFF)
        # self.real_size = DEFAULT_SECTOR_SIZE * (((offset_size_high & 0x0F00)<<8)|(offset_size_high & 0x00FF))


# Author: Lisen, root-none
def calculate_entry_desc(current_offset, data_size, is_combine, is_voice=None):
    sector_size = DEFAULT_SECTOR_SIZE
    if is_combine:
        sector_offset = current_offset // sector_size
        byte_offset = current_offset % sector_size
        size_sectors = (data_size + sector_size - 1) // sector_size
        if byte_offset + data_size > sector_size * size_sectors:
            size_sectors += 1
        return sector_offset, byte_offset, size_sectors, data_size&0xFFFF
    else:
        offset_aligned = current_offset // sector_size
        offset_low = offset_aligned & 0xFFFF
        offset_high = (offset_aligned & 0xF0000) >> 4
        if is_voice:
            size_sectors = data_size // sector_size
            assert data_size%sector_size == 0
            offset_size_high = offset_high | (size_sectors & 0x0FFF)
            return offset_low, offset_size_high
        size_low = data_size & 0xFFFF
        if (size_low == 0) or (data_size % sector_size == 0):
            size_sectors = data_size // sector_size
        else:
            size_sectors = data_size // sector_size + 1
        return offset_low, offset_high, size_sectors, size_low


# Author: Hintay, root-none, base hedutil.write_entry_with_padding
def add_entry_padding(is_combine, data_size):
    if is_combine:
        pad_len = 8 - data_size % 8
        pad_data = b'\xFF'*pad_len
    else:
        pad_len = (DEFAULT_SECTOR_SIZE - data_size % DEFAULT_SECTOR_SIZE) if data_size % DEFAULT_SECTOR_SIZE else 0
        pad_data = b'\x00'*(pad_len%0x10) + (b'\x0c'+b'\x00'*0xF)*(pad_len//0x10)
    return pad_len, pad_data
