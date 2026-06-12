@echo off
echo ===================================================
echo     Iniciando o Express Purchase Tracker...
echo ===================================================

:: Entra na pasta do backend
cd backend

:: Abre o Dashboard principal no navegador
start http://localhost:8000

:: Abre a documentacao do FastAPI em uma nova aba
start http://localhost:8000/docs

:: Liga o servidor do FastAPI
uvicorn main:app