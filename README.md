# Express Purchase Tracker
![CI/CD](https://github.com/rafaelnicodemrn/Express-purchase-tracker/actions/workflows/ci-cd.yml/badge.svg)

Aplicação interna de gestão de pedidos de compras, com backend em **FastAPI** (Python) e frontend em **Svelte 5** (Vite). Pedidos com valor estimado acima de R$ 5.000,00 disparam uma notificação assíncrona para a diretoria.

## Stack

| Camada   | Tecnologia                     | Porta padrão |
|----------|--------------------------------|--------------|
| Backend  | Python 3.11+, FastAPI, SQLite  | 8000         |
| Frontend | Svelte 5, Vite 8               | 5173 (dev)   |
| Banco    | SQLite (`backend/compras.db`)  | —            |

## Como rodar localmente

### Backend

```bash
pip install -r backend/requirements.txt
cd backend
uvicorn main:app --reload --port 8000
```

A API estará disponível em `http://localhost:8000`, com documentação interativa em `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

O frontend estará disponível em `http://localhost:5173` e consumirá a API em `http://localhost:8000/pedidos`.

### Sistema completo (Windows)

```bash
.\iniciar_sistema.bat
```

### Testes do backend

```bash
cd backend
pytest tests/ -v --cov=main --cov-report=term-missing
```

### Build de produção do frontend

```bash
cd frontend
npm run build
```

O build gerado em `frontend/dist/` é servido pelo FastAPI via `StaticFiles` na rota `/`.

## Endpoints

| Método | Rota                     | Descrição                                                                                          |
|--------|--------------------------|----------------------------------------------------------------------------------------------------|
| POST   | `/pedidos`               | Cria novo pedido                                                                                   |
| GET    | `/pedidos`               | Lista pedidos (filtros opcionais via query params: `setor`, `urgencia`, `comprado`)                |
| GET    | `/pedidos/resumo`        | Retorna resumo agregado: total de pedidos, valor total pendente, contagem por urgência e por setor |
| PUT    | `/pedidos/{id}`          | Atualiza um pedido existente                                                                       |
| PUT    | `/pedidos/{id}/concluir` | Marca pedido como comprado                                                                         |
| DELETE | `/pedidos/{id}`          | Remove pedido                                                                                      |
| GET    | `/docs`                  | Swagger UI (gerado automaticamente pelo FastAPI)                                                   |
