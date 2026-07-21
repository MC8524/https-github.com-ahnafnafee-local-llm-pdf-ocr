# 02 — Padrão HTML/CSS do SEI

O SEI tem um conjunto de classes CSS oficiais que o seu editor reconhece quando o HTML é colado. Manter essas classes preserva a numeração automática, a formatação dos itens e a estética padrão.

## Classes oficiais

### `Item_Nivel1` — itens de primeiro nível (seções)

Aparece em caixa alta, fundo cinza claro, negrito. Funciona como cabeçalho da seção.

```css
p.Item_Nivel1 {
  text-transform: uppercase;
  font-weight: bold;
  background-color: #e6e6e6;
  font-size: 12pt;
  font-family: Calibri;
  text-align: justify;
  word-wrap: normal;
  text-indent: 0;
  margin: 12pt 0 8pt 0;
  padding: 6pt 8pt;
  line-height: 1.4;
  counter-increment: item-n1;
  counter-set: item-n2 0 romano_maiusculo 0 letra_minuscula 0;
}
p.Item_Nivel1:before {
  content: counter(item-n1) ".";
  display: inline-block;
  width: 25mm;
  font-weight: normal;
}
```

### `Item_Nivel2` — itens de segundo nível (parágrafos numerados)

```css
p.Item_Nivel2 {
  font-size: 12pt;
  font-family: Calibri;
  text-indent: 0mm;
  text-align: justify;
  word-wrap: normal;
  margin: 5pt 0;
  line-height: 1.4;
  counter-increment: item-n2;
  counter-set: romano_maiusculo 0 letra_minuscula 0;
}
p.Item_Nivel2:before {
  content: counter(item-n1) "." counter(item-n2) ".";
  display: inline-block;
  width: 25mm;
  font-weight: normal;
}
```

### `Item_Inciso_Romano` — incisos em algarismo romano maiúsculo

Para subitens dentro de um `Item_Nivel2`.

```css
p.Item_Inciso_Romano {
  font-size: 12pt;
  font-family: Calibri;
  text-align: justify;
  word-wrap: break-word;
  text-indent: 0mm;
  line-height: 1.4;
  counter-increment: romano_maiusculo;
  counter-set: letra_minuscula 0;
  margin: 4pt 0 4pt 35mm;
}
p.Item_Inciso_Romano:before {
  content: counter(romano_maiusculo, upper-roman) " - ";
  display: inline-block;
  width: 15mm;
  font-weight: normal;
}
```

### `Texto_Justificado` — parágrafo comum

Para texto introdutório ou de transição, sem numeração.

```css
p.Texto_Justificado {
  font-size: 12pt;
  font-family: Calibri;
  text-align: justify;
  line-height: 1.4;
}
```

### Inicialização dos contadores no `body`

```css
body {
  font-family: Calibri, sans-serif;
  font-size: 12pt;
  color: #000;
  margin: 0;
  padding: 20px;
  background: #f5f5f5;
  counter-reset: item-n1 item-n2 romano_maiusculo letra_minuscula;
}
```

## A diferença crítica entre `counter-reset` e `counter-set`

Bug conhecido: se usar `counter-reset` dentro de `p.Item_Nivel1` para zerar `item-n2` e `romano_maiusculo`, **não funciona**. O `counter-reset` declarado em um elemento cria um escopo **dentro daquele elemento**, e como o `<p>` não tem filhos com `counter-increment`, esse escopo fica isolado e não afeta os parágrafos irmãos seguintes.

Sintoma: numeração sai como `1.1, 1.2, 1.3, 2.4, 2.5, 2.6...` (em vez de `2.1, 2.2, 2.3`) e os romanos continuam `IV, V, VI` em vez de zerar.

Solução: usar `counter-set` (CSS Counter Styles Level 3). O `counter-set` **define o valor do contador no escopo do pai**, sem criar escopo novo. Resolve o problema.

```css
/* Errado — não zera */
counter-reset: item-n2 0 romano_maiusculo 0;

/* Certo — zera corretamente */
counter-set: item-n2 0 romano_maiusculo 0;
```

