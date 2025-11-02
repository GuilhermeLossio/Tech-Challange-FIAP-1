# Challanger API

A **Challanger API** é uma interface RESTful para gerenciamento de usuários, autenticação e manipulação de desafios de programação. Ela foi desenvolvida em **Python (Flask)** com **SQLite** como banco de dados e inclui autenticação via JWT.

---

## 🚀 Funcionalidades

* Registro e autenticação de usuários
* Criação, listagem e exclusão de desafios
* Sistema de pontuação e progresso
* Validação via token JWT

---

## ⚙️ Instalação

### Pré-requisitos

* Python 3.10+
* pip

### Passos

```bash
git clone https://github.com/seuusuario/challanger-api.git
cd challanger-api
pip install -r requirements.txt
```

### Executando o servidor localmente

```bash
python services/api/src/app.py
```

O servidor rodará em: `http://127.0.0.1:5000`

---

## 🔑 Autenticação

A API utiliza **JWT (JSON Web Token)**. Para obter o token, envie uma requisição `POST` para `/login` com suas credenciais:

```json
{
  "username": "admin",
  "password": "admin
```

A resposta conterá o token:

```json
{
  "access_token": "<seu_token_aqui>"
}
```

Use esse token no cabeçalho `Authorization` para acessar rotas protegidas:

```
Authorization: Bearer <seu_token_aqui>
```

---

## 📘 Endpoints da API – Versão Completa

### 🔹 Endpoints Obrigatórios (Core)

| Método | Rota | Descrição |
| ------ | ---- | --------- |
| `GET` | `/api/v1/books` | Lista todos os livros disponíveis na base de dados |
| `GET` | `/api/v1/books/{id}` | Retorna detalhes completos de um livro específico pelo ID |
| `GET` | `/api/v1/books/search?title={title}&category={category}` | Busca livros por título e/ou categoria |
| `GET` | `/api/v1/categories` | Lista todas as categorias de livros disponíveis |
| `GET` | `/api/v1/health` | Verifica status da API e conectividade com os dados |

---

### 🔹 Endpoints Opcionais (Insights)

| Método | Rota | Descrição |
| ------ | ---- | --------- |
| `GET` | `/api/v1/stats/overview` | Estatísticas gerais da coleção (total de livros, preço médio, distribuição de ratings) |
| `GET` | `/api/v1/stats/categories` | Estatísticas detalhadas por categoria (quantidade de livros, preços por categoria) |
| `GET` | `/api/v1/books/top-rated` | Lista os livros com melhor avaliação (rating mais alto) |
| `GET` | `/api/v1/books/price-range?min={min}&max={max}` | Filtra livros dentro de uma faixa de preço específica |

---

### 🔹 Endpoints de Autenticação

| Método | Rota | Descrição |
| ------ | ---- | --------- |
| `POST` | `/api/v1/auth/login` | Obter token JWT |
| `POST` | `/api/v1/auth/refresh` | Renovar token JWT |

---

### 🔹 Endpoints de Machine Learning

| Método | Rota | Descrição |
| ------ | ---- | --------- |
| `GET` | `/api/v1/ml/features` | Dados formatados para features |
| `GET` | `/api/v1/ml/training-data` | Dataset para treinamento |
| `POST` | `/api/v1/ml/predictions` | Endpoint para receber predições |

---


## 🧠 Estrutura do projeto

```
├── 📁 data
│   ├── 📁 bronze
│   │   └── 📄 books.csv
│   └── 📁 silver
│       ├── 📄 books.csv
│       └── 📄 books.parquet
├── 📁 docs
│   └── 📝 api_documentation.md
├── 📁 instance
│   └── 📄 users.db
├── 📁 migrations
│   ├── 📁 versions
│   ├── 📄 README
│   ├── 🐍 env.py
│   └── 📄 script.py.mako
├── 📁 services
│   ├── 📁 api
│   │   └── 📁 src
│   │       └── 🐍 app.py
│   ├── 📁 database
│   │   └── 📁 models
│   │       └── 🐍 base.py
│   ├── 📁 resources
│   │   └── 🐍 Extract.py
│   └── 📁 scraper
│       ├── 📁 extractors
│       │   └── 🐍 scrape_books.py
│       └── 📁 transformers
│           └── 🐍 clean_books.py
├── 📝 README.md
├── 🐍 addANewUser.py
├── ⚙️ alembic.ini
├── 📄 requirements.txt
└── 📄 users.db
```

---

## 🧩 Exemplo de uso com `curl`

```bash
curl -X POST http://127.0.0.1:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"1234"}'
```

---

## 🔒 Segurança

* Todas as rotas críticas exigem JWT válido.
* Tokens têm tempo de expiração configurável.
* As senhas são armazenadas com hash (bcrypt ou werkzeug.security).

---

## 🧰 Tecnologias utilizadas

* Flask
* Flask-JWT-Extended
* SQLite
* SQLAlchemy
* Werkzeug

---

## 🧪 Testes

Você pode rodar os testes unitários com:

```bash
pytest tests/
```

---

## 📜 Licença

Este projeto está sob a licença MIT — veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## 🤝 Contribuições

Sinta-se livre para abrir **issues** e **pull requests**. Toda ajuda é bem-vinda!

---

### 💬 Contato

**Autor:** Guilherme Ferreira Medeiros Lossio
**GitHub:** [@guilhermelossio](https://github.com/guilhermelossio)
