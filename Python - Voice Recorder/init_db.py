# init_db.py
from models.database import Base, engine

# Import model modules so SQLAlchemy's declarative base knows about them
# Add new model imports here as models are added to the project.
try:
    # explicit import to register the tables
    import models.recording  # noqa: F401
except Exception:
    # If a model import fails, print a warning but still attempt to create tables
    print("⚠️ Warning: Failed to import one or more model modules; tables may be missing.")


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized.")
