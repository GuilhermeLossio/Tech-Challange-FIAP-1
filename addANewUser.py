from services.database.models.base import Base, User
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Configuração do banco (mesmo caminho do alembic.ini)
engine = create_engine("sqlite:///users.db", echo=True)

# Cria tabelas (se ainda não existirem)
Base.metadata.create_all(engine)

# Cria uma sessão
Session = sessionmaker(bind=engine)
session = Session()

# Adiciona um usuário
new_user = User(username="admin", password="password")  # futuramente hash
session.add(new_user)
session.commit()

print(f"Usuário {new_user.username} adicionado com ID {new_user.id}")
