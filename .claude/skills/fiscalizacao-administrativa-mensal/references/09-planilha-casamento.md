# 09 — Planilha de casamento (cruzamento final)

A planilha de casamento é a saída consolidada da fiscalização do mês. Tem uma linha por trabalhador da competência e cruza, lado a lado, o que aparece na folha, no FGTS Digital e na planilha de movimentação. É a base para identificar divergências e gerar a lista final de achados.

Template vazio disponível em `templates/planilha-casamento-fiscalizacao.xlsx`.

## Estrutura — uma aba principal

A aba principal chama-se **Casamento** e tem as colunas abaixo, na ordem.

### Identificação e movimentação

| # | Coluna | Origem | Observação |
|---|---|---|---|
| 1 | CPF | Movimentação / folha | Chave do casamento. |
| 2 | Nome | Movimentação / folha | |
| 3 | Cargo | Movimentação | |
| 4 | Posto / unidade | Movimentação | |
| 5 | Status na competência | Movimentação / folha | Ativo, Afastado — Doença, Afastado — Maternidade, Férias, Admitido no mês, Demitido no mês. |
| 6 | Substituição | Movimentação | Se aplicável, indicar substituto/substituído (CPF). |

### Folha de pagamento — proventos

| # | Coluna | Observação |
|---|---|---|
| 7 | Salário base | |
| 8 | Salário-mínimo (referência) | Para checagem de piso. Manter o salário-mínimo vigente. |
| 9 | Insalubridade | Valor pago. |
| 10 | Periculosidade | Valor pago. |
| 11 | Adicional noturno | Valor pago. |
| 12 | Hora noturna reduzida | Valor pago. Aplica-se quando há trabalho noturno. |
| 13 | Salário-família | Valor pago. |

### Folha de pagamento — descontos e benefícios

| # | Coluna | Observação |
|---|---|---|
| 14 | Desconto de vale-transporte | Em branco quando não houver. Quando houver, o valor descontado. |
| 15 | Valor pago de vale-alimentação | Informativo, vindo da folha ou de comprovante separado. |
| 16 | Valor pago de cesta básica | Informativo, quando houver. |
| 17 | Valor pago de vale-transporte | Informativo. Cruzar com a coluna de desconto: se houve desconto, deve haver pagamento. |

### FGTS

| # | Coluna | Observação |
|---|---|---|
| 18 | Depósito de FGTS demonstrado em folha | Geralmente 8% da base. |
| 19 | Base de remuneração total — FGTS Digital | Vinda da Relação de Categorias da guia detalhada. |
| 20 | Valor depositado — FGTS Digital | Vinda da guia. |
| 21 | Divergência FGTS | Cálculo: coluna 20 − coluna 18 (resultado diferente de zero é alerta). |

### INSS

| # | Coluna | Observação |
|---|---|---|
| 22 | Base de cálculo do INSS — folha | |
| 23 | Base de cálculo do INSS — DCTFWeb | Quando extraível por trabalhador (depende do detalhamento). |
| 24 | Divergência INSS | Cálculo: coluna 23 − coluna 22. |

### Resultado do casamento

| # | Coluna | Observação |
|---|---|---|
| 25 | Em folha | Sim/Não |
| 26 | No FGTS Digital | Sim/Não |
| 27 | Na movimentação | Sim/Não |
| 28 | Tomador correto | Sim/Não |
| 29 | Apontamentos | Texto livre, com termos diretos. |

## Aba auxiliar — Inconsistências

Aba **Inconsistências**, gerada por filtro/seleção da aba principal, contendo apenas linhas com `Apontamentos` preenchidos ou alguma divergência. Esta aba é a base do despacho de fiscalização.

## Aba auxiliar — Resumo

Aba **Resumo** com totais:

- Quantidade de trabalhadores na competência (movimentação).
- Quantidade em folha.
- Quantidade no FGTS Digital.
- Quantidade com divergência de base do FGTS.
- Quantidade com tomador incorreto.
- Quantidade de admissões no mês.
- Quantidade de rescisões no mês.
- Quantidade de trabalhadores em férias.
- Quantidade de afastados (doença/maternidade/outros).

## Regras de preenchimento

1. Uma linha por CPF. Trabalhadores admitidos ou demitidos no mês entram normalmente (com status correspondente).
2. Valores em branco quando a rubrica não se aplica (ex.: trabalhador sem insalubridade, coluna 9 fica vazia).
3. Para o vale-transporte, manter coluna 14 (desconto) e coluna 17 (pagamento) sempre verificáveis em conjunto.
4. A coluna `Apontamentos` (29) deve usar termos diretos. Exemplos: `Tomador Incorreto`, `Em folha, ausente no FGTS Digital`, `Divergência base FGTS`, `Sem pagamento de VT com desconto em folha`, `Substituição sem CPF do substituído`.

## Como a planilha é usada no despacho

A planilha de casamento é anexo do despacho/relatório de fiscalização. As linhas com apontamento alimentam a seção de achados. Os totais da aba Resumo entram no corpo do texto (ex.: "Foram identificados X trabalhadores com divergência entre base FGTS Digital e base da folha de pagamento; relação detalhada no Anexo Y").
