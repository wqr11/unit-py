from sqlalchemy import String, Column, Boolean
from models.db_session import SqlAlchemyBase

class Users(SqlAlchemyBase):
    __tablename__ = 'users'

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    is_student = Column(Boolean, nullable=False)