# init_db.py
from models.database import Base, engine

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized.")
