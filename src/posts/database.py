from contextlib import asynccontextmanager
import os
from sqlalchemy.orm import sessionmaker
from sqlmodel import create_engine, SQLModel, Session

from fastapi import FastAPI
import logging

# Database configuration with environment variables
engine = create_engine("postgresql+psycopg2://minhdangpy134:minhdang@db:5432/gold_price")
SQLModel.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=engine)

