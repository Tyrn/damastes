import copy
import os
from pathlib import Path

import src.damastes.shoot as shoot
# fmt: off
from src.damastes import (CLEAN_CONTEXT_PARAMS, RestrictedDotDict, __version__,
                          human_fine, initials, str_strip_numbers, strcmp_c,
                          strcmp_naturally)

# fmt: on


class TestPureFunctions:
    def test_version(self):
        assert __version__ == "0.9.5"

    def test_zero_pad(self):
        assert str(3).zfill(5) == "00003"
        assert str(15331).zfill(3) == "15331"

    def test_explicit_plus(self):
        assert f"{1:+d}" == "+1"
        assert f"{-1:+d}" == "-1"

    def test_isdigit(self):
        assert "".isdigit() == False
        assert "0".isdigit() == True
        assert "42".isdigit() == True
        assert "-42".isdigit() == False
        assert "4₂".isdigit() == True
        assert "4²".isdigit() == True

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

    def test_initials(self):
        """
        There are four delimiters: comma, hyphen, dot, and space.
        initials() syntax philosophy: if a delimiter is
        misplaced, it's ignored.
        """
        assert initials("") == ""
        assert initials(" ") == ""
        assert initials(".. , .. ") == ""
        assert initials(" ,, .,") == ""
        assert initials(", a. g, ") == "A.G."
        assert initials("- , -I.V.-A,E.C.N-, .") == "I.V-A.,E.C.N."
        assert initials("John ronald reuel Tolkien") == "J.R.R.T."
        assert initials("  e.B.Sledge ") == "E.B.S."
        assert initials("Apsley Cherry-Garrard") == "A.C-G."
        assert initials("Windsor Saxe-\tCoburg - Gotha") == "W.S-C-G."
        assert initials("Elisabeth Kubler-- - Ross") == "E.K-R."
        assert initials("  Fitz-Simmons Ashton-Burke Leigh") == "F-S.A-B.L."
        assert initials('Arleigh "31-knot"Burke ') == "A.B."
        assert initials('Harry "Bing" Crosby, Kris "Tanto" Paronto') == "H.C.,K.P."
        assert (
            initials('William J. "Wild Bill" Donovan, Marta "Cinta Gonzalez')
            == "W.J.D.,M.C.G."
        )
        assert initials("a.s , - . ,b.s.") == "A.S.,B.S."
        assert initials("A. Strugatsky, B...Strugatsky.") == "A.S.,B.S."
        assert initials("Иржи Кропачек,, Йозеф Новотный") == "И.К.,Й.Н."
        assert initials("Язон динАльт, Шарль д'Артаньян") == "Я.динА.,Ш.д'А."
        assert initials("Charles de Batz de Castelmore d'Artagnan") == "C.d.B.d.C.d'A."
        assert initials("Mario Del Monaco, Hutchinson of London") == "M.D.M.,H.o.L."
        assert initials("Anselm haut Rodric") == "A.h.R."
        assert initials("Ансельм от Родрик") == "А.о.Р."
        assert initials("Leonardo Wilhelm DiCaprio") == "L.W.DiC."
        assert initials("леонардо вильгельм ди каприо") == "Л.В.д.К."
        assert initials("kapitän zur see") == "K.z.S."
        assert initials("De Beers, Guido van Rossum") == "D.B.,G.v.R."
        assert initials("Манфред фон Рихтгофен") == "М.ф.Р."
        assert initials("Armand Jean du Plessis") == "A.J.d.P."
        assert initials("johannes diderik van der waals") == "J.D.v.d.W."
        assert initials("Karl Hård af Segerstad") == "K.H.a.S."
        assert initials("Österreich über alles") == "Ö.Ü.A."
        assert initials("José Eduardo dos Santos") == "J.E.d.S."
        assert initials("Gnda'Ke") == "Gnda'K."
        assert initials("gnda'ke") == "G."
        assert initials("gnda'") == "G."
        assert initials("'Bravo") == "'B."
        assert initials("'") == "'."
        assert initials("'B") == "'B."
        assert initials("'b") == "'b."
        assert initials("dA") == "dA."
        assert initials("DA") == "DA."
        assert initials("DAMadar") == "DA."
        assert initials("Плиний Старший") == "П.Ст."
        assert initials("Pliny the Elder") == "P.t.E."
        assert initials("Плиний Младший") == "П.Мл."
        assert initials("Плиний Мл.") == "П.Мл."
        assert initials("George Smith Patton Jr.") == "G.S.P.Jr."
        assert initials("Джордж Смит паттон ст") == "Д.С.П.ст."
        assert initials("Redington Sr") == "R.Sr."

    def test_human_fine(self):
        assert human_fine(0) == "0"
        assert human_fine(1) == "1"
        assert human_fine(42) == "42"
        assert human_fine(1800) == "2kB"
        assert human_fine(123456789) == "117.7MB"
        assert human_fine(123456789123) == "114.98GB"
        assert human_fine(1024) == "1kB"
        assert human_fine(1024**2) == "1.0MB"
        assert human_fine(1024**3) == "1.00GB"
        assert human_fine(1024**4) == "1.00TB"


class TestNonPureHelpers:
    def new_args(self):
        return RestrictedDotDict(copy.deepcopy(CLEAN_CONTEXT_PARAMS))

    def test_compare(self, monkeypatch):
        args = self.new_args()
        monkeypatch.setattr(shoot, "_ARGS", args)

        args.sort_lex = True
        assert shoot._path_compare(Path("alfa"), Path("alfa" + os.path.sep)) == 0
        assert shoot._path_compare(Path("10alfa"), Path("2bravo")) == -1
        assert shoot._file_compare(Path("10alfa"), Path("2bravo")) == -1
        assert shoot._file_compare(Path("alfa.ogg"), Path("alfa.mp3")) == 0
        assert shoot._file_compare(Path("Alfa.ogg"), Path("alfa.mp3")) == -1
        args.sort_lex = False
        assert shoot._path_compare(Path("10alfa"), Path("2bravo")) == 1
        assert shoot._file_compare(Path("10alfa"), Path("2bravo")) == 1

    def test_decorate(self, monkeypatch):
        args = self.new_args()
        monkeypatch.setattr(shoot, "_ARGS", args)
        monkeypatch.setattr(shoot, "_FILES_TOTAL", 42)

        assert shoot._artist_part(prefix=" - ", suffix=" - ") == ""
        args.artist = "Daniel Defoe"
        assert shoot._artist_part(prefix=" - ", suffix=" - ") == " - Daniel Defoe - "
        assert shoot._artist_part(prefix=" - ") == " - Daniel Defoe"
        assert shoot._artist_part() == "Daniel Defoe"

        assert shoot._file_decorate(7, ["deeper"], Path("delta.m4a")) == "07-delta.m4a"
        args.prepend_subdir_name = True
        assert (
            shoot._file_decorate(7, ["deeper", "yet"], Path("delta.m4a"))
            == "07-[deeper][yet]-delta.m4a"
        )
        args.strip_decorations = True
        assert (
            shoot._file_decorate(7, ["deeper"], Path("delta.m4a"))
            == "07-[deeper]-delta.m4a"
        )
        args.tree_dst = True
        assert shoot._file_decorate(7, ["deeper"], Path("delta.m4a")) == "delta.m4a"
        monkeypatch.setattr(shoot, "_FILES_TOTAL", 533)
        args.strip_decorations = False
        args.tree_dst = False
        assert (
            shoot._file_decorate(7, ["deeper"], Path("delta.m4a"))
            == "007-[deeper]-delta.m4a"
        )
