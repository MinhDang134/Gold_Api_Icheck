from sqlmodel import SQLModel, Session, select
from typing import Type, TypeVar, Generic, Optional

ModelType = TypeVar("ModelType", bound=SQLModel)

class CRUDBase(Generic[ModelType]):
    # Generic[ModelType] : lớp tổng quát này là lớp cho phép có thể xử lú rất nhiều kiểu dữ liệu khác nhau đổ vào mà không bị lỗ
    def __init__(self, model: Type[ModelType]):
        self.model = model
#38 nhận được dữ liệu gồm db và data thì nó sẽ sử lý
    def create(self, db: Session, data: dict) -> ModelType:
        obj = self.model(**data) #39 cái là cái gì quên luôn rồi
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj#40 return về lại cái data sau khi thêm vào

    def get_by_id(self, db: Session, id: int) -> Optional[ModelType]:
        return db.exec(select(self.model).where(self.model.id == id)).first()


    def get_all(self, db: Session) -> list[ModelType]:
        return db.exec(select(self.model)).all()
