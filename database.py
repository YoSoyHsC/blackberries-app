import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///berries.db")

# Por si algún día la URL empieza con postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)

extra_args = {}
if DATABASE_URL.startswith("sqlite"):
    extra_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    pool_size=10,        # más conexiones en el pool
    max_overflow=20,     # conexiones extra permitidas
    pool_timeout=30,     # tiempo máximo de espera
    pool_pre_ping=True,  # verifica que la conexión siga viva
    pool_recycle=1800,   # recicla conexiones viejas (30 min)
    **extra_args
)

# scoped_session para poder hacer remove() al final de cada request
SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False)
)

Base = declarative_base()