## Tabelas 80% centralizadas

Padrão visual fixo para tabelas de identificação e caixas de destaque.

```css
table.identificacao {
  border-collapse: collapse;
  border: 1px solid #1f4e78;
  width: 80%;
  margin: 0 auto 18px;
}
table.identificacao td {
  border: 1px solid #c0cbd6;
  padding: 7pt 10pt;
  vertical-align: top;
  font-family: Calibri;
  font-size: 12pt;
  background-color: #f7f9fc;
  line-height: 1.4;
}
table.identificacao td.rotulo {
  width: 26%;
  white-space: nowrap;
  font-weight: bold;
  color: #1f4e78;
  background-color: #e9f0f7;
}
table.identificacao tr.cabecalho-tn td {
  background-color: #1f4e78;
  color: #fff;
  font-weight: bold;
  text-align: center;
  letter-spacing: 0.04em;
  padding: 8pt 10pt;
  font-size: 12pt;
  border: 1px solid #1f4e78;
}
```

## Caixas de destaque

### Azul-claro (diretrizes, requisitos importantes)

```css
table.caixa-azul {
  border-collapse: collapse;
  border: 1px solid #1f4e78;
  width: 80%;
  margin: 10px auto 14px;
  font-family: Calibri;
  font-size: 12pt;
}
table.caixa-azul td {
  border: 1px solid #1f4e78;
  padding: 10pt 14pt;
  text-align: justify;
  line-height: 1.4;
  background-color: #f7f9fc;
}
```

### Vermelha (prazo crítico, advertência)

```css
table.caixa-vermelha {
  border-collapse: collapse;
  border: 2px solid #c0392b;
  width: 80%;
  margin: 14px auto 18px;
  font-family: Calibri;
  font-size: 12pt;
}
table.caixa-vermelha td {
  border: 1px solid #c0392b;
  padding: 12pt 16pt;
  text-align: center;
  line-height: 1.5;
  background-color: #fff5f3;
  color: #7a1f12;
  font-weight: bold;
}
```

### Cinza (rótulo de bloco, como "PONTOS IRREGULARES")

```css
table.caixa-cinza-rotulo {
  border-collapse: collapse;
  border: 1px solid #646464;
  width: 100%;
  margin: 10px 0;
}
table.caixa-cinza-rotulo td {
  background-color: #d9d9d9;
  padding: 8pt 12pt;
  text-align: center;
  font-weight: bold;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-size: 12pt;
  font-family: Calibri;
}
```

## Cuidados específicos do SEI

1. **O SEI tem CSS próprio na hora de gerar PDF.** Em alguns casos, sobrescreve estilos. Em particular, ele pode tratar `counter-reset` em vez de `counter-set` na hora de renderizar. Se a numeração quebrar ao colar no SEI, é provavelmente o motor antigo de CSS dele agindo. Não há solução perfeita; o padrão `counter-set` é o que funciona melhor.

2. **O SEI remove pseudo-elementos em alguns contextos.** Aspas tipográficas em `:before` e `:after` de blockquotes às vezes somem ao colar. Não depender de pseudo-elemento para conteúdo essencial.

3. **Margem negativa nem sempre sobrevive.** Se o estilo do `Item_Nivel1` usa margens negativas para o cinza "vazar" até as bordas da página, o SEI pode resetar. Aceitar o fallback (cinza só atrás do texto).

4. **Fonte padrão Calibri 12pt.** Não trocar. É o padrão visual do órgão.

5. **`line-height: 1.4` em todos os parágrafos do corpo.** Valor consagrado para boa legibilidade no SEI; 1.3 fica apertado, 1.5 fica solto demais.

## Codificação e DOCTYPE

Sempre HTML 4.01 Strict no início do documento, charset UTF-8:

```html
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html lang="pt-br">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<title>[Título da notificação]</title>
<style type="text/css">
  [CSS aqui]
</style>
</head>
<body>
[Conteúdo aqui]
</body>
</html>
```

O DOCTYPE HTML 4.01 é o que o editor do SEI processa melhor; HTML5 também funciona mas em alguns contextos o motor antigo do SEI ignora regras.
