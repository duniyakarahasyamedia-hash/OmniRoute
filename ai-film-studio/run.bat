@echo off
REM AI Film Studio launcher (Windows)
set DIR=%~dp0
if exist "%DIR%.venv\Scripts\python.exe" (
  "%DIR%.venv\Scripts\python.exe" "%DIR%run_film.py" %*
) else (
  python "%DIR%run_film.py" %*
)
