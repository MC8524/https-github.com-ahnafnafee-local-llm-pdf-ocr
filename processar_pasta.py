#!/usr/bin/env python3
"""
Processa uma pasta cheia de PDFs (contracheques, comprovantes, DCTF, etc.)
e gera uma planilha CSV com os dados extraídos.

Uso pela linha de comando:
    uv run processar_pasta.py                    # pergunta interativamente
    uv run processar_pasta.py C:\\pasta\\com\\pdfs
    uv run processar_pasta.py C:\\pasta saida.csv

Também chamado pelo processar_pasta.bat (duplo-clique no Windows).

Requisitos:
    - LM Studio aberto, com o modelo allenai/olmocr-2-7b carregado e
      servindo no endpoint http://localhost:1234/v1 (botão "Start Server").
    - Dependências instaladas via `uv sync`.
"""

from __future__ import annotations

import asyncio
import csv
import sys
import traceback
from pathlib import Path

from src.pdf_ocr import analyze_document


# Ordem das colunas da planilha. O pós-processador pode emitir mais campos
# — ajustados aqui ficam no começo; o resto fica numa coluna "outros".
COLUNAS = [
    "arquivo",
    "cpf",
    "cpf_valido",
    "cnpj",
    "cnpj_valido",
    "nome",
    "empresa",
    "competencia",
    "data",
    "salario_bruto",
    "inss",
    "irrf",
    "fgts",
    "liquido",
    "agencia",
    "conta",
    "banco",
    "valor",
    "auth_code",
    "dctf_recibo",
    "avisos",
    "pdf_pesquisavel",
]


def _first_value(result, name: str) -> str:
    f = result.first(name)
    if f is None:
        return ""
    if f.parsed is not None:
        return str(f.parsed)
    return f.value or ""


def _valid_mark(result, name: str) -> str:
    f = result.first(name)
    if f is None or f.valid is None:
        return ""
    return "sim" if f.valid else "NÃO"


async def processar_um_pdf(pdf_path: Path) -> dict[str, str]:
    """Roda o OCR + extração em um PDF e devolve uma linha para a planilha."""
    try:
        resultado = await analyze_document(
            str(pdf_path),
            preprocess="auto",
            extract_fields=True,
            llm_extract=True,
        )
    except Exception as e:
        traceback.print_exc()
        return {
            "arquivo": pdf_path.name,
            "avisos": f"ERRO: {e}",
            **{c: "" for c in COLUNAS if c not in ("arquivo", "avisos")},
        }

    linha = {
        "arquivo":          pdf_path.name,
        "cpf":              _first_value(resultado, "cpf"),
        "cpf_valido":       _valid_mark(resultado, "cpf"),
        "cnpj":             _first_value(resultado, "cnpj"),
        "cnpj_valido":      _valid_mark(resultado, "cnpj"),
        "nome":             _first_value(resultado, "nome"),
        "empresa":          _first_value(resultado, "empresa"),
        "competencia":      _first_value(resultado, "competencia"),
        "data":             _first_value(resultado, "date"),
        "salario_bruto":    _first_value(resultado, "salario_bruto"),
        "inss":             _first_value(resultado, "inss"),
        "irrf":             _first_value(resultado, "irrf"),
        "fgts":             _first_value(resultado, "fgts"),
        "liquido":          _first_value(resultado, "liquido"),
        "agencia":          _first_value(resultado, "agencia"),
        "conta":            _first_value(resultado, "conta"),
        "banco":            _first_value(resultado, "banco"),
        "valor":            _first_value(resultado, "brl"),
        "auth_code":        _first_value(resultado, "auth_code"),
        "dctf_recibo":      _first_value(resultado, "dctf_recibo"),
        "avisos":           " | ".join(resultado.warnings),
        "pdf_pesquisavel":  resultado.output_pdf,
    }
    return linha


async def processar_pasta(
    pasta_entrada: Path, arquivo_saida: Path
) -> int:
    pdfs = sorted(p for p in pasta_entrada.iterdir() if p.suffix.lower() == ".pdf")
    pdfs = [p for p in pdfs if "_ocr" not in p.stem]  # ignora saídas nossas

    if not pdfs:
        print(f"[!] Nenhum PDF encontrado em '{pasta_entrada}'.")
        return 1

    print(f"[OK] {len(pdfs)} PDFs encontrados. Processando...\n")
    linhas: list[dict[str, str]] = []
    for i, pdf in enumerate(pdfs, 1):
        print(f"[{i}/{len(pdfs)}] {pdf.name}")
        linha = await processar_um_pdf(pdf)
        linhas.append(linha)
        cpf = linha.get("cpf", "")
        liquido = linha.get("liquido", "")
        print(f"         CPF={cpf}  líquido={liquido}  avisos={linha.get('avisos', '')}\n")

    # utf-8-sig para o Excel abrir com acentos certos.
    with open(arquivo_saida, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUNAS, delimiter=";")
        writer.writeheader()
        writer.writerows(linhas)

    print(f"\n[OK] Planilha gerada em: {arquivo_saida}")
    print(f"     Abra no Excel ou Google Sheets.")
    return 0


def perguntar_pasta() -> Path:
    print("\n=== Processar pasta de PDFs ===\n")
    print("Cole aqui o caminho da pasta onde estão os PDFs (ex: C:\\contracheques):")
    entrada = input("> ").strip().strip('"').strip("'")
    return Path(entrada)


def main() -> None:
    if len(sys.argv) >= 2:
        pasta = Path(sys.argv[1]).expanduser()
    else:
        pasta = perguntar_pasta()

    if not pasta.is_dir():
        print(f"[X] Pasta não encontrada: {pasta}")
        sys.exit(2)

    if len(sys.argv) >= 3:
        saida = Path(sys.argv[2]).expanduser()
    else:
        saida = pasta / "resultado.csv"

    codigo = asyncio.run(processar_pasta(pasta, saida))
    sys.exit(codigo)


if __name__ == "__main__":
    main()
