Damastes a.k.a. Procrustes
**************************

Ever got frustrated with an audiobook like this one?

::

    Robinson Crusoe $ ls
    'Disc 1'   'Disc 14'  'Disc 3'  'Disc 8'
    'Disc 10'  'Disc 15'  'Disc 4'  'Disc 9'
    'Disc 11'  'Disc 16'  'Disc 5'
    'Disc 12'  'Disc 17'  'Disc 6'
    'Disc 13'  'Disc 2'   'Disc 7'

::

    Robinson Crusoe $ tree
    ...
    ├── Disc 17
    │   ├── 01 Track 1.mp3
    │   ├── 02 Track 2.mp3
    ...
    │   ├── 13 Track 13.mp3
    ├── Disc 2
    │   ├── 01 Track 1.mp3
    │   ├── 02 Track 2.mp3
    │   ├── 03 Track 3.mp3
    ...
    │   ├── 15 Track 15.mp3
    │   └── desktop.ini
    ├── Disc 3
    │   ├── 01 Track 1.mp3
    │   ├── 02 Track 2.mp3
    ...

Try **Damastes**, this way:

::

    Robinson Crusoe $ damastes -via 'Daniel Defoe' -g 'Robinson Crusoe' . ~/MyAudioLibrary

- ``MyAudioLibrary`` must exist

or just like this:

::

    Robinson Crusoe $ damastes -a 'Daniel Defoe' -u 'Robinson Crusoe' . ~/MyAudioLibrary

Notice the tags set by **Damastes**.

Description
===========

**Damastes** is a CLI utility for basic processing and copying
of audio albums, mostly slovenly built audiobooks, possibly to cheap mobile
devices. Common poor design problems: track number tags
missing or incorrect, directory and/or file names enumerated
without leading zeroes, etc.

Meanwhile, one cannot listen to an audiobook with the tracks in the wrong
order. **Damastes** tries hard to sort the tracks properly.
To check the track order visually use ``-v``, and avoid ``-u``.

**Damastes** renames directories and audio files, replacing tags,
if necessary, while copying the album to destination. Source files
and directories are not modified in any way. Files are copied sequentially,
by default file number one first, optionally in reverse order, as some
mobile devices are copy-order sensitive.

General syntax
==============

::

    $ damastes [<options>] <source directory> <destination directory>

Options
=======

``-h, --help``                       *short description and options*

``-V, --version``                    *package version*

``-v, --verbose``                    *unless verbose, just progress bar is shown*

``-d, --drop-tracknumber``           *do not set track numbers*

``-s, --strip-decorations``          *strip file and directory name decorations*

``-f, --file-title``                 *use file name for title tag*

``-F, --file-title-num``             *use numbered file name for title tag*

``-x, --sort-lex``                   *sort files lexicographically*

``-t, --tree-dst``                   *retain the tree structure of the source album at destination*

``-p, --drop-dst``                   *do not create destination directory*

``-r, --reverse``                    *copy files in reverse order (number one file is the last to be copied)*

``-w, --overwrite``                  *silently remove existing destination directory (not recommended)*

``-y, --dry-run``                    *without actually modifying anything (trumps* ``-w``, *too)*

``-c, --count``                      *just count the files*

``-i, --prepend-subdir-name``        *prepend current subdirectory name to a file name*

``-e, --file-type FILE_TYPE``        *accept only audio files of the specified type (e.g.* ``-e mp3``*)*

``-u, --unified-name UNIFIED_NAME``  *destination root directory name and file names are based on UNIFIED_NAME, serial number prepended, file extensions retained*

``-b, --album-num ALBUM_NUM``        *0..99; prepend ALBUM_NUM to the destination root directory name*

``-a, --artist-tag ARTIST_TAG``      *artist tag name*

``-g, --album-tag ALBUM_TAG``        *album tag name*

Examples
========

::

    Source Album $ damastes -c . .

- All the files in *Source Album* get checked. Destination directory is required (and ignored).

::

    Source Album $ damastes -y . .

- Dry run: everything is done according to any options; no new files or directories created, destination is left undisturbed.

::

    Source Album $ damastes -a "Peter Crowcroft" -g "Mice All Over" . /run/media/user/F8950/Audiobooks/

- Destination directory */run/media/user/F8950/Audiobooks/Source Album/* is created;

- Track numbers are set according to the natural sort order (file names *..., 5, 6, 7, 8, 9, 10...*; regardless of the absence of the leading zeroes);

- *Artist* is set to *Peter Crowcroft*;

- *Album* is set to *Mice All Over*;

- *Title* is set to *1 P.C. - Mice All Over* for the first file, all titles enumerated;

::

    Source Album $ damastes -dst . /run/media/user/F8950/Audiobooks/

- *Source Album* directory is copied to */run/media/user/F8950/Audiobooks/* in its entirety, without modification; sequential copy order, natural or lexicographical, is guaranteed.

Damastes library
================

**Damastes** package exposes an API of sorts.
It is available system-, project-, or user-wide as soon as the ``damastes`` package is installed.

One can play with it:

::

    >>> import damastes as d

    >>> d.list_safe_imports()
    ['has_ext_of', 'human_fine', 'human_rough', 'list_safe_imports', 'make_initials', 'str_strip_numbers', 'strcmp_c', 'strcmp_naturally']

    >>> help(d.list_safe_imports)

    >>> help(d.make_initials)

    >>> d.make_initials('William J. "Wild Bill" Donovan, Joseph Gordon-Levitt')
    'W.J.D.,J.G-L.'
    >>>

The ``run()`` function is not on the list, because it is by no means safe and incredibly rich on side effects.
One can still use it, with care.

::

    >>> import os
    >>> os.getcwd()
    '/home/user/dir-src'
    >>> from damastes import run
    >>> run(argv=['-va', 'Vladimir Nabokov', '-u', 'Ada', '.', '/home/user/dir-dst'], version='42')
       1/5 ✔ /home/user/dir-dst/Vladimir Nabokov - Ada/1-Ada - Vladimir Nabokov.mp3  ✔ +20277
       2/5 ✔ /home/user/dir-dst/Vladimir Nabokov - Ada/2-Ada - Vladimir Nabokov.mp3  ✔ +20257
       3/5 ✔ /home/user/dir-dst/Vladimir Nabokov - Ada/3-Ada - Vladimir Nabokov.mp3  ✔ +20081
       4/5 ✔ /home/user/dir-dst/Vladimir Nabokov - Ada/4-Ada - Vladimir Nabokov.mp3  ✔ +20493
       5/5 ✔ /home/user/dir-dst/Vladimir Nabokov - Ada/5-Ada - Vladimir Nabokov.mp3  ✔ +20383
     🟢 Done (5, 91.6MB; 3.8s).
    0
    >>>

The tailing number like ``+20277`` means that the file grew fatter by 20277 bytes because of the set tags.
