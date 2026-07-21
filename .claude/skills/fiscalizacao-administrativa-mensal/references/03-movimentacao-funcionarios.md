# 03 — Planilha de movimentação de funcionários

A planilha de movimentação é o documento mestre que diz quem trabalhou no contrato no mês. É o ponto de partida do casamento com a folha e com o FGTS Digital.

## Campos esperados

Para cada trabalhador alocado no contrato na competência, a planilha deve trazer:

| Campo | Obrigatório | Observação |
|---|---|---|
| Nome completo | Sim | |
| CPF | Sim | |
| Cargo / função | Sim | |
| Posto / unidade de lotação | Sim | Ex.: ala, setor do HC-UFPE. |
| Jornada / escala | Sim | Ex.: 12x36, 6x1. |
| Data de admissão no contrato | Sim | |
| Status na competência | Sim | Ativo, Afastado (doença/maternidade), Férias, Demitido. |
| Substituição (quando aplicável) | Condicional | Ver campos abaixo. |

## Campos exigidos quando há substituição

Sempre que um trabalhador estiver substituindo outro (cobertura de férias, afastamento, vaga em aberto), a planilha deve trazer:

| Campo | Observação |
|---|---|
| Nome do substituído | |
| CPF do substituído | |
| Nome do substituto | |
| CPF do substituto | |
| Motivo da substituição | Férias, afastamento por doença, licença-maternidade, vaga em aberto, etc. |
| Prazo da substituição | Período coberto, com data de início e fim previstos. |
| Natureza | Temporária ou definitiva. |

A ausência de qualquer um desses campos quando há substituição é apontamento. A regra prática: se há substituto, deve haver substituído identificado por CPF.

## Validações a realizar

1. **Completude dos campos** acima.
2. **Cruzamento com a folha de pagamento**:
   - Todo trabalhador na movimentação deve estar na folha (exceto admissões/desligamentos no fim do mês, com justificativa).
   - Todo trabalhador na folha deve estar na movimentação.
   - Discrepâncias devem ir para a planilha de casamento.
3. **Tomador correto**: confirmar que os trabalhadores estão alocados sob o CNPJ do contratante (HC-UFPE / EBSERH). Casos em que o tomador é a própria empresa contratada ou outro tomador são apontamento sério.
4. **Coerência com substituições**: o substituto deve aparecer também na folha; e o motivo declarado (ex.: "férias do substituído") deve ser coerente com o status do substituído (que estaria como "Férias" no mesmo período).
5. **Funcionários em curso (ativos)**: separar visualmente os ativos no mês dos demais (afastados, demitidos, em férias) para depois conferir individualmente o recebimento correto.

## Saída desta fase

Duas saídas:

1. **Tabela enxuta de inconsistências da movimentação**, no formato:

| CPF | Nome | Problema |
|---|---|---|

Onde Problema usa termos diretos: `Falta CPF substituído`, `Sem motivo de substituição`, `Tomador Incorreto`, `Em folha, ausente na movimentação`, `Na movimentação, ausente na folha`, etc.

2. **Lista de funcionários ativos na competência**, pronta para servir de base na extração da folha (Fase 4) e no casamento final (Fase 7).
