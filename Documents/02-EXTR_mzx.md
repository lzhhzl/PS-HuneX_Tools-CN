 Script Localization - *.MZX Script Extraction
===============================================

 Used Tools
------------
- `mzx_tool.py` [in-house dev / Python 3 / New-Develop]
- `mzx/decomp_mzx0.py` [in-house dev / Python 3]
- `prep_tpl.py` [in-house dev / Python 3]

 About
-----------

allpac.mrg, extracted using `hedutil`, contains *.MZX files, which are compressed files with an 'MZX0' sig.

An .MZX file is not necessarily a game script, it is a compressed stream similar to gzip.
On the other hand, all *.MZX files in allpac.mrg are likely to be game scripts. And the \*.MZX files in voice\*.mrg with b"LV\x03\x00\x00\x09\x00" head are likely to be ATRAC stream.

`prep_tpl` decompresses and preprocesses scripts into a format better suited for editing.


Extraction
-----------

For `_prep_tpl.py`:

1. This assumes allpac.hed/mrg was extracted into `base_directory/allpac-unpacked/`
2. Create a folder as such: `"base_directory/1.prep_mzx_to_tpl"` and place a copy of script extraction tools into it.

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

 Command
-----------

For `_prep_tpl.py`:

	python _prep_tpl.py ../allpac-unpacked
-or-

	python _prep_tpl.py ../allpac-unpacked/<scriptname.MZX>

For `mzx_tool.py`:

	python mzx_tool.py ./dir_contain_mzx_files
-or-

	python mzx_tool.py ./dir_contain_mzx_files/<name.MZX\mzx>

 Source(s)
-----------
1. ..\allpac-unpacked\*.MZX [from allpac.mrg]

 Product(s)
-----------

* Folder:`10rawscript`

* `10rawscript`\~sourcefileMZX~.ini  => result of input stream decompression plus XOR'ed. Encoding = CP932 usually

* Folder:`20decodedscript`

* `20decodedscript`\~sourcefileMZX~.tpl.txt  => localizable text [where applicable], encoding = UTF8

 Expected Output
-----------

	C:\work\_TL_\psp_aya\1.prep_mzx_to_tpl>python prep_tpl.py ../allpac-unpacked
	[..\allpac-unpacked\CO0203.MZX] ERR
	193 scripts, 192 SUCCESS, 1 FAILURE
	C:\work\_TL_\psp_aya\1.prep_mzx_to_tpl>python prep_tpl.py ../allpac-unpacked/TO11B.MZX
	1 scripts, 1 SUCCESS, 0 FAILURE
	C:\work\_TL_\psp_aya\1.prep_mzx_to_tpl>
