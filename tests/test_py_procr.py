import unittest
from py_procr import __version__
from py_procr.pcp import *


class TestHelpers(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_version(self):
        assert __version__ == "0.1.0"

    def test_zero_pad(self):
        self.assertEqual(str(3).zfill(5), "00003")
        self.assertEqual(str(15331).zfill(3), "15331")

    def test_has_ext_of(self):
        self.assertEqual(has_ext_of(Path("/alfa/bra.vo/charlie.ogg"), "OGG"), True)
        self.assertEqual(has_ext_of(Path("/alfa/bra.vo/charlie.ogg"), ".ogg"), True)
        self.assertEqual(has_ext_of(Path("/alfa/bra.vo/charlie.ogg"), "mp3"), False)

    def test_str_strip_numbers(self):
        self.assertEqual(str_strip_numbers("ab11cdd2k.144"), [11, 2, 144])
        self.assertEqual(str_strip_numbers("Ignacio Vazquez-Abrams"), [])

    def test_strcmp_c(self):
        self.assertEqual(strcmp_c("aardvark", "bobo"), -1)
        self.assertEqual(strcmp_c([], []), 0)
        self.assertEqual(strcmp_c([1], []), 1)
        self.assertEqual(strcmp_c([3], []), 1)
        self.assertEqual(strcmp_c([1, 2, 3], [1, 2, 3, 4, 5]), -1)
        self.assertEqual(strcmp_c([1, 4], [1, 4, 16]), -1)
        self.assertEqual(strcmp_c([2, 8], [2, 2, 3]), 1)
        self.assertEqual(strcmp_c([0, 0, 2, 4], [0, 0, 15]), -1)
        self.assertEqual(strcmp_c([0, 13], [0, 2, 2]), 1)
        self.assertEqual(strcmp_c([11, 2], [11, 2]), 0)

    def test_strcmp_naturally(self):
        self.assertEqual(strcmp_naturally("", ""), 0)
        self.assertEqual(strcmp_naturally("2a", "10a"), -1)
        self.assertEqual(strcmp_naturally("alfa", "bravo"), -1)

    def test_make_initials(self):
        self.assertEqual(make_initials(" "), ".")
        self.assertEqual(make_initials("John ronald reuel Tolkien"), "J.R.R.T.")
        self.assertEqual(make_initials("  e.B.Sledge "), "E.B.S.")
        self.assertEqual(make_initials("Apsley Cherry-Garrard"), "A.C-G.")
        self.assertEqual(make_initials("Windsor Saxe-\tCoburg - Gotha"), "W.S-C-G.")
        self.assertEqual(make_initials("Elisabeth Kubler-- - Ross"), "E.K-R.")
        self.assertEqual(
            make_initials("  Fitz-Simmons Ashton-Burke Leigh"), "F-S.A-B.L."
        )
        self.assertEqual(make_initials('Arleigh "31-knot"Burke '), "A.B.")
        self.assertEqual(
            make_initials('Harry "Bing" Crosby, Kris "Tanto" Paronto'), "H.C.,K.P."
        )
        self.assertEqual(make_initials("a.s.,b.s."), "A.S.,B.S.")
        self.assertEqual(make_initials("A. Strugatsky, B...Strugatsky."), "A.S.,B.S.")
        self.assertEqual(make_initials("Иржи Кропачек, Йозеф Новотный"), "И.К.,Й.Н.")
        self.assertEqual(make_initials("österreich"), "Ö.")
