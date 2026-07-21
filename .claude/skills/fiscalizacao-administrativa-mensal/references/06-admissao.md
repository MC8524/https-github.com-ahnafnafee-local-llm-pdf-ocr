# 06 — Documentos de admissão

Aplicável a todo trabalhador admitido no mês ou nos meses imediatamente anteriores cujo registro ainda não tenha sido apresentado.

## Documentos esperados

| Documento | Obrigatório | Observação |
|---|---|---|
| Evento de admissão no eSocial (S-2200) | Preferencial | Traz todas as informações necessárias (admissão, jornada, salário, dependentes, opção pelo VT, etc.). |
| CTPS assinada | Alternativa | Aceita quando o eSocial não estiver disponível ou completo. |
| Ficha de registro de empregado | Sim | Documento interno da empresa, com dados pessoais e funcionais. |
| ASO admissional | Sim | Atestado de Saúde Ocupacional, com data de exame e aptidão declarada. |
| Declaração de opção pelo vale-transporte | Condicional | Quando o trabalhador opta por receber VT (com desconto). |

## Validações de conteúdo

### eSocial / CTPS

- **Data de admissão**: deve ser coerente com a planilha de movimentação.
- **Função/cargo**: deve corresponder ao posto previsto no contrato.
- **Salário inicial**: deve ser pelo menos o piso da categoria (CCT) ou o salário-mínimo nacional, o que for maior. Verificar adicionais devidos por insalubridade/periculosidade já no registro.
- **Jornada**: coerente com a escala do contrato.
- **Tomador de serviço**: HC-UFPE / EBSERH (CNPJ correto).

### Ficha de registro

- Dados pessoais completos (RG, CPF, endereço, dependentes).
- Assinaturas (empregado e empregador).
- Coerência com eSocial/CTPS.

### ASO admissional

- Data anterior ao início efetivo das atividades.
- Identificação do médico do trabalho (nome, CRM).
- Aptidão expressa.
- Riscos ocupacionais avaliados.

### Opção pelo vale-transporte

- Assinada pelo trabalhador.
- Indicação de adesão ou renúncia.
- Quando há adesão, indicação dos meios de transporte e valor diário.

## Saída desta fase

Para cada admissão:

| CPF | Nome | Data admissão | Documento | Status |
|---|---|---|---|---|

Status usando termos diretos: `OK`, `Falta`, `Não Assinado`, `Ilegível`, `Vencido` (no caso de ASO com data muito anterior ao início), `Salário Abaixo do Piso`, etc.
