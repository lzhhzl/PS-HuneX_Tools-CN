 The .hed/.nam/.mrg format
===========================
> Revision 1, maintainer: Waku_Waku, root-none

> Reverse-engineered by Waku_Waku

All fields are little-endian unless specified otherwise.


 Introduction
==============

This document refers to the top-level MRG/HED/NAM structure, an archive format mostly used in consumer titles in Playstation 2-era and early PSP lifetime, and was later continued to be used on psv and ps4.

They are commonly found at top-level of disc filesystem for PS2 titles, or in the USRDIR folder otherwise.

NOTE: encrypted allpac.cpk has not been reversed yet. I know chinese hackers managed to do it for Mashiro Iro Symphony PSP, though.


These containers typically contain the following file types:

- *.MRG, *.MZP ('mrgd00')
> generic container, group of files or texts or pictures(described in ``mzp_format.md``).
> For MRG, it's divided into single .mrg and split .hed/.mrg files.

- *.HED, *.NAM
> generic entry and files name Descriptor, but not all mrg file come with nam file, maybe because the engine doesn't need file names to seek files.

- *.MZX ('MZX0')
> Compressed data stream (described in ``mzx_compression.md``)

- *.ahx, *.at3, *.at9
> CRI Middleware MPEG-2 audio file or ATRAC3-in-RIFF/ATRAC9-in-RIFF audio file (generally easily decodable to .wav for people who want to create voice patches or whatever)


 I) .hed structure 
===================

> For the general purpose like 'allpac.hed':

    { n times (0x8 bytes): Generic Entry Descriptor }

> For the specific 'voice*.hed':

    { n times (0x4 bytes): Voice Entry Descriptor }


A series of sixteen 0xFF bytes marks EOF.



 I.1)  Generic Entry Descriptor (allpac)
-----------------------------------------

> For single .mrg file, entry desc-block start at 0x8 (Same as .mzp):

	2 bytes - offset, sector count (0x800 bytes)
	2 bytes - offset, within sector
	2 bytes - size upper boundary, sector count (0x800 bytes)
	2 bytes - size in data section (Raw)

Single .mrg file's Entry offset and Entry size, see the Real offset and the Real size described in ``mzp_format.md``.

> For split .mrg file, it has no magic and entries num in head-part.
> The entry desc-block store in .hed file with same basename.

	2 bytes - offset, low Word
	2 bytes - offset, high Word
	2 bytes - size upper bound, sector count (0x800 bytes)
	2 bytes - size, low Word

Entry offset = 0x800 * (((.ofsHigh & 0xF000) << 4) | .ofsLow)

If .sizeLow is zero:
Entry size = 0x800 * .sizeSect

Otherwise:
Entry size = (0x800 * (.sizeSect - 1) & 0xFFFF0000) | .sizeLow


I.2)  Voice Entry Descriptor (voice*)
--------------------------------------

	2 bytes - offset, low Word
	2 bytes - offset and size, high Word

Entry offset = 0x800 * (((.ofsSzHigh & 0xF000) << 4) | .ofsLow)

Entry size = 0x800 * (.ofsSzHigh & 0x0FFF)


