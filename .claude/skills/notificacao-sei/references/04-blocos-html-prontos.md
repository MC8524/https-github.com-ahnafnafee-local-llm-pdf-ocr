# 04 — Blocos HTML prontos

Snippets prontos para montar a notificação. Cada bloco é autocontido em termos de HTML; o CSS está no `<head>` do template (`templates/notificacao-modelo.html`).

## Bloco — Tabela de identificação

```html
<table class="identificacao">
  <tr class="cabecalho-tn">
    <td colspan="2">
      TERMO DE OCORRÊNCIA<br>
      REGISTRO DE OCORRÊNCIA Nº [NN]/[AAAA]/HC/UFPE — EBSERH
    </td>
  </tr>
  <tr>
    <td class="rotulo">CONTRATO Nº:</td>
    <td>[NN/AAAA]</td>
  </tr>
  <tr>
    <td class="rotulo">EMPRESA CONTRATADA:</td>
    <td>[RAZÃO SOCIAL COMPLETA EM CAIXA ALTA]</td>
  </tr>
  <tr>
    <td class="rotulo">CNPJ:</td>
    <td>[XX.XXX.XXX/XXXX-XX]</td>
  </tr>
  <tr>
    <td class="rotulo">OBJETO:</td>
    <td>[Resumo do objeto contratual em uma linha]</td>
  </tr>
  <tr>
    <td class="rotulo">ASSUNTO:</td>
    <td>[Frase técnica resumindo o que a notificação trata]</td>
  </tr>
</table>
```

Observações:
- Em notificações sem necessidade do "Termo de Ocorrência", remover a primeira linha (`tr.cabecalho-tn`).
- O CNPJ pode ser omitido quando o número do contrato já identifica a empresa nos autos.

## Bloco — Caixa rótulo "PONTOS IRREGULARES E PROVIDÊNCIAS REQUERIDAS"

```html
<table class="caixa-cinza-rotulo">
  <tr>
    <td>PONTOS IRREGULARES E PROVIDÊNCIAS REQUERIDAS</td>
  </tr>
</table>
```

## Bloco — Parágrafo introdutório

```html
<p class="Texto_Justificado">
  O Hospital das Clínicas da UFPE (HC-UFPE/EBSERH), por meio de sua Fiscalização Administrativa, <strong>NOTIFICA</strong> essa empresa acerca [do/da] [resumo do motivo], conforme verificado na análise da documentação da competência [MM/AAAA].
</p>
```

## Bloco — Seção com itens numerados

```html
<p class="Item_Nivel1">DA CONTEXTUALIZAÇÃO: HISTÓRICO REITERADO DE IRREGULARIDADES</p>

<p class="Item_Nivel2">
  A empresa [RAZÃO SOCIAL] já foi notificada formalmente, em mais de uma oportunidade, acerca de [tema], conforme registrado na <strong>Notificação SEI nº [NN]/[AAAA]/UFAC/SAD/DAF/GAD/HC-UFPE-EBSERH</strong> e na <strong>Notificação SEI nº [NN]/[AAAA]</strong>, vinculadas ao Contrato nº [NN/AAAA].
</p>

<p class="Item_Nivel2">
  As referidas notificações apontaram, com clareza, o padrão de [tipo de falha], bem como o descumprimento de prazos fixados pela Fiscalização para regularização das pendências. A empresa foi expressamente advertida de que a reincidência implicaria adoção de medidas administrativas sancionadoras.
</p>

<p class="Item_Nivel2">
  A presente notificação destina-se a registrar que, não obstante as advertências formais já expedidas, o padrão de falhas <strong>persiste</strong> na execução do Contrato nº [NN/AAAA], conforme descrito nos itens seguintes.
</p>
```

A numeração (1, 1.1, 1.2, 1.3) é gerada automaticamente pelas classes CSS; não escrever os números no HTML.

## Bloco — Fato verificado com incisos romanos

```html
<p class="Item_Nivel1">DOS FATOS VERIFICADOS NA COMPETÊNCIA DE [MM/AAAA]</p>

<p class="Item_Nivel2">
  <strong>[Título curto do fato em negrito]:</strong> [descrição do fato em prosa, com data, número de documento, página, e o efeito sobre a obrigação].
</p>

<p class="Item_Inciso_Romano">[Primeiro detalhamento, complementação ou evidência específica].</p>
<p class="Item_Inciso_Romano">[Segundo detalhamento].</p>
<p class="Item_Inciso_Romano">[Terceiro detalhamento].</p>

<p class="Item_Nivel2">
  <strong>[Próximo fato]:</strong> [descrição].
</p>
```

## Bloco — Fundamentação legal

