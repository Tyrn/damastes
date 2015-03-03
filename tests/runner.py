import unittest
from procr.core.pcp import *


class TestHelpers(unittest.TestCase):

    def setUp(self):
        pass

    def test_zero_pad(self):
        self.assertEqual(str(3).zfill(5), "00003")
        self.assertEqual(str(15331).zfill(3), "15331")

    def test_sans_ext(self):
        self.assertEqual(sans_ext("/alfa/bravo/charlie.dat"), "/alfa/bravo/charlie")
        self.assertEqual(sans_ext(""), "")
        self.assertEqual(sans_ext("/alfa/bravo/charlie"), "/alfa/bravo/charlie")
        self.assertEqual(sans_ext("/alfa/bravo/charlie/"), "/alfa/bravo/charlie/")
        self.assertEqual(sans_ext("/alfa/bra.vo/charlie.dat"), "/alfa/bra.vo/charlie")

    def test_has_ext_of(self):
        self.assertEqual(has_ext_of("/alfa/bra.vo/charlie.ogg", "OGG"), True)
        self.assertEqual(has_ext_of("/alfa/bra.vo/charlie.ogg", ".ogg"), True)
        self.assertEqual(has_ext_of("/alfa/bra.vo/charlie.ogg", "mp3"), False)

    def test_str_strip_numbers(self):
        self.assertEqual(str_strip_numbers("ab11cdd2k.144"), [11, 2, 144])
        self.assertEqual(str_strip_numbers("Ignacio Vazquez-Abrams"), [])

    def test_cmpv_int(self):
        self.assertEqual(cmpv_int([], []), 0)
        self.assertEqual(cmpv_int([1], []), 1)
        self.assertEqual(cmpv_int([3], []), 1)
        self.assertEqual(cmpv_int([1, 2, 3], [1, 2, 3, 4, 5]), -2)
        self.assertEqual(cmpv_int([1, 4], [1, 4, 16]), -1)
        self.assertEqual(cmpv_int([2, 8], [2, 2, 3]), 1)
        self.assertEqual(cmpv_int([0, 0, 2, 4], [0, 0, 15]), -1)
        self.assertEqual(cmpv_int([0, 13], [0, 2, 2]), 1)
        self.assertEqual(cmpv_int([11, 2], [11, 2]), 0)

    def test_cmpstr_naturally(self):
        self.assertEqual(cmpstr_naturally("", ""), 0)
        self.assertEqual(cmpstr_naturally("2a", "10a"), -1)
        self.assertEqual(cmpstr_naturally("alfa", "bravo"), -1)

    def test_make_initials(self):
        self.assertEqual(make_initials("John ronald reuel Tolkien", "."), "J.R.R.T")
        self.assertEqual(make_initials("e. B. Sledge", "."), "E.B.S")
        
    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
