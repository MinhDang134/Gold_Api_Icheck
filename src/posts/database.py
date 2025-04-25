from contextlib import asynccontextmanager
import os
from sqlalchemy.orm import sessionmaker

from sqlmodel import create_engine, SQLModel, Session
from fastapi import FastAPI
import logging
ENV = os.getenv("ENV", "development")

if ENV == "docker":
  DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://minhdangpy134:minhdang@db:5432/gold_price")
else:
  DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://minhdangpy134:minhdang@localhost:5432/gold_price")
  logging.info(f"ENV: {ENV}, Database URL: {DATABASE_URL}")


engine = create_engine(
     DATABASE_URL,
     echo=ENV == "development",  # Only echo in development
     pool_pre_ping=True,  # Check connection before using
     pool_size=5,  # Number of connections in pool
     max_overflow=10,  # Number of connections that can exceed pool_size
     pool_timeout=30,  # Timeout for getting a connection from pool
     pool_recycle=1800  # Recycle connections after 30 minutes
  )

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
  )


def init_db():
    try:
        logging.info("Initializing database...")
        SQLModel.metadata.create_all(engine)
        logging.info("Database initialized successfully!")
    except Exception as e:
        logging.error(f"Error initializing database: {str(e)}")
        raise

