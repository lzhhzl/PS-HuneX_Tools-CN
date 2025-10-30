 *.mrg/.hed/.nam Extraction
=================================

 Used Tools
------------
- `mrg_tool.py` [in-house dev / Python 3 / New-Develop]
- `hedutil.py` [in-house dev / Python 3 / Prototype]


 About
-----------

.hed/.nam/.mrg triples are commonly found at top-level of disc filesystem for PS2 titles, or in the USRDIR folder otherwise.

These containers typically contain the following file types:

- *.MRG, *.MZP ('mrgd00')
> generic container, group of files or texts or pictures

- *.MZX ('MZX0')
> Compressed data stream.

- *.ahx, *.at3, *.at9
> CRI Middleware MPEG-2 audio file or ATRAC3-in-RIFF/ATRAC9-in-RIFF audio file

- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

 Command
-----------
	python mrg_tool.py unpack allpac.mrg

or

	python hedutil.py unpack --filelist allpac.list allpac.hed


 Source(s)
-----------
***When unpacking***:

1. allpac.hed
2. allpac.nam (optional)
3. allpac.mrg

or

1. allscr.mrg

***When repacking***:

1. filename_allpac.list + files referenced inside (mrg_tool)

or

1. allpac.list + files referenced inside (hedutil)


 Product(s)
-----------
***When unpacking***:

* items in subfolder (Example: ``allpac_unpack`` / ``allpac-unpacked``)
* Ordered file list (Example: ``filename_allpac.list`` / ``allpac.list``)

***When repacking***:

* *mrg_tool* —— HED/MRG double (``new_allpac.hed`` and ``new_allpac.mrg``, or single ``new_allscr.mrg`` etc.) 
* _hedutil_ —— HED/NAM/MRG treble (``newpac.hed``, etc.) 



 Expected Output
-----------

	C:\work\_TL_\ayakashibito_py\lab\01A-EXTR-hed>python hedutil.py
	usage: hedutil.py [-h] {unpack,replace,repack} ...


	C:\work\_TL_\ayakashibito_py\lab\01A-EXTR-hed>python hedutil.py unpack -h
	usage: hedutil.py unpack [-h] [-f FILELIST] input.hed
	
	positional arguments:
	  input.hed             Input .hed file
	
	optional arguments:
	  -h, --help            show this help message and exit
	  -f FILELIST, --filelist FILELIST
	                        Output filelist path (default: none -- only unpack
	                        files)


	C:\work\_TL_\ayakashibito_py\lab\01A-EXTR-hed>python hedutil.py unpack --filelist allpac.list allpac.hed
	----------------------------------------------------------------------------------------
	| Archive count: 6184 entries
	----------------------------------------------------------------------------------------
	|- KCUR00.MZP - 344 b
	|- KCUR01.MZP - 344 b
	|- ACURSOR01.MZP - 1416 b	
	(...)
	========================================================================================
	Filelist: allpac.list
	Output Directory: allpac-unpacked


	