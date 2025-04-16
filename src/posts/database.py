from sqlalchemy.orm import sessionmaker
from sqlmodel import create_engine,SQLModel,Session


SQLALCHEMY_DATABASE_URL = "postgresql://minhdang:minhdang@localhost:5432/gold_price"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SQLModel.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False,autoflush=False,bind = engine)
#SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#Base = declarative_base()
