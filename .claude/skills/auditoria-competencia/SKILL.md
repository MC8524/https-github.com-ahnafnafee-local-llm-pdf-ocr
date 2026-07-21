---
name: auditoria-competencia
description: "Skill mestre da Central de Fiscalização. Orquestra a auditoria completa de uma competência de contrato terceirizado: executa em sequência a fiscalização administrativa mensal (8 fases), a consolidação do relatório SEI e, se houver não conformidade, a notificação SEI, montando a pasta auditoria/ com todos os produtos. Use SEMPRE que o usuário pedir para \"auditar a competência\", \"rodar a auditoria\", \"processar a competência\", \"rodar a central\", \"fiscalização completa do mês\", ou apontar uma pasta de competência (entrada/) para processar. Ative também com frases curtas como \"audite 2026-06 do contrato 12/2024\" ou \"roda tudo nessa pasta\"."
---

# Auditoria de Competência — Skill Mestre (Fase 0 da Central de Fiscalização)

Esta skill encadeia os três robôs existentes em um fluxo único. Ela NÃO substitui
as skills especializadas; ela as aciona na ordem certa e organiza as saídas na
pasta `auditoria/` da competência. As regras de mérito (competências, tomador,
marcadores, estilo SEI) continuam sendo as das skills especializadas:

1. `fiscalizacao-administrativa-mensal` — o motor de análise (Fases 1 a 8)
2. `modificar-relatorio-sei-fiscalizacao` — o detalhamento do relatório
3. `notificacao-sei` — a minuta de notificação, quando houver não conformidade

## Princípios (herdados e inegociáveis)

- **Rascunho, não decisão.** Todos os produtos são minutas para revisão do fiscal.
  Nunca apresentar um resultado como definitivo ou pronto para assinatura.
- **Fato com fonte.** Toda afirmação objetiva registra documento, página/seção e
  grau de confiança em `evidencias.md`.
- **Sem alucinação de valor.** Valor, data ou número que não conste dos documentos
  não entra no texto; entra como placeholder entre colchetes com pedido de confirmação.
- **OCR só quando necessário.** Testar se o PDF é pesquisável antes; PDF nativo
  nunca passa por OCR. Para digitalizados, usar o pipeline deste repositório
  (`uv run main.py <arquivo> <saida>`) ou pdfplumber conforme o ambiente.
- **Sem travessões, sem juridiquês, sem fechos** em qualquer texto produzido.

## Entrada esperada

O usuário aponta uma competência, por nome ("2026-06 do contrato 12/2024") ou por
pasta. A estrutura esperada é a do `central-fiscalizacao/README.md`:

```
Contrato NN-AAAA — Empresa X/
├── config.yaml        ← dados fixos do contrato (LER SEMPRE PRIMEIRO)
└── AAAA-MM/
    ├── entrada/       ← pacote da competência
    └── auditoria/     ← esta skill cria e preenche
```

Se `config.yaml` não existir, oferecer criá-lo a partir de
`central-fiscalizacao/modelo-contrato/config.yaml`, extraindo o que for possível
dos documentos e perguntando o restante ao usuário ANTES de iniciar a análise.

## Fluxo de execução

Executar as etapas em ordem, salvando cada produto na pasta `auditoria/` assim que
ficar pronto (não acumular tudo para o final). Anunciar brevemente a etapa em curso.

### Etapa 0 — Contexto do contrato
Ler `config.yaml`: CNPJ tomador correto, CCT e benefícios, categorias
(mensalistas x diaristas), notificações anteriores e pendências abertas.
Esses dados alimentam todas as etapas seguintes e NÃO devem ser perguntados
de novo ao usuário.

### Etapa 1 — Inventário e mapa de competências → `01-mapa-competencias.md`
Aplicar a Fase 1 da skill `fiscalizacao-administrativa-mensal`: listar todos os
arquivos de `entrada/`, identificar tipo e competência declarada de cada um,
confrontar com a regra (salário e benefícios em M-1; DCTFWeb e FGTS Digital em M-2),
verificar CNPJ tomador. Registrar também: PDFs digitalizados que precisarão de OCR
e documentos esperados que faltam. Se houver documento de competência ou empresa
errada, sinalizar no mapa e seguir com o restante.

