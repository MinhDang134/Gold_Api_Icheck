from contextlib import asynccontextmanager

from sqlalchemy.orm import sessionmaker
from sqlmodel import create_engine,SQLModel,Session
from fastapi import FastAPI
from src.posts.service import data_mau

app = FastAPI()
SQLALCHEMY_DATABASE_URL = "postgresql://minhdang:minhdang@localhost:5432/gold_price"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SQLModel.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False,autoflush=False,bind = engine)
#SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#Base = declarative_base()
@asynccontextmanager
async def get_db(app: FastAPI):
    db = SessionLocal()
    try:
        await data_mau()
        yield db
    finally:
        db.close()
app.add_event_handler("startup", get_db)