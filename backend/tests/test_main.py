"""
Testes de integração — Express Purchase Tracker API
Cobertura mínima exigida pelo CI/CD: 80%
"""

import pytest
from fastapi.testclient import TestClient

# Importa a app sem o StaticFiles (evita falha em ambiente CI sem o dist)
import sys
import os

# Garante que o diretório backend está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Patch do StaticFiles antes de importar main
from unittest.mock import patch, MagicMock

with patch("fastapi.staticfiles.StaticFiles.__init__", return_value=None):
    with patch("fastapi.applications.FastAPI.mount"):
        from main import app, iniciar_db

client = TestClient(app)


# ──────────────────────────────────────────────
# FIXTURES
# ──────────────────────────────────────────────

@pytest.fixture(autouse=True)
def banco_em_memoria(tmp_path, monkeypatch):
    """
    Redireciona conexões SQLite para banco temporário por teste.
    Evita poluir o banco de produção local.
    """
    db_path = str(tmp_path / "test_compras.db")

    import sqlite3 as _sqlite3
    original_connect = _sqlite3.connect

    def mock_connect(database, *args, **kwargs):
        return original_connect(db_path, *args, **kwargs)

    monkeypatch.setattr("sqlite3.connect", mock_connect)
    iniciar_db()
    yield


# ──────────────────────────────────────────────
# TESTES — GET /pedidos
# ──────────────────────────────────────────────

class TestListarPedidos:
    def test_retorna_lista(self):
        response = client.get("/pedidos")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_pedidos_iniciais_presentes(self):
        response = client.get("/pedidos")
        dados = response.json()
        assert len(dados) >= 4  # dados de seed

    def test_estrutura_do_pedido(self):
        response = client.get("/pedidos")
        pedido = response.json()[0]
        campos_obrigatorios = {"id", "item", "quantidade", "urgencia", "preco_estimado", "setor", "comprado", "data_criacao"}
        assert campos_obrigatorios.issubset(pedido.keys())


# ──────────────────────────────────────────────
# TESTES — POST /pedidos
# ──────────────────────────────────────────────

class TestCriarPedido:
    def _payload_valido(self, **overrides):
        base = {
            "item": "Teclado Mecânico",
            "quantidade": 2,
            "urgencia": "Normal",
            "preco_estimado": 450.0,
            "setor": "TI",
        }
        base.update(overrides)
        return base

    def test_cria_pedido_com_sucesso(self):
        response = client.post("/pedidos", json=self._payload_valido())
        assert response.status_code == 200
        dados = response.json()
        assert dados["item"] == "Teclado Mecânico"
        assert dados["id"] is not None
        assert dados["comprado"] is False
        assert dados["data_criacao"] is not None

    def test_pedido_aparece_na_listagem_apos_criacao(self):
        client.post("/pedidos", json=self._payload_valido(item="Mouse Logitech"))
        response = client.get("/pedidos")
        itens = [p["item"] for p in response.json()]
        assert "Mouse Logitech" in itens

    def test_quantidade_zero_e_invalida(self):
        response = client.post("/pedidos", json=self._payload_valido(quantidade=0))
        assert response.status_code == 422

    def test_quantidade_negativa_e_invalida(self):
        response = client.post("/pedidos", json=self._payload_valido(quantidade=-5))
        assert response.status_code == 422

    def test_campos_obrigatorios_ausentes(self):
        response = client.post("/pedidos", json={"item": "Teste"})
        assert response.status_code == 422

    def test_pedido_alto_valor_nao_bloqueia_resposta(self):
        """Pedidos > R$5.000 disparam BackgroundTask — response deve ser imediata."""
        payload = self._payload_valido(quantidade=1, preco_estimado=6000.0)
        response = client.post("/pedidos", json=payload)
        assert response.status_code == 200


# ──────────────────────────────────────────────
# TESTES — PUT /pedidos/{id}/concluir
# ──────────────────────────────────────────────

class TestConcluirPedido:
    def _criar_pedido(self):
        response = client.post("/pedidos", json={
            "item": "Webcam HD",
            "quantidade": 1,
            "urgencia": "Baixa",
            "preco_estimado": 300.0,
            "setor": "RH",
        })
        return response.json()["id"]

    def test_concluir_pedido_existente(self):
        pedido_id = self._criar_pedido()
        response = client.put(f"/pedidos/{pedido_id}/concluir")
        assert response.status_code == 200
        assert response.json()["status"] == "sucesso"

    def test_pedido_marcado_como_comprado_apos_conclusao(self):
        pedido_id = self._criar_pedido()
        client.put(f"/pedidos/{pedido_id}/concluir")
        pedidos = client.get("/pedidos").json()
        pedido = next((p for p in pedidos if p["id"] == pedido_id), None)
        assert pedido is not None
        assert pedido["comprado"] is True


# ──────────────────────────────────────────────
# TESTES — DELETE /pedidos/{id}
# ──────────────────────────────────────────────

class TestDeletarPedido:
    def _criar_pedido(self):
        response = client.post("/pedidos", json={
            "item": "Hub USB",
            "quantidade": 1,
            "urgencia": "Normal",
            "preco_estimado": 150.0,
            "setor": "TI",
        })
        return response.json()["id"]

    def test_deletar_pedido_existente(self):
        pedido_id = self._criar_pedido()
        response = client.delete(f"/pedidos/{pedido_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "sucesso"

    def test_pedido_removido_da_listagem(self):
        pedido_id = self._criar_pedido()
        client.delete(f"/pedidos/{pedido_id}")
        pedidos = client.get("/pedidos").json()
        ids = [p["id"] for p in pedidos]
        assert pedido_id not in ids
