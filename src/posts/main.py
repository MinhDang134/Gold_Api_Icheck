# src/main.py

from fastapi import FastAPI

from src.posts.database import SessionLocal, init_db
from src.posts.router import router
import uvicorn
import os
# from src.posts.service import data_mau
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up...")
    try:
        print(f"Environment: {os.getenv('ENV', 'development')}")
        init_db()
        print("Database initialization completed")
    except Exception as e:
        print(f"Error during startup: {str(e)}")
        raise
    yield
    # Shutdown
    print("Shutting down...")


if __name__ == "__main__":
    # Set environment variable for local development
    os.environ["ENV"] = "development"
    uvicorn.run(
        "src.posts.main:app",
        host="localhost",
        port=8000,
        reload=True
    )

app = FastAPI(
    title="Gold Price API",
    description="API for Gold Price Management",
    version="1.0.0",
    lifespan=lifespan
        )
# Include router
app.include_router(router)

