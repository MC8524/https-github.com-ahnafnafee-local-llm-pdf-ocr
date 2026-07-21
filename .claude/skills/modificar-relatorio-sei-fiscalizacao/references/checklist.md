# Checklist final — antes de entregar o relatório modificado

Antes de apresentar o arquivo modificado ao usuário, percorra cada item abaixo.

## Conteúdo

- [ ] Identifiquei corretamente o tipo de caso (simples ou complexo).
- [ ] Li todos os e-mails do processo e a cronologia está correta (datas e horários do Outlook conferidos).
- [ ] Citei nomes de documentos pelos números oficiais (Notificação SEI nº X/AAAA, Ofício nº XXX/AAAA).
- [ ] Os valores monetários conferem com os documentos (folha, comprovantes, GFD, DARF).
- [ ] Movimentações de pessoal (admissão, demissão, férias) batem com a folha e com a planilha de relação de empregados.
- [ ] Não inventei datas, valores ou afirmações que não constam dos documentos.

## Estrutura e formatação

- [ ] As classes `Item_Nivel1`, `Item_Nivel2`, `Item_Nivel3` estão sendo usadas corretamente.
- [ ] A numeração automática (gerada via CSS) está consistente.
- [ ] Não há mais nenhum fundo vermelho (`#e74c3c`) no detalhamento.
- [ ] Os destaques amarelos estão envoltos em `<span style="background-color:#fff3cd;">`, não no `<p>`.
- [ ] Não há `border-left` (barra lateral) nos parágrafos de destaque.
- [ ] Tabelas usam borda `#3b68b9` e cabeçalho `#d4def0`.

## Linguagem

- [ ] Nenhum travessão (— ou –) em texto redigido (apenas no template original, ex.: linha de assinatura do fiscal).
- [ ] Sem juridiquês: "não há que se falar em", "ad cautelam", "sem prejuízo de" reescritas em linguagem clara.
- [ ] Telefonistas, motoristas, técnicos chamados de mensalistas; só costureira(s) chamada(s) de diarista(s).
- [ ] Posição da Fiscalização aparece como "suposto reequilíbrio... não se sobrepõe à necessidade legal..." e não como negação direta.

## Preservação do template

- [ ] Cabeçalho institucional (timbre, nome do hospital, endereço) intacto.
- [ ] Número do relatório SEI no início inalterado.
- [ ] Assinatura eletrônica (nome do fiscal, cargo, unidade) intacta.
- [ ] Rodapé com referência do processo e número do documento intacto.
- [ ] Seções não relacionadas ao detalhamento (Introdução, Identificação do Contrato, Documentos Analisados, Retenção/Conta Vinculada, Processos Relacionados, Conclusão) preservadas.

## Entrega

- [ ] O arquivo foi salvo na pasta selecionada pelo usuário com nome no padrão `Relatorio_SEI_NN_MODIFICADO.html` (ou similar).
- [ ] O link `computer://...` está sendo oferecido para o usuário abrir.
- [ ] A resposta ao usuário resume em até 5 bullets o que foi alterado.

## Antes de fechar

Faça um `grep` simples no arquivo final:

```bash
grep -c "&mdash;\|&ndash;" arquivo.html        # deve dar 0 ou só ocorrências do template
grep -c "background-color:#e74c3c" arquivo.html # deve dar 0
grep -c "border-left:" arquivo.html             # deve dar 0
```

Se algum desses retornar valor inesperado, volte e corrija antes de entregar.
