import os
import io
import json
import tempfile
import threading as real_threading
from datetime import datetime
import pandas as pd
import pytest

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import services.api.src.app as app_module
from flask_jwt_extended import create_access_token

@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Configura o ambiente de teste criando uma aplicação Flask com banco em memória.
    Isso garante que os testes não afetem o banco de dados real dos usuários.
    """
    app = app_module.app
    
    # Configurações específicas para teste
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # Banco em memória
    app.config['WTF_CSRF_ENABLED'] = False  # Desabilita CSRF para testes

    # Prepara o banco de dados para os testes
    with app.app_context():
        app_module.db.init_app(app)
        app_module.db.create_all()  # Cria todas as tabelas

    # Fornece o cliente de teste para os testes
    with app.test_client() as client:
        yield client


def test_home(client):
    """Testa se a página inicial está funcionando corretamente"""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Welcome to the Challanger." in response.data


def test_get_books_monkeypatched(client, monkeypatch):
    """Testa a busca de livros com dados simulados"""
    # Simula dados que seriam retornados pelo banco/API externa
    mock_books = pd.DataFrame([{"id": 1, "title": "Dom Casmurro", "price": 29.90, "rating": 4.5}])
    monkeypatch.setattr(app_module, "extract", app_module.extract)
    monkeypatch.setattr(app_module.extract, "load_books", lambda: mock_books)

    response = client.get('/api/v1/books')
    assert response.status_code == 200
    
    books_data = response.get_json()
    assert isinstance(books_data, list)
    assert books_data[0]['title'] == 'Dom Casmurro'


def test_get_book_found_and_not_found(client, monkeypatch):
    """Testa a busca por um livro específico - casos de sucesso e não encontrado"""
    
    # Caso de sucesso: livro encontrado
    monkeypatch.setattr(app_module.extract, "get_book", lambda book_id: {"id": book_id, "title": "O Cortiço"})
    response = client.get('/api/v1/books/1')
    assert response.status_code == 200
    assert response.get_json()["title"] == "O Cortiço"

    # Caso de erro: livro não encontrado
    monkeypatch.setattr(app_module.extract, "get_book", lambda book_id: None)
    response = client.get('/api/v1/books/999')
    assert response.status_code == 404
    assert response.get_json()["msg"] == "Livro não encontrado!"


def test_search_books(client, monkeypatch):
    """Testa a funcionalidade de busca de livros por título e categoria"""
    # Simula resultados de busca
    mock_results = pd.DataFrame([{"id": 5, "title": "1984", "price": 35.00}])
    monkeypatch.setattr(app_module.extract, "search_books", lambda title, category: mock_results)
    
    response = client.get('/api/v1/books/search?title=distopia&category=ficcao')
    assert response.status_code == 200
    
    search_results = response.get_json()
    assert isinstance(search_results, list)
    assert search_results[0]["title"] == "1984"


def test_get_categories_success(client, monkeypatch):
    """Testa a recuperação das categorias disponíveis"""
    mock_categories = ["Romance", "Ficção Científica", "Biografia"]
    monkeypatch.setattr(app_module.extract, "get_categories", lambda: mock_categories)
    
    response = client.get('/api/v1/categories')
    assert response.status_code == 200
    
    categories_data = response.get_json()
    assert "categories" in categories_data
    assert categories_data["total"] == 3
    assert "Romance" in categories_data["categories"]


def test_health_endpoint(client, monkeypatch):
    """Testa o endpoint de saúde da aplicação"""
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    
    health_data = response.get_json()
    assert health_data["status"] == "Ok"
    assert "database" in health_data  # Verifica conexão com banco
    assert "timestamp" in health_data  # Verifica timestamp da resposta


def _create_mock_user(username, valid_password=True):
    """Cria um usuário simulado para testes de autenticação"""
    class MockUser:
        def __init__(self, username, is_valid):
            self.username = username
            self._is_valid = is_valid

        def check_password(self, password):
            return self._is_valid and password == "senha_correta"

    return MockUser(username, valid_password)


def test_login_success_and_failure(client, monkeypatch):
    """Testa os cenários de login: credenciais válidas e inválidas"""
    
    # Simula a consulta ao banco de usuários
    def mock_filter_by(**filters):
        class QueryResult:
            def first(self):
                if filters.get("username") == "usuario_valido":
                    return _create_mock_user("usuario_valido", valid_password=True)
                return None
        return QueryResult()

    monkeypatch.setattr(app_module.User, "query", type("MockQuery", (), {"filter_by": staticmethod(mock_filter_by)}))

    # Caso de sucesso: login com credenciais corretas
    response = client.post('/api/v1/auth/login', 
                          json={"username": "usuario_valido", "password": "senha_correta"})
    assert response.status_code == 200
    response_data = response.get_json()
    assert "access_token" in response_data or 'access_token' in response.get_data(as_text=True)

    # Caso de falha: senha incorreta
    response = client.post('/api/v1/auth/login', 
                          json={"username": "usuario_valido", "password": "senha_errada"})
    assert response.status_code == 401
    assert response.get_json().get("error") == "Credenciais inválidas"


def test_protected_route_requires_jwt(client):
    """Testa que rotas protegidas exigem token JWT válido"""
    
    # Tentativa de acesso sem token
    response = client.get('/api/v1/ml/training-data')
    assert response.status_code in (401, 302)  # Não autorizado ou redirecionamento

    # Acesso com token válido
    token = create_access_token(identity="usuario_teste")
    response = client.get('/api/v1/ml/training-data', 
                         headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    # Verifica se retorna dados de treinamento
    assert "Dados de treinamento" in response.get_data(as_text=True) or response.get_json().get("message")


def test_trigger_scraping_starts_thread_and_updates_status(client, monkeypatch, tmp_path):
    """
    Testa o acionamento do processo de scraping.
    Simula a execução em thread e verifica atualização de status.
    """
    
    # Cria arquivo CSV temporário para simular resultado do scraping
    output_csv = tmp_path / "livros_scraped.csv"
    sample_data = pd.DataFrame([{"title": "O Alienista", "author": "Machado de Assis"}])
    sample_data.to_csv(output_csv, index=False, encoding="utf-8-sig")

    # Simula o módulo de scraping
    class MockScraper:
        OUT_PATH = str(output_csv)

        @staticmethod
        def main():
            # Em um cenário real, aqui ocorreria o scraping
            # Para testes, apenas simulamos a execução
            return

    monkeypatch.setattr(app_module, "books_scraper", MockScraper)

    # Faz a thread executar sincronamente para facilitar testes
    class SyncThread:
        def __init__(self, target=None, daemon=None):
            self._target = target

        def start(self):
            # Executa imediatamente (sincrono) em vez de em background
            if self._target:
                self._target()

    monkeypatch.setattr(app_module, "threading", type("ThreadSync", (), {"Thread": SyncThread}))

    # Aciona o scraping (rota protegida)
    token = create_access_token(identity="usuario_scraping")
    response = client.post('/api/v1/scraping/trigger', 
                          headers={"Authorization": f"Bearer {token}"})
    
    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data["message"] == "Scraping iniciado com sucesso."

    # Verifica se o status foi atualizado após execução
    import time
    time.sleep(0.1)  # Pequena pausa para garantir processamento
    
    status = app_module.scraping_status
    assert "running" in status
    assert isinstance(status.get("books_scraped"), int)  # Deve ter contagem de livros


def test_get_scraping_status_requires_jwt(client):
    """Testa que a consulta de status do scraping requer autenticação"""
    
    # Tentativa sem token
    response = client.get('/api/v1/scraping/status')
    assert response.status_code == 401  # Não autorizado

    # Consulta com token válido
    token = create_access_token(identity="qualquer_usuario")
    response = client.get('/api/v1/scraping/status', 
                         headers={"Authorization": f"Bearer {token}"})
    
    assert response.status_code == 200
    status_data = response.get_json()
    # Verifica estrutura básica do response
    assert "running" in status_data
    assert "books_scraped" in status_data