```html
<p class="Item_Nivel1">DA FUNDAMENTAÇÃO LEGAL E CONTRATUAL</p>

<p class="Item_Nivel2">
  Conforme o item 12 do Anexo XII da Instrução Normativa nº 5/2017 — SEGES/MPDG, a contratada deve apresentar, no prazo de 3 (três) dias úteis, comprovante das transferências bancárias relativas aos recolhimentos das obrigações trabalhistas e previdenciárias.
</p>

<p class="Item_Nivel2">
  A Cláusula [N] do Contrato nº [NN/AAAA] estabelece, em consonância com a referida IN, que [síntese da cláusula].
</p>

<p class="Item_Nivel2">
  O descumprimento dessas obrigações, conforme prevê a Cláusula [N] do contrato, sujeita a contratada a [tipo de penalidade], sem prejuízo da abertura de processo administrativo de apuração de responsabilidade.
</p>
```

## Bloco — Providências requeridas

```html
<p class="Item_Nivel1">DAS PROVIDÊNCIAS REQUERIDAS</p>

<p class="Item_Nivel2">
  Apresentar, no prazo desta notificação, [documento específico] referente à competência [MM/AAAA].
</p>

<p class="Item_Nivel2">
  Comprovar o recolhimento de [tributo/contribuição] da competência [MM/AAAA], com cópia do DARF e do comprovante de transferência bancária.
</p>

<p class="Item_Nivel2">
  Apresentar manifestação formal sobre [fato], esclarecendo [pontos específicos].
</p>
```

## Bloco — Caixa de prazo (vermelha)

```html
<table class="caixa-vermelha">
  <tr>
    <td>
      PRAZO PARA RESPOSTA: [X] DIAS ÚTEIS, A CONTAR DO RECEBIMENTO DESTA NOTIFICAÇÃO.<br>
      DATA-LIMITE: [DD/MM/AAAA].<br>
      O DESCUMPRIMENTO DO PRAZO ENSEJARÁ A ABERTURA DE PROCESSO ADMINISTRATIVO DE APURAÇÃO DE RESPONSABILIDADE.
    </td>
  </tr>
</table>
```

Variantes:

- Prazo em dias corridos: substituir "DIAS ÚTEIS" por "DIAS CORRIDOS".
- Sem advertência de processo: remover a última linha.
- Com data certa (sem dias): "DATA-LIMITE: [DD/MM/AAAA], às 18 horas".

## Bloco — Caixa azul (diretriz/requisito)

```html
<table class="caixa-azul">
  <tr>
    <td>
      [Texto da diretriz, requisito ou ponto que merece destaque mas não é prazo crítico. Útil para reforçar instrução específica que a empresa deve seguir no atendimento da notificação.]
    </td>
  </tr>
</table>
```

## Bloco — Ciência (recebimento físico)

```html
<table class="ciencia">
  <tr>
    <td>
      <p class="Texto_Justificado">
        Estou ciente do conteúdo desta notificação e do prazo que terei para cumprir com as exigências aqui registradas.
      </p>
      <p class="Texto_Justificado">Recebi a primeira via em ___/___/_____ às ____:____ (hora).</p>
      <p class="Texto_Justificado">Nome do responsável pela empresa: _________________________________________</p>
      <p class="Texto_Justificado">Assinatura: __________________________________________________________________</p>
      <p class="Texto_Justificado"><em>Poderá ser considerada a confirmação do recebimento via e-mail.</em></p>
    </td>
  </tr>
</table>
```

CSS associado:

```css
table.ciencia {
  border-collapse: collapse;
  border: 1px solid #808080;
  width: 100%;
  margin: 18px 0;
}
table.ciencia td {
  border: 1px solid #808080;
  padding: 12pt 14pt;
  background-color: #fafafa;
}
```

## Bloco — Referência ao processo

```html
<p class="Texto_Justificado" style="margin-top: 24pt;">
  <strong>Referência:</strong> Processo nº [NÚMERO] SEI nº [NÚMERO]
</p>
```

## Bloco — Placeholder de assinatura eletrônica (opcional)

Geralmente o SEI gera; manter como placeholder ajuda na visualização:

```html
<p class="Texto_Justificado" style="margin-top: 18pt;">
  Documento assinado eletronicamente por [NOME], [CARGO], em [DATA], conforme horário oficial de Brasília, com fundamento no art. 6º, caput, do Decreto nº 8.539, de 8 de outubro de 2015.
</p>
```

## Ordem de montagem

Ao gerar uma notificação completa, montar nesta ordem:

1. Tabela de identificação.
2. (Opcional) Caixa rótulo "PONTOS IRREGULARES".
3. Parágrafo introdutório com verbo de notificação.
4. (Opcional) Seção 1 — Contextualização.
5. Seção 2 — Fatos.
6. Seção 3 — Fundamentação.
7. Seção 4 — Providências.
8. Caixa de prazo (vermelha).
9. (Opcional) Caixa azul com diretriz.
10. (Opcional) Bloco de ciência.
11. (Opcional) Bloco de assinatura eletrônica.
12. Referência ao processo.
