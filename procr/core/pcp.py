#!/usr/bin/env python

from mutagen.easyid3 import EasyID3
import os
import re
import shutil
import argparse
import itertools as it
import functools as ft

utility_description = '''
pcp \"Procrustes\" SmArT is a CLI utility for copying subtrees containing audio (mp3)
files in sequence (preorder of the source subtree, alphabetically sorted by default).
The end result is a \"flattened\" copy of the source subtree. \"Flattened\" means
that only a namesake of the root source directory is created, where all the files get
copied to, names prefixed with a serial number. Mp3 tags 'Track' and 'Tracks Total'
get set, tags 'Artist' and 'Album' can be replaced optionally.
The writing process is strictly sequential: either starting with the number one file,
or in the reversed order. This can be important for some mobile devices.
'''


def flatten(lst):
    """
    Returns a flattened list; strings left as is
    """
    flat = []
    for x in lst:
        if hasattr(x, '__iter__') and not isinstance(x, str):
            flat.extend(flatten(x))
        else:
            flat.append(x)
    return flat


def part(iterable, n, fillvalue=None):
    """
    Collects data into fixed-length chunks or blocks (partition in Clojure)
    """
    args = [iter(iterable)] * n
    return it.zip_longest(*args, fillvalue=fillvalue)


def counter(x):
    """
    Provides a function returning next
    consecutive integer, starting from x
    """
    x -= 1

    def _cnt():
        nonlocal x
        x += 1
        return x
    return _cnt


def sans_ext(s):
    """
    Discards file extension
    """
    root, ext = os.path.splitext(s)
    return root


def str_strip_numbers(s):
    """
    Returns a vector of integer numbers
    embedded in a string argument
    """
    return [int(x) for x in re.compile('\d+').findall(s)]


def cmpv_int(vx, vy):
    """
    Compares vectors of integers using 'string semantics'
    """
    nonzero_tail = list(it.dropwhile(lambda x: x == 0, [x[0] - x[1] for x in zip(vx, vy)]))
    return len(vx) - len(vy) if nonzero_tail == [] else -1 if nonzero_tail[0] < 0 else 1


def cmpstr_c(x, y):
    return 0 if x == y else -1 if x < y else 1


def cmpstr_naturally(str_x, str_y):
    """
    If both strings contain digits, returns numerical comparison based on the numeric
    values embedded in the strings, otherwise returns the standard string comparison.
    The idea of the natural sort as opposed to the standard lexicographic sort is one of coping
    with the possible absence of the leading zeros in 'numbers' of files or directories
    """
    num_x = str_strip_numbers(str_x)
    num_y = str_strip_numbers(str_y)
    return cmpv_int(num_x, num_y) if num_x != [] and num_y != [] else cmpstr_c(str_x, str_y)


def compare_path(xp, yp):
    """
    Compares two paths, ignoring extensions
    """
    return cmpstr_naturally(sans_ext(xp), sans_ext(yp))


def compare_file(xf, yf):
    """
    Compares two paths, filenames only, ignoring extensions
    """
    return cmpstr_naturally(sans_ext(os.path.basename(xf)), sans_ext(os.path.basename(yf)))


def isaudiofile(x):
    """
    NB Not quite correct detection by extension
    """
    root, ext = os.path.splitext(x)
    return ext.upper() == ".MP3"


def list_dir_groom(abs_path):
    """
    Returns a tuple of: (0) naturally sorted list of
    offspring directory paths (1) naturally sorted list
    of offspring file paths.
    """
    lst = [os.path.join(abs_path, x) for x in os.listdir(abs_path)]
    dirs = sorted([x for x in lst if os.path.isdir(x)], key=ft.cmp_to_key(compare_path))
    files = sorted([x for x in lst if isaudiofile(x)], key=ft.cmp_to_key(compare_file))
    return (dirs, files)


