"""Contextual extraction of Brazilian fiscal fields."""

from decimal import Decimal

from src.pdf_ocr.postprocessing import ContextualExtractor, analyze_text


CONTRACHEQUE_OK = """
EMPRESA ACME LTDA
CNPJ: 11.222.333/0001-81
Funcionário: João da Silva
CPF: 529.982.247-25
Competência: 04/2024

Vencimentos               2.500,00
INSS                        225,00
IRRF                         75,00
Líquido a receber         2.200,00
"""


CONTRACHEQUE_INCONSISTENT = """
Funcionário: Maria
CPF: 529.982.247-25
Competência: 04/2024
Salário Bruto            R$ 3.000,00
INSS                     R$   300,00
IRRF                     R$   100,00
Líquido a receber        R$ 2.000,00
"""


COMPROVANTE = """
Banco do Brasil S.A.
CNPJ: 00.360.305/0001-04
Agência: 1234-5
Conta corrente: 98765-4
Valor: R$ 1.500,00
Data: 15/04/2024
Autenticação: ABC123DEF456
PIX UUID: 550e8400-e29b-41d4-a716-446655440000
"""


class TestContracheque:
    def test_extracts_all_fields(self):
        fields, warnings = ContextualExtractor().extract(CONTRACHEQUE_OK)
        assert fields["cpf"][0].value == "529.982.247-25"
        assert fields["cpf"][0].valid is True
        assert fields["cnpj"][0].value == "11.222.333/0001-81"
        assert fields["cnpj"][0].valid is True
        assert fields["competencia"][0].value == "04/2024"
        assert fields["salario_bruto"][0].parsed == Decimal("2500.00")
        assert fields["inss"][0].parsed == Decimal("225.00")
        assert fields["irrf"][0].parsed == Decimal("75.00")
        assert fields["liquido"][0].parsed == Decimal("2200.00")
        assert warnings == []

    def test_inconsistent_totals_warns(self):
        fields, warnings = ContextualExtractor().extract(CONTRACHEQUE_INCONSISTENT)
        assert fields["liquido"][0].parsed == Decimal("2000.00")
        # 3000 - 300 - 100 = 2600, not 2000 — should warn.
        assert any("líquido" in w.lower() or "Líquido" in w for w in warnings)

    def test_invalid_cpf_warns(self):
        text = "CPF: 111.111.111-11\n"
        _, warnings = ContextualExtractor().extract(text)
        assert any("CPF" in w for w in warnings)


class TestComprovante:
    def test_extracts_banking_fields(self):
        fields, _ = ContextualExtractor().extract(COMPROVANTE)
        assert fields["agencia"][0].value == "1234-5"
        assert fields["conta"][0].value == "98765-4"
        assert fields["brl"][0].parsed == Decimal("1500.00")
        assert fields["date"][0].value == "15/04/2024"
        assert fields["auth_code"][0].value == "ABC123DEF456"
        assert fields["pix_uuid"][0].value.startswith("550e8400")


class TestAnalyzeText:
    def test_joins_pages_and_extracts(self):
        pages = {
            0: ["EMPRESA ACME LTDA", "CNPJ: 11.222.333/0001-81"],
            1: ["CPF: 529.982.247-25"],
        }
        text, fields, warnings = analyze_text(pages)
        assert "ACME" in text
        assert fields["cpf"][0].valid is True
        assert fields["cnpj"][0].valid is True
