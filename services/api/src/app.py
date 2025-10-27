# Não alterar.
import sys
import os

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from flask import Flask, jsonify, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from flasgger import Swagger
from datetime import datetime

from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request, exceptions

from bs4 import BeautifulSoup
from jsonschema import ValidationError
import requests
import pandas as pd

import secrets

from services.resources.Extract import *

extract = Extract()

app = Flask(__name__)
#app.config.from_object('config')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = secrets.token_hex(32)  # Chave secreta para sessões do Flask

app.config["JWT_SECRET_KEY"] = secrets.token_hex(32)  # Chave secreta para JWT

db = SQLAlchemy(app)

jwt = JWTManager(app)

# Replace basic Swagger init with a richer template including security
template = {
    "swagger": "2.0",
    "info": {
        "title": "Challanger API",
        "description": "API para análise e extração de dados de livros.",
        "version": "1.0.0"
    },
    "basePath": "/",  # base da API
    "schemes": ["http"],
}

swagger_config = {
    "title": "API",
    "uiversion": 3,
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Token JWT: Bearer <token>"
        }
    },
    "security": [{"Bearer": []}],
}



app.config["SWAGGER"] = swagger_config
swagger = Swagger(app)

auth = HTTPBasicAuth()
users = {"admin": "password"}  # Adicionar ao db no futuro

#------------------- Endpoints Core --------------------


@app.route('/')
def home():
    """
    Home endpoint
    ---
    tags:
      - Home
    responses:
      200:
        description: Welcome message
        schema:
          type: string
    """
    return "Welcome to the Challanger."


# Retorna erro amigável quando a rota não existir
# Antonio G. Quadro
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Not Found",
        "message": "A rota informada não existe!"
    }), 404


#Retorna lista de livros
@app.route('/api/v1/books', methods=['GET'])
def get_books():
    """
    Lista todos os livros
    ---
    tags:
      - Books
    responses:
      200:
        description: Lista de livros encontrada com sucesso.
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              title:
                type: string
              price:
                type: number
              rating:
                type: integer
    security:
      - Bearer: []
    """
    return get_books()


# Retorna detalhes completos de um livro pelo id específico
@app.route('/api/v1/books/<int:book_id>', methods=['GET'])
def get_book(book_id):
    """
    Recupera detalhes de um livro pelo ID
    ---
    tags:
      - Books
    parameters:
      - name: book_id
        in: path
        required: true
        type: integer
        description: ID do livro
    responses:
      200:
        description: Detalhes do livro
        schema:
          type: object
      404:
        description: Livro não encontrado
    security:
      - Bearer: []
    """

    return get_book(book_id)


# Pesquisa livros por título e/ou categoria
@app.route('/api/v1/books/search', methods=['GET'])
def search_books():
    """
    Busca livros por título e/ou categoria
    ---
    tags:
      - Books
    parameters:
      - name: title
        in: query
        type: string
        required: false
        description: Título (ou parte do título) para busca
      - name: category
        in: query
        type: string
        required: false
        description: Categoria para filtrar
    responses:
      200:
        description: Resultados da busca
        schema:
          type: array
          items:
            type: object
      400:
        description: Parâmetros inválidos
    security:
      - Bearer: []
    """
    title = request.args.get("title", "").lower()
    category = request.args.get("category", "").lower()
    books = extract.load_books()

    results = [
        b for b in books
        if (title in b["title"].lower() if title else True) and (
            category in b["category"].lower() if category else True)
    ]

    return jsonify(results), 200


# Lista todas as categorias de livros disponiveis
# Antonio G. Quadro
@app.route('/api/v1/categories', methods=['GET'])
def get_categories():
    """
    Lista todas as categorias disponíveis
    ---
    tags:
      - Categories
    responses:
      200:
        description: Lista de categorias
        schema:
          type: array
          items:
            type: string
    security:
      - Bearer: []
    """
    return get_categories()


