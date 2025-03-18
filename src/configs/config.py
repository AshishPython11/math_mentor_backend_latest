from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Define your database URL (replace with your actual DB details)
DATABASE_URL = "postgresql://postgres:root@localhost:5432/mtest"


engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

