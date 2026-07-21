# 04 — Folha de pagamento (extração e análise)

A folha de pagamento é a fonte principal das remunerações e descontos do mês. A análise tem dois objetivos: (a) verificar se cada trabalhador recebeu corretamente (salário, adicionais, benefícios) e (b) extrair as colunas da planilha de casamento (Fase 7).

## Rubricas a observar

### Vencimentos (proventos)

| Rubrica | Observação |
|---|---|
| Salário base | Conferir com a base contratual e o piso da CCT. Quando piso, conferir contra o salário-mínimo nacional ou o piso da categoria por cargo. |
| Insalubridade | Quando devida (atividade insalubre). Conferir grau e base de cálculo conforme CCT/CLT. |
| Periculosidade | Quando devida. Conferir base. |
| Adicional noturno | Para trabalho entre 22h e 5h. Conferir percentual conforme CCT. |
| Hora noturna reduzida | A hora noturna tem duração de 52 min 30 s; o ajuste deve estar refletido. |
| Horas extras | Conferir percentual e base. |
| Salário-família | Quando devido (dependentes elegíveis). |
| Descanso semanal remunerado | Quando aplicável conforme escala. |
| Férias e 1/3 constitucional | Quando o trabalhador estiver em férias na competência ou tenha recebido férias no mês. |

### Descontos

| Rubrica | Observação |
|---|---|
| INSS | Conforme tabela. |
| IRRF | Conforme tabela. |
| Vale-transporte (desconto) | Limitado a 6% do salário base do trabalhador (Lei nº 7.418/1985). É a rubrica-chave: trabalhador com desconto de VT deve ter recebido VT. |
| Vale-alimentação (desconto, quando previsto) | Conforme CCT. |
| Pensão alimentícia | Conforme determinação judicial. |
| Outros descontos | Verificar autorização e legalidade. |

### Informações (não somam no líquido)

Algumas empresas registram em folha, apenas como informativo (sem afetar o cálculo do líquido):

- Valor pago de vale-alimentação no mês.
- Valor pago de cesta básica no mês.
- Valor pago de vale-transporte no mês.

Esses valores devem ser extraídos para a planilha de casamento, mas o foco é verificar a coerência: se há desconto de VT, deve haver pagamento de VT (a empresa pode demonstrar isso na folha, ou em comprovante separado).

### Base e depósito do FGTS

| Item | Observação |
|---|---|
| Base de cálculo do FGTS | Soma das remunerações que entram na base (salário, adicionais, etc.), conforme legislação. |
| Valor do depósito de FGTS demonstrado em folha | Geralmente 8% da base. Anotar para depois cruzar com o FGTS Digital. |

### Base de cálculo do INSS

Extrair o valor da base de cálculo do INSS por trabalhador para cruzar depois com a DCTFWeb e o FGTS Digital.

## Situação funcional do trabalhador

A folha geralmente traz a situação do trabalhador na competência. Padronizar para a planilha de casamento como:

| Código | Significado |
|---|---|
| Ativo | Trabalhando normalmente. |
| Afastado — Doença | Afastamento por doença (auxílio-doença, etc.). |
| Afastado — Maternidade | Licença-maternidade. |
| Afastado — Outros | Outras causas de afastamento. |
| Férias | Em gozo de férias na competência (mesmo que apareça em folha como "normal", marcar férias se houver pagamento de férias). |
| Admitido no mês | Admissão dentro da competência. |
| Demitido no mês | Rescisão dentro da competência. |

A regra prática: se há rubrica de férias na folha do trabalhador, sinalizar como "Férias" ainda que outro campo o trate como ativo.

## Foco no vale-transporte

Este é o ponto mais sensível da folha. Para cada trabalhador:

1. Verificar se há **desconto de VT** em folha. Se sim, registrar o valor descontado.
2. Verificar se há **pagamento/recarga de VT** demonstrado em folha (rubrica informativa) ou em documento separado de benefícios.
3. Caso haja desconto e **não haja** comprovação de pagamento/recarga: apontamento de divergência grave.
4. Caso haja pagamento sem desconto: aceitável se houver renúncia expressa ao desconto pelo trabalhador, ou se a CCT prevê custeio integral pela empresa.

## Particularidades de leitura

Algumas empresas concatenam rubricas em linha única (sem quebra por trabalhador), o que dificulta parser automático. Quando o documento for pesquisável e estruturado de forma confiável, a leitura pode ser visual ou apoiada por extrator dedicado. Quando o documento for digitalizado/imagem, **só então** considerar OCR (ver `10-cuidados-praticos.md`).

Preferência geral: leitura manual quando o volume for tratável; uso de extrator (Python) somente quando o volume justificar e a confiabilidade da extração for verificável. Em qualquer caso, em apresentações de dados extraídos para o usuário, apresentar trabalhadores em **grupos sequenciais de 10**, sem pedir confirmação entre grupos.

## Cálculos básicos a conferir

Erros básicos aparecem com frequência:

- Soma de proventos diferente do total declarado.
- Desconto de VT acima do teto de 6% do salário base.
- Salário-família com valor por dependente diferente do oficial.
- Insalubridade calculada sobre base errada (a CCT pode prever salário-mínimo, piso da categoria ou salário-base; depende do contrato).
- Adicional noturno multiplicado por horas trabalhadas em horário diurno.

Apontar como `Erro de Cálculo` com a demonstração: "Soma das rubricas X+Y+Z = R$ A, total declarado R$ B, diferença R$ A-B".
