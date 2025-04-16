# src/Controller/crud.py
from sqlmodel import Session
from src.posts import models
from src.posts.base_crud import CRUDBase
from datetime import datetime

gold_crud = CRUDBase(models.GoldPrice)
#47 sau khi nhận tham số thì hàm ngày nó sẽ chuyển định dạng tiếp
def get_gold_prices_in_range(db: Session, start_date: str, end_date: str):
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    #48 đây là cách để gán cái giá điểm đầu và điểm cuối để tính thời gian lấy
    end_date = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    return (db.query(models.GoldPrice) #49 lấy querry của cái model.goldprice để lấy cái from đó trong database
    #49 bằng câu query sau đó lọc nhưng bảng mà có thời gian lớn hơn hoặc bằng ngày start và nhỏ hơn hoặc bằng ngày cuối thêm all() là để gọi tất các phần tử
    #50 rồi sẽ return về danh sách đó
            .filter(models.GoldPrice.timestamp >= start_date,
                    models.GoldPrice.timestamp <= end_date).all())
