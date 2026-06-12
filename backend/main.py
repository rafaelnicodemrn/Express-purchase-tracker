from __future__ import annotations

import sqlite3
import asyncio
import logging
from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

# Configuracao de logging corporativo
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="API Gestao de Suprimentos")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


class Pedido(BaseModel):
    id: Optional[int] = None
    item: str
    quantidade: int = Field(..., gt=0)
    urgencia: str
    preco_estimado: float
    setor: str
    comprado: bool = False
    data_criacao: Optional[str] = None


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
                (
                    "Monitor 24 polegadas",
                    3,
                    "Baixa",
                    900.0,
                    "Marketing",
                    1,
                    "2023-10-23",
                ),
                (
                    "Licenca Software Adobe",
                    1,
                    "Alta",
                    3500.0,
                    "Design",
                    0,
                    "2023-10-25",
                ),
            ]
            conn.executemany(
                "INSERT INTO pedidos (item, quantidade, urgencia, preco_estimado, setor, comprado, data_criacao) VALUES (?,?,?,?,?,?,?)",
                dados_iniciais,
            )
            conn.commit()


iniciar_db()


async def processar_notificacao_diretoria(item: str, valor: float):
    logger.info(f"Processando notificacao de aprovacao para o item: {item}")
    await asyncio.sleep(5)
    logger.info(f"Notificacao de aprovacao enviada. Valor total: R$ {valor:.2f}")


@app.post("/pedidos", response_model=Pedido)
async def criar_pedido(pedido: Pedido, background_tasks: BackgroundTasks):
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
def listar_pedidos():
    with sqlite3.connect("compras.db") as conn:
        conn.row_factory = sqlite3.Row
        pedidos = conn.execute(
            "SELECT * FROM pedidos ORDER BY comprado ASC, id DESC"
        ).fetchall()
        return [dict(p) for p in pedidos]


@app.put("/pedidos/{pedido_id}/concluir")
def concluir_pedido(pedido_id: int):
    with sqlite3.connect("compras.db") as conn:
        conn.execute("UPDATE pedidos SET comprado = 1 WHERE id = ?", (pedido_id,))
        conn.commit()
    return {"status": "sucesso"}


@app.delete("/pedidos/{pedido_id}")
def deletar_pedido(pedido_id: int):
    with sqlite3.connect("compras.db") as conn:
        conn.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
        conn.commit()
    return {"status": "sucesso"}


app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="frontend")
