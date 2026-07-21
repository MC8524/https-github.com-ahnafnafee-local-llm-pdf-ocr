# 11 — Uso da skill no Claude

Esta skill é portável (markdown puro + um xlsx) e roda em qualquer LLM que aceite contexto de instruções. Esta seção descreve a forma específica de uso no Claude e o ganho prático em cada etapa da fiscalização.

## Onde colocar a skill no Claude

O Claude tem três níveis de uso natural para esta skill:

### 1. Como Skill instalada (recomendado para uso recorrente)

No claude.ai (web ou app), instalar a skill via Settings → Skills, apontando para o `.skill` empacotado (gerado a partir desta pasta). A partir daí, a skill fica disponível em qualquer conversa: o Claude consulta a `SKILL.md` automaticamente quando a descrição do frontmatter casar com a pergunta do usuário.

Vantagem: zero esforço por conversa. O usuário só envia o pacote da empresa e diz a competência.

### 2. Em um Projeto dedicado por contrato

Criar um Projeto no claude.ai por contrato em fiscalização (ex.: "Fiscalização Mensal — Contrato 14/2022 — SOLL"), e colar o conteúdo da SKILL.md (ou anexar o `.skill`) nas instruções do Projeto. Anexar também documentos contratuais e CCT aplicável.

Vantagem: mantém o histórico mensal acumulado por contrato, evita confundir documentos entre contratos.

### 3. Como anexo de uma conversa pontual

Em conversa avulsa, anexar `SKILL.md` (e referências relevantes) como arquivo no chat. Funciona, mas perde o ganho de ativação automática.

## Como ativar a skill em conversa

Frases típicas que o Claude reconhece (graças aos gatilhos na descrição da skill):

- "Vou iniciar a fiscalização do mês de [competência] do contrato XX/AAAA."
- "Segue o pacote da empresa Y para a competência MM/AAAA, faça a fiscalização."
- "Fiscalização mensal — competência abril/2026 — SOLL."
- "Casamento da folha com o FGTS Digital."
- "Conferir DCTFWeb e DARF da competência X."

Frases mais curtas como "fiscalização do mês" também devem ativar.

## Prompts típicos por fase

### Início do mês — pacote completo

> Segue o pacote da [empresa] para a competência [MM/AAAA] do Contrato [XX/AAAA]. Faça a fiscalização administrativa mensal completa conforme a skill.

A partir disso, o Claude deve seguir as oito fases.

### Foco em uma fase específica

> Para o pacote já enviado, faça só a Fase 5 (documentos fiscais), com saída em tabela.

### Cruzamento ad hoc

> Para a folha já analisada, gere a planilha de casamento (Fase 7) preenchida.

### Diligência

> Com base nos achados, redija a diligência à empresa em estilo formal e plano, sem fechos nem assinaturas.

## O que esperar como saída

Ao acionar a skill com o pacote completo, a saída ideal vem na ordem:

1. Tabela de competências dos documentos (Fase 1).
2. Checklist documental por categoria (Fase 2).
3. Análise da movimentação (Fase 3).
4. Extração da folha por trabalhador, em grupos de 10 (Fase 4).
5. Análise dos documentos fiscais (Fase 5).
6. Análise dos documentos individuais (Fase 6, quando houver).
7. Planilha de casamento preenchida (Fase 7).
8. Lista classificada de achados (Fase 8).

## Diferença prática que a skill faz na fiscalização

Sem a skill, cada conversa começa do zero: o usuário precisa relembrar a estrutura, repetir convenções (termos de status, regra de competências, formato de evidência), e fazer follow-up para corrigir omissões. Com a skill, ganha-se:

1. **Ordenação automática do trabalho.** O Claude segue as oito fases sem precisar ser lembrado. Isso reduz erros por pular etapas (ex.: começar a cruzar dados antes de validar competências).

2. **Convenções estáveis.** Termos como `Falta`, `Não Assinado`, `Competência Incorreta`, `Tomador Incorreto` ficam padronizados entre meses e contratos. Isso facilita comparação histórica e geração de despachos com vocabulário consistente.

3. **Captura das regras-chave.** Pontos como "FGTS Digital vem de M − 2", "leitura na página Relação de Categorias", "VT só com desconto ≤ 6%", "pagamento de férias até 2 dias antes do gozo", "prazo de 3 dias úteis do Anexo XII item 12" entram no contexto sem precisar ser repetidos.

4. **Saída em formato pronto para o SEI.** A redação respeita o estilo já definido (sem travessões, sem fechos, sem juriquês), o que reduz reedição manual antes de assinar.

5. **Planilha de casamento padronizada.** O template xlsx + a descrição das colunas garante que a fiscalização de janeiro tenha a mesma estrutura da de dezembro, e do contrato A tenha a mesma estrutura do contrato B. Isso reduz custo de revisão e abre caminho para acumular base histórica.

6. **Redução de alucinação.** A skill obriga a citar fonte (página/seção) e a separar fato literal de interpretação. Isso protege contra extrações inventadas, particularmente sensíveis em fiscalização (um valor errado num achado vira retrabalho ou prejuízo à empresa).

7. **Portabilidade.** Como é markdown + xlsx, a mesma skill pode ser usada em outras IAs (ChatGPT com Custom GPT, Gemini com Gem, qualquer LLM com system prompt) com adaptações mínimas. O conhecimento operacional não fica preso a uma ferramenta.

## Quando a skill NÃO se aplica

- Fiscalização técnica (verificação de execução em campo) e não administrativa.
- Análise de termos contratuais (aditivos, reajustes) sem componente de obrigações mensais.
- Pareceres jurídicos pontuais que extrapolam o ciclo mensal.

Nesses casos, usar outros recursos. Esta skill é específica para o ciclo mensal de obrigações trabalhistas, previdenciárias e fiscais.

## Atualizações futuras

A skill é viva. Sempre que um padrão novo aparecer (ex.: empresa que entrega em formato diferente, novo código de receita, mudança de CCT), atualizar a referência correspondente e empacotar nova versão. O frontmatter da `SKILL.md` deve continuar com gatilhos abrangentes para garantir ativação.
