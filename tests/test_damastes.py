from src.damastes import __version__
from src.damastes import *


class TestPureFunctions:
    def test_version(self):
        assert __version__ == "0.9.4"

    def test_zero_pad(self):
        assert str(3).zfill(5) == "00003"
        assert str(15331).zfill(3) == "15331"

    def test_explicit_plus(self):
        assert f"{1:+d}" == "+1"
        assert f"{-1:+d}" == "-1"

    def test_str_strip_numbers(self):
        assert str_strip_numbers("ab11cdd2k.144") == [11, 2, 144]
        assert str_strip_numbers("Ignacio Vazquez-Abrams") == []

    def test_strcmp_c(self):
        assert strcmp_c("aardvark", "bobo") == -1
        assert strcmp_c([], []) == 0
        assert strcmp_c([1], []) == 1
        assert strcmp_c([3], []) == 1
        assert strcmp_c([1, 2, 3], [1, 2, 3, 4, 5]) == -1
        assert strcmp_c([1, 4], [1, 4, 16]) == -1
        assert strcmp_c([2, 8], [2, 2, 3]) == 1
        assert strcmp_c([0, 0, 2, 4], [0, 0, 15]) == -1
        assert strcmp_c([0, 13], [0, 2, 2]) == 1
        assert strcmp_c([11, 2], [11, 2]) == 0

    def test_strcmp_naturally(self):
        assert strcmp_naturally("", "") == 0
        assert strcmp_naturally("2a", "10a") == -1
        assert strcmp_naturally("alfa", "bravo") == -1

    def test_make_initials(self):
        assert make_initials("") == ""
        assert make_initials(" ") == ""
        assert make_initials("....") == ""
        assert make_initials(",,,") == ",,,"
        assert make_initials(", a. g") == ",A.G."
        assert make_initials("John ronald reuel Tolkien") == "J.R.R.T."
        assert make_initials("  e.B.Sledge ") == "E.B.S."
        assert make_initials("Apsley Cherry-Garrard") == "A.C-G."
        assert make_initials("Windsor Saxe-\tCoburg - Gotha") == "W.S-C-G."
        assert make_initials("Elisabeth Kubler-- - Ross") == "E.K-R."
        assert make_initials("  Fitz-Simmons Ashton-Burke Leigh") == "F-S.A-B.L."
        assert make_initials('Arleigh "31-knot"Burke ') == "A.B."
        assert make_initials('Harry "Bing" Crosby, Kris "Tanto" Paronto') == "H.C.,K.P."
        assert make_initials("a.s.,b.s.") == "A.S.,B.S."
        assert make_initials("A. Strugatsky, B...Strugatsky.") == "A.S.,B.S."
        assert make_initials("Иржи Кропачек, Йозеф Новотный") == "И.К.,Й.Н."
        assert make_initials("Österreich über alles") == "Ö.Ü.A."

    def test_human_fine(self):
        assert human_fine(0) == "0"
        assert human_fine(1) == "1"
        assert human_fine(42) == "42"
        assert human_fine(1800) == "2kB"
        assert human_fine(123456789) == "117.7MB"
        assert human_fine(123456789123) == "114.98GB"
        assert human_fine(1024) == "1kB"
        assert human_fine(1024 ** 2) == "1.0MB"
        assert human_fine(1024 ** 3) == "1.00GB"
        assert human_fine(1024 ** 4) == "1.00TB"