# Verifica o status da API e a conectivade com os dados
# Antonio G. Quadro
@app.route('/api/v1/health', methods=['GET'])
def get_health():
    """
    Health check da API
    ---
    tags:
      - Health
    responses:
      200:
        description: Status da API e timestamp
        schema:
          type: object
          properties:
            status:
              type: string
            database:
              type: string
            timestamp:
              type: string
    """
    health = {
        "status": "Ok",
        "database":
        "developing...",  # Aguardo a conexão com o banco para retornar se a conexão está ativa
        "timestamp": datetime.now().isoformat()
    }
    return jsonify(health), 200


#------------------- Endpoints de insights --------------------


# Retorna total de livros, preço médio, e distribuição por rating
@app.route('/api/v1/stats/overview', methods=['GET'])
def get_stats_overview():
    """
    Estatísticas gerais da coleção
    ---
    tags:
      - Stats
    responses:
      200:
        description: Estatísticas (total, preço médio, distribuição de ratings)
        schema:
          type: object
    security:
      - Bearer: []
    """
    stats = {
        "total_books": webScrapping.get_total_books(),
        "average_price": webScrapping.get_average_price(),
        "rating_distribution": webScrapping.get_rating_distribution()
    }
    return jsonify(stats), 200


# Estatísticas por categoria (lista de categorias com métricas)
@app.route('/api/v1/stats/categories', methods=['GET'])
def get_category_stats():
    """
    Estatísticas por categoria
    ---
    tags:
      - Stats
    responses:
      200:
        description: Estatísticas detalhadas por categoria
        schema:
          type: array
          items:
            type: object
    security:
      - Bearer: []
    """
    # Adjusted to return all categories stats - implementation may vary
    categories = webScrapping.get_categories()
    stats_list = []
    for c in categories:
        stats_list.append({
            "category":
            c,
            "total_books":
            webScrapping.get_total_books_by_category(c),
            "average_price":
            webScrapping.get_average_price_by_category(c),
            "rating_distribution":
            webScrapping.get_rating_distribution_by_category(c)
        })
    return jsonify(stats_list), 200


# Retorna os livros com a melhor avaliação
# Antonio G. Quadro
@app.route('/api/v1/books/top-rated', methods=['GET'])
def get_top_rated():
    """
    Lista livros top-rated
    ---
    tags:
      - Books
    responses:
      200:
        description: Lista de livros com maior avaliação
        schema:
          type: array
          items:
            type: object
    security:
      - Bearer: []
    """
    books = webScrapping.get_books_top_rated()
    return jsonify(books), 200


# Filtra os livros dentro de uma faixa especifica de preço
# Antonio G. Quadro
@app.route('/api/v1/books/price-range', methods=['GET'])
def get_price_range():
    """
    Filtra livros por faixa de preço
    ---
    tags:
      - Books
    parameters:
      - name: min
        in: query
        type: number
        required: false
      - name: max
        in: query
        type: number
        required: false
    responses:
      200:
        description: Lista de livros na faixa de preço
        schema:
          type: array
          items:
            type: object
      400:
        description: Parâmetros inválidos
    security:
      - Bearer: []
    """
    min_value = request.args.get('min', type=float)
    max_value = request.args.get('max', type=float)
    if min_value is not None or max_value is not None:
        books = webScrapping.get_books_by_price_range(min_value, max_value)
        return jsonify(books), 200
    else:
        return jsonify({
            "error":
            "O campo min (mínimo) ou max (máximo) devem ser informados!"
        }), 400


#------------------- Desafios adicionais (Bonus) --------------------
# Implementar autenticação JWT para proteger certos endpoints Desafio 1@
# Obter token JWT
@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    """
    Obter token JWT
    ---
    tags:
      - Auth
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            username:
              type: string
            password:
              type: string
    responses:
      200:
        description: Token de acesso
        schema:
          type: object
          properties:
            access_token:
              type: string
      401:
        description: Credenciais inválidas
    """
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = db.session.query(User).filter_by(username=username).first()
    if not user or user.password != password:  # futuramente use hash
        return jsonify({"error": "Invalid credentials"}), 401

    session["access_token"] = create_access_token(identity=username)
    return jsonify(access_token=session["access_token"]), 200


