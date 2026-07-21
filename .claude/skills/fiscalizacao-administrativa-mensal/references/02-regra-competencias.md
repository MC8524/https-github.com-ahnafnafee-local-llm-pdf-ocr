# 02 — Regra das competências

A competência é o período de referência de cada documento. Empresas eventualmente enviam documentos de competência errada (do mês passado retrasado, de outro contrato, ou até de outra empresa). A primeira coisa a fazer em qualquer fiscalização mensal é validar a competência de tudo.

## Regra geral

Seja `M` o mês em que a fiscalização está sendo conduzida.

| Tipo de documento | Competência esperada |
|---|---|
| Folha de pagamento | `M - 1` (mês anterior) |
| Comprovantes individuais de salário | `M - 1` |
| Vale-alimentação / cesta básica | `M - 1` (referente ao mês de prestação) |
| Vale-transporte | `M - 1` |
| Planilha de movimentação | `M - 1` |
| DCTFWeb | `M - 2` (dois meses anteriores) |
| FGTS Digital | `M - 2` |
| DARF (INSS, terceiros, etc.) | `M - 2` |
| Comprovantes de recolhimento (fiscal/previdenciário) | `M - 2` (com data de pagamento no prazo legal) |
| Comprovantes de PIX/transferência | Conforme prazo IN 05/2017, Anexo XII, item 12: em até 3 dias úteis da operação. |

### Exemplo concreto

Fiscalização em maio:
- Folha, comprovantes de salário, benefícios, movimentação: competência **abril**.
- DCTFWeb, FGTS Digital, DARF: competência **março**.

## Validações a fazer

Para cada documento recebido:

1. Identificar a competência declarada no próprio documento (cabeçalho, página inicial).
2. Comparar com a esperada.
3. Em caso de divergência, classificar:
   - **Atrasado**: competência anterior à esperada (ex.: veio fevereiro quando se esperava março). Pode indicar pendência não sanada anteriormente.
   - **Antecipado**: competência posterior à esperada. Em geral é erro de envio.
   - **Empresa errada**: dados, CNPJ ou trabalhadores de outra empresa.
   - **Contrato errado**: documentos relativos a outro contrato da mesma empresa.

## Saída desta validação

Tabela com:

| Documento | Competência declarada | Competência esperada | Status |
|---|---|---|---|

Onde Status é: `OK`, `Competência Incorreta — Atrasado`, `Competência Incorreta — Antecipado`, `Empresa Incorreta` ou `Contrato Incorreto`.

## Exceções e bom senso

- Em meses iniciais de contrato, a competência da DCTFWeb/FGTS pode não existir ainda; isso não é falha.
- Quando há rescisões dentro do mês, a documentação rescisória da rescisão ocorrida em `M - 1` é parte do pacote do mês `M`.
- Pacotes com mais de uma competência (regularização) são aceitáveis, desde que cada competência venha completa e identificada.

## Por que isso importa

Sem validar competência primeiro, o resto da análise contamina. Cruzar folha de abril com FGTS Digital de fevereiro, por exemplo, gera divergências falsas (diferentes universos de trabalhadores). Validar primeiro evita retrabalho.
