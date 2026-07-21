# Caso complexo — competência com apontamento, notificação ou tratativas

Use este modelo quando, durante a competência, houve apontamento da Fiscalização, notificação à contratada, troca de manifestações ou pagamento complementar. O DETALHAMENTO precisa contar essa história em ordem cronológica, com datas, valores e decisões registrados de forma clara.

## Estrutura padrão

A seção fica organizada assim (a numeração X.Y é gerada automaticamente pelas classes `Item_Nivel2` e `Item_Nivel3`):

```
5. DETALHAMENTO
   5.1. Parágrafo introdutório (o que foi identificado)
       5.1.1. Tabela do apontamento principal (com valor pago, valor devido e diferença)
       5.1.2. Tabela do apontamento secundário, se houver
   5.2. Histórico das tratativas com a contratada
       5.2.1. Primeira interação (data + ato)
       5.2.2. Segunda interação ...
       5.2.X. Última interação (encerramento, comprovação do pagamento, com valor)
   5.3. Observação desta Fiscalização (destaque amarelo) — posição de mérito
   5.4. Providência adicional (destaque amarelo) — investigação retroativa, encaminhamentos
       5.4.1. Sub-providência (também em amarelo, se necessário)
```

## Princípios da redação

1. **Cronologia exata.** Use as datas e horários do Outlook como fonte da verdade. Se manhã e tarde do mesmo dia tiveram dois e-mails distintos, registre os dois (ex.: "em 20/05/2026, pela manhã, esta Fiscalização rebateu..."; "ainda em 20/05/2026, ao final da tarde, a empresa esclareceu...").

2. **Cite documentos pelo nome.** "Notificação SEI nº NN/AAAA", "Ofício nº XXX/AAAA", "e-mail de DD/MM/AAAA". Isso ancora o relatório nos autos.

3. **Mostre os valores.** Em casos de pagamento a menor, sempre incluir uma tabela com **valor pago**, **valor devido** e **diferença**. Se houve dedução de PAT (Programa de Alimentação do Trabalhador, 20%), informe o valor bruto e o líquido.

4. **Posição de mérito vai no destaque amarelo.** A "Observação desta Fiscalização" no item 5.3 é onde se firma a posição: por que o argumento da empresa não procede, qual a base legal/convencional. Use vocabulário claro, sem juridiquês. Frase típica boa: *"O suposto reequilíbrio econômico-financeiro alegado pela contratada não se sobrepõe à necessidade legal de a empresa cumprir os direitos trabalhistas das funcionárias."*

5. **Apuração retroativa, quando cabível.** Se o apontamento mostra um padrão (a empresa adota uma sistemática de cálculo que pode estar errada há tempos), use o item 5.4 para anunciar que a Fiscalização fará apuração retroativa "desde o início do contrato", com escopo claro (ex.: "feriados e também sábados e domingos efetivamente trabalhados").

## Snippets HTML prontos

### 5.1 Parágrafo introdutório

```html
<p class="Item_Nivel2" style="text-align:justify">
  <span style="font-family:Calibri;font-size:medium;">
    Na competência <strong>[MÊS/ANO]</strong>, durante a conferência dos
    comprovantes de [vale-alimentação / cesta básica / salário / etc.]
    encaminhados pela contratada, foram identificados pagamentos a menor
    para [algumas funcionárias / determinado posto], em quantidade
    inferior aos dias efetivamente trabalhados, conforme apurado pelas
    folhas de ponto.
  </span>
</p>
```

### 5.1.X Tabela de apontamento (formato com 7 colunas para benefício por dia)

```html
<p class="Item_Nivel3" style="text-align:justify; margin-left:40px">
  <span style="font-family:Calibri;font-size:medium;">
    <strong>Vale-alimentação pago em quantidade inferior aos dias trabalhados ([CATEGORIA]):</strong>
  </span>
</p>

<table border="1" style="border-collapse:collapse; border-color:#3b68b9; margin-left:auto; margin-right:auto; width:90%;">
  <thead>
    <tr>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Funcionária</strong></p></th>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Cargo</strong></p></th>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Dias pagos</strong></p></th>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Valor pago</strong></p></th>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Dias devidos</strong></p></th>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Valor devido</strong></p></th>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Diferença</strong></p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p class="Tabela_Texto_Centralizado">[NOME]</p></td>
      <td><p class="Tabela_Texto_Centralizado">[CARGO]</p></td>
      <td><p class="Tabela_Texto_Centralizado">[NN]</p></td>
      <td><p class="Tabela_Texto_Centralizado">R$ [VALOR]</p></td>
      <td><p class="Tabela_Texto_Centralizado">[NN]</p></td>
      <td><p class="Tabela_Texto_Centralizado">R$ [VALOR]</p></td>
      <td><p class="Tabela_Texto_Centralizado">R$ [VALOR]</p></td>
    </tr>
    <tr style="background-color:#f2f2f2;">
      <td colspan="6"><p class="Tabela_Texto_Alinhado_Esquerda"><strong>Total da diferença apontada</strong></p></td>
      <td><p class="Tabela_Texto_Centralizado"><strong>R$ [TOTAL]</strong></p></td>
    </tr>
  </tbody>
</table>
```

### 5.1.X Tabela de apontamento mensal (sem coluna de dias)

Use quando o benefício é mensal (cesta básica) e a diferença está em valor, não em dias:

