# 05 — Documentos fiscais e previdenciários

Cobre DCTFWeb, FGTS Digital, DARF, comprovantes de recolhimento e situações especiais (compensação, dedução, parcelamento, PIX).

## 1. DCTFWeb

A DCTFWeb declara as contribuições previdenciárias e outras retidas e recolhidas. O que conferir:

| Item | Como conferir |
|---|---|
| Recibo de Entrega | Conferir CNPJ, competência e status (Original/Retificadora). |
| Relação de Tomadores | Conferir se o tomador do serviço (HC-UFPE / EBSERH) aparece com o CNPJ correto. |
| Códigos de receita declarados | Verificar todos os códigos aplicáveis ao perfil da empresa e do contrato. |
| Valores declarados | Cruzar com a folha de pagamento (soma das contribuições por trabalhador). |
| Compensações / deduções | Quando houver, verificar PER/DCOMP e bases. |
| Parcelamentos | Quando houver, marcar como `ATENÇÃO` (status amarelo), não como pendência absoluta, desde que documentado. |
| Status final | DCTFWeb deve estar transmitida; retificações devem estar identificadas e justificadas. |

### Checklist específico de DCTFWeb

| Verificação | Resultado esperado |
|---|---|
| Competência confere com `M - 2` | Sim |
| CNPJ tomador correto | Sim |
| Todos os trabalhadores da folha refletidos | Sim |
| Valores fechando com folha + GFIP/eSocial | Sim |

## 2. FGTS Digital

O FGTS Digital substituiu o sistema antigo. A leitura correta usa a página **Relação de Categorias** da guia detalhada. O que conferir:

| Item | Como conferir |
|---|---|
| Competência | Conferir mês/ano de referência. |
| CNPJ do empregador e do tomador | Confirmar que o tomador é o contratante. |
| Relação de trabalhadores | Nome, CPF, categoria, base de remuneração total, valor depositado. |
| Base de remuneração total por trabalhador | Cruzar com a base do FGTS na folha. |
| Valor depositado por trabalhador | Geralmente 8% da base, salvo categorias específicas (ex.: aprendiz 2%). |
| Comprovante de recolhimento da guia | Bancário ou PIX, dentro do prazo. |
| Deduplicação | A mesma guia pode aparecer em mais de um documento (Guia + Comprovante + Extrato); contar uma vez só. |

### Página correta de extração

A relação detalhada de trabalhadores está em **"Relação de Categorias"**. Não confundir com páginas de resumo ou de totais, que omitem trabalhadores individuais.

## 3. DARF e comprovantes de recolhimento

| Item | Como conferir |
|---|---|
| Todos os códigos de receita | Verificar a presença de DARF para cada código declarado na DCTFWeb (INSS patronal, RAT, terceiros, etc., conforme perfil). |
| Valores | Confronto com os valores da DCTFWeb da mesma competência. |
| Data de pagamento | No prazo legal. |
| Comprovante bancário | Anexado ou PIX vinculado. |
| Forma de extinção | Pagamento, compensação, dedução, parcelamento. Cada forma exige documento específico. |

### Compensação / Dedução

Quando o débito foi extinto por compensação:

- Verificar PER/DCOMP correspondente.
- Conferir bases compensadas.
- O fato de não haver DARF de pagamento não é falha, desde que a PER/DCOMP esteja anexada.

### Parcelamento

Quando o débito está parcelado:

- Solicitar termo de parcelamento.
- Comprovante de pagamento das parcelas correntes.
- Status: `ATENÇÃO` (amarelo), não `PENDENTE`.

## 4. PIX e formas equivalentes

Empresas usam PIX/DARF (ex.: via Itaú) com frequência. O comprovante de PIX é válido desde que:

- Identifique o pagador (CNPJ da empresa).
- Indique o destinatário (Receita Federal ou conta da União para o tributo).
- Apresente data, valor e identificador da operação (E2E).
- Vincule-se a um DARF/guia da competência.

## 5. Prazo de apresentação dos comprovantes

Conforme **IN 05/2017, Anexo XII, item 12**, a empresa contratada deve apresentar comprovante das transferências bancárias relativas às obrigações trabalhistas em até **3 dias úteis** após a transação.

Apontamento típico: comprovante apresentado após esse prazo, com identificação da operação e da data efetiva.

## 6. Saída desta fase

Tabela consolidada:

| Documento | Competência | Status | Valor declarado | Valor pago | Forma de extinção | Observação |
|---|---|---|---|---|---|---|

Os valores devem fechar entre si (DCTFWeb x DARF x FGTS Digital x Folha). Eventuais divergências entram diretamente na seção de achados.
