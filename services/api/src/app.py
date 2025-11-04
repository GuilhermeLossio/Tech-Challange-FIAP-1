from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request, exceptions
import secrets
from datetime import timedelta, datetime

from flask import Flask, jsonify, request, session, render_template_string
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_httpauth import HTTPBasicAuth
from flasgger import Swagger
import sys
import os
from sqlalchemy import create_engine
import threading
import time

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from services.database.models.base import db, User
from services.resources.Extract import Extract
import services.scraper.extractors.scrape_books as books_scraper


extract = Extract()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Guilherme, tem que ajustar esses tokens, secrets.token_hex(32) não estava funcionando, por isso deixei a chave fica ali embaixo

app.config['SECRET_KEY'] = secrets.token_hex(
    32)  # Chave secreta para sessões do Flask
app.config["JWT_SECRET_KEY"] = secrets.token_hex(32)  # Chave secreta para JWT

db.init_app(app)
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
    "title":
    "API",
    "uiversion":
    3,
    "headers": [],
    "specs": [{
        "endpoint": 'apispec',
        "route": '/apispec.json',
        "rule_filter": lambda rule: True,
        "model_filter": lambda tag: True,
    }],
    "static_url_path":
    "/flasgger_static",
    "swagger_ui":
    True,
    "specs_route":
    "/apidocs/",
    "securityDefinitions": {
        "Bearer": {
            "type":
            "apiKey",
            "name":
            "Authorization",
            "in":
            "header",
            "description":
            "JWT Authorization header using the Bearer scheme. Example: \"Authorization: Bearer {token}\""
        }
    },
    "security": [{
        "Bearer": []
    }]
}

app.config["SWAGGER"] = swagger_config
swagger = Swagger(app)

#------------------- Tratativas de erro --------------------


# Retorna erro amigável quando a rota não existir
# Antonio G. Quadro
@app.errorhandler(404)
def not_found(e):
    return jsonify({"msg": "A rota informada não existe!"}), 404


# Retorna erro amigável quando o tipo de requisição não corresponde ao do endpoint
# Antonio G. Quadro
@app.errorhandler(405)
def not_allowed(e):
    return jsonify({"msg": "Método não permitido"}), 405


# Erros internos do servidor
# Antonio G. Quadro
@app.errorhandler(500)
def server_error(e):
    return jsonify({"msg": "Falha ao processar solicitação!"}), 500


# Antonio G. Quadro
@app.errorhandler(400)
def bad_request(error):
    return jsonify(
        {"msg":
         "A requisição está malformada ou com parâmetros inválidos."}), 400


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
    return jsonify(
        extract.load_books().fillna("").to_dict(orient="records")), 200


