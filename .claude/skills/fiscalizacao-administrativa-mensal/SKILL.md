---
name: fiscalizacao-administrativa-mensal
description: "Conduz fiscalização administrativa mensal de contratos com dedicação exclusiva de mão de obra (IN 05/2017), em órgãos públicos federais (EBSERH, HC-UFPE e similares). Use SEMPRE que o usuário mencionar fiscalização administrativa, fiscalização mensal, análise de folha de pagamento, DCTFWeb, FGTS Digital, DARF, planilha de movimentação, casamento folha x FGTS, análise de admissão/rescisão/férias de empresa contratada, ou quando enviar pacote mensal de documentos (folha + benefícios + fiscal + trabalhista). Ative também com frases curtas como \"fiscalização do mês\", \"competência X da empresa Y\", \"análise mensal do contrato\". A skill define o passo a passo em 8 fases, a regra de competências (folha em M-1, FGTS/DCTFWeb em M-2), a estrutura da planilha de casamento e o formato de apresentação dos achados."
---

# Fiscalização Administrativa Mensal — Contratos com Dedicação Exclusiva de Mão de Obra

Esta skill orienta a fiscalização administrativa mensal de contratos de prestação continuada de serviços com dedicação exclusiva de mão de obra, no escopo da IN 05/2017 (Anexo XII). O objetivo é verificar, mês a mês, o cumprimento das obrigações trabalhistas, previdenciárias e fiscais pela empresa contratada, cruzando informações entre folha de pagamento, planilha de movimentação, documentos fiscais (DCTFWeb, FGTS Digital, DARF) e documentos individuais (admissão, rescisão, férias).

## Princípios fundamentais (não negociáveis)

Antes de qualquer análise, internalizar estes princípios:

1. **Análise fato-baseada e sem alucinação.** Trabalhar APENAS com os documentos efetivamente fornecidos na conversa em curso. Não misturar com documentos de outras conversas, salvo se o usuário pedir explicitamente. Para cada afirmação objetiva, indicar a fonte (página/seção do PDF). Separar fato literal de interpretação.

2. **Competência correta.** Cada documento se refere a uma competência específica. A regra geral é:
   - Salário e benefícios: competência do **mês imediatamente anterior** ao atual.
   - DCTFWeb e FGTS Digital: competência de **dois meses anteriores** ao atual.
   - Conferir competência antes de começar a análise. Empresas eventualmente enviam documento de outro mês, de outro contrato ou até de outra empresa por engano. Ver `references/02-regra-competencias.md`.

3. **Tomador correto.** O CNPJ tomador deve ser o do contratante (HC-UFPE / EBSERH). Existem casos em que a empresa lança trabalhadores fora do tomador correto, ou lança como tomador a própria empresa. Esses casos precisam ser identificados e questionados.

4. **Tim-tim por tim-tim.** A análise é detalhada. Não basta verificar se o documento está presente; é necessário ler conteúdo, conferir cálculos básicos (soma, multiplicação, divisão), datas, assinaturas e valores.

5. **OCR somente quando necessário.** PDFs nativos (texto pesquisável) NÃO devem passar por OCR. OCR é reservado para PDFs digitalizados (imagem). Antes de aplicar OCR, sempre testar se o PDF já é pesquisável. Ver `references/10-cuidados-praticos.md`.

6. **Marcadores de problema diretos.** Em tabelas e checklists, indicar problemas com termos específicos: `Falta`, `Não Assinado`, `Ilegível`, `Competência Incorreta`, `Tomador Incorreto`, `Erro de Cálculo`, `Valor Divergente`. Evitar "Não OK" genérico. Evitar legendas quando possível.

7. **Formato de evidência documental.** Para cada item objetivo extraído de documento, usar formato:
   - *Informação* [trecho literal ou valor exato]
   - *Localização* [página/seção do documento]
   - *Confiança* [explícito no documento / interpretação / cálculo derivado]

## Fluxo de trabalho da fiscalização mensal

Esta é a ordem padrão. Cada fase tem um arquivo de referência detalhado.

### Fase 1 — Inventário e validação de competência