def traverse_dir(src_dir, dst_root, dst_step, ffc):
    """
    Recursively traverses the source directory and returns the _recursive_ list of (src, dst) pairs;
    the destination directory and file names get decorated according to options
    """
    global args
    dirs, files = list_dir_groom(src_dir)

    def decorate_dir_name(i, name):
        return str(i + 1).zfill(3) + "-" + name

    def decorate_file_name(i, name):
        return str(i + 1).zfill(4) + "-" + (name if args.unified_name is None
                                                else args.unified_name + ".mp3")

    def dir_tree_handler(i, abs_path):
        step = os.path.join(dst_step, decorate_dir_name(i, os.path.basename(abs_path)))
        os.mkdir(os.path.join(dst_root, step))
        return traverse_dir(abs_path, dst_root, step, ffc)

    def dir_flat_handler(i, abs_path):
        return traverse_dir(abs_path, dst_root, "", ffc)

    def file_tree_handler(i, abs_path):
        dst_path = os.path.join(dst_root,
                            os.path.join(dst_step, decorate_file_name(i, os.path.basename(abs_path))))
        ffc()
        return (abs_path, dst_path)

    def file_flat_handler(i, abs_path):
        dst_path = os.path.join(dst_root, decorate_file_name(ffc(), os.path.basename(abs_path)))
        return (abs_path, dst_path)

    dh = dir_tree_handler if args.tree_dst else dir_flat_handler
    fh = file_tree_handler if args.tree_dst else file_flat_handler

    return [dh(i, x) for i, x in enumerate(dirs)] + [fh(i, x) for i, x in enumerate(files)]


def build_album():
    """
    Sets up boilerplate required by the options and returns the ammo belt
    (flat list of (src, dst) pairs)
    """
    global args
    src_name = os.path.basename(args.src_dir)
    prefix = "" if args.album_num is None else (str(args.album_num).zfill(2) + "-")
    base_dst = prefix + (src_name if args.unified_name is None else args.unified_name)
    executive_dst = os.path.join(args.dst_dir, "" if args.drop_dst else base_dst)
    file_counter = counter(0)

    if not args.drop_dst:
        os.mkdir(executive_dst)

    groom = lambda lst: list(part(flatten(lst), 2))    # Returns the flat ammo belt

    return (file_counter, groom(traverse_dir(args.src_dir, executive_dst, "", file_counter)))


def copy_album():
    """
    Runs through the ammo belt and does copying, in the reverse order if necessary
    """
    global args
    file_counter, ready_belt = build_album()
    fcount = file_counter()
    belt = reversed(ready_belt) if args.reverse else ready_belt

    def _set_tags(path, track):
        audio = EasyID3(path)
        audio["tracknumber"] = str(track + 1) + "/" + str(fcount)
        if args.artist_tag is not None:
            audio["artist"] = args.artist_tag
        if args.album_tag is not None:
            audio["album"] = args.album_tag
        audio.save()

    def _cp(i, entry):
        src, dst = entry
        shutil.copy(src, dst)
        _set_tags(dst, i)
        print("{:>4}/{:<4} {}".format(i + 1, fcount, dst))
        return entry

    copy = (lambda i, x: _cp(fcount - i - 1, x)) if args.reverse else lambda i, x: _cp(i, x)

    return [copy(i, x) for i, x in enumerate(belt)]


def retrieve_args():
    parser = argparse.ArgumentParser(description=utility_description)
    parser.add_argument("-t", "--tree-dst", help="copy as tree: keep source tree structure at destination", action="store_true")
    parser.add_argument("-p", "--drop-dst", help="do not create destination directory", action="store_true")
    parser.add_argument("-r", "--reverse", help="write files in reverse order (time sequence)", action="store_true")
    parser.add_argument("-u", "--unified-name", help="root substring for destination directory and file names")
    parser.add_argument("-b", "--album-num", help="album (book) start number, 0...99; omission means increment each call")
    parser.add_argument("-a", "--artist-tag", help="artist tag name")
    parser.add_argument("-g", "--album-tag", help="album tag name")
    parser.add_argument('src_dir', help="source directory, to be copied itself as root directory")
    parser.add_argument('dst_dir', help="destination directory")
    rg = parser.parse_args()
    rg.src_dir = os.path.abspath(rg.src_dir)    # Takes care of the trailing slash, too
    rg.dst_dir = os.path.abspath(rg.dst_dir)
    return rg


if __name__ == '__main__':
    args = retrieve_args()
    res = copy_album()
