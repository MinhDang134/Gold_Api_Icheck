# src/main.py

from fastapi import FastAPI
from src.posts.router import router

app = FastAPI()

app.include_router(router)