1. Listar todos os documentos recebidos da empresa no pacote do mês.
2. Para cada documento, registrar competência declarada (mês/ano) e tipo.
3. Confrontar com a regra de competências esperada. Sinalizar documentos com competência incorreta antes de prosseguir.
4. Verificar se o CNPJ tomador é o correto (HC-UFPE / EBSERH conforme contrato).

Detalhamento: `references/02-regra-competencias.md`.

### Fase 2 — Checklist documental por categoria

Confrontar o pacote recebido com o checklist de documentos obrigatórios:

- **Documentação de fiscalização mensal** (folha, planilha de movimentação, comprovantes de salário, benefícios).
- **Documentação fiscal e previdenciária** (DCTFWeb, FGTS Digital, DARF, comprovantes de recolhimento, eventuais compensações/parcelamentos).
- **Documentação trabalhista individual** (admissão, rescisão, férias quando houver evento no mês).

Detalhamento: `references/01-checklist-documental.md`.

### Fase 3 — Análise da planilha de movimentação

A planilha de movimentação é a base que diz quem trabalhou no contrato no mês. Conferir:

- Lista de funcionários ativos (em curso) na competência.
- Substituições registradas: CPF do substituto, nome, motivo, prazo, natureza (definitiva ou temporária).
- Cruzamento com a folha (quem está na movimentação deve estar na folha e vice-versa, exceto nos casos justificados).
- Funcionários fora do tomador correto (alerta).

Detalhamento: `references/03-movimentacao-funcionarios.md`.

### Fase 4 — Análise da folha de pagamento e extração de dados

Para cada trabalhador da competência, extrair as colunas da planilha de casamento (ver Fase 7). Conferir também:

- Recebimento correto de salário base e adicionais (insalubridade, periculosidade, adicional noturno, hora noturna reduzida, salário-família, salário-mínimo quando piso).
- Pagamento dos benefícios devidos (vale-alimentação ou cesta básica conforme CCT, vale-transporte).
- Foco no vale-transporte: para todo trabalhador com desconto de VT em folha, deve haver concessão de VT (presume-se o pagamento ou recarga). Casos com desconto e sem benefício são divergência.
- Situação funcional declarada em folha: ativo, afastado (doença, maternidade), férias.
- Base de cálculo do INSS por trabalhador.
- Depósito de FGTS demonstrado na folha (compara com o que sai no FGTS Digital depois).

Detalhamento: `references/04-folha-pagamento.md`.

### Fase 5 — Análise da documentação fiscal e previdenciária

Conferir:

- **DCTFWeb**: declaração presente, com todos os códigos de receita esperados; relação de tomadores correta; valores fechando com a folha; status (transmitida, retificada, parcelada).
- **FGTS Digital**: guia detalhada presente, com relação de trabalhadores por competência, base de remuneração total por trabalhador, valor depositado. Página correta de extração: **Relação de Categorias**.
- **DARF e comprovantes de recolhimento**: presença para todas as competências relacionadas; valores batendo; tipo de operação (pagamento, compensação, dedução, parcelamento) devidamente comprovado.
- **PIX/transferências**: aceitar quando houver comprovante válido (ex.: PIX/DARF Itaú).
- **Comprovação dentro do prazo**: conforme IN 05/2017, Anexo XII, item 12, a contratada deve apresentar comprovante de transferência bancária das obrigações trabalhistas em até **3 dias úteis** após a operação.

Detalhamento: `references/05-documentos-fiscais.md`.

### Fase 6 — Análise dos documentos trabalhistas individuais

Para cada evento ocorrido no mês:

- **Admissão**: verificar eSocial (preferencial) ou CTPS assinada, ficha de registro de empregado, ASO admissional, opção pelo vale-transporte declarada. Ver `references/06-admissao.md`.
- **Rescisão**: TRCT, comprovante de pagamento da rescisão, GRRF (quando devida), extrato do FGTS, ASO demissional. Conferir cálculos e descontos. Ver `references/07-rescisao.md`.
- **Férias**: aviso e recibo assinados, comprovante de pagamento até 2 dias antes do início do gozo, conferência aritmética dos cálculos. Ver `references/08-ferias.md`.

### Fase 7 — Casamento e planilha final

