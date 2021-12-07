from src.damastes import __version__
from src.damastes import *
import src.damastes.shoot as shoot


class TestPureFunctions:
    def test_version(self):
        assert __version__ == "0.9.5"

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
        """
        There are four delimiters: comma, hyphen, dot, and space.
        make_initials() syntax philosophy: if a delimiter is
        misplaced, it's ignored.
        """
        assert make_initials("") == ""
        assert make_initials(" ") == ""
        assert make_initials(".. , .. ") == ""
        assert make_initials(" ,, .,") == ""
        assert make_initials(", a. g, ") == "A.G."
        assert make_initials("- , -I.V.-A,E.C.N-, .") == "I.V-A.,E.C.N."
        assert make_initials("John ronald reuel Tolkien") == "J.R.R.T."
        assert make_initials("  e.B.Sledge ") == "E.B.S."
        assert make_initials("Apsley Cherry-Garrard") == "A.C-G."
        assert make_initials("Windsor Saxe-\tCoburg - Gotha") == "W.S-C-G."
        assert make_initials("Elisabeth Kubler-- - Ross") == "E.K-R."
        assert make_initials("  Fitz-Simmons Ashton-Burke Leigh") == "F-S.A-B.L."
        assert make_initials('Arleigh "31-knot"Burke ') == "A.B."
        assert make_initials('Harry "Bing" Crosby, Kris "Tanto" Paronto') == "H.C.,K.P."
        assert (
            make_initials('William J. "Wild Bill" Donovan, Marta "Cinta Gonzalez')
            == "W.J.D.,M.C.G."
        )
        assert make_initials("a.s , - . ,b.s.") == "A.S.,B.S."
        assert make_initials("A. Strugatsky, B...Strugatsky.") == "A.S.,B.S."
        assert make_initials("Иржи Кропачек,, Йозеф Новотный") == "И.К.,Й.Н."
        assert make_initials("Язон динАльт, Шарль д'Артаньян") == "Я.динА.,Ш.д'А."
        assert (
            make_initials("Charles de Batz de Castelmore d'Artagnan")
            == "C.d.B.d.C.d'A."
        )
        assert (
            make_initials("Mario Del Monaco, Hutchinson of London") == "M.D.M.,H.o.L."
        )
        assert make_initials("Anselm haut Rodric") == "A.h.R."
        assert make_initials("Ансельм от Родрик") == "А.о.Р."
        assert make_initials("Leonardo Wilhelm DiCaprio") == "L.W.DiC."
        assert make_initials("De Beers, Guido van Rossum") == "D.B.,G.v.R."
        assert make_initials("Манфред фон Рихтгофен") == "М.ф.Р."
        assert make_initials("Armand Jean du Plessis") == "A.J.d.P."
        assert make_initials("johannes diderik van der waals") == "J.D.v.d.W."
        assert make_initials("Österreich über alles") == "Ö.Ü.A."
        assert make_initials("José Eduardo dos Santos") == "J.E.d.S."
        assert make_initials("Gnda'Ke") == "Gnda'K."
        assert make_initials("gnda'ke") == "G."
        assert make_initials("gnda'") == "G."
        assert make_initials("'Bravo") == "'B."
        assert make_initials("'") == "'."
        assert make_initials("'B") == "'B."
        assert make_initials("'b") == "'b."

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

        assert shoot._decorate_dir_name(0, Path("charlie")) == "000-charlie"
        args.strip_decorations = True
        assert shoot._decorate_dir_name(0, Path("charlie")) == "charlie"

        assert shoot._artist_part(prefix=" - ", suffix=" - ") == ""
        args.artist = "Daniel Defoe"
        assert shoot._artist_part(prefix=" - ", suffix=" - ") == " - Daniel Defoe - "
        assert shoot._artist_part(prefix=" - ") == " - Daniel Defoe"
        assert shoot._artist_part() == "Daniel Defoe"

        assert (
            shoot._decorate_file_name(7, ["deeper"], Path("delta.m4a")) == "delta.m4a"
        )
        args.strip_decorations = False
        args.prepend_subdir_name = True
        assert (
            shoot._decorate_file_name(7, ["deeper", "yet"], Path("delta.m4a"))
            == "07-deeper-yet-delta.m4a"
        )
        monkeypatch.setattr(shoot, "_FILES_TOTAL", 533)
        assert (
            shoot._decorate_file_name(7, ["deeper"], Path("delta.m4a"))
            == "007-deeper-delta.m4a"
        )
