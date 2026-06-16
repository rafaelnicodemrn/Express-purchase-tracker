from __future__ import annotations

import os
import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta

from fastapi import FastAPI, BackgroundTasks, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from typing import Dict, List, Literal, Optional

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── Configuração JWT ──────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "projeto2025")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

app = FastAPI(title="API Gestao de Suprimentos")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


# ── Modelos ───────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class Pedido(BaseModel):
    id: Optional[int] = None
    item: str
    quantidade: int = Field(..., gt=0)
    urgencia: Literal["Alta", "Normal", "Baixa"]
    preco_estimado: float
    setor: str
    comprado: bool = False
    data_criacao: Optional[str] = None


class ResumoPedidos(BaseModel):
    total_pedidos: int
    valor_total_pendente: float
    por_urgencia: Dict[str, int]
    por_setor: Dict[str, int]


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _criar_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """Valida o Bearer token e retorna o username. Levanta 401 em caso de falha."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")


# ── Banco de dados ────────────────────────────────────────────────────────────

def iniciar_db():
    with sqlite3.connect("compras.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT NOT NULL,
                quantidade INTEGER NOT NULL,
                urgencia TEXT NOT NULL,
                preco_estimado REAL NOT NULL,
                setor TEXT NOT NULL,
                comprado BOOLEAN NOT NULL DEFAULT 0,
                data_criacao TEXT NOT NULL
            )
        """)
        cursor = conn.cursor()
        if cursor.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0] == 0:
            dados_iniciais = [
                ("Notebook Dell Latitude", 2, "Alta", 5500.0, "TI", 0, "2023-10-24"),
                ("Cadeira Ergonomica", 5, "Normal", 1200.0, "RH", 0, "2023-10-24"),
                ("Monitor 24 polegadas", 3, "Baixa", 900.0, "Marketing", 1, "2023-10-23"),
                ("Licenca Software Adobe", 1, "Alta", 3500.0, "Design", 0, "2023-10-25"),
            ]
            conn.executemany(
                "INSERT INTO pedidos (item, quantidade, urgencia, preco_estimado, setor, comprado, data_criacao) VALUES (?,?,?,?,?,?,?)",
                dados_iniciais,
            )
            conn.commit()


iniciar_db()


# ── Background tasks ──────────────────────────────────────────────────────────

async def processar_notificacao_diretoria(item: str, valor: float):
    logger.info(f"Processando notificacao de aprovacao para o item: {item}")
    await asyncio.sleep(5)
    logger.info(f"Notificacao de aprovacao enviada. Valor total: R$ {valor:.2f}")


# ── Endpoints de autenticação ─────────────────────────────────────────────────

@app.post("/auth/login", response_model=TokenResponse)
def login(credenciais: LoginRequest):
    """Autentica o usuário e retorna um JWT com expiração de 8 horas."""
    if credenciais.username != ADMIN_USERNAME or credenciais.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    token = _criar_token(credenciais.username)
    logger.info(f"Login bem-sucedido para usuário: {credenciais.username}")
    return TokenResponse(access_token=token, token_type="bearer")


# ── Endpoints de pedidos (protegidos) ─────────────────────────────────────────

@app.post("/pedidos", response_model=Pedido)
async def criar_pedido(
    pedido: Pedido,
    background_tasks: BackgroundTasks,
    _: str = Depends(get_current_user),
):
    pedido.data_criacao = datetime.now().strftime("%Y-%m-%d")

    with sqlite3.connect("compras.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pedidos (item, quantidade, urgencia, preco_estimado, setor, comprado, data_criacao) VALUES (?,?,?,?,?,?,?)",
            (
                pedido.item,
                pedido.quantidade,
                pedido.urgencia,
                pedido.preco_estimado,
                pedido.setor,
                False,
                pedido.data_criacao,
            ),
        )
        conn.commit()
        pedido.id = cursor.lastrowid

    if (pedido.preco_estimado * pedido.quantidade) > 5000:
        background_tasks.add_task(
            processar_notificacao_diretoria,
            pedido.item,
            pedido.preco_estimado * pedido.quantidade,
        )

    return pedido


