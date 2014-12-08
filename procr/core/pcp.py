#!/usr/bin/env python

#import mutagen
import os
import re
import itertools as it


def hello(msg="Hello, World!"):
    print(msg)

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
    nonzero_tail = list(it.dropwhile(lambda x: x == 0, list(map(lambda x, y: x - y, vx, vy))))
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


if __name__ == '__main__':
    hello("Main!")
