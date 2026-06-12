# CLAUDE.md — Express Purchase Tracker

> Arquivo de instrução para o Claude Code. Leia este arquivo inteiro antes de executar qualquer ação no projeto.

---

## 1. Visão Geral do Projeto

**Express Purchase Tracker** é uma aplicação interna de gestão de pedidos de compras.

| Camada     | Tecnologia                        | Porta padrão |
|------------|-----------------------------------|--------------|
| Backend    | Python 3.11+, FastAPI, SQLite     | 8000         |
| Frontend   | Svelte 5, Vite 8                  | 5173 (dev)   |
| Banco      | SQLite (`backend/compras.db`)     | —            |

---

## 2. Estrutura de Pastas Autorizada

```
express-purchase-tracker/          ← raiz do projeto
├── CLAUDE.md                      ← este arquivo
├── iniciar_sistema.bat            ← script de inicialização (Windows)
│
├── backend/                       ✅ ESCOPO PRINCIPAL
│   ├── main.py                    ← entrypoint FastAPI
│   ├── compras.db                 ← banco SQLite (gerado em runtime)
│   ├── requirements.txt           ← dependências Python
│   └── tests/
│       └── test_main.py           ← testes pytest
│
├── frontend/                      ✅ ESCOPO PRINCIPAL
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── svelte.config.js
│   ├── jsconfig.json
│   └── src/
│       ├── main.js
│       ├── App.svelte
│       └── lib/                   ← componentes reutilizáveis
│
└── .github/
    └── workflows/
        └── ci-cd.yml              ← pipeline CI/CD (GitHub Actions)
```

### ❌ Pastas FORA do escopo — não acesse, não modifique

- `node_modules/` — gerenciado pelo npm, nunca editar manualmente
- `frontend/dist/` — artefato de build, gerado automaticamente
- `backend/compras.db` — banco de dados de runtime, não versionar
- Qualquer pasta fora da raiz do projeto acima mapeada
- Arquivos de sistema operacional (`.DS_Store`, `Thumbs.db`, etc.)
- Diretórios temporários ou de cache (`.vite/`, `__pycache__/`, `.pytest_cache/`)

---

## 3. Regras de Trabalho

### 3.1 Antes de qualquer mudança
- Leia os arquivos relevantes antes de editar
- Nunca assuma o conteúdo de um arquivo sem lê-lo primeiro
- Se um arquivo não existir ainda, pergunte antes de criar fora da estrutura autorizada

### 3.2 Backend (Python/FastAPI)
- Entrypoint: `backend/main.py`
- Inicialização do banco: função `iniciar_db()` dentro do próprio `main.py`
- ORM: **não há** — uso direto de `sqlite3` com context manager
- Padrão de conexão: sempre usar `with sqlite3.connect("compras.db") as conn:`
- Nunca usar `conn.close()` explícito (context manager garante isso)
- Logging: usar o logger configurado (`logger = logging.getLogger(__name__)`)
- Notificações de alto valor: via `BackgroundTasks` do FastAPI (padrão já implementado)
- CORS: configurado para `allow_origins=["*"]` — não alterar sem autorização explícita

### 3.3 Frontend (Svelte/Vite)
- Framework: **Svelte 5** (sintaxe runes: `$state`, `$derived`, `$effect`)
- Bundler: Vite 8
- Sem roteador instalado — adicionar apenas se solicitado explicitamente
- CSS: sem framework instalado (plain CSS ou inline) — não instalar Tailwind sem autorização
- Build de produção: `npm run build` → gera `frontend/dist/` (consumido pelo FastAPI via `StaticFiles`)

### 3.4 Integração Backend ↔ Frontend
- O frontend em produção é servido pelo FastAPI via `StaticFiles` na rota `/`
- Em desenvolvimento, frontend roda em `:5173` e backend em `:8000`
- Requisições de API do frontend devem apontar para `/pedidos` (relativo em prod, `http://localhost:8000/pedidos` em dev)

### 3.5 CI/CD
- Pipeline: GitHub Actions (`.github/workflows/ci-cd.yml`)
- Trigger: push e pull_request nas branches `main` e `develop`
- Jobs obrigatórios:
  1. `lint-backend` — ruff + verificação de imports
  2. `test-backend` — pytest com coverage mínimo de 80%
  3. `build-frontend` — npm ci + npm run build
  4. `deploy` — executado apenas em push para `main` (requer secrets configurados)
- Nunca modificar o workflow sem entender o impacto nos jobs downstream

---

## 4. Modelo de Dados

### Tabela `pedidos`

| Coluna          | Tipo    | Restrições              |
|-----------------|---------|-------------------------|
| id              | INTEGER | PK, AUTOINCREMENT       |
| item            | TEXT    | NOT NULL                |
| quantidade      | INTEGER | NOT NULL, > 0           |
| urgencia        | TEXT    | NOT NULL (Alta/Normal/Baixa) |
| preco_estimado  | REAL    | NOT NULL                |
| setor           | TEXT    | NOT NULL                |
| comprado        | BOOLEAN | NOT NULL, DEFAULT 0     |
| data_criacao    | TEXT    | NOT NULL (YYYY-MM-DD)   |

---

## 5. Endpoints Existentes

| Método | Rota                         | Descrição                          |
|--------|------------------------------|------------------------------------|
| POST   | `/pedidos`                   | Cria novo pedido                   |
| GET    | `/pedidos`                   | Lista todos os pedidos             |
| PUT    | `/pedidos/{id}/concluir`     | Marca pedido como comprado         |
| DELETE | `/pedidos/{id}`              | Remove pedido                      |
| GET    | `/docs`                      | Swagger UI (FastAPI automático)    |

**Regra de negócio crítica:** pedidos com `preco_estimado * quantidade > 5000` disparam notificação assíncrona para diretoria via `BackgroundTasks`.

---

## 6. Comandos de Referência

```bash
# Backend — instalar dependências
pip install -r backend/requirements.txt

# Backend — rodar em desenvolvimento
cd backend && uvicorn main:app --reload --port 8000

# Backend — rodar testes
cd backend && pytest tests/ -v --cov=main --cov-report=term-missing

# Frontend — instalar dependências
cd frontend && npm ci

# Frontend — rodar em desenvolvimento
cd frontend && npm run dev

# Frontend — build de produção
cd frontend && npm run build

# Iniciar sistema completo (Windows)
.\iniciar_sistema.bat
```

---

## 7. Convenções de Código

- Python: PEP 8, type hints obrigatórios em funções novas, docstrings em funções públicas
- Svelte: componentes em PascalCase, arquivos `.svelte`
- Commits: padrão Conventional Commits (`feat:`, `fix:`, `ci:`, `test:`, `docs:`, `refactor:`)
- Nenhuma credencial, senha ou token deve ser inserida em código — usar variáveis de ambiente ou GitHub Secrets

---

## 8. O que NÃO fazer

- ❌ Não instalar novas dependências sem listar no `requirements.txt` ou `package.json`
- ❌ Não alterar a estrutura do banco sem criar migração documentada
- ❌ Não comentar ou remover o middleware CORS sem autorização
- ❌ Não versionar `compras.db`, `node_modules/` ou `frontend/dist/`
- ❌ Não usar `print()` no backend — use sempre `logger`
- ❌ Não acessar a internet durante testes (use mocks para chamadas externas futuras)
- ❌ Não criar arquivos fora da estrutura de pastas mapeada na seção 2
