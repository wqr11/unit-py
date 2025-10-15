from sqlalchemy import *
from models.db_session import SqlAlchemyBase
from pydantic import BaseModel


class LabsBase(BaseModel):
    id: str
    data_input: str
    data_output: str

class Labs(SqlAlchemyBase):
    __tablename__ = 'Labs'

    id = Column(String, primary_key=True)
    data_input = Column(String, nullable=True)
    data_output = Column(String, nullable=True)
    comment_for_ai = Column(String, nullable=True)