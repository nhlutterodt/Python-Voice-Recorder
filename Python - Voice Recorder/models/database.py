# models/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_PATH = "db/app.db"
engine = create_engine(f"sqlite:///{DATABASE_PATH}", echo=False, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()
