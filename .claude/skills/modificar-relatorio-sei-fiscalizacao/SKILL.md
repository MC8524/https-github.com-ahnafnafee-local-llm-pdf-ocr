---
name: modificar-relatorio-sei-fiscalizacao
description: Modificar relatórios de fiscalização administrativa no padrão SEI/EBSERH a partir dos documentos do processo (e-mails, notificações, ofícios, folhas de pagamento, comprovantes). Use esta skill sempre que o usuário pedir para "modificar o relatório", "atualizar o relatório SEI", "preencher o detalhamento", "fazer relatório de fiscalização administrativa do mês", "relatório da competência", ou enviar um zip de processo SEI contendo um arquivo HTML de relatório para ser editado. Também acionar quando o usuário falar sobre Notificação SEI, Ofício de contratada, vale-alimentação, cesta básica, repactuação, conta vinculada, ou outras tratativas típicas de fiscalização de contrato terceirizado, mesmo que não diga explicitamente "skill" ou "relatório".
---

# Modificar Relatório de Fiscalização Administrativa (SEI/EBSERH)

Esta skill orienta como modificar a seção DETALHAMENTO (e, quando necessário, outras seções) de relatórios de fiscalização administrativa no padrão SEI/EBSERH, mantendo a estrutura, a numeração automática e a formatação do template, com base nos documentos do processo.

## O que esta skill faz

O usuário é fiscal administrativo de contratos terceirizados de um hospital universitário (HC-UFPE/EBSERH). A cada competência ele recebe da contratada um pacote de documentos (faturamento, folha de pagamento, comprovantes de benefícios, GFD, DARF, certidões) e faz uma fiscalização documental. Ao final, gera um relatório SEI mensal. O conteúdo da seção DETALHAMENTO varia muito conforme o que aconteceu na competência:

- Se foi tudo "tranquilo" (sem apontamentos, sem notificação), o detalhamento é enxuto: apenas as movimentações de pessoal (admissões, demissões, férias) e a constatação de que a documentação está regular.
- Se houve apontamento, notificação à empresa, troca de ofícios ou tratativas, o detalhamento precisa contar essa "história", em ordem cronológica, com as datas, os valores, e as decisões da Fiscalização.

A skill ajuda a decidir qual fluxo aplicar e a redigir corretamente cada parte, preservando o HTML do template.

## Antes de começar

1. **Confirme os arquivos** que o usuário disponibilizou (geralmente um `.zip` extraído do SEI). O conjunto típico inclui:
   - Um arquivo HTML do relatório (a base a ser editada, geralmente nomeado `Relatorio___SEI_NN.html`)
   - Um ou mais PDFs de e-mails trocados com a contratada
   - PDFs de notificações ou ofícios (quando houver)
   - GFD/FGTS Digital, DARF/Receita Federal, folha de pagamento, comprovantes de vale-alimentação/cesta básica/vale-transporte
   - Planilhas (.xls) com relação de empregados
   - Certidões negativas

2. **Leia os e-mails primeiro.** Os e-mails contam a história da competência: o que a Fiscalização pediu, o que a empresa respondeu, se houve notificação, se a empresa pagou, etc. A ordem dos e-mails (datas e horários do Outlook) é a fonte da verdade para a cronologia. Quando houver dúvida sobre a sequência, releia.

3. **Pergunte ao usuário, se necessário**, qual o tipo de competência: "tranquila" (apenas confirmar regularidade) ou "com tratativas" (houve notificação/apontamento). Se houver indícios claros (existe `Notificação`, `Ofício 0XX/2026` nos anexos), assuma que é caso complexo. Em caso de dúvida, pergunte antes de redigir.

## Fluxo principal

