# Caso simples — competência sem apontamentos

Use este modelo quando a competência transcorreu normalmente: documentos entregues no prazo, sem divergências, sem notificação à empresa. O foco é informar **movimentações de pessoal** (admissão, demissão, férias) e confirmar que a **demais documentação está regular**.

## Estrutura da seção DETALHAMENTO

A seção fica enxuta. O esqueleto é:

1. Um parágrafo introdutório curto, dizendo que a documentação foi analisada e está regular.
2. (Se houve) Tabela de **movimentações de pessoal** (admissões e demissões).
3. (Se houve) Tabela de **férias** concedidas/iniciadas/encerradas.
4. Frase final confirmando que as demais documentações estão de acordo.

Se não houve nenhuma movimentação e nenhuma férias, escreva apenas o parágrafo introdutório e a frase final, sem tabelas.

## Snippets HTML prontos

### Parágrafo introdutório

```html
<p class="Item_Nivel2" style="text-align:justify">
  <span style="font-family:Calibri;font-size:medium;">
    Na competência <strong>[MÊS/ANO]</strong>, a documentação encaminhada
    pela contratada foi analisada e está em conformidade com o disposto
    na Instrução Normativa SEGES/MP nº 05/2017 e demais normas aplicáveis,
    não sendo identificadas divergências relativas a salários, benefícios
    ou encargos trabalhistas.
  </span>
</p>
```

### Subtítulo + tabela de admissões e demissões

```html
<p class="Item_Nivel3" style="text-align:justify; margin-left:40px">
  <span style="font-family:Calibri;font-size:medium;">
    <strong>Movimentação de pessoal na competência:</strong>
  </span>
</p>

<table border="1" style="border-collapse:collapse; border-color:#3b68b9; margin-left:auto; margin-right:auto; width:85%;">
  <thead>
    <tr>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Tipo</strong></p></th>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Funcionário(a)</strong></p></th>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Cargo</strong></p></th>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Data</strong></p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p class="Tabela_Texto_Centralizado">Admissão</p></td>
      <td><p class="Tabela_Texto_Centralizado">[NOME]</p></td>
      <td><p class="Tabela_Texto_Centralizado">[CARGO]</p></td>
      <td><p class="Tabela_Texto_Centralizado">[DD/MM/AAAA]</p></td>
    </tr>
    <tr>
      <td><p class="Tabela_Texto_Centralizado">Demissão</p></td>
      <td><p class="Tabela_Texto_Centralizado">[NOME]</p></td>
      <td><p class="Tabela_Texto_Centralizado">[CARGO]</p></td>
      <td><p class="Tabela_Texto_Centralizado">[DD/MM/AAAA]</p></td>
    </tr>
  </tbody>
</table>
```

### Subtítulo + tabela de férias

```html
<p class="Item_Nivel3" style="text-align:justify; margin-left:40px">
  <span style="font-family:Calibri;font-size:medium;">
    <strong>Férias concedidas/em curso na competência:</strong>
  </span>
</p>

<table border="1" style="border-collapse:collapse; border-color:#3b68b9; margin-left:auto; margin-right:auto; width:85%;">
  <thead>
    <tr>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Funcionário(a)</strong></p></th>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Cargo</strong></p></th>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Período aquisitivo</strong></p></th>
      <th style="background-color:#d4def0;"><p class="Tabela_Texto_Centralizado"><strong>Período de gozo</strong></p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p class="Tabela_Texto_Centralizado">[NOME]</p></td>
      <td><p class="Tabela_Texto_Centralizado">[CARGO]</p></td>
      <td><p class="Tabela_Texto_Centralizado">[DD/MM/AAAA a DD/MM/AAAA]</p></td>
      <td><p class="Tabela_Texto_Centralizado">[DD/MM/AAAA a DD/MM/AAAA]</p></td>
    </tr>
  </tbody>
</table>
```

### Parágrafo de fechamento

```html
<p class="Item_Nivel2" style="text-align:justify">
  <span style="font-family:Calibri;font-size:medium;">
    As demais documentações apresentadas pela contratada
    (folha de pagamento, comprovantes de salários e benefícios, GFD,
    DARF, certidões) foram conferidas e encontram-se regulares,
    sem pendências impeditivas para a liquidação e pagamento da
    competência.
  </span>
</p>
```

## O que NÃO incluir em caso simples

- Histórico de tratativas com a contratada (não houve)
- Tabelas de diferenças de valores (não houve)
- Bloco de observação destacado em amarelo (reserve para casos com apontamento real)
- Anúncio de investigação retroativa (não é o lugar)

## Onde encontrar as movimentações

- **Admissões/demissões:** geralmente vêm na folha de pagamento (campo "Adm:") e em comprovantes específicos enviados pela empresa. Confira pela planilha de relação de empregados (.xls).
- **Férias:** vêm em recibo de férias individual e/ou na folha de pagamento (rubrica "Férias"). Períodos costumam estar em documento próprio enviado quando a empresa vai pagar férias.

Se o documento não estiver claro, prefira não inventar período: registre apenas o que está documentado e marque para o usuário confirmar os dados antes de assinar.
