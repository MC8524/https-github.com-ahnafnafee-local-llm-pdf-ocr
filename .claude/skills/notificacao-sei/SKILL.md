---
name: notificacao-sei
description: "Gera notificações administrativas no padrão SEI (Sistema Eletrônico de Informações) usado por órgãos públicos federais brasileiros (EBSERH, HC-UFPE e similares), em formato HTML pronto para colar no editor do SEI. Use SEMPRE que o usuário mencionar notificação, notificar empresa, registro de ocorrência, termo de ocorrência, ofício de notificação, fiscalização que vai notificar contratada, ou quando pedir minuta/redação de notificação para empresa contratada. Ative também com frases curtas como \"faz uma notificação\", \"redige uma notificação para a empresa X\", \"notificação no modelo de sempre\", \"notificação SEI\". A skill define a estrutura (identificação, contextualização, fatos, fundamentação, providências, prazo, ciência), as classes HTML oficiais do SEI (Item_Nivel1, Item_Nivel2, Item_Inciso_Romano), o padrão visual (line-height 1.4, tabelas 80% centralizadas, caixas de destaque azul e vermelha), e o estilo redacional formal e plano sem travessões nem fechos."
---

# Notificação Administrativa no Padrão SEI

Esta skill produz notificações administrativas no formato usado por fiscalizações de contratos em órgãos públicos federais (EBSERH, HC-UFPE e similares), em HTML pronto para colar no editor do SEI. Cobre desde a estrutura de blocos até as classes CSS oficiais do SEI e o estilo redacional formal.

## Princípios fundamentais

1. **Saída em HTML, não em DOCX.** O SEI tem editor próprio que aceita HTML colado. A saída padrão da skill é HTML autocontido (CSS inline ou em `<style>` no `<head>`), pronto para `Ctrl+C` na visualização do navegador e `Ctrl+V` no editor do SEI.

2. **Classes oficiais do SEI.** A numeração da notificação usa as classes `Item_Nivel1`, `Item_Nivel2` e `Item_Inciso_Romano`, com contadores CSS automáticos. NUNCA escrever os números manualmente; o CSS faz isso e mantém consistência.

3. **`counter-set`, não `counter-reset`.** Para que a numeração zere corretamente entre seções, usar `counter-set` no `Item_Nivel1` (e variações). O `counter-reset` cria escopo novo dentro do `<p>` e não afeta irmãos seguintes — bug conhecido em CSS para parágrafos sem filhos.

4. **Estilo redacional formal e plano.** Sem juriquês, sem rebuscamento. Tom firme e objetivo quando o caso é de descumprimento reiterado. Tom técnico e neutro quando é apontamento isolado.

5. **Sem travessões (—).** Usar vírgulas ou parênteses. Esta é regra fixa, não preferência opcional.

6. **Sem fechos, assinaturas ou identificação de unidade.** O SEI gera automaticamente o bloco "Documento assinado eletronicamente por ..." e o rodapé. Não escrever "Atenciosamente", nem nome, nem cargo, nem unidade no fim do corpo da notificação.

7. **Referências SEI: completa só na primeira menção.** A primeira citação a um ofício/notificação/processo traz o caminho completo (ex.: "Ofício SEI nº 190/2024/UFAC/SAD/DAF/GAD/HC-UFPE-EBSERH"). Da segunda menção em diante, usar forma curta (ex.: "Ofício SEI nº 190/2024").

8. **Caixas de destaque com semântica fixa.** Caixa azul-claro (`#f7f9fc`) para diretrizes e requisitos importantes a chamar atenção do leitor. Caixa vermelha (`#c0392b`) para prazos críticos e advertências de sanção. Não misturar cores.

## Estrutura padrão da notificação

Toda notificação completa segue esta ordem de blocos. Detalhamento em `references/01-estrutura-notificacao.md`.