# Retorna detalhes completos de um livro pelo id específico
@app.route('/api/v1/books/<string:book_id>', methods=['GET'])
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
    book = extract.get_book(book_id)
    if book:
        return jsonify(book), 200
    return jsonify({"msg": "Livro não encontrado!"}), 404


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

    results = extract.search_books(title, category)

    return results.fillna("").to_dict(orient="records"), 200


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
				type: object
				items:
					type: object
	security:
		- Bearer: {
		"categories": [{}],
		"total": 1
		}
	"""
    try:
        categories = extract.get_categories()
        return jsonify({
            "categories": categories,
            "total": len(categories)
        }), 200

    except FileNotFoundError:
        print(
            "Verifique se está na pasta do projeto! cd Tech-Challange-FIAP-1")
    except Exception as e:
        print(e)

    return {"msg": "Erro interno ao obter categorias!"}, 500


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
    try:
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "Online"
    except Exception as e:
        db_status = "Offline"

    health = {
        "status": "Ok",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }
    return jsonify(health), 200


# #------------------- Endpoints de insights --------------------


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
    stats = extract.get_overview()
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

    stats_category = extract.get_category_stats()
    return jsonify(stats_category), 200


# Retorna os livros com a melhor avaliação
# Antonio G. Quadro
@app.route('/api/v1/books/top-rated', methods=['GET'])
@jwt_required()
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
    try:
        books = extract.get_books_top_rated()
        return books, 200
    except Exception as e:
        print(e)
        return {"msg": "Erro interno ao retornar requisição!"}, 500


# Filtra os livros dentro de uma faixa especifica de preço
# Antonio G. Quadro
@app.route('/api/v1/books/price-range', methods=['GET'])
@jwt_required()
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
    try:
        min_value = request.args.get('min', type=float)
        max_value = request.args.get('max', type=float)
        if min_value is not None or max_value is not None:
            books = extract.get_books_price_range(min_value, max_value)
            return books, 200
        else:
            return {
                "msg":
                "O campo min (mínimo) ou max (máximo) devem ser informados!"
            }, 400
    except Exception as e:
        print(e)
        return {"msg": "Erro interno ao retornar requisição!"}, 500


#------------------- Desafios adicionais (Bonus) --------------------
# Implementar autenticação JWT para proteger certos endpoints Desafio 1
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
            required:
              - username
              - password
            properties:
                username:
                    type: string
                    example: "admin"
                password:
                    type: string
                    example: "password"
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
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON in request"}), 400

        username = (data.get("username") or "").strip()
        password = data.get("password")

        if not username or not password:
            return jsonify({"error":
                            "Username and password are required"}), 400

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            logger.warning(f"Tentativa de login falhor para o User:{username}")
            return jsonify({"error": "Credenciais inválidas"}), 401

        # user = db.session.query(User).filter_by(username=username).first()
        # if not user or user.password != password:  # futuramente use hash
        #     return jsonify({"error": "Invalid credentials"}), 401

        access_token = create_access_token(identity=username,
                                           expires_delta=timedelta(hours=1))
        
        response = jsonify({
			"access_token": access_token,
			"token_type": "bearer",
			"message": "Login successful"
		})
        
        response.set_cookie(
			'access_token',
			value=access_token,
			httponly=True,
			secure=False,  # True em produção com HTTPS
			samesite='Lax',
			max_age=3600
		)

        logger.info(
            f"Tentativa de login bem-sucedido para o usuario: {username}")

        # session["access_token"] = access_token

        return response, 200
    except Exception as e:
        logger.error(f"Erro no login : {str(e)}")
        return jsonify({
            "message":
            f"Falha no servidor ao realizar autenticação: {str(e)}"
        }), 500


# Variável global pra controlar o status do scraping
scraping_status = {
    "running": False,
    "started_by": None,
    "start_time": None,
    "end_time": None,
    "books_scraped": 0,
    "error": None
}


# Executa mais uma extração, por web Scrapping
@app.route("/api/v1/scraping/trigger", methods=["POST"])
@jwt_required()
def trigger_scraping():
    """
    Dispara o scraping de livros manualmente.
    ---
    tags:
        - Scraping
    responses:
        200:
            description: Scraping iniciado com sucesso.
    """
    try:
        current_user = get_jwt_identity()

        if scraping_status["running"]:
            return jsonify({"message": "Scraping já está em execução!"}), 400

        def run_scraping():
            try:
                scraping_status.update({
                    "running": True,
                    "started_by": current_user,
                    "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "end_time": None,
                    "error": None,
                    "books_scraped": 0
                })
                print(f"[SCRAPER] Iniciado por {current_user} às {scraping_status['start_time']}")

                # Executa o scraping real
                books_scraper.main()

                # Após o término, lê o CSV pra contabilizar livros
                import pandas as pd
                df = pd.read_csv(books_scraper.OUT_PATH, encoding="utf-8-sig")
                scraping_status["books_scraped"] = len(df)

                scraping_status["end_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
                scraping_status["running"] = False
                print("[SCRAPER] Finalizado com sucesso!")
            except Exception as e:
                scraping_status.update({
                    "running": False,
                    "error": str(e),
                    "end_time": time.strftime("%Y-%m-%d %H:%M:%S")
                })
                print(f"[SCRAPER] Erro: {e}")

        # Dispara thread
        threading.Thread(target=run_scraping, daemon=True).start()

        return jsonify({
            "message": "Scraping iniciado com sucesso.",
            "started_by": current_user,
            "status": "em execução"
        }), 200

    except Exception as e:
        return jsonify({"error": f"Erro ao iniciar scraping: {str(e)}"}), 500


@app.route("/api/v1/scraping/status", methods=["GET"])
@jwt_required()
def get_scraping_status():
    """
    Retorna o status atual do scraping.
    ---
    tags:
        - Scraping
    responses:
        200:
            description: Status atual do scraping.
    """
    return jsonify(scraping_status), 200



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


# Adição de configurações para o JWT_Manager
# Caso o token não seja fornecido
@jwt.unauthorized_loader
def unauthorized_response(callback):
    return jsonify({"error": "Missing or invalid token"}), 401


# Caso o token esteja inválido
@jwt.invalid_token_loader
def invalid_token_response(callback):
    return jsonify({"error": "Invalid token"}), 401


# Caso o token tenha expirado
@jwt.expired_token_loader
def expired_token_response(callback, payload):
    return jsonify({"error": "Token has expired"}), 401

@app.route('/dashboard')
@jwt_required()
def dashboard():
    """
    Dashboard visual autenticado via JWT (token simples)
    """
    try:
        current_user = get_jwt_identity()  # string
        html = f"""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <title>Dashboard</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f5f6fa;
                    margin: 0;
                    padding: 0;
                }}
                header {{
                    background-color: #2f3640;
                    color: white;
                    padding: 1rem;
                    text-align: center;
                }}
                .container {{
                    max-width: 900px;
                    margin: 40px auto;
                    background-color: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                }}
                .cards {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                }}
                .card {{
                    background: #74b9ff;
                    color: white;
                    border-radius: 10px;
                    padding: 20px;
                    text-align: center;
                    transition: transform 0.2s;
                }}
                .card:hover {{
                    transform: scale(1.05);
                }}
                .logout {{
                    background: #d63031;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    float: right;
                }}
                .logout:hover {{
                    background: #ff7675;
                }}
            </style>
        </head>
        <body>
            <header>
                <h2>📊 Dashboard</h2>
            </header>
            <div class="container">
                <button class="logout" onclick="logout()">Sair</button>
                <h1>Bem-vindo, {current_user}!</h1>
                <p>Autenticado com sucesso em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                
                <div class="cards">
                    <div class="card">
                        <h3>📚 Livros</h3>
                        <p>128 cadastrados</p>
                    </div>
                    <div class="card">
                        <h3>👥 Usuários</h3>
                        <p>57 registrados</p>
                    </div>
                    <div class="card">
                        <h3>⭐ Avaliações</h3>
                        <p>Média 4.8</p>
                    </div>
                    <div class="card">
                        <h3>🕒 Sessão</h3>
                        <p>Ativa há 12 min</p>
                    </div>
                </div>
            </div>
            
            <script>
                function logout() {{
                    alert("Você saiu com sucesso!");
                    window.location.href = '/test-dashboard';
                }}
            </script>
        </body>
        </html>
        """
        return html
    except Exception as e:
        return jsonify({"error": f"Erro no dashboard: {str(e)}"}), 500



@app.route('/test-dashboard')
def test_dashboard():
    """
    Página de teste para autenticar e acessar o dashboard
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Dashboard</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f1f2f6;
                text-align: center;
                padding-top: 100px;
            }
            button {
                padding: 10px 20px;
                background-color: #0984e3;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }
            button:hover {
                background-color: #74b9ff;
            }
            #result {
                margin-top: 30px;
                font-size: 16px;
                color: #2d3436;
            }
        </style>
    </head>
    <body>
        <h1>🔐 Teste de Acesso ao Dashboard</h1>
        <p>Insira o token JWT para visualizar a página protegida:</p>
        <button onclick="testAccess()">Acessar Dashboard</button>
        <div id="result"></div>
        
        <script>
        async function testAccess() {
            const token = prompt("Cole seu token JWT:");
            if (!token) return;
            
            try {
                const response = await fetch('/dashboard', {
                    headers: {
                        'Authorization': 'Bearer ' + token
                    }
                });
                const html = await response.text();
                document.open();
                document.write(html);
                document.close();
            } catch (error) {
                document.getElementById('result').innerHTML = 'Erro: ' + error;
            }
        }
        </script>
    </body>
    </html>
    """
    return html

#---------- Desafio 3 : Monitoramento de Analytics ------------------
#Logs estruturados de todas as chamadas de API (incluindo parâmetros, respostas e tempos de resposta)
#Metricas de performance da API (tempo médio de resposta, taxa de erro)
# A etapa 1 e 2 foram mescladas, porque conter dois app.before_request e app.after_request pode gerar conflitos na aplicação
import logging
from time import time
import services.database.models.base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.before_request
def log_request_info():
    """ if "Authorization" not in request.headers and "access_token" in session:
		request.headers = request.headers.copy()
		request.headers["Authorization"] = f"Bearer {session['access_token']}" """

    # Inicia o timer para medir o tempo da requisição
    request.start_time = time()
    # Faz log básico da requisição
    logger.info(
        f"Request: {request.method} {request.url} - Body: {request.get_data()}"
    )

    public_routes = [
        "/", "/apidocs/", "/apispec.json", "/flasgger_static/",
        "/api/v1/auth/login", "/api/v1/health"
    ]

    # Libera tudo que comece com /apidocs ou /flasgger_static (Swagger UI)
    if any(request.path.startswith(route) for route in public_routes):
        return
    try:
        verify_jwt_in_request()
        current_user = get_jwt_identity()
        logger.info(f"Usuário foi autenticado : {current_user}")
    except exceptions.NoAuthorizationError:
        logger.warning(f"Tentativa de acesso sem token: {request.path}")
        return jsonify({"error": "Token de acesso não fornecido"}), 401
    except exceptions.InvalidHeaderError:
        logger.warning(f"Header de autorização inválido: {request.path}")
        return jsonify({"error": "Header de autorização inválido"}), 401
    except Exception as e:
        logger.error(f"Erro na verificação do token: {e}")
        return jsonify({"error": "Erro na autenticação"}), 401


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
            logger.info(
                f"Request to {request.path} took {duration:.4f} seconds")
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

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Database tables created.")
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
