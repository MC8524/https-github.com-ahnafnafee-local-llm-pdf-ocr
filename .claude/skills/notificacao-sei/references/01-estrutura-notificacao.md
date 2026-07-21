# 01 — Estrutura da notificação

Detalhamento dos blocos da notificação, na ordem em que aparecem.

## Visão geral

A notificação SEI é dividida em blocos visuais e textuais bem definidos. Nem toda notificação tem todos os blocos; o critério é a finalidade.

| # | Bloco | Sempre presente | Observação |
|---|---|---|---|
| 1 | Cabeçalho do órgão | Gerado pelo SEI | Não escrever no HTML. |
| 2 | Tabela de identificação | Sim | Contrato, Empresa, Objeto, Assunto. |
| 3 | Caixa "PONTOS IRREGULARES" | Em notificações contundentes | Suprimir em apontamento simples. |
| 4 | Parágrafo introdutório com verbo de notificação | Sim | Com "NOTIFICA"/"REGISTRA"/"ADVERTE" em negrito. |
| 5 | Seção 1 — Contextualização / Histórico | Só em reincidência | Suprimir quando for primeira notificação. |
| 6 | Seção 2 — Fatos verificados | Sim | Datas, números, evidências. |
| 7 | Seção 3 — Fundamentação legal | Sim | IN 05/2017, CLT, CCT, cláusulas contratuais. |
| 8 | Seção 4 — Providências requeridas | Sim | O que a empresa deve fazer. |
| 9 | Caixa de prazo (vermelha) | Sim | Prazo em destaque, com data ou prazo em dias. |
| 10 | Bloco de ciência | Em notificações que precisam de assinatura física | Tabela com campos para data, hora, nome, assinatura. |
| 11 | Referência ao processo | Sim | `Processo nº ... SEI nº ...` |

## Detalhamento por bloco

### Bloco 2 — Tabela de identificação

Sempre 80% de largura, centralizada. Campos típicos:

| Campo | Conteúdo |
|---|---|
| CONTRATO Nº | Número/ano do contrato. |
| EMPRESA CONTRATADA | Razão social completa em caixa alta. |
| CNPJ | Quando relevante destacar. |
| OBJETO | Resumo do objeto contratual em uma linha. |
| ASSUNTO | Resumo do que a notificação trata, em uma frase técnica. |

O campo ASSUNTO é o mais importante: descreve em uma frase o que a notificação faz. Exemplos:

- "Descumprimento reiterado das obrigações de qualidade e completude da documentação mensal fiscalizatória e de atendimento tempestivo às diligências da Fiscalização."
- "Apresentação de Planilha de Movimentação de Pessoal com substituições não justificadas e ausência de CPF do substituído."
- "Recolhimento de FGTS em atraso na competência [MM/AAAA] e ausência de comprovante de transferência bancária no prazo do Anexo XII, item 12, da IN 05/2017."

### Bloco 3 — Caixa "PONTOS IRREGULARES E PROVIDÊNCIAS REQUERIDAS"

Faixa em destaque (fundo cinza claro ou azul-claro), título em caixa alta, centralizado. Funciona como rótulo do bloco textual que vem em seguida. Pode ser suprimida em notificações curtas; aí o título da seção 1 já cumpre o papel.

### Bloco 4 — Parágrafo introdutório

Sempre traz o nome do órgão (forma curta, já que o cabeçalho gerado pelo SEI já traz a forma longa), a unidade fiscalizadora e o verbo de notificação em negrito.

Exemplo:

> O Hospital das Clínicas da UFPE — HC-UFPE/EBSERH, por meio de sua Fiscalização Administrativa, **NOTIFICA** essa empresa acerca do [resumo do motivo].

Substituir o travessão (—) por vírgula ou parênteses no texto real, conforme regra de estilo.

### Bloco 5 — Contextualização / Histórico (só em reincidência)

Resume o histórico de notificações anteriores e advertências já feitas, para deixar claro que a presente notificação é parte de um padrão. Estrutura típica:

