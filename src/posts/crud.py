# src/Controller/crud.py
from sqlmodel import Session
from src.posts import models
from src.posts.base_crud import CRUDBase
from datetime import datetime

gold_crud = CRUDBase(models.GoldPrice)
save_search_gold = CRUDBase(models.Save_search_gold)
def get_gold_prices_in_range(db: Session, start_date: str, end_date: str):
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    return (db.query(models.GoldPrice)
            .filter(models.GoldPrice.timestamp >= start_date,
                    models.GoldPrice.timestamp <= end_date).all())
