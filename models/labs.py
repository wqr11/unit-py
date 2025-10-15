from sqlalchemy import *
from models.db_session import SqlAlchemyBase

class Labs(SqlAlchemyBase):
    __tablename__ = 'Labs'

    id = Column(String, primary_key=True)
    data_input = Column(String, nullable=True)
    data_output = Column(String, nullable=True)
    comment_for_ai = Column(String, nullable=True)