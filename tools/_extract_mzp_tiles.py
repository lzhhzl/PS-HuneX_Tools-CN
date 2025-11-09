#!/usr/bin/env python
#
# MZP Tiles Extraction Library version 1.4
# comes with ABSOLUTELY NO WARRANTY.
#
# Copyright (C) 2016 Hintay <hintay@me.com>
# Portions Copyright (C) caoyang131
# And probably portions Copyright (C) Waku_Waku
# And portions Copyright (C) root-none
#
# The tiles from MZP files extraction library
# For more information, see Specifications/mzp_format.md
#
# Changelog (recent first):
# 2016-05-30 Hintay: Fixed 4bpp conversion and add 4bpp Alpha-channel to 8bpp for 4bpp MZPs.
# 2016-05-20 Hintay: Fixed 4bpp conversion.
# 2016-04-18 Hintay: Add 24/32bpp True-color support. (bmp_type = 0x08 or 0x0B)
#                    Add pixel crop feature support.
#                    Thanks to caoyang131 for 16bpp conversion.
# 2016-04-11 Hintay: Add 4bpp Alpha-channel to 8bpp conversion. (bmp_type = 0x11 or 0x91)
# 2016-04-10 caoyang131: Add RGBATim2 palette type support.
# 2016-04-09 Hintay: Encapsulated as a library.

import sys
import zlib
import logging
from pathlib import Path
from struct import unpack, pack
from subprocess import call
from mzx.decomp_mzx0 import mzx0_decompress
from lib.hep import hep_extract

logger = logging.getLogger('MZP')


# http://blog.flip-edesign.com/?p=23
class Byte(object):
    def __init__(self, number):
        self.number = number

    @property
    def high(self):
        return self.number >> 4

    @property
    def low(self):
        return self.number & 0x0F