Consolidar tudo em uma única planilha de casamento (ver template em `templates/planilha-casamento-fiscalizacao.xlsx`), com uma linha por trabalhador da competência e colunas que cruzam folha x FGTS Digital x movimentação. Identificar:

- Trabalhador em folha sem correspondência no FGTS Digital.
- Trabalhador no FGTS Digital sem correspondência na folha.
- Base de cálculo divergente entre folha e FGTS Digital.
- Trabalhador na movimentação sem registro em folha/FGTS.
- Tomador incorreto.

Detalhamento das colunas e regras: `references/09-planilha-casamento.md`.

### Fase 8 — Relatório de fiscalização

Consolidar achados em despacho ou relatório, separando:

- Achados sem ressalva (conforme).
- Achados com ressalva (pendência sanável, prazo para diligência).
- Achados de não conformidade (potencial PAAR, glosa, notificação).

A redação segue o estilo formal e plano, sem juriquês, sem travessões, sem fechos ou assinaturas (eles ficam no SEI/Outlook).

## Saídas esperadas da skill

Ao usar esta skill em uma fiscalização, a IA deve entregar, em ordem:

1. **Mapa de competências** dos documentos recebidos, sinalizando inconsistências.
2. **Checklist documental** preenchido com marcadores específicos.
3. **Análise crítica da folha**, com problemas por trabalhador (em grupos sequenciais de 10, sem pedir confirmação entre grupos).
4. **Análise da movimentação** com cruzamento contra folha.
5. **Análise dos fiscais** (DCTFWeb, FGTS Digital, DARF), com casamento de valores.
6. **Análise dos documentos individuais** (admissão/rescisão/férias) quando houver.
7. **Planilha de casamento consolidada** preenchida.
8. **Lista final de achados** classificada por gravidade.

## Como esta skill é usada no Claude

Esta skill é portável e funciona em qualquer LLM que aceite contexto de instruções. No Claude (Claude.ai / app mobile / desktop / Claude Code), a forma típica de uso é:

1. Anexar a skill ao Projeto correspondente (ex.: Projeto "Fiscalização Mensal — Contrato XX/AAAA — Empresa Z"), via "Skills" ou via instruções do Projeto.
2. Em cada conversa do mês, o usuário envia o pacote da empresa (PDFs e/ou planilhas) e diz apenas a competência. A skill ativa automaticamente o fluxo das Fases 1 a 8.
3. Para contratos diferentes, basta criar Projetos diferentes; a skill é a mesma.

Detalhes operacionais e exemplos de prompts: `references/11-uso-com-claude.md`.

## Mapa das referências detalhadas

| Arquivo | Conteúdo |
|---|---|
| `references/01-checklist-documental.md` | Lista mestre de documentos obrigatórios por categoria, com marcadores de problema. |
| `references/02-regra-competencias.md` | Regra das competências mês anterior / dois meses anteriores, exemplos e exceções. |
| `references/03-movimentacao-funcionarios.md` | Campos exigidos da planilha de movimentação, regras de substituição, casamento com folha. |
| `references/04-folha-pagamento.md` | Rubricas, situações, regras de extração para a planilha final, particularidades do VT. |
| `references/05-documentos-fiscais.md` | DCTFWeb, FGTS Digital, DARF, compensação, parcelamento, PIX, prazos. |
| `references/06-admissao.md` | Documentos e validações de admissão. |
| `references/07-rescisao.md` | Documentos, GRRF, conferência de cálculos rescisórios. |
| `references/08-ferias.md` | Documentos, prazo de pagamento, conferência aritmética. |
| `references/09-planilha-casamento.md` | Estrutura da planilha consolidada de casamento (corresponde ao template xlsx). |
| `references/10-cuidados-praticos.md` | OCR, PDF nativo vs digitalizado, tomador errado, casos limite. |
| `references/11-uso-com-claude.md` | Como acionar esta skill no Claude, prompts típicos, ganhos práticos. |

## Template

O arquivo `templates/planilha-casamento-fiscalizacao.xlsx` é um template vazio com todas as colunas da planilha final de casamento, pronto para receber os dados extraídos da competência em análise. As colunas estão descritas em `references/09-planilha-casamento.md`.