### Etapa 2 — OCR seletivo
Somente para os PDFs marcados como digitalizados na Etapa 1. Guardar as versões
pesquisáveis em `auditoria/ocr/` sem alterar os originais de `entrada/`.

### Etapa 3 — Análise completa (Fases 2 a 7 da fiscalização mensal)
Executar a skill `fiscalizacao-administrativa-mensal` de ponta a ponta:
- Checklist documental → `02-checklist-documental.xlsx` (marcadores específicos:
  Falta, Não Assinado, Ilegível, Competência Incorreta, Tomador Incorreto,
  Erro de Cálculo, Valor Divergente)
- Movimentação, folha (grupos sequenciais de 10 trabalhadores, sem pedir
  confirmação entre grupos), fiscais (DCTFWeb, FGTS Digital, DARF), documentos
  individuais de admissão/rescisão/férias quando houver evento
- Planilha de casamento → `03-planilha-casamento.xlsx`, a partir do template
  `templates/planilha-casamento-fiscalizacao.xlsx` da skill de fiscalização
- Durante toda a etapa, alimentar `evidencias.md` no formato
  Informação / Localização / Confiança

### Etapa 4 — Classificação e consolidação → `04-achados.md`
Consolidar os achados por bloco temático (remuneração, benefícios, FGTS e
previdência, movimentação de pessoal, documentos individuais), classificando cada
bloco em exatamente um de três estados:

- **Conforme** — nenhuma diligência sobre o tema e a verificação fechou.
- **Ressalva** — pendência sanável (documento faltante, assinatura ausente),
  com sugestão de prazo de diligência para o fiscal decidir.
- **Não conformidade** — divergência de valor, tomador incorreto, pagamento a
  menor, descumprimento de prazo da IN 05/2017.

Cruzar com `pendencias_abertas` do config.yaml: pendência de mês anterior que
continua sem solução é agravante e deve constar do bloco correspondente.

### Etapa 5 — Relatório SEI → `05-Relatorio_SEI_MODIFICADO.html`
Executar a skill `modificar-relatorio-sei-fiscalizacao` sobre o HTML base presente
em `entrada/` (se não houver HTML base, avisar e entregar o detalhamento em HTML
avulso no mesmo padrão de classes SEI):

- Blocos **Conformes** saem em redação final, no texto padrão de regularidade
  (caso simples). Não gerar pergunta nem placeholder para eles.
- Blocos com **Ressalva** saem redigidos com a pendência descrita e o trecho que
  depende de decisão do fiscal destacado em `<span style="background-color:#fff3cd;">`.
- Blocos de **Não conformidade** seguem o caso complexo: cronologia exata a partir
  dos e-mails (datas e horários do Outlook são a fonte da verdade), valores com
  fonte, decisões da Fiscalização.

### Etapa 6 — Notificação (condicional) → `06-notificacao-rascunho.html`
Somente se houver bloco de Não conformidade. Executar a skill `notificacao-sei`,
usando `notificacoes_anteriores` do config.yaml para decidir entre estrutura
completa (reincidência, com contextualização) ou enxuta (apontamento isolado).

### Etapa 7 — Fechamento
1. Conferir que `auditoria/` contém todos os produtos aplicáveis e que
   `evidencias.md` cobre os valores citados no relatório.
2. Propor ao usuário as atualizações do `config.yaml` (novas pendências abertas,
   notificação emitida, pendência sanada), mas SÓ gravar após confirmação.
3. Entregar um resumo final curto: estado de cada bloco (conforme / ressalva /
   não conformidade), o que exige decisão do fiscal e o que falta a empresa enviar.

## Saída padrão da pasta auditoria/

```
auditoria/
├── 01-mapa-competencias.md
├── 02-checklist-documental.xlsx
├── 03-planilha-casamento.xlsx
├── 04-achados.md
├── 05-Relatorio_SEI_MODIFICADO.html
├── 06-notificacao-rascunho.html   (condicional)
├── evidencias.md
└── ocr/                            (condicional)
```

## O que esta skill NÃO faz

- Não envia nada ao SEI, por e-mail ou a terceiros.
- Não altera os arquivos de `entrada/`.
- Não conclui pela aplicação de sanção; aponta os fatos e a classificação,
  a decisão é do fiscal.
