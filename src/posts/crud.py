# src/Controller/crud.py
from sqlmodel import Session,func
from src.posts import models
from src.posts.base_crud import CRUDBase
import logging
import json
from datetime import datetime

gold_crud = CRUDBase(models.GoldPrice)
save_search_gold = CRUDBase(models.Save_search_gold)
def get_gold_prices_in_range(db: Session, start_date: str, end_date: str):
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    return (db.query(models.GoldPrice)
            .filter(models.GoldPrice.timestamp >= start_date,
                    models.GoldPrice.timestamp <= end_date).all())

def get_data_indatabase(db : Session , date : str):
    # nếu mà date truyền vào mà không có thì tính sau giờ cứ lấy trong database đã
    kiemtra_date = datetime.strptime(date,"%Y-%m-%d").date()
    return (db.query(models.GoldPrice).filter(func.date(models.GoldPrice.timestamp) == kiemtra_date).all())


def increment_search_count(db: Session, date: str) -> int:
    """Tăng số lần tìm kiếm cho một ngày"""
    search_count = db.query(models.SearchCount).filter(models.SearchCount.date == date).first()

    if search_count:
        search_count.count += 1
        search_count.last_updated = datetime.now()
    else:
        search_count = models.SearchCount(date=date, count=1)
        db.add(search_count)

    db.commit()
    db.refresh(search_count)
    return search_count.count


def get_search_count(db: Session, date: str) -> int:
    """Lấy số lần tìm kiếm cho một ngày"""
    search_count = db.query(models.SearchCount).filter(models.SearchCount.date == date).first()
    return search_count.count if search_count else 0