```html
<table border="1" style="border-collapse:collapse; border-color:#3b68b9; margin-left:auto; margin-right:auto; width:85%;">
  <thead>
    <tr>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Funcionária</strong></p></th>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Cargo</strong></p></th>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Valor creditado</strong></p></th>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Valor devido</strong></p></th>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Diferença</strong></p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p class="Tabela_Texto_Centralizado">[NOME]</p></td>
      <td><p class="Tabela_Texto_Centralizado">[CARGO]</p></td>
      <td><p class="Tabela_Texto_Centralizado">R$ [VALOR]</p></td>
      <td><p class="Tabela_Texto_Centralizado">R$ [VALOR]</p></td>
      <td><p class="Tabela_Texto_Centralizado">R$ [VALOR]</p></td>
    </tr>
  </tbody>
</table>
```

### 5.2 Cabeçalho do histórico de tratativas

```html
<p class="Item_Nivel2" style="text-align:justify">
  <span style="font-family:Calibri;font-size:medium;">
    <strong>Histórico das tratativas com a contratada:</strong>
  </span>
</p>
```

### 5.2.X Cada item da cronologia (um parágrafo por evento)

```html
<p class="Item_Nivel3" style="text-align:justify; margin-left:40px">
  <span style="font-family:Calibri;font-size:medium;">
    Em <strong>[DD/MM/AAAA]</strong>, [descrição do que ocorreu: quem
    fez o quê, com qual base, qual o documento citado].
  </span>
</p>
```

Eventos típicos para listar (em ordem):

1. Pedido inicial de esclarecimentos da Fiscalização.
2. Primeira resposta da empresa (explicação do cálculo, eventual reconhecimento parcial).
3. Encaminhamento da Notificação SEI à empresa (citar número).
4. Apresentação do Ofício da empresa em resposta à notificação (citar número e argumento central).
5. Manhã do dia X: Fiscalização rebate e pergunta se o Ofício é a manifestação final.
6. Tarde do mesmo dia X: empresa esclarece e informa que valores serão encaminhados para pagamento.
7. Dia Y: encaminhamento dos comprovantes complementares, com valor bruto, dedução do PAT (se houver) e valor líquido.

### 5.3 Observação desta Fiscalização (destaque amarelo SÓ no texto)

```html
<p class="Item_Nivel2" style="text-align:justify">
  <span style="background-color:#fff3cd;">
    <span style="font-family:Calibri;font-size:medium;">
      <strong>Observação desta Fiscalização:</strong>
      O suposto reequilíbrio econômico-financeiro alegado pela
      contratada <strong>não se sobrepõe à necessidade legal</strong>
      de a empresa cumprir os direitos trabalhistas das funcionárias,
      pagando integralmente o [benefício] pelos dias efetivamente
      trabalhados. O benefício é direito do trabalhador e não pode
      ser suprimido, reduzido ou condicionado à medição ou
      faturamento do contrato. Os encargos trabalhistas decorrentes
      da execução contratual permanecem sob responsabilidade exclusiva
      da contratada, na condição de empregadora.
    </span>
  </span>
</p>
```

**Pontos a observar nesse trecho:**

- O `background-color` está no `<span>` interno, NÃO no `<p>`. Isso é o que faz a numeração (5.3.) ficar sem fundo amarelo.
- Não use `border-left` nem outras "barras laterais". Só o preenchimento `#fff3cd`.
- A frase de abertura **suposto** é importante: indica que a Fiscalização não está reconhecendo o reequilíbrio como real, apenas referindo-se ao argumento da empresa.

### 5.4 Providência adicional — investigação retroativa (destaque amarelo SÓ no texto)

```html
<p class="Item_Nivel2" style="text-align:justify">
  <span style="background-color:#fff3cd;">
    <span style="font-family:Calibri;font-size:medium;">
      <strong>Providência adicional:</strong> Embora a discussão no
      presente apontamento tenha se concentrado [no recorte aplicável,
      ex.: nos feriados], esta Fiscalização conduzirá <strong>apuração
      retroativa desde o início do contrato</strong> até a presente data,
      com o objetivo de verificar se o pagamento do [benefício] foi
      realizado corretamente em todas as competências anteriores. A
      verificação irá alcançar não apenas [recorte original, ex.: os
      feriados], mas também os <strong>sábados e domingos efetivamente
      trabalhados</strong>, uma vez que tais dias não podem ser excluídos
      do cômputo do benefício quando houver prestação de serviço
      registrada na folha de ponto.
    </span>
  </span>
</p>
```

### 5.4.1 Sub-item da providência (também em amarelo)

```html
<p class="Item_Nivel3" style="text-align:justify; margin-left:40px">
  <span style="background-color:#fff3cd;">
    <span style="font-family:Calibri;font-size:medium;">
      Os resultados dessa apuração serão objeto de relatório específico,
      com eventual solicitação de pagamento complementar retroativo, caso
      confirmadas as diferenças.
    </span>
  </span>
</p>
```

## Erros recorrentes a evitar

- **Confundir cronologia** (ex.: dizer que a empresa "esclareceu" antes da Fiscalização rebater, quando foi o contrário).
- **Usar "diaristas" para telefonistas** (telefonistas no contrato típico são mensalistas).
- **Dizer "não há que se falar em reequilíbrio"** (juridiquês). Prefira: *"o suposto reequilíbrio... não se sobrepõe à necessidade legal..."*.
- **Atribuir à empresa argumentos que ela não fez** (ex.: dizer que a empresa "alegou exclusão de sábados e domingos" se ela só falou em feriados). A iniciativa de investigar sábados/domingos é da Fiscalização, não decorrência do que a empresa disse.
- **Aplicar `background-color` no `<p>`** com a classe `Item_NivelX` (a numeração fica amarela junto). Sempre envolva o texto em `<span>`.
- **Usar travessões** (— ou –) em frases redigidas. Reescreva com vírgulas, parênteses ou ponto-e-vírgula.
