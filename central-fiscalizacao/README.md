# Central de Fiscalização

Programa único que consolida os robôs de fiscalização administrativa de contratos
com dedicação exclusiva de mão de obra (IN 05/2017): fiscalização mensal em 8 fases,
relatório SEI e notificação SEI, com OCR local para PDFs digitalizados.

**Estado atual: Fase 0** — orquestração via skill mestre, sem código novo.
Você aponta a pasta `entrada/` de uma competência e a skill executa os três robôs
em sequência, montando a pasta `auditoria/` completa.

## Como usar (Fase 0)

1. Monte a estrutura de pastas do contrato seguindo o modelo em `modelo-contrato/`:

   ```
   Fiscalização/
   └── Contrato NN-AAAA — Empresa X/
       ├── config.yaml          ← copie de modelo-contrato/config.yaml e preencha
       └── AAAA-MM/             ← uma pasta por competência
           ├── entrada/         ← pacote recebido da empresa (PDFs, planilhas, e-mails)
           └── auditoria/       ← criada pela skill (resultado)
   ```

2. Numa conversa do Claude (Claude Code ou Projeto com as skills anexadas), diga:

   > Audite a competência 2026-06 do Contrato 12-2024

   ou aponte diretamente a pasta:

   > Rode a auditoria na pasta "Fiscalização/Contrato 12-2024 — Empresa Alfa/2026-06"

3. A skill mestre (`.claude/skills/auditoria-competencia/`) executa o fluxo completo
   e entrega a pasta `auditoria/` com:

   | Arquivo | Conteúdo |
   |---|---|
   | `01-mapa-competencias.md` | Inventário dos documentos, competência de cada um, o que falta |
   | `02-checklist-documental.xlsx` | Checklist com marcadores: Falta, Não Assinado, Tomador Incorreto... |
   | `03-planilha-casamento.xlsx` | Template oficial preenchido, uma linha por trabalhador |
   | `04-achados.md` | Achados classificados: conforme / ressalva / não conformidade |
   | `05-Relatorio_SEI_MODIFICADO.html` | Detalhamento pronto para colar no SEI |
   | `06-notificacao-rascunho.html` | Só quando houver não conformidade |
   | `evidencias.md` | Cada afirmação com fonte (documento, página, confiança) |

4. **Revise tudo antes de levar ao SEI.** O programa produz rascunhos; quem assina é o fiscal.

## Piloto

Para validar a Fase 0, escolha um contrato com **uma competência já concluída
manualmente** e rode a auditoria sobre ela. Compare o resultado da skill com a sua
análise: planilha de casamento, achados e detalhamento. As divergências alimentam
o ajuste das skills antes de avançar para a Fase 1.

## Regra de consolidação do relatório

Para cada bloco temático do detalhamento, a skill decide o tratamento:

- **Conforme** — nenhuma diligência sobre o tema e a verificação fechou: o bloco sai
  redigido em versão final, no texto padrão de regularidade.
- **Ressalva** — pendência sanável (documento faltante, assinatura ausente): bloco
  redigido com a pendência descrita e destaque amarelo pedindo decisão do fiscal.
- **Não conformidade** — divergência de valor, tomador incorreto, pagamento a menor:
  o bloco monta a cronologia das tratativas e a skill gera junto a minuta de notificação.

## Roadmap

| Fase | Entrega | Estado |
|---|---|---|
| 0 | Estrutura de pastas + `config.yaml` + skill mestre de orquestração | **Este diretório** |
| 1 | Pipeline em Python: inventário automático, OCR seletivo, análise fase a fase, planilha, relatório | Planejada |
| 2 | Interface web local (evolução do `server.py` deste repositório): contratos, progresso, tela de revisão | Planejada |
| 2.5 | **Empacotamento como programa instalável (.exe)** — ver `docs/plano-exe.md` | Planejada |
| 3 | Memória entre competências: reincidência automática, pendências que atravessam meses | Planejada |
