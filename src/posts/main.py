# src/main.py

from fastapi import FastAPI

from src.posts.database import SessionLocal
from src.posts.router import router
import uvicorn
# from src.posts.service import data_mau
from contextlib import asynccontextmanager
app = FastAPI()

if __name__ == "__main__":
    uvicorn.run("src.posts.main:app", host="localhost", port=8002, reload=True)

# @app.on_event("startup")
# async def startup_event():
#     await data_mau()
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Include router
app.include_router(router)

