from sqlmodel import Session
from decimal import Decimal
from app.Model import models
from datetime import datetime


def create_gold_price(db: Session, price: Decimal, price_per_ounce: Decimal, price_per_luong: Decimal, price_per_gram: Decimal):
    new_gold_price = models.GoldPrice(
        price=price,
        price_per_ounce=price_per_ounce,
        price_per_luong=price_per_luong,
        price_per_gram=price_per_gram
    )
    db.add(new_gold_price)
    db.commit()
    db.refresh(new_gold_price)
    return new_gold_price

def get_gold_prices_in_range(db: Session, start_date: str, end_date: str):
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    end_date = end_date.replace(hour=23, minute=59, second=59)
    return (db.query(models.GoldPrice)
            .filter(models.GoldPrice.timestamp >= start_date,
                    models.GoldPrice.timestamp <= end_date).all())
