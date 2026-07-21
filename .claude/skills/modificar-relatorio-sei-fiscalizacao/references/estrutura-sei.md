# Estrutura do HTML do relatório SEI

O template SEI usa um conjunto fechado de classes CSS que controlam numeração automática, recuos, fontes e alinhamentos. Para que o relatório editado continue parecendo um documento SEI legítimo no navegador, sempre reutilize essas classes em vez de criar estilos novos inline.

## Numeração automática

A numeração das seções (1., 1.1., 1.1.1., ...) é gerada via CSS `counter()` no pseudo-elemento `:before`. Isso significa duas coisas:

1. **Você não deve escrever a numeração no texto.** Ela aparece sozinha quando você usa a classe certa.
2. **Aplicar `background-color` diretamente no `<p class="Item_NivelX">` colore também o número.** Para evitar isso, envolva o texto em um `<span>` e aplique o `background-color` no span.

## Tabela de classes mais usadas

| Classe                                   | Usa para                                                                    |
| ---------------------------------------- | --------------------------------------------------------------------------- |
| `Item_Nivel1`                            | Título de seção principal (1., 2., ...). Fundo cinza, maiúsculas, negrito.  |
| `Item_Nivel2`                            | Subitem (1.1., 1.2., ...). Texto normal, justificado.                       |
| `Item_Nivel3`                            | Sub-subitem (1.1.1., ...). Igual ao Nivel2 mas com mais um nível de recuo.  |
| `Item_Nivel4`, `Item_Nivel5`, `Item_Nivel6` | Níveis adicionais quando necessário. Pouco usados.                       |
| `Texto_Justificado`                      | Parágrafo de texto corrido, sem numeração, justificado.                     |
| `Texto_Justificado_Recuo_Primeira_Linha` | Parágrafo justificado com indentação de 2,5cm na primeira linha.            |
| `Texto_Centralizado`                     | Parágrafo centralizado.                                                     |
| `Texto_Centralizado_Maiusculas_Negrito`  | Título centralizado, maiúsculas, em negrito (ex.: nome do relatório).       |
| `Tabela_Texto_Centralizado`              | Texto centralizado dentro de célula de tabela.                              |
| `Tabela_Texto_Alinhado_Esquerda`         | Texto à esquerda dentro de célula de tabela.                                |
| `Tabela_Texto_Alinhado_Direita`          | Texto à direita dentro de célula de tabela.                                 |

## Cabeçalho e rodapé — NÃO MEXER

O HTML começa com um bloco `<div>` que contém o timbre institucional (imagem base64), o nome do hospital e o endereço. Termina com o número do relatório SEI, a referência do processo e o número do documento. Esses blocos vêm do template do SEI e **não devem ser editados**. Mudanças aqui podem invalidar o documento.

## Cores institucionais (padrão SEI)

| Onde                                    | Cor (hex)         | Uso                                |
| --------------------------------------- | ----------------- | ---------------------------------- |
| Fundo do cabeçalho de tabela (`<th>`)   | `#d4def0`         | Azul claro institucional           |
| Borda de tabela                          | `#3b68b9`         | Azul institucional                 |
| Linha de total / destaque suave         | `#f2f2f2`         | Cinza muito claro                  |
| Destaque amarelo de observação          | `#fff3cd`         | Amarelo claro (chamar atenção)     |

**Não use vermelho (`#e74c3c`) em texto final.** O vermelho aparece em templates antigos como marcador de "preencher aqui" e deve ser sempre removido na versão final.

## Padrão de tabela usado nos relatórios

```html
<table border="1" style="border-collapse:collapse; border-color:#3b68b9;
       margin-left:auto; margin-right:auto; width:85%;">
  <thead>
    <tr>
      <th style="background-color:#d4def0;">
        <p class="Tabela_Texto_Centralizado"><strong>[CABEÇALHO]</strong></p>
      </th>
      ...
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>
        <p class="Tabela_Texto_Centralizado">[CONTEÚDO]</p>
      </td>
      ...
    </tr>
  </tbody>
</table>
```

## Padrão de destaque amarelo (item de observação)

**Errado** (colore a numeração junto):

```html
<p class="Item_Nivel2" style="background-color:#fff3cd;">
  <strong>Observação:</strong> texto...
</p>
```

**Certo** (destaca só o texto, deixa a numeração limpa):

```html
<p class="Item_Nivel2" style="text-align:justify">
  <span style="background-color:#fff3cd;">
    <span style="font-family:Calibri;font-size:medium;">
      <strong>Observação:</strong> texto...
    </span>
  </span>
</p>
```

## Hierarquia visual padrão

Mantenha:

- **Cabeçalho cinza** (Item_Nivel1) → títulos como "DETALHAMENTO", "RETENÇÃO", "CONCLUSÃO".
- **Texto normal** (Item_Nivel2) → parágrafos principais sob cada título.
- **Texto com mais recuo** (Item_Nivel3) → subitens, parágrafos de cronologia, listas detalhadas.

Não invente um Item_Nivel0 nem misture classes que não existem no `<style>` do documento — o navegador renderiza estranho.

## Verificação rápida no fim

Antes de fechar o arquivo, faça um `grep` por:

- `&mdash;` e `&ndash;` → não deve aparecer no detalhamento (são travessões).
- `background-color:#e74c3c` → não deve restar (vermelho do template antigo).
- `border-left:` em parágrafos amarelos → não deve aparecer (barra lateral indevida).
- `stratátivas`, `dispostas`, `postergação` com til errado, etc. → verificar ortografia.
