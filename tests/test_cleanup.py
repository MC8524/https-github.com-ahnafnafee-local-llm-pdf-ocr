"""Text cleanup — whitespace, hyphenation, OCR confusions."""

from src.pdf_ocr.postprocessing.cleanup import (
    cleanup_text,
    dehyphenate,
    fix_numeric_confusion,
    fix_rn_confusion,
    normalize_whitespace,
)


class TestWhitespace:
    def test_collapses_multiple_spaces(self):
        assert normalize_whitespace("a    b") == "a b"

    def test_strips_space_before_punct(self):
        assert normalize_whitespace("olá , mundo .") == "olá, mundo."

    def test_normalizes_smart_quotes(self):
        assert normalize_whitespace("\u201ctext\u201d") == '"text"'

    def test_collapses_many_blank_lines(self):
        text = "a\n\n\n\n\nb"
        out = normalize_whitespace(text)
        # 3+ blanks collapse to 2.
        assert out.count("\n\n\n") == 0


class TestDehyphenate:
    def test_joins_across_line_break(self):
        assert dehyphenate("pala-\nvra") == "palavra"

    def test_preserves_capital_after_break(self):
        # Rule only fires lowercase-lowercase, so capitals stay split.
        assert "-\n" in dehyphenate("final-\nPartida")


class TestRnConfusion:
    def test_fixes_rn_to_m(self):
        assert fix_rn_confusion("rnodelo") == "modelo"

    def test_preserves_safe_word(self):
        assert fix_rn_confusion("carne") == "carne"

    def test_preserves_interno(self):
        assert fix_rn_confusion("interno") == "interno"


class TestNumericConfusion:
    def test_rewrites_zero_lookalikes_in_number(self):
        # Pure-letter "O" followed by comma and digits looks numeric enough.
        assert fix_numeric_confusion("1.OOO,OO") == "1.000,00"

    def test_leaves_alpha_words_alone(self):
        assert fix_numeric_confusion("líquido") == "líquido"

    def test_rewrites_S_to_5_in_number(self):
        assert "5" in fix_numeric_confusion("R$ 1.S00,00")

    def test_no_change_for_plain_text(self):
        assert fix_numeric_confusion("Salário bruto") == "Salário bruto"


class TestCleanupPipeline:
    def test_all_together(self):
        raw = "  Salá-\nrio   bruto :  R$  1.OOO,OO  "
        out = cleanup_text(raw)
        assert "Salário" in out
        assert "1.000,00" in out
