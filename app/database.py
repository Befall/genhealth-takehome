import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Get database URL from environment, with fallback
# Priority: DATABASE_URL env var > DATA_PATH env var > local default
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    # Fallback to old DATA_PATH behavior for Railway compatibility
    data_path = os.getenv("DATA_PATH", ".")
    db_path = os.path.join(data_path, "orders.db")
    DATABASE_URL = f"sqlite:///{db_path}"

SQLALCHEMY_DATABASE_URL = DATABASE_URL

# Create engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()
