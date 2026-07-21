# 05 — Uso da skill no Claude e portabilidade

Como acionar esta skill no Claude e como adaptá-la para outras IAs.

## Onde colocar a skill no Claude

### 1. Skill instalada (recomendado)

Instalar o `.skill` empacotado em Settings → Capabilities → Skills. A partir daí, a skill ativa automaticamente em qualquer conversa quando o usuário diz frases como "faz uma notificação", "redige notificação para a empresa X", "notificação SEI".

### 2. Anexada a um Projeto

Criar um Projeto para o ciclo de notificações (ex.: "Notificações Fiscalização Administrativa") e colar o conteúdo da SKILL.md nas instruções do Projeto. Anexar também notificações já enviadas como referência (memória do Projeto).

### 3. Anexo de conversa pontual

Em conversa avulsa, anexar `SKILL.md` e referências como arquivos no chat. Funciona, mas exige reanexar a cada conversa nova.

## Frases que ativam a skill

A descrição no frontmatter casa com frases como:

- "Faz uma notificação para a empresa X sobre o atraso no FGTS."
- "Redige uma notificação SEI no padrão de sempre."
- "Notificação para o contrato 17/2025 — apontamento de planilha de movimentação com falhas."
- "Quero uma minuta de notificação para apurar [fato]."
- "Notificação contundente para reincidência de [tema]."
- "Registro de ocorrência para [empresa]."

## Prompts típicos

### Notificação completa (com contexto fornecido)

> Faz uma notificação para a SOLL, Contrato 17/2025, sobre o descumprimento de prazo de comprovação dos recolhimentos da competência [MM/AAAA]. É reincidência. As anteriores foram Notificação SEI nº 16/2025 e Notificação SEI nº 2/2026. Prazo de 5 dias úteis. Estrutura completa.

### Notificação simples

> Notificação enxuta para [empresa] sobre o envio da planilha de movimentação sem CPF dos substituídos na competência [MM/AAAA]. Prazo de 3 dias úteis.

### A partir de documento

> Segue o pacote da empresa Y para a competência [MM/AAAA]. Identifique os apontamentos e redija a notificação no formato da skill.

A skill, nesse último caso, articula com a skill de fiscalização administrativa mensal (quando ambas estiverem instaladas): a de fiscalização identifica os achados, esta de notificação redige o documento.

## O que esperar como saída

Arquivo HTML único em `outputs/`, com:

- DOCTYPE HTML 4.01 + CSS no `<head>`.
- Estrutura conforme a finalidade escolhida.
- Placeholders entre colchetes para tudo que depende de dado externo.
- Mensagem curta listando o que ainda precisa ser preenchido antes de colar no SEI.

## Como colar no SEI

1. Abrir o HTML no navegador.
2. Selecionar tudo (`Ctrl+A`).
3. Copiar (`Ctrl+C`).
4. No SEI, abrir o editor do documento (Notificação ou Ofício).
5. Colar (`Ctrl+V`).
6. Conferir visualmente:
   - Numeração dos itens (1.1, 1.2, 2.1...).
   - Tabela de identificação centralizada.
   - Caixa de prazo em destaque.
7. Editar placeholders entre colchetes manualmente.
8. Salvar e assinar.

Em alguns casos, o SEI sobrescreve parte do CSS na renderização final do PDF. Quando isso acontece, o conteúdo continua certo e a estrutura permanece, mas detalhes visuais (cinza estendendo até as bordas, aspas tipográficas em blockquotes) podem mudar. Aceitar.

## Portabilidade para outras IAs

A skill é markdown puro + HTML/CSS. Portável da seguinte forma:

### Custom GPT (ChatGPT)

1. Criar um GPT na loja.
2. Colar o conteúdo de `SKILL.md` no campo "Instructions". Se passar do limite, suprimir a seção "Mapa de referências" e enviar os arquivos `references/*.md` como **knowledge files** do GPT.
3. Enviar `templates/notificacao-modelo.html` também como knowledge file.
4. Em uso, o GPT consulta os knowledge files automaticamente.

### Gem do Gemini

Mesma estratégia do Custom GPT.

### Copilot Studio

Mesma estratégia, com a particularidade de o knowledge ir em uma seção específica de "Sources".

### Sistema próprio com API

Concatenar `SKILL.md` no `system` da chamada. Referências e template podem entrar como contexto inicial (em uma chamada com prompt fixo) ou como tool/RAG quando a integração permitir.

### Outra IA com persona

Colar o conteúdo de `SKILL.md` na persona/system prompt.

## Diferença prática que a skill faz

Sem skill, cada nova notificação reabre as mesmas discussões:

- "Qual o padrão de cabeçalho mesmo?"
- "A numeração 1.1, 2.1 fica certa ou quebra?"
- "Onde a caixa vermelha entra?"
- "Pode usar travessão? E o 'Atenciosamente'?"
- "Como cito o ofício anterior?"

Com a skill, esses pontos estão fixados. Cada nova notificação parte do template e do estilo já validados. Ganha-se:

1. **Tempo na redação.** O texto vem pronto com a estrutura correta.
2. **Consistência visual.** Todas as notificações saem com a mesma cara (tabelas 80%, line-height 1.4, caixas azul/vermelha, numeração funcionando).
3. **Consistência redacional.** Tom uniforme, sem travessões, sem fechos, com referências SEI abreviadas conforme regra.
4. **Menor retrabalho no SEI.** O HTML cola limpo, sem precisar mexer em formatação depois.
5. **Histórico replicável.** O padrão fica documentado; se outra pessoa da equipe precisar redigir, segue a mesma referência.

## Atualizações futuras

Quando surgir uma situação nova (novo verbo de notificação, novo tipo de bloco, mudança em IN ou CCT), atualizar o arquivo de referência correspondente e empacotar nova versão. Manter os gatilhos do frontmatter abrangentes para garantir ativação.
