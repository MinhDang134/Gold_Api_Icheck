from pydantic import BaseModel #xtdlrq
from datetime import datetime
from decimal import Decimal

class DateRange(BaseModel):
    start_date: datetime
    end_date: datetime


class GoldPriceBase(BaseModel):
    price: Decimal
    timestamp: datetime

class GoldPriceCreate(GoldPriceBase):
    pass



class GoldPrice(GoldPriceBase):
    id: int
    price_per_ounce: Decimal
    price_per_luong: Decimal
    price_per_gram: Decimal

    class Config:
        from_attributes = True