- Itens 1.1 a 1.3.
- 1.1: lista notificações/ofícios anteriores com referência abreviada (a primeira menção pode trazer o caminho completo).
- 1.2: relembra que a empresa já foi advertida de que a reincidência implicaria sanção.
- 1.3: anuncia que a presente notificação registra a persistência do padrão.

Suprimir este bloco quando a notificação é a primeira sobre o assunto.

### Bloco 6 — Fatos verificados

Coração da notificação. Estrutura típica:

- Item de nível 1 em caixa alta com fundo cinza: "DOS FATOS VERIFICADOS NA COMPETÊNCIA DE [MM/AAAA]".
- Itens 2.1, 2.2, 2.3... com fatos específicos, cada um com:
  - O fato (em frase enxuta).
  - A evidência (página do PDF, número do documento, data).
  - O efeito (qual obrigação foi descumprida).

Detalhar quando o fato é grave; ser breve quando é apontamento simples. Não inventar fatos; cada item precisa ter respaldo no documento que a fiscalização analisou.

### Bloco 7 — Fundamentação legal e contratual

Item de nível 1: "DA FUNDAMENTAÇÃO LEGAL E CONTRATUAL".

Listar:

- Dispositivos da IN 05/2017 aplicáveis (Anexos VIII-B, XI, XII conforme o caso).
- Dispositivos da CLT (quando se tratar de obrigação trabalhista).
- Cláusulas do contrato (com número da cláusula).
- Trechos da CCT aplicável (quando se tratar de benefício ou piso de categoria).

Para cada dispositivo, citação curta e remissão ao número. Evitar transcrição de artigos longos.

### Bloco 8 — Providências requeridas

Item de nível 1: "DAS PROVIDÊNCIAS REQUERIDAS" ou "DA PROVIDÊNCIA REQUERIDA".

Lista numerada (4.1, 4.2, ...) com o que a empresa deve fazer. Cada providência é uma ação concreta, verificável, com prazo se diferente do prazo geral da notificação. Verbos no imperativo formal: "Apresentar", "Comprovar", "Promover", "Encaminhar", "Adotar", "Cessar".

### Bloco 9 — Caixa de prazo (vermelha)

Caixa em destaque com borda e/ou fundo vermelho (`#c0392b` ou borda vermelha com fundo claro), conteúdo centralizado, com:

- O prazo (em dias úteis ou corridos, conforme o caso).
- A data-limite quando puder ser calculada (ex.: "até 30/05/2026").
- A advertência sobre as consequências da inobservância (instauração de processo de apuração de responsabilidade, glosa, aplicação de penalidade contratual).

### Bloco 10 — Ciência

Tabela final com campos para o responsável da empresa registrar recebimento físico. Inclui:

- Frase de ciência: "Recebi a primeira via em ___/___/___ às ___:___ horas".
- Campo: "Nome do responsável pela empresa".
- Campo: "Assinatura".
- Observação: "Poderá ser considerada a confirmação do recebimento via e-mail."

Suprimir quando a notificação é enviada exclusivamente por SEI/e-mail e o protocolo eletrônico já cumpre a função de ciência.

### Bloco 11 — Referência

Linha final, em negrito ou em bloco simples:

> **Referência:** Processo nº [NÚMERO] SEI nº [NÚMERO]

## Variantes de estrutura

### Estrutura completa (notificação contundente / reincidência)

Blocos 2, 3, 4, 5, 6, 7, 8, 9, 10, 11. É o padrão para casos como descumprimento reiterado, falhas estruturais, abertura iminente de processo de apuração.

### Estrutura média (apontamento com fundamentação)

Blocos 2, 4, 6, 7, 8, 9, 11. Suprime contextualização (não há reincidência) e ciência física (tramitação só por SEI).

### Estrutura enxuta (registro simples de ocorrência)

Blocos 2, 4, 6, 8, 9, 11. Para apontamentos isolados, sem fundamentação legal extensa, com providência simples (ex.: refazer planilha com campo faltante).

## Como decidir qual variante usar

- Se há reincidência documentada → estrutura completa.
- Se é a primeira ocorrência mas o fato é grave (FGTS não recolhido, salário não pago) → estrutura média ou completa.
- Se é apontamento simples sanável (assinatura faltando, página cortada) → estrutura enxuta.
