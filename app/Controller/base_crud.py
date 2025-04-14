from sqlmodel import SQLModel, Session, select
from typing import Type, TypeVar, Generic, Optional

ModelType = TypeVar("ModelType", bound=SQLModel)

class CRUDBase(Generic[ModelType]):
    # Generic[ModelType] : lớp tổng quát này là lớp cho phép có thể xử lú rất nhiều kiểu dữ liệu khác nhau đổ vào mà không bị lỗi


    def __init__(self, model: Type[ModelType]):
        self.model = model

    def create(self, db: Session, data: dict) -> ModelType:
        obj = self.model(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def get_by_id(self, db: Session, id: int) -> Optional[ModelType]:
        return db.exec(select(self.model).where(self.model.id == id)).first()


    def get_all(self, db: Session) -> list[ModelType]:
        return db.exec(select(self.model)).all()