1. **Cabeçalho do órgão** (gerado pelo SEI; não escrever).
2. **Tabela de identificação** com Contrato, Empresa, Objeto, Assunto (80% de largura, centralizada).
3. **Caixa "PONTOS IRREGULARES E PROVIDÊNCIAS REQUERIDAS"** (opcional, mas comum em notificações contundentes).
4. **Parágrafo introdutório** com verbo de notificação em negrito ("NOTIFICA").
5. **Seção 1 — Contextualização / Histórico** (quando houver reincidência, referência a notificações anteriores; em casos isolados, suprimir).
6. **Seção 2 — Fatos verificados** na competência (com datas, números, evidências).
7. **Seção 3 — Fundamentação legal e contratual** (IN 05/2017, CLT, CCT, cláusulas contratuais aplicáveis).
8. **Seção 4 — Providências requeridas** da empresa.
9. **Caixa de prazo** (vermelha) com o prazo de resposta.
10. **Bloco de ciência** (tabela com campos para data, hora, nome e assinatura do responsável).
11. **Referência ao processo** (`Processo nº ... / SEI nº ...`).

Não toda notificação tem todos os blocos. O critério é a finalidade. Para notificação de descumprimento reiterado, usar todos. Para apontamento simples, suprimir contextualização e usar estrutura mais enxuta (identificação → fatos → providências → prazo → ciência).

## Fluxo de geração

Quando acionada, a skill segue:

1. **Confirmar dados mínimos** com o usuário (ou extrair dos documentos enviados): contrato, empresa, objeto, assunto, fatos a notificar, prazo desejado, referência a notificações anteriores (se reincidência).
2. **Decidir a estrutura** (completa ou enxuta) conforme o caso.
3. **Redigir o corpo** seguindo `references/03-estilo-redacional.md`.
4. **Montar o HTML** usando os blocos prontos em `references/04-blocos-html-prontos.md` e o template `templates/notificacao-modelo.html`.
5. **Conferir checklist final** antes de entregar (ver final desta SKILL).
6. **Entregar arquivo HTML** em `outputs/`, com nome no formato `notificacao-NN-AAAA-empresa.html`.

## Saídas esperadas

- Arquivo HTML único, autocontido (CSS no `<head>`), com placeholders entre colchetes para campos que dependem do usuário ([NÚMERO DA NOTIFICAÇÃO], [PROCESSO Nº], [DATA], etc.).
- Mensagem curta indicando o que ainda falta preencher antes de colar no SEI.

## Mapa de referências

| Arquivo | Conteúdo |
|---|---|
| `references/01-estrutura-notificacao.md` | Detalhamento de cada bloco, ordem, quando usar/suprimir. |
| `references/02-padrao-html-sei.md` | Classes CSS oficiais do SEI, contadores, line-height, tabelas 80%, caixas de destaque. |
| `references/03-estilo-redacional.md` | Tom, vocabulário, referências SEI abreviadas, regra de travessões e fechos. |
| `references/04-blocos-html-prontos.md` | Snippets de HTML para colar direto: identificação, caixa de pontos, caixa de prazo, ciência. |
| `references/05-uso-com-claude.md` | Como acionar a skill no Claude, prompts típicos, portabilidade para outras IAs. |

## Template

`templates/notificacao-modelo.html` é uma notificação em branco completa, com todas as classes CSS já definidas, contadores configurados e blocos com placeholders. Para gerar uma nova notificação, partir desse template é o caminho mais rápido.

## Checklist final antes de entregar

Antes de devolver o arquivo HTML ao usuário, conferir:

- [ ] Nenhum travessão (—) no corpo do texto.
- [ ] Nenhum "Atenciosamente", nome, cargo ou unidade no fim do documento.
- [ ] Verbo de notificação ("NOTIFICA", "REGISTRA", "ADVERTE") em negrito no parágrafo introdutório.
- [ ] Referência SEI completa só na primeira menção; abreviada nas demais.
- [ ] Numeração dos itens funcionando (1.1, 1.2, 2.1, 2.2... resetando entre seções).
- [ ] Tabelas em 80% de largura, centralizadas.
- [ ] `line-height: 1.4` em todos os parágrafos do corpo.
- [ ] Caixa de prazo em vermelho, separada visualmente.
- [ ] Placeholders entre colchetes para tudo o que depende de dado externo (número, data, processo, etc.).
- [ ] Bloco "Documento assinado eletronicamente por [NOME]" presente, mas sem nome preenchido (será gerado pelo SEI).
- [ ] `Referência: Processo nº [NÚMERO] SEI nº [NÚMERO]` no fim.

Se algum item falhar, corrigir antes de devolver.
