@echo off
REM ============================================================
REM  processar_pasta.bat
REM  Duplo-clique neste arquivo para processar uma pasta cheia
REM  de PDFs (contracheques, comprovantes, DCTF, etc.)
REM
REM  Pre-requisito: LM Studio aberto com o modelo carregado
REM  e o Local Server em http://localhost:1234/v1
REM ============================================================

cd /d "%~dp0"

echo.
echo === FiscalDocAI - Processador de PDFs ===
echo.
echo Antes de comecar, confirme:
echo   1) O LM Studio esta ABERTO?
echo   2) O modelo esta CARREGADO?
echo   3) O Local Server foi INICIADO (botao Start Server)?
echo.
pause
echo.

uv run processar_pasta.py %*

echo.
echo Pronto. Pressione qualquer tecla para sair.
pause >nul
