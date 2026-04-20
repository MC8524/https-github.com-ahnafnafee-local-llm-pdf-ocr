"""Checksum and parsing validators for Brazilian fiscal tokens."""

from datetime import date
from decimal import Decimal

import pytest

from src.pdf_ocr.postprocessing.validators import (
    brl_to_decimal,
    cnpj_valid,
    cpf_valid,
    date_parse,
)


class TestCPF:
    @pytest.mark.parametrize("cpf", [
        "529.982.247-25",
        "111.444.777-35",
        "248.438.034-80",
    ])
    def test_valid(self, cpf):
        assert cpf_valid(cpf) is True

    @pytest.mark.parametrize("cpf", [
        "111.111.111-11",   # all same digit
        "000.000.000-00",
        "123.456.789-00",   # wrong checksum
        "529.982.247-26",   # off-by-one last digit
        "529.982.247",      # too short
    ])
    def test_invalid(self, cpf):
        assert cpf_valid(cpf) is False


class TestCNPJ:
    @pytest.mark.parametrize("cnpj", [
        "11.222.333/0001-81",
        "00.360.305/0001-04",   # Banco do Brasil
    ])
    def test_valid(self, cnpj):
        assert cnpj_valid(cnpj) is True

    @pytest.mark.parametrize("cnpj", [
        "11.111.111/1111-11",   # all same
        "11.222.333/0001-80",   # wrong checksum
        "11.222.333/0001",
    ])
    def test_invalid(self, cnpj):
        assert cnpj_valid(cnpj) is False


class TestBRL:
    @pytest.mark.parametrize("s,expected", [
        ("R$ 1.234,56", Decimal("1234.56")),
        ("R$1234,56", Decimal("1234.56")),
        ("1.234,56", Decimal("1234.56")),
        ("R$ 0,01", Decimal("0.01")),
        ("R$ 12.345.678,90", Decimal("12345678.90")),
    ])
    def test_parses(self, s, expected):
        assert brl_to_decimal(s) == expected

    def test_no_match(self):
        assert brl_to_decimal("sem valor aqui") is None


class TestDateParse:
    def test_slash_format(self):
        assert date_parse("15/04/2024") == date(2024, 4, 15)

    def test_dash_format(self):
        assert date_parse("15-04-2024") == date(2024, 4, 15)

    def test_two_digit_year_modern(self):
        assert date_parse("15/04/24") == date(2024, 4, 15)

    def test_two_digit_year_legacy(self):
        assert date_parse("15/04/99") == date(1999, 4, 15)

    def test_month_word(self):
        assert date_parse("15 de abril de 2024") == date(2024, 4, 15)

    def test_month_word_abbrev(self):
        assert date_parse("15 de abr de 2024") == date(2024, 4, 15)

    def test_invalid(self):
        assert date_parse("apenas texto") is None

    def test_impossible_date(self):
        assert date_parse("32/13/2024") is None
