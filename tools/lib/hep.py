#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# HEP Data Extract
# Rewrite base mahoyo_tools hep.py(https://github.com/loicfrance/mahoyo_tools/blob/main/hep.py)
# Portions copyright (C) loicfrance
import struct

"""
HEP struct(20 bytes)
{
    char magic[4] HEP\0;
    uint32_t file size;  // little endian, from start of header to last byte of file
    uint32_t unknown1, uint32_t unknown2; // (e.g. 00 00 30 D9 05 00 00 00 / 00 00 30 1D 06 00 00 00), seems to depend on dimensions
    uint32_t unknown3; // seem like always 10 00 00 00
    uint32_t width;
    uint32_t height;
    uint32_t transparency;  // 0: fully transparent, 1: partially transparent, 2: fully opaque
    {width*height} bytes  index-data;
    n*4 bytes  palette(RGBA);
}
"""

HEP_MAGIC = b'HEP\0'
HEP_HEADER_SIZE = 0x20
HEP_PALETTE_SIZE = 0x400


def hep_extract(hep_data):
    magic, file_size, u1, u2, u3,\
        width, height, transparency = struct.unpack('<4sIIIIIII', hep_data[:HEP_HEADER_SIZE])
    pixels_size = width * height
    assert magic == HEP_MAGIC, f"Invalid magic of HEP data: {magic}"
    assert file_size == HEP_HEADER_SIZE + pixels_size + HEP_PALETTE_SIZE, \
        f"Wrong file size {file_size}. Expected {HEP_HEADER_SIZE + pixels_size + HEP_PALETTE_SIZE}"
    assert transparency in [0, 1, 2]
    assert struct.pack('<I',u3)==b'\x10\x00\x00\x00', f"New u3: {struct.pack('<I',u3)} appear, please report."
    hep_info = {
        "width": width,
        "height": height,
        "u1": struct.pack('<I',u1).hex(),
        "u2": struct.pack('<I',u2).hex(),
        "transparency": transparency,
    }

    pixels_index = hep_data[HEP_HEADER_SIZE: HEP_HEADER_SIZE+pixels_size]
    palette_buf = hep_data[HEP_HEADER_SIZE+pixels_size:]
    assert len(palette_buf) == HEP_PALETTE_SIZE
    palette = []
    for i in range(0, HEP_PALETTE_SIZE, 4):
        rgb = palette_buf[i:i+3]
        temp_a = palette_buf[i+3]
        a = (temp_a << 1) + (temp_a >> 6) if (temp_a < 0x80) else 255
        palette.append(rgb + struct.pack('B', a))
    tile_data = b""
    for index in pixels_index:
        tile_data += palette[index]
    
    return tile_data, hep_info