###############################################
# PNG utils
def write_pngsig(f):
    f.write(b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A')


def write_pngchunk_withcrc(f, type, data):
    f.write(pack(">I", len(data)))
    f.write(type)
    f.write(data)
    f.write(pack(">I", zlib.crc32(type + data, 0) & 0xffffffff))


"""
IHDR Image header Struct:
    Width:              4 bytes
    Height:             4 bytes
    Bit depth:          1 byte
    Color type:         1 byte
    Compression method: 1 byte
    Filter method:      1 byte
    Interlace method:   1 byte

Color type = 1 (palette used), 2 (color used), and 4 (alpha channel used). Valid values are 0, 2, 3, 4, and 6. 

    Color    Allowed    Interpretation
    Type    Bit Depths
   
    0       1,2,4,8,16  Each pixel is a grayscale sample.
   
    2       8,16        Each pixel is an R,G,B triple.
   
    3       1,2,4,8     Each pixel is a palette index;
                       a PLTE chunk must appear.
   
    4       8,16        Each pixel is a grayscale sample,
                       followed by an alpha sample.
   
    6       8,16        Each pixel is an R,G,B triple,
                       followed by an alpha sample.
"""


def write_ihdr(f, width, height, depth, color):
    chunk = pack(">IIBB", width, height, depth, color) + b'\0\0\0'
    write_pngchunk_withcrc(f, b"IHDR", chunk)


def write_plte(f, palettebin):
    write_pngchunk_withcrc(f, b"PLTE", palettebin)


def write_trns(f, transparencydata):
    write_pngchunk_withcrc(f, b"tRNS", transparencydata)


def write_idat(f, pixels):
    write_pngchunk_withcrc(f, b"IDAT", zlib.compress(pixels))


def write_iend(f):
    write_pngchunk_withcrc(f, b"IEND", b"")


def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in range(0, len(l), n):
        yield l[i:i + n]


###############################################
# struct TGAHeader
# {
#   uint8   idLength,           // Length of optional identification sequence.
#           paletteType,        // Is a palette present? (1=yes)
#           imageType;          // Image data type (0=none, 1=indexed, 2=rgb,
#                               // 3=grey, +8=rle packed).
#   uint16  firstPaletteEntry,  // First palette index, if present.
#           numPaletteEntries;  // Number of palette entries, if present.
#   uint8   paletteBits;        // Number of bits per palette entry.
#   uint16  x,                  // Horiz. pixel coord. of lower left of image.
#           y,                  // Vert. pixel coord. of lower left of image.
#           width,              // Image width in pixels.
#           height;             // Image height in pixels.
#   uint8   depth,              // Image color depth (bits per pixel).
#           descriptor;         // Image attribute flags.
# };

def is_indexed_bitmap(bmp_info):
    return bmp_info == 0x01


class MzpFile:
    def __init__(self, file: Path, data, entries_descriptors,
                 plt_convert, extend):
        self.file = file
        self.data = data
        self.entries_descriptors = entries_descriptors
        self.palette_convert = plt_convert
        self.extend = extend

    def extract_tiles(self):
        self.paletteblob = b''
        self.palettepng = b''
        self.transpng = b''
        self.extract_desc()
        self.bytesperpx = self.bitmap_bpp // 8
        if self.bytesperpx == 0:  # <=4bb
            self.bytesperpx = 1
        self.debug_format()
        self.rows = [b''] * (self.height - self.tile_y_count * self.tile_crop)
        self.loop_data()

    def save_image(self, output_path):
        if self.palette_convert:
            self.output_tga(output_path)
        self.output_png(output_path)

    def extract_desc(self):
        self.data.seek(self.entries_descriptors[0].real_offset)
        self.width, self.height, self.tile_width, self.tile_height, self.tile_x_count, self.tile_y_count,\
            self.bmp_type, self.bmp_depth, self.tile_crop = unpack('<HHHHHHHBB', self.data.read(0x10))
        self.tile_size = self.tile_width * self.tile_height

        # set img real size
        self.img_width = self.width - self.tile_x_count * self.tile_crop * 2
        self.img_height = self.height - self.tile_y_count * self.tile_crop * 2
        if self.bmp_type not in [0x01, 0x03, 0x08, 0x0B, 0x0C]:
            logger.error("Unknown type 0x{:02X}".format(self.bmp_type))
            call(["cmd", "/c", "pause"])
            sys.exit(1)

        # 有索引
        if is_indexed_bitmap(self.bmp_type):
            if self.bmp_depth in [0x01, 0x11, 0x91]:
                self.bitmap_bpp = 8
                self.palette_count = 0x100  # 256 colors
            elif self.bmp_depth in [0x00, 0x10]:
                self.bitmap_bpp = 4
                self.palette_count = 0x10  # 16 colors
            else:
                logger.error("Unknown depth 0x{:02X}".format(self.bmp_depth))
                call(["cmd", "/c", "pause"])
                sys.exit(1)

            # extract palette
            if self.bmp_depth in [0x00, 0x10]:
                for i in range(self.palette_count):
                    r = self.data.read(1)
                    g = self.data.read(1)
                    b = self.data.read(1)

                    # a = self.data.read(1)
                    # Experimental
                    # 4bpp Alpha-channel to 8bpp
                    # Author: Hintay <hintay@me.com>
                    temp_a, = unpack('B', self.data.read(1))
                    # 4bpp及8bpp的字库图的原透明度范围在0~127
                    a = (temp_a << 1) + (temp_a >> 6) if (temp_a < 0x80) else 255
                    a = pack('B', a)

                    # build palette(rgb,alpha)
                    self.paletteblob += (b + g + r + a)
                    self.palettepng += (r + g + b)
                    self.transpng += a

            # :PalType:RGBATim2:
            # Author: caoyang131
            elif self.bmp_depth in [0x11, 0x91, 0x01]:
                pal_start = self.data.tell()
                for h in range(0, self.palette_count * 4 // 0x80, 1):
                    for i in range(2):
                        for j in range(2):
                            self.data.seek(h * 0x80 + (i + j * 2) * 0x20 + pal_start)
                            for k in range(8):
                                r = self.data.read(1)
                                g = self.data.read(1)
                                b = self.data.read(1)

                                # Experimental
                                # 4bpp Alpha-channel to 8bpp
                                # Author: Hintay <hintay@me.com>
                                temp_a, = unpack('B', self.data.read(1))
                                a = (temp_a << 1) + (temp_a >> 6) if (temp_a < 0x80) else 255
                                a = pack('B', a)

                                self.paletteblob += (b + g + r + a)
                                self.palettepng += (r + g + b)
                                self.transpng += a
            else:
                logger.error("Unsupported palette type 0x{:02X}".format(self.bmp_depth))
                call(["cmd", "/c", "pause"])
                sys.exit(1)

            # 4bpp补全索引至8bpp
            for i in range(self.palette_count, 0x100):
                self.paletteblob += b'\x00\x00\x00\xFF'
                self.palettepng += b'\x00\x00\x00'
                self.transpng += b'\xFF'
        elif self.bmp_type == 0x08:
            if self.bmp_depth == 0x14:
                self.bitmap_bpp = 24
            else:
                logger.error("Unknown depth 0x{:02X}".format(self.bmp_depth))
                call(["cmd", "/c", "pause"])
                sys.exit(1)
        elif self.bmp_type == 0x0B:
            if self.bmp_depth == 0x14:
                self.bitmap_bpp = 32
            else:
                logger.error("Unknown depth 0x{:02X}".format(self.bmp_depth))
                call(["cmd", "/c", "pause"])
                sys.exit(1)
        elif self.bmp_type == 0x0C:
            self.hep_info = {"transparency":[], "unknown":[]}
            if self.bmp_depth == 0x11:
                self.bitmap_bpp = 32
            else:
                logger.error("Unknown depth 0x{:02X}".format(self.bmp_depth))
                call(["cmd", "/c", "pause"])
                sys.exit(1)
        elif self.bmp_type == 0x03:  # 'PEH' 8bpp + palette
            logger.error("Unsupported type 0x{:02X} (PEH)".format(self.bmp_type))
            call(["cmd", "/c", "pause"])
            sys.exit(1)
        else:
            logger.error("Unknown bmp type 0x{:02X} & depth 0x{:02X} pair".format(self.bmp_type, self.bmp_depth))
            call(["cmd", "/c", "pause"])
            sys.exit(1)

        # Experimental, base https://github.com/loicfrance/mahoyo_tools/issues/7#issuecomment-2746356020
        # Tile transparency byte:
        # 00-fully transparent tile; 01-with transparency; 02-opaque;
        assert self.entries_descriptors[0].real_size-(self.data.tell()-self.entries_descriptors[0].real_offset)==self.tile_x_count*self.tile_y_count
        tiles_trans_data = self.data.read(self.tile_x_count * self.tile_y_count)
        for b in tiles_trans_data: assert b in [0x0, 0x1, 0x2], f'Unknown tile transparency byte:{b.hex()}'
        self.tile_trans = tiles_trans_data.hex(' ')

        del self.entries_descriptors[0]

    def debug_format(self):
        logger.debug(
            'MZP Format: Width = %s, Height = %s, Bitmap type = %s, Bitmap depth = %s, '
            'Bits per pixel = %s, Bytes Per pixel = %s' % (
                self.width, self.height, self.bmp_type, self.bmp_depth, self.bitmap_bpp, self.bytesperpx))
        logger.debug('Tile Format: Width = %s, Height = %s, X count = %s, Y count = %s, Tile crop = %s,\nTile transparency = %s' % (
            self.tile_width, self.tile_height, self.tile_x_count, self.tile_y_count, self.tile_crop, self.tile_trans))
        if self.tile_crop:
            logger.debug('MZP Cropped Size: Width = %s, Height = %s' % (self.img_width, self.img_height))
        print('',end='\n')

    def get_tile_info(self):
        tile_info = {
            'width': self.width, 'height': self.height,
            'bmp_type': self.bmp_type, 'bmp_depth': self.bmp_depth, 'bitmap_bpp': self.bitmap_bpp,
            'tile_width': self.tile_width, 'tile_height': self.tile_height,
            'tile_x_count': self.tile_x_count, 'tile_y_count': self.tile_y_count,
            'tile_crop': self.tile_crop, 'tile_trans': self.tile_trans,
        }
        if self.bmp_type==0x0C:
            assert len(self.hep_info["unknown"])==1
            tile_info["hep_trans"] = " ".join(self.hep_info["transparency"])
            tile_info["hep_others"] = "".join(self.hep_info["unknown"][0])
        if self.tile_x_count*self.tile_y_count > len(self.entries_descriptors) and self.extend:
            tile_info["note"] = f"{self.tile_x_count*self.tile_y_count} tiles more than {len(self.entries_descriptors)} tile entries"
        return tile_info

    def extract_tile(self, index):
        if index >= len(self.entries_descriptors) and not self.extend:
            # !Note: few mzp files have tile X*Y count > entries num, strangely
            raise IndexError(f"This mzp Tiles-num out of tile entries-num: {len(self.entries_descriptors)}.")
        entry = self.entries_descriptors[index if index < len(self.entries_descriptors) else (index-len(self.entries_descriptors))]
        self.data.seek(entry.real_offset)
        sig, size = unpack('<4sL', self.data.read(0x8))
        assert sig == b'MZX0', f"Unkonwn signature: {sig}, usually won't happen this error."
        status, dec_buf = mzx0_decompress(self.data, entry.real_size - 8, size)
        dec_buf = dec_buf.read()
        # 4bpp index bitmap for 0x01 bmp type
        if self.bitmap_bpp == 4:
            tile_data = b''
            for octet in dec_buf:
                the_byte = Byte(octet)
                tile_data += pack('BB', the_byte.low, the_byte.high)
            dec_buf = tile_data

        # RGB/RGBA true color for 0x08 and 0x0B bmp type
        elif self.bitmap_bpp in [24, 32] and self.bmp_type in [0x08, 0x0B]:
            # 16bpp
            tile_data = b''
            for index in range(self.tile_size):
                P = dec_buf[index * 2]  # first byte, low-byte
                Q = dec_buf[(index * 2) + 1]  # second byte, high-byte
                # rgb565, little-order every 2bytes
                b = (P & 0x1f) << 3
                g = (Q & 0x07) << 5 | (P & 0xe0) >> 3
                r = (Q & 0xf8)

                # Offset(rgb323) for rgb 16bpp to 24bpp
                offset_byte = dec_buf[self.tile_size * 2 + index]
                r_offset = offset_byte >> 5
                g_offset = (offset_byte & 0x1f) >> 3
                b_offset = offset_byte & 0x7

                # Alpha
                if self.bitmap_bpp == 32:
                    a = dec_buf[self.tile_size * 3 + index]
                    tile_data += pack('<BBBB', r + r_offset, g + g_offset, b + b_offset, a)
                else:
                    tile_data += pack('<BBB', r + r_offset, g + g_offset, b + b_offset)
            dec_buf = tile_data
        
        # :HEP Tile data for 0x0C bmp type
        # Author: loicfrance
        elif self.bmp_type == 0x0C:
            dec_buf, hep_info = hep_extract(dec_buf)
            assert self.tile_width == hep_info['width'] and self.tile_height == hep_info['height']
            self.hep_info["transparency"].append(str(hep_info['transparency']))
            if (hep_info['u1'],hep_info['u2']) not in self.hep_info["unknown"]:
                self.hep_info["unknown"].append((hep_info['u1'],hep_info['u2']))
        return dec_buf

    def loop_data(self):
        for y in range(self.tile_y_count):
            start_row = y * (self.tile_height - self.tile_crop * 2)  # 上下切边
            rowcount = min(self.img_height, start_row + (self.tile_height - self.tile_crop * 2)) - start_row  # 共几行
            self.loop_x(y, start_row, rowcount)

    def loop_x(self, y, start_row, rowcount):
        # Tile 块处理
        for x in range(self.tile_x_count):
            dec_buf = self.extract_tile(self.tile_x_count * y + x)

            assert len(dec_buf)%(self.tile_width*self.bytesperpx)==0  # debug
            for i, tile_row_px in enumerate(chunks(dec_buf, self.tile_width * self.bytesperpx)):
                if i < self.tile_crop:
                    continue
                if (i - self.tile_crop) >= rowcount:
                    break
                cur_row = start_row + i - self.tile_crop  # 实际图像行定位
                cur_px = len(self.rows[cur_row]) // self.bytesperpx
                assert len(self.rows[cur_row])%self.bytesperpx==0  # debug
                assert cur_px==(x * (self.tile_width - self.tile_crop * 2))  # debug
                px_count = (min(self.img_width-cur_px, self.tile_width-2*self.tile_crop) + 2*self.tile_crop) * self.bytesperpx
                try:
                    temp_row = tile_row_px[:px_count]
                    self.rows[cur_row] += temp_row[self.tile_crop * self.bytesperpx: len(
                        temp_row) - self.tile_crop * self.bytesperpx]
                except IndexError:
                    logger.error(f"Current row Index:{cur_row} Error")

    # 输出PNG
    def output_png(self, output_path):
        png_path = output_path.joinpath(self.file.with_suffix('.png').name)
        with png_path.open('wb') as png:
            write_pngsig(png)
            width = self.width - self.tile_x_count * self.tile_crop * 2
            height = self.height - self.tile_y_count * self.tile_crop * 2
            if is_indexed_bitmap(self.bmp_type):
                if self.palette_convert:
                    write_ihdr(png, width, height, 8, 6)  # 8bpp (RGBA)
                    for i in range(len(self.rows)):
                        row = self.rows[i]
                        new_row = b''.join([
                            self.palettepng[bi*3:(bi*3+3)]+self.transpng[bi:(bi+1)] for bi in row])
                        assert len(new_row)==len(self.rows[i])*4
                        self.rows[i] = new_row
                else:
                    write_ihdr(png, width, height, 8, 3)  # 8bpp (PLTE)
                    write_plte(png, self.palettepng)
                    write_trns(png, self.transpng)

            elif self.bitmap_bpp == 24:  # RGB True-color
                write_ihdr(png, width, height, 8, 2)  # 24bpp

            elif self.bitmap_bpp == 32:  # RGBA True-color
                write_ihdr(png, width, height, 8, 6)  # 32bpp

            # split into rows and add png filtering info (mandatory even with no filter)
            row_data = b''
            for row in self.rows:
                row_data += b'\x00' + row

            write_idat(png, row_data)
            write_iend(png)
    # call(["cmd", "/c", "start", pngoutpath])

    # 输出TGA
    def output_tga(self, output_path):
        tga_path = output_path.joinpath(self.file.with_suffix('.tga').name)
        with tga_path.open('wb') as tga:
            colormap_type = 1  # 使用调色板
            image_type = 1     # 索引颜色图像（带调色板）
            colormap_first_entry_index = 0
            colormap_length = 256  # 8bpp
            colormap_depth = 32  # 每个调色板条目 32 位（RGBA）
            bits_per_pixel = 8

            # Image Descriptor Byte:
            # Bit 5: 1 → top-left origin
            # Bits 3-0: 8 → 8-bit alpha
            image_descriptor = 0b00100000 | 0b00001000  # 32 + 8 = 40

            # TGA 文件头结构
            tga_header = pack(
                '<BBBHHBHHHHBB',
                0,  # id_length
                colormap_type,
                image_type,
                # Color Map Specification
                colormap_first_entry_index,
                colormap_length,
                colormap_depth,
                # Image Specification
                0,  # x_origin
                0,  # y_origin
                self.img_width,
                self.img_height,
                bits_per_pixel,
                image_descriptor
            )

            # 构建调色板（每个颜色条目是 BGRA，4 字节）
            colormap = self.paletteblob

            # 图像数据
            packed_image_data = b''
            for row in self.rows:
                packed_image_data += row
            
            tga.write(tga_header)
            tga.write(colormap)
            tga.write(packed_image_data)
