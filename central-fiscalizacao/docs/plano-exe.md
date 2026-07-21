# Plano do instalável (.exe) — Fase 2.5

O usuário conseguiu instalar programas no PC do trabalho (o SmartScreen alertou,
mas permitiu). Portanto, além da versão "servidor local aberto no navegador"
(Fase 2), a Central de Fiscalização também será entregue como programa Windows
instalável. As duas soluções coexistem: mesmo código, dois empacotamentos.

## Estratégia

1. **Base única.** O `.exe` é o mesmo backend Python (pipeline + FastAPI) da
   Fase 2, embutido. Nenhuma funcionalidade é exclusiva de um formato.

2. **Empacotamento com PyInstaller** (`--onedir`, não `--onefile`):
   - `--onedir` inicia mais rápido e reduz falsos positivos de antivírus,
     relevante em PC corporativo.
   - O executável sobe o servidor FastAPI em `127.0.0.1` numa porta livre e abre
     a interface. Duas opções de janela:
     - **a) navegador padrão** (mais simples, zero dependência extra);
     - **b) janela própria via `pywebview`** (aparência de programa de verdade,
       como o PDF Studio). Preferência: começar com (a), adicionar (b) depois.

3. **Instalador com Inno Setup**: atalho no menu Iniciar e na área de trabalho,
   desinstalador, escolha da pasta `Fiscalização/` no primeiro uso.

4. **SmartScreen**: sem assinatura digital, o alerta aparece (como aconteceu com
   o PDF Studio) e o usuário clica em "Executar assim mesmo". Se o alerta virar
   bloqueio pela política do órgão, alternativas em ordem de custo:
   - distribuir como `.zip` portátil (sem instalador, sem SmartScreen de instalação);
   - certificado de assinatura de código (custo anual, elimina o alerta).

5. **O que NÃO vai embutido no .exe da primeira versão**:
   - O motor de OCR local (Surya + modelo de visão) pesa gigabytes. O `.exe`
     chama a API do Claude para análise e trata OCR assim:
     - PDFs nativos: extração direta (PyMuPDF, leve, já no pacote);
     - PDFs digitalizados: envio das páginas como imagem para o modelo via API.
   - O OCR local vira download opcional posterior ("componente offline"), se a
     política de dados exigir processamento 100% local.

6. **Configuração da API**: chave do Claude informada na primeira execução e
   guardada no Credential Manager do Windows (nunca em arquivo de texto).

## Critérios para começar a Fase 2.5

- Fase 1 (pipeline) validada no contrato piloto.
- Fase 2 (interface web) funcional, pois o .exe é só outro invólucro dela.
- Decisão da seção 4.3 do planejamento confirmada (API x local) para saber o que
  embutir.