```
Entrou pedido para modificar relatório?
        │
        ▼
Ler o HTML base + extrair texto dos PDFs (pdfplumber)
        │
        ▼
Tem notificação / ofício / apontamento nos e-mails?
        │
   ┌────┴────┐
   │         │
  SIM       NÃO
   │         │
   ▼         ▼
[Caso     [Caso
complexo]  simples]
   │         │
   └────┬────┘
        ▼
Substituir SOMENTE a seção DETALHAMENTO no HTML, preservando
todas as outras seções (Introdução, Retenção, Processos
Relacionados, Conclusão, assinatura, rodapé).
        │
        ▼
Salvar como `Relatorio_SEI_NN_MODIFICADO.html` na pasta do usuário
e oferecer o link `computer://...` para abrir no navegador.
```

## Como decidir entre caso simples e caso complexo

**Caso simples** (use `references/caso-simples.md`):
- Não houve notificação no SEI durante a competência
- Os e-mails são apenas troca de comprovantes ("segue documentação", "recebido")
- Folhas de pagamento e comprovantes batem com as folhas de ponto
- Pode ter havido movimentação de pessoal (admissão, demissão, férias) mas sem apontamento

**Caso complexo** (use `references/caso-complexo.md`):
- Foi emitida Notificação SEI ou Ofício de Apontamento à contratada
- Houve troca de manifestações (empresa enviou Ofício respondendo, Fiscalização rebateu)
- Foi identificado pagamento a menor de salário, benefício, encargo
- A contratada questionou o entendimento da Fiscalização (alegou reequilíbrio, custos, etc.)
- Há comprovantes de pagamento complementar

## Regras de redação que valem sempre

Estas regras vêm de feedback direto do usuário e devem ser respeitadas em todo relatório:

1. **Sem juridiquês excessivo.** Linguagem clara, direta, profissional, mas legível. Evite expressões como "não há que se falar em", "sem prejuízo de", "ad cautelam".

2. **Sem travessões (— ou –).** Não use em-dash nem en-dash em parágrafo redigido. Use vírgulas, parênteses, ponto-e-vírgula, dois-pontos, ou simplesmente reescreva a frase. A única exceção é o template original (assinatura do fiscal "Nome do Fiscal – Cargo"), que NÃO deve ser alterado.

3. **Preserve a estrutura SEI.** O HTML usa classes CSS que geram numeração automática (`Item_Nivel1`, `Item_Nivel2`, `Item_Nivel3`, etc.). Mantenha-as. Não altere o cabeçalho institucional, o número do relatório, a assinatura eletrônica, o rodapé.

4. **Destaque em amarelo cobre só o texto, nunca a numeração.** Quando precisar destacar uma observação importante (item 5.3, 5.4, etc.), envolva o texto em `<span style="background-color:#fff3cd;">...</span>` em vez de aplicar `background-color` no `<p>`. Isso garante que a numeração gerada via `:before` permaneça sem fundo. Não use barra lateral (`border-left`), apenas o preenchimento amarelo claro `#fff3cd`.

5. **Diaristas vs. mensalistas.** Telefonistas, motoristas, técnicos de edificação e administrativos no contrato típico do HC-UFPE são **mensalistas**. Costureira(s) são **diaristas**. Não chame todo mundo de "diarista". Quando em dúvida, releia a folha de pagamento (campo "Salário" mensal x "valor/dia").

6. **Valores e datas sempre acompanhados de fonte.** Quando citar um valor (R$), uma data, um número de notificação ou um número de ofício, confirme nos documentos. Se não tiver certeza, escreva genericamente e marque para o usuário confirmar.

7. **Cronologia exata.** Em casos complexos, a sequência dos e-mails é central. Releia os horários de envio (manhã/tarde do mesmo dia podem inverter quem rebateu quem). Em particular, lembre que a Fiscalização pode rebater uma manifestação da empresa **no mesmo dia**, e a empresa pode responder à rebatida ainda **no mesmo dia**.

## Estrutura do HTML SEI (resumo)

O relatório SEI usa estas classes CSS para numeração e estilo:

| Classe                                  | Uso                                                            |
| --------------------------------------- | -------------------------------------------------------------- |
| `Item_Nivel1`                           | Título de seção (1., 2., 3., ...) com fundo cinza e maiúsculas |
| `Item_Nivel2`                           | Subitem (X.1., X.2.)                                           |
| `Item_Nivel3`                           | Sub-subitem (X.Y.1., X.Y.2.)                                   |
| `Item_Nivel4` a `Item_Nivel6`           | Mais níveis (raramente usados)                                 |
| `Texto_Justificado_Recuo_Primeira_Linha` | Parágrafo de texto corrido com indentação                      |
| `Tabela_Texto_Centralizado`             | Texto centralizado em célula de tabela                         |
| `Tabela_Texto_Alinhado_Esquerda`        | Texto à esquerda em célula                                     |

Para detalhes do HTML, veja `references/estrutura-sei.md`.

## Próximos passos

- Para detalhar a seção quando **NÃO houve apontamento**, consulte `references/caso-simples.md`.
- Para detalhar a seção quando **houve notificação/ofício**, consulte `references/caso-complexo.md`.
- Para a tabela de classes e snippets HTML, consulte `references/estrutura-sei.md`.
- Para o checklist final antes de entregar, consulte `references/checklist.md`.
