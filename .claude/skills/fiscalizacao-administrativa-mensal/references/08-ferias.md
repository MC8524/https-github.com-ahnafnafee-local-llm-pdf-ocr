# 08 — Documentos de férias

Aplicável a todo trabalhador que gozou férias com início no mês, ou que recebeu pagamento de férias no mês para gozo no mês seguinte.

## Documentos esperados

| Documento | Obrigatório | Observação |
|---|---|---|
| Aviso de férias | Sim | Comunicação prévia ao empregado, com data de início e fim do gozo. |
| Recibo de férias | Sim | Discriminação dos valores pagos. |
| Comprovante de pagamento | Sim | Bancário ou equivalente. |

## Validações de conteúdo

### Aviso de férias

- Antecedência mínima legal de **30 dias** ao início do gozo (CLT, art. 135).
- Assinaturas: empregado (recebimento) e empregador.
- Indicar data de início e fim do gozo, e período aquisitivo.

### Recibo de férias

- Discriminação completa:
  - Remuneração de férias (salário base + médias de variáveis, quando houver).
  - 1/3 constitucional.
  - Eventuais adicionais habituais (insalubridade, periculosidade, adicional noturno).
  - Descontos (INSS, IRRF).
- Assinatura do empregado.
- Coerência com o aviso (mesmas datas e período aquisitivo).

### Comprovante de pagamento

- Data do pagamento: até **2 dias antes do início do gozo** (CLT, art. 145). É o ponto mais frequente de apontamento. Pagamento na véspera ou no próprio dia do gozo é irregular.
- Valor coerente com o recibo.

### Conferência aritmética

Erros básicos aparecem com frequência. Recalcular:

- Remuneração de férias = (salário-base + adicionais habituais) × (dias de gozo / 30).
- 1/3 constitucional = remuneração de férias / 3.
- INSS sobre férias: incide.
- IRRF sobre férias: incide, com tabela e base própria (dedução do 1/3 antes? não — incide sobre o total).

Quando o trabalhador receber em férias fracionadas, conferir somatórios.

## Observação sobre a folha do mês

Mesmo que a folha do mês traga o trabalhador em status "normal/ativo", se ele recebeu rubrica de férias na competência, ele deve ser marcado como **Férias** na planilha de casamento. A folha às vezes mantém o status original e isso pode confundir leitura automática.

## Saída desta fase

Por trabalhador em férias na competência:

| CPF | Nome | Período aquisitivo | Início do gozo | Fim do gozo | Data pagamento | Status |
|---|---|---|---|---|---|---|

Status com termos diretos: `OK`, `Pagamento Fora do Prazo`, `Aviso Não Assinado`, `Recibo Não Assinado`, `Erro de Cálculo`, `Falta Comprovante`, `Antecedência Insuficiente`.
