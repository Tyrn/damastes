Procrustes SmArT
================

Description
-----------
**Procrustes SmArT** is a CLI utility for basic processing and copying
of audio albums, mostly audiobooks of unknown provenance to cheap mobile
devices. Audiobooks in question can be poorly designed: track number tags
may be missing or incorrect, directory and/or files names enumerated
without leading zeroes, etc.

**Procrustes SmArT** renames directories and audio files, replacing tags,
if necessary, while copying the album to destination. Source files
and directories are not modified in any way.

General syntax
--------------

``$ pcp [<options>] <source directory> <destination directory>``

Options
-------

``-h, --help``
short description and options

``-t, --tree-dst``
copy as tree

Examples
--------