# Refresh token (mantido em /api/v1/auth/refresh)
@app.route('/api/v1/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Renovar token JWT
    ---
    tags:
      - Auth
    security:
      - Bearer: []
    responses:
      200:
        description: Novo token de acesso
        schema:
          type: object
          properties:
            access_token:
              type: string
    """
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)
    return jsonify(access_token=new_access_token), 200


#Desafio 2 - Endpoints protegidos para retornar dados de treinamento e previsões do modelo


# Endpoint protegido para retornar dados de treinamento
# É aqui que o filho chora e a mãe não vê
@app.route('/api/v1/ml/training-data', methods=['GET'])
@jwt_required()
def get_training_data():
    current_user = get_jwt_identity()
    # Implementar a lógica para retornar os dados de treinamento
    return jsonify({"message":
                    "Dados de treinamento retornados com sucesso."}), 200


# Endpoint protegido para retornar previsões do modelo
@app.route('/api/v1/ml/predictions', methods=['POST'])
@jwt_required()
def get_predictions():
    current_user = get_jwt_identity()
    # Implementar a lógica para retornar as previsões
    return jsonify({"message": "Previsões retornadas com sucesso."}), 200


#---------- Desafio 3 : Monitoramento de Analytics ------------------
#Logs estruturados de todas as chamadas de API (incluindo parâmetros, respostas e tempos de resposta)
#Metricas de performance da API (tempo médio de resposta, taxa de erro)
# A etapa 1 e 2 foram mescladas, porque conter dois app.before_request e app.after_request pode gerar conflitos na aplicação
import logging
from time import time
from services.database.models.base import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.before_request
def log_request_info():
    if "Authorization" not in request.headers and "access_token" in session:
        request.headers = request.headers.copy()
        request.headers["Authorization"] = f"Bearer {session['access_token']}"

    # Inicia o timer para medir o tempo da requisição
    request.start_time = time()
    if request.path.startswith(("/flasgger", "/apispec_")):
        return
    # Faz log básico da requisição
    logger.info(
        f"Request: {request.method} {request.url} - Body: {request.get_data()}"
    )

    public_routes = ["/", "/apidocs", "/api/v1/auth/login", "/api/v1/health"]

    # Libera tudo que comece com /apidocs ou /flasgger_static (Swagger UI)
    if request.path.startswith("/apidocs") or request.path.startswith(
            "/flasgger_static"):
        return
    if request.path in public_routes:
        return
    try:
        verify_jwt_in_request()
    except exceptions.NoAuthorizationError:
        logger.warning(f"Tentativa de acesso sem token: {request.path}")
        return jsonify({"error": "Missing or invalid token"}), 401


@app.after_request
def log_response_info(response):
    try:
        if not response.direct_passthrough:
            body = response.get_data(as_text=True)
        else:
            body = "<streaming or static file>"
        logger.info(f"Response: {response.status} - Body: {body}")
    except Exception as e:
        logger.error(f"Error logging response: {e}")
    finally:
        if hasattr(request, "start_time"):
            duration = time() - request.start_time
            logger.info(f"Response time: {duration:.2f} seconds")
        return response


#Dashboard simples para visualizar as métricas de uso da API (pode ser uma rota protegida que retorna dados em formato JSON)
@app.route('/api/v1/analytics', methods=['GET'])
@jwt_required()
def get_analytics():
    current_user = get_jwt_identity()
    # Implementar a lógica para retornar as métricas de uso da API
    return jsonify(
        {"message": "Métricas de uso da API retornadas com sucesso."}), 200


#------------------- Rodar aplicação --------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database tables created.")
    app.run(debug=True, threaded=True)