@app.get("/pedidos", response_model=List[Pedido])
def listar_pedidos(
    setor: Optional[str] = None,
    urgencia: Optional[str] = None,
    comprado: Optional[bool] = None,
    _: str = Depends(get_current_user),
) -> List[dict]:
    """Lista pedidos, com filtros opcionais por setor, urgência e status de compra."""
    query = "SELECT * FROM pedidos WHERE 1=1"
    params: list = []

    if setor is not None:
        query += " AND setor = ?"
        params.append(setor)
    if urgencia is not None:
        query += " AND urgencia = ?"
        params.append(urgencia)
    if comprado is not None:
        query += " AND comprado = ?"
        params.append(1 if comprado else 0)

    query += " ORDER BY comprado ASC, id DESC"

    with sqlite3.connect("compras.db") as conn:
        conn.row_factory = sqlite3.Row
        pedidos = conn.execute(query, params).fetchall()
        return [dict(p) for p in pedidos]


@app.get("/pedidos/resumo", response_model=ResumoPedidos)
def resumo_pedidos(_: str = Depends(get_current_user)) -> ResumoPedidos:
    """Retorna totais e contagens agregadas dos pedidos cadastrados."""
    with sqlite3.connect("compras.db") as conn:
        conn.row_factory = sqlite3.Row

        total_pedidos = conn.execute(
            "SELECT COUNT(*) AS total FROM pedidos"
        ).fetchone()["total"]

        valor_total_pendente = conn.execute(
            "SELECT COALESCE(SUM(preco_estimado * quantidade), 0) AS total "
            "FROM pedidos WHERE comprado = 0"
        ).fetchone()["total"]

        por_urgencia = {
            row["urgencia"]: row["total"]
            for row in conn.execute(
                "SELECT urgencia, COUNT(*) AS total FROM pedidos GROUP BY urgencia"
            ).fetchall()
        }

        por_setor = {
            row["setor"]: row["total"]
            for row in conn.execute(
                "SELECT setor, COUNT(*) AS total FROM pedidos GROUP BY setor"
            ).fetchall()
        }

    return ResumoPedidos(
        total_pedidos=total_pedidos,
        valor_total_pendente=valor_total_pendente,
        por_urgencia=por_urgencia,
        por_setor=por_setor,
    )


@app.put("/pedidos/{pedido_id}", response_model=Pedido)
def atualizar_pedido(
    pedido_id: int,
    pedido: Pedido,
    _: str = Depends(get_current_user),
) -> dict:
    """Atualiza os dados de um pedido existente."""
    with sqlite3.connect("compras.db") as conn:
        conn.row_factory = sqlite3.Row

        existente = conn.execute(
            "SELECT * FROM pedidos WHERE id = ?", (pedido_id,)
        ).fetchone()
        if existente is None:
            raise HTTPException(status_code=404, detail="Pedido não encontrado")

        conn.execute(
            """UPDATE pedidos
               SET item = ?, quantidade = ?, urgencia = ?, preco_estimado = ?, setor = ?, comprado = ?
               WHERE id = ?""",
            (
                pedido.item,
                pedido.quantidade,
                pedido.urgencia,
                pedido.preco_estimado,
                pedido.setor,
                pedido.comprado,
                pedido_id,
            ),
        )
        conn.commit()

        atualizado = conn.execute(
            "SELECT * FROM pedidos WHERE id = ?", (pedido_id,)
        ).fetchone()

    return dict(atualizado)


@app.put("/pedidos/{pedido_id}/concluir")
def concluir_pedido(pedido_id: int, _: str = Depends(get_current_user)):
    with sqlite3.connect("compras.db") as conn:
        conn.execute("UPDATE pedidos SET comprado = 1 WHERE id = ?", (pedido_id,))
        conn.commit()
    return {"status": "sucesso"}


@app.delete("/pedidos/{pedido_id}")
def deletar_pedido(pedido_id: int, _: str = Depends(get_current_user)):
    with sqlite3.connect("compras.db") as conn:
        conn.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
        conn.commit()
    return {"status": "sucesso"}


if os.path.isdir("../frontend/dist"):
    app.mount(
        "/", StaticFiles(directory="../frontend/dist", html=True), name="frontend"
    )
else:
    logger.warning("frontend/dist não encontrado — rodando em modo API-only")
