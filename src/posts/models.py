from sqlalchemy import table, Numeric
from sqlmodel import SQLModel , Field, Column
from sqlalchemy.sql import func
from decimal import Decimal
from datetime import datetime
class GoldPrice(SQLModel,table=True):
    __tablename__ = 'gold_prices'

    id:int = Field(default=None ,primary_key=True)
    price:Decimal = Field(sa_column=Column(Numeric(20, 2), nullable=False))
    timestamp:datetime = Field( default=func.now())
    price_per_ounce:Decimal = Field(sa_column=Column(Numeric(20, 2)))
    price_per_luong:Decimal = Field(sa_column=Column(Numeric(20, 2)))
    price_per_gram:Decimal = Field(sa_column=Column(Numeric(20, 2)))
