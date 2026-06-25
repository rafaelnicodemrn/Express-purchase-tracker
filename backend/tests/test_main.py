"""
Testes de integração — Express Purchase Tracker API
Cobertura mínima exigida pelo CI/CD: 80%
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch

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


@pytest.fixture
def auth_headers():
    """Retorna headers com token JWT válido para uso nos testes."""
    res = client.post(
        "/auth/login", json={"username": "admin", "password": "projeto2025"}
    )
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ──────────────────────────────────────────────
# TESTES — Autenticação
# ──────────────────────────────────────────────


class TestAutenticacao:
    def test_login_credenciais_corretas_retorna_token(self):
        res = client.post(
            "/auth/login", json={"username": "admin", "password": "projeto2025"}
        )
        assert res.status_code == 200
        dados = res.json()
        assert "access_token" in dados
        assert dados["token_type"] == "bearer"
        assert len(dados["access_token"]) > 10

    def test_login_senha_errada_retorna_401(self):
        res = client.post(
            "/auth/login", json={"username": "admin", "password": "senha_errada"}
        )
        assert res.status_code == 401

    def test_login_usuario_errado_retorna_401(self):
        res = client.post(
            "/auth/login", json={"username": "hacker", "password": "projeto2025"}
        )
        assert res.status_code == 401

    def test_acesso_sem_token_retorna_401(self):
        res = client.get("/pedidos")
        assert res.status_code == 401

    def test_acesso_com_token_invalido_retorna_401(self):
        res = client.get(
            "/pedidos", headers={"Authorization": "Bearer token.invalido.mesmo"}
        )
        assert res.status_code == 401

    def test_acesso_com_token_valido_retorna_200(self, auth_headers):
        res = client.get("/pedidos", headers=auth_headers)
        assert res.status_code == 200

    def test_post_sem_token_retorna_401(self):
        res = client.post(
            "/pedidos",
            json={
                "item": "Teste",
                "quantidade": 1,
                "urgencia": "Normal",
                "preco_estimado": 100.0,
                "setor": "TI",
            },
        )
        assert res.status_code == 401

    def test_put_sem_token_retorna_401(self):
        res = client.put("/pedidos/1/concluir")
        assert res.status_code == 401

    def test_delete_sem_token_retorna_401(self):
        res = client.delete("/pedidos/1")
        assert res.status_code == 401

    def test_resumo_sem_token_retorna_401(self):
        res = client.get("/pedidos/resumo")
        assert res.status_code == 401

    def test_docs_acessivel_sem_autenticacao(self):
        res = client.get("/docs")
        assert res.status_code == 200


# ──────────────────────────────────────────────
# TESTES — GET /pedidos
# ──────────────────────────────────────────────


class TestListarPedidos:
    def test_retorna_lista(self, auth_headers):
        response = client.get("/pedidos", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_pedidos_iniciais_presentes(self, auth_headers):
        response = client.get("/pedidos", headers=auth_headers)
        dados = response.json()
        assert len(dados) >= 4

    def test_estrutura_do_pedido(self, auth_headers):
        response = client.get("/pedidos", headers=auth_headers)
        pedido = response.json()[0]
        campos_obrigatorios = {
            "id",
            "item",
            "quantidade",
            "urgencia",
            "preco_estimado",
            "setor",
            "comprado",
            "data_criacao",
        }
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

    def test_cria_pedido_com_sucesso(self, auth_headers):
        response = client.post(
            "/pedidos", json=self._payload_valido(), headers=auth_headers
        )
        assert response.status_code == 200
        dados = response.json()
        assert dados["item"] == "Teclado Mecânico"
        assert dados["id"] is not None
        assert dados["comprado"] is False
        assert dados["data_criacao"] is not None

    def test_pedido_aparece_na_listagem_apos_criacao(self, auth_headers):
        client.post(
            "/pedidos",
            json=self._payload_valido(item="Mouse Logitech"),
            headers=auth_headers,
        )
        response = client.get("/pedidos", headers=auth_headers)
        itens = [p["item"] for p in response.json()]
        assert "Mouse Logitech" in itens

    def test_quantidade_zero_e_invalida(self, auth_headers):
        response = client.post(
            "/pedidos", json=self._payload_valido(quantidade=0), headers=auth_headers
        )
        assert response.status_code == 422

    def test_quantidade_negativa_e_invalida(self, auth_headers):
        response = client.post(
            "/pedidos", json=self._payload_valido(quantidade=-5), headers=auth_headers
        )
        assert response.status_code == 422

    def test_campos_obrigatorios_ausentes(self, auth_headers):
        response = client.post("/pedidos", json={"item": "Teste"}, headers=auth_headers)
        assert response.status_code == 422

    def test_pedido_alto_valor_nao_bloqueia_resposta(self, auth_headers):
        """Pedidos > R$5.000 disparam BackgroundTask — response deve ser imediata."""
        payload = self._payload_valido(quantidade=1, preco_estimado=6000.0)
        response = client.post("/pedidos", json=payload, headers=auth_headers)
        assert response.status_code == 200

    def test_urgencia_invalida_e_rejeitada(self, auth_headers):
        response = client.post(
            "/pedidos",
            json=self._payload_valido(urgencia="Urgentissimo"),
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("urgencia", ["Alta", "Normal", "Baixa"])
    def test_urgencias_validas_sao_aceitas(self, urgencia, auth_headers):
        response = client.post(
            "/pedidos",
            json=self._payload_valido(urgencia=urgencia),
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["urgencia"] == urgencia


# ──────────────────────────────────────────────
# TESTES — GET /pedidos (filtros)
# ──────────────────────────────────────────────


class TestFiltrosListagem:
    def test_filtro_por_setor(self, auth_headers):
        response = client.get("/pedidos", params={"setor": "TI"}, headers=auth_headers)
        assert response.status_code == 200
        dados = response.json()
        assert len(dados) >= 1
        assert all(p["setor"] == "TI" for p in dados)

    def test_filtro_por_urgencia(self, auth_headers):
        response = client.get(
            "/pedidos", params={"urgencia": "Alta"}, headers=auth_headers
        )
        assert response.status_code == 200
        dados = response.json()
        assert len(dados) >= 1
        assert all(p["urgencia"] == "Alta" for p in dados)

    def test_filtro_por_comprado(self, auth_headers):
        response = client.get(
            "/pedidos", params={"comprado": "true"}, headers=auth_headers
        )
        assert response.status_code == 200
        dados = response.json()
        assert len(dados) >= 1
        assert all(p["comprado"] is True for p in dados)

    def test_filtro_combinado_sem_resultado(self, auth_headers):
        response = client.get(
            "/pedidos",
            params={"setor": "Inexistente", "urgencia": "Alta"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []


# ──────────────────────────────────────────────
# TESTES — GET /pedidos/resumo
# ──────────────────────────────────────────────


class TestResumoPedidos:
    def test_estrutura_da_resposta(self, auth_headers):
        response = client.get("/pedidos/resumo", headers=auth_headers)
        assert response.status_code == 200
        dados = response.json()
        assert set(dados.keys()) == {
            "total_pedidos",
            "valor_total_pendente",
            "por_urgencia",
            "por_setor",
        }

    def test_totais_consistentes_com_listagem(self, auth_headers):
        pedidos = client.get("/pedidos", headers=auth_headers).json()
        resumo = client.get("/pedidos/resumo", headers=auth_headers).json()

        assert resumo["total_pedidos"] == len(pedidos)

        valor_esperado = sum(
            p["preco_estimado"] * p["quantidade"] for p in pedidos if not p["comprado"]
        )
        assert resumo["valor_total_pendente"] == pytest.approx(valor_esperado)

        por_urgencia_esperado = {}
        for p in pedidos:
            por_urgencia_esperado[p["urgencia"]] = (
                por_urgencia_esperado.get(p["urgencia"], 0) + 1
            )
        assert resumo["por_urgencia"] == por_urgencia_esperado

        por_setor_esperado = {}
        for p in pedidos:
            por_setor_esperado[p["setor"]] = por_setor_esperado.get(p["setor"], 0) + 1
        assert resumo["por_setor"] == por_setor_esperado

    def test_resumo_atualiza_apos_criar_pedido(self, auth_headers):
        resumo_antes = client.get("/pedidos/resumo", headers=auth_headers).json()
        client.post(
            "/pedidos",
            json={
                "item": "Cabo HDMI",
                "quantidade": 10,
                "urgencia": "Baixa",
                "preco_estimado": 20.0,
                "setor": "TI",
            },
            headers=auth_headers,
        )
        resumo_depois = client.get("/pedidos/resumo", headers=auth_headers).json()
        assert resumo_depois["total_pedidos"] == resumo_antes["total_pedidos"] + 1
        assert resumo_depois["valor_total_pendente"] == pytest.approx(
            resumo_antes["valor_total_pendente"] + 200.0
        )


# ──────────────────────────────────────────────
# TESTES — PUT /pedidos/{id}
# ──────────────────────────────────────────────


class TestAtualizarPedido:
    def _criar_pedido(self, auth_headers):
        response = client.post(
            "/pedidos",
            json={
                "item": "Impressora Laser",
                "quantidade": 1,
                "urgencia": "Normal",
                "preco_estimado": 800.0,
                "setor": "TI",
            },
            headers=auth_headers,
        )
        return response.json()["id"]

    def test_atualizar_pedido_existente(self, auth_headers):
        pedido_id = self._criar_pedido(auth_headers)
        response = client.put(
            f"/pedidos/{pedido_id}",
            json={
                "item": "Impressora Laser Colorida",
                "quantidade": 2,
                "urgencia": "Alta",
                "preco_estimado": 1500.0,
                "setor": "Design",
                "comprado": True,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        dados = response.json()
        assert dados["item"] == "Impressora Laser Colorida"
        assert dados["quantidade"] == 2
        assert dados["urgencia"] == "Alta"
        assert dados["preco_estimado"] == 1500.0
        assert dados["setor"] == "Design"
        assert dados["comprado"] is True

    def test_atualizacao_persiste_na_listagem(self, auth_headers):
        pedido_id = self._criar_pedido(auth_headers)
        client.put(
            f"/pedidos/{pedido_id}",
            json={
                "item": "Impressora Atualizada",
                "quantidade": 3,
                "urgencia": "Baixa",
                "preco_estimado": 999.0,
                "setor": "RH",
                "comprado": False,
            },
            headers=auth_headers,
        )
        pedidos = client.get("/pedidos", headers=auth_headers).json()
        pedido = next((p for p in pedidos if p["id"] == pedido_id), None)
        assert pedido is not None
        assert pedido["item"] == "Impressora Atualizada"
        assert pedido["setor"] == "RH"

    def test_atualizar_pedido_inexistente_retorna_404(self, auth_headers):
        response = client.put(
            "/pedidos/999999",
            json={
                "item": "Item Fantasma",
                "quantidade": 1,
                "urgencia": "Normal",
                "preco_estimado": 10.0,
                "setor": "TI",
            },
            headers=auth_headers,
        )
        assert response.status_code == 404


# ──────────────────────────────────────────────
# TESTES — PUT /pedidos/{id}/concluir
# ──────────────────────────────────────────────


class TestConcluirPedido:
    def _criar_pedido(self, auth_headers):
        response = client.post(
            "/pedidos",
            json={
                "item": "Webcam HD",
                "quantidade": 1,
                "urgencia": "Baixa",
                "preco_estimado": 300.0,
                "setor": "RH",
            },
            headers=auth_headers,
        )
        return response.json()["id"]

    def test_concluir_pedido_existente(self, auth_headers):
        pedido_id = self._criar_pedido(auth_headers)
        response = client.put(f"/pedidos/{pedido_id}/concluir", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "sucesso"

    def test_pedido_marcado_como_comprado_apos_conclusao(self, auth_headers):
        pedido_id = self._criar_pedido(auth_headers)
        client.put(f"/pedidos/{pedido_id}/concluir", headers=auth_headers)
        pedidos = client.get("/pedidos", headers=auth_headers).json()
        pedido = next((p for p in pedidos if p["id"] == pedido_id), None)
        assert pedido is not None
        assert pedido["comprado"] is True


# ──────────────────────────────────────────────
# TESTES — DELETE /pedidos/{id}
# ──────────────────────────────────────────────


class TestDeletarPedido:
    def _criar_pedido(self, auth_headers):
        response = client.post(
            "/pedidos",
            json={
                "item": "Hub USB",
                "quantidade": 1,
                "urgencia": "Normal",
                "preco_estimado": 150.0,
                "setor": "TI",
            },
            headers=auth_headers,
        )
        return response.json()["id"]

    def test_deletar_pedido_existente(self, auth_headers):
        pedido_id = self._criar_pedido(auth_headers)
        response = client.delete(f"/pedidos/{pedido_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "sucesso"

    def test_pedido_removido_da_listagem(self, auth_headers):
        pedido_id = self._criar_pedido(auth_headers)
        client.delete(f"/pedidos/{pedido_id}", headers=auth_headers)
        pedidos = client.get("/pedidos", headers=auth_headers).json()
        ids = [p["id"] for p in pedidos]
        assert pedido_id not in ids
